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
           "manual_none": "Check this against the assignment yourself", "checked": "Checked",
           "h_fail_rest": "thing to fix before you hand this in|things to fix before you hand this in",
           "lb_found": "Found", "lb_fix": "Fix", "lb_how": "How", "m_files": "Files"},
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
           "manual_none": "Сверьте это с заданием самостоятельно", "checked": "Проверено",
           "h_fail_rest": "нужно исправить перед сдачей|нужно исправить перед сдачей",
           "lb_found": "Найдено", "lb_fix": "Исправить", "lb_how": "Как", "m_files": "Файлы"},
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
           "manual_none": "Звірте це із завданням самостійно", "checked": "Перевірено",
           "h_fail_rest": "треба виправити перед здачею|треба виправити перед здачею",
           "lb_found": "Знайдено", "lb_fix": "Виправити", "lb_how": "Як", "m_files": "Файли"},
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
:root{--paper:#fbfbf9;--ink:#101114;--sub:#6a6c73;--faint:#a3a5ab;--rule:#e4e4df;--rule2:#101114;--tint:#f2f2ee;
--red:#d1001f;--amber:#a86400;--green:#16824a;--brand:#0003fd;color-scheme:light dark;
--mono:ui-monospace,"SF Mono","Cascadia Mono","JetBrains Mono",Menlo,Consolas,monospace;
--sans:-apple-system,BlinkMacSystemFont,"SF Pro Text","Segoe UI Variable Text","Segoe UI",Inter,Roboto,"Helvetica Neue",Arial,sans-serif}
@media (prefers-color-scheme:dark){:root{--paper:#0e0f12;--ink:#ecedf0;--sub:#9a9ca4;--faint:#62646c;--rule:#24252b;
--rule2:#ecedf0;--tint:#17181d;--red:#ff5c70;--amber:#f0a83a;--green:#46c981;--brand:#7b86ff}}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--paper);color:var(--ink);font:15px/1.55 var(--sans);-webkit-font-smoothing:antialiased}
main{max-width:820px;margin:0 auto;padding:44px 32px 56px}
.lbl{font:500 11px/1.4 var(--mono);letter-spacing:.08em;text-transform:uppercase;color:var(--sub)}
.top{display:flex;justify-content:space-between;align-items:center;gap:16px;padding-bottom:14px;border-bottom:2px solid var(--rule2)}
.brand{display:flex;align-items:center;gap:10px;font-weight:650;letter-spacing:-.01em}
.logo{height:16px;width:auto}
@media (prefers-color-scheme:dark){.logo{filter:brightness(0) invert(1)}}
.verdict{display:grid;grid-template-columns:auto 1fr;gap:4px 28px;align-items:end;padding:36px 0 30px;border-bottom:1px solid var(--rule)}
.big{font:600 clamp(72px,14vw,120px)/.82 var(--sans);letter-spacing:-.06em;font-variant-numeric:tabular-nums}
.verdict.fail .big{color:var(--red)}.verdict.incomplete .big{color:var(--amber)}.verdict.pass .big{color:var(--green)}
.status{display:inline-flex;align-items:center;gap:8px;font:600 12px/1 var(--mono);letter-spacing:.1em;text-transform:uppercase}
.status i{width:9px;height:9px;display:inline-block}
.fail .status i{background:var(--red)}.incomplete .status i{background:var(--amber)}.pass .status i{background:var(--green)}
h1{font:600 clamp(24px,3.6vw,32px)/1.12 var(--sans);letter-spacing:-.022em;margin-top:10px;max-width:520px}
.meta{display:grid;grid-template-columns:repeat(4,1fr);border-bottom:1px solid var(--rule)}
.meta div{padding:14px 0 16px;border-right:1px solid var(--rule);padding-left:16px}
.meta div:first-child{padding-left:0}.meta div:last-child{border-right:0}
.meta b{display:block;font:600 22px/1.2 var(--sans);letter-spacing:-.02em;margin-top:4px;font-variant-numeric:tabular-nums}
.meta .f b{color:var(--red)}.meta .u b{color:var(--amber)}.meta .p b{color:var(--green)}
.files{display:flex;flex-wrap:wrap;gap:6px 18px;padding:12px 0;border-bottom:1px solid var(--rule);list-style:none;
font:12.5px/1.5 var(--mono);color:var(--sub)}
.files li::before{content:"▪ ";color:var(--faint)}
section{margin-top:44px}
h2{display:flex;align-items:baseline;gap:12px;padding-bottom:10px;border-bottom:2px solid var(--rule2)}
h2 .no{font:500 12px var(--mono);color:var(--faint)}
h2 .t{font:650 19px/1.2 var(--sans);letter-spacing:-.015em}
h2 .c{margin-left:auto;font:600 12px var(--mono);letter-spacing:.06em}
.fail h2 .c{color:var(--red)}.unverified h2 .c{color:var(--amber)}.pass h2 .c{color:var(--green)}
.note{color:var(--sub);font-size:14px;padding:10px 0 2px}
.item{display:grid;grid-template-columns:44px 1fr;padding:18px 0;border-bottom:1px solid var(--rule);position:relative}
.item::before{content:"";position:absolute;left:0;top:20px;width:3px;height:calc(100% - 40px);min-height:18px}
.fail .item::before{background:var(--red)}.unverified .item::before{background:var(--amber)}
.num{font:500 12px/1.9 var(--mono);color:var(--faint);padding-left:14px}
.req{font-size:16.5px;font-weight:550;letter-spacing:-.01em;line-height:1.4}
.kv{display:grid;grid-template-columns:84px 1fr;gap:6px 12px;margin-top:10px;font-size:14px}
.kv dt{padding-top:2px}
.kv dd{color:var(--sub)}.kv dd.fix{color:var(--ink);font-weight:500}
.kv dd p+p{margin-top:3px}
.file{font:500 12.5px var(--mono);color:var(--ink);margin-right:8px}
.q{font:12.5px var(--mono);color:var(--ink);background:var(--tint);padding:1px 5px;overflow-wrap:anywhere}
.ok{list-style:none;padding-top:6px}
.ok li{break-inside:avoid;display:grid;grid-template-columns:22px 1fr;padding:9px 0;border-bottom:1px solid var(--rule);font-size:14.5px}
.ok svg{width:14px;height:14px;margin-top:4px;color:var(--green)}
.foot{display:flex;flex-wrap:wrap;justify-content:space-between;gap:8px;margin-top:48px;padding-top:12px;
border-top:2px solid var(--rule2);font:11.5px/1.5 var(--mono);color:var(--sub);letter-spacing:.02em}
.foot span{display:inline-flex;align-items:center;gap:6px}.foot svg{width:13px;height:13px}
@media (max-width:620px){main{padding:24px 18px 40px}.verdict{grid-template-columns:1fr;gap:12px}
.meta{grid-template-columns:repeat(2,1fr)}.meta div:nth-child(2){border-right:0}
.meta div:nth-child(3){padding-left:0;border-top:1px solid var(--rule)}.meta div:nth-child(4){border-top:1px solid var(--rule)}
.item{grid-template-columns:34px 1fr}.num{padding-left:10px}
.kv{grid-template-columns:1fr;gap:2px}.kv dd{margin-bottom:8px}}
@media print{main{padding:0;max-width:none}section{break-inside:auto}.item{break-inside:avoid}}
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
        return f'<p><span class="file">{html.escape(name)}</span><span>{_rich(m.group(2))}</span></p>'
    return f"<p><span>{_rich(text[:1].upper() + text[1:])}</span></p>"


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
        headline = plural(L["h_fail_rest"], c["fail"])
    else:
        headline = L["h_" + verdict]
    big = c["fail"] if verdict == "fail" else c["unverified"] if verdict == "incomplete" else c["pass"]
    stamp = (now or datetime.now()).strftime("%Y-%m-%d %H:%M")
    counter = {"n": 0}

    def rows(status):
        out = []
        for i in (x for x in items if x["status"] == status):
            counter["n"] += 1
            evidence = [e for e in i["evidence"] if status != "unverified" or e != DEFAULT_REASON]
            fixes = i["fixes"] or ([L["manual_none"]] if status == "unverified" else [])
            kv = ""
            if evidence:
                kv += f'<dt class="lbl">{L["lb_found"]}</dt><dd>{"".join(_evidence(e) for e in evidence)}</dd>'
            if fixes:
                key = L["lb_fix"] if status == "fail" else L["lb_how"]
                kv += f'<dt class="lbl">{key}</dt><dd class="fix">{"".join(f"<p>{_rich(h)}</p>" for h in fixes)}</dd>'
            dl = f'<dl class="kv">{kv}</dl>' if kv else ""
            out.append(f'<div class="item"><span class="num">{counter["n"]:02d}</span><div>'
                       f'<p class="req">{_rich(i["source"])}</p>{dl}</div></div>')
        return "".join(out)

    def head(no, status, title):
        return (f'<h2><span class="no">{no:02d}</span><span class="t">{title}</span>'
                f'<span class="c">{c[status]}</span></h2>')

    sections, no = [], 0
    if c["fail"]:
        no += 1
        sections.append(f'<section class="fail">{head(no, "fail", L["s_fail"])}{rows("fail")}</section>')
    if c["unverified"]:
        no += 1
        sections.append(f'<section class="unverified">{head(no, "unverified", L["s_manual"])}'
                        f'<p class="note">{L["manual_note"]}</p>{rows("unverified")}</section>')
    if c["pass"]:
        no += 1
        oks = "".join(f'<li>{_icon("pass")}<span>{_rich(i["source"])}</span></li>'
                      for i in items if i["status"] == "pass")
        sections.append(f'<section class="pass">{head(no, "pass", L["s_pass"])}<ul class="ok">{oks}</ul></section>')
    meta = "".join(f'<div class="{k}"><span class="lbl">{L[lab]}</span><b>{v}</b></div>'
                   for k, lab, v in (("", "m_files", n_files), ("f", "lg_fail", c["fail"]),
                                     ("u", "lg_manual", c["unverified"]), ("p", "lg_pass", c["pass"])))
    chips = "".join(f"<li>{html.escape(n.split('/')[-1])}</li>" for n in files)
    return f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Barracuda: {html.escape(L["pill_" + verdict])}</title><style>{CSS}</style></head>
<body><main>
<header class="top"><div class="brand">{_logo()}Barracuda</div><span class="lbl">{L["checked"]} {stamp}</span></header>
<div class="verdict {verdict}"><div class="big">{big if items else "0"}</div>
<div><span class="status"><i></i>{L["pill_" + verdict]}</span><h1>{html.escape(headline)}</h1></div></div>
<div class="meta">{meta}</div>
{f'<ul class="files" aria-label="{L["files"]}">{chips}</ul>' if chips else ""}
{''.join(sections)}
<footer class="foot"><span>{_icon("lock")}{L["private"]}</span><span>Barracuda {VERSION}</span></footer>
</main></body></html>
"""
