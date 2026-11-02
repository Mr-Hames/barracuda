"""Second batch of real-life phrasings, written after the parser was tuned on the first batch.
Its first-run score is the honest "unseen wording" number.

  python tests/hard_phrasings_2.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import hard_phrasings  # noqa: E402

CASES = [
    ("Обсяг роботи — не менше ніж 20 сторінок без урахування додатків.", [("pages", {"min": 20})]),
    ("Курсова: 35–40 стр. основного тексту", [("pages", {"min": 35, "max": 40})]),
    ("Довжина есе — до 1200 слів.", [("words", {"max": 1200})]),
    ("Your essay should be around 2000 words (+/- 10%).", [("words", {"min": 1800, "max": 2200})]),
    ("Minimum length 6 pages, maximum 8.", [("pages", {"min": 6, "max": 8})]),
    ("Слайдов — 8, плюс титульный.", [("slides", {"min": 8})]),
    ("Deck: 5 slides exactly.", [("slides", {"min": 5, "max": 5})]),
    ("Додайте 2–3 діаграми.", [("images", {"min": 2})]),
    ("Include at least two charts.", [("images", {"min": 2})]),
    ("Только pdf, вордовские файлы не принимаю.", [("only_formats", {}), ("file_required", {"target": "pdf"})]),
    ("Attach both the report (PDF) and the source spreadsheet (XLSX).",
     [("file_required", {"target": "pdf"}), ("file_required", {"target": "xlsx"})]),
    ("Загальний розмір архіву — не більше 50 МБ.", [("max_size_mb", {"max": 50})]),
    ("Файл назвать по схеме: Группа_Фамилия_Лаб3.docx", [("filename", {"target": "docx"})]),
    ('Save it as "Smith_Proposal_v2.pdf".', [("filename", {"target": "pdf"})]),
    ("Основной текст — Calibri 11, заголовки — 14.", [("font", {"name": "Calibri"}), ("font_size", {"value": 11})]),
    ("Шрифт: Times New Roman, розмір 14.", [("font", {"name": "Times New Roman"}), ("font_size", {"value": 14})]),
    ("Поля по 2 см с каждой стороны.", [("margins", {"left": 20, "right": 20, "top": 20, "bottom": 20})]),
    ("Margins: 2.5 cm top/bottom, 3 cm left, 1.5 cm right.",
     [("margins", {"top": 25, "bottom": 25, "left": 30, "right": 15})]),
    ("Лист A4, альбомний.", [("page_format", {"paper": "A4", "orientation": "landscape"})]),
    ("Разделы работы: «Введение», «Теория», «Практика», «Выводы».", [("sections", {})]),
    ("Sections required: Abstract; Methods; Results; Discussion.", [("sections", {})]),
    ("В отчете обязательно должна быть фраза «Работа выполнена самостоятельно».", [("contains", {})]),
    ("Удалить все комментарии рецензента.", [("no_comments", {})]),
    ("No tracked changes in the final version.", [("no_tracked_changes", {})]),
    ("Проверьте, чтобы не осталось текста-рыбы.", [("no_placeholders", {})]),
    ("Excel без ошибок #ЗНАЧ! и #ССЫЛКА!.", [("no_formula_errors", {})]),
    ('Workbook must contain a sheet named "Budget".', [("sheets", {})]),
    ("Не кладите в архив скрытые файлы и папку __MACOSX.", [("zip_clean", {})]),
    # must stay manual
    ("Интервал между строками — одинарный.", "unverified"),
    ("Отступ первой строки 1,25.", "unverified"),
    ("Текст выровнять по ширине, переносы включить.", "unverified"),
    ("Page numbers in the footer.", "unverified"),
    ("Обов'язково зміст з номерами сторінок.", "unverified"),
    ("Список литературы — в алфавитном порядке.", "unverified"),
    ("Робота перевіряється на Unicheck.", "unverified"),
    ("Presentation should take 10 minutes.", "unverified"),
    ("Каждый рисунок должен быть подписан.", "unverified"),
    ("Цитаты оформлять в кавычках-ёлочках.", "unverified"),
    ("Charts must have axis labels.", "unverified"),
    ("Не используйте ИИ для написания текста.", "unverified"),
]

if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    hard_phrasings.CASES[:] = CASES
    ok, misses = hard_phrasings.run()
    for text, why in misses:
        print(f"MISS  {text}\n      {why}")
    print(f"\n{ok}/{len(CASES)} phrasings read correctly ({ok / len(CASES):.0%})")
