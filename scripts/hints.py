"""One short "how to fix it" line per result, in the language of the assignment.

Hints only say what to do. They never decide the status: a result is pass, fail or unverified before
it gets here, and an unverified result only gets advice on how a person can check it.
"""
import re

EXAMPLE_NAME = {"en": "Smith", "ru": "Иванов", "uk": "Шевченко"}

HINTS = {
    "en": {
        "more": {"pages": "Add {n} more page|Add {n} more pages", "slides": "Add {n} more slide|Add {n} more slides",
                 "words": "Add about {n} more word|Add about {n} more words",
                 "images": "Add {n} more picture or chart|Add {n} more pictures or charts"},
        "less": {"pages": "Cut {n} page|Cut {n} pages", "slides": "Remove {n} slide|Remove {n} slides",
                 "words": "Cut about {n} word|Cut about {n} words",
                 "images": "Remove {n} picture|Remove {n} pictures"},
        "sections": "Add these headings, spelled as in the assignment: {items}",
        "contains": "Add the missing text exactly as written in the assignment",
        "no_comments": "In Word: Review → Delete → Delete All Comments in Document, then save",
        "no_comments_other": "Delete the comments and save the file again",
        "no_tracked_changes": "In Word: Review → Accept → Accept All Changes, then save",
        "no_placeholders": "Replace the placeholder text with real content",
        "no_formula_errors": "Open the cell shown and fix its formula (often a division by zero or a deleted reference)",
        "filename": "Rename the file, for example «{example}»",
        "font": "Select all text (Ctrl+A) and set the font to {name}",
        "font_size": "Select all text (Ctrl+A) and set the size to {value} pt",
        "margins": "In Word: Layout → Margins → Custom Margins",
        "page_format": "In Word: Layout → Size and Layout → Orientation",
        "file_required": "Add a .{target} file to what you hand in",
        "only_formats": "Convert or remove the files in other formats",
        "max_size_mb": "Make the file smaller: compress pictures (File → Compress Pictures) or remove large media",
        "zip_clean": "Pack the archive again without these files",
        "sheets": "Add or rename the sheets so they match the assignment",
        "readable": "Open the file in its app, save it again and check that it opens",
        "u_deadline": "Check the deadline on the course page or in the original email",
        "u_original": "Run the plagiarism checker your school or client accepts",
        "u_sources": "Count the entries in your reference list",
        "u_style": "Compare your citations with the required style guide",
        "u_spacing": "Check line spacing: Home → Line and Paragraph Spacing",
    },
    "uk": {
        "more": {"pages": "Додайте сторінок: {n}", "slides": "Додайте слайдів: {n}",
                 "words": "Додайте приблизно слів: {n}", "images": "Додайте зображень або діаграм: {n}"},
        "less": {"pages": "Скоротіть сторінок: {n}", "slides": "Видаліть зайві слайди: {n}",
                 "words": "Скоротіть приблизно слів: {n}", "images": "Приберіть зайві зображення: {n}"},
        "sections": "Додайте заголовки так, як вони написані в завданні: {items}",
        "contains": "Додайте текст, якого бракує, точно як у завданні",
        "no_comments": "У Word: Рецензування → Видалити → Видалити всі примітки в документі, потім збережіть",
        "no_comments_other": "Видаліть коментарі й збережіть файл ще раз",
        "no_tracked_changes": "У Word: Рецензування → Прийняти → Прийняти всі зміни, потім збережіть",
        "no_placeholders": "Замініть текст-заглушку справжнім текстом",
        "no_formula_errors": "Відкрийте вказану клітинку й виправте формулу (часто це ділення на нуль або видалене посилання)",
        "filename": "Перейменуйте файл, наприклад «{example}»",
        "font": "Виділіть увесь текст (Ctrl+A) і поставте шрифт {name}",
        "font_size": "Виділіть увесь текст (Ctrl+A) і поставте розмір {value} пт",
        "margins": "У Word: Макет → Поля → Настроювані поля",
        "page_format": "У Word: Макет → Розмір і Орієнтація",
        "file_required": "Додайте файл .{target} до того, що здаєте",
        "only_formats": "Перетворіть або приберіть файли інших форматів",
        "max_size_mb": "Зменште файл: стисніть зображення (Файл → Стиснути зображення) або приберіть велике відео",
        "zip_clean": "Запакуйте архів наново без цих файлів",
        "sheets": "Додайте або перейменуйте аркуші, як у завданні",
        "readable": "Відкрийте файл у його програмі, збережіть ще раз і перевірте, що він відкривається",
        "u_deadline": "Перевірте термін на сторінці курсу або в листі із завданням",
        "u_original": "Перевірте текст сервісом антиплагіату, який приймає викладач або клієнт",
        "u_sources": "Порахуйте джерела у списку літератури",
        "u_style": "Звірте оформлення посилань із потрібним стандартом",
        "u_spacing": "Перевірте інтервал: Основне → Інтервал між рядками",
    },
    "ru": {
        "more": {"pages": "Добавьте страниц: {n}", "slides": "Добавьте слайдов: {n}",
                 "words": "Добавьте примерно слов: {n}", "images": "Добавьте изображений или диаграмм: {n}"},
        "less": {"pages": "Сократите страниц: {n}", "slides": "Удалите лишние слайды: {n}",
                 "words": "Сократите примерно слов: {n}", "images": "Уберите лишние изображения: {n}"},
        "sections": "Добавьте заголовки так, как они написаны в задании: {items}",
        "contains": "Добавьте недостающий текст точно как в задании",
        "no_comments": "В Word: Рецензирование → Удалить → Удалить все примечания в документе, затем сохраните",
        "no_comments_other": "Удалите комментарии и сохраните файл заново",
        "no_tracked_changes": "В Word: Рецензирование → Принять → Принять все исправления, затем сохраните",
        "no_placeholders": "Замените текст-заглушку настоящим текстом",
        "no_formula_errors": "Откройте указанную ячейку и исправьте формулу (часто это деление на ноль или удалённая ссылка)",
        "filename": "Переименуйте файл, например «{example}»",
        "font": "Выделите весь текст (Ctrl+A) и поставьте шрифт {name}",
        "font_size": "Выделите весь текст (Ctrl+A) и поставьте размер {value} пт",
        "margins": "В Word: Макет → Поля → Настраиваемые поля",
        "page_format": "В Word: Макет → Размер и Ориентация",
        "file_required": "Добавьте файл .{target} к тому, что сдаёте",
        "only_formats": "Преобразуйте или уберите файлы других форматов",
        "max_size_mb": "Уменьшите файл: сожмите изображения (Файл → Сжать рисунки) или уберите большое видео",
        "zip_clean": "Запакуйте архив заново без этих файлов",
        "sheets": "Добавьте или переименуйте листы, как в задании",
        "readable": "Откройте файл в его программе, сохраните заново и проверьте, что он открывается",
        "u_deadline": "Проверьте срок на странице курса или в письме с заданием",
        "u_original": "Проверьте текст сервисом антиплагиата, который принимает преподаватель или клиент",
        "u_sources": "Посчитайте источники в списке литературы",
        "u_style": "Сверьте оформление ссылок с нужным стандартом",
        "u_spacing": "Проверьте интервал: Главная → Междустрочный интервал",
    },
}

