"""Human-readable reports: grouping, consistent numbers, safe HTML.

Run: python -m unittest discover tests
"""
import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from report import grouped, markdown, to_html  # noqa: E402


def result(source, status, rtype="font", evidence=None):
    return {"id": "R", "type": rtype, "source": source, "status": status, "evidence": evidence or [f"x.docx: {status}"]}


REPORT = {
    "verdict": "fail",
    "counts": {"fail": 2, "pass": 3, "unverified": 1},
    "results": [
        result("Use Times New Roman, 12 pt", "pass", "font", ["r.docx: main font Times New Roman"]),
        result("Use Times New Roman, 12 pt", "fail", "font_size", ["r.docx: main text 14 pt (need 12 pt)"]),
        result("Name it <b>x</b>.pdf", "fail", "filename", ["<script>alert(1)</script>.pdf: does not match"]),
        result("Margins: 25 mm", "pass", "margins"),
        result("Be original", "unverified", "unverified", ["can't be checked from the files"]),
        result("Submit a PDF", "pass", "file_required", ["found: r.pdf"]),
    ],
    "files": [{"name": "r.docx"}, {"name": "r.pdf"}, {"name": "a.zip/r.pdf", "in_zip": "a.zip"}],
}


class Reports(unittest.TestCase):
    def test_one_line_per_sentence_worst_status_wins(self):
        items = grouped(REPORT)
        self.assertEqual(len(items), 5)
        tnr = next(i for i in items if i["source"].startswith("Use Times"))
        self.assertEqual(tnr["status"], "fail")
        self.assertEqual(tnr["evidence"], ["r.docx: main text 14 pt (need 12 pt)"])  # only what failed

    def test_numbers_match_everywhere(self):
        md = markdown(REPORT)
        self.assertIn("2 not met · 2 met · 1 need a human check", md)
        page = to_html(REPORT)
        self.assertIn("2 things to fix", page)
        self.assertIn("against 5 requirements", page)
        self.assertIn("Checked 2 files", page)  # files inside archives aren't counted twice

    def test_html_escapes_everything(self):
        page = to_html(REPORT)
        self.assertNotIn("<script>alert(1)</script>", page)
        self.assertNotIn("<b>x</b>", page)
        self.assertIn("&lt;b&gt;x&lt;/b&gt;", page)

    def test_html_loads_nothing_from_the_internet(self):
        page = to_html(REPORT)
        self.assertFalse(re.search(r"(src|href)=\"(https?:)?//", page))
        self.assertNotIn("@import", page)

    def test_all_languages_and_verdicts(self):
        for lang in ("en", "ru", "uk"):
            for verdict in ("fail", "incomplete", "pass"):
                page = to_html(dict(REPORT, verdict=verdict), lang)
                self.assertIn(f'lang="{lang}"', page)
                self.assertTrue(page.rstrip().endswith("</html>"))

    def test_empty_report(self):
        empty = {"verdict": "incomplete", "counts": {"fail": 0, "pass": 0, "unverified": 0}, "results": [], "files": []}
        self.assertIn("No requirements found", to_html(empty))
        self.assertIn("no requirements found", markdown(empty))


if __name__ == "__main__":
    unittest.main()
