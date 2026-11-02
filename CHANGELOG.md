# Changelog

## 0.1.0 (2 November 2026)

First public prototype.

- Reads an assignment written in English, Ukrainian or Russian and turns it into a list of requirements.
- Checks PDF, DOCX, PPTX, XLSX and ZIP files (including files inside archives) for format, file name, size, pages, slides, words, sections, phrases, font, font size, margins, page format, images, comments, tracked changes, placeholder text, sheets, formula errors and junk files.
- Anything it can't measure goes to "needs a human check" and is never reported as met.
- Ready-to-show report in the language of the assignment (text or a self-contained HTML page); `--format json` for details; `--selftest`.
- Safe with hostile files: path traversal, zip bombs, encrypted and damaged files.
- Tested on Windows, macOS and Linux with Python 3.9 and 3.13. 600-case benchmark, two sets of real-life phrasings, stress tests for bad inputs.
