![Barracuda, deliverable contract guard](assets/banner.jpg)

[![tests](https://github.com/Mr-Hames/barracuda/actions/workflows/tests.yml/badge.svg)](https://github.com/Mr-Hames/barracuda/actions/workflows/tests.yml) [![codeql](https://github.com/Mr-Hames/barracuda/actions/workflows/codeql.yml/badge.svg)](https://github.com/Mr-Hames/barracuda/actions/workflows/codeql.yml) [![release](https://img.shields.io/github/v/release/Mr-Hames/barracuda)](https://github.com/Mr-Hames/barracuda/releases) [![license](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

# Barracuda

You finished the work. Before you send it, Barracuda reads the assignment, opens your files and tells you what's missing.

It's a skill for AI coding agents (Claude, Codex, Cursor, GitHub Copilot, Google Antigravity). You give it the task text and your files. It gives you back a short report in three parts: what doesn't meet the requirements, what it can't judge and you need to check yourself, and what's fine.

It works with PDF, Word (DOCX), PowerPoint (PPTX), Excel (XLSX) and ZIP archives, including files packed inside an archive. Assignments can be written in English, Ukrainian or Russian.

## Who it's for

Students handing in coursework, where a lecturer asked for 15 to 20 pages in Times New Roman 14 with 3 cm left margin. Freelancers and agencies sending deliverables to a client who wrote the requirements in an email. Anyone who has had work bounced back because of a wrong file name, a forgotten comment or a missing section.

## What it checks

Barracuda only checks things that can be measured in the file itself. In plain words, it will notice if:

- the file is in the wrong format, has the wrong name or is too big
- there are too few or too many pages, slides or words
- a required section or phrase is missing ("Introduction", "Conclusion", your variant number)
- the font, font size, margins, paper size or orientation are not what was asked
- there are fewer pictures or charts than required
- comments, tracked changes or placeholder text like "Lorem ipsum" were left in
- the Excel file lacks a required sheet or has formula errors like #REF! or #DIV/0!
- the archive contains junk such as __MACOSX or .DS_Store

## What it won't pretend to check

Some requirements can't be judged by looking at the file: originality, tone, quality of arguments, deadlines, number of sources, citation style, line spacing. Barracuda never marks these as done. It lists them under "needs a human check" so nothing quietly slips through.

This is the main rule of the project. If the tool isn't sure, it says so.

## What a report looks like

```
# Barracuda: NOT READY

2 not met · 5 met · 1 needs a human check

## Not met
1. Length: 15-20 pages. report.pdf: 12 pages (need 15–20 pages)
2. Name the file "<Surname>_Marketing_LR2.pdf". report.pdf: does not match

## Needs a human check (the files can't show this)
1. The work must be original. Not an objective file property

## Met
- Submit as a PDF. found: report.pdf
- Use Times New Roman font. report.pdf: main font TimesNewRomanPSMT
- Required sections: Introduction, Analysis, Conclusion. report.pdf: all 3 sections found
...
```

The report comes out in the language of the assignment.

## Install

You need Python 3.9 or newer and a few libraries. Install them once:

```bash
pip install pdfplumber python-docx python-pptx openpyxl defusedxml
```

Then add the skill to your agent. The simplest way picks the right folder by itself:

```bash
npx skills add Mr-Hames/barracuda
```

If you'd rather do it by hand, clone the repository into your agent's skills folder:

| Agent | Folder |
|---|---|
| Claude Code | `~/.claude/skills/barracuda` |
| Codex | `~/.codex/skills/barracuda` |
| Google Antigravity | `~/.gemini/antigravity/skills/barracuda` |
| Cursor | `~/.cursor/skills/barracuda` |
| GitHub Copilot | `~/.copilot/skills/barracuda` |

```bash
git clone https://github.com/Mr-Hames/barracuda ~/.claude/skills/barracuda
```

On claude.ai, download this repository as a ZIP and upload it in Settings, Capabilities, Skills.

Agents sometimes move their skills folder between versions. If yours doesn't see the skill, look up "skills" in its documentation. To make sure everything works, run `python scripts/guard.py --selftest`. It should answer `"selftest": "ok"`.

## How to use it

Attach your files, paste the assignment and ask something like "check my work against this task". That's it.

You can also run the checker yourself, without an agent:

```bash
python scripts/guard.py --task task.txt report.docx slides.pptx
```

Add `--format json` to see every detail the script read from your files.

Your files never leave your computer. Everything is read locally, and hostile files (zip bombs, tricky archive paths, broken documents) are handled safely. See [SECURITY.md](SECURITY.md).

## How well it works

This is a prototype, and here are the numbers as they are.

On 600 generated assignments with 1,195 deliberately planted mistakes, Barracuda found all of them, raised no false alarms and never called an unverifiable requirement "done". Those assignments come from templates I wrote myself, so the score is optimistic about understanding real wording.

The more honest number comes from 40 real-life phrasings written separately: 90% were understood correctly on the first try. The misses never turned into a false "done". In the worst case the tool raised an extra warning or left a requirement for you to check.

Known limits. A Word file's page count is only known if the file was last saved in Microsoft Word. Margins are read from Word files only. Scanned PDFs can't be checked for text. Formatting standards such as APA or DSTU are not built in yet.

## For developers

The checks are done by a script, so the result is the same no matter which AI model runs it. The model only shows the report.

```bash
python scripts/guard.py --task task.txt --extract-only > contract.json   # see how the task was read
python scripts/guard.py --contract contract.json report.docx             # check against an edited list
python -m unittest discover tests                                         # unit and stress tests
python bench/generate.py --n 50 --seed 7 && python bench/evaluate.py      # benchmark (needs pymupdf, pillow)
python tests/hard_phrasings_2.py                                          # real-life phrasings
```

Tested on Python 3.9 to 3.13.

## License

MIT
