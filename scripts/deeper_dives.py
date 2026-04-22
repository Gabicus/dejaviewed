#!/usr/bin/env python3
"""Generate Deeper Dive pages — full narrative pages from selected deep dives.

Tier 1 = auto-detected clusters + curated insight cards (deep_dives.py)
Tier 2 = Deeper Dives — agentic narrative pages with full reasoning

Usage:
  python scripts/deeper_dives.py [--dive-id dd-xxx] [--all-curated] [--dry-run]
"""
import json
import sys
import os
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "site" / "catalog.json"
DEEP_DIVES_JSON = ROOT / "data" / "deep_dives.json"
DEEPER_DIR = ROOT / "site" / "deeper"
DEEPER_DATA = ROOT / "data" / "deeper_dives.json"
TEMPLATE = ROOT / "scripts" / "deeper_template.html"


def load_catalog():
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def load_deep_dives():
    return json.loads(DEEP_DIVES_JSON.read_text(encoding="utf-8"))


def get_entry_map(catalog):
    return {e["id"]: e for e in catalog["entries"]}


def build_deeper_page(dive: dict, entry_map: dict, catalog: dict) -> dict:
    """Build a Deeper Dive data structure from a Tier 1 dive.

    Returns a dict with all fields needed to render the HTML page.
    The actual narrative generation happens via Claude (agentic reasoning).
    This function prepares the structured context for that generation.
    """
    entries = [entry_map[eid] for eid in dive.get("entry_ids", []) if eid in entry_map]

    creators = sorted(set(e.get("creator", "") for e in entries if e.get("creator")))
    all_tools = sorted(set(t for e in entries for t in (e.get("tools") or [])))
    all_techniques = sorted(set(t for e in entries for t in (e.get("techniques") or [])))
    all_domains = sorted(set(d for e in entries for d in (e.get("domains") or [])))

    entry_briefs = []
    for e in entries:
        entry_briefs.append({
            "id": e["id"],
            "title": e.get("title", ""),
            "summary": e.get("summary", ""),
            "creator": e.get("creator", ""),
            "tier": e.get("tier", "C"),
            "type": e.get("type", ""),
            "tools": e.get("tools", []),
            "techniques": e.get("techniques", []),
            "url": e.get("url", ""),
            "has_guide": e.get("has_guide", False),
            "deep_dive_slug": e.get("deep_dive_slug", ""),
        })

    slug = dive["id"].replace("dd-", "deeper-")

    return {
        "id": slug,
        "source_dive_id": dive["id"],
        "title": dive.get("title", "Untitled"),
        "dive_type": dive.get("type", "") or dive.get("class", ""),
        "thesis": dive.get("thesis", ""),
        "why_it_matters": dive.get("why_it_matters", ""),
        "action_sketch": dive.get("action_sketch", ""),
        "prerequisites": dive.get("prerequisites", ""),
        "quality_rating": dive.get("quality_rating", 0),
        "execution_difficulty": dive.get("execution_difficulty", ""),
        "creators": creators,
        "tools": all_tools,
        "techniques": all_techniques,
        "domains": all_domains,
        "entries": entry_briefs,
        "entry_count": len(entry_briefs),
        "slug": slug,
        "generated_at": datetime.now().isoformat(),
        "narrative": "",  # filled by agentic generation
        "sections": [],   # filled by agentic generation
    }


