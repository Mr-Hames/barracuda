"""Plain-text assignment (Russian, Ukrainian, English) -> contract: a list of requirements.

Rule-based on purpose: the same text always gives the same contract, so results can be measured.
Anything that looks like a requirement but is not understood becomes type "unverified" — it is
never checked and never reported as met.
"""
import re

EXT_PATTERNS = [
    ("pdf", r"\bpdf\b|пдф"),
    ("docx", r"\bdocx?\b|\bms ?word\b|\bword (?:document|file|format|doc)|\bin word\b|\bв word\b|"
             r"\bу word\b|ворд\w*|документ\w* word|\.docx"),
    ("pptx", r"\bpptx?\b|power ?point|презентац\w*|\bslide deck\b|\bdeck\b"),
    ("xlsx", r"\bxlsx?\b|excel|эксел\w*|ексел\w*|электронн\w* таблиц\w*|електронн\w* таблиц\w*|spreadsheet"),
    ("zip", r"\bzip\b|архив\w*|архів\w*|\barchive\b"),
]
U_PAGES = r"страниц\w*|\bстр\b\.?|сторін\w*|\bpages?\b|(?:(?<=\d)|(?<=\d ))с(?:\.|$)"  # "10–12 с."
U_SLIDES = r"слайд\w*|\bslides?\b"
U_WORDS = r"\bслов\w*|\bслів\b|\bwords?\b"
U_IMAGES = (r"рисун\w*|иллюстрац\w*|изображен\w*|картин\w*|ілюстрац\w*|зображен\w*|малюн\w*|диаграмм\w*|"
            r"діаграм\w*|график\w*|графік\w*|\bimages?\b|\bfigures?\b|\bpictures?\b|\bcharts?\b|"
            r"\billustrations?\b|\bdiagrams?\b|\bphotos?\b|фото\w*")
U_MB = r"(?<![a-zа-я])мб\b|(?<![a-zа-я])mb\b|мегабайт\w*|megabytes?|(?<![a-zа-я])мбайт\b"
U_SHEETS = r"\bлист\w*|\bаркуш\w*|\bsheets?\b|вкладк\w*|\btabs?\b"

Q_EXACT = r"ровно|рівно|exactly|строго|точно"
Q_MIN = (r"не менее|не меньше|минимум|как минимум|не менше|щонайменше|мінімум|принаймні|хотя бы|"
         r"at least|minimum(?: of)?|\bmin\b\.?|no less than|no fewer than")
Q_MORE = r"(?<!не )(?:более чем|более|больше)|понад|(?<!не )більше ніж|(?<!no )(?<!not )more than|\bover\b"
Q_MAX = (r"не более|не больше|максимум|не більше|не перевищ\w*|не превыша\w*|не длиннее|\bдо\b|up to|"
         r"at most|maximum(?: of)?|\bmax\b\.?|no more than|not exceed\w*|not more than|within|limit(?:ed)? to|"
         r"\blimit\b(?: is)?:?")
Q_LESS = r"(?<!не )(?:менее|меньше|менше)|less than|fewer than|\bunder\b"
Q_AFTER_MIN = r"^\s*(?:или более|и более|і більше|або більше|or more|and more|\+)"
Q_AFTER_MAX = r"^\s*(?:или меньше|или менее|и менее|або менше|or less|or fewer|max)"

CUE = re.compile(
    r"долж|необходим|нужно|надо|требу|следует|обязател|повин|\bмає\b|мають|необхідн|потрібн|\bслід|"
    r"\bmust\b|\bshould\b|required|requires|\bneed|has to|have to|ensure|make sure|please|"
    r"использ|використ|оформ|сда[йтв]|сдать|здай|здат|надішл|надсил|подай|подат|отправ|пришл|прикреп|"
    r"\bsubmit|\bsend\b|upload|загруз|завантаж|\binclude|\badd\b|добав|прилож|додай|\buse\b|\bkeep\b|"
    r"\bsave\b|сохран|збереж|не допуска|не допуска|\bбез\b|without|avoid|не более|не менее|"
    r"не більше|не менше|at least|at most|no more|допускается|допускаєт|приним|прийма|accepted|"
    r"минимум|максимум|мінімум|максимум|minimum|maximum|\bобъ[её]м|\bобсяг|\blength\b|\bvolume\b", re.I)
