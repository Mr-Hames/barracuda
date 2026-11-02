"""Bad inputs must never crash the guard and never produce a 'pass' without evidence.

Run: python -m unittest discover tests
"""
import os
import shutil
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from guard import run  # noqa: E402


def statuses(report):
    return {r["type"]: r["status"] for r in report["results"]}


class BadFiles(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def path(self, name, data=b""):
        p = os.path.join(self.dir, name)
        with open(p, "wb") as fh:
            fh.write(data)
        return p

    def docx(self, name="ok.docx", text="Introduction " + "word " * 50):
        import docx
        d = docx.Document()
        d.add_paragraph(text)
        p = os.path.join(self.dir, name)
        d.save(p)
        return p

    def test_empty_pdf(self):
        r = run("Submit a PDF of at least 3 pages.", [self.path("empty.pdf")])
        self.assertEqual(r["verdict"], "fail")
        self.assertNotEqual(statuses(r).get("pages"), "pass")
        self.assertEqual(statuses(r).get("readable"), "fail")

    def test_text_renamed_to_docx(self):
        r = run("Submit a Word document (DOCX) with at least 100 words.", [self.path("fake.docx", b"hello")])
        self.assertEqual(statuses(r)["words"], "fail")
        self.assertEqual(statuses(r)["readable"], "fail")

    def test_uppercase_extension_and_unicode_name(self):
        src = self.docx()
        dst = os.path.join(self.dir, "Мой отчёт ФИНАЛ.DOCX")
        os.rename(src, dst)
        r = run("Сдайте документ Word (DOCX). Не менее 40 слов.", [dst])
        self.assertEqual(statuses(r)["file_required"], "pass")
        self.assertEqual(statuses(r)["words"], "pass")

    def test_scanned_pdf_text_checks_unverified(self):
        import pymupdf  # test-only dependency
        from PIL import Image
        img = os.path.join(self.dir, "scan.png")
        Image.new("RGB", (600, 800), (240, 240, 240)).save(img)
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_image(page.rect, filename=img)
        pdf = os.path.join(self.dir, "scan.pdf")
        doc.save(pdf)
        r = run('Submit a PDF. At least 500 words. Include "Conclusion". No placeholder text (Lorem ipsum).', [pdf])
        s = statuses(r)
        self.assertEqual(s["file_required"], "pass")
        for t in ("words", "contains", "no_placeholders"):
            self.assertEqual(s[t], "unverified", t)

    def test_zip_path_traversal_not_extracted_outside(self):
        z = os.path.join(self.dir, "evil.zip")
        with zipfile.ZipFile(z, "w") as zf:
            zf.write(self.docx(), "../../escaped.docx")
        run("Submit a ZIP archive.", [z])
        self.assertFalse(os.path.exists(os.path.join(os.path.dirname(self.dir), "escaped.docx")))

    def test_encrypted_zip_entry(self):
        z = self.path("locked.zip")
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("a.docx", b"x" * 100)
        with open(z, "rb") as fh:
            data = bytearray(fh.read())
        # set the "encrypted" flag on the local and central headers
        for sig in (b"PK\x03\x04", b"PK\x01\x02"):
            i = data.find(sig)
            off = 6 if sig == b"PK\x03\x04" else 8
            data[i + off] |= 1
        with open(z, "wb") as fh:
            fh.write(bytes(data))
        r = run("Submit a ZIP with a Word document (DOCX) of at least 10 words.", [z])
        self.assertNotEqual(statuses(r).get("words"), "pass")

    def test_zip_bomb_is_stopped(self):
        import readers
        z = os.path.join(self.dir, "bomb.zip")
        with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("big.docx", b"\0" * (8 * 1024 * 1024))  # 8 MB of zeros packs to a few KB
        old = readers.MAX_UNPACKED_BYTES
        readers.MAX_UNPACKED_BYTES = 1024 * 1024  # pretend the limit is 1 MB
        try:
            r = run("Submit a ZIP with a Word document (DOCX) of at least 10 words.", [z])
        finally:
            readers.MAX_UNPACKED_BYTES = old
        self.assertNotEqual(statuses(r).get("words"), "pass")
        self.assertIn("zip bomb", " ".join(e for x in r["results"] for e in x["evidence"]))

    def test_sibling_folder_traversal(self):
        z = os.path.join(self.dir, "evil2.zip")
        with zipfile.ZipFile(z, "w") as zf:
            zf.writestr("../guard_x/escaped.txt", b"x")
        run("Submit a ZIP archive.", [z])
        self.assertFalse(os.path.exists(os.path.join(tempfile.gettempdir(), "guard_x", "escaped.txt")))

    def test_nested_zip(self):
        inner = os.path.join(self.dir, "inner.zip")
        with zipfile.ZipFile(inner, "w") as zf:
            zf.write(self.docx(), "report.docx")
        outer = os.path.join(self.dir, "outer.zip")
        with zipfile.ZipFile(outer, "w") as zf:
            zf.write(inner, "inner.zip")
        r = run("Submit a ZIP archive with a Word document (DOCX).", [outer])
        self.assertEqual(statuses(r)["file_required"], "pass")

    def test_empty_assignment_is_not_ready(self):
        r = run("", [self.docx()])
        self.assertNotEqual(r["verdict"], "pass")

    def test_only_subjective_is_not_ready(self):
        r = run("Make it interesting and original.", [self.docx()])
        self.assertEqual(r["verdict"], "incomplete")

    def test_unknown_file_type(self):
        r = run("At least 10 words.", [self.path("notes.txt", b"one two three")])
        self.assertNotEqual(statuses(r)["words"], "pass")

    def test_empty_xlsx(self):
        import openpyxl
        p = os.path.join(self.dir, "empty.xlsx")
        openpyxl.Workbook().save(p)
        r = run('Submit an Excel file (XLSX) with sheets "Data" and "Summary". Formulas must have no errors.', [p])
        s = statuses(r)
        self.assertEqual(s["sheets"], "fail")
        self.assertEqual(s["no_formula_errors"], "pass")


if __name__ == "__main__":
    unittest.main()
