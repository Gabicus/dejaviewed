#!/usr/bin/env python3
"""Extract Pinterest saved pins/boards into DejaViewed JSONL format.

Uses Pinterest's internal API with session cookies from a copied Chrome profile.

Usage:
    python3 adapters/pinterest_boards.py --out data/pinterest_saved.jsonl
    python3 adapters/pinterest_boards.py --boards "AI Tools,Design Inspo" --out data/pinterest_saved.jsonl
    python3 adapters/pinterest_boards.py --all-boards --out data/pinterest_saved.jsonl

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
from urllib.parse import urlparse

import requests

try:
    import browser_cookie3
except ImportError:
    print("[pinterest] ERROR: pip install browser-cookie3", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / ".profile-copy"

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

SKIP_DOMAINS = {
    "pinterest.com", "www.pinterest.com", "i.pinimg.com",
    "pin.it", "pinimg.com", "s.pinimg.com",
}

# Pinterest internal API base
API_BASE = "https://www.pinterest.com/resource"


def load_cookies(profile_path):
    """Load Pinterest cookies from copied Chrome profile."""
    cookies_db = profile_path / "Default" / "Cookies"
    if not cookies_db.exists():
        raise SystemExit(f"[pinterest] Cookies DB not found: {cookies_db}")
    try:
        cj = browser_cookie3.chromium(cookie_file=str(cookies_db), domain_name=".pinterest.com")
    except Exception:
        try:
            cj = browser_cookie3.chrome(cookie_file=str(cookies_db), domain_name=".pinterest.com")
        except Exception as e:
            raise SystemExit(f"[pinterest] Failed to load cookies: {type(e).__name__}: {e}")
    count = sum(1 for _ in cj)
    has_session = any(c.name == "_pinterest_sess" for c in cj)
    print(f"[pinterest] cookies loaded: {count} (session present: {has_session})", file=sys.stderr)
    return cj


def get_csrf_token(cookie_jar):
    """Extract csrftoken from cookies."""
    for c in cookie_jar:
        if c.name == "csrftoken":
            return c.value
    return None


def get_api_headers(csrf_token):
    """Build headers for Pinterest's internal API."""
    return {
        "User-Agent": UA,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrf_token or "",
        "X-Pinterest-AppState": "active",
        "X-APP-VERSION": "0",
        "Referer": "https://www.pinterest.com/",
        "Origin": "https://www.pinterest.com",
    }


def get_user_info(session, headers):
    """Get current logged-in user's info."""
    data = {
        "source_url": "/",
        "data": json.dumps({
            "options": {},
            "context": {}
        }),
    }
    try:
        r = session.get(
            f"{API_BASE}/UserResource/get/",
            params=data,
            headers=headers,
            timeout=15,
        )
        if r.status_code == 200:
            result = r.json()
            user = result.get("resource_response", {}).get("data", {})
            return user.get("username"), user.get("full_name")
    except Exception:
        pass

    # Fallback: parse from homepage
    try:
        r = session.get("https://www.pinterest.com/", headers={"User-Agent": UA}, timeout=15)
        if r.status_code == 200:
            m = re.search(r'"username"\s*:\s*"([^"]+)"', r.text)
            if m:
                return m.group(1), None
    except Exception:
        pass
    return None, None


def get_boards(session, headers, username):
    """Get all boards for a user."""
    boards = []
    bookmark = None

    while True:
        options = {
            "username": username,
            "page_size": 25,
            "privacy_filter": "all",
            "sort": "last_pinned_to",
            "field_set_key": "profile_grid_item",
            "include_archived": True,
        }
        if bookmark:
            options["bookmarks"] = [bookmark]

        data = {
            "source_url": f"/{username}/boards/",
            "data": json.dumps({"options": options, "context": {}}),
        }

        try:
            r = session.get(
                f"{API_BASE}/BoardsResource/get/",
                params=data,
                headers=headers,
                timeout=20,
            )
        except requests.RequestException as e:
            print(f"[pinterest] Board fetch failed: {e}", file=sys.stderr)
            break

        if r.status_code != 200:
            print(f"[pinterest] Board fetch HTTP {r.status_code}", file=sys.stderr)
            break

        result = r.json()
        resource = result.get("resource_response", {})
        board_list = resource.get("data", [])

        if not board_list:
            break

        for b in board_list:
            if isinstance(b, dict) and b.get("id"):
                boards.append({
                    "id": b["id"],
                    "name": b.get("name", ""),
                    "url": b.get("url", ""),
                    "pin_count": b.get("pin_count", 0),
                })

        bookmark = resource.get("bookmark")
        if not bookmark or bookmark == "-end-":
            break
        time.sleep(1)

    return boards


