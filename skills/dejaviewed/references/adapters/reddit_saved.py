#!/usr/bin/env python3
"""Extract Reddit saved posts/comments into DejaViewed JSONL format.

Scrapes old.reddit.com/user/<you>/saved with session cookies from a copied
Chrome profile. old.reddit.com serves simple HTML — no JS rendering needed.

Usage:
    python3 adapters/reddit_saved.py --out data/reddit_saved.jsonl
    python3 adapters/reddit_saved.py --profile /path/to/.profile-copy --out data/reddit_saved.jsonl
    python3 adapters/reddit_saved.py --limit 50 --out data/reddit_saved.jsonl

Security:
    Cookie values are NEVER printed, logged, or written to any output file.
"""

import argparse
import json
import os
import re
import sys
import time
from html import unescape
from pathlib import Path
from urllib.parse import urlparse, urljoin

import requests

try:
    import browser_cookie3
except ImportError:
    print("[reddit] ERROR: pip install browser-cookie3", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / ".profile-copy"

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

SKIP_DOMAINS = {"reddit.com", "www.reddit.com", "old.reddit.com", "i.redd.it", "v.redd.it", "preview.redd.it"}


def load_cookies(profile_path):
    """Load Reddit cookies from copied Chrome profile."""
    cookies_db = profile_path / "Default" / "Cookies"
    if not cookies_db.exists():
        raise SystemExit(f"[reddit] Cookies DB not found: {cookies_db}")
    try:
        cj = browser_cookie3.chromium(cookie_file=str(cookies_db), domain_name=".reddit.com")
    except Exception:
        try:
            cj = browser_cookie3.chrome(cookie_file=str(cookies_db), domain_name=".reddit.com")
        except Exception as e:
            raise SystemExit(f"[reddit] Failed to load cookies: {type(e).__name__}: {e}")
    count = sum(1 for _ in cj)
    has_session = any(c.name in ("reddit_session", "token_v2") for c in cj)
    print(f"[reddit] cookies loaded: {count} (session present: {has_session})", file=sys.stderr)
    return cj


def get_username(session):
    """Detect the logged-in Reddit username."""
    r = session.get("https://old.reddit.com/api/me.json", headers=HEADERS, timeout=15)
    if r.status_code == 200:
        data = r.json()
        name = data.get("data", {}).get("name")
        if name:
            return name
    # Fallback: scrape the old.reddit.com page for username
    r = session.get("https://old.reddit.com/", headers=HEADERS, timeout=15)
    if r.status_code == 200:
        m = re.search(r'logged-in-as["\s>]+[^>]*href="/user/([^/"]+)"', r.text)
        if m:
            return m.group(1)
        m = re.search(r'/user/([\w_-]+)"[^>]*>[\w_-]+</a>\s*\(\d+', r.text)
        if m:
            return m.group(1)
    return None


def parse_saved_page(html_text):
    """Parse a page of old.reddit.com saved items. Returns (items, next_url)."""
    items = []

    # Split on thing divs: <div class=" thing" id="thing_t3_xxxxx" ...>
    # Each block contains the data- attributes and content for one saved item
    thing_blocks = re.split(r'<div[^>]*class="[^"]*\bthing\b[^"]*"', html_text)

    for block in thing_blocks[1:]:  # skip pre-first-thing content
        item = {}

        # data attributes
        fn = re.search(r'data-fullname="([^"]*)"', block)
        du = re.search(r'data-url="([^"]*)"', block)
        ds = re.search(r'data-subreddit="([^"]*)"', block)
        da = re.search(r'data-author="([^"]*)"', block)
        dt = re.search(r'data-timestamp="([^"]*)"', block)
        dtype = re.search(r'data-type="([^"]*)"', block)

        if not fn:
            continue

        fullname = fn.group(1)
        is_comment = fullname.startswith("t1_")

        # Title (for posts)
        title_m = re.search(r'<a[^>]*class="[^"]*title[^"]*"[^>]*>([^<]+)</a>', block)
        title = unescape(title_m.group(1).strip()) if title_m else ""

        # Self-text / comment body
        body_m = re.search(r'<div[^>]*class="[^"]*md[^"]*"[^>]*>(.*?)</div>', block, re.DOTALL)
        body = ""
        if body_m:
            body = re.sub(r'<[^>]+>', ' ', body_m.group(1)).strip()
            body = re.sub(r'\s+', ' ', body)
            body = unescape(body)

        # Permalink
        perm_m = re.search(r'data-permalink="([^"]*)"', block)
        permalink = perm_m.group(1) if perm_m else ""
        if permalink and not permalink.startswith("http"):
            permalink = "https://old.reddit.com" + permalink

        # Score
        score_m = re.search(r'<span[^>]*class="[^"]*score[^"]*"[^>]*title="(\d+)"', block)
        score = score_m.group(1) if score_m else None

        # External URL (for link posts)
        ext_url = du.group(1) if du else ""
        if ext_url and ext_url.startswith("/"):
            ext_url = "https://old.reddit.com" + ext_url

        # Outbound links from body
        outbound = []
        if ext_url:
            parsed = urlparse(ext_url)
            if parsed.netloc and parsed.netloc not in SKIP_DOMAINS:
                outbound.append({"label": parsed.netloc, "url": ext_url})
        body_links = re.findall(r'href="(https?://[^"]+)"', block)
        for link in body_links:
            parsed = urlparse(link)
            if parsed.netloc and parsed.netloc not in SKIP_DOMAINS and link != ext_url:
                outbound.append({"label": parsed.netloc, "url": link})

        # Subreddit
        subreddit = ds.group(1) if ds else ""
        author = da.group(1) if da else ""

        # Timestamp
        date_str = ""
        if dt:
            try:
                from datetime import datetime, timezone
                ts_ms = int(dt.group(1))
                date_str = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc).strftime("%B %d, %Y")
            except (ValueError, OSError):
                pass
        if not date_str:
            time_m = re.search(r'<time[^>]*datetime="([^"]*)"', block)
            if time_m:
                date_str = time_m.group(1)[:10]

        # Build caption
        if is_comment:
            caption = body[:500] if body else "(saved comment)"
            media_type = "comment"
            card_title = title or f"Comment in r/{subreddit}" if subreddit else "Saved comment"
        else:
            caption = body[:500] if body else title
            media_type = "post"
            card_title = title

        # Determine post URL
        post_url = permalink or ext_url or ""

        if not post_url:
            continue

        items.append({
            "source": "reddit",
            "post_url": post_url,
            "creator": f"u/{author}" if author else "",
            "collection": f"r/{subreddit}" if subreddit else "reddit",
            "date": date_str,
            "media_type": media_type,
            "caption_original": caption,
            "summary": "",
            "card_title": card_title,
            "type": "resource",
            "tools_mentioned": [],
            "repos_or_projects_mentioned": [],
            "links": outbound[:15],
            "score": score,
            "fullname": fullname,
        })

    # Find "next" page link
    next_url = None
    next_m = re.search(r'<a[^>]*rel="next"[^>]*href="([^"]*)"', html_text)
    if next_m:
        next_url = unescape(next_m.group(1))
        if not next_url.startswith("http"):
            next_url = "https://old.reddit.com" + next_url

    return items, next_url


