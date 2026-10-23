#!/usr/bin/env python3
"""Render per-entry summary pages from data/entries.parquet.

Writes one site/e/<id>.html per row, plus an index at site/e/index.html.
Uses a single template that embeds the shared.css card styling, so pages
look identical to the rest of the site. Every page link is a root-absolute clean
URL (/e/<id>, /catalog, /guides/<slug>, /collections/<c>) — what Cloudflare Pages
serves without a 308 hop; asset links (../shared.css) stay relative.

Hierarchical tableau (Phase 5): five zoom levels per entry — 100k, 50k,
10k, 5k, 1k ft. At first render only the top level is populated from the
existing summary; lower tiers are stubs marked "needs deep-dive" that a
future LLM pass (or admin edit) can fill in.
"""
from __future__ import annotations

import html
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from cms import load_entries, load_crosslinks  # noqa: E402
from build_collections import collection_name, collection_url  # noqa: E402

SITE = ROOT / "site"
OUT = SITE / "e"


def esc(x) -> str:
    return html.escape(str(x or ""), quote=True)


def safe_slug(rid: str) -> str:
    """Filesystem-safe id (some post_ids include '/' or other chars)."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in rid)


def _pill(text: str, cls: str = "") -> str:
    return f'<span class="pill{" "+cls if cls else ""}">{esc(text)}</span>'


def _tier_pill(tier: str) -> str:
    t = (tier or "C").upper()
    return f'<span class="tier-pill tier-{t.lower()}">{esc(t)}-TIER</span>'


def tableau_levels(row: dict) -> list[dict]:
    """Five zoom levels, top-down. Missing fields get a placeholder so the
    UI renders consistently even before a deep-dive pass fills them in."""
    summary = (row.get("summary") or "").strip()
    takeaways = row.get("takeaways") or []
    takeaways = takeaways[: min(len(takeaways), 5)]
    caption = (row.get("caption") or "").strip()
    deep = row.get("deep_dive_slug") or ""
    tools = row.get("tools") or []
    techniques = row.get("techniques") or []
    return [
        {"label": "100k ft — What is this?",
         "body": row.get("title") or "(untitled)",
         "tags": [row.get("type"), row.get("tier") + "-tier" if row.get("tier") else ""]},
        {"label": "50k ft — Why care?",
         "body": summary or "(no summary — add via admin UI)",
         "tags": row.get("domains") or []},
        {"label": "10k ft — Key takeaways",
         "body": "\n".join(f"• {t}" for t in takeaways) or "(no takeaways yet)",
         "tags": []},
        {"label": "5k ft — Tools & techniques",
         "body": (
             (", ".join(tools) or "(no tools tagged)") + "\n\n" +
             (", ".join(techniques) or "(no techniques tagged)")
         ),
         "tags": []},
        {"label": "1k ft — Deep-dive / try it",
         "body": (caption[:800] + ("…" if len(caption) > 800 else ""))
                 if caption else "(no deep-dive content yet — add via admin UI or run skill)",
         "tags": [deep] if deep else []},
    ]


TEMPLATE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<title>{title} — DejaViewed</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="../shared.css">
<script src="../shared.js"></script>
<style>
  main.entry {{ max-width: 880px; margin: 24px auto 80px; padding: 0 20px; }}
  .entry h1 {{ font: 600 28px/1.25 Inter, system-ui; margin: 8px 0 12px; color: var(--text); }}
  .entry .meta {{ color: var(--text-mute); font-size: 13px; margin-bottom: 16px; }}
  .entry .actions a {{ margin-right: 10px; }}
  .tableau {{ margin-top: 28px; }}
  .level {{ background: var(--panel); border: 1px solid var(--border);
           border-radius: 12px; padding: 16px 18px; margin-bottom: 12px; }}
  .level h3 {{ margin: 0 0 8px; font: 600 13px/1 Inter, system-ui;
              letter-spacing: .08em; text-transform: uppercase; color: var(--text-mute); }}
  .level .body {{ white-space: pre-wrap; color: var(--text); font-size: 14px; line-height: 1.55; }}
  .level .tags {{ margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; }}
  .pill {{ display: inline-block; padding: 2px 8px; border-radius: 999px;
          background: var(--panel-2); color: var(--text-mute); border: 1px solid var(--border);
          font-size: 11px; }}
  details.level summary {{ cursor: pointer; font: 600 13px/1 Inter, system-ui; letter-spacing: .08em;
              text-transform: uppercase; color: var(--text-mute); }}
  details.level[open] summary {{ margin-bottom: 8px; }}
  .back {{ color: var(--text-mute); font-size: 12px; text-decoration: none; }}
  .back:hover {{ color: var(--accent); }}
  nav.crumbs {{ font-size: 12px; color: var(--text-mute); margin-bottom: 6px; }}
  nav.crumbs a {{ color: var(--text-mute); text-decoration: none; }}
  nav.crumbs a:hover {{ color: var(--accent); }}
  nav.crumbs .sep {{ margin: 0 6px; opacity: .6; }}
  .hub {{ margin-top: 28px; }}
  .hub h2 {{ margin: 0 0 10px; font: 600 13px/1 Inter, system-ui; letter-spacing: .08em;
            text-transform: uppercase; color: var(--text-mute); }}
  .hub ul {{ list-style: none; margin: 0; padding: 0; }}
  .hub li {{ background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
            padding: 10px 14px; margin-bottom: 8px; font-size: 14px; line-height: 1.45; }}
  .hub li a {{ color: var(--text); text-decoration: none; font-weight: 500; }}
  .hub li a:hover {{ color: var(--accent); }}
  .hub .why {{ display: block; color: var(--text-mute); font-size: 11px; margin-top: 3px; }}
  .hub .links a {{ margin-right: 14px; }}
  nav.pn {{ display: flex; justify-content: space-between; gap: 12px; margin-top: 28px;
           border-top: 1px solid var(--border); padding-top: 16px; font-size: 13px; }}
  nav.pn a {{ color: var(--text-mute); text-decoration: none; max-width: 48%; }}
  nav.pn a:hover {{ color: var(--accent); }}
  nav.pn .next {{ margin-left: auto; text-align: right; }}
</style>
</head><body>
<script>DV.mountHeader(document.body, 'entries');</script>
<main class="entry" data-pagefind-body data-pagefind-filter="kind:Entry">
  {crumbs_html}
  <a class="back" data-pagefind-ignore href="/e/">← all entries</a>
  <div style="margin:10px 0">{tier_pill} {type_pill}</div>
  <h1>{title}</h1>
  <div class="meta">{meta}</div>
  <div class="actions">
    {source_link}
  </div>
  <section class="tableau">
    {levels_html}
  </section>
  {transcript_html}
  {hub_html}
</main>
</body></html>
"""


