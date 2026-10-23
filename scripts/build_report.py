#!/usr/bin/env python3
"""Build the standalone DejaViewed status report (HTML + Markdown) from two JSON files.

Inputs  (default date 2026-10-23, override with --date YYYY-MM-DD):
    data/reports/status_<date>.json
    data/reports/growth_assets_<date>.json
Outputs:
    docs/reports/dejaviewed_status_<date>.html   single file, inline CSS/JS, no network requests
    docs/reports/dejaviewed_status_<date>.md     faithful Markdown rendering for diffing

Idempotent: the output depends only on the inputs (plus the list of entry pages in site/e/,
used to turn bare entry ids into /e/<id> links). Re-run after the JSONs are regenerated:
    python3 scripts/build_report.py
"""
from __future__ import annotations

import argparse
import difflib
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = "https://dejaviewed.dev"

# ---------------------------------------------------------------- acronyms
# Expanded on first use per section (Victor does not know most acronyms).
GLOSSARY = [
    ("JSON-LD", "JSON-LD structured-data markup for search engines"),
    ("SEO", "search-engine optimization"),
    ("AEO", "answer-engine optimization, i.e. getting cited by AI assistants"),
    ("GSC", "Google Search Console"),
    ("FTC", "US Federal Trade Commission, the regulator that requires ad disclosures"),
    ("CFTC", "US Commodity Futures Trading Commission"),
    ("MCPs", "Model Context Protocol servers, plug-ins that let AI agents use tools"),
    ("MCP", "Model Context Protocol, the plug-in standard that lets AI agents use tools"),
    ("IG", "Instagram"),
    ("UGC", "user-generated content"),
    ("TTS", "text-to-speech"),
    ("CTAs", "calls to action"),
    ("CTA", "call to action"),
    ("LLMs", "large language models"),
    ("LLM", "large language model"),
    ("DMs", "direct messages"),
    ("DM", "direct message"),
    ("CLI", "command-line tool"),
    ("YMYL", "'Your Money or Your Life', Google's label for finance/health topics held to a stricter quality bar"),
    ("UX", "user experience"),
    ("UI", "user interface"),
    ("RSS", "Really Simple Syndication feed"),
    ("UAs", "user agents, the name strings browsers and bots send"),
    ("UA", "user agent, the name string a browser or bot sends"),
    ("OG", "Open Graph social-preview tags"),
    ("MRR", "monthly recurring revenue"),
    ("H1", "main page heading"),
    ("GPUs", "graphics processors"),
    ("GPU", "graphics processor"),
    ("SERP", "search results page"),
    ("SDK", "software development kit"),
    ("YT", "YouTube"),
    ("YC", "Y Combinator"),
    ("FAQs", "frequently asked questions"),
    ("FAQ", "frequently asked questions"),
    ("DIY", "do-it-yourself"),
    ("CN", "China"),
    ("SKU", "product package"),
    ("AGPL", "Affero General Public License, a share-alike open-source license"),
    ("LCP", "Largest Contentful Paint, a page-load speed metric"),
    ("CLS", "Cumulative Layout Shift, a visual-stability metric"),
    ("PR", "public relations"),
]
_BASE = {a: a.rstrip("s") if a.endswith("s") and a.rstrip("s") in dict(GLOSSARY) else a for a, _ in GLOSSARY}
_ACR_RE = re.compile(r"(?<![\w\-/.#])(" + "|".join(re.escape(a) for a, _ in GLOSSARY) + r")(?![\w\-])")
_FULL = dict(GLOSSARY)


class Section:
    """Tracks which acronyms were already expanded inside one report section."""

    def __init__(self):
        self.used: set[str] = set()

    def expand(self, text: str) -> str:
        def rep(m):
            a = m.group(1)
            base = _BASE[a]
            if base in self.used:
                return a
            self.used.add(base)
            return f"{_FULL[a]} ({a})"
        return _ACR_RE.sub(rep, text)


# ---------------------------------------------------------------- linking
SITE_SEGMENTS = (
    "e|guides|deeper|tools|compare|best|go|prompts|api|catalog|method|about|collections|"
    "start-here|search|rate|system-prompts|feed\\.xml|robots\\.txt|sitemap\\.xml|llms\\.txt|"
    "llms-full\\.txt|dataset|this-does-not-exist"
)
PATH_RE = re.compile(r"(?<![\w.~/:\-])(/(?:" + SITE_SEGMENTS + r")(?:[\w\-./#]*[\w/#])?)(?![\w<])")
URL_RE = re.compile(r"https?://[^\s<>\"'()&]+[^\s<>\"'()&.,;:]")
ENTRY_IDS: set[str] = set()


def site_url(path: str) -> str:
    return SITE + path


def _id_re():
    if not ENTRY_IDS:
        return None
    return re.compile(r"(?<![\w/\-])(" + "|".join(sorted((re.escape(i) for i in ENTRY_IDS), key=len, reverse=True)) + r")(?![\w\-])")


ID_RE = None


def _tokenize(text: str):
    """Split text into ('text', s) / ('link', label, href) pieces. URLs > site paths > bare entry ids."""
    out = []
    pos = 0
    pats = [URL_RE, PATH_RE] + ([ID_RE] if ID_RE else [])
    while pos < len(text):
        best = None
        for i, p in enumerate(pats):
            m = p.search(text, pos)
            if m and (best is None or m.start() < best[0].start()):
                best = (m, i)
        if not best:
            out.append(("text", text[pos:]))
            break
        m, i = best
        if m.start() > pos:
            out.append(("text", text[pos:m.start()]))
        tok = m.group(0)
        if i == 0:
            out.append(("link", tok, tok))
        elif i == 1:
            out.append(("link", tok, site_url(tok)))
        else:
            out.append(("link", tok, site_url("/e/" + tok)))
        pos = m.end()
    return out


def h(text, sec: Section | None = None, link=True) -> str:
    """Plain text -> safe HTML: acronym expansion, escaping, auto-links."""
    text = "" if text is None else str(text)
    if sec:
        text = sec.expand(text)
    if not link:
        return html.escape(text)
    parts = []
    for t in _tokenize(text):
        if t[0] == "text":
            parts.append(html.escape(t[1]))
        else:
            parts.append(f'<a href="{html.escape(t[2])}" target="_blank" rel="noopener">{html.escape(t[1])}</a>')
    return "".join(parts)


def m(text, sec: Section | None = None, link=True, cell=False) -> str:
    """Plain text -> Markdown with the same expansion and links."""
    text = "" if text is None else str(text)
    if sec:
        text = sec.expand(text)
    text = text.replace("\n", " ")
    if not link:
        out = text
    else:
        parts = []
        for t in _tokenize(text):
            if t[0] == "text":
                parts.append(t[1])
            else:
                parts.append(f"[{t[1]}]({t[2]})")
        out = "".join(parts)
    out = out.replace("<", "&lt;").replace(">", "&gt;")
    if cell:
        out = out.replace("|", "\\|")
    return out


def a_tag(href: str, label: str) -> str:
    return f'<a href="{html.escape(href)}" target="_blank" rel="noopener">{html.escape(label)}</a>'


def live_link_html(p: str) -> str:
    """live_urls entries: '/x', '/e/<id>' placeholder, or '/x (note)'."""
    path, _, rest = p.partition(" ")
    if "<" in path:
        return f'<code>{html.escape(p)}</code>'
    out = a_tag(site_url(path), SITE.replace("https://", "") + path)
    return out + (" " + html.escape(rest) if rest else "")


