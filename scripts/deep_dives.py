#!/usr/bin/env python3
"""Detect natural deep dive groupings across the catalog.

Scans crosslinks and entry metadata to find clusters of related posts
that could form deep dives. Posts can belong to multiple deep dives.

Usage:
  python scripts/deep_dives.py [--min-entries 3] [--dry-run]
"""
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "site" / "catalog.json"
DEEP_DIVES_JSON = ROOT / "data" / "deep_dives.json"
DEEP_DIVES_JS = ROOT / "site" / "deep_dives.js"


def detect_tool_dives(entries: list[dict], min_entries: int = 3) -> list[dict]:
    """Group posts by shared tools — each tool used by 3+ posts = a dive."""
    tool_posts = defaultdict(list)
    for e in entries:
        for t in (e.get("tools") or []):
            tool_posts[t].append(e)

    dives = []
    for tool, posts in sorted(tool_posts.items(), key=lambda x: -len(x[1])):
        if len(posts) < min_entries:
            continue
        ids = [p["id"] for p in posts]
        tiers = Counter(p.get("tier", "C") for p in posts)
        best_tier = "S" if tiers.get("S") else "A" if tiers.get("A") else "B"
        creators = sorted(set(p.get("creator", "") for p in posts if p.get("creator")))
        dives.append({
            "id": f"dd-tool-{tool.lower().replace(' ', '-').replace('/', '-')}",
            "title": f"{tool} — {len(posts)} posts",
            "type": "tool",
            "anchor_tag": tool,
            "entry_ids": ids,
            "entry_count": len(ids),
            "tier": best_tier,
            "creators": creators[:5],
            "summary": f"{len(posts)} posts covering {tool}. Creators: {', '.join(f'@{c}' for c in creators[:3])}.",
            "suggested_by": "auto",
        })
    return dives


def detect_technique_dives(entries: list[dict], min_entries: int = 3) -> list[dict]:
    """Group by shared techniques."""
    tech_posts = defaultdict(list)
    for e in entries:
        for t in (e.get("techniques") or []):
            tech_posts[t].append(e)

    dives = []
    for tech, posts in sorted(tech_posts.items(), key=lambda x: -len(x[1])):
        if len(posts) < min_entries:
            continue
        ids = [p["id"] for p in posts]
        creators = sorted(set(p.get("creator", "") for p in posts if p.get("creator")))
        dives.append({
            "id": f"dd-tech-{tech.lower().replace(' ', '-').replace('/', '-')}",
            "title": f"{tech} — {len(posts)} posts",
            "type": "technique",
            "anchor_tag": tech,
            "entry_ids": ids,
            "entry_count": len(ids),
            "tier": "A",
            "creators": creators[:5],
            "summary": f"{len(posts)} posts demonstrating {tech}.",
            "suggested_by": "auto",
        })
    return dives


def detect_creator_dives(entries: list[dict], min_entries: int = 3) -> list[dict]:
    """Creators with 3+ posts get a creator deep dive."""
    creator_posts = defaultdict(list)
    for e in entries:
        c = e.get("creator", "")
        if c:
            creator_posts[c].append(e)

    dives = []
    for creator, posts in sorted(creator_posts.items(), key=lambda x: -len(x[1])):
        if len(posts) < min_entries:
            continue
        ids = [p["id"] for p in posts]
        tiers = Counter(p.get("tier", "C") for p in posts)
        tools = sorted(set(t for p in posts for t in (p.get("tools") or [])))
        types = Counter(p.get("type", "") for p in posts)
        top_type = types.most_common(1)[0][0] if types else "resource"
        dives.append({
            "id": f"dd-creator-{creator.lower().replace(' ', '-')}",
            "title": f"@{creator} — {len(posts)} posts",
            "type": "creator",
            "anchor_tag": creator,
            "entry_ids": ids,
            "entry_count": len(ids),
            "tier": "S" if tiers.get("S") else "A" if tiers.get("A") else "B",
            "creators": [creator],
            "tools": tools[:5],
            "primary_type": top_type,
            "summary": f"@{creator} has {len(posts)} curated posts" + (f" using {', '.join(tools[:3])}" if tools else "") + ".",
            "suggested_by": "auto",
        })
    return dives


def detect_domain_dives(entries: list[dict], min_entries: int = 4) -> list[dict]:
    """Group by domain — higher threshold since domains are broad."""
    domain_posts = defaultdict(list)
    for e in entries:
        for d in (e.get("domains") or []):
            domain_posts[d].append(e)

    dives = []
    for domain, posts in sorted(domain_posts.items(), key=lambda x: -len(x[1])):
        if len(posts) < min_entries:
            continue
        ids = [p["id"] for p in posts]
        creators = sorted(set(p.get("creator", "") for p in posts if p.get("creator")))
        dives.append({
            "id": f"dd-domain-{domain.lower().replace(' ', '-').replace('/', '-')}",
            "title": f"{domain} — {len(posts)} posts",
            "type": "domain",
            "anchor_tag": domain,
            "entry_ids": ids,
            "entry_count": len(ids),
            "tier": "A",
            "creators": creators[:5],
            "summary": f"{len(posts)} posts in the {domain} domain.",
            "suggested_by": "auto",
        })
    return dives