TRANSCRIPT_CLIP = 1500  # keep entry pages light; full text lives in catalog.json


def clip(text: str, n: int) -> str:
    text = " ".join((text or "").split())
    if len(text) <= n:
        return text
    cut = text[:n].rsplit(" ", 1)[0]
    return cut + "…"


def transcript_block(row: dict) -> str:
    """Collapsed transcript excerpt — visible on demand, and indexed by Pagefind."""
    t = clip(row.get("transcript") or "", TRANSCRIPT_CLIP)
    if not t:
        return ""
    return ('<details class="level transcript"><summary>Transcript excerpt</summary>'
            f'<div class="body">{esc(t)}</div></details>')


# ── Hub sections (internal linking) ─────────────────────────────────────
# Crosslink dims that carry content signal. tier/type/collection pair almost
# everything with everything, so they only break ties and never qualify a
# pair on their own.
DIM_W = {"tool": 1.5, "technique": 1.5, "domain": 1.0, "subject": 1.0, "style_tag": 1.0,
         "reference": 1.0, "medium": 0.5, "creator": 1.0,
         "collection": 0.3, "type": 0.2, "tier": 0.1}
WEAK_DIMS = {"collection", "type", "tier"}
RELATED_N, CREATOR_N = 6, 5
HANDLE_RE = re.compile(r"[a-z0-9._]{1,30}")


def clean_handle(handle) -> str:
    """Valid lowercase IG handle or "" (same rule as build_guides.clean_handle)."""
    h = str(handle or "").lstrip("@").strip()
    return h if HANDLE_RE.fullmatch(h) else ""


def catalog_anchor(row: dict) -> str:
    """Same id catalog.html gives each card: post-<shortcode from post_url>."""
    m = re.search(r"/(?:p|reel)/([^/?#]+)", row.get("url") or "")
    return "post-" + (m.group(1) if m else "")


