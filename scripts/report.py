"""Human-readable reports (Markdown and a self-contained HTML page) built from a check result.

Both formats use the same grouping: one line per sentence of the assignment. A sentence such as
"Use Times New Roman, 12 pt" is two checks inside, but the person reads it as one requirement, so it
is shown once, with the worst status of its checks.
"""
import base64
import html
import os
import re

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
           "private": "Your files never left this computer"},
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
           "private": "Файлы не покидали этот компьютер"},
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
           "private": "Файли не залишали цей комп'ютер"},
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
        evidence = []
        for p in it["parts"]:
            if p["status"] != status:
                continue
            for e in p["evidence"]:
                if not e.startswith("not measurable, skipped") and e not in evidence:
                    evidence.append(e)
        out.append({"source": it["source"], "status": status, "evidence": evidence})
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


def _evidence(text):
    m = FILE_RE.match(text)
    if m:
        name = m.group(1).split("/")[-1]
        return f'<li><span class="file">{html.escape(name)}</span><span>{html.escape(m.group(2))}</span></li>'
    return f"<li><span>{html.escape(text[:1].upper() + text[1:])}</span></li>"


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
:root{--bg:#f4f5f8;--card:#fff;--ink:#0a0b14;--sub:#686c7e;--hair:#ebecf1;--chip:#f2f3f7;
--red:#d70022;--red-bg:#fdecee;--amber:#b86e00;--amber-bg:#fdf3e1;--green:#12864a;--green-bg:#e7f5ed;
--brand:#0003fd;--shadow:0 1px 2px rgba(10,11,20,.04),0 24px 48px -24px rgba(10,11,20,.18);color-scheme:light dark}
@media (prefers-color-scheme:dark){:root{--bg:#0b0c12;--card:#15161e;--ink:#f3f4f8;--sub:#9a9eb0;--hair:#252733;
--chip:#20222c;--red:#ff6b7f;--red-bg:#3a1820;--amber:#f2b24c;--amber-bg:#36290f;--green:#4ccd86;--green-bg:#123022;
--shadow:0 24px 48px -24px rgba(0,0,0,.6)}}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI Variable Text",
"Segoe UI",Inter,Roboto,"Helvetica Neue",Arial,sans-serif;-webkit-font-smoothing:antialiased}
.hero{height:220px;background:radial-gradient(120% 140% at 10% 0%,#4a4cff 0%,var(--brand) 45%,#0000a8 100%)}
main{max-width:780px;margin:-150px auto 48px;padding:0 20px}
.card{background:var(--card);border-radius:24px;padding:40px 44px 30px;box-shadow:var(--shadow)}
.top{display:flex;align-items:center;justify-content:space-between;gap:12px}
.brand{display:flex;align-items:center;gap:10px;font-weight:600;letter-spacing:-.01em}
.logo{height:18px;width:auto}
@media (prefers-color-scheme:dark){.logo{filter:brightness(0) invert(1)}}
.pill{font-size:13px;font-weight:600;padding:5px 12px;border-radius:99px;white-space:nowrap}
.pill.fail{color:var(--red);background:var(--red-bg)}.pill.incomplete{color:var(--amber);background:var(--amber-bg)}
.pill.pass{color:var(--green);background:var(--green-bg)}
h1{font:600 clamp(28px,4.4vw,38px)/1.1 -apple-system,BlinkMacSystemFont,"SF Pro Display","Segoe UI Variable Display",
"Segoe UI",Inter,Roboto,sans-serif;letter-spacing:-.026em;margin-top:30px}
.sub{color:var(--sub);margin-top:10px;font-size:15.5px}
.bar{display:flex;gap:3px;height:6px;margin-top:24px;border-radius:99px;overflow:hidden}
.bar span{display:block}.bar .f{background:var(--red)}.bar .u{background:var(--amber)}.bar .p{background:var(--green)}
.legend{display:flex;flex-wrap:wrap;gap:6px 20px;margin-top:12px;font-size:13px;color:var(--sub)}
.legend b{color:var(--ink);font-weight:600;margin-right:3px}
.legend i{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:8px;vertical-align:1px}
h2{font-size:13px;font-weight:600;color:var(--sub);margin:36px 0 2px}
.row{display:flex;gap:14px;padding:15px 0;border-top:1px solid var(--hair)}
h2+.row{border-top:0}
.ic{flex:none;width:28px;height:28px;border-radius:50%;display:grid;place-items:center}
.ic svg{width:16px;height:16px}
.fail .ic{color:var(--red);background:var(--red-bg)}.unverified .ic{color:var(--amber);background:var(--amber-bg)}
.req{font-size:16px;font-weight:500;letter-spacing:-.008em;line-height:1.4}
.ev{list-style:none;margin-top:6px;display:grid;gap:5px;font-size:14px;color:var(--sub)}
.ev li{display:flex;flex-wrap:wrap;gap:4px 10px;align-items:baseline}
.file{font-size:12.5px;font-weight:500;color:var(--ink);background:var(--chip);padding:2px 8px;border-radius:7px}
.ok{list-style:none;display:flex;flex-wrap:wrap;gap:8px;margin-top:12px}
.ok li{display:inline-flex;align-items:center;gap:6px;font-size:13.5px;background:var(--green-bg);padding:6px 12px 6px 9px;
border-radius:99px}
.ok svg{width:15px;height:15px;color:var(--green);flex:none}
.foot{display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;margin-top:34px;padding-top:18px;
border-top:1px solid var(--hair);font-size:12.5px;color:var(--sub)}
.foot span{display:inline-flex;align-items:center;gap:6px}.foot svg{width:14px;height:14px}
@media (max-width:560px){.card{padding:28px 22px 22px;border-radius:20px}main{margin-top:-170px}}
@media print{.hero{display:none}main{margin:0;max-width:none}.card{box-shadow:none;padding:0}}
"""


def to_html(report, lang="en"):
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
    total = max(len(items), 1)

    def rows(status):
        out = []
        for i in (x for x in items if x["status"] == status):
            ev = "".join(_evidence(e) for e in i["evidence"])
            out.append(f'<div class="row {status}"><div class="ic">{_icon(status)}</div><div>'
                       f'<p class="req">{html.escape(i["source"])}</p><ul class="ev">{ev}</ul></div></div>')
        return "".join(out)

    sections = []
    if c["fail"]:
        sections.append(f'<h2>{L["s_fail"]}</h2>{rows("fail")}')
    if c["unverified"]:
        sections.append(f'<h2>{L["s_manual"]}</h2>{rows("unverified")}')
    if c["pass"]:
        oks = "".join(f'<li>{_icon("pass")}{html.escape(i["source"])}</li>' for i in items if i["status"] == "pass")
        sections.append(f'<h2>{L["s_pass"]}</h2><ul class="ok">{oks}</ul>')
    bar = "".join(f'<span class="{k}" style="flex:{c[s]}"></span>'
                  for k, s in (("f", "fail"), ("u", "unverified"), ("p", "pass")) if c[s])
    legend = "".join(f'<span><i style="background:var(--{col})"></i><b>{c[s]}</b>{L[lab]}</span>'
                     for s, col, lab in (("fail", "red", "lg_fail"), ("unverified", "amber", "lg_manual"),
                                         ("pass", "green", "lg_pass")))
    return f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Barracuda: {html.escape(L["pill_" + verdict])}</title><style>{CSS}</style></head>
<body><div class="hero"></div><main><article class="card">
<header class="top"><div class="brand">{_logo()}Barracuda</div><span class="pill {verdict}">{L["pill_" + verdict]}</span></header>
<h1>{html.escape(headline)}</h1><p class="sub">{html.escape(sub)}</p>
<div class="bar" role="img" aria-label="{c['fail']} / {c['unverified']} / {c['pass']}" style="opacity:{1 if total else 0}">{bar}</div>
<div class="legend">{legend}</div>
{''.join(sections)}
<footer class="foot"><span>{_icon("lock")}{L["private"]}</span><span>Barracuda {VERSION}</span></footer>
</article></main></body></html>
"""
