#!/usr/bin/env python3
"""Extract Firefox bookmarks into DejaViewed JSONL format.

Usage:
    python3 adapters/firefox_bookmarks.py [--profile PATH] --out data/firefox_bookmarks.jsonl
"""

import argparse
import glob
import json
import os
import platform
import shutil
import sqlite3
import sys
import tempfile
from datetime import datetime, timezone
from urllib.parse import urlparse

SKIP_SCHEMES = {"chrome", "about", "place", "javascript", "data", "file", "moz-extension"}


def default_firefox_profile():
    """Auto-detect Firefox places.sqlite path."""
    system = platform.system()
    if system == "Linux":
        base = os.path.expanduser("~/.mozilla/firefox/")
    elif system == "Darwin":
        base = os.path.expanduser("~/Library/Application Support/Firefox/Profiles/")
    elif system == "Windows":
        appdata = os.environ.get("APPDATA", "")
        base = os.path.join(appdata, "Mozilla", "Firefox", "Profiles")
    else:
        return None

    # Find *.default-release profile
    matches = glob.glob(os.path.join(base, "*.default-release"))
    if matches:
        return os.path.join(matches[0], "places.sqlite")
    # Fallback: any profile with places.sqlite
    matches = glob.glob(os.path.join(base, "*/places.sqlite"))
    if matches:
        return matches[0]
    return None


def firefox_time_to_date(us):
    """Convert Firefox epoch (microseconds since 1970-01-01) to human-readable date."""
    try:
        ts = int(us) / 1_000_000
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
        return dt.strftime("%B %d, %Y")
    except (ValueError, OverflowError, OSError):
        return ""


def get_folder_names(cursor):
    """Build a dict of folder id -> folder name."""
    cursor.execute("SELECT id, title FROM moz_bookmarks WHERE type = 2")
    folders = {}
    for row in cursor.fetchall():
        folders[row[0]] = row[1] or ""
    return folders


def to_jsonl_record(title, url, date_added, folder_name, domain):
    """Convert to DejaViewed JSONL format."""
    return {
        "source": "firefox",
        "post_url": url,
        "creator": folder_name,
        "collection": "firefox",
        "date": firefox_time_to_date(date_added),
        "media_type": "bookmark",
        "caption_original": title or "",
        "summary": "",
        "card_title": title or "",
        "type": "resource",
        "tools_mentioned": [],
        "repos_or_projects_mentioned": [],
        "links": [{"label": domain, "url": url}],
    }


def main():
    parser = argparse.ArgumentParser(description="Extract Firefox bookmarks to JSONL")
    parser.add_argument("--profile", type=str, default=None, help="Path to Firefox places.sqlite")
    parser.add_argument("--out", type=str, required=True, help="Output JSONL path")
    args = parser.parse_args()

    profile_path = args.profile or default_firefox_profile()
    if not profile_path or not os.path.exists(profile_path):
        print(f"[firefox] places.sqlite not found: {profile_path}", file=sys.stderr)
        sys.exit(1)

    # Firefox locks places.sqlite, so copy to a temp file
    tmp = tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False)
    tmp.close()
    try:
        shutil.copy2(profile_path, tmp.name)
        conn = sqlite3.connect(tmp.name)
        cursor = conn.cursor()

        folders = get_folder_names(cursor)

        cursor.execute("""
            SELECT b.title, p.url, b.dateAdded, b.parent
            FROM moz_bookmarks b
            JOIN moz_places p ON b.fk = p.id
            WHERE b.type = 1
        """)

        seen_urls = set()
        records = []
        total = 0

        for title, url, date_added, parent in cursor.fetchall():
            total += 1
            if not url:
                continue
            parsed = urlparse(url)
            if parsed.scheme in SKIP_SCHEMES:
                continue
            if url in seen_urls:
                continue
            seen_urls.add(url)

            folder_name = folders.get(parent, "")
            records.append(to_jsonl_record(title, url, date_added, folder_name, parsed.netloc))

        conn.close()
    finally:
        os.unlink(tmp.name)

    print(f"[firefox] Found {total} bookmarks, {len(records)} unique", file=sys.stderr)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        for rec in records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"[firefox] Wrote {len(records)} to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
