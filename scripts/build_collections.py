#!/usr/bin/env python3
"""Static per-collection index pages: site/collections/<collection>.html + index.html.

Every entry gets a crawlable path of depth <= 3 from the home page:
    /  ->  /collections/  ->  /collections/<c>  ->  /e/<id>
(and depth 2 via the static footer nav's /e/ link). Each collection page lists ALL of its
entries (tier pill, title -> /e/<id>, one-line summary, creator, date; sorted tier then
newest first) under a short intro computed from the data: counts, tier mix, top tools,
top creators, and the curated guides that draw >= 3 entries from the collection.

Reads site/catalog.json (written by `cms.py rebuild`) and data/deep_dives.json.
Links are root-absolute clean URLs (what Cloudflare Pages serves without a 308 hop).
The head carries a minimal <!-- seo:start --> block (description + canonical) that
build_seo.py replaces wholesale if it ever adds "collections" to its page set.

Usage:  python3 scripts/build_collections.py
"""
from __future__ import annotations

import html
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
OUT = SITE / "collections"
CATALOG = SITE / "catalog.json"
DIVES = ROOT / "data" / "deep_dives.json"
SITE_URL = "https://dejaviewed.dev"
GUIDE_MIN = 3  # a curated guide is linked when it draws >= this many entries from the collection

# Display names. Collections are Instagram saved-folder ids (ai1..ai8 were sequential
# "AI" folders); unknown ids fall back to a title-cased version of the id.
COLLECTION_NAMES = {
    "ai1": "AI Saves, Vol. 1", "ai2": "AI Saves, Vol. 2", "ai3": "AI Saves, Vol. 3",
    "ai4": "AI Saves, Vol. 4", "ai5": "AI Saves, Vol. 5", "ai6": "AI Saves, Vol. 6",
    "ai7": "AI Saves, Vol. 7", "ai8": "AI Saves, Vol. 8",
    "creative": "Creative", "creative4": "Creative, Vol. 4",
    "art-i-like": "Art I Like", "art-inspiration": "Art Inspiration",
    "music": "Music", "quant": "Quant & Trading", "stock2": "Stocks, Vol. 2",
    "stock3": "Stocks, Vol. 3", "game-theory": "Game Theory", "prompts": "Prompts",
}
TIER_ORDER = {"S": 0, "A": 1, "B": 2, "C": 3}


def esc(x) -> str:
    return html.escape(str(x or ""), quote=True)


