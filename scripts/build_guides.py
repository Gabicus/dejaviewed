#!/usr/bin/env python3
"""Generate full guide pages for curated deep dives + rebuild site/guides/index.html.

Usage:
    python3 scripts/build_guides.py [--dry-run] [--dive-id ID] [--force] [--no-index] [--out-dir DIR]

- Source of dives: data/deep_dives.json (curated = suggested_by == "curated" or pinned).
  Missing why_it_matters / prerequisites fall back to data/manual_dives.json (same ids).
- Entries come from site/catalog.json (matched on id or post_id).
- Slug = dive id minus 'dd-insight-' -> site/guides/<slug>.html.
- Existing pages are skipped unless --force (hand-written pages may be richer).
- index.html is static HTML, so it is regenerated from the real set of *.html files
  in site/guides (plus pages this run would create) and the dive metadata.
- Read-only on data/*. Never writes data files.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
GUIDES = SITE / "guides"
DEEPER = SITE / "deeper"
DEEP_DIVES = ROOT / "data" / "deep_dives.json"
MANUAL_DIVES = ROOT / "data" / "manual_dives.json"
CATALOG = SITE / "catalog.json"

SLUG_PREFIX = "dd-insight-"
CURATOR = "6ab3"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prompt_systems import load_packs, section_markdown, PS_CSS, GUIDE_COPY_JS  # noqa: E402
PACKS = load_packs()

# Featured guides pinned to the top of the index (pink FEATURED card).
FEATURED = {
    "claude-mastery": (
        "From first install to advanced agent architecture — the definitive Claude reference. "
        "9 sections, 50+ sourced entries, model timeline, living document."
    ),
}

# --------------------------------------------------------------------------- guide page template
# Head/style copied verbatim from the curated-template pages (e.g. agent-architecture.html).
PAGE_HEAD = """<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · DejaViewed</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="../shared.css">
<script src="../shared.js"></script>
<style>
.chip.guide{{color:var(--c-guide);border-color:rgba(167,139,250,.28)}}
.chip.platform{{color:var(--c-platform);border-color:rgba(224,208,64,.28)}}
.chip.resource{{color:var(--c-resource);border-color:rgba(64,208,224,.28)}}
.card .actions{{display:flex;gap:8px;margin-top:14px;padding-top:14px;border-top:1px solid var(--border)}}
.btn{{flex:1;text-align:center;padding:8px 12px;border-radius:8px;font-size:12px;font-weight:700;border:1px solid var(--border);background:var(--panel);color:var(--text);transition:all .15s}}
.btn:hover{{background:var(--panel-2);border-color:var(--border-hi);color:#fff}}
.btn.primary{{background:linear-gradient(135deg,rgba(167,139,250,.2),rgba(244,114,182,.2));border-color:rgba(167,139,250,.4);color:#fff}}
.btn.primary:hover{{background:linear-gradient(135deg,rgba(167,139,250,.3),rgba(244,114,182,.3))}}
footer.site{{margin:60px 0 40px;padding-top:30px;border-top:1px solid var(--border);color:var(--text-mute);font-size:12.5px;text-align:center}}
footer.site a{{color:var(--text-dim)}}
footer.site code{{background:rgba(0,0,0,.5);border:1px solid var(--border);padding:2px 7px;border-radius:5px;color:var(--accent);font-family:'JetBrains Mono',Menlo,monospace;font-size:11.5px}}
.guide{{max-width:780px;margin:30px auto;padding:0 22px;font-size:16px;line-height:1.75}}
.guide h1,.guide h2,.guide h3{{letter-spacing:-0.015em;margin-top:1.7em}}
.guide h1{{font-size:34px;font-weight:900;margin-top:0;letter-spacing:-0.02em;background:linear-gradient(135deg,#fff 0%,#a78bfa 50%,#f472b6 100%);-webkit-background-clip:text;background-clip:text;color:transparent}}
.guide h2{{font-size:24px;color:var(--text);border-bottom:1px solid var(--border);padding-bottom:6px}}
.guide h3{{font-size:18px;color:#fff}}.guide p{{color:var(--text)}}
.guide code{{background:rgba(255,255,255,.07);padding:2px 6px;border-radius:4px;font-family:'JetBrains Mono',Menlo,monospace;font-size:.9em;color:var(--accent)}}
.guide pre{{background:rgba(0,0,0,.55);border:1px solid var(--border);padding:16px;border-radius:var(--radius-sm);overflow-x:auto}}
.guide pre code{{background:none;padding:0;color:var(--text)}}
.guide blockquote{{border-left:3px solid var(--accent);padding-left:16px;color:var(--text-dim);margin:16px 0}}
.guide a{{color:var(--accent);text-decoration:underline;text-decoration-color:rgba(167,139,250,.3)}}
.guide a:hover{{text-decoration-color:var(--accent)}}
.guide hr{{border:none;border-top:1px solid var(--border);margin:30px 0}}
.guide ul,.guide ol{{padding-left:24px}}
.confidence-badge{{display:inline-block;padding:4px 10px;border-radius:6px;font-size:11px;font-weight:900;text-transform:uppercase;letter-spacing:.08em;margin-bottom:18px}}
.confidence-badge.high{{background:rgba(76,218,140,.12);color:var(--c-repo);border:1px solid rgba(76,218,140,.4)}}
.confidence-badge.medium{{background:rgba(240,160,80,.12);color:var(--c-tool);border:1px solid rgba(240,160,80,.4)}}
@media(max-width:900px){{
  .layout{{grid-template-columns:1fr}}
  .sidebar{{position:relative;top:0;max-height:none}}
  .nav{{gap:4px}}
  .nav a{{padding:6px 10px;font-size:11px}}}}
</style></head><body>
<script>DV.mountHeader(document.body, 'home');</script>
<article class="guide">
  <div class="confidence-badge {confidence}">Source confidence: {confidence}</div>
{cross_link}  <div id="guide-body"></div>
</article>
<footer class="site"><div class="wrap"><a href="../index.html">← Back to DejaViewed</a> · curated by <a href="https://instagram.com/{curator}">@{curator}</a> · <code>dejaviewed</code></div></footer>
<script id="md" type="text/markdown">"""

PAGE_TAIL = """</script>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/dompurify@3/dist/purify.min.js"></script>
<script>
const raw=document.getElementById('md').textContent;
const html=DOMPurify.sanitize(marked.parse(raw));
document.getElementById('guide-body').innerHTML=html;
</script><style>""" + PS_CSS + "</style>" + GUIDE_COPY_JS + "</body></html>"

# Same markup the hand-written pages use for the deeper-dive cross-link.
CROSS_LINK = (
    '<div class="cross-link" style="margin:1.5rem 0;padding:12px 16px;background:rgba(251,191,36,0.06);'
    'border:1px solid rgba(251,191,36,0.2);border-radius:8px;font-size:0.9rem;">'
    '<strong style="color:#fbbf24;">See also:</strong> '
    '<a href="../deeper/{file}" style="color:#fbbf24;text-decoration:none;font-weight:600;">'
    'Deeper Dive — {title} →</a></div>\n'
)


# --------------------------------------------------------------------------- helpers
def load_json(p: Path):
    with p.open() as f:
        return json.load(f)


def slug_of(dive_id: str) -> str:
    return dive_id[len(SLUG_PREFIX):] if dive_id.startswith(SLUG_PREFIX) else dive_id


def is_curated(d: dict) -> bool:
    return d.get("suggested_by") == "curated" or bool(d.get("pinned"))


def class_label(cls: str, classes: dict) -> str:
    meta = classes.get(cls) if isinstance(classes, dict) else None
    if isinstance(meta, dict) and meta.get("label"):
        return meta["label"]
    return (cls or "").replace("_", " ").title()


def escape_script(md: str) -> str:
    """Neutralise any closing script tag inside the text/markdown block."""
    return re.sub(r"</(script)", r"&lt;/\1", md, flags=re.IGNORECASE)


def text_block(v) -> str:
    """Dive text fields may be a string or a list of strings (rendered as bullets)."""
    if isinstance(v, (list, tuple)):
        return "\n".join(f"- {str(x).strip()}" for x in v if str(x).strip())
    return str(v or "").strip()


HANDLE_RE = re.compile(r"[a-z0-9._]{1,30}")


def clean_handle(handle) -> str:
    """Valid lowercase IG handle or "" (catalog has scrape artifacts like creator='Edited')."""
    h = str(handle or "").lstrip("@").strip()
    return h if HANDLE_RE.fullmatch(h) else ""


def creator_link(handle: str) -> str:
    h = clean_handle(handle)
    return f"[@{h}](https://instagram.com/{h})" if h else "unknown"


def deeper_file(slug: str) -> str | None:
    for name in (f"deeper-insight-{slug}.html", f"{slug}.html"):
        if (DEEPER / name).exists():
            return name
    return None


def parse_date(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def date_range(entries: list[dict]) -> str:
    ds = sorted(d for d in (parse_date(e.get("date")) for e in entries) if d)
    if not ds:
        return ""
    return f"{ds[0].strftime('%b %Y')} – {ds[-1].strftime('%b %Y')}"


# --------------------------------------------------------------------------- markdown body
def build_markdown(d: dict, entries: list[dict], classes: dict, catalog_total: int) -> str:
    cmap = d.get("connection_map") or {}
    tools = sorted({t for e in entries for t in (e.get("tools") or []) if t})
    creators = sorted({clean_handle(e.get("creator")) for e in entries} - {""})

    out = [f"# {d['title']}", ""]
    out.append(
        f"**Insight class:** {class_label(d.get('class') or d.get('dive_class'), classes)} · "
        f"**Difficulty:** {d.get('execution_difficulty') or 'Unknown'} · "
        f"**Quality:** {d.get('quality_rating') or '?'}/5"
    )
    line = f"**Connected entries:** {len(entries)}"
    if tools:
        line += f" · **Tools:** {', '.join(tools)}"
    out += [line, "", "---", ""]

    out += ["## Thesis", "", text_block(d.get("thesis")), "", "---", ""]
    if d.get("why_it_matters"):
        out += ["## Why it matters", "", text_block(d["why_it_matters"]), "", "---", ""]

    out += ["## The evidence — connected entries", ""]
    for e in entries:
        eid = e.get("_dive_key")
        out.append(f"### {e.get('title') or eid}")
        out.append(f"**Creator:** {creator_link(e.get('creator'))} · **Tier:** {e.get('tier') or '?'}")
        if e.get("tools"):
            out.append(f"**Tools:** {', '.join(e['tools'])}")
        out.append("")
        role = cmap.get(eid) or cmap.get(e.get("id")) or cmap.get(e.get("post_id"))
        if role:
            out += [f"> {role}", ""]
        if e.get("summary"):
            out += [text_block(e["summary"]), ""]
        if e.get("url"):
            out.append(f"[View original post]({e['url']})")
    out += ["", "---", ""]

    if d.get("action_sketch"):
        out += ["## Action sketch — how to implement this", "", text_block(d["action_sketch"]), "", "---", ""]
    if d.get("prerequisites"):
        out += ["## Prerequisites", "", text_block(d["prerequisites"]), "", "---", ""]

    if tools:
        out += ["## Key tools and resources", ""] + [f"- **{t}**" for t in tools] + [""]
    if creators:
        out += ["## Creators to follow", ""] + [f"- {creator_link(c)}" for c in creators] + [""]
    out += ["---", ""]

    pack = PACKS.get(slug_of(d["id"]))
    if pack:
        out += [section_markdown(pack), ""]

    out += [
        "## Related deep dives", "",
        f"Browse more deep dives at [DejaViewed](../catalog.html) — {catalog_total} entries across the full catalog.",
        "", "---", "",
        f"*Generated {date.today().isoformat()} · curated by [@{CURATOR}](https://instagram.com/{CURATOR}) for DejaViewed*",
        "",
    ]
    return "\n".join(out)


def build_page(d: dict, entries: list[dict], classes: dict, catalog_total: int) -> str:
    slug = slug_of(d["id"])
    q = d.get("quality_rating") or 0
    confidence = "high" if isinstance(q, (int, float)) and q >= 5 else "medium"
    df = deeper_file(slug)
    cross = "  " + CROSS_LINK.format(file=df, title=html.escape(d["title"])) if df else ""
    head = PAGE_HEAD.format(
        title=html.escape(d["title"]),
        confidence=confidence,
        cross_link=cross,
        curator=CURATOR,
    )
    return head + escape_script(build_markdown(d, entries, classes, catalog_total)) + PAGE_TAIL


# --------------------------------------------------------------------------- index page
INDEX_HEAD = """<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Guides — DejaViewed</title>
<link rel="stylesheet" href="../shared.css">
<style>
  .guides-container { max-width: 900px; margin: 2rem auto; padding: 0 1.5rem; }
  .guides-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; margin-top: 1.5rem; }
  .guide-card:hover { border-color: rgba(125,211,252,0.3) !important; }
  .filter-bar { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 1rem; }
  .filter-pill.active { background: rgba(125,211,252,0.15) !important; border-color: rgba(125,211,252,0.3) !important; color: #7dd3fc !important; }
</style>
<script src="../shared.js" defer></script>
<script>document.addEventListener("DOMContentLoaded",()=>window.DV&&DV.mountHeader(document.body,"guides"))</script>
</head><body>
"""

INDEX_TAIL = """  </div>
</div>

<script>
document.querySelectorAll('.filter-pill').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const tier = btn.dataset.tier;
    document.querySelectorAll('.guide-card').forEach(card => {
      card.style.display = (tier === 'all' || card.dataset.tier === tier) ? 'block' : 'none';
    });
  });
});
</script>"""

PILL = ('<button class="filter-pill{active}" data-tier="{tier}" style="padding:6px 14px;border-radius:20px;'
        'border:1px solid {border};background:{bg};color:{color};cursor:pointer;font-size:0.85rem;">{label} ({n})</button>')

BADGE_STYLE = {
    "featured": "background:linear-gradient(135deg,rgba(167,139,250,.25),rgba(244,114,182,.25));color:#f472b6;border:1px solid rgba(244,114,182,.4);",
    "guide": "background:rgba(167,139,250,.18);color:#a78bfa;border:1px solid rgba(167,139,250,.35);",
    "standalone": "background:rgba(125,211,252,.12);color:#7dd3fc;border:1px solid rgba(125,211,252,.25);",
}
CARD_STYLE = {
    "featured": "background:linear-gradient(135deg,rgba(167,139,250,.04),rgba(244,114,182,.04));border-radius:12px;border:1px solid rgba(244,114,182,.35);",
    "guide": "background:rgba(255,255,255,0.03);border-radius:12px;border:1px solid rgba(167,139,250,0.25);",
    "standalone": "background:rgba(255,255,255,0.03);border-radius:12px;border:1px solid rgba(255,255,255,0.06);",
}


def card_html(c: dict) -> str:
    tier = c["tier"]
    featured = tier == "featured"
    title_style = ("font-weight:900;color:#fff;flex:1;min-width:0;font-size:1.1rem;" if featured
                   else "font-weight:600;color:#e2e8f0;flex:1;min-width:0;")
    dr = (f'<span style="color:#64748b;font-size:0.75rem;"> · {c["range"]}</span>' if c.get("range") else "")
    lines = [
        f'<a href="{c["slug"]}.html" class="guide-card" data-tier="{tier}" style="display:block;padding:16px;{CARD_STYLE[tier]}text-decoration:none;transition:border-color 0.2s;">',
        '  <div style="display:flex;align-items:flex-start;gap:8px;">',
        f'    <div style="{title_style}">{html.escape(c["title"], quote=False)}</div>',
        f'    <span style="display:inline-block;padding:2px 7px;border-radius:4px;font-size:9px;font-weight:900;letter-spacing:.06em;text-transform:uppercase;{BADGE_STYLE[tier]}margin-left:auto;flex-shrink:0;">{tier.upper()}</span>',
        "  </div>",
        f'  <div style="font-size:0.8rem;color:#94a3b8;margin-top:4px;">{c["meta"]}{dr}</div>',
    ]
    if featured and c.get("blurb"):
        lines.append(f'  <div style="font-size:0.8rem;color:#e2e8f0;margin-top:8px;line-height:1.5;padding:8px;background:rgba(244,114,182,0.05);border-radius:6px;">{html.escape(c["blurb"], quote=False)}</div>')
    lines.append("</a>")
    return "\n".join(lines)


def page_title(path: Path) -> str | None:
    try:
        m = re.search(r"<title>(.*?)</title>", path.read_text(errors="replace"), re.S)
    except OSError:
        return None
    if not m:
        return None
    t = html.unescape(m.group(1)).strip()
    return re.sub(r"\s*[·—|-]\s*DejaViewed\s*$", "", t).strip() or None


def build_index(page_slugs: set[str], curated: dict[str, dict], resolved: dict[str, list[dict]]) -> str:
    cards = []
    covered: set[str] = set()
    for slug in page_slugs:
        d = curated.get(slug)
        if d:
            ents = resolved.get(slug, [])
            covered.update(e["_dive_key"] for e in ents)
            tier = "featured" if slug in FEATURED else "guide"
            cards.append({
                "slug": slug, "tier": tier, "title": d["title"],
                "meta": f"{d.get('class') or d.get('dive_class') or 'guide'} · {len(ents)} entries",
                "range": date_range(ents), "blurb": FEATURED.get(slug), "count": len(ents),
            })
        else:
            title = page_title(GUIDES / f"{slug}.html") or slug.replace("-", " ").title()
            cards.append({"slug": slug, "tier": "standalone", "title": title,
                          "meta": "standalone guide", "count": 0})

    order = {"featured": 0, "guide": 1, "standalone": 2}
    cards.sort(key=lambda c: (order[c["tier"]], -c["count"] if c["tier"] != "standalone" else 0, c["slug"]))
    n = {t: sum(1 for c in cards if c["tier"] == t) for t in order}

    pills = [
        PILL.format(active=" active", tier="all", border="rgba(125,211,252,0.3)", bg="rgba(125,211,252,0.15)",
                    color="#7dd3fc", label="All", n=len(cards)),
        PILL.format(active="", tier="featured", border="rgba(244,114,182,0.3)", bg="transparent",
                    color="#f472b6", label="Featured", n=n["featured"]),
        PILL.format(active="", tier="guide", border="rgba(167,139,250,0.25)", bg="transparent",
                    color="#a78bfa", label="Guides", n=n["guide"]),
        PILL.format(active="", tier="standalone", border="rgba(125,211,252,0.15)", bg="transparent",
                    color="#7dd3fc", label="Standalone", n=n["standalone"]),
    ]
    body = [
        INDEX_HEAD,
        '<div class="guides-container">',
        '  <h1 style="font-size:1.8rem;margin-bottom:0.25rem;">Guides</h1>',
        f'  <p style="color:#94a3b8;margin-bottom:1rem;">{len(cards)} deep dive guides connecting ideas across {len(covered)} entries</p>',
        "  ",
        '  <div class="filter-bar">',
        "    " + "\n".join(pills),
        "  </div>",
        "  ",
        '  <div class="guides-grid" id="guides-grid">',
        "    " + "\n".join(card_html(c) for c in cards),
        INDEX_TAIL,
    ]
    body.append("</body></html>")
    return "\n".join(body)


# --------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="print what would be written; write nothing")
    ap.add_argument("--dive-id", help="only build this dive (full id, e.g. dd-insight-agent-architecture)")
    ap.add_argument("--force", action="store_true", help="overwrite existing guide pages")
    ap.add_argument("--no-index", action="store_true", help="do not regenerate guides/index.html")
    ap.add_argument("--out-dir", type=Path, help="write pages here instead of site/guides (preview/diff)")
    args = ap.parse_args()

    dd = load_json(DEEP_DIVES)
    classes = dd.get("classes") or {}
    manual = {m["id"]: m for m in load_json(MANUAL_DIVES).get("manual_dives", [])} if MANUAL_DIVES.exists() else {}
    cat = load_json(CATALOG)
    entries = cat["entries"] if isinstance(cat, dict) else cat
    by_id: dict[str, dict] = {}
    for e in entries:
        for k in (e.get("id"), e.get("post_id")):
            if k:
                by_id.setdefault(k, e)

    curated: dict[str, dict] = {}
    for d in dd.get("deep_dives", []):
        if not is_curated(d):
            continue
        merged = dict(d)
        for k, v in manual.get(d["id"], {}).items():
            if not merged.get(k) and v:
                merged[k] = v  # fill gaps (why_it_matters, prerequisites) from manual_dives
        curated[slug_of(d["id"])] = merged

    # resolve entries + validate ids
    resolved: dict[str, list[dict]] = {}
    bad: dict[str, list[str]] = {}
    bad_creators: dict[str, list[str]] = {}
    for slug, d in curated.items():
        ents = []
        for eid in d.get("entry_ids") or []:
            e = by_id.get(eid)
            if e is None:
                bad.setdefault(d["id"], []).append(eid)
                continue
            if e.get("creator") and not clean_handle(e.get("creator")):
                bad_creators.setdefault(d["id"], []).append(f"{eid}={e.get('creator')!r}")
            ents.append({**e, "_dive_key": eid})
        resolved[slug] = ents

    targets = list(curated)
    if args.dive_id:
        s = slug_of(args.dive_id)
        if s not in curated:
            print(f"error: {args.dive_id} is not a curated dive in {DEEP_DIVES.relative_to(ROOT)}", file=sys.stderr)
            return 2
        targets = [s]

    out_dir = args.out_dir or GUIDES
    new, overwrite, skipped = [], [], []
    for slug in targets:
        exists = (GUIDES / f"{slug}.html").exists()
        if exists and not args.force:
            skipped.append(slug)
            continue
        (overwrite if exists else new).append(slug)
        page = build_page(curated[slug], resolved[slug], classes, len(entries))
        dest = out_dir / f"{slug}.html"
        if args.dry_run:
            print(f"[dry-run] would {'overwrite' if exists else 'create'} {dest.relative_to(ROOT) if dest.is_relative_to(ROOT) else dest} "
                  f"({len(resolved[slug])} entries, {len(page):,} bytes"
                  f"{', deeper link' if deeper_file(slug) else ''})")
        else:
            out_dir.mkdir(parents=True, exist_ok=True)
            dest.write_text(page)
            print(f"wrote {dest}")

    print()
    print(f"curated dives: {len(curated)}  | targeted: {len(targets)}")
    print(f"new: {len(new)}  overwrite: {len(overwrite)}  skipped (exists, no --force): {len(skipped)}")
    if new:
        print("  new:", ", ".join(new))
    if skipped:
        print("  skipped:", ", ".join(skipped))
    if bad:
        print("\nWARNING: entry ids missing from site/catalog.json:")
        for did, ids in bad.items():
            print(f"  {did}: {', '.join(ids)}")
    else:
        print("entry ids: all resolve in site/catalog.json")
    if bad_creators:
        print("\nWARNING: malformed creator handles (rendered as 'unknown'; fix in catalog):")
        for did, ids in bad_creators.items():
            print(f"  {did}: {', '.join(ids)}")

    if not args.no_index:
        page_slugs = {p.stem for p in GUIDES.glob("*.html") if p.stem != "index"} | set(new)
        idx = build_index(page_slugs, curated, resolved)
        dest = out_dir / "index.html"
        n_feat = sum(1 for s in page_slugs if s in curated and s in FEATURED)
        n_guide = sum(1 for s in page_slugs if s in curated) - n_feat
        summary = f"{len(page_slugs)} cards (featured {n_feat}, guide {n_guide}, standalone {len(page_slugs) - n_feat - n_guide})"
        if args.dry_run:
            print(f"\n[dry-run] would regenerate {dest.relative_to(ROOT) if dest.is_relative_to(ROOT) else dest}: {summary}")
        else:
            dest.write_text(idx)
            print(f"\nwrote {dest}: {summary}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
