"""Barracuda (Deliverable Contract Guard): check submitted files against a plain-text assignment.

  python guard.py --task task.txt report.docx slides.pptx         # ready-to-show report (Markdown)
  python guard.py --task task.txt --format json report.docx       # full details as JSON
  python guard.py --task task.txt --format html --out report.html report.docx   # a page for the browser
  python guard.py --task task.txt --extract-only                  # just the contract (to review/edit)
  python guard.py --contract contract.json report.pdf data.zip    # check against an edited contract
  python guard.py --selftest                                      # is everything installed and working?

Works with Python 3.9+. Needs pdfplumber, python-docx, python-pptx, openpyxl.
"""
import argparse
import importlib
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

DEPENDENCIES = {"pdfplumber": "pdfplumber", "docx": "python-docx", "pptx": "python-pptx", "openpyxl": "openpyxl"}


def missing_dependencies():
    out = []
    for module, package in DEPENDENCIES.items():
        try:
            importlib.import_module(module)
        except ImportError:
            out.append(package)
    return out


def run(task_text=None, files=(), contract=None):
    from check import check
    from extract import extract
    from readers import read_deliverables

    contract = contract if contract is not None else extract(task_text or "")
    facts = read_deliverables(list(files))
    report = check(contract, facts)
    report["files"] = [{k: v for k, v in f.items() if k not in ("text", "headings")} for f in facts]
    return report


# ---------- human-readable report ----------

from report import detect_lang, markdown, to_html  # noqa: E402


# ---------- self-test ----------

def selftest():
    """Build a tiny DOCX with a known problem and check it end to end."""
    import docx

    tmp = tempfile.mkdtemp(prefix="barracuda_selftest_")
    path = os.path.join(tmp, "report.docx")
    d = docx.Document()
    d.add_heading("Introduction", level=1)
    d.add_paragraph("word " * 60)
    d.save(path)
    task = ("Submit a Word document (DOCX).\nInclude sections: Introduction and Conclusion.\n"
            "Write at least 50 words.\nDeadline: May 1.")
    report = run(task, [path])
    got = {r["type"]: r["status"] for r in report["results"]}
    expected = {"file_required": "pass", "sections": "fail", "words": "pass", "unverified": "unverified"}
    problems = [f"{k}: expected {v}, got {got.get(k)}" for k, v in expected.items() if got.get(k) != v]
    shutil.rmtree(tmp, ignore_errors=True)  # a leftover temp folder must not fail the self-test
    return {"selftest": "ok" if not problems else "failed", "python": sys.version.split()[0],
            "problems": problems}


def main():
    p = argparse.ArgumentParser(description="Check deliverables against an assignment.")
    p.add_argument("files", nargs="*")
    p.add_argument("--task", help="assignment text file (UTF-8)")
    p.add_argument("--contract", help="contract JSON (from --extract-only, possibly edited)")
    p.add_argument("--extract-only", action="store_true", help="print the contract and stop")
    p.add_argument("--format", choices=("md", "html", "json"), default="md",
                   help="md: ready-to-show text report (default); html: a page to open in the browser; json: details")
    p.add_argument("--out", help="write the report to this file instead of the screen")
    p.add_argument("--lang", choices=("en", "ru", "uk"), help="report language (default: the assignment's)")
    p.add_argument("--selftest", action="store_true", help="check the installation")
    a = p.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    missing = missing_dependencies()
    if missing:
        print(json.dumps({"error": "missing_dependencies", "missing": missing,
                          "fix": f"{os.path.basename(sys.executable)} -m pip install " + " ".join(missing)},
                         ensure_ascii=False, indent=2))
        sys.exit(2)
    if a.selftest:
        result = selftest()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        sys.exit(0 if result["selftest"] == "ok" else 1)
    if not a.task and not a.contract:
        p.error("give --task or --contract")

    contract = None
    if a.contract:
        with open(a.contract, encoding="utf-8-sig") as fh:
            contract = json.load(fh)
        if isinstance(contract, dict):  # accept {"requirements": [...]} too
            contract = contract.get("requirements") or contract.get("contract") or []
    text = None
    if a.task:
        with open(a.task, encoding="utf-8-sig") as fh:
            text = fh.read()
    if a.extract_only:
        from extract import extract
        print(json.dumps(extract(text or ""), ensure_ascii=False, indent=2))
        return
    not_found = [f for f in a.files if not os.path.isfile(f)]
    if not_found:
        print(json.dumps({"error": "file_not_found", "files": not_found}, ensure_ascii=False, indent=2))
        sys.exit(2)
    if not a.files:
        print(json.dumps({"error": "no_files", "fix": "pass the submitted files after the options"}, indent=2))
        sys.exit(2)
    report = run(text, a.files, contract)
    lang = a.lang or detect_lang(text or " ".join(r.get("source", "") for r in report["results"]))
    if a.format == "json":
        output = json.dumps(report, ensure_ascii=False, indent=2)
    elif a.format == "html":
        output = to_html(report, lang)
    else:
        output = markdown(report, lang)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            fh.write(output)
        print(f"Report saved to {os.path.abspath(a.out)}")
    else:
        print(output)


if __name__ == "__main__":
    main()
