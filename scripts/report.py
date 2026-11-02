"""Human-readable reports (Markdown and a self-contained HTML page) built from a check result.

Both formats use the same grouping: one line per sentence of the assignment. A sentence such as
"Use Times New Roman, 12 pt" is two checks inside, but the person reads it as one requirement, so it
is shown once, with the worst status of its checks.
"""
import base64
import html
import os
import re
from datetime import datetime

from hints import hint

VERSION = "0.1.0"
RANK = {"fail": 0, "unverified": 1, "pass": 2}

LABELS = {
    "en": {"fail": "NOT READY", "incomplete": "CHECK MANUALLY", "pass": "READY",
           "summary": "{f} not met · {p} met · {u} need a human check",
           "not_met": "Not met", "manual": "Needs a human check (the files can't show this)", "met": "Met",
           "files": "Files checked", "none": "(no requirements found in the assignment)",
           "all_ok_but": "All checkable requirements are met, but {u} need a human check: don't call it done yet.",
           "readable": "All files must open",
           # HTML
           "pill_fail": "Not ready", "pill_incomplete": "Check manually", "pill_pass": "Ready",
           "h_fail": "{n} thing to fix before you hand this in|{n} things to fix before you hand this in",
           "h_incomplete": "Everything checkable is in order", "h_pass": "Ready to hand in",
           "h_none": "No requirements found",
           "sub": "Checked {f} file against {r} requirements from the assignment.|"
                  "Checked {f} files against {r} requirements from the assignment.",
           "lg_fail": "to fix", "lg_manual": "to check yourself", "lg_pass": "already fine",
           "s_fail": "Fix these", "s_manual": "Check these yourself", "s_pass": "Already fine",
           "private": "Your files never left this computer",
           "manual_note": "The files can't show these. Here is how to check them yourself.",
           "manual_none": "Check this against the assignment yourself", "checked": "Checked"},
    "ru": {"fail": "НЕ ГОТОВО", "incomplete": "ПРОВЕРЬТЕ ВРУЧНУЮ", "pass": "ГОТОВО",
           "summary": "не выполнено: {f} · выполнено: {p} · нужна ручная проверка: {u}",
           "not_met": "Не выполнено", "manual": "Нужна ручная проверка (по файлам этого не определить)",
           "met": "Выполнено", "files": "Проверенные файлы", "none": "(в задании не найдено требований)",
           "all_ok_but": "Все проверяемые требования выполнены, но {u} нужно проверить вручную, "
                         "поэтому работу пока не считайте готовой.",
           "readable": "Все файлы должны открываться",
           "pill_fail": "Не готово", "pill_incomplete": "Проверьте вручную", "pill_pass": "Готово",
           "h_fail": "Перед сдачей нужно исправить: {n}|Перед сдачей нужно исправить: {n}",
           "h_incomplete": "Всё, что можно проверить, в порядке", "h_pass": "Готово к сдаче",
           "h_none": "В задании не найдено требований",
           "sub": "Проверено файлов: {f}, требований из задания: {r}.|Проверено файлов: {f}, требований из задания: {r}.",
           "lg_fail": "исправить", "lg_manual": "проверить самому", "lg_pass": "в порядке",
           "s_fail": "Исправьте", "s_manual": "Проверьте сами", "s_pass": "Уже в порядке",
           "private": "Файлы не покидали этот компьютер",
           "manual_note": "По файлам этого не определить. Вот как проверить самому.",
           "manual_none": "Сверьте это с заданием самостоятельно", "checked": "Проверено"},
    "uk": {"fail": "НЕ ГОТОВО", "incomplete": "ПЕРЕВІРТЕ ВРУЧНУ", "pass": "ГОТОВО",
           "summary": "не виконано: {f} · виконано: {p} · потрібна ручна перевірка: {u}",
           "not_met": "Не виконано", "manual": "Потрібна ручна перевірка (за файлами цього не визначити)",
           "met": "Виконано", "files": "Перевірені файли", "none": "(у завданні не знайдено вимог)",
           "all_ok_but": "Усі вимоги, які можна перевірити, виконано, але {u} треба перевірити вручну, "
                         "тож роботу поки не вважайте готовою.",
           "readable": "Усі файли мають відкриватися",
           "pill_fail": "Не готово", "pill_incomplete": "Перевірте вручну", "pill_pass": "Готово",
           "h_fail": "Перед здачею треба виправити: {n}|Перед здачею треба виправити: {n}",
           "h_incomplete": "Усе, що можна перевірити, гаразд", "h_pass": "Готово до здачі",
           "h_none": "У завданні не знайдено вимог",
           "sub": "Перевірено файлів: {f}, вимог із завдання: {r}.|Перевірено файлів: {f}, вимог із завдання: {r}.",
           "lg_fail": "виправити", "lg_manual": "перевірити самому", "lg_pass": "гаразд",
           "s_fail": "Виправте", "s_manual": "Перевірте самі", "s_pass": "Уже гаразд",
           "private": "Файли не залишали цей комп'ютер",
           "manual_note": "За файлами цього не визначити. Ось як перевірити самому.",
           "manual_none": "Звірте це із завданням самостійно", "checked": "Перевірено"},
}


