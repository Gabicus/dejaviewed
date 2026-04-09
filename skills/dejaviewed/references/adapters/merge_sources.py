#!/usr/bin/env python3
"""Merge multiple JSONL source files with cross-source deduplication.

Usage:
    python3 adapters/merge_sources.py \\
        --sources data/chrome_bookmarks.jsonl data/firefox_bookmarks.jsonl data/catalog.jsonl \\
        --out data/catalog_merged.jsonl \\
        --dedup-by url
"""

import argparse
import json
import os
import sys


def get_dedup_key(record, dedup_field):
    """Extract the dedup key from a record."""
    if dedup_field == "url":
        return record.get("post_url", "")
    return record.get(dedup_field, "")


def richness_score(record):
    """Score a record by metadata richness. Higher = richer."""
    score = 0
    if record.get("caption_original"):
        score += len(record["caption_original"])
    if record.get("summary"):
        score += len(record["summary"]) * 2  # summaries are more valuable
    if record.get("tools_mentioned"):
        score += len(record["tools_mentioned"]) * 10
    if record.get("repos_or_projects_mentioned"):
        score += len(record["repos_or_projects_mentioned"]) * 10
    if record.get("key_takeaways"):
        score += len(record["key_takeaways"]) * 15
    if record.get("links"):
        score += len(record["links"]) * 3
    # Instagram records are generally richer than bookmarks
    if record.get("source") not in ("chrome", "firefox", "edge"):
        score += 50
    if record.get("media_type") != "bookmark":
        score += 20
    return score


def merge_records(existing, new_record):
    """Merge two records for the same URL, keeping the richer metadata."""
    # Determine which is richer
    if richness_score(new_record) > richness_score(existing):
        base, extra = new_record, existing
    else:
        base, extra = existing, new_record

    merged = dict(base)

    # Build sources list
    sources = set()
    for rec in (existing, new_record):
        if "sources" in rec:
            sources.update(rec["sources"])
        elif "source" in rec:
            sources.add(rec["source"])
        # Also detect Instagram records (no explicit source field in old catalog)
        if "instagram.com" in rec.get("post_url", ""):
            sources.add("instagram")
    if sources:
        merged["sources"] = sorted(sources)

    # Merge links (dedup by url)
    all_links = {link["url"]: link for link in base.get("links", [])}
    for link in extra.get("links", []):
        if link["url"] not in all_links:
            all_links[link["url"]] = link
    merged["links"] = list(all_links.values())

    # Merge list fields
    for field in ("tools_mentioned", "repos_or_projects_mentioned"):
        vals = set(base.get(field, []) or [])
        vals.update(extra.get(field, []) or [])
        if vals:
            merged[field] = sorted(vals)

    return merged


def main():
    parser = argparse.ArgumentParser(description="Merge multiple JSONL sources with dedup")
    parser.add_argument("--sources", nargs="+", required=True, help="Input JSONL files")
    parser.add_argument("--out", type=str, required=True, help="Output JSONL path")
    parser.add_argument("--dedup-by", type=str, default="url", help="Dedup field (default: url)")
    args = parser.parse_args()

    records_by_key = {}  # dedup_key -> merged record
    insertion_order = []  # preserve order
    total_input = 0
    dupes_merged = 0

    for source_file in args.sources:
        if not os.path.exists(source_file):
            print(f"[merge] Skipping missing file: {source_file}", file=sys.stderr)
            continue

        file_count = 0
        with open(source_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue

                total_input += 1
                file_count += 1
                key = get_dedup_key(record, args.dedup_by)

                if not key:
                    # No dedup key, just append
                    insertion_order.append(id(record))
                    records_by_key[id(record)] = record
                    continue

                if key in records_by_key:
                    records_by_key[key] = merge_records(records_by_key[key], record)
                    dupes_merged += 1
                else:
                    records_by_key[key] = record
                    insertion_order.append(key)

        print(f"[merge] Loaded {file_count} records from {source_file}", file=sys.stderr)

    # Write output in insertion order
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    written = 0
    with open(args.out, "w", encoding="utf-8") as f:
        for key in insertion_order:
            if key in records_by_key:
                f.write(json.dumps(records_by_key[key], ensure_ascii=False) + "\n")
                written += 1

    print(f"[merge] {total_input} input records, {dupes_merged} dupes merged, {written} written to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
