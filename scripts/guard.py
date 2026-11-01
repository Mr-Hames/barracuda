"""Deliverable Contract Guard: check submitted files against a plain-text assignment.

  python guard.py --task task.txt report.docx slides.pptx         # extract + check
  python guard.py --task task.txt --extract-only                  # just the contract (to review/edit)
  python guard.py --contract contract.json report.pdf data.zip    # check against an edited contract

Prints JSON. Needs pdfplumber, python-docx, python-pptx, openpyxl.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check import check  # noqa: E402
from extract import extract  # noqa: E402
from readers import read_deliverables  # noqa: E402


def run(task_text=None, files=(), contract=None):
    contract = contract if contract is not None else extract(task_text or "")
    facts = read_deliverables(list(files))
    report = check(contract, facts)
    report["files"] = [{k: v for k, v in f.items() if k not in ("text", "headings")} for f in facts]
    return report


def main():
    p = argparse.ArgumentParser(description="Check deliverables against an assignment.")
    p.add_argument("files", nargs="*")
    p.add_argument("--task", help="assignment text file (UTF-8)")
    p.add_argument("--contract", help="contract JSON (from --extract-only, possibly edited)")
    p.add_argument("--extract-only", action="store_true")
    a = p.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if not a.task and not a.contract:
        p.error("give --task or --contract")
    contract = None
    if a.contract:
        with open(a.contract, encoding="utf-8") as fh:
            contract = json.load(fh)
    text = None
    if a.task:
        with open(a.task, encoding="utf-8-sig") as fh:
            text = fh.read()
    if a.extract_only:
        print(json.dumps(extract(text or ""), ensure_ascii=False, indent=2))
        return
    missing = [f for f in a.files if not os.path.exists(f)]
    if missing:
        sys.exit("File not found: " + ", ".join(missing))
    print(json.dumps(run(text, a.files, contract), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
