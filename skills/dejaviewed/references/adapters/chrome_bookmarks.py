#!/usr/bin/env python3
"""Extract Chrome bookmarks into DejaViewed JSONL format.

Usage:
    python3 adapters/chrome_bookmarks.py [--profile PATH] --out data/chrome_bookmarks.jsonl
"""

import argparse
import json
import os
import platform
import sys
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

# Chrome epoch: microseconds since Jan 1, 1601
CHROME_EPOCH = datetime(1601, 1, 1, tzinfo=timezone.utc)
SKIP_SCHEMES = {"chrome", "chrome-extension", "about", "edge", "brave", "vivaldi", "opera", "data", "javascript", "file"}


def default_chrome_profile():
    """Auto-detect Chrome bookmarks path based on OS."""
    system = platform.system()
    if system == "Linux":
        return os.path.expanduser("~/.config/google-chrome/Default/Bookmarks")
    elif system == "Darwin":
        return os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Bookmarks")
    elif system == "Windows":
        local = os.environ.get("LOCALAPPDATA", "")
        return os.path.join(local, "Google", "Chrome", "User Data", "Default", "Bookmarks")
    return None


def chrome_time_to_date(chrome_us):
    """Convert Chrome epoch (microseconds since 1601-01-01) to human-readable date."""
    try:
        ts = int(chrome_us)
        dt = CHROME_EPOCH + timedelta(microseconds=ts)
        return dt.strftime("%B %d, %Y")
    except (ValueError, OverflowError):
        return ""


def extract_bookmarks(node, folder_name="", results=None):
    """Recursively extract bookmarks from Chrome JSON tree."""
    if results is None:
        results = []

    if node.get("type") == "url":
        url = node.get("url", "")
        parsed = urlparse(url)
        if parsed.scheme not in SKIP_SCHEMES and url:
            results.append({
                "url": url,
                "name": node.get("name", ""),
                "date_added": node.get("date_added", "0"),
                "folder": folder_name,
                "domain": parsed.netloc,
            })
    elif node.get("type") == "folder":
        current_folder = node.get("name", folder_name)
        for child in node.get("children", []):
            extract_bookmarks(child, current_folder, results)

    return results


def to_jsonl_record(bm):
    """Convert a raw bookmark dict to DejaViewed JSONL format."""
    return {
        "source": "chrome",
        "post_url": bm["url"],
        "creator": bm["folder"],
        "collection": "chrome",
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
    parser = argparse.ArgumentParser(description="Extract Chrome bookmarks to JSONL")
    parser.add_argument("--profile", type=str, default=None, help="Path to Chrome Bookmarks JSON file")
    parser.add_argument("--out", type=str, required=True, help="Output JSONL path")
    args = parser.parse_args()

    profile_path = args.profile or default_chrome_profile()
    if not profile_path or not os.path.exists(profile_path):
        print(f"[chrome] Bookmarks file not found: {profile_path}", file=sys.stderr)
        sys.exit(1)

    with open(profile_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    roots = data.get("roots", {})
    all_bookmarks = []
    for root_name, root_node in roots.items():
        if isinstance(root_node, dict):
            extract_bookmarks(root_node, root_name, all_bookmarks)

    # Dedup by URL
    seen_urls = set()
    unique = []
    for bm in all_bookmarks:
        if bm["url"] not in seen_urls:
            seen_urls.add(bm["url"])
            unique.append(bm)

    print(f"[chrome] Found {len(all_bookmarks)} bookmarks, {len(unique)} unique", file=sys.stderr)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for bm in unique:
            f.write(json.dumps(to_jsonl_record(bm), ensure_ascii=False) + "\n")

    print(f"[chrome] Wrote {len(unique)} to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
