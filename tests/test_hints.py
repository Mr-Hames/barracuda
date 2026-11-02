import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from hints import HINTS, hint  # noqa: E402


def r(type_, status="fail", evidence=(), **kw):
    return {"type": type_, "status": status, "evidence": list(evidence), **kw}


class Hints(unittest.TestCase):
    def test_passing_results_get_no_hint(self):
        self.assertIsNone(hint(r("pages", "pass", ["a.pdf: 12 pages (need 10–15)"], min=10, max=15)))

    def test_counts_say_how_many(self):
        self.assertEqual(hint(r("slides", evidence=["d.pptx: 12 slides (need ≤10 slides)"], max=10)), "Remove 2 slides")
        self.assertEqual(hint(r("pages", evidence=["a.pdf: 14 pages (need 15–20 pages)"], min=15, max=20)),
                         "Add 1 more page")
        self.assertEqual(hint(r("words", evidence=["a.docx: 1,450 words (need ≤1200 words)"], max=1200), "uk"),
                         "Скоротіть приблизно слів: 250")

    def test_filename_gives_an_example(self):
        h = hint(r("filename", pattern="<Surname>_HW1.pdf"), "ru")
        self.assertIn("Иванов_HW1.pdf", h)

    def test_missing_sections_are_named(self):
        h = hint(r("sections", evidence=["a.docx: missing sections: «Conclusion», «Summary»"]))
        self.assertIn("«Conclusion», «Summary»", h)

    def test_unverified_gets_advice_only_when_topic_is_known(self):
        self.assertIn("deadline", hint(r("unverified", "unverified", source="Deadline: Friday, 23:59")))
        self.assertIn("plagiarism", hint(r("unverified", "unverified", source="The work must be original")))
        self.assertIsNone(hint(r("unverified", "unverified", source="Write in a friendly tone")))

    def test_every_language_has_every_key(self):
        keys = set(HINTS["en"])
        for lang in ("uk", "ru"):
            self.assertEqual(set(HINTS[lang]), keys, lang)
            self.assertEqual(set(HINTS[lang]["more"]), set(HINTS["en"]["more"]))


if __name__ == "__main__":
    unittest.main()
