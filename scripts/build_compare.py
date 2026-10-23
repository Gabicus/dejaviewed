#!/usr/bin/env python3
"""Dated comparison, best-of and library pages rendered from authored data files.

    data/compare/<slug>.json  ->  site/compare/<slug>.html   (dir "compare")
                                  site/best/<slug>.html      (dir "best")
                                  site/<slug>.html           (dir "root", e.g. system-prompts)
    + site/compare/index.html and site/best/index.html listing every page.

Every page: breadcrumb, H1, the direct answer first (AEO), a "Last verified <date>" line, the
fact/comparison table, sections, a verdict, a Sources list at the bottom. Every corpus claim links
/e/<id>; every external fact cites a numbered source ([[s:key]]) that carries url + accessed date.

Inline markup inside any authored string (escaped first, then expanded):
    [[e:ID]] / [[e:ID|label]]  -> link to the entry page (label defaults to the entry title)
    [[s:key]]                  -> numbered superscript link to the Sources list
    [[t:slug|label]]           -> /tools/<slug> link when site/tools/<slug>.html exists, plain label otherwise
    [[go:slug|label]]          -> /go/<slug> button when slug is in data/monetize/affiliates.json
    [label](https://...)       -> external link (rel=noopener)   [label](/path) -> internal link
    `code`  **bold**

Page kinds (data "kind"): "compare" | "best" | "library" (system-prompts; built from
data/prompt_systems.json). Counts in "corpus" blocks are computed from site/catalog.json at build time.

The head carries only <title>, <meta name="description"> and canonical; build_seo.py adds the
seo block for compare/ and best/ afterwards. Links are root-absolute clean URLs.

Usage:  python3 scripts/build_compare.py          # write pages
        python3 scripts/build_compare.py --check  # exit 1 if any page would change or data is invalid
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DATA = ROOT / "data" / "compare"
CATALOG = SITE / "catalog.json"
AFFILIATES = ROOT / "data" / "monetize" / "affiliates.json"
PACKS = ROOT / "data" / "prompt_systems.json"
DIVES = ROOT / "data" / "deep_dives.json"
GAPS = ROOT / "data" / "seo" / "content_gaps_2026-10-22.json"
SITE_URL = "https://dejaviewed.dev"
MARK = "<!-- gen:build_compare -->"
TIER_ORDER = {"S": 0, "A": 1, "B": 2, "C": 3}
DESC_MAX = 155   # build_seo.clip_sentence limit
TITLE_MAX = 65

sys.path.insert(0, str(ROOT / "scripts"))
try:  # one copy-button handler site-wide
    from prompt_systems import COPY_JS
except Exception:  # pragma: no cover - fallback keeps the page working if the import breaks
    COPY_JS = ("<script>document.addEventListener('click',e=>{const b=e.target.closest('.ps-copy,.md-copy');if(!b)return;"
               "const pre=b.parentElement.querySelector('pre');navigator.clipboard.writeText(pre.innerText).then(()=>"
               "{b.textContent='Copied';setTimeout(()=>b.textContent='Copy',1200)});});</script>")


def esc(x) -> str:
    return html.escape(str(x if x is not None else ""), quote=True)


def safe_slug(rid: str) -> str:
    """Must match render_entries.safe_slug (entry page filename)."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in rid)


def clip(text: str, n: int) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= n:
        return text
    return text[:n].rsplit(" ", 1)[0].rstrip(",.;:—-") + "…"


def page_url(d: dict) -> str:
    return {"compare": f"/compare/{d['slug']}", "best": f"/best/{d['slug']}"}.get(d["dir"], f"/{d['slug']}")


def page_file(d: dict) -> Path:
    return {"compare": SITE / "compare", "best": SITE / "best"}.get(d["dir"], SITE) / f"{d['slug']}.html"


# ─────────────────────────────────────────────────────────── context ──
class Ctx:
    def __init__(self):
        cat = json.loads(CATALOG.read_text(encoding="utf-8"))
        self.entries = {e["id"]: e for e in cat.get("entries", []) if e.get("id")}
        self.aff = json.loads(AFFILIATES.read_text(encoding="utf-8")) if AFFILIATES.exists() else {}
        self.errors: list[str] = []
        self.cited: set[str] = set()
        self.cited_auto: set[str] = set()
        self.n_packs = 0
        self.src_index: dict[str, int] = {}
        self.src_used: set[str] = set()

    def tool_page(self, slug: str) -> bool:
        return (SITE / "tools" / f"{slug}.html").is_file()

    def entry_ok(self, rid: str) -> bool:
        if rid not in self.entries:
            self.errors.append(f"unknown entry id {rid!r}")
            return False
        if not (SITE / "e" / f"{safe_slug(rid)}.html").is_file():
            self.errors.append(f"entry page missing for {rid!r}")
        return True


