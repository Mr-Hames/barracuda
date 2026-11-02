"""Build the benchmark: N assignments (RU/UK/EN) with file sets and labelled violations.

  python bench/generate.py --out bench/cases --n 50 --seed 7

Each case folder: task.txt, files/..., gold.json. gold.json lists every requirement sentence with
its type, target and the expected status: "fail" (planted violation), "pass", or "unverified"
(subjective or not a file property: it must never come out as "pass").
Needs: pymupdf, python-docx, python-pptx, openpyxl, Pillow; Windows fonts for PDFs.
"""
import argparse
import json
import os
import random
import re
import shutil
import sys
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from readers import count_words  # noqa: E402

FONT_FILES = {"Times New Roman": r"C:\Windows\Fonts\times.ttf", "Arial": r"C:\Windows\Fonts\arial.ttf",
              "Calibri": r"C:\Windows\Fonts\calibri.ttf"}
VOCAB = {
    "ru": "анализ рынок данные компания стратегия клиент продукт результат исследование метод развитие цена "
          "спрос услуга модель процесс система оценка качество решение проект команда отчет показатель рост".split(),
    "uk": "аналіз ринок дані компанія стратегія клієнт продукт результат дослідження метод розвиток ціна попит "
          "послуга модель процес система оцінка якість рішення проєкт команда звіт показник зростання".split(),
    "en": "analysis market data company strategy customer product result research method growth price demand "
          "service model process system evaluation quality decision project team report indicator trend".split(),
}
SECTIONS = {
    "ru": ["Введение", "Анализ рынка", "Методология", "Результаты", "Заключение", "Список литературы"],
    "uk": ["Вступ", "Аналіз ринку", "Методологія", "Результати", "Висновки", "Список літератури"],
    "en": ["Introduction", "Market Analysis", "Methodology", "Results", "Conclusion", "References"],
}
PHRASES = {"ru": ["Цифровой маркетинг", "Вывод", "Целевая аудитория"],
           "uk": ["Цифровий маркетинг", "Висновок", "Цільова аудиторія"],
           "en": ["Digital marketing", "Key findings", "Target audience"]}
SHEETS = {"ru": ["Данные", "Итоги", "Расчеты"], "uk": ["Дані", "Підсумки", "Розрахунки"],
          "en": ["Data", "Summary", "Calculations"]}
SUBJECTIVE = {
    "ru": ["Текст должен быть грамотным и логичным.", "Работа должна быть оригинальной, проверка на плагиат обязательна.",
           "Срок сдачи — 20 мая.", "Используйте не менее 5 источников.", "Оформление должно быть аккуратным.",
           "Выводы должны быть аргументированными."],
    "uk": ["Текст має бути грамотним і логічним.", "Робота має бути оригінальною, перевірка на плагіат обов'язкова.",
           "Термін здачі — 20 травня.", "Використайте не менше 5 джерел.", "Оформлення має бути охайним.",
           "Висновки мають бути аргументованими."],
    "en": ["Write in a clear, professional tone.", "The work must be original; it will be checked for plagiarism.",
           "Deadline: May 20.", "Cite at least 5 sources.", "The design should look polished.",
           "Conclusions must be well argued."],
}
CONTEXT = {"ru": ["Дисциплина: Маркетинг.", "Тема: продвижение малого бизнеса."],
           "uk": ["Дисципліна: Маркетинг.", "Тема: просування малого бізнесу."],
           "en": ["Course: Marketing 101.", "Topic: promoting a small business."]}
NOUN = {  # how each file type is called in the assignment
    "ru": {"pdf": "PDF", "docx": "документ Word (DOCX)", "pptx": "презентацию PowerPoint (PPTX)", "xlsx": "файл Excel (XLSX)"},
    "uk": {"pdf": "PDF", "docx": "документ Word (DOCX)", "pptx": "презентацію PowerPoint (PPTX)", "xlsx": "файл Excel (XLSX)"},
    "en": {"pdf": "a PDF", "docx": "a Word document (DOCX)", "pptx": "a PowerPoint deck (PPTX)", "xlsx": "an Excel file (XLSX)"},
}
POOL = {
    "docx": ["pages", "words", "sections", "font", "font_size", "margins", "page_format", "images", "no_comments",
             "no_tracked_changes", "no_placeholders", "filename", "max_size_mb", "contains"],
    "pdf": ["pages", "words", "sections", "font", "font_size", "page_format", "images", "no_comments",
            "no_placeholders", "filename", "max_size_mb", "contains"],
    "pptx": ["slides", "images", "sections", "no_placeholders", "filename", "max_size_mb", "contains", "words"],
    "xlsx": ["sheets", "no_formula_errors", "contains", "filename", "max_size_mb"],
}


