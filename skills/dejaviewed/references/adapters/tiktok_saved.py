#!/usr/bin/env python3
"""Extract TikTok favorites (saved videos) into DejaViewed JSONL format.

Uses TikTok's internal API with session cookies from a copied Chrome profile.
TikTok favorites are at tiktok.com → Profile → Favorites.

Usage:
    python3 adapters/tiktok_saved.py --out data/tiktok_saved.jsonl
    python3 adapters/tiktok_saved.py --profile /path/to/.profile-copy --out data/tiktok_saved.jsonl
    python3 adapters/tiktok_saved.py --limit 100 --out data/tiktok_saved.jsonl

Security:
    Cookie values are NEVER printed, logged, or written to any output file.
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

try:
    import browser_cookie3
except ImportError:
    print("[tiktok] ERROR: pip install browser-cookie3", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / ".profile-copy"

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

SKIP_DOMAINS = {"tiktok.com", "www.tiktok.com", "vm.tiktok.com", "m.tiktok.com", "p16-sign.tiktokcdn-us.com"}

# TikTok's internal API endpoint for favorites
FAVORITES_API = "https://www.tiktok.com/api/favorite/item_list/"


def load_cookies(profile_path):
    """Load TikTok cookies from copied Chrome profile."""
    cookies_db = profile_path / "Default" / "Cookies"
    if not cookies_db.exists():
        raise SystemExit(f"[tiktok] Cookies DB not found: {cookies_db}")
    try:
        cj = browser_cookie3.chromium(cookie_file=str(cookies_db), domain_name=".tiktok.com")
    except Exception:
        try:
            cj = browser_cookie3.chrome(cookie_file=str(cookies_db), domain_name=".tiktok.com")
        except Exception as e:
            raise SystemExit(f"[tiktok] Failed to load cookies: {type(e).__name__}: {e}")
    count = sum(1 for _ in cj)
    has_session = any(c.name in ("sessionid", "sid_tt", "sessionid_ss") for c in cj)
    print(f"[tiktok] cookies loaded: {count} (session present: {has_session})", file=sys.stderr)
    return cj


def ts_to_date(ts):
    """Unix timestamp to human-readable date."""
    try:
        dt = datetime.fromtimestamp(int(ts), tz=timezone.utc)
        return dt.strftime("%B %d, %Y")
    except (ValueError, OSError, TypeError):
        return ""


def parse_tiktok_item(item):
    """Extract fields from a TikTok API item object."""
    video = item.get("video", {})
    author = item.get("author", {})
    stats = item.get("stats", {})
    desc = item.get("desc", "")

    video_id = item.get("id", "")
    unique_id = author.get("uniqueId", "")
    nickname = author.get("nickname", "")

    post_url = f"https://www.tiktok.com/@{unique_id}/video/{video_id}" if unique_id and video_id else ""

    # Date
    create_time = item.get("createTime", 0)
    date_str = ts_to_date(create_time)

    # Stats
    likes = stats.get("diggCount", 0)
    comments = stats.get("commentCount", 0)
    shares = stats.get("shareCount", 0)
    plays = stats.get("playCount", 0)

    # Duration
    duration = video.get("duration", 0)

    # Extract outbound URLs from description
    outbound = []
    urls = re.findall(r'https?://[^\s"<>\)]+', desc)
    for u in urls:
        parsed = urlparse(u)
        if parsed.netloc and parsed.netloc not in SKIP_DOMAINS:
            outbound.append({"label": parsed.netloc, "url": u})

    # Hashtags as tools/topics
    hashtags = re.findall(r'#(\w+)', desc)

    # Music
    music = item.get("music", {})
    music_title = music.get("title", "")

    # Clean description (remove excess hashtags at end)
    clean_desc = re.sub(r'(\s*#\w+){5,}$', '', desc).strip()

    return {
        "source": "tiktok",
        "post_url": post_url,
        "creator": f"@{unique_id}" if unique_id else "",
        "creator_name": nickname,
        "collection": "tiktok",
        "date": date_str,
        "media_type": "video",
        "caption_original": clean_desc,
        "summary": "",
        "card_title": "",
        "type": "resource",
        "tools_mentioned": [],
        "repos_or_projects_mentioned": [],
        "links": outbound[:15],
        "likes": likes,
        "plays": plays,
        "duration_sec": duration,
        "hashtags": hashtags[:20],
    }


def fetch_favorites_api(session, cursor=0, count=30):
    """Fetch favorites from TikTok's internal API."""
    params = {
        "count": count,
        "cursor": cursor,
        "aid": "1988",
        "app_language": "en",
        "app_name": "tiktok_web",
        "browser_language": "en-US",
        "browser_name": "Mozilla",
        "browser_platform": "Linux x86_64",
        "channel": "tiktok_web",
        "device_platform": "web_pc",
        "region": "US",
    }

    headers = {
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.tiktok.com/",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        r = session.get(FAVORITES_API, params=params, headers=headers, timeout=30)
    except requests.RequestException as e:
        print(f"[tiktok] Request failed: {e}", file=sys.stderr)
        return [], 0, False

    if r.status_code == 429:
        print("[tiktok] Rate limited (429) — waiting 30s", file=sys.stderr)
        time.sleep(30)
        return [], 0, False  # caller retries on next loop iteration

    if r.status_code != 200:
        print(f"[tiktok] HTTP {r.status_code}: {r.text[:200]}", file=sys.stderr)
        return [], 0, False

    data = r.json()

    if data.get("statusCode") != 0 and data.get("status_code") != 0:
        print(f"[tiktok] API error: status={data.get('statusCode', data.get('status_code'))}", file=sys.stderr)
        return [], 0, False

    items = data.get("itemList", [])
    has_more = data.get("hasMore", False)
    new_cursor = data.get("cursor", 0)

    return items, new_cursor, has_more


def fetch_favorites_html(session):
    """Fallback: scrape favorites from TikTok's HTML page (embedded JSON)."""
    headers = {
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    try:
        r = session.get("https://www.tiktok.com/", headers=headers, timeout=20)
        if r.status_code != 200:
            return []

        # Find logged-in user's unique_id — look specifically in user/login module
        m = (re.search(r'"LoginUserModule"\s*:\s*\{[^}]*"uniqueId"\s*:\s*"([^"]+)"', r.text)
             or re.search(r'"UserModule"\s*:\s*\{[^}]*"uniqueId"\s*:\s*"([^"]+)"', r.text)
             or re.search(r'"userInfo"\s*:\s*\{[^}]*"uniqueId"\s*:\s*"([^"]+)"', r.text))
        if not m:
            return []
        unique_id = m.group(1)

        # Navigate to favorites
        r = session.get(f"https://www.tiktok.com/@{unique_id}", headers=headers, timeout=20)
        if r.status_code != 200:
            return []

        # Extract SIGI_STATE or __UNIVERSAL_DATA
        json_m = re.search(r'<script[^>]*id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(\{.*?\})</script>', r.text)
        if not json_m:
            json_m = re.search(r'<script[^>]*id="SIGI_STATE"[^>]*>(\{.*?\})</script>', r.text)
        if not json_m:
            return []

        state = json.loads(json_m.group(1))
        # Extract items from state — structure varies by TikTok version
        items = []
        for key, val in state.items():
            if isinstance(val, dict) and "itemList" in val:
                items.extend(val["itemList"])
        return items

    except Exception as e:
        print(f"[tiktok] HTML fallback failed: {e}", file=sys.stderr)
        return []


def main():
    parser = argparse.ArgumentParser(description="Extract TikTok favorites to JSONL")
    parser.add_argument("--profile", type=str, default=None, help="Path to .profile-copy directory")
    parser.add_argument("--out", type=str, required=True, help="Output JSONL path")
    parser.add_argument("--limit", type=int, default=0, help="Max items to fetch (0 = all)")
    parser.add_argument("--pause", type=float, default=2.0, help="Seconds between API requests")
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

    all_items = []
    cursor = 0
    page_num = 0
    api_works = True

    # Try API first
    while api_works:
        page_num += 1
        print(f"[tiktok] Fetching page {page_num} (cursor={cursor})...", file=sys.stderr)

        raw_items, new_cursor, has_more = fetch_favorites_api(session, cursor)

        if not raw_items and page_num == 1:
            print("[tiktok] API returned no items — trying HTML fallback", file=sys.stderr)
            api_works = False
            break

        parsed = [parse_tiktok_item(it) for it in raw_items]
        parsed = [p for p in parsed if p and p["post_url"]]
        new_items = [p for p in parsed if p["post_url"] not in done]
        all_items.extend(new_items)

        print(f"[tiktok]   Got {len(raw_items)} items, {len(new_items)} new", file=sys.stderr)

        if not has_more:
            break
        if args.limit and len(all_items) >= args.limit:
            all_items = all_items[:args.limit]
            break

        cursor = new_cursor
        time.sleep(args.pause)

    # HTML fallback
    if not api_works:
        raw_items = fetch_favorites_html(session)
        parsed = [parse_tiktok_item(it) for it in raw_items]
        parsed = [p for p in parsed if p and p["post_url"]]
        new_items = [p for p in parsed if p["post_url"] not in done]
        all_items.extend(new_items)
        print(f"[tiktok] HTML fallback: got {len(new_items)} new items", file=sys.stderr)

    # Write output
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "a" if done else "w", encoding="utf-8") as f:
        for item in all_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    total = len(done) + len(all_items)
    print(f"[tiktok] Done: {len(all_items)} new items written, {total} total in {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
