![Barracuda — Deliverable Contract Guard](assets/banner.jpg)

# Barracuda — Deliverable Contract Guard (prototype)

A Claude skill that checks submitted files against a plain-text assignment: it turns the task text (Russian, Ukrainian or English) into a list of requirements, checks the objective ones in the actual PDF / DOCX / PPTX / XLSX / ZIP files, and lists everything it could not verify instead of calling it done.

Checks: required formats, allowed formats only, file name pattern, file size, pages, slides, word count, required sections, required phrases, main font, font size, margins, page size and orientation, number of images, leftover comments, tracked changes, placeholder text, sheet names, formula errors, junk files in archives.

## Status: prototype, go/no-go benchmark

Criterion to continue: on 50 prepared assignments with file sets, detect ≥ 90% of labelled objective violations and never report an unverifiable requirement as met.

| test | size | result |
|---|---|---|
| Synthetic benchmark, 12 seeds | 600 assignments, 1195 planted violations | 100% detected, 0 unverifiable reported as met, 0 false alarms |
| Unseen real-life phrasings, batch 1 | 50 sentences | 66% on first run → 100% after fixes |
| Unseen real-life phrasings, batch 2 (written after batch 1 fixes) | 40 sentences | **90% on first run** → 100% after fixes |
| Bad inputs: empty, fake, scanned PDF, encrypted / nested / path-traversal ZIP, empty task | 11 cases | no crashes, no false "met" |
| Python 3.9, 3.10, 3.11, 3.12, 3.13 | – | same results |

**How to read this.** The synthetic benchmark is generated from phrase templates by the same author as the parser: it proves the file readers and checks, and is optimistic about understanding real wording. The best estimate for unseen wording is the first-run score of batch 2: about **90%** of sentences read correctly. None of the misses produced a false "met"; a miss means a false alarm or a requirement left for manual check. The next step is 50 real assignments with real files, labelled by hand.

Known limits: DOCX page count only if Word saved it; margins only from DOCX; fonts from PPTX/XLSX not read; line spacing, indents, alignment, page numbers, character counts, citation styles, originality, tone and deadlines are always "needs a human check"; scanned PDFs (no text layer) can't be text-checked.

## Install

The skill is a `SKILL.md` plus a Python script (Python 3.9+), so it works in any agent that supports Agent Skills and can run terminal commands. Install the libraries once:

```bash
pip install pdfplumber python-docx python-pptx openpyxl
```

Then put this repository into your agent's skills folder. The easiest way (picks the right folder for each agent):

```bash
npx skills add Mr-Hames/barracuda
```

Or clone it by hand:

| Agent | Folder (user-wide) |
|---|---|
| Claude Code | `~/.claude/skills/barracuda` |
| Codex | `~/.codex/skills/barracuda` (or `.agents/skills/` in a project) |
| Google Antigravity | `~/.gemini/antigravity/skills/barracuda` |
| Cursor | `~/.cursor/skills/barracuda` (or `.cursor/skills/` in a project) |
| GitHub Copilot | `~/.copilot/skills/barracuda` (or `.github/skills/` in a project) |

```bash
git clone https://github.com/Mr-Hames/barracuda <folder from the table>
```

Claude.ai: download the repo as ZIP and upload it in Settings → Capabilities → Skills.

Folder names change between agent versions; if the agent doesn't see the skill, check its documentation for "skills". To check the installation: `python scripts/guard.py --selftest`.

## Use

Ask the agent: "check my files against this assignment" and attach the files and the task text. Or run it directly:

```bash
python scripts/guard.py --task task.txt report.docx slides.pptx archive.zip       # Markdown report
python scripts/guard.py --task task.txt --format json report.docx                  # full JSON
python scripts/guard.py --task task.txt --extract-only > contract.json             # review, edit, then:
python scripts/guard.py --contract contract.json report.docx
```

The report comes in the assignment's language (English, Russian, Ukrainian). The script does all the checking, so results don't depend on which model runs it; the model only shows the report. Hand-edited contracts are validated: an item with missing or non-numeric values becomes "needs a human check", never "met".

Tested on Python 3.9, 3.10, 3.11, 3.12 and 3.13 (Windows).

## Benchmark

```bash
pip install pymupdf pillow                     # only for generating test files
python bench/generate.py --n 50 --seed 7       # writes bench/cases/ (not in git)
python bench/evaluate.py                       # recall, false passes, false alarms
python -m unittest discover tests
python tests/hard_phrasings.py     # unseen phrasings, batch 1
python tests/hard_phrasings_2.py   # unseen phrasings, batch 2
```

PDF generation uses Windows fonts (Times New Roman, Arial, Calibri).
