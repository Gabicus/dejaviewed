#!/usr/bin/env python3
"""Convert Playwright-scraped raw JSON → catalog entries, dedupe, merge.

Usage:
  python scripts/process_raw.py --raw data/ai5_raw.json --collection ai5
  python scripts/process_raw.py --raw data/art-i-like_raw.json --collection art-i-like --art
"""
import argparse
import json
import hashlib
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "site" / "catalog.json"
CATALOG_JS = ROOT / "site" / "catalog.js"


def stable_id(url: str) -> str:
    return "D" + hashlib.sha256(url.encode()).hexdigest()[:10]


def load_catalog() -> list[dict]:
    if not CATALOG.exists():
        return []
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else data.get("entries", [])


def build_stats(entries: list[dict]) -> dict:
    from collections import Counter
    colls = Counter()
    tools_idx: dict[str, list[str]] = {}
    tech_idx: dict[str, list[str]] = {}
    for e in entries:
        c = e.get("collection") or e.get("source_collection") or ""
        if c:
            colls[c] += 1
        eid = e.get("id", "")
        for t in (e.get("tools") or []):
            tools_idx.setdefault(t, []).append(eid)
        for t in (e.get("techniques") or []):
            tech_idx.setdefault(t, []).append(eid)
    return {
        "stats": {"collections": dict(colls)},
        "indices": {"by_tool": tools_idx, "by_technique": tech_idx},
    }


def save_catalog(entries: list[dict]):
    extra = build_stats(entries)
    wrapper = {
        "entries": entries,
        "stats": extra["stats"],
        "indices": extra["indices"],
        "generated_at": datetime.now().isoformat(),
    }
    CATALOG.write_text(json.dumps(wrapper, indent=2, ensure_ascii=False), encoding="utf-8")
    js = "window.__CATALOG = " + json.dumps(wrapper, ensure_ascii=False) + ";\n"
    CATALOG_JS.write_text(js, encoding="utf-8")
    print(f"Wrote {len(entries)} entries to catalog.json + catalog.js")


def raw_to_entry(raw: dict, collection: str, is_art: bool) -> dict:
    shortcode = raw.get("shortcode", "")
    url = raw.get("url", f"https://www.instagram.com/p/{shortcode}/")
    entry_id = stable_id(url)
    creator = (raw.get("creator") or "").lstrip("@")
    caption = raw.get("caption") or ""
    title_from_caption = caption.split("\n")[0][:80] if caption else f"Post by {creator}"
    if len(title_from_caption) > 75:
        title_from_caption = title_from_caption[:72] + "..."

    entry = {
        "id": entry_id,
        "post_id": shortcode,
        "url": url,
        "source_collection": collection,
        "collections": [collection],
        "creator": creator,
        "date": raw.get("date") or "",
        "title": title_from_caption,
        "summary": "",
        "caption": caption,
        "media_type": raw.get("media_type") or "image",
        "type": "art" if is_art else "resource",
        "tier": "C",
        "audience": "",
        "tags": [],
        "domains": [],
        "tools": [],
        "techniques": [],
        "models": [],
        "repos": [],
        "takeaways": [],
        "has_guide": False,
        "deep_dive_slug": "",
        "favorited": False,
        "user_notes": "",
        "transcript": "",
        "transcript_source": "",
        "transcript_at": "",
        "media_url": raw.get("thumbnail") or "",
        "collection": collection,
        "deep_dive": "",
        "is_new": True,
    }
    return entry


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--raw", required=True, help="Path to raw JSON from Playwright scrape")
    p.add_argument("--collection", required=True, help="Collection name (ai5, art-i-like, etc)")
    p.add_argument("--art", action="store_true", help="Use art type instead of resource")
    args = p.parse_args()

    raw_data = json.loads(Path(args.raw).read_text(encoding="utf-8"))
    print(f"Raw entries: {len(raw_data)}")

    existing = load_catalog()
    existing_urls = {e.get("url", "") for e in existing}
    existing_posts = {e.get("post_id", "") for e in existing if e.get("post_id")}

    new_count = 0
    dup_count = 0
    merged_count = 0

    for raw in raw_data:
        url = raw.get("url", "")
        shortcode = raw.get("shortcode", "")

        if url in existing_urls or shortcode in existing_posts:
            found = next((e for e in existing if e.get("url") == url or e.get("post_id") == shortcode), None)
            if found:
                cols = set(found.get("collections") or [])
                if args.collection not in cols:
                    cols.add(args.collection)
                    found["collections"] = sorted(cols)
                    merged_count += 1
                else:
                    dup_count += 1
            continue

        entry = raw_to_entry(raw, args.collection, args.art)
        existing.append(entry)
        existing_urls.add(url)
        existing_posts.add(shortcode)
        new_count += 1

    # Clear is_new from entries NOT in this batch
    for e in existing:
        if e.get("source_collection") != args.collection:
            pass  # don't touch other collections' is_new flags

    save_catalog(existing)
    print(f"\nResults: {new_count} new, {dup_count} duplicates, {merged_count} added to collection")

    # Sync to parquet + rebuild crosslinks + API exports
    import subprocess
    print("\n[process_raw] Syncing to CMS parquet...")
    r1 = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "cms.py"), "migrate"],
        capture_output=True, text=True
    )
    if r1.returncode != 0:
        print(f"[process_raw] ERROR: cms.py migrate failed:\n{r1.stderr}", file=sys.stderr)
    else:
        print("[process_raw] Parquet sync complete")

    api_script = ROOT / "scripts" / "build_api.py"
    if api_script.exists():
        r2 = subprocess.run(
            [sys.executable, str(api_script)],
            capture_output=True, text=True
        )
        if r2.returncode != 0:
            print(f"[process_raw] ERROR: build_api.py failed:\n{r2.stderr}", file=sys.stderr)
        else:
            print("[process_raw] API export complete")


if __name__ == "__main__":
    sys.exit(main() or 0)