def build_lookups(rows: list[dict]) -> dict:
    """Precompute every cross-entry index once (not per page)."""
    ids = {r["id"] for r in rows if r.get("id")}
    by_id = {r["id"]: r for r in rows if r.get("id")}

    # crosslinks -> per-entry scored neighbours
    score: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    strong: dict[str, dict[str, set]] = defaultdict(lambda: defaultdict(set))
    for L in load_crosslinks():
        a, b, dim = L["a_id"], L["b_id"], L["dim"]
        if a not in ids or b not in ids or a == b:
            continue
        w = DIM_W.get(dim, 0.5) * float(L.get("weight") or 1.0)
        score[a][b] += w
        score[b][a] += w
        if dim not in WEAK_DIMS:
            strong[a][b].add(dim)
            strong[b][a].add(dim)

    # creator index (catalog order = date desc)
    by_creator: dict[str, list[str]] = defaultdict(list)
    for r in sorted(rows, key=lambda r: (str(r.get("date") or ""), r.get("id") or ""), reverse=True):
        h = clean_handle(r.get("creator"))
        if h and r.get("id"):
            by_creator[h].append(r["id"])

    # prev/next within source_collection by date
    by_coll: dict[str, list[str]] = defaultdict(list)
    for r in sorted(rows, key=lambda r: (str(r.get("date") or ""), r.get("id") or "")):
        c = r.get("collection") or r.get("source_collection") or ""
        if c and r.get("id"):
            by_coll[c].append(r["id"])
    prev_next: dict[str, tuple] = {}
    for c, lst in by_coll.items():
        for i, rid in enumerate(lst):
            prev_next[rid] = (lst[i - 1] if i > 0 else None, lst[i + 1] if i + 1 < len(lst) else None)

    # guide / deeper membership (only pages that exist on disk)
    appears: dict[str, list[tuple[str, str]]] = defaultdict(list)
    try:
        from build_guides import slug_of, is_curated, deeper_file, page_title, GUIDES
    except Exception as ex:  # pragma: no cover
        print(f"[render_entries] warn: guide lookup unavailable ({ex})", file=sys.stderr)
        slug_of = None
    if slug_of:
        dd_path = ROOT / "data" / "deep_dives.json"
        dives = json.loads(dd_path.read_text(encoding="utf-8")).get("deep_dives", []) if dd_path.exists() else []
        seen: dict[str, set] = defaultdict(set)

        def add(rid, href, label):
            if rid in ids and href not in seen[rid]:
                seen[rid].add(href)
                appears[rid].append((href, label))

        for d in dives:
            if not is_curated(d):
                continue
            slug = slug_of(d["id"])
            gpath = GUIDES / f"{slug}.html"
            dfile = deeper_file(slug)
            for eid in d.get("entry_ids") or []:
                if gpath.exists():
                    add(eid, f"/guides/{slug}", f"Guide: {d.get('title') or slug}")
                if dfile:
                    add(eid, f"/deeper/{dfile.removesuffix('.html')}", f"Deeper dive: {d.get('title') or slug}")
        for r in rows:  # standalone single-entry guides (deep_dive_slug)
            slug = r.get("deep_dive_slug") or ""
            gpath = GUIDES / f"{slug}.html" if slug else None
            if gpath and gpath.exists():
                add(r["id"], f"/guides/{slug}", f"Guide: {page_title(gpath) or slug}")

    return {"by_id": by_id, "score": score, "strong": strong, "by_creator": by_creator,
            "prev_next": prev_next, "appears": appears, "by_coll": by_coll}


def _entry_link(r: dict, why: str = "") -> str:
    t = (r.get("title") or r.get("id") or "(untitled)")[:110]
    return (f'<li>{_tier_pill(r.get("tier") or "C")} <a href="/e/{esc(safe_slug(r["id"]))}">{esc(t)}</a>'
            + (f'<span class="why">{esc(why)}</span>' if why else "") + "</li>")