def pick(rnd, options):
    return options[rnd.randrange(len(options))]


# ---------- assignment sentences ----------

def sentence(rnd, lang, req, ext):
    t, p = req["type"], req
    n = NOUN[lang][ext]
    q = lambda xs: ", ".join(f"«{x}»" if lang != "en" else f'"{x}"' for x in xs)  # noqa: E731
    lst = lambda xs: ", ".join(xs[:-1]) + (" и " if lang == "ru" else " і " if lang == "uk" else " and ") + xs[-1]  # noqa: E731
    if t == "file_required":
        return pick(rnd, {"ru": [f"Сдайте работу как {n}.", f"Работу нужно отправить в формате {ext.upper()}."],
                          "uk": [f"Здайте роботу як {n}.", f"Роботу потрібно надіслати у форматі {ext.upper()}."],
                          "en": [f"Submit your work as {n}.", f"The deliverable must be in {ext.upper()} format."]}[lang])
    if t == "pages":
        lo, hi = p.get("min"), p.get("max")
        if lo and hi:
            return pick(rnd, {"ru": [f"Объем — от {lo} до {hi} страниц.", f"Объем работы {lo}–{hi} страниц."],
                              "uk": [f"Обсяг — від {lo} до {hi} сторінок.", f"Обсяг роботи {lo}–{hi} сторінок."],
                              "en": [f"Length: {lo}–{hi} pages.", f"The paper should be between {lo} and {hi} pages."]}[lang])
        return pick(rnd, {"ru": [f"Объем не менее {lo} страниц."], "uk": [f"Обсяг не менше {lo} сторінок."],
                          "en": [f"At least {lo} pages are required."]}[lang])
    if t == "slides":
        lo, hi = p.get("min"), p.get("max")
        if lo and hi:
            return pick(rnd, {"ru": [f"Презентация должна содержать от {lo} до {hi} слайдов."],
                              "uk": [f"Презентація має містити від {lo} до {hi} слайдів."],
                              "en": [f"The deck must have {lo}–{hi} slides."]}[lang])
        return pick(rnd, {"ru": [f"Не более {hi} слайдов."], "uk": [f"Не більше {hi} слайдів."],
                          "en": [f"No more than {hi} slides."]}[lang])
    if t == "words":
        lo, hi = p.get("min"), p.get("max")
        if lo and hi:
            return pick(rnd, {"ru": [f"Объем текста: от {lo} до {hi} слов."], "uk": [f"Обсяг тексту: від {lo} до {hi} слів."],
                              "en": [f"Word count: {lo}–{hi} words."]}[lang])
        if lo:
            return pick(rnd, {"ru": [f"Текст — не менее {lo} слов."], "uk": [f"Текст — щонайменше {lo} слів."],
                              "en": [f"Write at least {lo} words."]}[lang])
        return pick(rnd, {"ru": [f"Не более {hi} слов."], "uk": [f"Не більше {hi} слів."],
                          "en": [f"Keep it under {hi + 1} words."]}[lang])
    if t == "sections":
        items = p["items"]
        return pick(rnd, {"ru": [f"Работа должна содержать разделы: {lst(items)}.", f"Обязательные разделы: {q(items)}."],
                          "uk": [f"Робота має містити розділи: {lst(items)}.", f"Обов'язкові розділи: {q(items)}."],
                          "en": [f"Include the following sections: {lst(items)}.", f"Required sections: {q(items)}."]}[lang])
    if t == "contains":
        return pick(rnd, {"ru": [f"В тексте обязательно укажите {q(p['phrases'])}."],
                          "uk": [f"У тексті обов'язково зазначте {q(p['phrases'])}."],
                          "en": [f"The text must mention {q(p['phrases'])}."]}[lang])
    if t == "font":
        return pick(rnd, {"ru": [f"Шрифт — {p['name']}.", f"Используйте шрифт {p['name']}."],
                          "uk": [f"Шрифт — {p['name']}.", f"Використовуйте шрифт {p['name']}."],
                          "en": [f"Use {p['name']} font.", f"Font: {p['name']}."]}[lang])
    if t == "font_size":
        return pick(rnd, {"ru": [f"Размер шрифта основного текста — {p['value']} пт.", f"Кегль {p['value']}."],
                          "uk": [f"Розмір шрифту основного тексту — {p['value']} пт.", f"Кегль {p['value']}."],
                          "en": [f"Body text size {p['value']} pt.", f"Font size: {p['value']} pt."]}[lang])
    if t == "margins":
        m = p
        if len({m["left"], m["right"], m["top"], m["bottom"]}) == 1:
            v = m["left"]
            cm = f"{v / 10:g}".replace(".", "," if lang != "en" else ".")  # 25 mm -> "2,5 см", not "2 см"
            return pick(rnd, {"ru": [f"Поля со всех сторон — {v} мм.", f"Поля {cm} см."],
                              "uk": [f"Поля з усіх боків — {v} мм.", f"Поля {cm} см."],
                              "en": [f"Margins: {v} mm on all sides.", f"Use {cm} cm margins."]}[lang])
        return {"ru": f"Поля: левое {m['left']} мм, правое {m['right']} мм, верхнее и нижнее {m['top']} мм.",
                "uk": f"Поля: ліве {m['left']} мм, праве {m['right']} мм, верхнє і нижнє {m['top']} мм.",
                "en": f"Margins: left {m['left']} mm, right {m['right']} mm, top and bottom {m['top']} mm."}[lang]
    if t == "page_format":
        o = p["orientation"]
        ow = {"ru": {"portrait": "книжная", "landscape": "альбомная"}, "uk": {"portrait": "книжкова", "landscape": "альбомна"},
              "en": {"portrait": "portrait", "landscape": "landscape"}}[lang][o]
        return {"ru": f"Формат листа A4, ориентация {ow}.", "uk": f"Формат аркуша A4, орієнтація {ow}.",
                "en": f"Page size A4, {ow} orientation."}[lang]
    if t == "images":
        return pick(rnd, {"ru": [f"Добавьте не менее {p['min']} иллюстраций.", f"Минимум {p['min']} рисунка."],
                          "uk": [f"Додайте щонайменше {p['min']} ілюстрації.", f"Мінімум {p['min']} малюнки."],
                          "en": [f"Include at least {p['min']} figures.", f"Add a minimum of {p['min']} images."]}[lang])
    if t == "no_comments":
        return pick(rnd, {"ru": ["Удалите все комментарии перед сдачей.", "В файле не должно быть комментариев."],
                          "uk": ["Видаліть усі коментарі перед здачею.", "У файлі не повинно бути коментарів."],
                          "en": ["Remove all comments before submitting.", "No comments may be left in the file."]}[lang])
    if t == "no_tracked_changes":
        return pick(rnd, {"ru": ["Примите все исправления: режим правок должен быть отключен."],
                          "uk": ["Прийміть усі виправлення: режим відстеження змін має бути вимкнений."],
                          "en": ["Accept all tracked changes before submitting."]}[lang])
    if t == "no_placeholders":
        return pick(rnd, {"ru": ["Не оставляйте шаблонный текст и заглушки (Lorem ipsum)."],
                          "uk": ["Не залишайте шаблонний текст і заглушки (Lorem ipsum)."],
                          "en": ["No placeholder text (Lorem ipsum, TODO) may remain."]}[lang])
    if t == "filename":
        return pick(rnd, {"ru": [f"Назовите файл «{p['pattern']}».", f"Имя файла: {p['pattern']}."],
                          "uk": [f"Назвіть файл «{p['pattern']}».", f"Ім'я файлу: {p['pattern']}."],
                          "en": [f'Name the file "{p["pattern"]}".', f"File name: {p['pattern']}."]}[lang])
    if t == "max_size_mb":
        return pick(rnd, {"ru": [f"Размер файла — не более {p['max']} МБ."], "uk": [f"Розмір файлу — не більше {p['max']} МБ."],
                          "en": [f"The file must not exceed {p['max']} MB."]}[lang])
    if t == "sheets":
        return {"ru": f"В таблице должны быть листы {q(p['names'])}.", "uk": f"У таблиці мають бути аркуші {q(p['names'])}.",
                "en": f"The spreadsheet must have sheets {q(p['names'])}."}[lang]
    if t == "no_formula_errors":
        return pick(rnd, {"ru": ["Формулы должны считаться без ошибок (#ДЕЛ/0!, #ССЫЛКА!)."],
                          "uk": ["Формули мають рахуватися без помилок у формулах."],
                          "en": ["Formulas must have no errors such as #REF! or #DIV/0!."]}[lang])
    if t == "zip_clean":
        return {"ru": "Упакуйте всё в один ZIP-архив без лишних служебных файлов (__MACOSX, .DS_Store).",
                "uk": "Запакуйте все в один ZIP-архів без зайвих службових файлів (__MACOSX, .DS_Store).",
                "en": "Pack everything into one ZIP archive with no junk files (__MACOSX, .DS_Store)."}[lang]
    raise ValueError(t)