# what an unverified sentence is about, so the advice can be specific
UNVERIFIED_TOPICS = [
    ("u_deadline", r"deadline|due\b|submit by|until|срок|дедлайн|до \d|термін|здати до|\d{1,2}[:.]\d{2}"),
    ("u_original", r"original|plagiar|unique|оригинальн|уникальн|плагиат|оригінальн|унікальн|плагіат"),
    ("u_sources", r"sources|references|bibliograph|источник|литератур|джерел|літератур"),
    ("u_style", r"\bAPA\b|\bMLA\b|harvard|chicago|citation|ГОСТ|ДСТУ|цитирован|цитуванн|оформлен"),
    ("u_spacing", r"spacing|интервал|інтервал"),
]

NUMBER = re.compile(r": (\d[\d,\s]*)\s")


def _plural(template, n):
    if "|" not in template:
        return template
    one, many = template.split("|")
    return one if n == 1 else many


def _count_hint(r, H):
    for e in r.get("evidence", []):
        m = NUMBER.search(e)
        if not m:
            continue
        got = int(re.sub(r"[,\s]", "", m.group(1)))
        lo, hi = r.get("min"), r.get("max")
        if lo is not None and got < lo:
            n = int(lo - got + 0.999)
            return _plural(H["more"][r["type"]], n).format(n=n)
        if hi is not None and got > hi:
            n = int(got - hi + 0.999)
            return _plural(H["less"][r["type"]], n).format(n=n)
    return None


def hint(r, lang="en"):
    """Advice for one result, or None. Passing results need none."""
    H = HINTS.get(lang, HINTS["en"])
    t, status = r.get("type"), r.get("status")
    if status == "pass":
        return None
    if status == "unverified":
        text = r.get("source") or ""
        for key, pattern in UNVERIFIED_TOPICS:
            if re.search(pattern, text, re.I):
                return H[key]
        return None
    if t in ("pages", "slides", "words", "images"):
        return _count_hint(r, H)
    if t in ("sections", "contains"):
        missing = [m for e in r.get("evidence", []) for m in re.findall(r"«([^»]+)»", e)]
        if t == "sections" and missing:
            return H["sections"].format(items=", ".join(f"«{m}»" for m in dict.fromkeys(missing)))
        return H["contains"] if t == "contains" else None
    if t == "no_comments":
        on_word = any(".docx" in e.lower() for e in r.get("evidence", []))
        return H["no_comments" if on_word else "no_comments_other"]
    if t == "filename":
        example = re.sub(r"<[^>]+>", EXAMPLE_NAME.get(lang, "Smith"), r.get("pattern") or "")
        return H["filename"].format(example=example) if example else None
    if t == "font":
        return H["font"].format(name=r.get("name", ""))
    if t == "font_size":
        return H["font_size"].format(value=f"{r.get('value', 0):g}")
    if t == "file_required":
        return H["file_required"].format(target=r.get("target") or "")
    return H.get(t)