def render_html(deeper: dict) -> str:
    """Render a Deeper Dive to a standalone HTML page."""
    title = deeper["title"]
    thesis = deeper.get("thesis", "")
    narrative = deeper.get("narrative", thesis)
    sections = deeper.get("sections", [])
    entries = deeper.get("entries", [])

    sections_html = ""
    for sec in sections:
        sections_html += f'<section class="dd-sec"><h2>{_esc(sec.get("heading", ""))}</h2>\n'
        sections_html += f'<div class="dd-sec-body">{_esc(sec.get("body", ""))}</div></section>\n'

    entries_html = ""
    for e in entries:
        tier_cls = f"t{e.get('tier', 'C')}"
        safe_id = e["id"].replace("/", "_")
        entries_html += f'''<div class="dd-entry">
  <img src="../thumb/{safe_id}.jpg" alt="" class="dd-entry-thumb" onerror="this.style.display='none'">
  <div class="dd-entry-info">
    <div class="dd-entry-title">{_esc(e.get("title", e["id"]))}</div>
    <div class="dd-entry-meta"><span class="tier-badge {tier_cls}">{e.get("tier","C")}</span> {_esc(e.get("type",""))} · @{_esc(e.get("creator",""))}</div>
    <div class="dd-entry-summary">{_esc(e.get("summary", ""))}</div>
    {f'<a href="../guides/{e["deep_dive_slug"]}.html" class="dd-entry-guide">Read Guide →</a>' if e.get("has_guide") and e.get("deep_dive_slug") else ""}
  </div>
</div>\n'''

    tools_html = " · ".join(f"<span class='tool-pill'>{_esc(t)}</span>" for t in deeper.get("tools", []))

    return f'''<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><title>{_esc(title)} — Deeper Dive — DejaViewed</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="../shared.css">
<script src="../shared.js"></script>
<style>
body{{background:var(--bg);color:var(--text);font-family:'JetBrains Mono','Fira Code',monospace}}
.deeper-wrap{{max-width:860px;margin:24px auto 80px;padding:0 20px}}
.deeper-hero{{margin-bottom:32px}}
.deeper-hero h1{{font-size:28px;font-weight:900;line-height:1.2;background:linear-gradient(135deg,#fff 30%,var(--accent));-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin:0 0 12px}}
.deeper-hero .type-label{{display:inline-block;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:700;background:rgba(167,139,250,.15);color:var(--accent);margin-bottom:12px}}
.deeper-hero .thesis{{font-size:15px;line-height:1.6;color:var(--text-dim);font-style:italic;margin:0 0 16px;padding-left:16px;border-left:3px solid var(--accent)}}
.deeper-hero .tools{{font-size:11px;color:var(--text-mute);margin-top:12px}}
.tool-pill{{display:inline-block;padding:2px 8px;border-radius:999px;background:rgba(255,255,255,.06);border:1px solid var(--border);margin:2px}}
.dd-narrative{{font-size:14px;line-height:1.7;color:var(--text);margin:24px 0}}
.dd-narrative p{{margin:0 0 14px}}
.dd-sec{{margin:28px 0}}
.dd-sec h2{{font-size:18px;font-weight:800;color:#fff;margin:0 0 10px}}
.dd-sec-body{{font-size:13.5px;line-height:1.65;color:var(--text-dim)}}
.dd-entries{{margin:32px 0}}
.dd-entries h2{{font-size:16px;font-weight:800;color:#fff;margin:0 0 14px}}
.dd-entry{{display:flex;gap:14px;background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:12px 14px;margin-bottom:10px}}
.dd-entry-thumb{{width:80px;height:60px;object-fit:cover;border-radius:6px;flex-shrink:0}}
.dd-entry-title{{font-size:13px;font-weight:700;color:var(--text)}}
.dd-entry-meta{{font-size:11px;color:var(--text-mute);margin:3px 0}}
.dd-entry-summary{{font-size:12px;color:var(--text-dim);line-height:1.5}}
.dd-entry-guide{{display:inline-block;margin-top:6px;padding:3px 10px;font-size:11px;font-weight:600;color:#fff;background:var(--accent);border-radius:6px;text-decoration:none}}
.tier-badge{{display:inline-block;padding:1px 6px;border-radius:4px;font-size:10px;font-weight:700}}
.tS{{background:rgba(251,191,36,.2);color:#fbbf24}}.tA{{background:rgba(167,139,250,.2);color:#a78bfa}}
.tB{{background:rgba(96,165,250,.2);color:#60a5fa}}.tC{{background:rgba(106,106,128,.2);color:#6a6a80}}
.back-link{{display:inline-block;margin-bottom:20px;color:var(--accent);text-decoration:none;font-size:12px;font-weight:600}}
.back-link:hover{{text-decoration:underline}}
.action-sketch{{background:rgba(167,139,250,.08);border:1px solid rgba(167,139,250,.2);border-radius:10px;padding:16px 18px;margin:24px 0}}
.action-sketch h3{{font-size:14px;font-weight:800;color:#fff;margin:0 0 8px}}
.action-sketch p{{font-size:13px;line-height:1.6;color:var(--text-dim);margin:0}}
.prereqs{{font-size:12px;color:var(--text-mute);line-height:1.5;margin:16px 0;padding:12px;background:rgba(255,255,255,.03);border-radius:8px}}
</style>
</head><body>
<main class="deeper-wrap">
<a href="../" class="back-link">← Back to DejaViewed</a>
<div class="deeper-hero">
  <div class="type-label">{_esc(deeper.get("dive_type", "insight"))}</div>
  <h1>{_esc(title)}</h1>
  <div class="thesis">{_esc(thesis)}</div>
  <div class="tools">{tools_html}</div>
</div>

<div class="dd-narrative">{narrative if narrative != thesis else ""}</div>

{sections_html}

{"<div class='action-sketch'><h3>Try It — Action Sketch</h3><p>" + _esc(deeper.get("action_sketch", "")) + "</p></div>" if deeper.get("action_sketch") else ""}

{"<div class='prereqs'><strong>Prerequisites:</strong> " + _esc(deeper.get("prerequisites", "")) + "</div>" if deeper.get("prerequisites") else ""}

<div class="dd-entries">
<h2>Connected Posts ({len(entries)})</h2>
{entries_html}
</div>

<div style="margin-top:40px;padding-top:20px;border-top:1px solid var(--border);font-size:11px;color:var(--text-mute)">
  Deeper Dive generated {deeper.get("generated_at", "")} · Curated by Claude for Gabe (@6ab3) · <a href="https://dejaviewed.com" style="color:var(--accent)">dejaviewed.com</a>
</div>
</main>
</body></html>'''


