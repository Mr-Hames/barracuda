"""Real-life phrasings written separately from the benchmark generator, with the expected reading.

  python tests/hard_phrasings.py        # prints the hit rate and every miss

Each case: (text, expected). expected is a list of (type, {param: value}) that must be found, or
"unverified" when the sentence must only produce a manual-check item (and nothing that could pass).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from extract import extract  # noqa: E402

CASES = [
    # --- volume ---
    ("Объем курсовой 25-30 листов печатного текста.", [("pages", {"min": 25, "max": 30})]),
    ("Обсяг: 10–12 с.", [("pages", {"min": 10, "max": 12})]),
    ("Реферат на 10 страниц (не меньше!).", [("pages", {"min": 10})]),
    ("Не больше пяти страниц.", [("pages", {"max": 5})]),
    ("Essay, 1,500-2,000 words.", [("words", {"min": 1500, "max": 2000})]),
    ("Max. 800 words, excluding references.", [("words", {"max": 800})]),
    ("Word limit: 2500.", [("words", {"max": 2500})]),
    ("Презентация на 10-15 слайдов.", [("slides", {"min": 10, "max": 15})]),
    ("Presentation: up to 12 slides incl. title slide.", [("slides", {"max": 12})]),
    ("Не менее 3-х рисунков и 2-х таблиц.", [("images", {"min": 3})]),
    ("Мінімум три ілюстрації.", [("images", {"min": 3})]),
    # --- format and files ---
    ("Работу загрузить в Moodle в формате .docx.", [("file_required", {"target": "docx"})]),
    ("Файл в формате PDF, не Word!", [("file_required", {"target": "pdf"})]),
    ("Send me the deck as PPTX and the data as an .xlsx file.",
     [("file_required", {"target": "pptx"}), ("file_required", {"target": "xlsx"})]),
    ("Все файлы — одним zip-архивом.", [("file_required", {"target": "zip"})]),
    ("Размер вложения до 20 Мб.", [("max_size_mb", {"max": 20})]),
    ("File size limit is 10MB.", [("max_size_mb", {"max": 10})]),
    ("Назва файлу: ПІБ_група_ЛР1.docx", [("filename", {"target": "docx"})]),
    ("Имя файла — Иванов_ИС-21_курсовая.pdf (свою фамилию и группу).", [("filename", {"target": "pdf"})]),
    # --- typography ---
    ("Шрифт Times New Roman 14 кегль, интервал полуторный.", [("font", {"name": "Times New Roman"}),
                                                            ("font_size", {"value": 14})]),
    ("TNR 12 pt, single spacing.", [("font_size", {"value": 12})]),
    ("Arial 11.", [("font", {"name": "Arial"}), ("font_size", {"value": 11})]),
    ("Поля: лев. – 3 см, прав. – 1,5 см, верх. и ниж. – 2 см.",
     [("margins", {"left": 30, "right": 15, "top": 20, "bottom": 20})]),
    ("1 inch margins on all sides.", [("margins", {"left": 25.4})]),
    ("Формат А4, книжная ориентация.", [("page_format", {"paper": "A4", "orientation": "portrait"})]),
    ("Slides in landscape.", [("page_format", {"orientation": "landscape"})]),
    # --- structure ---
    ("Структура: титульный лист, содержание, введение, 2 главы, заключение, список литературы.",
     [("sections", {})]),
    ("Обов'язково: вступ, основна частина, висновки.", [("sections", {})]),
    ("The report must include an Executive Summary and a Conclusion section.", [("sections", {})]),
    ("Укажите в начале номер варианта: «Вариант 7».", [("contains", {})]),
    # --- hygiene ---
    ("Перед сдачей уберите все примечания и исправления.", [("no_comments", {}), ("no_tracked_changes", {})]),
    ("Please make sure track changes are off and all comments resolved.",
     [("no_tracked_changes", {}), ("no_comments", {})]),
    ("В таблице не должно быть #ДЕЛ/0 и прочих ошибок.", [("no_formula_errors", {})]),
    ("Листы в книге: «Исходные данные», «Расчет», «Графики».", [("sheets", {})]),
    ("Архив без мусора (никаких .DS_Store).", [("zip_clean", {})]),
    # --- must stay manual ---
    ("Оформить по ГОСТ 7.32-2017.", "unverified"),
    ("Уникальность текста не ниже 70% по антиплагиату.", "unverified"),
    ("Межстрочный интервал 1,5.", "unverified"),
    ("Абзацный отступ 1,25 см.", "unverified"),
    ("Выравнивание по ширине.", "unverified"),
    ("Нумерация страниц внизу по центру.", "unverified"),
    ("Не менее 20 источников, не старше 5 лет.", "unverified"),
    ("Сдать до 23:59 пятницы.", "unverified"),
    ("Use APA 7th edition for citations.", "unverified"),
    ("Слайды должны быть читабельными, без перегруза текстом.", "unverified"),
    ("Обсяг — 20 000 знаків з пробілами.", "unverified"),
    ("The tone should be formal.", "unverified"),
    ("Каждый слайд — с заголовком.", "unverified"),
    ("Titles in bold.", "unverified"),
    ("Подпишите работу на титульном листе.", "unverified"),
]

CHECKABLE = {"pages", "slides", "words", "images", "font", "font_size", "margins", "page_format", "sections",
             "contains", "no_comments", "no_tracked_changes", "no_placeholders", "no_formula_errors", "sheets",
             "zip_clean", "filename", "max_size_mb", "only_formats"}


def matches(item, params):
    for k, v in params.items():
        got = item.get(k)
        if isinstance(v, (int, float)) and isinstance(got, (int, float)):
            if abs(got - v) > 0.6:
                return False
        elif got != v:
            return False
    return True


def run():
    ok, misses = 0, []
    for text, expected in CASES:
        items = extract(text)
        if expected == "unverified":
            risky = [i for i in items if i["type"] in CHECKABLE]
            listed = any(i["type"] == "unverified" for i in items)
            good = listed and not risky
            why = f"checkable items {[(i['type'], {k: v for k, v in i.items() if k in ('min', 'max', 'value')}) for i in risky]}" \
                if risky else "not listed as manual check"
        else:
            missing = [(t, p) for t, p in expected
                       if not any(i["type"] == t and matches(i, p) for i in items)]
            good = not missing
            why = f"missing {missing}; got {[(i['type'], {k: v for k, v in i.items() if k not in ('id', 'source', 'type')}) for i in items]}"
        if good:
            ok += 1
        else:
            misses.append((text, why))
    return ok, misses


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ok, misses = run()
    for text, why in misses:
        print(f"MISS  {text}\n      {why}")
    print(f"\n{ok}/{len(CASES)} phrasings read correctly ({ok / len(CASES):.0%})")
    sys.exit(0 if ok == len(CASES) else 1)  # CI: any regression is a failure