# ---------- plan ----------

def plan_case(rnd, idx):
    lang = ["ru", "uk", "en"][idx % 3]
    primary = ["docx", "pdf", "pptx", "xlsx", "docx", "pdf", "pptx", "docx", "pdf", "docx"][idx % 10]
    reqs = [{"type": "file_required", "target": primary}]
    pages = rnd.randint(3, 8)
    for t in rnd.sample(POOL[primary], k=min(len(POOL[primary]), rnd.randint(5, 8))):
        r = {"type": t, "target": primary}
        if t == "pages":
            lo = max(2, pages - rnd.randint(0, 2))
            r.update(min=lo, max=lo + rnd.randint(2, 4)) if rnd.random() < 0.7 else r.update(min=lo)
        elif t == "slides":
            lo = rnd.randint(6, 10)
            r.update(min=lo, max=lo + rnd.randint(2, 5)) if rnd.random() < 0.6 else r.update(max=lo + 5)
        elif t == "words":
            base = pages * 180 if primary != "pptx" else 400
            kind = rnd.random()
            if kind < 0.4:
                r.update(min=base - 150, max=base + 300)
            elif kind < 0.75:
                r.update(min=base - 200)
            else:
                r.update(max=base + 400)
        elif t == "sections":
            r["items"] = rnd.sample(SECTIONS[lang], 3)
        elif t == "contains":
            r["phrases"] = [pick(rnd, PHRASES[lang])]
        elif t == "font":
            r["name"] = pick(rnd, list(FONT_FILES))
        elif t == "font_size":
            r["value"] = pick(rnd, [12, 14])
        elif t == "margins":
            if rnd.random() < 0.5:
                v = pick(rnd, [20, 25, 30])
                r.update(left=v, right=v, top=v, bottom=v)
            else:
                r.update(left=30, right=15, top=20, bottom=20)
        elif t == "page_format":
            r.update(paper="A4", orientation=pick(rnd, ["portrait", "portrait", "landscape"]))
        elif t == "images":
            r["min"] = rnd.randint(2, 4)
        elif t == "filename":
            course = {"ru": "Маркетинг", "uk": "Маркетинг", "en": "Marketing"}[lang]
            token = {"ru": "Фамилия", "uk": "Прізвище", "en": "<Surname>"}[lang]
            r["pattern"] = f"{token}_{course}_ЛР{rnd.randint(1, 5)}.{primary}" if lang != "en" else \
                f"{token}_{course}_HW{rnd.randint(1, 5)}.{primary}"
        elif t == "max_size_mb":
            r["max"] = pick(rnd, [1, 2, 3])
        elif t == "sheets":
            r["names"] = rnd.sample(SHEETS[lang], 2)
        reqs.append(r)
    if primary in ("pdf", "docx") and rnd.random() < 0.3:
        x = {"type": "file_required", "target": "xlsx"}
        reqs += [x, {"type": "sheets", "target": "xlsx", "names": rnd.sample(SHEETS[lang], 2)},
                 {"type": "no_formula_errors", "target": "xlsx"}]
    packed = rnd.random() < 0.4
    if packed:
        reqs.append({"type": "zip_clean", "target": "zip"})
    # Violations: 1-3 objective requirements, never the base "file_required" except rarely
    violable = [r for r in reqs if r["type"] != "file_required"]
    for r in rnd.sample(violable, k=min(len(violable), rnd.randint(1, 3))):
        r["violate"] = True
    subjective = rnd.sample(SUBJECTIVE[lang], rnd.randint(1, 2))
    return {"lang": lang, "primary": primary, "pages": pages, "reqs": reqs, "packed": packed,
            "subjective": subjective}