SUBJECTIVE = re.compile(
    r"оригинальн|уникальн|грамотн|логичн|качествен|професс?иональн|професійн|\btone\b|стил[ьюе]\b|"
    r"\bstyle\b|актуальн|убедительн|переконлив|аргумент|креатив|интересн|цікав|понятн|зрозуміл|\bclear\b|"
    r"concise|engaging|plagiar|плагиат|плагіат|антиплаг|deadline|\bсрок|\bтермін|дедлайн|оценк|оцінк|"
    r"\bgrade|источник|джерел|sources?\b|referenc|ссылк|посилан|самостоятельн|самостійн|own words|"
    r"своими словами|власними словами|accurate|точн[ыои]|корректн|коректн|релевант|relevant|appropriate|"
    r"уместн|доречн|красив|аккуратн|охайн|neat|polished|creative|persuasive|well[- ]|"
    r"\bзнак\w*|символ\w*|characters?\b|интервал\w*|інтервал\w*|spacing|гост|дсту|\bapa\b|\bmla\b", re.I)

KNOWN_FONTS = ["Times New Roman", "Arial", "Calibri", "Cambria", "Georgia", "Verdana", "Helvetica",
               "Tahoma", "Garamond", "Courier New", "Roboto", "Open Sans", "PT Serif", "PT Sans",
               "Liberation Serif", "Liberation Sans", "Segoe UI", "Book Antiqua", "Century Gothic"]
NAME_PLACEHOLDERS = (r"фамилия|прізвище|surname|last ?name|first ?name|name|имя|ім'?я|фио|піб|группа|група|"
                     r"group|номер|number|студент|student|id|дата|date|вариант|варіант|variant")


ABBREV = re.compile(r"(?:^|\s)(?:max|min|incl|excl|approx|e\.g|i\.e|etc|vs|no|стр|с|см|мм|лев|прав|верх|"
                    r"ниж|т\.е|т\.к|напр|мин|макс|прим|рис|табл|п|пп|гл|ч|мін|макс)\.$", re.I)
CONTEXT = re.compile(r"^\s*(?:тема|дисциплина|дисципліна|предмет|курс|course|topic|subject|module|модуль|группа|"
                     r"група|group|преподаватель|викладач|teacher|instructor|lecturer|задание|завдання|"
                     r"assignment|task|вариант|варіант)\b[^:—]{0,30}[:—]", re.I)
HEADING = re.compile(r"^[^.!?]{0,60}:$|"
                     r"^(?:требования|вимоги|requirements|оформление|оформлення|formatting)\b[^.]{0,40}$",
                     re.I)
NUMBER_WORDS = [
    (r"одн[ау]|один|одного|одной|one", "1"), (r"два|две|двух|дві|двох|two", "2"),
    (r"три|трех|трьох|three", "3"), (r"четыре|четырех|чотири|чотирьох|four", "4"),
    (r"пять|пяти|п'ять|п'яти|five", "5"), (r"шесть|шести|шість|six", "6"), (r"семь|семи|сім|seven", "7"),
    (r"восемь|восьми|вісім|eight", "8"), (r"девять|девяти|дев'ять|дев'яти|nine", "9"),
    (r"десять|десяти|ten", "10"), (r"двенадцати|двенадцать|дванадцяти|дванадцять|twelve", "12"),
    (r"пятнадцати|пятнадцать|п'ятнадцяти|п'ятнадцять|fifteen", "15"),
    (r"двадцати|двадцать|двадцяти|двадцять|twenty", "20"),
]


def norm(s):
    return re.sub(r"\s+", " ", s.replace("ё", "е").replace("’", "'")).strip()


def split_fragments(text):
    """Lines and sentences; bullets and numbering stripped."""
    out = []
    for line in text.splitlines():
        line = re.sub(r"^\s*(?:[-–—•*·▪●]|\d+[.)]|[a-zа-я][.)])\s+", "", line).strip()
        if not line:
            continue
        parts = []
        for part in re.split(r"(?<=[.!?])\s+(?=[«\"“A-ZА-ЯЁІЇЄҐ0-9])|;\s*", line):
            if parts and ABBREV.search(parts[-1]):
                parts[-1] += " " + part  # "Max. 800 words", "лев. – 3 см"
            else:
                parts.append(part)
        for part in parts:
            part = part.strip(" .")
            if part:
                out.append(part)
    return out


