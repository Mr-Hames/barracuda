---
name: deliverable-guard
description: Check submitted files (PDF, DOCX, PPTX, XLSX, ZIP) against a plain-text assignment, brief or contract before handing them in. Turns the task text into a list of requirements, checks the objective ones in the real files (format, file name, size, pages, slides, words, sections, phrases, font, font size, margins, page format, images, comments, tracked changes, placeholder text, sheets, formula errors, junk files in archives) and lists everything it could not verify. Use when the user asks whether their work meets the requirements, before submitting homework, a report, a tender or client deliverable, or to compare files with a brief.
---

# Deliverable Contract Guard

Compare what was asked with what is in the files. Never call a requirement met without evidence.

## Workflow

1. **Get the assignment text and the files.** The text can be pasted, a .txt/.docx/.pdf brief, or an email; save it as UTF-8 `task.txt`. Files: PDF, DOCX, PPTX, XLSX, or a ZIP with them (archives are opened and checked inside).

2. **Extract the contract** with the script in this skill's folder (`python3` if `python` is missing; needs `pip install pdfplumber python-docx python-pptx openpyxl`):
   ```bash
   python scripts/guard.py --task task.txt --extract-only > contract.json
   ```
   Read the assignment yourself and compare with `contract.json`:
   - Fix wrong numbers or targets, add objective requirements the parser missed, using only the types below.
   - Anything subjective or not a file property (originality, tone, deadline, number of sources, citation style, line spacing, character counts) stays `"type": "unverified"`. Never delete an unverified item and never turn one into a check that could pass.
   - Keep `source` = the sentence from the assignment, so the user sees where each item came from.

3. **Check the files:**
   ```bash
   python scripts/guard.py --contract contract.json report.docx slides.pptx data.zip
   ```
   (Or `--task task.txt` instead of `--contract` to skip the review step.) Output: `verdict` (`pass` / `fail` / `incomplete`), `counts`, and `results` — one per requirement with `status` (`pass`, `fail`, `unverified`) and `evidence` (what was found, e.g. `report.pdf: 8 pages (need 10–12 pages)`).

4. **Report** in the user's language:
   - Verdict first. `pass` only when every item passed. With any `unverified` item say "N of M checkable requirements are met; K need your check" — never "all requirements are met".
   - **Not met** (`fail`): the requirement, the evidence, and the concrete fix (e.g. "add 2 pages", "rename to Ivanov_Marketing_LR2.pdf", "Review → Accept All Changes", "delete the __MACOSX folder from the archive").
   - **Needs a human check** (`unverified`): list each with its source sentence and why it can't be checked from the files.
   - **Met**: one compact list.

## Requirement types (contract schema)

Every item: `{"id", "type", "target", "source", ...params}`. `target` is a file type (`pdf`, `docx`, `pptx`, `xlsx`, `zip`) or `null` (= the text documents submitted).

| type | params | checked in |
|---|---|---|
| file_required | – (target = type) | any |
| only_formats | exts: [..] | all files |
| filename | pattern, regex | files of target |
| max_size_mb | max | files and archives |
| pages | min, max | PDF; DOCX only if Word saved a page count; PPTX = slides |
| slides | min, max | PPTX |
| words | min, max | PDF, DOCX, PPTX |
| sections | items: [..] | headings / heading-like lines |
| contains | phrases: [..] | text |
| font | name | DOCX, PDF (main font by amount of text) |
| font_size | value | DOCX, PDF (main size) |
| margins | left, right, top, bottom (mm) | DOCX |
| page_format | paper (A4…), orientation | PDF, DOCX |
| images | min, max | PDF, DOCX, PPTX |
| no_comments / no_tracked_changes / no_placeholders | – | DOCX, PPTX, XLSX, PDF |
| sheets | names, min | XLSX |
| no_formula_errors | – | XLSX (formulas saved without results stay unverified) |
| zip_clean | – | ZIP (__MACOSX, .DS_Store, Thumbs.db, ~$ files) |
| unverified | reason | never checked |

## Rules

- Files are read locally; never upload them anywhere.
- A missing fact is `unverified`, not `pass` (e.g. a DOCX page count that Word didn't save, a PDF's margins).
- Don't guess requirements the assignment doesn't state. Hygiene problems you notice in `files` (comments left, placeholder text) can be mentioned separately as "worth fixing", not as failed requirements.