def detect_lang(text):
    if re.search(r"[іїєґІЇЄҐ]", text or ""):
        return "uk"
    if re.search(r"[а-яА-ЯёЁ]", text or ""):
        return "ru"
    return "en"


def plural(template, n):
    one, many = template.split("|")
    return (one if n == 1 else many)


def grouped(report, lang="en"):
    """One item per assignment sentence: {source, status, evidence: [str]}; worst status wins and only the
    evidence behind that status is kept (a failed sentence shows what failed, not what passed)."""
    items = {}
    for r in report["results"]:
        source = (r.get("source") or "").strip()
        if r.get("type") == "readable":
            source = LABELS[lang]["readable"]
        key = source or r.get("id", "")
        it = items.setdefault(key, {"source": source, "parts": []})
        it["parts"].append(r)
    out = []
    for it in items.values():
        status = min((p["status"] for p in it["parts"]), key=lambda s: RANK[s])
        evidence, fixes = [], []
        for p in it["parts"]:
            if p["status"] != status:
                continue
            for e in p["evidence"]:
                if not e.startswith("not measurable, skipped") and e not in evidence:
                    evidence.append(e)
            h = hint(p, lang)
            if h and h not in fixes:
                fixes.append(h)
        out.append({"source": it["source"], "status": status, "evidence": evidence, "fixes": fixes})
    return out


def counts(items):
    return {s: sum(1 for i in items if i["status"] == s) for s in ("fail", "unverified", "pass")}


# ---------- Markdown ----------

def markdown(report, lang="en"):
    L = LABELS[lang]
    items = grouped(report, lang)
    c = counts(items)
    lines = [f"# Barracuda: {L[report['verdict']]}", "",
             L["summary"].format(f=c["fail"], p=c["pass"], u=c["unverified"]), ""]
    if report["verdict"] == "incomplete" and c["unverified"]:
        lines += [L["all_ok_but"].format(u=c["unverified"]), ""]
    if not items:
        lines += [L["none"], ""]
    for status, title in (("fail", L["not_met"]), ("unverified", L["manual"]), ("pass", L["met"])):
        group = [i for i in items if i["status"] == status]
        if not group:
            continue
        lines += [f"## {title}", ""]
        for n, i in enumerate(group, 1):
            ev = "; ".join(i["evidence"])
            lines.append(f"{n}. **{i['source']}**. {ev}" if status != "pass" else f"- {i['source']}. {ev}")
            lines += [f"   → {h}" for h in i["fixes"]]
        lines.append("")
    names = [f["name"] for f in report.get("files", [])]
    if names:
        lines += [f"{L['files']}: " + ", ".join(names)]
    return "\n".join(lines).rstrip() + "\n"


# ---------- HTML ----------

