"""Turn deliverable files into plain facts: pages, words, fonts, margins, comments, sheets...

Every reader returns a dict. A value of None means "could not be determined" — checks treat that
as unverified, never as passed.
"""
import collections
import io
import logging
import os
import re
import shutil
import tempfile
import zipfile

MM_PER_PT = 25.4 / 72
EMU_PER_MM = 36000
WORD_RE = re.compile(r"[^\W\d_]+(?:[-'’][^\W\d_]+)*")
PLACEHOLDER_RE = re.compile(
    r"lorem ipsum|\bTODO\b|\bTBD\b|\bXXX+\b|\[\s*(?:вставить|вставити|insert|текст|text|название|назва|name)"
    r"[^\]]*\]|<\s*(?:вставить|вставити|insert)[^>]*>|вставьте текст|вставте текст|insert text here|"
    r"click here to (?:add|enter)|нажмите,? чтобы добавить|натисніть,? щоб додати", re.I)
ZIP_JUNK_RE = re.compile(r"(^|/)(__MACOSX/|\.DS_Store$|Thumbs\.db$|desktop\.ini$|~\$|\._)", re.I)
FORMULA_ERRORS = {"#REF!", "#DIV/0!", "#VALUE!", "#NAME?", "#N/A", "#NUM!", "#NULL!", "#SPILL!", "#CALC!"}
DOC_EXTS = {"pdf", "docx", "pptx", "xlsx"}

logging.getLogger("pdfminer").setLevel(logging.ERROR)


def count_words(text):
    return len(WORD_RE.findall(text or ""))


def placeholders(text):
    return sorted({m.group(0).strip() for m in PLACEHOLDER_RE.finditer(text or "")})


def main_value(weights):
    """Value with the most characters behind it (None if nothing is known)."""
    known = {k: v for k, v in weights.items() if k is not None}
    if not known:
        return None
    return max(known, key=known.get)


def paper(w_mm, h_mm):
    """(name, orientation) for a page size in mm."""
    short, long_ = sorted((w_mm, h_mm))
    names = {"A3": (297, 420), "A4": (210, 297), "A5": (148, 210), "Letter": (215.9, 279.4),
             "Legal": (215.9, 355.6)}
    name = next((n for n, (a, b) in names.items() if abs(short - a) <= 3 and abs(long_ - b) <= 3), None)
    orientation = "landscape" if w_mm > h_mm + 1 else "portrait" if h_mm > w_mm + 1 else "square"
    return name, orientation


# ---------- PDF ----------

def read_pdf(path):
    import pdfplumber

    f = {"kind": "pdf"}
    with pdfplumber.open(path) as pdf:
        f["pages"] = len(pdf.pages)
        texts, fonts, sizes, images, annots = [], collections.Counter(), collections.Counter(), 0, 0
        for page in pdf.pages:
            texts.append(page.extract_text() or "")
            for c in page.chars:
                fonts[re.sub(r"^[A-Z]{6}\+", "", c.get("fontname", ""))] += 1
                sizes[round(c.get("size", 0) * 2) / 2] += 1
            images += len(page.images)
            annots += sum(1 for a in page.annots
                          if str((a.get("data") or {}).get("Subtype", "")).strip("/'") in ("Text", "FreeText"))
        first = pdf.pages[0] if pdf.pages else None
        if first is not None:
            w, h = float(first.width) * MM_PER_PT, float(first.height) * MM_PER_PT
            f["page_mm"] = [round(w, 1), round(h, 1)]
            f["paper"], f["orientation"] = paper(w, h)
    f["text"] = "\n".join(texts)
    f["words"] = count_words(f["text"])
    f["main_font"] = main_value(fonts) if fonts else None
    f["main_font_size"] = main_value(sizes) if sizes else None
    f["images"] = images
    f["comments"] = annots
    f["headings"] = None  # PDF has no reliable heading structure; checks fall back to text lines
    f["margins_mm"] = None
    return f


# ---------- DOCX ----------

def _style_attr(style, attr):
    while style is not None:
        value = getattr(style.font, attr)
        if value is not None:
            return value
        style = style.base_style
    return None


def _theme_minor_font(z):
    try:
        xml = z.read("word/theme/theme1.xml").decode("utf-8", "replace")
    except KeyError:
        return None
    m = re.search(r"<a:minorFont>\s*<a:latin typeface=\"([^\"]+)\"", xml)
    return m.group(1) if m else None