# ---------- content ----------

def words_text(rnd, lang, n):
    return " ".join(pick(rnd, VOCAB[lang]) for _ in range(n))


def content_model(rnd, plan):
    """What the files must contain, honouring every requirement except the violated ones."""
    lang, primary = plan["lang"], plan["primary"]
    m = {"lang": lang, "pages": plan["pages"], "font": "Times New Roman", "size": 12, "paper": "A4",
         "orientation": "portrait", "margins": dict(left=25, right=25, top=25, bottom=25), "sections": [],
         "phrases": [], "images": 1, "comments": 0, "tracked": 0, "placeholder": False, "pad_mb": 0,
         "slides": 8, "sheets": [SHEETS[lang][0]], "formula_error": False, "zip_junk": False,
         "words": None, "filename": None, "write_pages_meta": False}
    for r in plan["reqs"]:
        t, v = r["type"], r.get("violate", False)
        if t == "pages":
            lo, hi = r.get("min"), r.get("max")
            ok = rnd.randint(lo, hi) if hi else lo + rnd.randint(0, 2)
            m["pages"] = (lo - 1 if lo > 1 else (hi or lo) + 2) if v else ok
            if primary == "docx":
                m["write_pages_meta"] = True
        elif t == "slides":
            lo, hi = r.get("min"), r.get("max")
            ok = rnd.randint(lo or max(3, hi - 6), hi or lo + 3)
            m["slides"] = ((lo - 2) if lo else hi + 2) if v else ok
        elif t == "words":
            lo, hi = r.get("min"), r.get("max")
            if v:
                m["words"] = int(lo * 0.6) if lo else int(hi * 1.4)
            else:
                a = lo if lo is not None else max(50, hi // 2)
                b = hi if hi is not None else lo + 400
                m["words"] = (a + b) // 2
        elif t == "sections":
            m["sections"] = list(r["items"][:-1] if v else r["items"])
        elif t == "contains":
            m["phrases"] = [] if v else list(r["phrases"])
        elif t == "font":
            m["font"] = pick(rnd, [f for f in FONT_FILES if f != r["name"]]) if v else r["name"]
        elif t == "font_size":
            m["size"] = (16 if r["value"] == 14 else 10) if v else r["value"]
        elif t == "margins":
            mm = {k: r[k] for k in ("left", "right", "top", "bottom")}
            if v:
                side = pick(rnd, list(mm))
                mm[side] += 10
            m["margins"] = mm
        elif t == "page_format":
            want = r["orientation"]
            if v:
                if rnd.random() < 0.5:
                    m["paper"], m["orientation"] = "Letter", want
                else:
                    m["orientation"] = "landscape" if want == "portrait" else "portrait"
            else:
                m["orientation"] = want
        elif t == "images":
            m["images"] = r["min"] - 1 if v else r["min"] + rnd.randint(0, 1)
        elif t == "no_comments":
            m["comments"] = 2 if v else 0
        elif t == "no_tracked_changes":
            m["tracked"] = 1 if v else 0
        elif t == "no_placeholders":
            m["placeholder"] = v
        elif t == "filename":
            m["filename"] = None if v else realise_name(r["pattern"], lang)
        elif t == "max_size_mb":
            m["pad_mb"] = r["max"] + 0.6 if v else 0
        elif t == "sheets":
            m["sheets"] = list(r["names"][:-1] + [SHEETS[lang][2] if r["names"][-1] != SHEETS[lang][2] else "Sheet9"]) \
                if v else list(r["names"])
        elif t == "no_formula_errors":
            m["formula_error"] = v
        elif t == "zip_clean":
            m["zip_junk"] = v
    if m["words"] is None:
        m["words"] = m["pages"] * 180 if primary in ("docx", "pdf") else 200
    # Pages must be able to hold the words (about 380 words per page at most)
    m["pages"] = max(m["pages"], 1)
    return m


def realise_name(pattern, lang):
    surname = {"ru": "Иванов", "uk": "Шевченко", "en": "Smith"}[lang]
    return re.sub(r"<Surname>|Фамилия|Прізвище", surname, pattern)


def png(rnd, path):
    from PIL import Image
    Image.new("RGB", (120, 80), tuple(rnd.randrange(256) for _ in range(3))).save(path)
    return path


def paragraphs(rnd, m, total_words, chunks):
    """Split total_words into body chunks around the headings and phrases."""
    fixed = sum(count_words(s) for s in m["sections"]) + sum(count_words(p) for p in m["phrases"]) \
        + (5 if m["placeholder"] else 0)
    body = max(chunks * 5, total_words - fixed)
    sizes = [body // chunks + (1 if i < body % chunks else 0) for i in range(chunks)]
    return [words_text(rnd, m["lang"], s) for s in sizes]


def build_pdf(rnd, m, path, tmp):
    import pymupdf

    doc = pymupdf.open()
    w, h = (612, 792) if m["paper"] == "Letter" else (595, 842)
    if m["orientation"] == "landscape":
        w, h = h, w
    pages = m["pages"]
    bodies = paragraphs(rnd, m, m["words"], pages)
    heads = list(m["sections"])
    extra = list(m["phrases"]) + (["Lorem ipsum dolor sit amet"] if m["placeholder"] else [])
    images = m["images"]
    for i in range(pages):
        page = doc.new_page(width=w, height=h)
        page.insert_font(fontname="F0", fontfile=FONT_FILES[m["font"]])
        y = 60
        lines = []
        if heads:
            lines.append(heads.pop(0))
        if extra and i == pages - 1:
            lines += extra
        if i == pages - 1 and heads:
            lines += heads
        rect = pymupdf.Rect(60, y, w - 60, h - 60)
        text = "\n".join(lines + [bodies[i]])
        rc = page.insert_textbox(rect, text, fontname="F0", fontsize=m["size"])
        if rc < 0:  # did not fit: try a bigger box with the same font size
            rc = page.insert_textbox(pymupdf.Rect(30, 30, w - 30, h - 10), text, fontname="F0", fontsize=m["size"])
        if rc < 0:
            raise Overflow("text does not fit on the page")  # build_case re-plans the case
        if images > 0:
            img = png(rnd, os.path.join(tmp, f"i{i}.png"))
            page.insert_image(pymupdf.Rect(w - 160, h - 120, w - 60, h - 60), filename=img)
            images -= 1
    while images > 0:  # more images than pages
        img = png(rnd, os.path.join(tmp, f"j{images}.png"))
        doc[-1].insert_image(pymupdf.Rect(60 + images * 20, h - 120, 160 + images * 20, h - 60), filename=img)
        images -= 1
    for k in range(m["comments"]):
        doc[0].add_text_annot((100 + 30 * k, 100), "please fix")
    if m["pad_mb"]:
        doc.set_metadata({"subject": "".join(rnd.choice("abcdef0123456789") for _ in range(int(m["pad_mb"] * 1024 * 1024)))})
    doc.save(path, garbage=3, deflate=True)
    doc.close()


def build_docx(rnd, m, path, tmp):
    import docx
    from docx.enum.section import WD_ORIENT
    from docx.oxml import parse_xml
    from docx.oxml.ns import nsdecls
    from docx.shared import Mm, Pt

    d = docx.Document()
    st = d.styles["Normal"]
    st.font.name = m["font"]
    st.font.size = Pt(m["size"])
    s = d.sections[0]
    w, h = (215.9, 279.4) if m["paper"] == "Letter" else (210, 297)
    if m["orientation"] == "landscape":
        s.orientation = WD_ORIENT.LANDSCAPE
        w, h = h, w
    s.page_width, s.page_height = Mm(w), Mm(h)
    for k, v in m["margins"].items():
        setattr(s, f"{k}_margin", Mm(v))
    heads = list(m["sections"])
    chunks = max(len(heads), 1) + 1
    bodies = paragraphs(rnd, m, m["words"], chunks)
    first = d.add_paragraph(bodies[0])
    for i, b in enumerate(bodies[1:]):
        if i < len(heads):
            d.add_heading(heads[i], level=1)
        d.add_paragraph(b)
    for ph in m["phrases"]:
        d.add_paragraph(ph)
    if m["placeholder"]:
        d.add_paragraph("Lorem ipsum dolor sit amet")
    for i in range(m["images"]):
        d.add_picture(png(rnd, os.path.join(tmp, f"d{i}.png")), width=Mm(40))
    for _ in range(m["comments"]):
        d.add_comment(first.runs, text="please fix", author="Teacher")
    if m["tracked"]:
        first._p.append(parse_xml(f'<w:ins {nsdecls("w")} w:id="901" w:author="Teacher" '
                                  f'w:date="2026-01-01T00:00:00Z"><w:r><w:t>added</w:t></w:r></w:ins>'))
    d.save(path)
    # Simulate Word's saved statistics when the case is about page count
    if m["write_pages_meta"]:
        from readers import read_docx
        words = read_docx(path)["words"]
        rewrite_zip(path, {"docProps/app.xml": lambda x: re.sub(rb"<Words>\d+</Words>", f"<Words>{words}</Words>".encode(),
                                                                  re.sub(rb"<Pages>\d+</Pages>", f"<Pages>{m['pages']}</Pages>".encode(), x))})
    if m["pad_mb"]:
        add_zip_part(path, "word/media/pad.bin", os.urandom(int(m["pad_mb"] * 1024 * 1024)))


def build_pptx(rnd, m, path, tmp):
    from pptx import Presentation
    from pptx.util import Mm

    prs = Presentation()
    n = m["slides"]
    heads = list(m["sections"])
    bodies = paragraphs(rnd, m, m["words"], n)
    images = m["images"]
    for i in range(n):
        slide = prs.slides.add_slide(prs.slide_layouts[1])
        title = heads.pop(0) if heads else f"{pick(rnd, VOCAB[m['lang']]).capitalize()} {i + 1}"
        slide.shapes.title.text = title
        body = bodies[i]
        if i == n - 1:
            body = " ".join(m["phrases"] + (["Lorem ipsum dolor sit amet"] if m["placeholder"] else []) + [body])
        slide.placeholders[1].text = body
        if images > 0:
            slide.shapes.add_picture(png(rnd, os.path.join(tmp, f"p{i}.png")), Mm(180), Mm(120), width=Mm(50))
            images -= 1
    while images > 0:
        prs.slides[-1].shapes.add_picture(png(rnd, os.path.join(tmp, f"q{images}.png")), Mm(20 + images * 10),
                                          Mm(120), width=Mm(30))
        images -= 1
    prs.save(path)
    if m["pad_mb"]:
        add_zip_part(path, "ppt/media/pad.bin", os.urandom(int(m["pad_mb"] * 1024 * 1024)))


def build_xlsx(rnd, m, path, tmp):
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = m["sheets"][0]
    for name in m["sheets"][1:]:
        wb.create_sheet(name)
    for sheet in wb.worksheets:
        sheet.append([pick(rnd, VOCAB[m["lang"]]).capitalize() for _ in range(4)])
        for _ in range(10):
            sheet.append([rnd.randint(1, 999) for _ in range(4)])
    for i, ph in enumerate(m["phrases"]):
        wb.worksheets[0].cell(row=14 + i, column=1, value=ph)
    if m["placeholder"]:
        wb.worksheets[0]["F2"] = "Lorem ipsum"
    if m["formula_error"]:
        wb.worksheets[-1]["E5"] = "#DIV/0!"
    wb.save(path)
    if m["pad_mb"]:
        add_zip_part(path, "xl/media/pad.bin", os.urandom(int(m["pad_mb"] * 1024 * 1024)))


def rewrite_zip(path, edits):
    tmp = path + ".tmp"
    with zipfile.ZipFile(path) as src, zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename in edits:
                data = edits[item.filename](data)
            dst.writestr(item, data)
    os.replace(tmp, path)


def add_zip_part(path, name, data):
    with zipfile.ZipFile(path, "a", zipfile.ZIP_STORED) as z:
        z.writestr(name, data)


BUILDERS = {"pdf": build_pdf, "docx": build_docx, "pptx": build_pptx, "xlsx": build_xlsx}


class Overflow(Exception):
    pass


def build_case(idx, seed, out):
    """Plans that can't be built (more words than the pages hold) are re-planned with another draw."""
    for attempt in range(20):
        try:
            return _build_case(idx, seed, out, random.Random(seed * 1000 + idx + attempt * 100003))
        except Overflow:
            continue
    raise RuntimeError(f"case {idx + 1}: no buildable plan")


def _build_case(idx, seed, out, rnd):
    plan = plan_case(rnd, idx)
    m = content_model(rnd, plan)
    lang, primary = plan["lang"], plan["primary"]
    folder = os.path.join(out, f"case{idx + 1:02d}")
    shutil.rmtree(folder, ignore_errors=True)
    files_dir = os.path.join(folder, "files")
    tmp = os.path.join(folder, "_tmp")
    os.makedirs(files_dir)
    os.makedirs(tmp)

    generic = {"ru": "работа", "uk": "робота", "en": "assignment"}[lang]
    name = m["filename"] or f"{'final_version' if any(r['type'] == 'filename' for r in plan['reqs']) else generic}.{primary}"
    built = [os.path.join(tmp if plan["packed"] else files_dir, name)]
    BUILDERS[primary](rnd, m, built[0], tmp)
    if any(r["type"] == "file_required" and r["target"] == "xlsx" for r in plan["reqs"]) and primary != "xlsx":
        xm = dict(m, sheets=next(r for r in plan["reqs"] if r["type"] == "sheets" and r["target"] == "xlsx")["names"],
                  phrases=[], placeholder=False, pad_mb=0)
        sheet_req = next(r for r in plan["reqs"] if r["type"] == "sheets" and r["target"] == "xlsx")
        if sheet_req.get("violate"):
            xm["sheets"] = sheet_req["names"][:1] + ["Sheet9"]
        xm["formula_error"] = any(r["type"] == "no_formula_errors" and r.get("violate") for r in plan["reqs"])
        path = os.path.join(tmp if plan["packed"] else files_dir, "data.xlsx")
        build_xlsx(rnd, xm, path, tmp)
        built.append(path)
    if plan["packed"]:
        with zipfile.ZipFile(os.path.join(files_dir, "submission.zip"), "w", zipfile.ZIP_DEFLATED) as z:
            for p in built:
                z.write(p, os.path.basename(p))
            if m["zip_junk"]:
                z.writestr("__MACOSX/._" + os.path.basename(built[0]), b"\x00" * 64)
                z.writestr(".DS_Store", b"\x00" * 64)
    shutil.rmtree(tmp)

    # Assignment text and gold labels
    lines, gold = [], []
    lines.append(pick(rnd, CONTEXT[lang]))
    items = [r for r in plan["reqs"]]
    rnd.shuffle(items)
    items.sort(key=lambda r: r["type"] != "file_required")  # delivery format first, like real briefs
    for r in items:
        ext = r["target"] if r["target"] in NOUN[lang] else primary
        s = sentence(rnd, lang, r, ext)
        lines.append(f"- {s}")
        gold.append({"type": r["type"], "target": r["target"], "sentence": s,
                     "expect": "fail" if r.get("violate") else "pass"})
    for s in plan["subjective"]:
        lines.insert(rnd.randrange(2, len(lines) + 1), f"- {s}")
        gold.append({"type": "unverified", "target": None, "sentence": s, "expect": "unverified"})
    with open(os.path.join(folder, "task.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    with open(os.path.join(folder, "gold.json"), "w", encoding="utf-8") as fh:
        json.dump({"lang": lang, "primary": primary, "packed": plan["packed"], "requirements": gold}, fh,
                  ensure_ascii=False, indent=2)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "cases"))
    p.add_argument("--n", type=int, default=50)
    p.add_argument("--seed", type=int, default=7)
    a = p.parse_args()
    for i in range(a.n):
        build_case(i, a.seed, a.out)
    print(f"{a.n} cases in {a.out}")


if __name__ == "__main__":
    main()
