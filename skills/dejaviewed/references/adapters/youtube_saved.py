#!/usr/bin/env python3
"""Extract YouTube saved playlists (Watch Later, Liked Videos) into DejaViewed JSONL format.

Scrapes YouTube playlist pages with session cookies from a copied Chrome profile.
Extracts video metadata from the embedded ytInitialData JSON blob.

Usage:
    python3 adapters/youtube_saved.py --out data/youtube_saved.jsonl
    python3 adapters/youtube_saved.py --playlists WL,LL --out data/youtube_saved.jsonl
    python3 adapters/youtube_saved.py --playlists WL,LL,PLxxxxxxxx --out data/youtube_saved.jsonl

Playlist codes:
    WL  = Watch Later
    LL  = Liked Videos
    PLx = Any custom playlist ID

Security:
    Cookie values are NEVER printed, logged, or written to any output file.
"""

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode

import requests

try:
    import browser_cookie3
except ImportError:
    print("[youtube] ERROR: pip install browser-cookie3", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / ".profile-copy"

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

SKIP_DOMAINS = {
    "youtube.com", "www.youtube.com", "m.youtube.com", "youtu.be",
    "i.ytimg.com", "yt3.ggpht.com", "yt3.googleusercontent.com",
    "accounts.google.com", "play.google.com",
}

PLAYLIST_NAMES = {
    "WL": "Watch Later",
    "LL": "Liked Videos",
}


def load_cookies(profile_path):
    """Load YouTube/Google cookies from copied Chrome profile."""
    cookies_db = profile_path / "Default" / "Cookies"
    if not cookies_db.exists():
        raise SystemExit(f"[youtube] Cookies DB not found: {cookies_db}")
    try:
        cj = browser_cookie3.chromium(cookie_file=str(cookies_db), domain_name=".youtube.com")
    except Exception:
        try:
            cj = browser_cookie3.chrome(cookie_file=str(cookies_db), domain_name=".youtube.com")
        except Exception as e:
            raise SystemExit(f"[youtube] Failed to load cookies: {type(e).__name__}: {e}")
    count = sum(1 for _ in cj)
    has_login = any(c.name in ("LOGIN_INFO", "SID", "SSID") for c in cj)
    print(f"[youtube] cookies loaded: {count} (login present: {has_login})", file=sys.stderr)
    return cj


def extract_sapisidhash(cookie_jar):
    """Generate SAPISIDHASH for YouTube API auth (time-based hash of SAPISID cookie).
    Returns the auth header value or None."""
    import hashlib
    sapisid = None
    for c in cookie_jar:
        if c.name == "SAPISID":
            sapisid = c.value
            break
    if not sapisid:
        # Try __Secure-3PAPISID
        for c in cookie_jar:
            if c.name == "__Secure-3PAPISID":
                sapisid = c.value
                break
    if not sapisid:
        return None
    timestamp = str(int(time.time()))
    hash_input = f"{timestamp} {sapisid} https://www.youtube.com"
    hash_val = hashlib.sha1(hash_input.encode()).hexdigest()
    return f"SAPISIDHASH {timestamp}_{hash_val}"


def parse_video_renderer(renderer, playlist_name):
    """Extract fields from a playlistVideoRenderer or gridVideoRenderer."""
    video_id = renderer.get("videoId", "")
    if not video_id:
        return None

    # Title
    title_runs = renderer.get("title", {}).get("runs", [])
    title = "".join(r.get("text", "") for r in title_runs) if title_runs else renderer.get("title", {}).get("simpleText", "")

    # Channel
    channel_runs = renderer.get("shortBylineText", {}).get("runs", [])
    channel = channel_runs[0].get("text", "") if channel_runs else ""
    channel_id = ""
    if channel_runs:
        nav = channel_runs[0].get("navigationEndpoint", {}).get("browseEndpoint", {})
        channel_id = nav.get("browseId", "")

    # Duration
    duration_text = renderer.get("lengthText", {}).get("simpleText", "")

    # View count
    view_text = renderer.get("videoInfo", {}).get("runs", [{}])
    if isinstance(view_text, list) and view_text:
        view_text = view_text[0].get("text", "")
    else:
        view_text = ""

    # Description snippet
    desc_snippet = renderer.get("descriptionSnippet", {})
    desc_runs = desc_snippet.get("runs", []) if desc_snippet else []
    description = "".join(r.get("text", "") for r in desc_runs)

    # Thumbnail
    thumbs = renderer.get("thumbnail", {}).get("thumbnails", [])
    thumb_url = thumbs[-1].get("url", "") if thumbs else ""

    # Published date (not always available in playlist context)
    date_str = ""

    post_url = f"https://www.youtube.com/watch?v={video_id}"

    return {
        "source": "youtube",
        "post_url": post_url,
        "creator": channel,
        "creator_id": channel_id,
        "collection": playlist_name,
        "date": date_str,
        "media_type": "video",
        "caption_original": description or title,
        "summary": "",
        "card_title": title,
        "type": "resource",
        "tools_mentioned": [],
        "repos_or_projects_mentioned": [],
        "links": [],
        "duration": duration_text,
        "thumbnail_url": thumb_url,
        "video_id": video_id,
    }


def fetch_playlist_page(session, playlist_id):
    """Fetch a YouTube playlist page and extract ytInitialData."""
    url = f"https://www.youtube.com/playlist?list={playlist_id}"
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        r = session.get(url, headers=headers, timeout=30)
    except requests.RequestException as e:
        print(f"[youtube] Request failed: {e}", file=sys.stderr)
        return None

    if r.status_code != 200:
        print(f"[youtube] HTTP {r.status_code} for playlist {playlist_id}", file=sys.stderr)
        return None

    # Extract ytInitialData — split-based approach avoids catastrophic regex backtracking
    marker = "var ytInitialData = "
    idx = r.text.find(marker)
    if idx == -1:
        marker = 'window["ytInitialData"] = '
        idx = r.text.find(marker)
    if idx == -1:
        print(f"[youtube] Could not find ytInitialData for playlist {playlist_id}", file=sys.stderr)
        return None

    json_start = idx + len(marker)
    # Find the end: ytInitialData is terminated by ";\n" or ";</script>"
    # Use a simple brace-counting approach for robustness
    depth = 0
    json_end = json_start
    for i, ch in enumerate(r.text[json_start:], json_start):
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                json_end = i + 1
                break
    else:
        print(f"[youtube] Could not find end of ytInitialData JSON", file=sys.stderr)
        return None

    try:
        return json.loads(r.text[json_start:json_end])
    except json.JSONDecodeError as e:
        print(f"[youtube] JSON parse error: {e}", file=sys.stderr)
        return None


def fetch_continuation(session, continuation_token, api_key="AIzaSyAO_FJ2SlqU8Q4STEHLGCilw_Y9_11qcW8"):
    """Fetch next page of playlist results using YouTube's browse API."""
    url = "https://www.youtube.com/youtubei/v1/browse"
    params = {"key": api_key, "prettyPrint": "false"}

    sapisidhash = extract_sapisidhash(session.cookies)

    headers = {
        "User-Agent": UA,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Youtube-Client-Name": "1",
        "X-Youtube-Client-Version": "2.20240101.00.00",
        "Origin": "https://www.youtube.com",
        "Referer": "https://www.youtube.com/",
    }
    if sapisidhash:
        headers["Authorization"] = sapisidhash

    body = {
        "context": {
            "client": {
                "clientName": "WEB",
                "clientVersion": "2.20240101.00.00",
                "hl": "en",
                "gl": "US",
            }
        },
        "continuation": continuation_token,
    }

    try:
        r = session.post(url, params=params, headers=headers, json=body, timeout=30)
    except requests.RequestException as e:
        print(f"[youtube] Continuation request failed: {e}", file=sys.stderr)
        return [], None

    if r.status_code != 200:
        print(f"[youtube] Continuation HTTP {r.status_code}", file=sys.stderr)
        return [], None

    data = r.json()
    return extract_items_from_response(data)


def extract_items_from_response(data):
    """Extract video renderers and continuation token from API response."""
    items = []
    next_continuation = None

    # Walk the response tree looking for playlistVideoRenderer
    # Only capture continuation tokens from "continuationItemRenderer" (top-level paginators),
    # not from per-video continuation commands
    def walk(obj, inside_video=False):
        nonlocal next_continuation
        if isinstance(obj, dict):
            if "playlistVideoRenderer" in obj:
                items.append(obj["playlistVideoRenderer"])
                return  # don't descend into video renderers for continuation tokens
            if "continuationItemRenderer" in obj:
                token = (obj["continuationItemRenderer"]
                         .get("continuationEndpoint", {})
                         .get("continuationCommand", {})
                         .get("token"))
                if token:
                    next_continuation = token
            for v in obj.values():
                walk(v, inside_video)
        elif isinstance(obj, list):
            for v in obj:
                walk(v, inside_video)

    walk(data)
    return items, next_continuation


def extract_playlist_items(session, playlist_id, playlist_name, done_urls, limit=0):
    """Extract all videos from a playlist, handling pagination."""
    print(f"[youtube] Fetching playlist: {playlist_name} ({playlist_id})", file=sys.stderr)

    initial_data = fetch_playlist_page(session, playlist_id)
    if not initial_data:
        return []

    # Extract from initial page
    renderers, continuation = extract_items_from_response(initial_data)
    all_parsed = []

    for r in renderers:
        parsed = parse_video_renderer(r, playlist_name)
        if parsed and parsed["post_url"] not in done_urls:
            all_parsed.append(parsed)

    print(f"[youtube]   Initial page: {len(renderers)} videos, {len(all_parsed)} new", file=sys.stderr)

    # Pagination
    page = 1
    while continuation:
        if limit and len(all_parsed) >= limit:
            break

        page += 1
        time.sleep(1.5)
        print(f"[youtube]   Continuation page {page}...", file=sys.stderr)

        renderers, continuation = fetch_continuation(session, continuation)
        for r in renderers:
            parsed = parse_video_renderer(r, playlist_name)
            if parsed and parsed["post_url"] not in done_urls:
                all_parsed.append(parsed)

        print(f"[youtube]   Got {len(renderers)} more videos", file=sys.stderr)

        if not renderers:
            break

    return all_parsed


def main():
    parser = argparse.ArgumentParser(description="Extract YouTube saved playlists to JSONL")
    parser.add_argument("--profile", type=str, default=None, help="Path to .profile-copy directory")
    parser.add_argument("--out", type=str, required=True, help="Output JSONL path")
    parser.add_argument("--playlists", type=str, default="WL,LL",
                        help="Comma-separated playlist IDs (default: WL,LL)")
    parser.add_argument("--limit", type=int, default=0, help="Max items per playlist (0 = all)")
    args = parser.parse_args()

    profile_path = Path(args.profile) if args.profile else PROFILE
    cj = load_cookies(profile_path)

    session = requests.Session()
    session.cookies = cj

    # Resume: load already-scraped URLs
    out_path = Path(args.out)
    done = set()
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            if line.strip():
                try:
                    done.add(json.loads(line)["post_url"])
                except (json.JSONDecodeError, KeyError):
                    pass

    playlist_ids = [p.strip() for p in args.playlists.split(",") if p.strip()]
    all_items = []

    for pl_id in playlist_ids:
        pl_name = PLAYLIST_NAMES.get(pl_id, f"playlist:{pl_id}")
        items = extract_playlist_items(session, pl_id, pl_name, done, args.limit)
        all_items.extend(items)
        if len(playlist_ids) > 1:
            time.sleep(2)

    # Write output
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "a" if done else "w", encoding="utf-8") as f:
        for item in all_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    total = len(done) + len(all_items)
    print(f"[youtube] Done: {len(all_items)} new videos written, {total} total in {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