def live_link_md(p: str) -> str:
    path, _, rest = p.partition(" ")
    if "<" in path:
        return f"`{p}`"
    return f"[{SITE.replace('https://', '')}{path}]({site_url(path)})" + (" " + rest if rest else "")


def slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# ---------------------------------------------------------------- CSS / JS
CSS = """
:root{--bg:#0a0a0f;--bg-2:#0f0f1a;--surface:#12121a;--panel:#161622;--border:rgba(255,255,255,0.08);--border-hi:rgba(255,255,255,0.15);
--text:#e8e8f0;--text-dim:#a0a0b8;--text-mute:#6a6a80;--accent:#a78bfa;--accent-2:#f472b6;--accent-3:#60a5fa;--ok:#4cda8c;--warn:#fbbf24;--bad:#f05060;
--s:#fbbf24;--a:#a78bfa;--b:#60a5fa;--c:#6a6a80;
--sans:system-ui,-apple-system,'Segoe UI',Roboto,'Helvetica Neue',Arial,sans-serif;--mono:ui-monospace,'SF Mono',Menlo,Consolas,'DejaVu Sans Mono','Liberation Mono',monospace}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--text);font-family:var(--sans);line-height:1.55;font-size:15px}
a{color:var(--accent-3);text-decoration:none;overflow-wrap:anywhere}a:hover{text-decoration:underline}
code,pre,.mono{font-family:var(--mono)}
code{font-size:.88em;background:var(--panel);padding:1px 5px;border-radius:4px;overflow-wrap:anywhere}
pre{background:#07070c;border:1px solid var(--border);border-radius:8px;padding:12px 14px;font-size:12.5px;line-height:1.5;white-space:pre-wrap;word-break:break-word;margin:8px 0}
.layout{display:flex;max-width:1440px;margin:0 auto}
nav.toc{flex:0 0 250px;position:sticky;top:0;align-self:flex-start;max-height:100vh;overflow:auto;padding:22px 14px 22px 20px;border-right:1px solid var(--border);font-size:13px}
nav.toc summary{font-family:var(--mono);font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--text-mute);cursor:pointer;margin-bottom:8px}
nav.toc ol{list-style:none;padding:0;margin:0}nav.toc li{margin:2px 0}
nav.toc a{color:var(--text-dim);display:block;padding:3px 8px;border-radius:6px}nav.toc a:hover{background:var(--panel);color:var(--text);text-decoration:none}
nav.toc ol ol a{font-size:12px;padding-left:20px;color:var(--text-mute)}
main{flex:1;min-width:0;padding:26px 36px 60px;max-width:1150px}
h1{font-size:28px;margin:0 0 6px;letter-spacing:-.01em}
h2{font-size:21px;margin:44px 0 12px;padding-top:12px;border-top:1px solid var(--border)}
h2 .num{font-family:var(--mono);color:var(--accent);font-size:14px;margin-right:8px}
h3{font-size:16px;margin:26px 0 10px;color:var(--text)}
h4{font-size:14px;margin:0 0 6px}
p{margin:8px 0}
.sub{color:var(--text-dim);font-family:var(--mono);font-size:12px}
.lede{color:var(--text-dim);max-width:900px}
.note{color:var(--text-mute);font-size:12.5px}
.tablewrap{overflow-x:auto;margin:10px 0}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{border-bottom:1px solid var(--border);padding:7px 8px;text-align:left;vertical-align:top;overflow-wrap:anywhere}
th{font-family:var(--mono);font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--text-mute);font-weight:600;background:var(--bg-2)}
td.n{font-family:var(--mono);white-space:nowrap}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(320px,100%),1fr));gap:12px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:14px 16px;min-width:0}
.card.wide{grid-column:1/-1}
.card p{font-size:14px}
.ev{font-family:var(--mono);font-size:11.5px;color:var(--text-mute);margin-top:8px;overflow-wrap:anywhere}
.ev b{color:var(--text-dim);font-weight:600}
.links{font-size:12.5px;margin-top:6px}
.badge{display:inline-block;font-family:var(--mono);font-size:10.5px;font-weight:700;text-transform:uppercase;letter-spacing:.05em;padding:2px 7px;border-radius:999px;border:1px solid var(--border-hi);color:var(--text-dim);vertical-align:middle;white-space:nowrap}
.b-todo{color:var(--warn);border-color:rgba(251,191,36,.45)}
.b-done{color:var(--ok);border-color:rgba(76,218,140,.45)}
.b-opt{color:var(--accent-3);border-color:rgba(96,165,250,.45)}
.b-part{color:var(--accent);border-color:rgba(167,139,250,.45)}
.b-defer{color:var(--text-mute)}
.b-H{color:var(--ok);border-color:rgba(76,218,140,.45)}.b-M{color:var(--warn);border-color:rgba(251,191,36,.45)}.b-L{color:var(--text-mute)}
.tier{display:inline-block;font-family:var(--mono);font-weight:800;font-size:11px;width:20px;text-align:center;border-radius:4px;color:#0a0a0f}
.t-S{background:var(--s)}.t-A{background:var(--a)}.t-B{background:var(--b)}.t-C{background:var(--c)}
.today{background:linear-gradient(135deg,rgba(167,139,250,.10),rgba(96,165,250,.06));border:1px solid rgba(167,139,250,.35);border-radius:10px;padding:12px 16px;margin:12px 0}
.today ol{margin:6px 0 0;padding-left:20px}
.todo{background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px 16px;margin:10px 0}
.todo .head{display:flex;gap:10px;align-items:flex-start}
.todo input{margin-top:5px;accent-color:var(--accent);width:16px;height:16px;flex:0 0 auto}
.todo h4{font-size:15px;flex:1}
.todo ol{margin:6px 0;padding-left:22px;font-size:14px}
.meta{display:flex;flex-wrap:wrap;gap:6px 18px;font-size:12.5px;color:var(--text-dim);margin-top:6px}
.meta b{color:var(--text-mute);font-family:var(--mono);font-size:11px;text-transform:uppercase;font-weight:600;margin-right:4px}
details>summary{cursor:pointer;color:var(--text-dim);font-size:13px}
details.more{margin-top:6px}
.week{font-family:var(--mono);color:var(--accent);font-weight:700}
.gantt{display:grid;grid-template-columns:150px repeat(8,1fr);gap:3px 0;font-size:12px;margin:12px 0;align-items:center}
.gantt .hd{font-family:var(--mono);font-size:10.5px;color:var(--text-mute);text-align:center;border-bottom:1px solid var(--border);padding-bottom:4px}
.gantt .lbl{padding-right:8px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.gantt .bar{height:16px;border-radius:4px;font-family:var(--mono);font-size:10px;line-height:16px;padding:0 6px;overflow:hidden;white-space:nowrap;color:#0a0a0f}
.bar.apply{background:linear-gradient(90deg,#7c5cf0 0 33%,rgba(167,139,250,.30) 33%);color:#fff;text-shadow:0 1px 2px rgba(0,0,0,.6)}
.bar.cond{background:rgba(251,191,36,.16);border:1px solid rgba(251,191,36,.6);color:var(--warn)}
.bar.other{background:transparent;border:1px dashed var(--border-hi);color:var(--text-mute)}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-size:12px;color:var(--text-dim)}
.legend span::before{content:'';display:inline-block;width:22px;height:10px;border-radius:3px;margin-right:6px;vertical-align:middle}
.legend .l1::before{background:linear-gradient(90deg,#7c5cf0 0 33%,rgba(167,139,250,.30) 33%)}
.legend .l2::before{background:rgba(251,191,36,.16);border:1px solid rgba(251,191,36,.6)}
.legend .l3::before{border:1px dashed var(--border-hi)}
.money{border-left:3px solid var(--warn);padding:8px 14px;background:var(--surface);border-radius:0 8px 8px 0}
.fn{font-size:12px;color:var(--text-mute)}
sup a{font-family:var(--mono);font-size:10px}
ul.checks{list-style:none;padding:0}ul.checks li{display:flex;gap:10px;align-items:flex-start;margin:6px 0;font-size:14px}
ul.checks input{margin-top:4px;accent-color:var(--accent)}
footer{margin-top:50px;padding-top:14px;border-top:1px solid var(--border);font-size:12px;color:var(--text-mute)}
.sr{position:absolute;left:-9999px}
@media (max-width:1000px){.badge{white-space:normal}.layout{display:block}nav.toc{position:static;max-height:none;border-right:0;border-bottom:1px solid var(--border);padding:12px 16px}main{padding:18px 16px 40px}.gantt{grid-template-columns:110px repeat(8,1fr)}}
@media print{
 :root{--bg:#fff;--bg-2:#f3f3f6;--surface:#fff;--panel:#f1f1f4;--border:#d8d8e0;--border-hi:#bbb;--text:#111;--text-dim:#333;--text-mute:#555;--accent:#5b3fd0;--accent-3:#1d4ed8}
 body{font-size:11pt;background:#fff}nav.toc{display:none}main{max-width:none;padding:0}
 pre{background:#f6f6f8}.bar.apply{color:#111;text-shadow:none}.card,.todo,tr{break-inside:avoid}a{color:#1d4ed8}
 h2{break-after:avoid}
}
"""

