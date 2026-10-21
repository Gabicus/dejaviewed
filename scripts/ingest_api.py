#!/usr/bin/env python3
"""Ingest entries from Instagram collection-feed API dumps (ig_collection_api.py).

Unlike ingest.py placeholders, these rows arrive with caption, creator, date,
media_type and media_url already populated, so no caption-scrape pass is needed.

Usage:
    python3 scripts/ingest_api.py data/new_items_2026-10-21.json
    python3 scripts/ingest_api.py data/ai8_api.json --collection ai8
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cms import (entry_from_catalog, upsert, write_entries, write_crosslinks,  # noqa: E402
                 compute_crosslinks, load_entries, _write_catalog_exports)

MEDIA_TYPE = {"1": "image", "2": "video", "8": "carousel"}


def to_row(it: dict, collection: str) -> dict:
    code = it["code"]
    ts = it.get("taken_at")
    date = ""
    if ts:
        date = datetime.fromtimestamp(int(ts), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
    mt = MEDIA_TYPE.get(str(it.get("media_type")), "image")
    caption = it.get("caption") or ""
    return {
        "url": f"https://www.instagram.com/p/{code}/",
        "post_id": code,
        "collection": collection,
        "title": f"[NEEDS ENRICHMENT] {code}",
        "caption": caption,
        "summary": "",
        "creator": f"@{it['creator']}" if it.get("creator") else "",
        "date": date,
        "tier": "C",
        "type": "resource",
        "media_type": mt,
        "media_url": it.get("video_url") or "",
        "user_notes": "",
        "domains": [], "tools": [], "techniques": [],
        "models": [], "repos": [], "takeaways": [],
        "has_guide": False, "deep_dive": "",
        "is_new": True,
    }


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("path")
    p.add_argument("--collection", help="override collection for every item")
    a = p.parse_args(argv)
    data = json.load(open(a.path))
    items = data["items"] if isinstance(data, dict) else data
    rows = load_entries()
    counts = {}
    for it in items:
        coll = a.collection or it.get("collection") or (data.get("collection") if isinstance(data, dict) else "")
        if not coll:
            print(f"[ingest_api] {it.get('code')}: no collection, skipping")
            continue
        rows, action = upsert(rows, entry_from_catalog(to_row(it, coll)))
        counts[action] = counts.get(action, 0) + 1
    write_entries(rows)
    write_crosslinks(compute_crosslinks(rows))
    _write_catalog_exports(rows)
    print(f"[ingest_api] {counts} -> {len(rows)} total entries")


if __name__ == "__main__":
    main()
