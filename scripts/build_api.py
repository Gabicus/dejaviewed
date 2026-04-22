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
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
API = SITE / "api"
API.mkdir(exist_ok=True)

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
            "thumb": f'thumb/{e.get("post_id","")}.jpg' if e.get("post_id") else "",
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

    sitemap = ['<?xml version="1.0" encoding="UTF-8"?>',
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
               '  <url><loc>https://dejaviewed.com/</loc><priority>1.0</priority></url>',
               '  <url><loc>https://dejaviewed.com/graph.html</loc><priority>0.8</priority></url>',
               '  <url><loc>https://dejaviewed.com/graph-cosmos.html</loc><priority>0.8</priority></url>',
               '  <url><loc>https://dejaviewed.com/board.html</loc><priority>0.7</priority></url>',
               '  <url><loc>https://dejaviewed.com/admin.html</loc><priority>0.3</priority></url>',
               '  <url><loc>https://dejaviewed.com/api/catalog.json</loc><priority>0.9</priority></url>',
               '  <url><loc>https://dejaviewed.com/api/creators.json</loc><priority>0.7</priority></url>',
               '  <url><loc>https://dejaviewed.com/api/tools.json</loc><priority>0.7</priority></url>',
               '  <url><loc>https://dejaviewed.com/api/collections.json</loc><priority>0.7</priority></url>',
               '  <url><loc>https://dejaviewed.com/api/deep_dives.json</loc><priority>0.8</priority></url>']
    for coll in ["ai1", "ai2", "ai3", "ai4", "ai5", "quant", "art-i-like", "art-inspiration"]:
        sitemap.append(f'  <url><loc>https://dejaviewed.com/{coll}.html</loc><priority>0.7</priority></url>')
    sitemap.append('  <url><loc>https://dejaviewed.com/llms.txt</loc><priority>0.6</priority></url>')
    sitemap.append('  <url><loc>https://dejaviewed.com/llms-full.txt</loc><priority>0.6</priority></url>')
    for e in entries:
        eid = e.get("id", "")
        if eid:
            from xml.sax.saxutils import escape
            sitemap.append(f'  <url><loc>https://dejaviewed.com/e/{escape(eid)}.html</loc><priority>0.5</priority></url>')
    sitemap.append('</urlset>')
    (SITE / "sitemap.xml").write_text("\n".join(sitemap), encoding="utf-8")

    # llms-full.txt — complete catalog dump for LLM agents
    lines = [f"# DejaViewed — Full Catalog ({len(entries)} entries)", ""]
    for e in entries:
        lines.append(f"## {e.get('title', 'Untitled')}")
        lines.append(f"- Creator: @{e.get('creator', '')} | Type: {e.get('type', '')} | Tier: {e.get('tier', '')} | Collection: {e.get('collection', '')}")
        if e.get("url"): lines.append(f"- URL: {e['url']}")
        parts = []
        if e.get("tools"): parts.append(f"Tools: {', '.join(e['tools'])}")
        if e.get("techniques"): parts.append(f"Techniques: {', '.join(e['techniques'])}")
        if e.get("domains"): parts.append(f"Domains: {', '.join(e['domains'])}")
        if e.get("medium"): parts.append(f"Medium: {e['medium']}")
        if parts: lines.append(f"- {' | '.join(parts)}")
        if e.get("summary"): lines.append(f"- {e['summary']}")
        lines.append("")
    # Append deep dives to llms-full.txt
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
            lines.append(f"## {title}")
            if cls: lines.append(f"- Class: {cls}")
            if rating: lines.append(f"- Quality: {rating}/5")
            if difficulty: lines.append(f"- Difficulty: {difficulty}")
            if thesis: lines.append(f"- Thesis: {thesis}")
            if entry_ids: lines.append(f"- Entries: {', '.join(entry_ids[:8])}")
            action = d.get("action_sketch", "")
            if action: lines.append(f"- Action: {action}")
            lines.append("")

    (SITE / "llms-full.txt").write_text("\n".join(lines), encoding="utf-8")

    dd_count = len(dd_data.get("deep_dives", [])) if dd_path.exists() else 0
    print(f"API: {len(entries)} entries, {len(creators_out)} creators, "
          f"{sum(len(v) for v in tools_out.values())} tool/tech/domain entries, {dd_count} deep dives")
    print(f"Sitemap: {len(entries) + 10} URLs")
    print(f"llms-full.txt: {len(lines)} lines")

    # Render per-entry detail pages
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


if __name__ == "__main__":
    main()