ICONS = {
    "fail": '<path d="M5 5l6 6M11 5l-6 6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" fill="none"/>',
    "unverified": '<path d="M6.1 6.1a1.95 1.95 0 113.05 1.6c-.72.45-1.15.9-1.15 1.7" stroke="currentColor" '
                  'stroke-width="1.7" stroke-linecap="round" fill="none"/><circle cx="8" cy="11.7" r=".95" fill="currentColor"/>',
    "pass": '<path d="M4 8.4l2.6 2.5L12 5.2" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" '
            'stroke-linejoin="round" fill="none"/>',
    "lock": '<rect x="3.5" y="7" width="9" height="6.5" rx="1.6" fill="none" stroke="currentColor" stroke-width="1.4"/>'
            '<path d="M5.6 7V5.4a2.4 2.4 0 014.8 0V7" fill="none" stroke="currentColor" stroke-width="1.4"/>',
}
FILE_RE = re.compile(r"^(.+?\.(?:docx|pdf|pptx|xlsx|zip|[a-z0-9]{2,5})): (.*)$", re.I)


def _icon(name):
    return f'<svg viewBox="0 0 16 16" aria-hidden="true">{ICONS[name]}</svg>'


def _logo():
    """The mark, embedded so the page works offline and loads nothing from the internet."""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets", "logo-mark.png")
    try:
        with open(path, "rb") as fh:
            data = base64.b64encode(fh.read()).decode("ascii")
        return f'<img class="logo" src="data:image/png;base64,{data}" alt="">'
    except OSError:
        return ""




