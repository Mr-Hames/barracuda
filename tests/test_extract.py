"""Phrasings that are NOT in the benchmark generator: a check that parsing generalises a little.

Run: python -m unittest discover tests
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from extract import extract  # noqa: E402


def items(text):
    return [{k: v for k, v in r.items() if k not in ("id", "source")} for r in extract(text)]


def find(text, rtype):
    return [r for r in items(text) if r["type"] == rtype]


class Paraphrases(unittest.TestCase):
    def test_pages_abbreviation(self):
        r = find("Объём работы — 10-12 стр., шрифт 14.", "pages")
        self.assertEqual((r[0]["min"], r[0]["max"]), (10, 12))

    def test_size_lowercase_mb(self):
        self.assertEqual(find("Вес файла не больше 2 Мб", "max_size_mb")[0]["max"], 2)

    def test_typography_line(self):
        text = "Оформление: Times New Roman, кегль 14, интервал 1,5, поля 2 см."
        self.assertEqual(find(text, "font")[0]["name"], "Times New Roman")
        self.assertEqual(find(text, "font_size")[0]["value"], 14)
        self.assertEqual(find(text, "margins")[0]["left"], 20)

    def test_slides_in_brackets(self):
        r = find("Prepare a PowerPoint presentation (max 10 slides).", "slides")
        self.assertEqual(r[0].get("max"), 10)

    def test_words_more_than(self):
        self.assertEqual(find("Essay of more than 1500 words.", "words")[0]["min"], 1501)

    def test_characters_are_not_words(self):
        # "знаков" (characters) is not a word count: it must stay unverified, not become a words check
        r = items("Объем — минимум 15000 знаков.")
        self.assertFalse([x for x in r if x["type"] == "words"])
        self.assertTrue([x for x in r if x["type"] == "unverified"])

    def test_gost_is_unverified(self):
        r = items("Оформите список литературы по ГОСТ 7.1-2003.")
        self.assertEqual([x["type"] for x in r], ["unverified"])

    def test_zip_delivery(self):
        r = items("Файлы прислать одним архивом .zip.")
        self.assertIn("zip", [x["target"] for x in r if x["type"] == "file_required"])

    def test_sheet_names_listed(self):
        r = find("Excel: листы: Data, Results.", "sheets")
        self.assertEqual(r[0]["names"], ["Data", "Results"])

    def test_convert_from_word(self):
        r = find("Конвертируйте документ из Word в PDF и отправьте.", "file_required")
        self.assertEqual([x["target"] for x in r], ["pdf"])

    def test_word_count_header(self):
        r = find("Word count: 930–1380 words.", "words")
        self.assertEqual((r[0]["min"], r[0]["max"]), (930, 1380))

    def test_ukrainian_portrait(self):
        self.assertEqual(find("Орієнтація сторінки книжкова, формат А4.", "page_format")[0]["orientation"], "portrait")

    def test_only_pdf(self):
        r = find("Принимаются только файлы PDF.", "only_formats")
        self.assertEqual(r[0]["exts"], ["pdf"])

    def test_every_unclear_sentence_listed(self):
        r = items("Срок сдачи 1 июня.\nРабота должна быть интересной.\nCite 5 sources.")
        self.assertEqual(sum(1 for x in r if x["type"] == "unverified"), 3)

    def test_context_line_ignored(self):
        self.assertEqual(items("Тема: История Киева."), [])


class HandEditedContracts(unittest.TestCase):
    """A model may edit the contract badly: it must never turn into a false 'pass'."""

    def setUp(self):
        from check import check
        self.check = check
        self.files = [{"name": "a.pdf", "ext": "pdf", "size_bytes": 1000, "pages": 3, "words": 100, "text": "x"}]

    def status(self, item):
        return self.check([dict(item, id="R1", source="s")], self.files)["results"][0]["status"]

    def test_missing_numbers_is_unverified(self):
        self.assertEqual(self.status({"type": "pages", "target": "pdf"}), "unverified")

    def test_numbers_as_strings(self):
        self.assertEqual(self.status({"type": "pages", "target": ".PDF", "min": "10"}), "fail")
        self.assertEqual(self.status({"type": "pages", "target": "pdf", "min": "2,5"}), "pass")

    def test_garbage_number(self):
        self.assertEqual(self.status({"type": "pages", "target": "pdf", "min": "ten"}), "unverified")

    def test_unknown_type(self):
        self.assertEqual(self.status({"type": "originality", "target": None}), "unverified")

    def test_pattern_without_regex(self):
        self.assertEqual(self.status({"type": "filename", "target": "pdf", "pattern": "<Surname>_HW1.pdf"}), "fail")


if __name__ == "__main__":
    unittest.main()