def numberize(text):
    """'пяти страниц' -> '5 страниц', '1,500 words' -> '1500 words', '3-х рисунков' -> '3 рисунков'."""
    t = norm(text).lower()
    t = re.sub(r"(?<=\d)[ \u00a0](?=\d{3}\b)", "", t)
    t = re.sub(r"(?<=\d),(?=\d{3}\b)", "", t)
    t = re.sub(r"(\d+)-(?:х|ти|ми|ох|ьох|и)\b", r"\1", t)
    for pattern, digit in NUMBER_WORDS:
        t = re.sub(r"(?<![\w'])(?:" + pattern + r")(?![\w'])", digit, t)
    return t


def exts_in(frag):
    low = frag.lower()
    return [ext for ext, pat in EXT_PATTERNS if re.search(pat, low)]


def to_number(s):
    return float(s.replace(",", "."))


def quantity(frag, unit, default="exact"):
    """(min, max) for a number attached to a unit, e.g. 'не менее 5 страниц' -> (5, None)."""
    low = frag.lower()
    num = r"(?<![a-zа-яё])(\d+(?:[.,]\d+)?)"
    matches = list(re.finditer(unit, low))
    if not matches:
        return None
    # "Word count: 930–1380 words": use the unit occurrence that has a number right before it
    m = next((x for x in matches if re.search(rf"{num}\s*(?:[^\d\s]+\s*){{0,2}}$", low[:x.start()])), matches[0])
    before, after = low[:m.start()], low[m.end():]
    rng = re.search(rf"(?:от|від|from|between)?\s*{num}\s*(?:-|–|—|до|to|and|и|і|по)\s*{num}\s*(?:[^\d\s]+\s*){{0,2}}$",
                    before)
    if rng:
        return to_number(rng.group(1)), to_number(rng.group(2))
    near = re.search(rf"{num}\s*(?:[^\d\s]+\s*){{0,2}}$", before)
    if near:
        n = to_number(near.group(1))
        lead = before[:near.start()][-40:]
        tail = after[:25]
    else:
        far = re.search(rf"^[^\d]{{0,40}}?{num}", after)
        if not far:
            return None
        n = to_number(far.group(1))
        lead = before[-40:] + " " + after[:far.start(1)]
        tail = after[far.end():far.end() + 25]
    if re.search(Q_EXACT, lead):
        return n, n
    if re.search(Q_AFTER_MIN, tail) or re.search(rf"(?:{Q_MIN})\s*[:—-]?\s*$", lead.strip() + " ") \
            or re.search(rf"(?:{Q_MIN})\W*$", lead) or re.search(rf"(?:{Q_MIN})\b[^\d,.;]{{0,20}}$", lead):
        # "minimum length 6 pages, maximum 8": an upper bound may follow
        upper = re.search(rf"^[^\d.;]{{0,15}}?(?:{Q_MAX})\s*{num}", low[m.end():])
        return n, (to_number(upper.group(1)) if upper else None)
    if re.search(rf"(?:{Q_MORE})\W*$", lead):
        return n + 1 if n == int(n) else n, None
    if re.search(Q_AFTER_MAX, tail) or re.search(rf"(?:{Q_MAX})\W*$", lead) \
            or re.search(rf"(?:{Q_MAX})\b[^\d,.;]{{0,20}}$", lead):
        return None, n
    if re.search(rf"(?:{Q_LESS})\W*$", lead):
        return None, n - 1 if n == int(n) else n
    if default == "min":
        return n, None
    if default == "max":
        return None, n
    if default == "about":
        return round(n * 0.9), round(n * 1.1)
    return n, n


def quoted(frag):
    return [q.strip() for q in re.findall(r"[«\"“„']([^«»\"“”„']{1,80})[»\"”']", frag) if q.strip()]


def listed(frag):
    """Items after a colon: 'разделы: Введение, Основная часть и Заключение'."""
    if ":" not in frag:
        return []
    tail = frag.rsplit(":", 1)[1]
    items = re.split(r",|;|\s+(?:и|і|та|and)\s+", tail)
    return [i.strip(" .«»\"“”'") for i in items if 1 < len(i.strip(" .«»\"“”'")) <= 60]


def name_regex(pattern):
    """'Фамилия_Группа_ЛР1.pdf' or '<Surname>_HW1.pdf' -> regex."""
    parts = re.split(r"(<[^>]+>|\[[^\]]+\]|\{[^}]+\})", pattern)
    out = []
    for p in parts:
        if not p:
            continue
        if re.fullmatch(r"<[^>]+>|\[[^\]]+\]|\{[^}]+\}", p):
            out.append(".+")
            continue
        tokens = re.split(r"([_\-. ])", p)
        for t in tokens:
            if re.fullmatch(rf"(?:{NAME_PLACEHOLDERS})", t, re.I):
                out.append(".+")
            else:
                out.append(re.escape(t))
    rx = "".join(out)
    if not re.search(r"\\\.(pdf|docx|pptx|xlsx|zip)$", rx, re.I):
        rx += r"\.[a-z0-9]+"
    return "^" + rx + "$"