CSS = """
:root{--bg:#f5f6f9;--card:#fff;--ink:#0a0b14;--sub:#62667a;--hair:#ebecf1;--chip:#f1f2f6;--fixbg:#f7f8fb;
--red:#d70022;--red-soft:#fdecee;--amber:#b06900;--amber-soft:#fdf3e1;--green:#12864a;--green-soft:#e7f5ed;
--on:#fff;--brand:#0003fd;--glow:rgba(0,3,253,.10);
--shadow:0 1px 2px rgba(10,11,20,.04),0 24px 48px -24px rgba(10,11,20,.18);color-scheme:light dark}
@media (prefers-color-scheme:dark){:root{--bg:#0b0c12;--card:#15161e;--ink:#f3f4f8;--sub:#9ea2b4;--hair:#262833;
--chip:#22242f;--fixbg:#1b1c26;--red:#ff6b7f;--red-soft:#3a1820;--amber:#f2b24c;--amber-soft:#36290f;--green:#4ccd86;
--green-soft:#123022;--on:#15161e;--glow:rgba(108,123,255,.16);--shadow:0 24px 48px -24px rgba(0,0,0,.6)}}
*{box-sizing:border-box;margin:0;padding:0}
body{background:radial-gradient(90% 360px at 50% 0,var(--glow),transparent) no-repeat,var(--bg);color:var(--ink);
font:15px/1.5 -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI Variable Text","Segoe UI",Inter,Roboto,
"Helvetica Neue",Arial,sans-serif;-webkit-font-smoothing:antialiased;min-height:100vh}
main{max-width:780px;margin:56px auto;padding:0 20px}
.card{background:var(--card);border-radius:24px;padding:40px 44px 30px;box-shadow:var(--shadow)}
.top{display:flex;align-items:center;justify-content:space-between;gap:12px}
.brand{display:flex;align-items:center;gap:10px;font-weight:600;letter-spacing:-.01em}
.logo{height:18px;width:auto}
@media (prefers-color-scheme:dark){.logo{filter:brightness(0) invert(1)}}
.pill{font-size:13px;font-weight:600;padding:5px 12px;border-radius:99px;white-space:nowrap}
.pill.fail{color:var(--red);background:var(--red-soft)}.pill.incomplete{color:var(--amber);background:var(--amber-soft)}
.pill.pass{color:var(--green);background:var(--green-soft)}
h1{font:600 clamp(28px,4.4vw,38px)/1.1 -apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI Variable Display",
"Segoe UI",Inter,Roboto,sans-serif;letter-spacing:-.026em;margin-top:30px}
.sub{color:var(--sub);margin-top:10px;font-size:15.5px}
.files{display:flex;flex-wrap:wrap;gap:6px;margin-top:12px;list-style:none}
.file,.q{font-size:12.5px;font-weight:500;color:var(--ink);background:var(--chip);padding:2px 8px;border-radius:7px;
overflow-wrap:anywhere}
.q{font-family:ui-monospace,"SF Mono","Cascadia Mono",Consolas,monospace;font-size:12.5px;font-weight:400}
.bar{display:flex;gap:3px;height:6px;margin-top:24px;border-radius:99px;overflow:hidden}
.bar span{display:block}.bar .f{background:var(--red)}.bar .u{background:var(--amber)}.bar .p{background:var(--green)}
.legend{display:flex;flex-wrap:wrap;gap:6px 20px;margin-top:12px;font-size:13px;color:var(--sub)}
.legend b{color:var(--ink);font-weight:600;margin-right:3px}
.legend i{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:8px;vertical-align:1px}
h2{display:flex;align-items:center;gap:10px;font-size:17px;font-weight:600;letter-spacing:-.012em;margin:40px 0 4px}
h2 .n{font-size:12.5px;font-weight:600;min-width:24px;text-align:center;padding:1px 8px;border-radius:99px}
h2.fail .n{color:var(--red);background:var(--red-soft)}h2.unverified .n{color:var(--amber);background:var(--amber-soft)}
h2.pass .n{color:var(--green);background:var(--green-soft)}
.note{color:var(--sub);font-size:14px;margin-bottom:4px}
.row{display:flex;gap:14px;padding:16px 0;border-top:1px solid var(--hair)}
h2+.row,.note+.row{border-top:0}
.ic{flex:none;width:24px;height:24px;border-radius:50%;display:grid;place-items:center;margin-top:1px;color:var(--on)}
.ic svg{width:14px;height:14px}
.fail .ic{background:var(--red)}.unverified .ic{background:var(--amber)}
.body{min-width:0;flex:1}
.req{font-size:16px;font-weight:500;letter-spacing:-.008em;line-height:1.4}
.ev{list-style:none;margin-top:6px;display:grid;gap:5px;font-size:14px;color:var(--sub)}
.ev li{display:flex;flex-wrap:wrap;gap:4px 10px;align-items:baseline}
.fix{margin-top:10px;display:grid;gap:6px}
.fix p{display:flex;gap:8px;align-items:flex-start;font-size:14px;background:var(--fixbg);border-radius:10px;padding:8px 12px}
.fix svg{flex:none;width:14px;height:14px;margin-top:3px;color:var(--sub)}
.ok{list-style:none;margin-top:6px}
.ok li{display:flex;gap:10px;align-items:flex-start;padding:7px 0;font-size:14.5px}
.ok svg{flex:none;width:16px;height:16px;margin-top:3px;color:var(--green)}
.foot{display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;margin-top:34px;padding-top:18px;
border-top:1px solid var(--hair);font-size:12.5px;color:var(--sub)}
.foot span{display:inline-flex;align-items:center;gap:6px}.foot svg{width:14px;height:14px}
@media (max-width:560px){main{margin:20px auto}.card{padding:28px 20px 22px;border-radius:20px}}
@media print{body{background:#fff}main{margin:0;max-width:none}.card{box-shadow:none;border:0;padding:0}}
"""

ICONS["arrow"] = ('<path d="M3 8h9M8.5 4.5L12 8l-3.5 3.5" stroke="currentColor" stroke-width="1.6" '
                  'stroke-linecap="round" stroke-linejoin="round" fill="none"/>')
QUOTED = re.compile(r"[«\"“„]([^«»\"“”„]{1,120})[»\"”]")
DEFAULT_REASON = "can't be checked from the files"


def _rich(text):
    """Escape text and show quoted names in one style, whatever quotes the assignment used."""
    out, pos = [], 0
    for m in QUOTED.finditer(text):
        out.append(html.escape(text[pos:m.start()]))
        out.append(f'<span class="q">{html.escape(m.group(1))}</span>')
        pos = m.end()
    out.append(html.escape(text[pos:]))
    return "".join(out)