def get_board_pins(session, headers, board_id, board_name, done_urls, limit=0):
    """Get all pins from a board."""
    pins = []
    bookmark = None
    page = 0

    while True:
        page += 1
        options = {
            "board_id": board_id,
            "page_size": 25,
            "field_set_key": "partner",
        }
        if bookmark:
            options["bookmarks"] = [bookmark]

        data = {
            "source_url": f"/board/{board_id}/",
            "data": json.dumps({"options": options, "context": {}}),
        }

        try:
            r = session.get(
                f"{API_BASE}/BoardFeedResource/get/",
                params=data,
                headers=headers,
                timeout=20,
            )
        except requests.RequestException as e:
            print(f"[pinterest]   Board feed request failed: {e}", file=sys.stderr)
            break

        if r.status_code == 429:
            print("[pinterest]   Rate limited — waiting 30s", file=sys.stderr)
            time.sleep(30)
            continue

        if r.status_code != 200:
            print(f"[pinterest]   Board feed HTTP {r.status_code}", file=sys.stderr)
            break

        result = r.json()
        resource = result.get("resource_response", {})
        pin_list = resource.get("data", [])

        if not pin_list:
            break

        for pin in pin_list:
            if not isinstance(pin, dict) or not pin.get("id"):
                continue

            parsed = parse_pin(pin, board_name)
            if parsed and parsed["post_url"] not in done_urls:
                pins.append(parsed)

        print(f"[pinterest]   Page {page}: {len(pin_list)} pins, {len(pins)} total new", file=sys.stderr)

        if limit and len(pins) >= limit:
            pins = pins[:limit]
            break

        bookmark = resource.get("bookmark")
        if not bookmark or bookmark == "-end-":
            break
        time.sleep(1.5)

    return pins


def parse_pin(pin, board_name):
    """Parse a pin object into DejaViewed JSONL format."""
    pin_id = pin.get("id", "")
    description = pin.get("description", "") or ""
    title = pin.get("title", "") or pin.get("grid_title", "") or ""

    # Pinner / source
    pinner = pin.get("pinner", {}) or {}
    pinner_name = pinner.get("full_name", "") or pinner.get("username", "")

    # Rich metadata (article pins)
    rich = pin.get("rich_metadata", {}) or {}
    rich_title = rich.get("title", "")
    rich_desc = rich.get("description", "")
    site_name = rich.get("site_name", "")

    # Source link (the linked website)
    source_url = pin.get("link", "") or ""
    domain_name = pin.get("domain", "") or ""

    # Build outbound links
    outbound = []
    if source_url:
        parsed = urlparse(source_url)
        if parsed.netloc and parsed.netloc not in SKIP_DOMAINS:
            label = domain_name or parsed.netloc
            outbound.append({"label": label, "url": source_url})

    # Additional URLs from description
    desc_urls = re.findall(r'https?://[^\s"<>\)]+', description)
    for u in desc_urls:
        parsed = urlparse(u)
        if parsed.netloc and parsed.netloc not in SKIP_DOMAINS:
            if not any(l["url"] == u for l in outbound):
                outbound.append({"label": parsed.netloc, "url": u})

    # Thumbnail
    images = pin.get("images", {}) or {}
    orig = images.get("orig", {}) or images.get("736x", {}) or {}
    thumb_url = orig.get("url", "")

    # Media type
    media_type = "image"
    if pin.get("videos"):
        media_type = "video"
    elif pin.get("is_video"):
        media_type = "video"
    elif pin.get("story_pin_data"):
        media_type = "story"

    # Date
    created_at = pin.get("created_at", "")
    date_str = ""
    if created_at:
        try:
            # Pinterest dates: "Thu, 15 Feb 2024 12:00:00 +0000" or ISO format
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(created_at)
            date_str = dt.strftime("%B %d, %Y")
        except Exception:
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                date_str = dt.strftime("%B %d, %Y")
            except Exception:
                date_str = created_at[:10] if len(created_at) >= 10 else ""

    # Best title: rich > pin title > description truncated
    card_title = rich_title or title or (description[:70] + "..." if len(description) > 70 else description)

    # Best description: combine sources
    caption = description
    if rich_desc and rich_desc != description:
        caption = f"{description}\n\n{rich_desc}" if description else rich_desc

    post_url = f"https://www.pinterest.com/pin/{pin_id}/" if pin_id else ""

    if not post_url:
        return None

    return {
        "source": "pinterest",
        "post_url": post_url,
        "creator": pinner_name,
        "collection": board_name or "pinterest",
        "date": date_str,
        "media_type": media_type,
        "caption_original": caption,
        "summary": "",
        "card_title": card_title,
        "type": "resource",
        "tools_mentioned": [],
        "repos_or_projects_mentioned": [],
        "links": outbound[:15],
        "thumbnail_url": thumb_url,
        "domain": domain_name,
        "site_name": site_name,
    }