def hub_sections(row: dict, lk: dict) -> tuple[str, str]:
    """(breadcrumb html, hub sections html) for one entry."""
    rid = row["id"]
    by_id = lk["by_id"]
    coll = row.get("collection") or row.get("source_collection") or ""
    cname = collection_name(coll) if coll else ""
    title = row.get("title") or rid
    crumbs = ('<nav class="crumbs" aria-label="Breadcrumb" data-pagefind-ignore>'
              '<a href="/">Home</a><span class="sep">›</span>'
              '<a href="/catalog">Catalog</a><span class="sep">›</span>'
              + (f'<a href="{collection_url(coll)}">{esc(cname)}</a><span class="sep">›</span>' if coll else "")
              + f'<span aria-current="page">{esc(title[:70])}</span></nav>')

    out = []
    # Same creator (computed first so Related can skip these)
    h = clean_handle(row.get("creator"))
    same = [x for x in lk["by_creator"].get(h, []) if x != rid][:CREATOR_N] if h else []
    # Related: needs at least one content dim in common
    sc = lk["score"].get(rid, {})
    strong = lk["strong"].get(rid, {})
    cands = sorted((b for b in sc if strong.get(b) and b not in same and b in by_id),
                   key=lambda b: (-sc[b], b))[:RELATED_N]
    if cands:
        items = "".join(_entry_link(by_id[b], "shared " + ", ".join(sorted(strong[b]))) for b in cands)
        out.append(f'<section class="hub related" data-pagefind-ignore><h2>Related</h2><ul>{items}</ul></section>')
    app = lk["appears"].get(rid, [])
    if app:
        items = "".join(f'<li><a href="{esc(href)}">{esc(label)}</a></li>' for href, label in app)
        out.append(f'<section class="hub appears" data-pagefind-ignore><h2>Appears in</h2><ul>{items}</ul></section>')
    if same:
        items = "".join(_entry_link(by_id[x]) for x in same if x in by_id)
        out.append(f'<section class="hub creator" data-pagefind-ignore><h2>More from @{esc(h)}</h2><ul>{items}</ul></section>')
    anchor = catalog_anchor(row)
    coll_links = (f'<a href="{collection_url(coll)}">All {len(lk["by_coll"].get(coll, []))} entries in {esc(cname)}</a>'
                  if coll else "")
    coll_links += (f'<a href="/catalog#{esc(anchor)}">Find this post in the catalog</a>'
                   if anchor != "post-" else '<a href="/catalog">Browse the full catalog</a>')
    coll_links += '<a href="/collections/">All collections</a><a href="/e/">All entries</a>'
    out.append(f'<section class="hub collection" data-pagefind-ignore><h2>Collection{": " + esc(cname) if coll else ""}</h2>'
               f'<div class="links">{coll_links}</div></section>')
    prev_id, next_id = lk["prev_next"].get(rid, (None, None))
    if prev_id or next_id:
        pn = ""
        if prev_id:
            pn += f'<a class="prev" rel="prev" href="/e/{esc(safe_slug(prev_id))}">← {esc((by_id[prev_id].get("title") or prev_id)[:70])}</a>'
        if next_id:
            pn += f'<a class="next" rel="next" href="/e/{esc(safe_slug(next_id))}">{esc((by_id[next_id].get("title") or next_id)[:70])} →</a>'
        out.append(f'<nav class="pn" aria-label="Previous and next in {esc(cname)}" data-pagefind-ignore>{pn}</nav>')
    return crumbs, "\n  ".join(out)


def render_one(row: dict, lookups: dict | None = None) -> str:
    title = row.get("title") or row.get("id") or "(untitled)"
    meta_bits = []
    if row.get("creator"): meta_bits.append(esc(row["creator"]))
    if row.get("date"): meta_bits.append(esc(row["date"]))
    cols = row.get("collections") or []
    if cols: meta_bits.append("in " + ", ".join(f'<a href="{collection_url(c)}">{esc(collection_name(c))}</a>' for c in cols))
    meta = " · ".join(meta_bits)
    source_link = (
        f'<a class="primary" href="{esc(row["url"])}" target="_blank" rel="noopener">Open post ↗</a>'
        if row.get("url") else ""
    )
    levels = tableau_levels(row)
    levels_html = "\n".join(
        f'<div class="level"><h3>{esc(L["label"])}</h3>'
        f'<div class="body">{esc(L["body"])}</div>'
        + (
            '<div class="tags">' + "".join(_pill(t) for t in L["tags"] if t) + "</div>"
            if L["tags"] else ""
        )
        + "</div>"
        for L in levels
    )
    crumbs_html, hub_html = hub_sections(row, lookups) if lookups and row.get("id") else ("", "")
    return TEMPLATE.format(
        title=esc(title),
        crumbs_html=crumbs_html,
        hub_html=hub_html,
        tier_pill=_tier_pill(row.get("tier") or "C"),
        type_pill=_pill(row.get("type") or "resource"),
        meta=meta,
        source_link=source_link,
        levels_html=levels_html,
        transcript_html=transcript_block(row),
    )


