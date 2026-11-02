---
name: barracuda
description: Check submitted files (PDF, DOCX, PPTX, XLSX, ZIP) against a plain-text assignment, brief or contract before handing them in. Turns the task text into requirements, checks the objective ones in the real files (format, file name, size, pages, slides, words, sections, phrases, font, font size, margins, page format, images, comments, tracked changes, placeholder text, sheets, formula errors, junk files in archives) and lists everything it could not verify. Use when the user asks whether their work meets the requirements, before submitting homework, a report, a tender or client deliverable, or to compare files with a brief.
---

# Barracuda: Deliverable Contract Guard

Compare what the assignment asks for with what is really in the files. A script does the checking; your job is to run it and show its report.

`SKILL_DIR` below means the folder this SKILL.md is in.

## Steps

1. **Save the assignment text** the user gave (pasted text, email, or the text of a brief) to a UTF-8 file `task.txt` in the working folder. Copy the text exactly; do not summarise or rewrite it.

2. **Run the check** with all submitted files (use `python3` if `python` is not found):
   ```bash
   python SKILL_DIR/scripts/guard.py --task task.txt FILE1 FILE2 ...
   ```
   - If it prints `"error": "missing_dependencies"`, run the command in its `"fix"` field, then run step 2 again.
   - To confirm the installation works: `python SKILL_DIR/scripts/guard.py --selftest` must print `"selftest": "ok"`.

3. **Show the report** the script printed (Markdown) to the user. It is already in the assignment's language. You may translate the evidence notes into the user's language and add, under each item in "Not met", one short sentence on how to fix it (e.g. "add 2 pages", "rename the file to …", "Review → Accept All Changes", "remove the __MACOSX folder from the archive").

## Rules (always)

- Never say "everything is fine" or "all requirements are met" unless the report's title is READY / ГОТОВО. If anything is under "Needs a human check", say those items still need the user's own check.
- Never change a "Needs a human check" item into "met", and never drop it from what you show.
- Never invent requirements that are not in the assignment, and never edit numbers in the report.
- Read the files only locally with the script; do not upload them anywhere.

## Optional: correct the requirement list (strong models only)

If the report clearly misread the assignment (wrong number, wrong file type, a clear objective requirement missing):

```bash
python SKILL_DIR/scripts/guard.py --task task.txt --extract-only > contract.json
# edit contract.json, then:
python SKILL_DIR/scripts/guard.py --contract contract.json FILE1 FILE2 ...
```

Contract items: `{"id", "type", "target", "source", ...}`. `target` = `pdf` / `docx` / `pptx` / `xlsx` / `zip` / `null` (text documents). Keep `source` as the original sentence. Anything subjective (originality, tone, deadline, sources, citation style, line spacing, character count) must stay `"type": "unverified"`. An item with missing or non-numeric values is automatically treated as unverified, never as met.

| type | fields |
|---|---|
| file_required | target |
| only_formats | exts: ["pdf", ...] |
| filename | pattern (e.g. "<Surname>_HW1.pdf") |
| max_size_mb | max |
| pages, slides, words, images | min and/or max |
| sections | items: [...] |
| contains | phrases: [...] |
| font | name |
| font_size | value (pt) |
| margins | left, right, top, bottom (mm) |
| page_format | paper ("A4"), orientation ("portrait"/"landscape") |
| no_comments, no_tracked_changes, no_placeholders, no_formula_errors, zip_clean | – |
| sheets | names: [...] and/or min |
| unverified | reason |

Add `--format json` to any check command for the full details (facts read from every file). Add `--format html --out barracuda-report.html` for a self-contained report page (light/dark, mobile, loads nothing from the internet); offer it when the user wants something to keep or share.