def safe_slug(rid: str) -> str:
    """Must match render_entries.safe_slug (entry page filename)."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in rid)


def collection_name(c: str) -> str:
    return COLLECTION_NAMES.get(c) or re.sub(r"[-_]+", " ", c).title()


def collection_slug(c: str) -> str:
    return safe_slug(c).lower()


def collection_url(c: str) -> str:
    return f"/collections/{collection_slug(c)}"


def entry_collection(e: dict) -> str:
    return e.get("collection") or e.get("source_collection") or ""


def clip(text: str, n: int) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= n:
        return text
    return text[:n].rsplit(" ", 1)[0].rstrip(",.;:") + "…"


def handle(e: dict) -> str:
    h = str(e.get("creator") or "").lstrip("@").strip()
    return h if re.fullmatch(r"[A-Za-z0-9._]{1,30}", h) else ""


def as_list(v) -> list:
    if isinstance(v, list):
        return [str(x) for x in v if x]
    if isinstance(v, str) and v.strip():
        return [v.strip()]
    return []


def curated_guides() -> list[dict]:
    """[{slug, title, entry_ids}] for curated dives whose guide page exists on disk."""
    if not DIVES.exists():
        return []
    sys.path.insert(0, str(ROOT / "scripts"))
    try:
        from build_guides import is_curated, slug_of
    except Exception:  # pragma: no cover
        def is_curated(d): return d.get("suggested_by") == "curated" or bool(d.get("pinned"))
        def slug_of(i): return i[len("dd-"):] if i.startswith("dd-") else i
    out = []
    for d in json.loads(DIVES.read_text(encoding="utf-8")).get("deep_dives", []):
        if not is_curated(d):
            continue
        slug = slug_of(d["id"])
        if (SITE / "guides" / f"{slug}.html").is_file():
            out.append({"slug": slug, "title": d.get("title") or slug, "entry_ids": set(d.get("entry_ids") or [])})
    return out


def sort_key(e: dict):
    return (TIER_ORDER.get((e.get("tier") or "C").upper(), 9), "".join(chr(0x10FFFF - ord(ch)) for ch in str(e.get("date") or "")),
            (e.get("title") or "").lower())


def fmt_date(d) -> str:
    return str(d or "")[:10]


HEAD = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<title>{title}</title>
<!-- seo:start -->
<meta name="description" content="{desc}">
<link rel="canonical" href="{canonical}">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{desc}">
<meta property="og:url" content="{canonical}">
<meta property="og:type" content="website">
<!-- seo:end -->
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="../shared.css">
<script src="../shared.js"></script>
<style>
  main.coll {{ max-width: 960px; margin: 24px auto 40px; padding: 0 20px; }}
  .coll h1 {{ font: 700 30px/1.2 Inter, system-ui; margin: 8px 0 12px; color: var(--text); }}
  .coll .lead {{ color: var(--text-dim); font-size: 15px; line-height: 1.6; margin: 0 0 14px; max-width: 760px; }}
  .coll .lead a, .coll .guides a {{ color: var(--accent); text-decoration: none; }}
  .coll .lead a:hover, .coll .guides a:hover {{ text-decoration: underline; }}
  nav.crumbs {{ font-size: 12px; color: var(--text-mute); margin-bottom: 6px; }}
  nav.crumbs a {{ color: var(--text-mute); text-decoration: none; }}
  nav.crumbs a:hover {{ color: var(--accent); }}
  nav.crumbs .sep {{ margin: 0 6px; opacity: .6; }}
  .coll h2 {{ margin: 28px 0 10px; font: 600 12px/1 'JetBrains Mono', ui-monospace, monospace; letter-spacing: .08em;
             text-transform: uppercase; color: var(--text-mute); }}
  .coll .guides {{ list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 8px; }}
  .coll .guides li {{ background: var(--panel); border: 1px solid var(--border); border-radius: 999px;
                     padding: 5px 12px; font-size: 13px; }}
  .coll .guides .n {{ color: var(--text-mute); font-size: 11px; margin-left: 6px; }}
  ol.entries {{ list-style: none; margin: 0; padding: 0; }}
  ol.entries li {{ background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
                  padding: 10px 14px; margin-bottom: 8px; }}
  ol.entries li:hover {{ border-color: var(--border-hi); }}
  ol.entries a.t {{ color: var(--text); text-decoration: none; font-weight: 600; font-size: 14px; }}
  ol.entries a.t:hover {{ color: var(--accent); }}
  ol.entries .s {{ display: block; color: var(--text-dim); font-size: 13px; line-height: 1.45; margin-top: 3px; }}
  ol.entries .m {{ display: block; color: var(--text-mute); font: 400 11px/1.6 'JetBrains Mono', ui-monospace, monospace; margin-top: 3px; }}
  .tb {{ display: inline-block; min-width: 18px; text-align: center; padding: 0 5px; margin-right: 8px; border-radius: 999px;
        font: 800 10px/16px Inter, system-ui; border: 1px solid var(--border); color: var(--text-mute); vertical-align: 1px; }}
  .tb.t-s {{ color: var(--c-entry-s); border-color: rgba(251,191,36,.45); background: rgba(251,191,36,.12); }}
  .tb.t-a {{ color: var(--c-entry-a); border-color: rgba(167,139,250,.45); background: rgba(167,139,250,.12); }}
  .tb.t-b {{ color: var(--c-entry-b); border-color: rgba(96,165,250,.45); background: rgba(96,165,250,.12); }}
  .cgrid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: 12px; margin: 0; padding: 0; list-style: none; }}
  .cgrid li a {{ display: block; background: var(--panel); border: 1px solid var(--border); border-radius: 12px;
                padding: 14px 16px; color: var(--text); text-decoration: none; height: 100%; box-sizing: border-box; }}
  .cgrid li a:hover {{ border-color: var(--accent); }}
  .cgrid h3 {{ margin: 0 0 4px; font: 600 16px/1.3 Inter, system-ui; }}
  .cgrid .m {{ color: var(--text-mute); font: 400 11px/1.6 'JetBrains Mono', ui-monospace, monospace; }}
  .cgrid p {{ color: var(--text-dim); font-size: 13px; line-height: 1.45; margin: 6px 0 0; }}
  .more {{ margin-top: 22px; font-size: 13px; color: var(--text-mute); }}
  .more a {{ color: var(--text-dim); margin-right: 14px; }}
</style>
</head><body>
<script>DV.mountHeader(document.body, 'collections');</script>
"""


def tier_badge(t: str) -> str:
    t = (t or "C").upper()
    return f'<span class="tb t-{esc(t.lower())}" title="{esc(t)}-tier">{esc(t)}</span>'