JS = """
(function(){
 var t=document.getElementById('toc-d');
 function fit(){ if(!t) return; if(window.innerWidth>1000){t.open=true;} }
 if(t){ if(window.innerWidth<=1000){t.open=false;} fit(); window.addEventListener('resize',fit); }
 window.addEventListener('beforeprint',function(){document.querySelectorAll('details').forEach(function(d){d.setAttribute('data-was',d.open?'1':'0');d.open=true;});});
 window.addEventListener('afterprint',function(){document.querySelectorAll('details[data-was]').forEach(function(d){d.open=d.getAttribute('data-was')==='1';});});
 var KEY='dv-report-checks';var st={};
 try{st=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){}
 document.querySelectorAll('input[type=checkbox][data-k]').forEach(function(c){
  var k=c.getAttribute('data-k'); if(k in st) c.checked=st[k];
  c.addEventListener('change',function(){st[k]=c.checked;try{localStorage.setItem(KEY,JSON.stringify(st))}catch(e){}});
 });
})();
"""


# ---------------------------------------------------------------- helpers
def badge_for_status(status: str):
    s = status.lower()
    if s.startswith("done"):
        return "done", "b-done"
    if s.startswith("optional"):
        return "optional", "b-opt"
    if s.startswith("partly"):
        return "partly done", "b-part"
    if s.startswith("deferred"):
        return "deferred", "b-defer"
    if s.startswith("likely"):
        return "to confirm", "b-part"
    return "to do", "b-todo"


def todo_bucket(t: dict) -> str:
    st = t["status"].lower()
    if st.startswith("done"):
        return "done"
    if st.startswith("optional"):
        return "optional"
    if st.startswith("deferred"):
        return "next"
    wk = re.search(r"\(week (\d+)", t["title"])
    if wk:
        return "this" if int(wk.group(1)) == 1 else "next"
    if "tip jar" in t["title"].lower():
        return "next"
    return "this"


BUCKETS = [("this", "This week"), ("next", "Next (weeks 2-6)"), ("optional", "Optional"), ("done", "Already done")]

# "Today" list: editorial pick of the 5 highest-leverage items, matched by title substring.
# Basis: 63 finished kits with 0 posted; the three highest affiliate priority scores; the one
# Cloudflare toggle verified still ON from the live site.
TODAY_PICKS = [
    ("Post the first Instagram content kit", "63 kits are finished and 0 are posted."),
    ("Affiliate signup: Runway", "highest affiliate priority score; 57 links already on the site."),
    ("Affiliate signup: Higgsfield", "second-highest priority score; 46 links on the site."),
    ("Affiliate signup: ElevenLabs", "third-highest priority score; easiest approval."),
    ("Email Address Obfuscation OFF", "verified still ON in the live home page HTML."),
]

AFF_APPLY = ("apply", "then apply", "request invite")


def aff_kind(action: str) -> str:
    a = action.lower()
    if a.startswith("apply only if") or a.startswith("defer until"):
        return "cond"
    if a == "apply" or "then apply" in a or a.startswith("request invite"):
        return "apply"
    return "other"


def similar(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a.lower(), b.lower()).ratio()