def entry_link(c: Ctx, rid: str, label: str | None = None, auto: bool = False) -> str:
    """auto=True: example picked by a computed corpus query (not part of the authored entries_cited)."""
    if not c.entry_ok(rid):
        return esc(label or rid)
    (c.cited_auto if auto else c.cited).add(rid)
    e = c.entries[rid]
    lab = label or clip(e.get("title") or rid, 70)
    tier = (e.get("tier") or "C").upper()
    return f'<a class="ent" href="/e/{esc(safe_slug(rid))}" title="{esc(tier)}-tier entry">{esc(lab)}</a>'


INLINE_RE = re.compile(
    r"\[\[(e|s|t|go):([^\]|]+)(?:\|([^\]]+))?\]\]"     # [[kind:arg|label]]
    r"|\[([^\]]+)\]\(((?:https?://|/)[^)\s]+)\)"        # [label](url)
    r"|`([^`]+)`"                                        # `code`
    r"|\*\*([^*]+)\*\*")                                 # **bold**


def inline(c: Ctx, raw: str) -> str:
    """Escape authored text, then expand the inline markup (markup chars survive html.escape)."""
    s = esc(raw)

    def rep(m: re.Match) -> str:
        kind, arg, lab = m.group(1), m.group(2), m.group(3)
        if kind == "e":
            return entry_link(c, html.unescape(arg).strip(), html.unescape(lab) if lab else None)
        if kind == "s":
            key = arg.strip()
            if key not in c.src_index:
                c.errors.append(f"unknown source key {key!r}")
                return ""
            c.src_used.add(key)
            n = c.src_index[key]
            return f'<sup class="src"><a href="#src-{n}" aria-label="source {n}">[{n}]</a></sup>'
        if kind == "t":
            slug, label = arg.strip(), (lab or arg).strip()
            return f'<a href="/tools/{esc(slug)}">{label}</a>' if c.tool_page(slug) else label
        if kind == "go":
            slug, label = arg.strip(), (lab or arg).strip()
            return go_button(c, slug, label)
        if m.group(4):
            url = html.unescape(m.group(5))
            ext = url.startswith("http")
            return (f'<a href="{esc(url)}"' + (' rel="noopener"' if ext else "") + f">{m.group(4)}</a>")
        if m.group(6):
            return f"<code>{m.group(6)}</code>"
        return f"<strong>{m.group(7)}</strong>"

    return INLINE_RE.sub(rep, s)


def go_button(c: Ctx, slug: str, label: str) -> str:
    """class="go cta" (not bare "go"): build_monetize.LINK_RE strips exact class="go" links on every page
    it does not re-link itself, so these generator-owned buttons use a second class to survive it.
    rel and the disclosure follow the program's live status, same as build_monetize.link()."""
    a = c.aff.get(slug)
    if a:
        if a.get("status") == "active":
            return (f'<a class="go cta" href="/go/{esc(slug)}" rel="sponsored nofollow noopener">{label}</a>'
                    f'<sup class="aff">affiliate link</sup>')
        return f'<a class="go cta" href="/go/{esc(slug)}" rel="noopener">{label}</a>'
    c.errors.append(f"go slug {slug!r} not in affiliates.json")
    return label


def plain(s: str) -> str:
    s = re.sub(r"\[\[(?:e|s|t|go):[^\]|]+\|([^\]]+)\]\]", r"\1", s)
    s = re.sub(r"\[\[(?:e|s|t|go):[^\]]+\]\]", "", s)
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    return re.sub(r"[`*]", "", s).strip()


# ─────────────────────────────────────────────────────────── corpus ──
ENTRY_FIELDS = ("title", "summary", "caption", "transcript", "tools", "tags", "takeaways", "repos")


CORE_FIELDS = ("title", "summary", "tools", "tags", "takeaways")   # themes: what the entry is about, not every word said


def entry_text(e: dict, fields=ENTRY_FIELDS) -> str:
    out = []
    for f in fields:
        v = e.get(f)
        out.append(" ".join(map(str, v)) if isinstance(v, list) else str(v or ""))
    return " ".join(out)


def match_ids(c: Ctx, pattern: str, exclude: str | None = None) -> list[str]:
    rx = re.compile(pattern, re.I)
    ex = re.compile(exclude, re.I) if exclude else None
    out = []
    for rid, e in c.entries.items():
        t = entry_text(e)
        if rx.search(t) and not (ex and ex.search(t)):
            out.append(rid)
    return out


def tier_sort(c: Ctx, ids) -> list[str]:
    return sorted(ids, key=lambda i: (TIER_ORDER.get((c.entries[i].get("tier") or "C").upper(), 9),
                                      "".join(chr(0x10FFFF - ord(ch)) for ch in str(c.entries[i].get("date") or ""))))


def tier_mix(c: Ctx, ids) -> str:
    t = Counter((c.entries[i].get("tier") or "C").upper() for i in ids)
    return " · ".join(f"{t[k]} {k}" for k in "SABC" if t.get(k))


