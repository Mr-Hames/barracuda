"""Contract + file facts -> per-requirement verdicts.

Status is one of: pass, fail, unverified. "unverified" is used whenever the facts needed are missing,
so nothing is ever reported as met without evidence.
"""
import os
import re

from readers import DOC_EXTS

TEXT_EXTS = {"pdf", "docx", "pptx"}
TEXT_TYPES = {"words", "pages", "sections", "contains", "font", "font_size", "margins", "page_format", "images"}


def norm(s):
    s = (s or "").lower().replace("ё", "е").replace("’", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s']", " ", s)).strip()


def font_key(name):
    base = re.split(r"[-,]", name or "")[0]
    n = re.sub(r"[^a-z0-9]", "", base.lower())
    n = re.sub(r"(regular|bold|italic|oblique|light|medium|semibold|book)+$", "", n)  # "Times New Roman Regular"
    return re.sub(r"(psmt|mt|ps)$", "", n)  # "TimesNewRomanPSMT", "ArialMT"


def fmt_range(lo, hi, unit):
    if lo is not None and hi is not None:
        return f"{lo:g}" if lo == hi else f"{lo:g}–{hi:g} {unit}"
    return f"≥{lo:g} {unit}" if lo is not None else f"≤{hi:g} {unit}"


def in_range(value, req):
    lo, hi = req.get("min"), req.get("max")
    return (lo is None or value >= lo) and (hi is None or value <= hi)


def pick(req, files):
    """Files a requirement applies to."""
    target = req.get("target")
    readable = [f for f in files if f.get("ext") != "zip" or req["type"] in ("zip_clean", "max_size_mb")]
    if target:
        return [f for f in readable if f.get("ext") == target]
    if req["type"] == "max_size_mb":
        return files  # archives and the files inside them
    if req["type"] in TEXT_TYPES:
        # "at least 2000 words" is about the text document, not the spreadsheet that comes with it
        docs = [f for f in readable if f.get("ext") in TEXT_EXTS]
        return docs or [f for f in readable if f.get("ext") in DOC_EXTS]
    if req["type"] in ("no_placeholders", "no_comments", "no_tracked_changes"):
        return [f for f in readable if f.get("ext") in DOC_EXTS]
    return readable


def per_file(req, f):
    """(status, evidence) for one file."""
    t, name = req["type"], f["name"]
    if f.get("error"):
        return "fail", f"{name}: {f['error']}"

    if t == "pages":
        pages = f.get("pages") if f["ext"] != "pptx" else f.get("slides")
        if pages is None:
            why = ("Word did not save a page count in this file" if f["ext"] == "docx"
                   else "page count does not apply to this file type")
            return "unverified", f"{name}: {why}"
        ok = in_range(pages, req)
        return ("pass" if ok else "fail"), f"{name}: {pages} pages (need {fmt_range(req.get('min'), req.get('max'), 'pages')})"
    if t == "slides":
        n = f.get("slides")
        if n is None:
            return "unverified", f"{name}: not a presentation"
        return ("pass" if in_range(n, req) else "fail"), \
            f"{name}: {n} slides (need {fmt_range(req.get('min'), req.get('max'), 'slides')})"
    if t == "words":
        n = f.get("words")
        if n is None:
            return "unverified", f"{name}: no text could be read"
        return ("pass" if in_range(n, req) else "fail"), \
            f"{name}: {n} words (need {fmt_range(req.get('min'), req.get('max'), 'words')})"
    if t == "images":
        n = f.get("images")
        if n is None:
            return "unverified", f"{name}: images are not counted for this file type"
        return ("pass" if in_range(n, req) else "fail"), \
            f"{name}: {n} images (need {fmt_range(req.get('min'), req.get('max'), 'images')})"
    if t in ("sections", "contains"):
        if f.get("text") is None:
            return "unverified", f"{name}: no text could be read"
        items = req.get("items") or req.get("phrases") or []
        text = norm(f.get("text"))
        lines = [norm(x) for x in (f.get("headings") or []) + (f.get("text") or "").splitlines() if 0 < len(x) <= 120]
        missing = []
        for item in items:
            key = norm(re.sub(r"^\s*(?:\d+(?:\.\d+)*|[ivxlc]+)[.)]?\s+", "", item, flags=re.I))
            if not key:
                continue
            if t == "sections":
                found = any(ln == key or ln.startswith(key) or re.sub(r"^\d+(?: \d+)* ", "", ln).startswith(key)
                            for ln in lines)
            else:
                found = key in text
            if not found:
                missing.append(item)
        what = "sections" if t == "sections" else "phrases"
        if missing:
            return "fail", f"{name}: missing {what}: " + ", ".join(f"«{m}»" for m in missing)
        return "pass", f"{name}: all {len(items)} {what} found"
    if t == "font":
        got = f.get("main_font")
        if got is None:
            return "unverified", f"{name}: main font is not recorded in the file"
        ok = font_key(got) == font_key(req["name"])
        return ("pass" if ok else "fail"), f"{name}: main font {got} (need {req['name']})"
    if t == "font_size":
        got = f.get("main_font_size")
        if got is None:
            return "unverified", f"{name}: main font size is not recorded in the file"
        ok = abs(got - req["value"]) <= 0.25
        return ("pass" if ok else "fail"), f"{name}: main text {got:g} pt (need {req['value']:g} pt)"
    if t == "margins":
        got = f.get("margins_mm")
        if got is None:
            return "unverified", f"{name}: margins can only be read from Word files"
        bad = [f"{s} {got[s]:g} mm (need {req[s]:g})" for s in ("left", "right", "top", "bottom")
               if s in req and abs(got[s] - req[s]) > 1.5]
        return ("fail", f"{name}: " + ", ".join(bad)) if bad else ("pass", f"{name}: margins as required")
    if t == "page_format":
        paper, orient = f.get("paper"), f.get("orientation")
        if "page_mm" not in f:
            return "unverified", f"{name}: page size unknown for this file type"
        problems = []
        if req.get("paper") and paper != req["paper"]:
            problems.append(f"paper {paper or 'custom ' + 'x'.join(str(v) for v in f['page_mm']) + ' mm'} "
                            f"(need {req['paper']})")
        if req.get("orientation") and orient != req["orientation"]:
            problems.append(f"{orient} (need {req['orientation']})")
        return ("fail", f"{name}: " + ", ".join(problems)) if problems else ("pass", f"{name}: {paper or ''} {orient}")
    if t == "no_comments":
        n = f.get("comments")
        if n is None:
            return "unverified", f"{name}: comments can't be read"
        return ("pass" if n == 0 else "fail"), f"{name}: {n} comments"
    if t == "no_tracked_changes":
        if f["ext"] == "pdf":
            return "pass", f"{name}: PDF has no tracked changes"
        n = f.get("tracked_changes")
        if n is None:
            return "unverified", f"{name}: tracked changes can't be read for this file type"
        return ("pass" if n == 0 else "fail"), f"{name}: {n} tracked changes"
    if t == "no_placeholders":
        ph = f.get("placeholders")
        if ph is None:
            return "unverified", f"{name}: no text could be read"
        return ("fail", f"{name}: placeholder text: " + ", ".join(ph[:5])) if ph else ("pass", f"{name}: none found")
    if t == "no_formula_errors":
        errs = f.get("formula_errors")
        if errs is None:
            return "unverified", f"{name}: not a spreadsheet"
        if errs:
            return "fail", f"{name}: {len(errs)} formula errors: " + ", ".join(errs[:5])
        if f.get("uncalculated_formulas"):
            return "unverified", (f"{name}: {f['uncalculated_formulas']} formulas were saved without results; "
                                  "open and save the file in Excel to check them")
        return "pass", f"{name}: no formula errors"
    if t == "sheets":
        sheets = f.get("sheets")
        if sheets is None:
            return "unverified", f"{name}: not a spreadsheet"
        have = {norm(s) for s in sheets}
        missing = [s for s in req.get("names") or [] if norm(s) not in have]
        too_few = req.get("min") is not None and len(sheets) < req["min"]
        if missing or too_few:
            msg = []
            if missing:
                msg.append("missing sheets: " + ", ".join(f"«{m}»" for m in missing))
            if too_few:
                msg.append(f"{len(sheets)} sheets (need ≥{req['min']:g})")
            return "fail", f"{name}: " + "; ".join(msg)
        return "pass", f"{name}: sheets {', '.join(sheets)}"
    if t == "zip_clean":
        junk = f.get("junk")
        if junk is None:
            return "unverified", f"{name}: not an archive"
        return ("fail", f"{name}: extra files: " + ", ".join(junk[:5])) if junk else ("pass", f"{name}: no extra files")
    if t == "max_size_mb":
        mb = f["size_bytes"] / 1024 / 1024
        return ("pass" if mb <= req["max"] + 1e-9 else "fail"), f"{name}: {mb:.2f} MB (limit {req['max']:g} MB)"
    if t == "filename":
        base = os.path.basename(name)
        ok = re.match(req["regex"], base, re.I) is not None
        return ("pass" if ok else "fail"), f"{name}: {'matches' if ok else 'does not match'} «{req['pattern']}»"
    return "unverified", f"{name}: unknown requirement type {t}"


REQUIRED = {  # a contract item without these can't be checked (e.g. hand-edited by a model)
    "pages": ("min", "max"), "slides": ("min", "max"), "words": ("min", "max"), "images": ("min", "max"),
    "sections": ("items",), "contains": ("phrases",), "font": ("name",), "font_size": ("value",),
    "margins": ("left", "right", "top", "bottom"), "page_format": ("paper", "orientation"),
    "filename": ("regex", "pattern"), "max_size_mb": ("max",), "sheets": ("names", "min"),
    "only_formats": ("exts",), "file_required": ("target",),
}
NUMERIC = ("min", "max", "value", "left", "right", "top", "bottom")


def normalise(req):
    """Make a contract item safe: numbers as numbers, a regex for a pattern, required fields present.
    Returns (item, problem or None)."""
    req = dict(req)
    req["type"] = str(req.get("type") or "unverified").strip()
    if req.get("target") in ("", "any", "all", "none"):
        req["target"] = None
    if isinstance(req.get("target"), str):
        req["target"] = req["target"].lower().lstrip(".")
    for k in NUMERIC:
        if k in req and req[k] is not None:
            try:
                req[k] = float(str(req[k]).replace(",", ".").split()[0])
            except (ValueError, IndexError):
                return req, f"«{k}» is not a number: {req[k]!r}"
    for k in ("items", "phrases", "names", "exts"):
        if isinstance(req.get(k), str):
            req[k] = [req[k]]
    if req["type"] == "filename" and not req.get("regex") and req.get("pattern"):
        from extract import name_regex
        req["regex"] = name_regex(req["pattern"])
    needed = REQUIRED.get(req["type"])
    if needed and not any(req.get(k) not in (None, [], "") for k in needed):
        return req, f"contract item has none of: {', '.join(needed)}"
    if req["type"] == "filename":
        try:
            re.compile(req["regex"])
        except re.error as e:
            return req, f"bad file name pattern: {e}"
    return req, None


def check_one(req, files):
    req, problem = normalise(req)
    if problem:
        return "unverified", [problem]
    t = req["type"]
    if t == "unverified":
        return "unverified", [req.get("reason", "needs a human check")]
    if t == "file_required":
        hits = [f["name"] for f in files if f.get("ext") == req["target"]]
        if hits:
            return "pass", [f"found: {', '.join(hits)}"]
        return "fail", [f"no .{req['target']} file submitted"]
    if t == "only_formats":
        allowed = set(req["exts"])
        bad = [f["name"] for f in files if f.get("ext") not in allowed
               and not (f.get("ext") == "zip" and "zip" in allowed)]
        return ("fail", [f"not allowed: {', '.join(bad)} (allowed: {', '.join(sorted(allowed))})"]) if bad \
            else ("pass", [f"all files are {', '.join(sorted(allowed))}"])
    targets = pick(req, files)
    if t == "filename":
        if not targets:
            return "fail", [f"no {'.' + req['target'] if req.get('target') else ''} file to check the name of"]
        results = [per_file(req, f) for f in targets]
        if any(s == "pass" for s, _ in results):
            return "pass", [e for s, e in results if s == "pass"]
        return "fail", [e for _, e in results]
    if not targets:
        if req.get("target"):
            return "fail", [f"no .{req['target']} file submitted, so this can't be met"]
        return "unverified", ["no file this requirement applies to"]
    results = [per_file(req, f) for f in targets]
    if not req.get("target"):
        # No file type named: judge on the files where the property can be measured at all
        # (fonts of a PDF, not of a spreadsheet). Nothing measurable stays unverified.
        measured = [x for x in results if x[0] != "unverified"]
        if measured:
            skipped = [e for s, e in results if s == "unverified"]
            results = measured + [("note", "not measurable, skipped: " + e) for e in skipped]
    statuses = {s for s, _ in results}
    status = "fail" if "fail" in statuses else "unverified" if "unverified" in statuses else "pass"
    return status, [e for _, e in results]


def check(contract, files):
    results = []
    for req in contract:
        status, evidence = check_one(req, files)
        results.append({**req, "status": status, "evidence": evidence})
    unreadable = [f for f in files if f.get("error")]
    if unreadable:
        results.append({"id": "R0", "type": "readable", "target": None, "source": "(always checked)",
                        "status": "fail", "evidence": [f"{f['name']}: {f['error']}" for f in unreadable]})
    counts = {s: sum(1 for r in results if r["status"] == s) for s in ("pass", "fail", "unverified")}
    verdict = "fail" if counts["fail"] else "incomplete" if counts["unverified"] else "pass"
    return {"verdict": verdict, "counts": counts, "results": results}