def stats_for(items: list[dict], guides: list[dict]) -> dict:
    tiers = Counter((e.get("tier") or "C").upper() for e in items)
    tools = Counter(t for e in items for t in as_list(e.get("tools")))
    creators = Counter(h for e in items if (h := handle(e)))
    dates = sorted(fmt_date(e.get("date")) for e in items if e.get("date"))
    ids = {e.get("id") for e in items}
    g = sorted(({"slug": d["slug"], "title": d["title"], "n": len(d["entry_ids"] & ids)} for d in guides
                if len(d["entry_ids"] & ids) >= GUIDE_MIN), key=lambda x: (-x["n"], x["title"]))
    return {"n": len(items), "tiers": tiers, "tools": tools, "creators": creators,
            "first": dates[0] if dates else "", "last": dates[-1] if dates else "", "guides": g}


def intro(name: str, st: dict) -> str:
    tier_mix = ", ".join(f"{st['tiers'][t]} {t}-tier" for t in "SABC" if st["tiers"].get(t))
    span = (f", saved between {st['first'][:7]} and {st['last'][:7]}" if st["first"] and st["first"][:7] != st["last"][:7]
            else (f", saved in {st['first'][:7]}" if st["first"] else ""))
    s1 = (f"{esc(name)} holds {st['n']} saved post{'s' if st['n'] != 1 else ''} from "
          f"{len(st['creators'])} creator{'s' if len(st['creators']) != 1 else ''}{span} ({tier_mix}).")
    bits = []
    top_tools = [t for t, _ in st["tools"].most_common(5)]
    if top_tools:
        bits.append(f"The most-tagged tools are {esc(', '.join(top_tools[:-1]) + (' and ' if len(top_tools) > 1 else '') + top_tools[-1])}.")
    top_cr = [(h, n) for h, n in st["creators"].most_common(3) if n > 1]
    if top_cr:
        bits.append("Most-saved creators: " + ", ".join(f"@{esc(h)} ({n})" for h, n in top_cr) + ".")
    if st["guides"]:
        gl = ", ".join(f'<a href="/guides/{esc(g["slug"])}">{esc(g["title"])}</a>' for g in st["guides"][:3])
        bits.append(f"{len(st['guides'])} curated guide{'s draw' if len(st['guides']) != 1 else ' draws'} "
                    f"{GUIDE_MIN}+ entries from it, starting with {gl}.")
    return s1 + (" " + " ".join(bits) if bits else "")


def describe(name: str, st: dict) -> str:
    """Meta description: what's in it first (no date span), cut at a word boundary <= 158 chars."""
    tools = [t for t, _ in st["tools"].most_common(4)]
    cr = [f"@{h}" for h, n in st["creators"].most_common(2) if n > 1]
    parts = [f"{st['n']} saved posts in {name}, ranked S to C ({st['tiers'].get('S', 0)} S-tier, "
             f"{st['tiers'].get('A', 0)} A-tier)."]
    if tools:
        parts.append("Tools: " + ", ".join(tools) + ".")
    if st["guides"]:
        parts.append(f"{len(st['guides'])} curated guide{'s' if len(st['guides']) != 1 else ''}.")
    if cr:
        parts.append("Top creators: " + ", ".join(cr) + ".")
    out = parts[0]
    for p in parts[1:]:  # whole sentences only, so nothing ends on a dangling fragment
        if len(out) + 1 + len(p) <= 158:
            out += " " + p
    return clip(out, 158)  # word-boundary cut with "…" only if the first sentence alone is too long