def render_index(rows: list[dict]) -> str:
    """All entries on one static page, grouped by collection (jump links at top), tier then
    title within a group. Every card links /e/<id>; every group header links /collections/<c>."""
    groups: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        if r.get("id"):
            groups[r.get("collection") or r.get("source_collection") or ""].append(r)
    order = sorted(groups, key=lambda c: (-len(groups[c]), c))
    total = sum(len(v) for v in groups.values())
    jump = " ".join(f'<a href="#c-{esc(c or "none")}">{esc(collection_name(c) if c else "Uncollected")} '
                    f'<span>{len(groups[c])}</span></a>' for c in order)
    sections = []
    for c in order:
        cards = []
        for r in sorted(groups[c], key=lambda r: (r.get("tier") or "Z", r.get("title") or "")):
            summ = r.get("summary") or ""
            cards.append(
                f'<a class="entry-card" href="/e/{esc(safe_slug(r["id"]))}">'
                f'  <div class="row">{_tier_pill(r.get("tier") or "C")} {_pill(r.get("type") or "resource")}</div>'
                f'  <h3>{esc((r.get("title") or "(untitled)")[:90])}</h3>'
                f'  <div class="meta">{esc(r.get("creator") or "")}</div>'
                f'  <p>{esc(summ[:180])}{"…" if len(summ) > 180 else ""}</p>'
                "</a>")
        head = (f'<a href="{collection_url(c)}">{esc(collection_name(c))}</a>' if c else "Uncollected")
        sections.append(f'<section class="group" id="c-{esc(c or "none")}"><h2>{head} '
                        f'<span class="n">{len(groups[c])} entries</span></h2>'
                        f'<div class="entries">\n' + "\n".join(cards) + "\n</div></section>")
    body = "\n".join(sections)
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><title>All Entries — DejaViewed</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="../shared.css">
<script src="../shared.js"></script>
<style>
  main.all {{ max-width: 1200px; margin: 24px auto 40px; padding: 0 20px; }}
  main.all h1 {{ font: 700 28px/1.2 Inter, system-ui; margin: 8px 0 8px; color: var(--text); }}
  main.all .lead {{ color: var(--text-dim); font-size: 14px; margin: 0 0 14px; }}
  main.all .lead a {{ color: var(--accent); }}
  nav.jump {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }}
  nav.jump a {{ font: 400 11px/1 'JetBrains Mono', ui-monospace, monospace; color: var(--text-dim); text-decoration: none;
               border: 1px solid var(--border); border-radius: 999px; padding: 5px 10px; background: var(--panel); }}
  nav.jump a:hover {{ border-color: var(--accent); color: var(--text); }}
  nav.jump span {{ color: var(--text-mute); }}
  .group h2 {{ font: 600 18px/1.3 Inter, system-ui; margin: 32px 0 12px; scroll-margin-top: 70px; }}
  .group h2 a {{ color: var(--text); text-decoration: none; }}
  .group h2 a:hover {{ color: var(--accent); }}
  .group h2 .n {{ color: var(--text-mute); font: 400 11px/1 'JetBrains Mono', ui-monospace, monospace; margin-left: 8px; }}
  .entries {{ display: grid; grid-template-columns: repeat(auto-fill,minmax(300px,1fr)); gap: 14px; }}
  .entry-card {{ display:block; background:var(--panel); border:1px solid var(--border);
                 border-radius:12px; padding:14px 16px; color:var(--text); text-decoration:none;
                 transition:border-color .15s, transform .15s; }}
  .entry-card:hover {{ border-color: var(--accent); transform: translateY(-2px); }}
  .entry-card h3 {{ font: 600 15px/1.35 Inter, system-ui; margin:8px 0 6px; color: var(--text); }}
  .entry-card .row {{ display:flex; gap:6px; font-size:11px; }}
  .entry-card .meta {{ color: var(--text-mute); font-size: 12px; margin-bottom: 8px; }}
  .entry-card p {{ color: var(--text-mute); font-size: 13px; line-height: 1.5; margin: 0; }}
  .pill {{ display:inline-block; padding:2px 8px; border-radius:999px; background:var(--panel-2);
          color:var(--text-mute); border:1px solid var(--border); font-size:11px; }}
</style>
</head><body>
<script>DV.mountHeader(document.body, 'entries');</script>
<main class="all">
<h1>All {total} entries</h1>
<p class="lead">Every saved post, grouped by collection, best tier first. Each collection also has its own page:
<a href="/collections/">browse collections</a>.</p>
<nav class="jump" aria-label="Collections on this page">{jump}</nav>
{body}
</main>
</body></html>
"""


def main():
    rows = load_entries()
    if not rows:
        print("[render_entries] no entries — run `python scripts/cms.py migrate` first", file=sys.stderr)
        return 1
    OUT.mkdir(exist_ok=True)
    lookups = build_lookups(rows)
    for r in rows:
        rid = r.get("id")
        if not rid: continue
        (OUT / f"{safe_slug(rid)}.html").write_text(render_one(r, lookups), encoding="utf-8")
    (OUT / "index.html").write_text(render_index(rows), encoding="utf-8")
    print(f"[render_entries] wrote {len(rows)} entry pages + index.html to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