def _esc(s):
    """HTML-escape a string."""
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def main():
    import argparse
    p = argparse.ArgumentParser(description="Generate Deeper Dive narrative pages")
    p.add_argument("--dry-run", action="store_true", help="Preview without saving")
    p.add_argument("--all-curated", action="store_true", help="Generate pages for all curated dives")
    p.add_argument("--dive-id", action="append", dest="dive_ids", default=[], help="Specific dive ID (repeatable)")
    args = p.parse_args()
    dry_run = args.dry_run
    all_curated = args.all_curated
    target_ids = args.dive_ids

    catalog = load_catalog()
    dd_data = load_deep_dives()
    entry_map = get_entry_map(catalog)
    dives = dd_data.get("deep_dives", [])

    if all_curated:
        targets = [d for d in dives if d.get("suggested_by") == "curated" or d.get("pinned")]
    elif target_ids:
        targets = [d for d in dives if d["id"] in target_ids]
    else:
        print("Usage: deeper_dives.py --all-curated | --dive-id <id>")
        print(f"\nAvailable curated dives ({sum(1 for d in dives if d.get('suggested_by')=='curated')}):")
        for d in dives:
            if d.get("suggested_by") == "curated":
                count = d.get("entry_count", len(d.get("entry_ids", [])))
                print(f"  {d['id']:50s} {count} entries  {d.get('title', '')[:50]}")
        return

    DEEPER_DIR.mkdir(parents=True, exist_ok=True)

    all_deeper = []
    for dive in targets:
        deeper = build_deeper_page(dive, entry_map, catalog)
        out_path = DEEPER_DIR / f"{deeper['slug']}.html"

        if not dry_run:
            html = render_html(deeper)
            out_path.write_text(html, encoding="utf-8")

        all_deeper.append(deeper)
        count = deeper["entry_count"]
        print(f"  {'[DRY] ' if dry_run else ''}Generated {deeper['slug']} ({count} entries)")

    if not dry_run and all_deeper:
        existing = []
        if DEEPER_DATA.exists():
            existing = json.loads(DEEPER_DATA.read_text(encoding="utf-8")).get("deeper_dives", [])
        existing_ids = {d["id"] for d in existing}
        for d in all_deeper:
            if d["id"] in existing_ids:
                existing = [x if x["id"] != d["id"] else d for x in existing]
            else:
                existing.append(d)

        wrapper = {
            "deeper_dives": existing,
            "count": len(existing),
            "generated_at": datetime.now().isoformat(),
            "attribution": "Curated by Claude for Gabe (@6ab3) — dejaviewed.com",
        }
        DEEPER_DATA.write_text(json.dumps(wrapper, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Generated {len(all_deeper)} Deeper Dives")
    if not dry_run:
        print(f"Pages: {DEEPER_DIR}")
        print(f"Data: {DEEPER_DATA}")


if __name__ == "__main__":
    main()