def main():
    parser = argparse.ArgumentParser(description="Extract Pinterest board pins to JSONL")
    parser.add_argument("--profile", type=str, default=None, help="Path to .profile-copy directory")
    parser.add_argument("--out", type=str, required=True, help="Output JSONL path")
    parser.add_argument("--boards", type=str, default=None,
                        help="Comma-separated board names to scrape (default: all)")
    parser.add_argument("--all-boards", action="store_true", help="Scrape all boards")
    parser.add_argument("--limit", type=int, default=0, help="Max pins per board (0 = all)")
    parser.add_argument("--pause", type=float, default=2.0, help="Seconds between requests")
    args = parser.parse_args()

    profile_path = Path(args.profile) if args.profile else PROFILE
    cj = load_cookies(profile_path)

    session = requests.Session()
    session.cookies = cj

    csrf = get_csrf_token(cj)
    if not csrf:
        print("[pinterest] WARNING: No csrftoken found — API may reject requests", file=sys.stderr)

    headers = get_api_headers(csrf)

    username, full_name = get_user_info(session, headers)
    if not username:
        print("[pinterest] Could not detect username. Are you logged in?", file=sys.stderr)
        sys.exit(1)
    print(f"[pinterest] Logged in as: {username} ({full_name or 'N/A'})", file=sys.stderr)

    # Get boards
    boards = get_boards(session, headers, username)
    print(f"[pinterest] Found {len(boards)} boards", file=sys.stderr)

    # Filter boards if specified
    if args.boards:
        filter_names = {n.strip().lower() for n in args.boards.split(",")}
        boards = [b for b in boards if b["name"].lower() in filter_names]
        print(f"[pinterest] Filtered to {len(boards)} boards", file=sys.stderr)

    if not boards:
        print("[pinterest] No boards to scrape", file=sys.stderr)
        sys.exit(0)

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

    all_pins = []
    for board in boards:
        print(f"[pinterest] Board: {board['name']} ({board['pin_count']} pins)", file=sys.stderr)
        pins = get_board_pins(session, headers, board["id"], board["name"], done, args.limit)
        all_pins.extend(pins)
        time.sleep(args.pause)

    # Write output
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "a" if done else "w", encoding="utf-8") as f:
        for pin in all_pins:
            f.write(json.dumps(pin, ensure_ascii=False) + "\n")

    total = len(done) + len(all_pins)
    print(f"[pinterest] Done: {len(all_pins)} new pins written, {total} total in {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