def render_corpus(c: Ctx, block: dict) -> str:
    """Computed counts: per group a pattern over the catalog, plus theme sub-counts with examples."""
    rows, union = [], set()
    for g in block["groups"]:
        ids = match_ids(c, g["pattern"], g.get("exclude"))
        union |= set(ids)
        themes = []
        for th in g.get("themes", []):
            tids = tier_sort(c, [i for i in ids if re.search(th["pattern"], entry_text(c.entries[i], CORE_FIELDS), re.I)])
            if not tids:
                continue
            # examples: entries whose title names the theme first, then by tier and recency
            ranked = sorted(tids, key=lambda i: not re.search(th["pattern"], c.entries[i].get("title") or "", re.I))
            ex = ", ".join(entry_link(c, i, auto=True) for i in ranked[:th.get("examples", 2)])
            themes.append(f"<li><strong>{esc(th['label'])}</strong> <span class=\"n\">{len(tids)}</span> e.g. {ex}</li>")
        rows.append(f'<div class="cg"><h3>{inline(c, g["label"])} <span class="n">{len(ids)} entries</span></h3>'
                    f'<p class="mix">{esc(tier_mix(c, ids))}</p>'
                    + (f'<ul class="themes">{"".join(themes)}</ul>' if themes else "")
                    + (f'<p>{inline(c, g["note"])}</p>' if g.get("note") else "") + "</div>")
    lead = block.get("lead", "").replace("{union}", str(len(union)))
    return (f'<p>{inline(c, lead)}</p>' if lead else "") + f'<div class="corpus">{"".join(rows)}</div>' \
        + (f'<p class="fine">{inline(c, block["method"])}</p>' if block.get("method") else "")


# ─────────────────────────────────────────────────────────── blocks ──
def render_table(c: Ctx, t: dict) -> str:
    head = "".join(f"<th scope=\"col\">{inline(c, h)}</th>" for h in t["columns"])
    body = []
    for r in t["rows"]:
        cells = [f'<th scope="row">{inline(c, r[0])}</th>'] + [f"<td>{inline(c, x)}</td>" for x in r[1:]]
        body.append("<tr>" + "".join(cells) + "</tr>")
    cap = f"<caption>{inline(c, t['caption'])}</caption>" if t.get("caption") else ""
    note = f'<p class="fine">{inline(c, t["note"])}</p>' if t.get("note") else ""
    return f'<div class="tw"><table>{cap}<thead><tr>{head}</tr></thead><tbody>{"".join(body)}</tbody></table></div>{note}'


VERDICT_LABEL = {"keep": "Keep", "try": "Try", "skip": "Skip"}
STATUS_LABEL = {"maintained": "Maintained", "slow": "Slow updates", "stale": "Stale", "archived": "Archived",
                "unverified": "Unverified", "official-hosted": "Official, hosted", "n/a": "Pattern"}


def pre_block(text: str) -> str:
    return f'<div class="ps-pre"><button class="md-copy ps-copy">Copy</button><pre>{esc(text)}</pre></div>'