def main():
    parser = argparse.ArgumentParser(description="Extract Reddit saved posts to JSONL")
    parser.add_argument("--profile", type=str, default=None, help="Path to .profile-copy directory")
    parser.add_argument("--out", type=str, required=True, help="Output JSONL path")
    parser.add_argument("--limit", type=int, default=0, help="Max items to fetch (0 = all)")
    parser.add_argument("--pause", type=float, default=2.0, help="Seconds between page requests")
    args = parser.parse_args()

    profile_path = Path(args.profile) if args.profile else PROFILE
    cj = load_cookies(profile_path)

    session = requests.Session()
    session.cookies = cj

    username = get_username(session)
    if not username:
        print("[reddit] Could not detect username. Are you logged in?", file=sys.stderr)
        sys.exit(1)
    print(f"[reddit] Logged in as: {username}", file=sys.stderr)

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

    url = f"https://old.reddit.com/user/{username}/saved/"
    all_items = []
    page_num = 0

    while url:
        page_num += 1
        print(f"[reddit] Page {page_num}: {url[:80]}...", file=sys.stderr)

        try:
            r = session.get(url, headers=HEADERS, timeout=20)
        except requests.RequestException as e:
            print(f"[reddit] Request failed: {e}", file=sys.stderr)
            break

        if r.status_code == 403:
            print("[reddit] 403 Forbidden — session may be expired", file=sys.stderr)
            break
        if r.status_code != 200:
            print(f"[reddit] HTTP {r.status_code}", file=sys.stderr)
            break

        items, next_url = parse_saved_page(r.text)
        new_items = [it for it in items if it["post_url"] not in done]
        all_items.extend(new_items)

        print(f"[reddit]   Found {len(items)} items, {len(new_items)} new", file=sys.stderr)

        if args.limit and len(all_items) >= args.limit:
            all_items = all_items[:args.limit]
            break

        url = next_url
        if url:
            time.sleep(args.pause)

    # Write output
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "a" if done else "w", encoding="utf-8") as f:
        for item in all_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    total = len(done) + len(all_items)
    print(f"[reddit] Done: {len(all_items)} new items written, {total} total in {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