def _doc_defaults(z):
    """Font and size from <w:docDefaults> (used when no style sets them)."""
    try:
        xml = z.read("word/styles.xml").decode("utf-8", "replace")
    except KeyError:
        return None, None
    m = re.search(r"<w:docDefaults>.*?</w:docDefaults>", xml, re.S)
    if not m:
        return None, None
    block = m.group(0)
    font = re.search(r"<w:rFonts [^>]*w:ascii=\"([^\"]+)\"", block)
    theme = re.search(r"<w:rFonts [^>]*w:asciiTheme=\"minor", block)
    size = re.search(r"<w:sz w:val=\"(\d+)\"", block)
    return (font.group(1) if font else ("@minor" if theme else None),
            int(size.group(1)) / 2 if size else None)


def read_docx(path):
    import docx

    f = {"kind": "docx"}
    d = docx.Document(path)
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
        body = z.read("word/document.xml").decode("utf-8", "replace")
        default_font, default_size = _doc_defaults(z)
        if default_font == "@minor":
            default_font = _theme_minor_font(z)
        app = z.read("docProps/app.xml").decode("utf-8", "replace") if "docProps/app.xml" in names else ""
        comments_xml = z.read("word/comments.xml").decode("utf-8", "replace") if "word/comments.xml" in names else ""
        f["images"] = sum(1 for n in names if n.startswith("word/media/"))
    f["comments"] = len(re.findall(r"<w:comment ", comments_xml))
    f["tracked_changes"] = len(re.findall(r"<w:(?:ins|del|moveFrom|moveTo) ", body))

    paragraphs = list(d.paragraphs)
    for t in d.tables:
        for row in t.rows:
            for cell in row.cells:
                paragraphs.extend(cell.paragraphs)
    texts, headings = [], []
    fonts, sizes = collections.Counter(), collections.Counter()
    for p in paragraphs:
        text = p.text
        texts.append(text)
        style_name = (p.style.name if p.style is not None else "") or ""
        if text.strip() and re.match(r"(heading|title|заголовок|название|назва)", style_name, re.I):
            headings.append(text.strip())
        for run in p.runs:
            n = len(run.text.strip())
            if not n:
                continue
            font = run.font.name or _style_attr(p.style, "name") or default_font
            size = run.font.size or _style_attr(p.style, "size")
            size = size.pt if size is not None else default_size
            fonts[font] += n
            sizes[size] += n
    f["text"] = "\n".join(texts)
    f["words"] = count_words(f["text"])
    f["headings"] = headings
    f["main_font"] = main_value(fonts)
    f["main_font_size"] = main_value(sizes)

    s = d.sections[0]
    if s.page_width and s.page_height:
        w, h = s.page_width / EMU_PER_MM, s.page_height / EMU_PER_MM
        f["page_mm"] = [round(w, 1), round(h, 1)]
        f["paper"], f["orientation"] = paper(w, h)
    margins = {k: getattr(s, f"{k}_margin") for k in ("left", "right", "top", "bottom")}
    f["margins_mm"] = ({k: round(v / EMU_PER_MM, 1) for k, v in margins.items()}
                       if all(v is not None for v in margins.values()) else None)

    # Page count only exists if Word saved it. Trust it only when the saved word count matches the
    # real one, otherwise it is stale (e.g. a generated file still saying "1 page, 0 words").
    pages = re.search(r"<Pages>(\d+)</Pages>", app)
    saved_words = re.search(r"<Words>(\d+)</Words>", app)
    f["pages"] = None
    if pages and saved_words and f["words"]:
        if abs(int(saved_words.group(1)) - f["words"]) <= max(10, 0.15 * f["words"]):
            f["pages"] = int(pages.group(1))
    return f


# ---------- PPTX ----------

def read_pptx(path):
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    f = {"kind": "pptx"}
    prs = Presentation(path)
    texts, titles, images, charts = [], [], 0, 0

    def walk(shapes):
        nonlocal images, charts
        for sh in shapes:
            if sh.shape_type == MSO_SHAPE_TYPE.GROUP:
                walk(sh.shapes)
                continue
            if sh.shape_type == MSO_SHAPE_TYPE.PICTURE:
                images += 1
            if getattr(sh, "has_chart", False) and sh.has_chart:
                charts += 1
            if sh.has_text_frame:
                texts.append(sh.text_frame.text)
            if getattr(sh, "has_table", False) and sh.has_table:
                for row in sh.table.rows:
                    for cell in row.cells:
                        texts.append(cell.text)

    for slide in prs.slides:
        walk(slide.shapes)
        title = slide.shapes.title
        if title is not None and title.text.strip():
            titles.append(title.text.strip())
    with zipfile.ZipFile(path) as z:
        f["comments"] = sum(len(re.findall(rb"<p:cm ", z.read(n))) for n in z.namelist()
                            if n.startswith("ppt/comments/"))
    f["slides"] = len(prs.slides)
    f["pages"] = f["slides"]
    f["text"] = "\n".join(texts)
    f["words"] = count_words(f["text"])
    f["headings"] = titles
    f["images"] = images + charts
    f["main_font"] = f["main_font_size"] = None
    w, h = prs.slide_width / EMU_PER_MM, prs.slide_height / EMU_PER_MM
    f["page_mm"] = [round(w, 1), round(h, 1)]
    f["paper"], f["orientation"] = paper(w, h)
    f["margins_mm"] = None
    return f


