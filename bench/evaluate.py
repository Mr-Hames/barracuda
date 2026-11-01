"""Score the guard on the benchmark.

  python bench/evaluate.py [--cases bench/cases] [--verbose]

Matching: a gold requirement is linked to the guard's results whose source text overlaps its sentence
and whose type is the same. Metrics:
  recall          planted violations reported as "fail"                 (goal >= 90%)
  false_pass      requirements labelled "unverified" that came out "pass" (goal 0)
  silent_drop     "unverified" sentences the guard didn't list at all      (informational)
  false_alarm     requirements labelled "pass" that came out "fail"       (informational)
"""
import argparse
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "scripts"))
from guard import run  # noqa: E402


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", s.lower().replace("ё", "е"))).strip()


def linked(gold_item, results):
    g = norm(gold_item["sentence"])
    out = []
    for r in results:
        src = norm(r.get("source", ""))
        if src and (src in g or g in src):
            out.append(r)
    return out


def evaluate(cases_dir, verbose=False):
    totals = dict(violations=0, detected=0, unverified=0, false_pass=0, silent_drop=0, passes=0, false_alarm=0,
                  recognised=0, objective=0)
    misses = []
    for case in sorted(glob.glob(os.path.join(cases_dir, "case*"))):
        with open(os.path.join(case, "task.txt"), encoding="utf-8") as fh:
            task = fh.read()
        with open(os.path.join(case, "gold.json"), encoding="utf-8") as fh:
            gold = json.load(fh)
        files = sorted(glob.glob(os.path.join(case, "files", "*")))
        report = run(task, files)
        results = report["results"]
        for g in gold["requirements"]:
            hits = linked(g, results)
            same = [r for r in hits if r["type"] == g["type"]
                    and (r.get("target") in (None, g["target"]) or g["type"] in ("file_required",))]
            if g["expect"] == "unverified":
                totals["unverified"] += 1
                if any(r["status"] == "pass" for r in hits):
                    totals["false_pass"] += 1
                    misses.append((case, "FALSE PASS", g, hits))
                elif not any(r["status"] == "unverified" for r in hits):
                    totals["silent_drop"] += 1
                    if verbose:
                        misses.append((case, "silent", g, hits))
                continue
            totals["objective"] += 1
            if same:
                totals["recognised"] += 1
            if g["expect"] == "fail":
                totals["violations"] += 1
                if any(r["status"] == "fail" for r in same):
                    totals["detected"] += 1
                else:
                    misses.append((case, "MISSED", g, same or hits))
            else:
                totals["passes"] += 1
                if any(r["status"] == "fail" for r in same):
                    totals["false_alarm"] += 1
                    misses.append((case, "false alarm", g, same))
    t = totals
    summary = {
        "cases": len(glob.glob(os.path.join(cases_dir, "case*"))),
        "violations": t["violations"],
        "recall": round(t["detected"] / t["violations"], 3) if t["violations"] else None,
        "unverified_labelled": t["unverified"],
        "false_pass": t["false_pass"],
        "silent_drop": t["silent_drop"],
        "objective_requirements": t["objective"],
        "recognised": round(t["recognised"] / t["objective"], 3) if t["objective"] else None,
        "false_alarm": t["false_alarm"],
        "false_alarm_rate": round(t["false_alarm"] / t["passes"], 3) if t["passes"] else None,
    }
    return summary, misses


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cases", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "cases"))
    p.add_argument("--verbose", action="store_true")
    a = p.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    summary, misses = evaluate(a.cases, a.verbose)
    for case, kind, g, hits in misses:
        print(f"{kind:12} {os.path.basename(case)} [{g['type']}/{g['target']}] {g['sentence']}")
        for r in hits[:3]:
            print(f"{'':14}-> {r['type']}/{r.get('target')} {r['status']}: {'; '.join(r['evidence'])[:150]}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    ok = (summary["recall"] or 0) >= 0.9 and summary["false_pass"] == 0
    print("CRITERION MET" if ok else "CRITERION NOT MET")


if __name__ == "__main__":
    main()
