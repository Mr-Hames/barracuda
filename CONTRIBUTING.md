# Contributing

Thanks for wanting to help. Bug reports, real assignments that Barracuda misreads, and pull requests are all welcome.

## Reporting a problem

Open an issue at https://github.com/Mr-Hames/barracuda/issues. The most useful reports include the assignment sentence that was misread (or the file type that failed) and what you expected. Please remove personal data from any files you attach. Security problems go through [SECURITY.md](SECURITY.md), not public issues.

## Sending a change

1. Fork the repository and create a branch.
2. Install the dependencies: `pip install -r requirements.txt pymupdf pillow ruff`.
3. Make your change. Every change in behaviour needs a test: a unit test in `tests/`, or a new line in `tests/hard_phrasings*.py` for parsing changes.
4. Before opening the pull request, make sure these pass:
   ```bash
   ruff check .
   python -m unittest discover tests
   python tests/hard_phrasings.py
   python tests/hard_phrasings_2.py
   python bench/generate.py --n 50 --seed 7 && python bench/evaluate.py   # Windows only (uses Windows fonts)
   ```
5. Open a pull request describing what changed and why. CI runs the checks on Windows and Linux for every change, and on macOS every week.

## Rules for changes

- Code style is enforced by ruff (`pyproject.toml`): line length 120, Python 3.9 compatible.
- Never make a check report "met" without evidence from the file. If a fact can't be read, the result must be "needs a human check".
- Files must only be read locally. No network calls.
- New requirement languages go with at least 40 test sentences in that language.

By contributing you agree that your work is released under the MIT license.