def item_anchor(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")[:60]


def render_item(c: Ctx, it: dict) -> str:
    v = it.get("verdict", "try")
    st = it.get("status", "n/a")
    ents = tier_sort(c, [i for i in it.get("entries", []) if c.entry_ok(i)])
    elinks = "; ".join(f'{entry_link(c, i)} <span class="tb">{esc((c.entries[i].get("tier") or "C").upper())}</span>'
                       for i in ents)
    meta = []
    if it.get("repo"):
        meta.append(f'<a href="https://github.com/{esc(it["repo"])}" rel="noopener">github.com/{esc(it["repo"])}</a>')
    elif it.get("docs_url"):
        meta.append(f'<a href="{esc(it["docs_url"])}" rel="noopener">official docs</a>')
    if it.get("stars") is not None and not it.get("hide_stars"):
        meta.append(f'{int(it["stars"]):,} stars')
    if it.get("last_commit"):
        meta.append(f'last commit {esc(it["last_commit"])}')
    if it.get("archived"):
        meta.append("archived on GitHub")
    if it.get("license"):
        meta.append(esc(it["license"]))
    if it.get("checked") and (it.get("repo") or it.get("docs_url")):
        meta.append(f'checked {esc(it["checked"])}')
    what = it.get("what") or it.get("unlocks") or ""
    inst = ""
    if it.get("install"):
        src = it.get("install_source", "")
        src_html = ""
        if src:
            src_html = (f' (from {entry_link(c, src, "the entry")})' if src in c.entries
                        else f' (from <a href="{esc(src)}" rel="noopener">source</a>)' if src.startswith("http") else "")
        inst = f'<p class="inst">Install{src_html}:</p>' + pre_block(it["install"])
    kind = it.get("kind") or ("official" if it.get("official") else "")
    return (f'<article class="item" id="{esc(item_anchor(it["name"]))}">'
            f'<h3>{esc(it["name"])}</h3>'
            f'<p class="badges"><span class="vd v-{esc(v)}">{esc(VERDICT_LABEL.get(v, v))}</span>'
            f'<span class="st s-{esc(st)}">{esc(STATUS_LABEL.get(st, st))}</span>'
            + (f'<span class="kd">{esc(kind)}</span>' if kind else "") + "</p>"
            f'<p>{inline(c, what)}</p>'
            f'<p class="why"><strong>Why {esc(VERDICT_LABEL.get(v, v).lower())}:</strong> {inline(c, it.get("reason", ""))}</p>'
            + (f'<p class="cov">Covered in: {elinks}</p>' if elinks else "")
            + (f'<p class="rm">{" · ".join(meta)}</p>' if meta else "")
            + inst + "</article>")


def render_items_summary(c: Ctx, items: list[dict], what_col: str) -> str:
    rows = []
    for it in items:
        v, st = it.get("verdict", "try"), it.get("status", "n/a")
        rows.append(f'<tr><th scope="row"><a href="#{esc(item_anchor(it["name"]))}">{esc(it["name"])}</a></th>'
                    f'<td><span class="vd v-{esc(v)}">{esc(VERDICT_LABEL.get(v, v))}</span></td>'
                    f'<td>{esc(STATUS_LABEL.get(st, st))}</td><td>{len(it.get("entries", []))}</td>'
                    f'<td>{esc(clip(plain(it.get("what") or it.get("unlocks") or ""), 90))}</td></tr>')
    return (f'<div class="tw"><table><thead><tr><th scope="col">Name</th><th scope="col">Verdict</th>'
            f'<th scope="col">Status</th><th scope="col">Entries</th><th scope="col">{esc(what_col)}</th></tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table></div>')


def render_section(c: Ctx, s: dict, d: dict) -> str:
    out = [f'<section id="{esc(s.get("id") or item_anchor(s["h2"]))}"><h2>{inline(c, s["h2"])}</h2>']
    for p in s.get("paras", []):
        out.append(f"<p>{inline(c, p)}</p>")
    if s.get("list"):
        out.append("<ul>" + "".join(f"<li>{inline(c, x)}</li>" for x in s["list"]) + "</ul>")
    if s.get("corpus"):
        out.append(render_corpus(c, s["corpus"]))
    if s.get("table"):
        out.append(render_table(c, s["table"]))
    if s.get("evidence"):   # [{label, entries:[ids], text}] per tool
        for ev in s["evidence"]:
            ids = tier_sort(c, [i for i in ev["entries"] if c.entry_ok(i)])
            out.append(f'<div class="ev"><h3>{inline(c, ev["label"])} <span class="n">{len(ids)} entries</span></h3>'
                       f'<p class="mix">{esc(tier_mix(c, ids))}</p><p>{inline(c, ev["text"])}</p>'
                       f'<p class="fine">All {len(ids)}: {"; ".join(entry_link(c, i) for i in ids)}</p></div>')
    if s.get("go"):
        btns = [go_button(c, g["slug"], esc(g["label"])) if g["slug"] in c.aff
                else f'<a class="go off" href="{esc(g["url"])}" rel="noopener">{esc(g["label"])}</a>' for g in s["go"]]
        out.append(f'<p class="gos">{" ".join(btns)}</p>')
        if s.get("go_note"):
            out.append(f'<p class="fine">{inline(c, s["go_note"])}</p>')
    if s.get("items"):
        if s.get("summary_table", True):
            out.append(render_items_summary(c, s["items"], s.get("what_col", "What it does")))
        out.extend(render_item(c, it) for it in s["items"])
    out.append("</section>")
    return "\n".join(out)


# ─────────────────────────────────────────────────────────── page ──
CSS = """
main.cmp{max-width:960px;margin:24px auto 40px;padding:0 20px}
.cmp h1{font:800 30px/1.2 Inter,system-ui;margin:8px 0 12px;color:var(--text)}
.cmp h2{font:800 20px/1.3 Inter,system-ui;color:var(--text);margin:34px 0 10px}
.cmp h3{font:700 16px/1.35 Inter,system-ui;color:var(--text);margin:18px 0 6px}
.cmp p,.cmp li{color:var(--text-dim);font-size:14.5px;line-height:1.65}
.cmp a{color:var(--accent);text-decoration:none}.cmp a:hover{text-decoration:underline}
.cmp code{background:rgba(255,255,255,.07);padding:1px 5px;border-radius:4px;font:12.5px 'JetBrains Mono',ui-monospace,monospace;color:var(--text)}
nav.crumbs{font-size:12px;color:var(--text-mute);margin-bottom:6px}
nav.crumbs a{color:var(--text-mute)}nav.crumbs .sep{margin:0 6px;opacity:.6}
.answer{background:var(--panel);border:1px solid var(--border);border-left:3px solid var(--accent);border-radius:10px;padding:14px 16px;margin:6px 0 10px}
.answer p{margin:0;color:var(--text);font-size:15.5px}
.verified{font:500 12px/1.6 'JetBrains Mono',ui-monospace,monospace;color:var(--text-mute);margin:0 0 6px}
.toc{font-size:13px;color:var(--text-mute);margin:8px 0 0}.toc a{margin-right:12px}
.tw{overflow-x:auto;margin:12px 0}
.cmp table{border-collapse:collapse;width:100%;font-size:13.5px;min-width:560px}
.cmp caption{text-align:left;color:var(--text-mute);font-size:12px;padding-bottom:6px}
.cmp th,.cmp td{border:1px solid var(--border);padding:8px 10px;text-align:left;vertical-align:top;color:var(--text-dim);line-height:1.5}
.cmp thead th{background:var(--panel);color:var(--text);font-weight:700}
.cmp tbody th{color:var(--text);font-weight:600}
.fine{font-size:12.5px!important;color:var(--text-mute)!important}
sup.src{font-size:10px;margin-left:1px}
.n{font:600 11px/1 'JetBrains Mono',ui-monospace,monospace;color:var(--text-mute);margin-left:6px}
.mix{font:500 11.5px/1.5 'JetBrains Mono',ui-monospace,monospace!important;color:var(--text-mute)!important;margin:0}
.corpus{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
.cg,.ev,.item{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:12px 16px;margin:10px 0}
.cg h3,.ev h3{margin-top:2px}.themes{padding-left:18px;margin:8px 0 0}.themes li{font-size:13px}
.item h3{margin:2px 0 6px}.item p{margin:6px 0}
.badges{display:flex;gap:6px;flex-wrap:wrap}
.vd,.st,.kd,.tb{display:inline-block;font:700 10.5px/18px Inter,system-ui;padding:0 8px;border-radius:999px;border:1px solid var(--border);color:var(--text-mute)}
.tb{padding:0 5px;font-size:9.5px;line-height:15px}
.v-keep{color:#4ade80;border-color:rgba(74,222,128,.45);background:rgba(74,222,128,.1)}
.v-try{color:#60a5fa;border-color:rgba(96,165,250,.45);background:rgba(96,165,250,.1)}
.v-skip{color:#f87171;border-color:rgba(248,113,113,.45);background:rgba(248,113,113,.1)}
.s-archived,.s-stale{color:#f87171}.s-maintained{color:#4ade80}.s-slow,.s-unverified{color:#fbbf24}
.rm{font:500 11.5px/1.6 'JetBrains Mono',ui-monospace,monospace!important;color:var(--text-mute)!important}
.inst{font-size:12.5px!important;margin-bottom:0!important}
.gos{display:flex;gap:10px;flex-wrap:wrap}
a.go{display:inline-block;padding:7px 14px;border-radius:8px;border:1px solid var(--accent);color:var(--text);font-weight:700;font-size:13px}
a.go.off{border-color:var(--border)}a.go:hover{background:rgba(167,139,250,.12);text-decoration:none}
.verdict{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:6px 16px 12px}
.gaps li{color:var(--text-dim)}
ol.sources{padding-left:22px}ol.sources li{font-size:13px;word-break:break-word}
.ps-pre{position:relative;margin:8px 0 12px}
.ps-pre pre{background:rgba(0,0,0,.55);border:1px solid var(--border);padding:12px 14px;border-radius:8px;overflow-x:auto;white-space:pre-wrap;word-break:break-word;font-size:12.5px;line-height:1.55;color:var(--text);margin:0}
.ps-copy{position:absolute;top:8px;right:8px;font:700 11px/1 'JetBrains Mono',monospace;padding:5px 9px;border-radius:6px;border:1px solid var(--border);background:var(--panel);color:var(--text-dim);cursor:pointer}
.ps-copy:hover{color:#fff;border-color:var(--border-hi)}
.pgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:12px;list-style:none;padding:0}
.pgrid li a{display:block;background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:14px 16px;height:100%;box-sizing:border-box;color:var(--text)}
.pgrid li a:hover{border-color:var(--accent);text-decoration:none}
.pgrid h3{margin:0 0 4px}.pgrid p{font-size:13px;margin:4px 0 0}
.spk{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:12px 16px;margin:12px 0}
.spk h3{margin:2px 0 4px}.spk .role{color:var(--text);font-size:14px}
.more{margin-top:22px;font-size:13px;color:var(--text-mute)}.more a{margin-right:14px}
"""


def head(title: str, desc: str, canonical: str) -> str:
    return (f'<!doctype html>\n<html lang="en"><head>\n<meta charset="utf-8">\n<title>{esc(title)}</title>\n'
            f'<meta name="description" content="{esc(desc)}">\n<link rel="canonical" href="{esc(canonical)}">\n'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            f'<link rel="stylesheet" href="/shared.css">\n<script src="/shared.js"></script>\n'
            f"<style>{CSS}</style>\n</head><body>\n{MARK}\n"
            f"<script>DV.mountHeader(document.body, 'compare');</script>\n")


def crumbs(parts: list[tuple[str, str | None]]) -> str:
    out = []
    for label, href in parts:
        out.append(f'<a href="{esc(href)}">{esc(label)}</a>' if href else f'<span aria-current="page">{esc(label)}</span>')
    return f'<nav class="crumbs" aria-label="Breadcrumb">{"<span class=sep>›</span>".join(out)}</nav>'


DIR_CRUMB = {"compare": ("Compare", "/compare/"), "best": ("Best of", "/best/"), "root": ("Compare", "/compare/")}


def render_sources(c: Ctx, d: dict) -> str:
    lis = []
    for s in d.get("sources", []):
        n = c.src_index[s["key"]]
        rel = ' rel="noopener"' if s["url"].startswith("http") else ""
        lis.append(f'<li id="src-{n}"><a href="{esc(s["url"])}"{rel}>{esc(s["title"])}</a>'
                   f' <span class="fine">accessed {esc(s["accessed"])}</span></li>')
    return f'<section id="sources"><h2>Sources</h2><ol class="sources">{"".join(lis)}</ol></section>' if lis else ""


def body_text_words(html_text: str) -> int:
    t = re.sub(r"<(script|style)\b.*?</\1>", " ", html_text, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    return len(html.unescape(t).split())


def render_page(c: Ctx, d: dict, extra_html: str = "") -> str:
    c.src_index = {s["key"]: i + 1 for i, s in enumerate(d.get("sources", []))}
    c.src_used, c.cited, c.cited_auto = set(), set(), set()
    label, href = DIR_CRUMB[d["dir"]]
    crumb = crumbs([("Home", "/"), (label, href), (d.get("crumb") or d["h1"], None)])
    parts = [f'<main class="cmp">', crumb, f'<h1>{esc(d["h1"])}</h1>',
             f'<div class="answer"><p>{inline(c, d["answer"])}</p></div>',
             f'<p class="verified">Last verified {esc(d["last_verified"])}'
             + (f' · {inline(c, d["scope_note"])}' if d.get("scope_note") else "") + "</p>"]
    secs = d.get("sections", [])
    toc = [(s.get("id") or item_anchor(s["h2"]), plain(s["h2"])) for s in secs]
    if d.get("verdict"):
        toc.append(("verdict", d["verdict"].get("h2", "Verdict")))
    if len(toc) > 2:
        parts.append('<p class="toc">' + "".join(f'<a href="#{esc(a)}">{esc(t)}</a>' for a, t in toc) + "</p>")
    for p in d.get("intro", []):
        parts.append(f"<p>{inline(c, p)}</p>")
    if d.get("table"):
        parts.append(render_table(c, d["table"]))
    parts.append(extra_html)
    for s in secs:
        parts.append(render_section(c, s, d))
    if d.get("verdict"):
        v = d["verdict"]
        vh = [f'<section id="verdict"><h2>{esc(v.get("h2", "Verdict"))}</h2><div class="verdict">']
        vh += [f"<p>{inline(c, p)}</p>" for p in v.get("paras", [])]
        if v.get("table"):
            vh.append(render_table(c, v["table"]))
        vh.append("</div></section>")
        parts.append("".join(vh))
    if d.get("unverified"):
        parts.append('<section id="not-verified"><h2>What we could not verify</h2><ul class="gaps">'
                     + "".join(f"<li>{inline(c, x)}</li>" for x in d["unverified"]) + "</ul></section>")
    if d.get("related"):
        parts.append('<p class="more">' + "".join(f'<a href="{esc(u)}">{esc(t)}</a>' for t, u in d["related"]) + "</p>")
    parts.append(render_sources(c, d))
    parts.append("</main>\n" + COPY_JS + "\n</body></html>\n")
    unused = set(c.src_index) - c.src_used
    if unused:
        c.errors.append(f"{d['slug']}: sources never cited: {sorted(unused)}")
    declared = set(d.get("entries_cited", []))
    if declared != c.cited:
        miss, extra = sorted(c.cited - declared), sorted(declared - c.cited)
        c.errors.append(f"{d['slug']}: entries_cited out of sync (add {miss[:6]}{'…' if len(miss) > 6 else ''}, "
                        f"drop {extra[:6]})")
    return head(d["title"], d["description"], SITE_URL + page_url(d)) + "\n".join(p for p in parts if p)


# ─────────────────────────────────────────────────── system prompts ──
ROLE_RE = re.compile(r"^\s*ROLE(?:\s+AND\s+STANCE)?\s*:?\s*\n?(.*?)(?:\n\s*\n|\n[A-Z][A-Z /&-]{3,}:?\s*\n)", re.S)


def role_line(one_shot: str) -> str:
    m = ROLE_RE.search(one_shot or "")
    text = m.group(1) if m else (one_shot or "")
    text = " ".join(text.split())
    sents = re.split(r"(?<=[.!?])\s+", text)
    out = " ".join(sents[:2])
    return clip(out, 320)


def guide_titles() -> dict[str, str]:
    out = {}
    for p in (SITE / "guides").glob("*.html"):
        m = re.search(r"<title>(.*?)</title>", p.read_text(encoding="utf-8", errors="replace"), re.S)
        if m:
            t = html.unescape(m.group(1)).strip()
            out[p.stem] = re.sub(r"\s*·\s*DejaViewed\s*$", "", t)
    return out


def pillar_of(slug: str, pillars: list[dict], overrides: dict[str, str], keywords=(), mission: str = "") -> str:
    """override > best rank in a pillar's top_dive_slugs > first keyword rule on slug + mission > "other"."""
    if slug in overrides:
        return overrides[slug]
    best, rank = None, 999
    for p in pillars:
        tops = p.get("stats", {}).get("top_dive_slugs", [])
        if slug in tops and tops.index(slug) < rank:
            best, rank = p["key"], tops.index(slug)
    if best:
        return best
    for rx, key in keywords:
        if re.search(rx, f"{slug} {mission}", re.I):
            return key
    return "other"


def render_system_prompts(c: Ctx, d: dict) -> str:
    packs = json.loads(PACKS.read_text(encoding="utf-8"))
    gaps = json.loads(GAPS.read_text(encoding="utf-8")) if GAPS.exists() else {"pillars": []}
    pillars = gaps.get("pillars", [])
    names = {p["key"]: p["pillar"].split(" (")[0] for p in pillars}   # headings without the gap-file tool lists
    names.update(d.get("group_names", {}))
    order = d.get("group_order") or [p["key"] for p in pillars]
    titles = guide_titles()
    groups: dict[str, list[str]] = {}
    for slug in sorted(packs):
        if not (SITE / "guides" / f"{slug}.html").is_file():
            continue
        key = pillar_of(slug, pillars, d.get("pillar_overrides", {}), d.get("pillar_keywords", []),
                        packs[slug].get("mission", ""))
        groups.setdefault(key, []).append(slug)
    keys = [k for k in order if k in groups] + sorted(k for k in groups if k not in order)
    n = sum(len(v) for v in groups.values())
    c.n_packs = n
    toc = '<p class="toc">' + "".join(f'<a href="#g-{esc(k)}">{esc(names.get(k, k))} ({len(groups[k])})</a>'
                                      for k in keys) + "</p>"
    out = [toc]
    for k in keys:
        out.append(f'<section id="g-{esc(k)}"><h2>{esc(names.get(k, k))}</h2>')
        for slug in groups[k]:
            p = packs[slug]
            rp = (p.get("deeper_not_bigger") or {}).get("rewritten_prompt", "")
            t = titles.get(slug, slug)
            out.append(f'<article class="spk" id="{esc(slug)}"><h3>{esc(t)}</h3>'
                       f'<p class="role">{esc(role_line(p.get("one_shot", "")))}</p>'
                       f'<p class="fine">Mission: {esc(clip(p.get("mission", ""), 220))}</p>'
                       + pre_block(rp) +
                       f'<p><a href="/guides/{esc(slug)}#prompt-system">Full prompt system: one-shot prompt, '
                       f'{len(p.get("steps") or [])} step prompts with audits, gap audit</a></p></article>')
        out.append("</section>")
    d = dict(d)
    d["answer"] = d["answer"].replace("{n}", str(n))
    d["description"] = d["description"].replace("{n}", str(n))
    return render_page(c, d, "\n".join(out))


# ─────────────────────────────────────────────────────────── index ──
def render_index(c: Ctx, which: str, pages: list[dict]) -> str:
    if which == "compare":
        title, h1 = "Compare AI tools: dated, sourced comparisons · DejaViewed", "Compare"
        lead = ("Dated comparisons, best-of lists and libraries built from the DejaViewed corpus of saved posts. "
                "Each page puts the direct answer first, cites the entries behind every claim, and lists its sources "
                "with the date they were checked.")
        show = pages
    else:
        title, h1 = "Best-of lists: tested picks with keep/skip verdicts · DejaViewed", "Best of"
        lead = ("Best-of lists with a keep, try or skip verdict per item, the corpus entries that cover it, and its "
                "GitHub maintenance status checked on a stated date.")
        show = [p for p in pages if p["dir"] == "best"] + [p for p in pages if p["dir"] != "best"]
    cards = []
    for p in show:
        kind = {"compare": "comparison", "best": "best-of", "root": "library"}[p["dir"]]
        cards.append(f'<li><a href="{esc(page_url(p))}"><span class="n">{esc(kind)} · verified {esc(p["last_verified"])}</span>'
                     f'<h3>{esc(p["h1"])}</h3><p>{esc(p["description"].replace("{n}", str(c.n_packs)))}</p></a></li>')
    lab = "Compare" if which == "compare" else "Best of"
    other = ('<a href="/best/">Best-of lists</a>' if which == "compare" else '<a href="/compare/">All comparisons</a>')
    body = (f'<main class="cmp">{crumbs([("Home", "/"), (lab, None)])}<h1>{h1}</h1>'
            f'<div class="answer"><p>{esc(lead)}</p></div><ul class="pgrid">{"".join(cards)}</ul>'
            f'<p class="more">{other}<a href="/prompts">Prompt systems</a><a href="/system-prompts">System prompt examples</a>'
            f'<a href="/guides/">All guides</a><a href="/catalog">Catalog</a></p></main>\n</body></html>\n')
    return head(title, clip(lead, DESC_MAX), f"{SITE_URL}/{which}/") + body


# ─────────────────────────────────────────────────────────── main ──
def validate_meta(c: Ctx, d: dict):
    for k in ("slug", "dir", "title", "h1", "description", "answer", "last_verified", "sources"):
        if k not in d:
            c.errors.append(f"{d.get('slug', '?')}: missing {k}")
    if d.get("dir") not in ("compare", "best", "root"):
        c.errors.append(f"{d.get('slug')}: bad dir {d.get('dir')!r}")
    desc = d.get("description", "").replace("{n}", "63")
    if len(desc) > DESC_MAX:
        c.errors.append(f"{d['slug']}: description {len(desc)} > {DESC_MAX} chars")
    if len(d.get("title", "")) > TITLE_MAX:
        c.errors.append(f"{d['slug']}: title {len(d['title'])} > {TITLE_MAX} chars")
    for s in d.get("sources", []):
        if not (s.get("url", "").startswith(("http", "/")) and s.get("accessed") and s.get("key")):
            c.errors.append(f"{d['slug']}: source incomplete {s}")


def norm(text: str) -> str:
    """Strip what later pipeline stages own (seo/sitenav/monetize blocks, the stray description and
    canonical build_seo moves into its block, and the <title> it may refit) so --check compares only
    what this generator writes."""
    text = re.sub(r"<!--\s*([\w-]+):start\s*-->.*?<!--\s*\1:end\s*-->\n?", "", text, flags=re.S)
    text = re.sub(r"<meta name=\"description\"[^>]*>\n?|<link rel=\"canonical\"[^>]*>\n?|<title>.*?</title>\n?", "", text)
    return text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="exit 1 if data is invalid or any page would change")
    a = ap.parse_args()
    if not CATALOG.exists():
        print("[compare] site/catalog.json missing; run cms.py rebuild first", file=sys.stderr)
        return 1
    c = Ctx()
    pages = []
    for f in sorted(DATA.glob("*.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        if d.get("slug") != f.stem:
            c.errors.append(f"{f.name}: slug {d.get('slug')!r} != file stem")
        validate_meta(c, d)
        pages.append(d)
    order = {"compare": 0, "best": 1, "root": 2}
    pages.sort(key=lambda d: (order.get(d.get("dir"), 9), d.get("order", 50), d.get("slug", "")))
    outputs: dict[Path, str] = {}
    stats = []
    for d in pages:
        html_out = render_system_prompts(c, d) if d.get("kind") == "library" else render_page(c, d)
        outputs[page_file(d)] = html_out
        stats.append((page_url(d), body_text_words(html_out), len(c.cited | c.cited_auto), len(d.get("sources", []))))
    outputs[SITE / "compare" / "index.html"] = render_index(c, "compare", pages)
    if any(d["dir"] == "best" for d in pages):
        outputs[SITE / "best" / "index.html"] = render_index(c, "best", pages)
    if c.errors:
        for e in c.errors:
            print(f"[compare] ERROR {e}", file=sys.stderr)
        return 1
    changed = []
    for path, text in outputs.items():
        old = path.read_text(encoding="utf-8") if path.exists() else None
        if old is None or norm(old) != norm(text):
            changed.append(path)
        # Write mode always rewrites: build_seo moves <meta name="description"> into its block and reads
        # the page's own tag as its source, so the tag must be back in place before every seo pass.
        # (seo, monetize and links run after this phase in rebuild.sh and restore their blocks.)
        if not a.check and old != text:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
    # stale pages this generator wrote earlier (marked) and no longer produces
    stale = [p for sub in ("compare", "best") for p in (SITE / sub).glob("*.html")
             if p not in outputs and MARK in p.read_text(encoding="utf-8", errors="replace")]
    for p in stale:
        changed.append(p)
        if not a.check:
            p.unlink()
    for url, words, cited, nsrc in stats:
        print(f"[compare] {url}: {words} words, {cited} entries cited, {nsrc} sources")
    if a.check:
        if changed:
            print(f"[compare] --check: {len(changed)} page(s) would change: "
                  f"{[str(p.relative_to(SITE)) for p in changed]}")
            return 1
        print("[compare] --check: clean")
        return 0
    print(f"[compare] wrote {len(changed)} changed page(s) of {len(outputs)}" + (f", removed {len(stale)} stale" if stale else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