def _evidence(text):
    m = FILE_RE.match(text)
    if m:
        name = m.group(1).split("/")[-1]
        return f'<li><span class="file">{html.escape(name)}</span><span>{_rich(m.group(2))}</span></li>'
    return f"<li><span>{_rich(text[:1].upper() + text[1:])}</span></li>"


def to_html(report, lang="en", now=None):
    L = LABELS[lang]
    items = grouped(report, lang)
    c = counts(items)
    verdict = report["verdict"]
    files = [f["name"] for f in report.get("files", []) if not f.get("in_zip")]
    n_files = len(files)
    if not items:
        headline = L["h_none"]
    elif verdict == "fail":
        headline = plural(L["h_fail"], c["fail"]).format(n=c["fail"])
    else:
        headline = L["h_" + verdict]
    sub = plural(L["sub"], n_files).format(f=n_files, r=len(items))
    stamp = (now or datetime.now()).strftime("%Y-%m-%d %H:%M")

    def rows(status):
        out = []
        for i in (x for x in items if x["status"] == status):
            evidence = [e for e in i["evidence"] if status != "unverified" or e != DEFAULT_REASON]
            ev = f'<ul class="ev">{"".join(_evidence(e) for e in evidence)}</ul>' if evidence else ""
            fixes = i["fixes"] or ([L["manual_none"]] if status == "unverified" else [])
            fix = "".join(f"<p>{_icon('arrow')}<span>{_rich(h)}</span></p>" for h in fixes)
            out.append(f'<div class="row {status}"><div class="ic">{_icon(status)}</div><div class="body">'
                       f'<p class="req">{_rich(i["source"])}</p>{ev}'
                       f'{f"<div class=fix>{fix}</div>" if fix else ""}</div></div>')
        return "".join(out)

    def head(status, title):
        return f'<h2 class="{status}">{title}<span class="n">{c[status]}</span></h2>'

    sections = []
    if c["fail"]:
        sections.append(head("fail", L["s_fail"]) + rows("fail"))
    if c["unverified"]:
        sections.append(head("unverified", L["s_manual"]) + f'<p class="note">{L["manual_note"]}</p>' + rows("unverified"))
    if c["pass"]:
        oks = "".join(f'<li>{_icon("pass")}<span>{_rich(i["source"])}</span></li>'
                      for i in items if i["status"] == "pass")
        sections.append(head("pass", L["s_pass"]) + f'<ul class="ok">{oks}</ul>')
    bar = "".join(f'<span class="{k}" style="flex:{c[s]}"></span>'
                  for k, s in (("f", "fail"), ("u", "unverified"), ("p", "pass")) if c[s])
    legend = "".join(f'<span><i style="background:var(--{col})"></i><b>{c[s]}</b>{L[lab]}</span>'
                     for s, col, lab in (("fail", "red", "lg_fail"), ("unverified", "amber", "lg_manual"),
                                         ("pass", "green", "lg_pass")))
    chips = "".join(f'<li class="file">{html.escape(n.split("/")[-1])}</li>' for n in files)
    return f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Barracuda: {html.escape(L["pill_" + verdict])}</title><style>{CSS}</style></head>
<body><main><article class="card">
<header class="top"><div class="brand">{_logo()}Barracuda</div><span class="pill {verdict}">{L["pill_" + verdict]}</span></header>
<h1>{html.escape(headline)}</h1><p class="sub">{html.escape(sub)}</p>
{f'<ul class="files" aria-label="{L["files"]}">{chips}</ul>' if chips else ""}
{f'<div class="bar" role="img" aria-label="{c["fail"]} / {c["unverified"]} / {c["pass"]}">{bar}</div><div class="legend">{legend}</div>' if items else ""}
{''.join(sections)}
<footer class="foot"><span>{_icon("lock")}{L["private"]}</span><span>{L["checked"]} {stamp} · Barracuda {VERSION}</span></footer>
</article></main></body></html>
"""