# ---------------------------------------------------------------- build
def build(status: dict, growth: dict, status_path: str, growth_path: str):
    H: list[str] = []   # html chunks (main)
    M: list[str] = []   # markdown chunks
    toc: list[tuple[str, str, list[tuple[str, str]]]] = []
    counts: dict[str, int] = {}
    unplaced: list[str] = []

    numbers = {n["metric"]: n for n in status["numbers"]}

    def num(metric_sub, field="value"):
        for k, v in numbers.items():
            if metric_sub.lower() in k.lower():
                return v.get(field)
        return None

    # ---------- 1. header
    sec = Section()
    title = "DejaViewed — 48-hour status, Oct 21–23 2026"
    win = status.get("window", "")
    entries, entries_before = num("Catalog entries"), num("Catalog entries", "before")
    visits = num("Baseline real visits")
    summary = (
        f"Between Oct 21 and Oct 23 2026 there were {len(status.get('commits', []))} commits to the site. "
        f"The catalog grew from {entries_before} to {entries} entries. "
        f"Every guide now ships a prompt system ({num('Prompt systems')} in total). "
        f"The site gained tool hubs ({num('Tool hubs')} indexed / noindex), {num('Comparisons')} comparison pages and {num('Best-of')} best-of lists. "
        f"Technical SEO work brought the live sitemap to {num('Sitemap URLs')} URLs and broken internal links to {num('Broken internal')}. "
        f"Nothing earns money yet: affiliate programs active = {num('Affiliate programs active')}, Instagram kits posted = {num('Instagram content kits')} (total kits, posted in brackets). "
        f"Traffic is small: {visits} real visits (7 days / 28 days), and Google Search Console shows 0 clicks and 0 impressions so far."
    )
    H.append(f'<header id="top"><h1>{html.escape(title)}</h1>'
             f'<div class="sub">Window: {html.escape(win)} · generated {html.escape(status.get("generated",""))} · site {a_tag(SITE, SITE)}</div>'
             f'<p class="lede">{h(summary, sec)}</p></header>')
    M.append(f"# {title}\n\nWindow: {win} · generated {status.get('generated','')} · site {SITE}\n\n{m(summary, Section())}\n")

    # numbers table
    sec_md = Section()
    H.append('<h2 id="numbers"><span class="num">1</span>The numbers</h2>')
    M.append("## 1. The numbers\n")
    toc.append(("numbers", "1. The numbers", []))
    footnotes = []
    rows_h, rows_m = [], []
    for n in status["numbers"]:
        val = n["value"]
        if isinstance(val, dict):
            val_h = "<br>".join(f'<span class="mono">{html.escape(k)}</span> {html.escape(str(v))}' for k, v in val.items())
            val_m = ", ".join(f"{k} {v}" for k, v in val.items())
        else:
            val_h, val_m = h(val, sec), m(val, sec_md, cell=True)
        fn_h = fn_m = ""
        if n.get("note"):
            footnotes.append(n["note"])
            i = len(footnotes)
            fn_h = f'<sup><a href="#fn{i}" id="fr{i}">[{i}]</a></sup>'
            fn_m = f" [^{i}]"
        before = n.get("before", "")
        rows_h.append(f"<tr><td>{h(n['metric'], sec)}{fn_h}</td><td class='mono'>{h(before, sec)}</td>"
                      f"<td class='mono'><b>{val_h}</b></td><td class='note'>{h(n.get('source',''), sec)}</td></tr>")
        rows_m.append(f"| {m(n['metric'], sec_md, cell=True)}{fn_m} | {m(before, sec_md, cell=True)} | **{m(val_m, None, cell=True) if isinstance(n['value'], dict) else val_m}** | {m(n.get('source',''), sec_md, cell=True)} |")
    H.append('<div class="tablewrap"><table><colgroup><col style="width:30%"><col style="width:22%"><col style="width:26%"><col style="width:22%"></colgroup>'
             '<thead><tr><th>Metric</th><th>Before</th><th>Now</th><th>Source</th></tr></thead><tbody>'
             + "".join(rows_h) + "</tbody></table></div>")
    H.append('<div class="fn">' + "".join(
        f'<p id="fn{i}">[{i}] {h(t, sec)} <a href="#fr{i}">back</a></p>' for i, t in enumerate(footnotes, 1)) + "</div>")
    M.append("| Metric | Before | Now | Source |\n|---|---|---|---|\n" + "\n".join(rows_m) + "\n")
    M.append("\n".join(f"[^{i}]: {m(t, sec_md)}" for i, t in enumerate(footnotes, 1)) + "\n")
    counts["numbers rows"] = len(status["numbers"])

    # ---------- 2. delivered
    sec, sec_md = Section(), Section()
    H.append('<h2 id="delivered"><span class="num">2</span>What was delivered</h2>')
    M.append("## 2. What was delivered\n")
    sub = []
    dl = status["delivered"]
    note = dl.get("_note_on_dates")
    if note:
        H.append(f'<p class="note">{h(note, sec)}</p>')
        M.append(f"> {m(note, sec_md)}\n")
    total_cards = 0
    for day in sorted(k for k, v in dl.items() if isinstance(v, list)):
        items = dl[day]
        aid = "day-" + day
        sub.append((aid, f"{day} ({len(items)})"))
        H.append(f'<h3 id="{aid}">{html.escape(day)} <span class="note">· {len(items)} items</span></h3><div class="cards">')
        M.append(f"### {day} ({len(items)} items)\n")
        for it in items:
            ev = it.get("evidence", {})
            ev_parts_h, ev_parts_m = [], []
            if ev.get("commits"):
                ev_parts_h.append("<b>commits</b> " + html.escape(", ".join(ev["commits"])))
                ev_parts_m.append("commits " + ", ".join(f"`{c}`" for c in ev["commits"]))
            if ev.get("files"):
                ev_parts_h.append("<b>files</b> " + html.escape(", ".join(ev["files"])))
                ev_parts_m.append("files " + ", ".join(f"`{f}`" for f in ev["files"]))
            if ev.get("counts"):
                ev_parts_h.append("<b>counts</b> " + html.escape(", ".join(f"{k}={v}" for k, v in ev["counts"].items())))
                ev_parts_m.append("counts " + ", ".join(f"{k}={v}" for k, v in ev["counts"].items()))
            links_h = " · ".join(live_link_html(u) for u in it.get("live_urls", []))
            links_m = " · ".join(live_link_md(u) for u in it.get("live_urls", []))
            H.append('<article class="card">'
                     f'<h4>{h(it["title"], sec)}</h4><p>{h(it["what_changed"], sec)}</p>'
                     + "".join(f'<div class="ev">{p}</div>' for p in ev_parts_h)
                     + (f'<div class="links">Live: {links_h}</div>' if links_h else "")
                     + "</article>")
            M.append(f"#### {m(it['title'], sec_md)}\n\n{m(it['what_changed'], sec_md)}\n\n"
                     + "".join(f"- Evidence: {p}\n" for p in ev_parts_m)
                     + (f"- Live: {links_m}\n" if links_m else "") + "\n")
            total_cards += 1
        H.append("</div>")
    toc.append(("delivered", "2. What was delivered", sub))
    counts["delivered cards"] = total_cards

    # ---------- 3. Victor's todo
    sec, sec_md = Section(), Section()
    H.append('<h2 id="todo"><span class="num">3</span>What you need to do</h2>')
    M.append("## 3. What you need to do\n")
    todos = status["victor_todo"]
    by_title = {t["title"]: t for t in todos}
    act_cmds = status.get("affiliate_activation", {}).get("commands", [])

    def find(sub_):
        for t in todos:
            if sub_.lower() in t["title"].lower():
                return t
        return None

    today_h, today_m = [], []
    for sub_, reason in TODAY_PICKS:
        t = find(sub_)
        if t:
            today_h.append(f'<li><a href="#todo-{slug(t["title"])}">{h(t["title"], sec)}</a> <span class="note">({html.escape(t["time_estimate"])}) {h(reason, sec)}</span></li>')
            today_m.append(f"1. [ ] {m(t['title'], sec_md)} ({t['time_estimate']}). {m(reason, sec_md)}")
    H.append('<div class="today"><b>Today</b> <span class="note">(the 5 highest-leverage items; picked from the list below by priority score and readiness)</span><ol>'
             + "".join(today_h) + "</ol></div>")
    M.append("**Today** (the 5 highest-leverage items):\n\n" + "\n".join(today_m) + "\n")
    sub = []
    ncards = 0
    for key, label in BUCKETS:
        items = [t for t in todos if todo_bucket(t) == key]
        if not items:
            continue
        aid = "todo-" + key
        sub.append((aid, f"{label} ({len(items)})"))
        H.append(f'<h3 id="{aid}">{html.escape(label)} <span class="note">· {len(items)}</span></h3>')
        M.append(f"### {label} ({len(items)})\n")
        for t in items:
            b, cls = badge_for_status(t["status"])
            k = "todo-" + slug(t["title"])
            checked = " checked" if b == "done" else ""
            steps_h = "".join(f"<li>{h(s, sec)}</li>" for s in t["steps"])
            steps_m = "\n".join(f"   {i}. {m(s, sec_md)}" for i, s in enumerate(t["steps"], 1))
            cmd_h = cmd_m = ""
            if t["commands"]:
                pre = html.escape("\n".join(t["commands"]))
                if act_cmds and t["commands"] == act_cmds:
                    cmd_h = (f'<details class="more"><summary>Activation commands (same block as in the '
                             f'<a href="#aff-activate">Affiliate timeline</a>)</summary><pre>{pre}</pre></details>')
                else:
                    cmd_h = f"<pre>{pre}</pre>"
                cmd_m = "\n   ```bash\n" + "\n".join("   " + c for c in t["commands"]) + "\n   ```\n"
            detail = "" if t["status"].lower() in ("todo", "done", "optional", "deferred") else \
                f'<div class="note">Status detail: {h(t["status"], sec)}</div>'
            H.append(f'<div class="todo" id="{k}"><div class="head"><input type="checkbox" data-k="{k}"{checked} aria-label="done">'
                     f'<h4>{h(t["title"], sec)}</h4><span class="badge {cls}">{b}</span></div>{detail}'
                     f'<p><b>Why:</b> {h(t["why"], sec)}</p><ol>{steps_h}</ol>{cmd_h}'
                     f'<div class="meta"><span><b>time</b>{html.escape(t["time_estimate"])}</span>'
                     f'<span><b>unblocks</b>{h(t["blocks"], sec)}</span></div></div>')
            M.append(f"- [{'x' if b == 'done' else ' '}] **{m(t['title'], sec_md)}** `{b}`"
                     + (f" (status: {m(t['status'], sec_md)})" if detail else "") + "\n"
                     f"   - Why: {m(t['why'], sec_md)}\n"
                     f"   - Steps:\n{steps_m}\n{cmd_m}"
                     f"   - Time: {t['time_estimate']}\n   - Unblocks: {m(t['blocks'], sec_md)}\n")
            ncards += 1
    toc.append(("todo", "3. What you need to do", sub))
    counts["todo items"] = ncards
    if ncards != len(todos):
        unplaced.append(f"victor_todo: {len(todos) - ncards} items not bucketed")

    # ---------- 4. affiliate timeline
    sec, sec_md = Section(), Section()
    aff = sorted(status["affiliate_timeline"], key=lambda x: (x["week"], x["priority"]))
    H.append('<h2 id="affiliates"><span class="num">4</span>Affiliate timeline</h2>')
    M.append("## 4. Affiliate timeline\n")
    H.append(f'<p class="lede">{h(f"{len(aff)} programs, grouped by the week to act. Every program is still pending. Links already sit on the site behind /go/<slug> redirects; activating a program swaps in the tracked link.", sec)}</p>')
    M.append(f"{len(aff)} programs, grouped by the week to act. Every program is still pending. Links already sit on the site behind `/go/<slug>` redirects; activating a program swaps in the tracked link.\n")
    # money paragraph
    basis = status.get("affiliate_traffic_basis", {})
    money = (f"Honest money estimate: {basis.get('assumption','')} "
             f"Basis: {basis.get('human_visits_28d')} human visits and {basis.get('human_pageviews_28d')} page views in 28 days, "
             f"{basis.get('human_visits_7d')} visits in the last 7 days, {basis.get('go_clicks_28d_recorded')} /go/ clicks recorded so far.")
    H.append(f'<div class="money">{h(money, sec)}</div>')
    M.append(f"> {m(money, sec_md)}\n")
    # shared rules + activation
    rule_sets = [set(a["placement_rules"]) for a in aff]
    shared_rules = [r for r in aff[0]["placement_rules"] if all(r in s for s in rule_sets)]
    act = status.get("affiliate_activation", {})
    same_steps = all(a["after_approval_steps"] == act.get("steps") for a in aff)
    same_cmds = all(a["after_approval_commands"] == act.get("commands") for a in aff)
    H.append('<h3 id="aff-activate">After approval: the same steps for every program</h3>'
             '<ol>' + "".join(f"<li>{h(s, sec)}</li>" for s in act.get("steps", [])) + "</ol>"
             f'<pre>{html.escape(chr(10).join(act.get("commands", [])))}</pre>'
             f'<p class="note">{h(act.get("note_on_order",""), sec)}</p>'
             + ("" if same_steps and same_cmds else '<p class="note">Some programs list different after-approval steps; see their detail rows.</p>'))
    M.append("### After approval: the same steps for every program\n\n"
             + "\n".join(f"{i}. {m(s, sec_md)}" for i, s in enumerate(act.get("steps", []), 1))
             + "\n\n```bash\n" + "\n".join(act.get("commands", [])) + "\n```\n\n" + m(act.get("note_on_order", ""), sec_md) + "\n")
    if shared_rules:
        H.append('<h3 id="aff-rules">Placement rules that apply to every program</h3><ul>'
                 + "".join(f"<li>{h(r, sec)}</li>" for r in shared_rules) + "</ul>")
        M.append("### Placement rules that apply to every program\n\n" + "\n".join(f"- {m(r, sec_md)}" for r in shared_rules) + "\n")
    sub = [("aff-activate", "After approval"), ("aff-gantt", "Week chart")]
    # gantt
    WEEKS = 8
    g_h = ['<div class="gantt" role="img" aria-label="Affiliate week chart"><div class="hd" style="text-align:left">Program</div>']
    g_h += [f'<div class="hd">W{w}{"*" if w > 6 else ""}</div>' for w in range(1, WEEKS + 1)]
    g_m = ["| Program | " + " | ".join(f"W{w}" for w in range(1, WEEKS + 1)) + " |", "|---|" + "---|" * WEEKS]
    for a in aff:
        kind = aff_kind(a["action"])
        start = a["week"]
        span = 3 if kind == "apply" else 1
        span = min(span, WEEKS - start + 1)
        lab = a["action"]
        g_h.append(f'<div class="lbl" title="{html.escape(a["tool"])}">{html.escape(a["tool"])}</div>')
        g_h.append(f'<div class="bar {kind}" style="grid-column:{start + 1} / span {span}" title="{html.escape(lab)}">{html.escape(lab)}</div>')
        # fill row remainder handled by grid auto placement: add empty spacer after bar
        rest = WEEKS - (start - 1 + span)
        cells = [""] * WEEKS
        for w in range(start - 1, start - 1 + span):
            cells[w] = "■" if kind == "apply" else ("▨" if kind == "cond" else "·")
        cells[start - 1] = cells[start - 1] + " " + lab
        g_m.append(f"| {a['tool']} | " + " | ".join(c.strip() for c in cells) + " |")
        if rest > 0:
            g_h.append(f'<div style="grid-column:{start + span + 1} / span {rest}"></div>')
    g_h.append("</div>")
    H.append('<h3 id="aff-gantt">Week chart</h3>'
             '<div class="legend"><span class="l1">apply in that week, then wait for approval (the steps say "typically days to 2 weeks")</span>'
             '<span class="l2">conditional: only once matching content exists</span><span class="l3">recheck / optional / skip / no action</span></div>'
             + "".join(g_h)
             + '<p class="note">W7 and W8 (*) show only the approval wait spilling past week 6. Bars are drawn from the week field; approval length is the generic estimate from the signup steps, not a per-program date.</p>')
    M.append("### Week chart\n\n■ = apply that week then wait for approval (typically days to 2 weeks); ▨ = conditional on content; · = recheck/optional/skip. W7-W8 show only approval spill-over.\n\n" + "\n".join(g_m) + "\n")
    # week tables
    for w in sorted({a["week"] for a in aff}):
        rows = [a for a in aff if a["week"] == w]
        aid = f"aff-w{w}"
        sub.append((aid, f"Week {w} ({len(rows)})"))
        H.append(f'<h3 id="{aid}"><span class="week">Week {w}</span> <span class="note">· {len(rows)} programs</span></h3>')
        M.append(f"### Week {w} ({len(rows)} programs)\n")
        H.append('<div class="tablewrap"><table><colgroup><col style="width:13%"><col style="width:16%"><col style="width:22%"><col style="width:12%"><col style="width:9%"><col style="width:16%"><col style="width:12%"></colgroup>'
                 '<thead><tr><th>Tool · action</th><th>Program / network</th><th>Commission</th><th>Payout minimum</th><th>On site</th><th>Expected monthly now</th><th>Sign up</th></tr></thead><tbody>')
        M.append("| Tool · action | Program / network | Commission | Payout minimum | On site | Expected monthly now | Sign up |\n|---|---|---|---|---|---|---|")
        for a in rows:
            su_h = a_tag(a["signup_url"], a["signup_url"].split("//", 1)[-1]) if a.get("signup_url") else '<span class="note">no signup URL on file</span>'
            su_m = f"[{a['signup_url'].split('//', 1)[-1]}]({a['signup_url']})" if a.get("signup_url") else "no signup URL on file"
            onsite = f"{a['links_on_site']} links on {a['distinct_pages_with_links']} pages"
            H.append(f"<tr><td><b>{html.escape(a['tool'])}</b><br><span class='note'>#{a['priority']} · {h(a['action'], sec)}</span></td>"
                     f"<td>{h(a['program'], sec)}<br><span class='note'>{h(a['network'], sec)}</span></td>"
                     f"<td>{h(a['commission'], sec)}</td><td>{h(a['payout_minimum'], sec)}</td>"
                     f"<td class='mono'>{onsite}<br>{a_tag(a['live_go_url'], '/go/' + a['slug'])}</td>"
                     f"<td>{h(a['expected_monthly_at_current_traffic'], sec)}</td><td>{su_h}</td></tr>")
            extra_rules = [r for r in a["placement_rules"] if r not in shared_rules]
            pages = a.get("pages_with_links", [])
            secs = ", ".join(f"{k} {v}" for k, v in a.get("pages_by_section", {}).items())
            more = (f"<div><b>Requirements:</b> {h(a['requirements'], sec)}</div>"
                    f"<div><b>Approval:</b> {h(a['approval_ease'], sec)}. {h(a['approval_notes'], sec)}</div>"
                    f"<div class='meta'><span><b>cookie</b>{h(a['cookie_days'], sec)}</span><span><b>research confidence</b>{h(a['research_confidence'], sec)}</span>"
                    f"<span><b>catalog entries tagged</b>{a['catalog_entries_tagged']} (tiers {html.escape(a['catalog_entry_tiers'] or '-')})</span>"
                    f"<span><b>priority score</b>{a['priority_score']['value']} = {html.escape(a['priority_score']['formula'])}</span>"
                    f"<span><b>pages by section</b>{html.escape(secs or '-')}</span></div>"
                    + (f"<div><b>Pages carrying links</b> ({len(pages)} listed of {a['distinct_pages_with_links']}): "
                       + ", ".join(a_tag(site_url(p), p) for p in pages) + "</div>" if pages else "")
                    + (f"<div><b>Program-specific placement rules:</b><ul>" + "".join(f"<li>{h(r, sec)}</li>" for r in extra_rules) + "</ul></div>" if extra_rules else "")
                    + (f"<div><b>Notes:</b><ul>" + "".join(f"<li>{h(n, sec)}</li>" for n in a["notes"]) + "</ul></div>" if a["notes"] else ""))
            H.append(f"<tr><td colspan='7' style='padding-top:0'><details class='more'><summary>{html.escape(a['tool'])}: requirements, rules, pages, notes</summary><div style='font-size:12.5px;padding:6px 0'>{more}</div></details></td></tr>")
            M.append(f"| **{a['tool']}** #{a['priority']} · {m(a['action'], sec_md, cell=True)} | {m(a['program'], sec_md, cell=True)} / {m(a['network'], sec_md, cell=True)} | "
                     f"{m(a['commission'], sec_md, cell=True)} | {m(a['payout_minimum'], sec_md, cell=True)} | {onsite}, [/go/{a['slug']}]({a['live_go_url']}) | "
                     f"{m(a['expected_monthly_at_current_traffic'], sec_md, cell=True)} | {su_m} |")
            M.append(f"| ↳ {a['tool']} details | *Requirements:* {m(a['requirements'], sec_md, cell=True)} *Approval:* {m(a['approval_ease'], sec_md, cell=True)}. {m(a['approval_notes'], sec_md, cell=True)} "
                     f"*Cookie:* {m(a['cookie_days'], None, cell=True)}. *Confidence:* {a['research_confidence']}. *Tagged entries:* {a['catalog_entries_tagged']} ({a['catalog_entry_tiers'] or '-'}). "
                     f"*Priority score:* {a['priority_score']['value']}. *Pages by section:* {secs or '-'}. "
                     + (f"*Pages:* " + ", ".join(f"[{p}]({site_url(p)})" for p in pages) + ". " if pages else "")
                     + (f"*Program rules:* " + " / ".join(m(r, sec_md, cell=True) for r in extra_rules) + ". " if extra_rules else "")
                     + (f"*Notes:* " + " / ".join(m(n, sec_md, cell=True) for n in a["notes"]) if a["notes"] else "")
                     + " |  |  |  |  |  |")
        H.append("</tbody></table></div>")
        M.append("")
    # skipped + go counts
    skipped = status.get("affiliate_skipped", [])
    if skipped:
        H.append('<h3 id="aff-skipped">Skipped</h3>' + "".join(f"<p><b>{html.escape(s['tool'])}</b>: {h(s['reason'], sec)}</p>" for s in skipped))
        M.append("### Skipped\n\n" + "\n".join(f"- **{s['tool']}**: {m(s['reason'], sec_md)}" for s in skipped) + "\n")
        sub.append(("aff-skipped", "Skipped"))
    glc = status.get("go_link_counts", {})
    if glc:
        H.append('<h3 id="aff-go">/go/ links on the site, by target</h3><div class="tablewrap"><table style="max-width:420px"><thead><tr><th>Target</th><th>Links</th></tr></thead><tbody>'
                 + "".join(f"<tr><td>{a_tag(site_url('/go/' + k), '/go/' + k)}</td><td class='n'>{v}</td></tr>" for k, v in glc.items()) + "</tbody></table></div>"
                 '<p class="note">/go/diy and /go/service are the site\'s own do-it-yourself and done-for-you links, present on every page footer.</p>')
        M.append("### /go/ links on the site, by target\n\n| Target | Links |\n|---|---|\n" + "\n".join(f"| [/go/{k}]({site_url('/go/' + k)}) | {v} |" for k, v in glc.items()) + "\n")
        sub.append(("aff-go", "/go/ link counts"))
    toc.append(("affiliates", "4. Affiliate timeline", sub))
    counts["affiliate rows"] = len(aff)

    # ---------- 5. campaigns
    sec, sec_md = Section(), Section()
    camps = sorted(growth["campaign_concepts"], key=lambda c: c["rank"])
    H.append('<h2 id="campaigns"><span class="num">5</span>Media campaigns from the archive</h2>')
    M.append("## 5. Media campaigns from the archive\n")
    H.append(f'<p class="lede">{len(camps)} campaign ideas built from the archive, ranked by expected value divided by effort (H/M/L value, S/M/L effort).</p><div class="cards">')
    M.append(f"{len(camps)} campaign ideas built from the archive, ranked by expected value divided by effort (H/M/L value, S/M/L effort).\n")
    for c in camps:
        ev_h = ", ".join(a_tag(site_url("/e/" + e), e) for e in c["evidence_from_corpus"])
        ev_m = ", ".join(f"[{e}]({site_url('/e/' + e)})" for e in c["evidence_from_corpus"])
        H.append(f'<article class="card"><h4><span class="mono" style="color:var(--accent)">#{c["rank"]}</span> {h(c["name"], sec)}</h4>'
                 f'<div><span class="badge">{h(c["format"], None, link=False)}</span> <span class="badge b-{c["effort"] if c["effort"] in "HML" else "M"}">effort {html.escape(c["effort"])}</span> '
                 f'<span class="badge b-{c["expected_value"]}">value {html.escape(c["expected_value"])}</span> <span class="note mono">score {c["score_ev_div_effort"]}</span></div>'
                 f'<p>{h(c["premise"], sec)}</p>'
                 f'<div class="meta"><span><b>cadence</b>{h(c["cadence"], sec)}</span></div>'
                 f'<div class="meta"><span><b>call to action target</b>{h(c["cta"], sec)}</span></div>'
                 f'<div class="ev"><b>source assets</b> ' + " · ".join(h(s, sec) for s in c["source_assets"]) + '</div>'
                 f'<div class="ev"><b>evidence entries</b> {ev_h}</div>'
                 f'<div style="margin-top:8px;font-size:13px"><b>First 3 posts</b><ol style="margin:4px 0;padding-left:20px">'
                 + "".join(f"<li>{h(p, sec)}</li>" for p in c["first_3_posts"]) + "</ol></div></article>")
        M.append(f"### #{c['rank']} {m(c['name'], sec_md)}\n\n- Format: {c['format']} · effort {c['effort']} · value {c['expected_value']} · score {c['score_ev_div_effort']}\n"
                 f"- Premise: {m(c['premise'], sec_md)}\n- Cadence: {m(c['cadence'], sec_md)}\n- Call to action target: {m(c['cta'], sec_md)}\n"
                 f"- Source assets: " + " · ".join(m(s, sec_md) for s in c["source_assets"]) + f"\n- Evidence entries: {ev_m}\n- First 3 posts:\n"
                 + "\n".join(f"  {i}. {m(p, sec_md)}" for i, p in enumerate(c["first_3_posts"], 1)) + "\n")
    H.append("</div>")
    qw = growth.get("quick_wins", [])
    H.append('<h3 id="quick-wins">Quick wins</h3><ul class="checks">'
             + "".join(f'<li><input type="checkbox" data-k="qw-{i}" aria-label="done"><span>{h(q, sec)}</span></li>' for i, q in enumerate(qw)) + "</ul>")
    M.append("### Quick wins\n\n" + "\n".join(f"- [ ] {m(q, sec_md)}" for q in qw) + "\n")
    toc.append(("campaigns", "5. Media campaigns", [("quick-wins", f"Quick wins ({len(qw)})")]))
    counts["campaign cards"] = len(camps)
    counts["quick wins"] = len(qw)

    # ---------- 6. archive knowledge
    sec, sec_md = Section(), Section()
    H.append('<h2 id="archive"><span class="num">6</span>What the archive already knows</h2>')
    M.append("## 6. What the archive already knows\n")
    H.append(f'<p class="lede">{h("Source: " + growth.get("source",""), sec)}</p><p class="note">{h("Method: " + growth.get("method",""), sec)}</p>')
    M.append(f"Source: {m(growth.get('source',''), sec_md)}\n\nMethod: {m(growth.get('method',''), sec_md)}\n")
    GROUP_NAMES = {
        "a_content_production": "a. Content production",
        "b_social_growth_tactics": "b. Social growth tactics",
        "c_automation_pipelines": "c. Automation pipelines",
        "d_seo_aeo": "d. Search-engine optimization (SEO) and answer-engine optimization (AEO)",
        "e_newsletter_email_community": "e. Newsletter, email and community",
        "f_monetization": "f. Monetization",
        "g_design_ux_brand": "g. Design, user experience (UX) and brand",
        "h_analytics_measurement": "h. Analytics and measurement",
    }
    sub = []
    n_assets = 0
    for gk, items in growth["growth_assets"].items():
        name = GROUP_NAMES.get(gk, gk)
        aid = "ga-" + gk.split("_")[0]
        sub.append((aid, f"{name.split(' (')[0] if gk != 'd_seo_aeo' else 'd. SEO and AEO'} ({len(items)})"))
        H.append(f'<h3 id="{aid}">{html.escape(name)} <span class="note">· {len(items)}</span></h3>'
                 '<div class="tablewrap"><table><colgroup><col style="width:22%"><col style="width:5%"><col style="width:11%"><col style="width:28%"><col style="width:28%"><col style="width:6%"></colgroup>'
                 '<thead><tr><th>Entry</th><th>Tier</th><th>Creator</th><th>What it teaches</th><th>How to apply here</th><th>Effort</th></tr></thead><tbody>')
        M.append(f"### {name} ({len(items)})\n\n| Entry | Tier | Creator | What it teaches | How to apply here | Effort |\n|---|---|---|---|---|---|")
        for it in items:
            url = site_url(it.get("url") or "/e/" + it["id"])
            tools = ", ".join(it.get("tools", []))
            H.append(f"<tr><td>{a_tag(url, it['title'])}" + (f"<div class='note mono'>{html.escape(tools)}</div>" if tools else "")
                     + f"</td><td><span class='tier t-{html.escape(it['tier'])}'>{html.escape(it['tier'])}</span></td><td>{html.escape(it['creator'])}</td>"
                     f"<td>{h(it['what_it_teaches'], sec)}</td><td>{h(it['how_to_apply_to_dejaviewed'], sec)}</td><td class='n'>{html.escape(it['effort'])}</td></tr>")
            M.append(f"| [{m(it['title'], None, link=False, cell=True)}]({url})" + (f"<br>tools: {m(tools, None, link=False, cell=True)}" if tools else "")
                     + f" | {it['tier']} | {m(it['creator'], None, link=False, cell=True)} | {m(it['what_it_teaches'], sec_md, cell=True)} | {m(it['how_to_apply_to_dejaviewed'], sec_md, cell=True)} | {it['effort']} |")
            n_assets += 1
        H.append("</tbody></table></div>")
        M.append("")
    gc = growth.get("counts", {})
    mismatch = {k: (gc.get(k), len(v)) for k, v in growth["growth_assets"].items() if gc.get(k) != len(v)}
    if mismatch:
        unplaced.append(f"growth counts mismatch vs rows: {mismatch}")
    rs = growth.get("repos_and_skills", [])
    H.append(f'<h3 id="repos">Repos and skills <span class="note">· {len(rs)}</span></h3>'
             '<div class="tablewrap"><table><colgroup><col style="width:15%"><col style="width:20%"><col style="width:23%"><col style="width:21%"><col style="width:21%"></colgroup>'
             '<thead><tr><th>Name</th><th>Repo or source entry</th><th>What it does</th><th>Use for us</th><th>Maturity</th></tr></thead><tbody>'
             + "".join(f"<tr><td><b>{html.escape(r['name'])}</b></td><td>{h(r['repo_url_or_source_entry'], sec)}</td><td>{h(r['what_it_does'], sec)}</td>"
                       f"<td>{h(r['use_for_us'], sec)}</td><td>{h(r['maturity_note'], sec)}</td></tr>" for r in rs)
             + "</tbody></table></div>")
    M.append(f"### Repos and skills ({len(rs)})\n\n| Name | Repo or source entry | What it does | Use for us | Maturity |\n|---|---|---|---|---|\n"
             + "\n".join(f"| **{m(r['name'], None, link=False, cell=True)}** | {m(r['repo_url_or_source_entry'], sec_md, cell=True)} | {m(r['what_it_does'], sec_md, cell=True)} | "
                         f"{m(r['use_for_us'], sec_md, cell=True)} | {m(r['maturity_note'], sec_md, cell=True)} |" for r in rs) + "\n")
    sub.append(("repos", f"Repos and skills ({len(rs)})"))
    toc.append(("archive", "6. What the archive knows", sub))
    counts["growth asset rows"] = n_assets
    counts["repos/skills rows"] = len(rs)

    # ---------- 7. Fable's queue
    sec, sec_md = Section(), Section()
    fq = status.get("fable_next", [])
    H.append('<h2 id="fable"><span class="num">7</span>Fable\'s queue</h2><p class="note">Work queued for Fable (the AI project manager on this repo), in the order listed.</p>'
             '<div class="tablewrap"><table><colgroup><col style="width:8%"><col style="width:30%"><col style="width:62%"></colgroup><thead><tr><th>Id</th><th>Item</th><th>Scope</th></tr></thead><tbody>'
             + "".join(f"<tr><td class='n'>{html.escape(str(f['id']))}</td><td><b>{h(f['item'], sec)}</b></td><td>{h(f['scope'], sec)}</td></tr>" for f in fq)
             + "</tbody></table></div>")
    M.append("## 7. Fable's queue\n\n| Id | Item | Scope |\n|---|---|---|\n"
             + "\n".join(f"| {f['id']} | **{m(f['item'], sec_md, cell=True)}** | {m(f['scope'], sec_md, cell=True)} |" for f in fq) + "\n")
    toc.append(("fable", "7. Fable's queue", []))
    counts["fable queue items"] = len(fq)

    # ---------- 8. risks
    sec, sec_md = Section(), Section()
    risks = [("status report", r) for r in status.get("risks_and_caveats", [])] + [("archive growth scan", r) for r in growth.get("caveats", [])]
    merged, dropped = [], []
    for src, r in risks:
        dup = next((x for x in merged if similar(x[1], r) > 0.8), None)
        if dup:
            dropped.append(r)
            if src not in dup[0]:
                dup[0].append(src)
        else:
            merged.append(([src], r))
    H.append('<h2 id="risks"><span class="num">8</span>Risks and caveats</h2>'
             f'<p class="note">{len(risks)} items from both files; {len(dropped)} near-duplicates merged.</p><ol>'
             + "".join(f"<li style='margin:6px 0'>{h(r, sec)} <span class='note mono'>[{', '.join(s)}]</span></li>" for s, r in merged) + "</ol>")
    M.append(f"## 8. Risks and caveats\n\n{len(risks)} items from both files; {len(dropped)} near-duplicates merged.\n\n"
             + "\n".join(f"{i}. {m(r, sec_md)} _[{', '.join(s)}]_" for i, (s, r) in enumerate(merged, 1)) + "\n")
    toc.append(("risks", "8. Risks and caveats", []))
    counts["risks (merged)"] = len(merged)

    # ---------- appendix: commits + sources (footer)
    commits = status.get("commits", [])
    H.append(f'<h2 id="commits"><span class="num">A</span>Commits in the window <span class="note">· {len(commits)}</span></h2>'
             '<details class="more"><summary>Show all commits</summary><div class="tablewrap"><table><colgroup><col style="width:10%"><col style="width:22%"><col style="width:68%"></colgroup><thead><tr><th>Hash</th><th>Date</th><th>Subject</th></tr></thead><tbody>'
             + "".join(f"<tr><td class='n'>{html.escape(c['hash'])}</td><td class='n'>{html.escape(c['date'])}</td><td>{html.escape(c['subject'])}</td></tr>" for c in commits)
             + "</tbody></table></div></details>")
    M.append(f"## A. Commits in the window ({len(commits)})\n\n| Hash | Date | Subject |\n|---|---|---|\n"
             + "\n".join(f"| `{c['hash']}` | {c['date']} | {m(c['subject'], None, link=False, cell=True)} |" for c in commits) + "\n")
    toc.append(("commits", "A. Commits", []))

    sources = status.get("sources", [])
    foot_h = (f'<footer>Generated {html.escape(status.get("generated",""))} (status) / {html.escape(growth.get("generated",""))} (archive scan). '
              f'Source files: <code>{html.escape(status_path)}</code>, <code>{html.escape(growth_path)}</code>. '
              f'Regenerate with <code>python3 scripts/build_report.py</code>.'
              f'<details class="more"><summary>Sources the status file was built from ({len(sources)})</summary><ul>'
              + "".join(f"<li><code>{html.escape(s)}</code></li>" for s in sources) + "</ul></details></footer>")
    H.append(foot_h)
    M.append(f"---\n\nGenerated {status.get('generated','')} (status) / {growth.get('generated','')} (archive scan). "
             f"Source files: `{status_path}`, `{growth_path}`. Regenerate with `python3 scripts/build_report.py`.\n\n"
             f"Sources the status file was built from:\n\n" + "\n".join(f"- `{s}`" for s in sources) + "\n")

    # ---------- assemble
    toc_html = '<nav class="toc" aria-label="Contents"><details id="toc-d" open><summary>Contents</summary><ol>'
    for aid, label, subs in toc:
        toc_html += f'<li><a href="#{aid}">{html.escape(label)}</a>'
        if subs:
            toc_html += "<ol>" + "".join(f'<li><a href="#{s}">{html.escape(l)}</a></li>' for s, l in subs) + "</ol>"
        toc_html += "</li>"
    toc_html += "</ol></details></nav>"
    doc = ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\">"
           "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
           "<meta name=\"robots\" content=\"noindex\"><link rel=\"icon\" href=\"data:,\">"
           f"<title>{html.escape(title)}</title><style>{CSS}</style></head>"
           f"<body><div class=\"layout\">{toc_html}<main>{''.join(H)}</main></div><script>{JS}</script></body></html>\n")
    md = "\n".join(M).rstrip() + "\n"
    return doc, md, counts, unplaced


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--date", default="2026-10-23")
    args = ap.parse_args()
    sp = f"data/reports/status_{args.date}.json"
    gp = f"data/reports/growth_assets_{args.date}.json"
    status = json.loads((ROOT / sp).read_text())
    growth = json.loads((ROOT / gp).read_text())

    global ID_RE
    e_dir = ROOT / "site" / "e"
    if e_dir.is_dir():
        ENTRY_IDS.update(p.stem for p in e_dir.glob("*.html") if len(p.stem) >= 8)
    for items in growth.get("growth_assets", {}).values():
        ENTRY_IDS.update(i["id"] for i in items)
    for c in growth.get("campaign_concepts", []):
        ENTRY_IDS.update(c.get("evidence_from_corpus", []))
    ID_RE = _id_re()

    doc, md, counts, unplaced = build(status, growth, sp, gp)
    out = ROOT / "docs" / "reports"
    out.mkdir(parents=True, exist_ok=True)
    hp = out / f"dejaviewed_status_{args.date}.html"
    mp = out / f"dejaviewed_status_{args.date}.md"
    hp.write_text(doc)
    mp.write_text(md)
    print(f"{hp.relative_to(ROOT)}  {hp.stat().st_size:,} bytes")
    print(f"{mp.relative_to(ROOT)}  {mp.stat().st_size:,} bytes")
    for k, v in counts.items():
        print(f"  {k}: {v}")
    for u in unplaced:
        print("  UNPLACED:", u)


if __name__ == "__main__":
    main()
