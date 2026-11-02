# Changelog

## Unreleased

- Every problem in the report now says how to fix it ("Remove 2 slides", "Rename the file, for example Smith_Marketing_Report.docx", the exact Word menu), in English, Ukrainian and Russian.
- Items that need a human check say how to check them (deadline, plagiarism, sources, citation style, spacing).
- HTML report redesigned as an inspection sheet: a big count up front, numbered items with Found / Fix lines, the checked files, the date and time of the check, one quote style. Works in light and dark mode, on a phone and in print.

## 0.1.0 (2 November 2026)

First public prototype.

- Reads an assignment written in English, Ukrainian or Russian and turns it into a list of requirements.
- Checks PDF, DOCX, PPTX, XLSX and ZIP files (including files inside archives) for format, file name, size, pages, slides, words, sections, phrases, font, font size, margins, page format, images, comments, tracked changes, placeholder text, sheets, formula errors and junk files.
- Anything it can't measure goes to "needs a human check" and is never reported as met.
- Ready-to-show report in the language of the assignment (text or a self-contained HTML page); `--format json` for details; `--selftest`.
- Safe with hostile files: path traversal, zip bombs, encrypted and damaged files.
- Tested on Windows, macOS and Linux with Python 3.9 and 3.13. 600-case benchmark (1,191 planted mistakes, all found), two sets of real-life phrasings, stress tests for bad inputs.