def margin_values(frag):
    """'левое 30 мм, правое 15 мм, верхнее и нижнее 20 мм' -> {'left': 30, ...}; one value -> all sides."""
    side_words = [("left", r"лев\w*|лів\w*|\bleft\b"), ("right", r"прав\w*|\bright\b"),
                  ("top", r"верх\w*|\btop\b"), ("bottom", r"ниж\w*|низ\w*|\bbottom\b")]
    tokens = []
    for side, pat in side_words:
        tokens += [(m.start(), "side", side) for m in re.finditer(pat, frag.lower())]
    for m in re.finditer(r"(\d+(?:[.,]\d+)?)\s*(мм|mm|см|cm|дюйм\w*|inch\w*|in\b|\")", frag.lower()):
        v = to_number(m.group(1))
        unit = m.group(2)
        v = v * 10 if unit in ("см", "cm") else v * 25.4 if unit.startswith(("дюйм", "inch", "in", '"')) else v
        tokens.append((m.start(), "value", v))
    tokens.sort()
    result, pending = {}, []
    if tokens and tokens[0][1] == "value":
        # "2.5 cm top/bottom, 3 cm left": sides come after their value
        for i, (_, kind, val) in enumerate(tokens):
            if kind != "value":
                continue
            sides = []
            for _, k2, v2 in tokens[i + 1:]:
                if k2 != "side":
                    break
                sides.append(v2)
            for s in sides or (["left", "right", "top", "bottom"] if not result else []):
                result.setdefault(s, round(val, 1))
        return result
    for _, kind, val in tokens:
        if kind == "side":
            pending.append(val)
        else:
            for s in pending or (["left", "right", "top", "bottom"] if not result else []):
                result.setdefault(s, round(val, 1))
            pending = []
    return result


class Contract:
    def __init__(self, primary):
        self.items = []
        self.primary = primary

    def add(self, frag, rtype, target=None, **params):
        item = {"type": rtype, "target": target, "source": frag}
        item.update({k: v for k, v in params.items() if v is not None})
        key = (rtype, target, tuple(sorted((k, str(v)) for k, v in params.items())),
               frag if rtype == "unverified" else None)  # every unclear sentence is listed
        if any(i.get("_key") == key for i in self.items):
            return
        item["_key"] = key
        self.items.append(item)