def detect_manual_dives(entries: list[dict]) -> list[dict]:
    """Entries with has_guide=true get grouped with related entries sharing tools/domains."""
    entry_map = {e["id"]: e for e in entries}
    dives = []
    for e in entries:
        if not (e.get("has_guide") and e.get("deep_dive_slug")):
            continue
        related = [e["id"]]
        e_tools = set(e.get("tools") or [])
        e_domains = set(e.get("domains") or [])
        for other in entries:
            if other["id"] == e["id"]:
                continue
            o_tools = set(other.get("tools") or [])
            o_domains = set(other.get("domains") or [])
            overlap = len(e_tools & o_tools) + len(e_domains & o_domains)
            if overlap >= 2 and other["id"] not in related:
                related.append(other["id"])
            if len(related) >= 6:
                break
        if len(related) < 2:
            continue
        creators = sorted(set(entry_map[r].get("creator", "") for r in related if entry_map[r].get("creator")))
        dives.append({
            "id": f"dd-guide-{e['deep_dive_slug']}",
            "title": e.get("title", "Deep Dive"),
            "type": "guide",
            "anchor_tag": e.get("deep_dive_slug", ""),
            "entry_ids": related,
            "entry_count": len(related),
            "tier": e.get("tier", "A"),
            "creators": creators[:5],
            "summary": e.get("summary", ""),
            "suggested_by": "manual",
        })
    return dives


MANUAL_DIVES_JSON = ROOT / "data" / "manual_dives.json"


def load_curated_dives() -> list[dict]:
    """Load hand-curated insight dives that survive regeneration."""
    if not MANUAL_DIVES_JSON.exists():
        return []
    data = json.loads(MANUAL_DIVES_JSON.read_text(encoding="utf-8"))
    return data.get("manual_dives", [])


def load_curated_classes() -> dict:
    """Load deep dive class definitions."""
    if not MANUAL_DIVES_JSON.exists():
        return {}
    data = json.loads(MANUAL_DIVES_JSON.read_text(encoding="utf-8"))
    return data.get("classes", {})


def main():
    import argparse
    p = argparse.ArgumentParser(description="Detect deep dive groupings across the catalog")
    p.add_argument("--dry-run", action="store_true", help="Preview without saving")
    p.add_argument("--min-entries", type=int, default=3, help="Minimum entries per dive cluster")
    args = p.parse_args()
    dry_run = args.dry_run
    min_entries = args.min_entries

    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    entries = data["entries"]

    # Curated dives first — these are pinned and never overwritten
    curated = load_curated_dives()
    curated_ids = {d["id"] for d in curated}

    all_dives = list(curated)
    # Auto-detected dives (skip any that collide with curated IDs)
    for dive in detect_creator_dives(entries, min_entries):
        if dive["id"] not in curated_ids:
            all_dives.append(dive)
    for dive in detect_tool_dives(entries, min_entries):
        if dive["id"] not in curated_ids:
            all_dives.append(dive)
    for dive in detect_technique_dives(entries, min_entries):
        if dive["id"] not in curated_ids:
            all_dives.append(dive)
    for dive in detect_domain_dives(entries, max(min_entries, 4)):
        if dive["id"] not in curated_ids:
            all_dives.append(dive)
    for dive in detect_manual_dives(entries):
        if dive["id"] not in curated_ids:
            all_dives.append(dive)

    # Sort: curated first, then manual, then by entry count desc
    def sort_key(d):
        if d.get("pinned") or d.get("suggested_by") == "curated":
            return (0, -d.get("quality_rating", 0))
        if d.get("suggested_by") == "manual":
            return (1, -d.get("entry_count", 0))
        return (2, -d["entry_count"])
    all_dives.sort(key=sort_key)

    # Stats
    by_type = Counter(d.get("type") or d.get("class", "insight") for d in all_dives)
    total_links = sum(d.get("entry_count", len(d.get("entry_ids", []))) for d in all_dives)
    unique_entries = len(set(eid for d in all_dives for eid in d.get("entry_ids", [])))

    print(f"Deep dives: {len(all_dives)} total")
    print(f"  By type: {dict(by_type)}")
    print(f"  Total entry links: {total_links} ({unique_entries} unique entries)")
    print(f"  Top 5:")
    for d in all_dives[:5]:
        dtype = d.get('type') or d.get('class', 'insight')
        count = d.get('entry_count', len(d.get('entry_ids', [])))
        print(f"    {d['title']} ({dtype}, {count} entries)")

    if dry_run:
        print("\nDry run — not saving")
        return

    classes = load_curated_classes()
    wrapper = {
        "deep_dives": all_dives,
        "classes": classes,
        "stats": {
            "total": len(all_dives),
            "curated": len(curated),
            "auto": len(all_dives) - len(curated),
            "by_type": dict(by_type),
            "total_links": total_links,
            "unique_entries": unique_entries,
        },
        "generated_at": datetime.now().isoformat(),
        "attribution": "Curated by Claude for Gabe (@6ab3) — dejaviewed.com",
    }
    DEEP_DIVES_JSON.write_text(json.dumps(wrapper, indent=2, ensure_ascii=False), encoding="utf-8")
    js = "window.__DEEP_DIVES = " + json.dumps(wrapper, ensure_ascii=False) + ";\n"
    DEEP_DIVES_JS.write_text(js, encoding="utf-8")

    # Normalize fields for parquet storage
    for d in all_dives:
        if not d.get("dive_type"):
            d["dive_type"] = d.get("type", d.get("class", d.get("value_type", "")))
        if not d.get("dive_class"):
            d["dive_class"] = d.get("class", d.get("value_type", ""))
        if not d.get("entry_count"):
            d["entry_count"] = len(d.get("entry_ids", []))
        # Ensure 'type' exists for frontend compatibility
        if not d.get("type"):
            d["type"] = d.get("dive_type") or d.get("dive_class") or d.get("value_type", "insight")

    # Persist to CMS parquet
    try:
        from cms import write_deep_dives
        write_deep_dives(all_dives)
    except Exception as e:
        print(f"  (parquet write skipped: {e})")

    print(f"\nSaved to {DEEP_DIVES_JSON} + {DEEP_DIVES_JS}")


if __name__ == "__main__":
    main()
