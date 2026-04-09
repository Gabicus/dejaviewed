#!/usr/bin/env python3
"""Extract Microsoft Edge bookmarks into DejaViewed JSONL format.

Reuses the Chrome adapter since Edge uses the same Chromium bookmark format.

Usage:
    python3 adapters/edge_bookmarks.py [--profile PATH] --out data/edge_bookmarks.jsonl
"""

import argparse
import json
import os
import platform
import sys

# Import shared logic from chrome adapter
sys.path.insert(0, os.path.dirname(__file__))
from chrome_bookmarks import extract_bookmarks, chrome_time_to_date, SKIP_SCHEMES
from urllib.parse import urlparse


def default_edge_profile():
    """Auto-detect Edge bookmarks path based on OS."""
    system = platform.system()
    if system == "Linux":
        return os.path.expanduser("~/.config/microsoft-edge/Default/Bookmarks")
    elif system == "Darwin":
        return os.path.expanduser("~/Library/Application Support/Microsoft Edge/Default/Bookmarks")
    elif system == "Windows":
        local = os.environ.get("LOCALAPPDATA", "")
        return os.path.join(local, "Microsoft", "Edge", "User Data", "Default", "Bookmarks")
    return None


def to_jsonl_record(bm):
    """Convert a raw bookmark dict to DejaViewed JSONL format for Edge."""
    return {
        "source": "edge",
        "post_url": bm["url"],
        "creator": bm["folder"],
        "collection": "edge",
        "date": chrome_time_to_date(bm["date_added"]),
        "media_type": "bookmark",
        "caption_original": bm["name"],
        "summary": "",
        "card_title": bm["name"],
        "type": "resource",
        "tools_mentioned": [],
        "repos_or_projects_mentioned": [],
        "links": [{"label": bm["domain"], "url": bm["url"]}],
    }


def main():
    parser = argparse.ArgumentParser(description="Extract Edge bookmarks to JSONL")
    parser.add_argument("--profile", type=str, default=None, help="Path to Edge Bookmarks JSON file")
    parser.add_argument("--out", type=str, required=True, help="Output JSONL path")
    args = parser.parse_args()

    profile_path = args.profile or default_edge_profile()
    if not profile_path or not os.path.exists(profile_path):
        print(f"[edge] Bookmarks file not found: {profile_path}", file=sys.stderr)
        sys.exit(1)

    with open(profile_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    roots = data.get("roots", {})
    all_bookmarks = []
    for root_name, root_node in roots.items():
        if isinstance(root_node, dict):
            extract_bookmarks(root_node, root_name, all_bookmarks)

    seen_urls = set()
    unique = []
    for bm in all_bookmarks:
        if bm["url"] not in seen_urls:
            seen_urls.add(bm["url"])
            unique.append(bm)

    print(f"[edge] Found {len(all_bookmarks)} bookmarks, {len(unique)} unique", file=sys.stderr)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for bm in unique:
            f.write(json.dumps(to_jsonl_record(bm), ensure_ascii=False) + "\n")

    print(f"[edge] Wrote {len(unique)} to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