# ---------- XLSX ----------

def read_xlsx(path):
    import openpyxl

    f = {"kind": "xlsx"}
    values = openpyxl.load_workbook(path, data_only=True, read_only=True)
    formulas = openpyxl.load_workbook(path, data_only=False, read_only=True)
    try:
        f["sheets"] = list(values.sheetnames)
        texts, errors, empty, uncalculated, comments = [], [], [], 0, 0
        for name in values.sheetnames:
            ws_v, ws_f = values[name], formulas[name]
            filled = 0
            for row_v, row_f in zip(ws_v.iter_rows(), ws_f.iter_rows()):
                for cv, cf in zip(row_v, row_f):
                    v = cv.value
                    is_formula = isinstance(cf.value, str) and cf.value.startswith("=")
                    if v is None and is_formula:
                        uncalculated += 1
                    if v is None:
                        continue
                    filled += 1
                    if isinstance(v, str):
                        if v.strip() in FORMULA_ERRORS:
                            errors.append(f"{name}!{cv.coordinate}: {v.strip()}")
                        else:
                            texts.append(v)
            if not filled:
                empty.append(name)
        f["formula_errors"] = errors
        # Formulas saved without results (files written by scripts): their errors can't be known.
        f["uncalculated_formulas"] = uncalculated
        f["empty_sheets"] = empty
    finally:
        values.close()
        formulas.close()
    with zipfile.ZipFile(path) as z:
        f["comments"] = sum(len(re.findall(rb"<comment ", z.read(n))) for n in z.namelist()
                            if re.match(r"xl/comments\d*\.xml", n))
    f["text"] = "\n".join(texts)
    f["words"] = count_words(f["text"])
    f["headings"] = None
    f["pages"] = None
    f["images"] = None
    f["main_font"] = f["main_font_size"] = None
    f["margins_mm"] = None
    return f


READERS = {"pdf": read_pdf, "docx": read_docx, "pptx": read_pptx, "xlsx": read_xlsx}


def read_file(path, name=None):
    ext = os.path.splitext(path)[1].lower().lstrip(".")
    f = {"name": name or os.path.basename(path), "ext": ext, "size_bytes": os.path.getsize(path)}
    reader = READERS.get(ext)
    if reader:
        try:
            f.update(reader(path))
        except Exception as e:  # a broken file is a finding, not a crash
            f["error"] = f"cannot read: {type(e).__name__}: {e}"
    if "text" in f:
        f["placeholders"] = placeholders(f["text"])
    return f


def read_zip(path, depth=0):
    f = {"name": os.path.basename(path), "ext": "zip", "kind": "zip", "size_bytes": os.path.getsize(path)}
    tmp = tempfile.mkdtemp(prefix="guard_")
    inner = []
    try:
        with zipfile.ZipFile(path) as z:
            entries = [i for i in z.infolist() if not i.is_dir()]
            f["entries"] = [i.filename for i in entries]
            f["junk"] = [n for n in f["entries"] if ZIP_JUNK_RE.search(n)]
            for i in entries:
                if ZIP_JUNK_RE.search(i.filename):
                    continue
                safe = os.path.normpath(i.filename).lstrip("\\/.")
                target = os.path.join(tmp, safe)
                if not os.path.abspath(target).startswith(os.path.abspath(tmp)):
                    continue  # path traversal attempt
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with z.open(i) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
                label = f"{f['name']}/{i.filename}"
                if target.lower().endswith(".zip") and depth < 2:
                    sub = read_zip(target, depth + 1)
                    sub["name"] = label
                    inner.append(sub)
                    inner.extend(sub.pop("inner", []))
                else:
                    fact = read_file(target, label)
                    fact["in_zip"] = f["name"]
                    inner.append(fact)
    except zipfile.BadZipFile as e:
        f["error"] = f"cannot read: {e}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    f["inner"] = inner
    return f


def read_deliverables(paths):
    """All submitted files, with ZIP contents flattened next to the archives."""
    out = []
    for p in paths:
        if p.lower().endswith(".zip"):
            z = read_zip(p)
            inner = z.pop("inner")
            out.append(z)
            out.extend(inner)
        else:
            out.append(read_file(p))
    return out
