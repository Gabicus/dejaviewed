#!/usr/bin/env python3
"""Generate machine-readable API files for agent/AI discoverability.

Outputs:
  site/api/catalog.json    — full catalog with all fields
  site/api/creators.json   — creator index with post counts
  site/api/tools.json      — tool/technique index
  site/api/collections.json — collection summaries
  site/sitemap.xml         — XML sitemap for crawlers
  site/e/*.html            — per-entry detail pages (via render_entries.py)
"""
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
API = SITE / "api"
API.mkdir(exist_ok=True)


def _safe_slug(rid: str) -> str:
    """Must match render_entries.safe_slug (entry page filename)."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in rid)


def _thumb_rel(e: dict) -> str:
    """Site-relative thumb path that actually exists on disk ('' if none).
    Thumbs are saved as thumb/<id with '/' -> '_'>.jpg (dots kept)."""
    pid = e.get("post_id") or e.get("id") or ""
    if not pid:
        return ""
    rel = f"thumb/{pid.replace('/', '_')}.jpg"
    return rel if (SITE / rel).is_file() else ""

# Sitemap = canonical, indexable HTML only (SEO-08). feed.xml, llms*.txt and api/*.json stay
# discoverable through robots.txt and llms.txt; graph/board/search/about/links are left out.
SITEMAP_TOP = [("index.html", "1.0", "weekly"), ("start-here.html", "0.9", "monthly"),
               ("method.html", "0.8", "monthly"), ("catalog.html", "0.9", "weekly"),
               ("prompts.html", "0.8", "weekly"), ("system-prompts.html", "0.8", "monthly"),
               ("flow.html", "0.8", "weekly")]
SITEMAP_DIRS = [("collections", "0.7", "weekly"), ("guides", "0.9", "weekly"), ("deeper", "0.8", "monthly"),
                ("tools", "0.8", "weekly"), ("compare", "0.8", "monthly"), ("best", "0.8", "monthly")]


_NOINDEX_RE = re.compile(r'<meta\s+name="robots"\s+content="[^"]*noindex', re.I)


def sitemap_rels() -> list[tuple[str, str, str]]:
    rels = [(r, p, f) for r, p, f in SITEMAP_TOP if (SITE / r).is_file()]
    for sub, pri, freq in SITEMAP_DIRS:
        d = SITE / sub
        if not d.is_dir():
            continue
        if (d / "index.html").is_file():
            rels.append((f"{sub}/index.html", pri, freq))
        for page in sorted(d.glob("*.html")):
            if page.name == "index.html" or page.name.startswith("_") or page.stem == "404":
                continue
            # noindex pages (thin tool hubs etc.) must not be listed: a listed-but-noindex URL is a crawl error
            if _NOINDEX_RE.search(page.read_text(encoding="utf-8", errors="replace")[:6000]):
                continue
            rels.append((f"{sub}/{page.name}", pri, freq))
    if (SITE / "e" / "index.html").is_file():
        rels.append(("e/index.html", "0.7", "weekly"))
    cat = json.loads((SITE / "catalog.json").read_text(encoding="utf-8"))
    for e in cat.get("entries", []):
        eid = e.get("id", "")
        # entry pages are written under render_entries.safe_slug(id) — ids with '/' or '.'
        # (e.g. "MoonshotAI/Kimi-K2.5") live at e/MoonshotAI_Kimi-K2_5.html
        rel = f"e/{_safe_slug(eid)}.html" if eid else ""
        if rel and (SITE / rel).is_file():
            rels.append((rel, "0.5", "monthly"))
    return rels


def sitemap_xml(fresh=None) -> str:
    """<lastmod> = last real content change (build_seo.Freshness, data/seo/content_hashes.json).
    Saves the freshness store only when it created it (build_seo saves its own)."""
    from xml.sax.saxutils import escape as _esc
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build_seo import Freshness, canonical_url
    own = fresh is None
    fresh = fresh or Freshness()
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for rel, pri, freq in sitemap_rels():
        url = canonical_url(rel)
        if url not in fresh.seen:
            fresh.observe(rel, (SITE / rel).read_text(encoding="utf-8", errors="replace"))
        lm = fresh.dates(rel)[1].isoformat()
        out.append(f"  <url><loc>{_esc(url)}</loc><lastmod>{lm}</lastmod>"
                   f"<changefreq>{freq}</changefreq><priority>{pri}</priority></url>")
    out.append("</urlset>")
    if own:
        fresh.save()
    return "\n".join(out) + "\n"


def main():
    data = json.loads((SITE / "catalog.json").read_text(encoding="utf-8"))
    entries = data["entries"]

    creators = defaultdict(lambda: {"posts": 0, "collections": set(), "tiers": Counter(), "types": Counter()})
    for e in entries:
        c = e.get("creator", "")
        if not c:
            continue
        creators[c]["posts"] += 1
        creators[c]["collections"].add(e.get("collection", ""))
        creators[c]["tiers"][e.get("tier", "C")] += 1
        creators[c]["types"][e.get("type", "resource")] += 1

    creators_out = []
    for name, info in sorted(creators.items(), key=lambda x: -x[1]["posts"]):
        creators_out.append({
            "handle": name,
            "post_count": info["posts"],
            "collections": sorted(info["collections"] - {""}),
            "tier_distribution": dict(info["tiers"]),
            "type_distribution": dict(info["types"]),
        })

    tools_out = {}
    for key_field, label in [("tools", "tools"), ("techniques", "techniques"), ("domains", "domains")]:
        idx = defaultdict(list)
        for e in entries:
            for v in (e.get(key_field) or []):
                idx[v].append({"id": e["id"], "title": e.get("title", ""), "tier": e.get("tier", "C")})
        tools_out[label] = {k: v for k, v in sorted(idx.items(), key=lambda x: -len(x[1]))}

    collections_out = []
    coll_groups = defaultdict(list)
    for e in entries:
        coll_groups[e.get("collection", "")].append(e)
    for coll, posts in sorted(coll_groups.items()):
        if not coll:
            continue
        tiers = Counter(p.get("tier", "C") for p in posts)
        types = Counter(p.get("type", "resource") for p in posts)
        collections_out.append({
            "name": coll,
            "post_count": len(posts),
            "tier_distribution": dict(tiers),
            "type_distribution": dict(types),
            "creators": len(set(p.get("creator", "") for p in posts)),
        })

    (API / "catalog.json").write_text(json.dumps({
        "version": "2.0",
        "generated": datetime.now().isoformat(),
        "total_entries": len(entries),
        "entries": [{
            "id": e.get("id"), "title": e.get("title"), "url": e.get("url"),
            "creator": e.get("creator"), "type": e.get("type"), "tier": e.get("tier"),
            "collection": e.get("collection"), "summary": e.get("summary"),
            "tools": e.get("tools", []), "techniques": e.get("techniques", []),
            "domains": e.get("domains", []), "medium": e.get("medium", ""),
            "style_tags": e.get("style_tags", []), "tags": e.get("tags", []),
            "thumb": _thumb_rel(e),
        } for e in entries]
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    (API / "creators.json").write_text(json.dumps({
        "total_creators": len(creators_out),
        "creators": creators_out
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    (API / "tools.json").write_text(json.dumps(tools_out, ensure_ascii=False, indent=2), encoding="utf-8")

    (API / "collections.json").write_text(json.dumps({
        "collections": collections_out
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    # Deep dives API endpoint
    dd_path = ROOT / "data" / "deep_dives.json"
    if dd_path.exists():
        try:
            dd_data = json.loads(dd_path.read_text(encoding="utf-8"))
            (API / "deep_dives.json").write_text(
                json.dumps(dd_data, ensure_ascii=False, indent=2), encoding="utf-8")
        except (json.JSONDecodeError, KeyError) as e:
            print(f"  Warning: deep_dives.json parse failed: {e}")

    # Render per-entry detail pages first, so the sitemap sees every page on disk
    render_script = ROOT / "scripts" / "render_entries.py"
    if render_script.exists():
        r = subprocess.run(
            [sys.executable, str(render_script)],
            capture_output=True, text=True
        )
        if r.returncode != 0:
            print(f"[build_api] WARNING: render_entries.py failed:\n{r.stderr}", file=sys.stderr)
        elif r.stdout.strip():
            print(r.stdout.strip())

    sitemap = sitemap_xml()
    (SITE / "sitemap.xml").write_text(sitemap, encoding="utf-8")

    # llms-full.txt — complete catalog dump for LLM agents (clean URLs; guides first)
    from build_seo import BASE, guide_index
    n_colls = len({e.get("collection", "") for e in entries} - {""})
    guides = guide_index()
    lines = [f"# DejaViewed — Full Catalog ({len(entries)} entries, {n_colls} collections, "
             f"{len(guides['guides'])} guides, {len(guides['deeper'])} deeper dives)",
             f"Updated: {datetime.now().strftime('%Y-%m-%d')}",
             f"Site map for agents: {BASE}/llms.txt · How it is built: {BASE}/method · JSON: {BASE}/api/catalog.json",
             "Usage: captions and transcripts belong to their creators (each entry links its source post); "
             f"titles, summaries, tiers and tags are DejaViewed's own curation. Terms: {BASE}/method#terms", ""]
    lines += ["# Guides", ""]
    for g in guides["guides"]:
        lines.append(f"## {g['title']}")
        lines.append(f"- URL: {g['url']}")
        if g["answer"]:
            lines.append(f"- In short: {g['answer']}")
        lines.append("")
    lines += ["# Entries", ""]
    for e in entries:
        lines.append(f"## {e.get('title', 'Untitled')}")
        lines.append(f"- Creator: @{e.get('creator', '')} | Type: {e.get('type', '')} | Tier: {e.get('tier', '')} | Collection: {e.get('collection', '')}")
        if e.get("id") and (SITE / "e" / f"{_safe_slug(e['id'])}.html").is_file():
            lines.append(f"- Page: {BASE}/e/{_safe_slug(e['id'])}")
        if e.get("url"): lines.append(f"- Source: {e['url']}")
        parts = []
        if e.get("tools"): parts.append(f"Tools: {', '.join(e['tools'])}")
        if e.get("techniques"): parts.append(f"Techniques: {', '.join(e['techniques'])}")
        if e.get("domains"): parts.append(f"Domains: {', '.join(e['domains'])}")
        if e.get("medium"): parts.append(f"Medium: {e['medium']}")
        if parts: lines.append(f"- {' | '.join(parts)}")
        if e.get("summary"): lines.append(f"- {e['summary']}")
        lines.append("")
    # Append deep dives to llms-full.txt
    dd_data = {}
    if dd_path.exists():
        try:
            dd_data = json.loads(dd_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, KeyError):
            dd_data = {}
        dives = dd_data.get("deep_dives", [])
        lines.append("# Deep Dives — Curated Insight Connections")
        lines.append("")
        for d in dives:
            title = d.get("title", "Untitled")
            thesis = d.get("thesis", d.get("summary", ""))
            cls = d.get("class") or d.get("dive_class") or d.get("type", "")
            rating = d.get("quality_rating", "")
            difficulty = d.get("execution_difficulty", "")
            entry_ids = d.get("entry_ids", [])
            slug = str(d.get("id", "")).replace("dd-insight-", "", 1)
            lines.append(f"## {title}")
            if slug and (SITE / "guides" / f"{slug}.html").is_file():
                lines.append(f"- Guide: {BASE}/guides/{slug}")
            if slug and (SITE / "deeper" / f"deeper-insight-{slug}.html").is_file():
                lines.append(f"- Deeper dive: {BASE}/deeper/deeper-insight-{slug}")
            if cls: lines.append(f"- Class: {cls}")
            if rating: lines.append(f"- Quality: {rating}/5")
            if difficulty: lines.append(f"- Difficulty: {difficulty}")
            if thesis: lines.append(f"- Thesis: {thesis}")
            if entry_ids: lines.append(f"- Entries: {', '.join(entry_ids[:8])}")
            action = d.get("action_sketch", "")
            if action: lines.append(f"- Action: {action}")
            lines.append("")

    (SITE / "llms-full.txt").write_text("\n".join(lines), encoding="utf-8")

    dd_count = len(dd_data.get("deep_dives", []))
    print(f"API: {len(entries)} entries, {len(creators_out)} creators, "
          f"{sum(len(v) for v in tools_out.values())} tool/tech/domain entries, {dd_count} deep dives")
    print(f"Sitemap: {sitemap.count('<url>')} URLs (indexable HTML only)")
    print(f"llms-full.txt: {len(lines)} lines")


if __name__ == "__main__":
    main()