def parse_fragment(frag, c):
    low = norm(frag).lower()
    qfrag = numberize(frag)
    exts = exts_in(frag)
    doc_exts = [e for e in exts if e != "zip"]
    target = doc_exts[0] if len(doc_exts) == 1 else (c.primary if not doc_exts else None)
    before = len(c.items)

    # Delivery format
    if exts and re.search(r"формат|format|файл|\bfile|сда|здай|здат|отправ|надіш|надсил|пода|загруз|завантаж|"
                          r"upload|submit|send|прикреп|прилож|презентац|presentation|таблиц|spreadsheet|"
                          r"архив|архів|archive|документ|document|deck|save|сохран|збереж|\bas\b|\bв\b|\bу\b",
                          low):
        if re.search(r"только|лише|тільки|\bonly\b|exclusively|исключительно|виключно|другие форматы не|"
                     r"інші формати не|other formats", low):
            c.add(frag, "only_formats", None, exts=sorted(set(exts)))
        for e in exts:
            # "convert from Word to PDF" asks for a PDF, not for a Word file
            source_only = re.search(r"(?:из|з|from|конверт\w*|convert\w*)\s+(?:\w+\s+)?(?:" + dict(EXT_PATTERNS)[e]
                                    + ")", low)
            if not source_only:
                c.add(frag, "file_required", e)

    # File name
    if re.search(r"назов|назвать|назван\w* файл|имя файла|имени файла|ім'?я файлу|назв\w* файл|file ?name|"
                 r"name (?:the|your) file|\bnamed\b|называться|називатися|назвіть|save (?:it|the file|your file|"
                 r"your work)? ?as|сохрани\w* (?:его |файл )?как|збереж\w* (?:його |файл )?як", low):
        cands = quoted(frag) or re.findall(r"[\w\-<>\[\]{}]+\.(?:pdf|docx|pptx|xlsx|zip)", frag, re.I)
        cands = cands or re.findall(r"[\w<>\[\]{}]+(?:[_\-][\w<>\[\]{}]+)+", frag)
        if cands:
            pat = cands[0]
            ext = re.search(r"\.(pdf|docx|pptx|xlsx|zip)$", pat, re.I)
            c.add(frag, "filename", ext.group(1).lower() if ext else target, pattern=pat, regex=name_regex(pat))

    # Size limit
    q = quantity(qfrag, U_MB, default="max")
    if q:
        size_target = "zip" if "zip" in exts and not doc_exts else (doc_exts[0] if len(doc_exts) == 1 else None)
        c.add(frag, "max_size_mb", size_target, max=q[1] if q[1] is not None else q[0])

    # Slides / pages / words / images / sheets
    q = quantity(qfrag, U_SLIDES)
    if q:
        c.add(frag, "slides", "pptx", min=q[0], max=q[1])
    sheet_context = bool(target == "xlsx" or "xlsx" in exts or re.search(r"таблиц\w*|spreadsheet|workbook", low)
                         or (quoted(frag) and re.search(U_SHEETS, low)))
    q = quantity(qfrag, U_PAGES) or (None if sheet_context else quantity(qfrag, r"\bлист(?:ов|а)?\b"))
    if q and not re.search(U_SLIDES, low):
        c.add(frag, "slides" if target == "pptx" else "pages", target, min=q[0], max=q[1])
    if not re.search(r"ключев\w* слов|ключов\w* слів|keywords?", low):
        q = quantity(qfrag, U_WORDS, default="about")
        if q:
            c.add(frag, "words", target, min=q[0], max=q[1])
    q = quantity(qfrag, U_IMAGES, default="min")
    if q:
        c.add(frag, "images", target, min=q[0], max=q[1])
    if re.search(U_SHEETS, low) and sheet_context:
        names = quoted(frag) or (listed(frag) if re.search(r"(?:лист\w*|аркуш\w*|sheets?|вкладк\w*|tabs?)\s*:",
                                                           low) else [])
        q = quantity(qfrag, U_SHEETS, default="min")
        c.add(frag, "sheets", "xlsx", names=names or None, min=q[0] if q and not names else None)

    # Sections and required phrases
    section_cue = re.search(r"раздел\w*|розділ\w*|section\w*|заголов\w*|heading\w*|\bглав\w*|chapter\w*|"
                            r"структур\w*|structure|\bчастин\w*|\bчаст[ьи]\b|\bparts?\b|пункт\w*", low)
    contains_cue = re.search(r"содерж\w*|включ\w*|указ\w*|укаж\w*|вкаж\w*|наличи\w*|містит\w*|вказ\w*|"
                             r"зазнач\w*|contain\w*|"
                             r"includ\w*|mention\w*|\bstate\b|присутств\w*|присутн\w*|appear\w*|должн\w* быть|"
                             r"має бути|must (?:have|be)", low)
    if section_cue:
        items = quoted(frag) or listed(frag)
        if not items:
            m = re.search(r"(?:include|includes|contain|contains|have|содерж\w*|включ\w*|містит\w*|включат\w*)\s+"
                          r"(.+?)\s+(?:sections?|chapters?|розділ\w*|раздел\w*)\b", frag, re.I)
            if m:
                items = [re.sub(r"^(?:an?|the)\s+", "", x.strip(), flags=re.I)
                         for x in re.split(r",|\s+(?:and|и|і|та)\s+", m.group(1)) if x.strip()]
        if items:
            c.add(frag, "sections", target, items=items)
    elif contains_cue and quoted(frag):
        c.add(frag, "contains", target, phrases=quoted(frag))

    # Typography and page setup
    fonts = [f for f in KNOWN_FONTS if re.search(r"\b" + re.escape(f.lower()) + r"\b", low)]
    if not fonts and re.search(r"\btnr\b", low):
        fonts = ["Times New Roman"]
    if fonts and not re.search(r"\barial\b.*\btimes\b.*\bили\b", low):
        c.add(frag, "font", target, name=fonts[0])
    fs = re.search(r"(\d+(?:[.,]\d+)?)\s*(?:пт\b|pt\b|пунктов|пункт\w*|points?\b)", low) or \
        re.search(r"(?:кегл\w*|размер\w* шрифта|розмір\w* шрифту|font size|font-size|шрифт\w*[^\d,.;]{0,25})\D{0,12}?"
                  r"(?<![a-zа-я])(\d{1,2}(?:[.,]5)?)(?![\d.,]*\s*(?:мм|см|mm|cm|%|слов|стр|сторін|page|слайд|slide))",
                  low)
    fs = fs or re.search(r"(?:" + "|".join(re.escape(f.lower()) for f in KNOWN_FONTS) + r"|\btnr)\s*,?\s*"
                         r"(\d{1,2}(?:[.,]5)?)(?![\d.,]*\s*(?:мм|см|mm|cm|%))\b", low)
    if fs:
        c.add(frag, "font_size", target, value=to_number(fs.group(1)))
    if re.search(r"\bпол[ея]\b|\bполей\b|відступ\w* від кра\w*|\bберег\w*|\bполя\w*|margins?", low) \
            and not re.search(r"абзац", low):
        mv = margin_values(frag)
        if mv:
            c.add(frag, "margins", target, **{k: mv[k] for k in mv})
    paper = re.search(r"(?<![a-zа-я0-9])[aа]\s?([345])(?![0-9])", low)
    orient = ("landscape" if re.search(r"альбомн|landscape|горизонтальн", low)
              else "portrait" if re.search(r"книжн|книжк|portrait|вертикальн", low) else None)
    if paper or orient:
        c.add(frag, "page_format", target if target != "pptx" else None,
              paper=f"A{paper.group(1)}" if paper else None, orientation=orient)

    # Hygiene
    negation = r"без\b|не долж|не повин|не допуска|не допуска|удал|видал|убер|прибер|remove|delete|\bno\b|without|" \
               r"resolve|не оставля|не залиша|не залиш|clean|чист|прийнят|принят|accept|отключ|вимкн"
    if re.search(r"комментари\w*|коментар\w*|примечани\w*|приміт\w*|comments?", low) and re.search(negation, low):
        c.add(frag, "no_comments", target)
    if re.search(r"исправлени\w*|правк\w*|рецензир\w*|track(?:ed)? changes|revisions?|виправлен\w*|"
                 r"режим\w* (?:исправлений|правок|виправлень)|отслеживан\w*|відстеж\w*", low) \
            and re.search(negation, low):
        c.add(frag, "no_tracked_changes", target)
    if re.search(r"заглуш\w*|lorem|placeholder\w*|шаблонн\w* текст|незаполненн\w*|незаповнен\w*|\btodo\b|"
                 r"template text|рыб\w*|пуст\w* пол|порожн\w* пол|dummy text|filler text", low):
        c.add(frag, "no_placeholders", target)
    if re.search(r"(?:ошиб\w*|помил\w*) (?:в|у) формул|#ref|#div|#знач|#дел|#ссыл|#имя|#н/д|#value|#name|#n/a|"
                 r"formula errors|errors in (?:the )?formulas|"
                 r"формул\w*[^.]{0,20}без (?:ошиб|помил)|без (?:ошиб|помил)\w*[^.]{0,20}формул|"
                 r"формул\w*[^.]{0,30}(?:коррект|корект|correct)|(?:ошиб|помил)\w* (?:вычислен|обчислен)|"
                 r"formulas?[^.]{0,30}(?:no errors|without errors|error[- ]free)|"
                 r"(?:no|without) (?:#\w+ )?errors?[^.]{0,20}formulas?", low):
        c.add(frag, "no_formula_errors", "xlsx")
    if re.search(r"лишн\w*|служебн\w*|зайв\w*|службов\w*|extra files|junk|system files|__macosx|ds_store|"
                 r"скрыт\w* файл|прихован\w* файл|hidden files|мусор|сміття", low):
        c.add(frag, "zip_clean", "zip")

    produced = len(c.items) > before
    understood_nothing = not produced and not CONTEXT.match(frag) and not HEADING.match(frag)
    if understood_nothing or SUBJECTIVE.search(frag):
        c.add(frag, "unverified", None, reason="not an objective file property the checker understands")


def extract(text):
    """Return the contract: list of requirement dicts with an id, type, target and source sentence."""
    all_exts = [e for e in exts_in(text) if e != "zip"]
    primary = all_exts[0] if len(set(all_exts)) == 1 else None
    c = Contract(primary)
    for frag in split_fragments(text):
        parse_fragment(frag, c)
    out = []
    for n, item in enumerate(c.items, 1):
        item.pop("_key", None)
        out.append({"id": f"R{n}", **item})
    return out