def plain(s: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", s))


def render_collection(c: str, items: list[dict], guides: list[dict], all_colls: list[tuple[str, int]]) -> str:
    name = collection_name(c)
    st = stats_for(items, guides)
    lead = intro(name, st)
    title = f"{name}: {st['n']} saved posts, ranked · DejaViewed"
    desc = describe(name, st)
    rows = []
    for e in sorted(items, key=sort_key):
        rid = e.get("id")
        if not rid:
            continue
        meta = " · ".join(x for x in ((f"@{handle(e)}" if handle(e) else ""), fmt_date(e.get("date")),
                                      e.get("type") or "") if x)
        summ = clip(e.get("summary") or "", 170)
        rows.append(f'<li>{tier_badge(e.get("tier"))}<a class="t" href="/e/{esc(safe_slug(rid))}">'
                    f'{esc(clip(e.get("title") or rid, 110))}</a>'
                    + (f'<span class="s">{esc(summ)}</span>' if summ else "")
                    + (f'<span class="m">{esc(meta)}</span>' if meta else "") + "</li>")
    guides_html = ""
    if st["guides"]:
        guides_html = ('<h2>Guides built from this collection</h2><ul class="guides">'
                       + "".join(f'<li><a href="/guides/{esc(g["slug"])}">{esc(g["title"])}</a>'
                                 f'<span class="n">{g["n"]} entries</span></li>' for g in st["guides"])
                       + "</ul>")
    others = "".join(f'<a href="{collection_url(o)}">{esc(collection_name(o))}</a>' for o, _ in all_colls if o != c)
    body = f"""<main class="coll">
  <nav class="crumbs" aria-label="Breadcrumb"><a href="/">Home</a><span class="sep">›</span><a href="/collections/">Collections</a><span class="sep">›</span><span aria-current="page">{esc(name)}</span></nav>
  <h1>{esc(name)}</h1>
  <p class="lead">{lead}</p>
  {guides_html}
  <h2>All {st['n']} entries · best first</h2>
  <ol class="entries">
{chr(10).join(rows)}
  </ol>
  <p class="more">Other collections: {others}</p>
  <p class="more"><a href="/catalog">Filter in the catalog</a><a href="/e/">Every entry</a><a href="/guides/">All guides</a></p>
</main>
</body></html>
"""
    return HEAD.format(title=esc(title), desc=esc(desc), canonical=f"{SITE_URL}{collection_url(c)}") + body


def render_index(groups: dict[str, list[dict]], guides: list[dict], order: list[tuple[str, int]]) -> str:
    total = sum(n for _, n in order)
    cards = []
    for c, n in order:
        st = stats_for(groups[c], guides)
        tools = ", ".join(t for t, _ in st["tools"].most_common(3))
        top = sorted(groups[c], key=sort_key)[0]
        cards.append(f'<li><a href="{collection_url(c)}"><h3>{esc(collection_name(c))}</h3>'
                     f'<span class="m">{n} entries · {st["tiers"].get("S", 0)} S · {st["tiers"].get("A", 0)} A'
                     + (f' · {len(st["guides"])} guide{"s" if len(st["guides"]) != 1 else ""}' if st["guides"] else "")
                     + "</span>"
                     + (f"<p>Top tools: {esc(tools)}</p>" if tools else "")
                     + f'<p>Best: {esc(clip(top.get("title") or top.get("id"), 80))}</p></a></li>')
    lead = (f"{total} saved posts across {len(order)} collections. Each collection page lists every entry, "
            f"best first, with links to the curated guides built from it.")
    title = f"Collections: {len(order)} curated sets, {total} saved posts · DejaViewed"
    body = f"""<main class="coll">
  <nav class="crumbs" aria-label="Breadcrumb"><a href="/">Home</a><span class="sep">›</span><span aria-current="page">Collections</span></nav>
  <h1>Collections</h1>
  <p class="lead">{esc(lead)}</p>
  <ul class="cgrid">
{chr(10).join(cards)}
  </ul>
  <p class="more"><a href="/catalog">Filter in the catalog</a><a href="/e/">Every entry on one page</a><a href="/guides/">All guides</a></p>
</main>
</body></html>
"""
    return HEAD.format(title=esc(title), desc=esc(clip(lead, 158)), canonical=f"{SITE_URL}/collections/") + body


def main() -> int:
    if not CATALOG.exists():
        print(f"[collections] {CATALOG} missing — run cms.py rebuild first", file=sys.stderr)
        return 1
    entries = json.loads(CATALOG.read_text(encoding="utf-8")).get("entries") or []
    groups: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        c = entry_collection(e)
        if c and e.get("id"):
            groups[c].append(e)
    order = sorted(((c, len(v)) for c, v in groups.items()), key=lambda x: (-x[1], x[0]))
    guides = curated_guides()
    OUT.mkdir(exist_ok=True)
    wanted = {"index.html"} | {f"{collection_slug(c)}.html" for c in groups}
    for stale in OUT.glob("*.html"):
        if stale.name not in wanted:
            stale.unlink()
    for c, _ in order:
        (OUT / f"{collection_slug(c)}.html").write_text(render_collection(c, groups[c], guides, order), encoding="utf-8")
    (OUT / "index.html").write_text(render_index(groups, guides, order), encoding="utf-8")
    n_linked = sum(len(v) for v in groups.values())
    print(f"[collections] wrote {len(order)} collection pages + index.html ({n_linked} entries linked, "
          f"{len(entries) - n_linked} without a collection)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
