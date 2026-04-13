#!/usr/bin/env python3
"""Extract Twitter/X bookmarks into DejaViewed JSONL format.

Uses X's internal GraphQL API with session cookies from a copied Chrome profile.
The ct0 cookie doubles as the CSRF token (sent as x-csrf-token header).

Usage:
    python3 adapters/twitter_bookmarks.py --out data/twitter_bookmarks.jsonl
    python3 adapters/twitter_bookmarks.py --profile /path/to/.profile-copy --out data/twitter_bookmarks.jsonl
    python3 adapters/twitter_bookmarks.py --limit 100 --out data/twitter_bookmarks.jsonl

Security:
    Cookie values are NEVER printed, logged, or written to any output file.
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse, quote

import requests

try:
    import browser_cookie3
except ImportError:
    print("[twitter] ERROR: pip install browser-cookie3", file=sys.stderr)
    sys.exit(1)

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / ".profile-copy"

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"

# X's public bearer token (embedded in the JS bundle, not a secret)
BEARER = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"

SKIP_DOMAINS = {"twitter.com", "x.com", "t.co", "pic.twitter.com", "pbs.twimg.com", "video.twimg.com", "abs.twimg.com"}

# Known GraphQL endpoint for bookmarks — the hash may change over time
# If this stops working, scrape the main.js bundle for the updated hash
BOOKMARKS_QUERY_ID = "yzqS_xwEwYMBiC_MgehMcg"
BOOKMARKS_FEATURES = {
    "graphql_timeline_v2_bookmark_timeline": True,
    "rweb_tipjar_consumption_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "articles_preview_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "tweetypie_unmention_optimization_enabled": True,
    "responsive_web_text_conversations_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
    "tweet_awards_web_tipping_enabled": False,
    "rweb_video_timestamps_enabled": True,
    "creator_subscriptions_quote_tweet_preview_enabled": False,
    "view_counts_everywhere_api_enabled": True,
}


def load_cookies(profile_path):
    """Load X/Twitter cookies from copied Chrome profile."""
    cookies_db = profile_path / "Default" / "Cookies"
    if not cookies_db.exists():
        raise SystemExit(f"[twitter] Cookies DB not found: {cookies_db}")
    try:
        cj = browser_cookie3.chromium(cookie_file=str(cookies_db), domain_name=".x.com")
    except Exception:
        try:
            cj = browser_cookie3.chrome(cookie_file=str(cookies_db), domain_name=".x.com")
        except Exception:
            # Try twitter.com domain
            try:
                cj = browser_cookie3.chromium(cookie_file=str(cookies_db), domain_name=".twitter.com")
            except Exception as e:
                raise SystemExit(f"[twitter] Failed to load cookies: {type(e).__name__}: {e}")
    count = sum(1 for _ in cj)
    has_ct0 = any(c.name == "ct0" for c in cj)
    has_auth = any(c.name == "auth_token" for c in cj)
    print(f"[twitter] cookies loaded: {count} (ct0: {has_ct0}, auth_token: {has_auth})", file=sys.stderr)
    if not has_ct0:
        print("[twitter] WARNING: no ct0 cookie — CSRF token missing, API calls will fail", file=sys.stderr)
    return cj


def get_csrf_token(cookie_jar):
    """Extract ct0 (CSRF token) from cookie jar. Value needed for header, not logging."""
    for c in cookie_jar:
        if c.name == "ct0":
            return c.value
    return None


def parse_tweet(tweet_result):
    """Extract fields from a tweet GraphQL result object."""
    if not tweet_result:
        return None

    # Navigate the nested structure
    tweet = tweet_result
    if "tweet" in tweet:
        tweet = tweet["tweet"]

    core = tweet.get("core", {})
    user_results = core.get("user_results", {}).get("result", {})
    legacy_user = user_results.get("legacy", {})
    legacy_tweet = tweet.get("legacy", {})

    if not legacy_tweet:
        return None

    tweet_id = legacy_tweet.get("id_str", tweet.get("rest_id", ""))
    full_text = legacy_tweet.get("full_text", "")
    screen_name = legacy_user.get("screen_name", "")
    name = legacy_user.get("name", "")

    # Date
    created_at = legacy_tweet.get("created_at", "")
    date_str = ""
    if created_at:
        try:
            dt = datetime.strptime(created_at, "%a %b %d %H:%M:%S %z %Y")
            date_str = dt.strftime("%B %d, %Y")
        except ValueError:
            date_str = created_at

    # Metrics
    likes = legacy_tweet.get("favorite_count", 0)
    retweets = legacy_tweet.get("retweet_count", 0)
    replies = legacy_tweet.get("reply_count", 0)
    views = tweet.get("views", {}).get("count", "")

    # Media type
    media_type = "tweet"
    media_entities = legacy_tweet.get("extended_entities", {}).get("media", [])
    if media_entities:
        mt = media_entities[0].get("type", "")
        if mt == "video" or mt == "animated_gif":
            media_type = "video"
        elif mt == "photo":
            media_type = "image"

    # Extract outbound URLs (expand t.co links)
    outbound = []
    urls_entities = legacy_tweet.get("entities", {}).get("urls", [])
    for ue in urls_entities:
        expanded = ue.get("expanded_url", ue.get("url", ""))
        if expanded:
            parsed = urlparse(expanded)
            if parsed.netloc and parsed.netloc not in SKIP_DOMAINS:
                outbound.append({"label": parsed.netloc, "url": expanded})

    # Clean display text (remove t.co URLs at end)
    clean_text = re.sub(r'\s*https://t\.co/\w+$', '', full_text).strip()

    # Card URL (for embedded links/articles)
    card = tweet.get("card", {})
    if card:
        card_url = card.get("legacy", {}).get("binding_values", [])
        for bv in card_url if isinstance(card_url, list) else []:
            if bv.get("key") == "card_url":
                cu = bv.get("value", {}).get("string_value", "")
                if cu:
                    parsed = urlparse(cu)
                    if parsed.netloc and parsed.netloc not in SKIP_DOMAINS:
                        if not any(l["url"] == cu for l in outbound):
                            outbound.append({"label": parsed.netloc, "url": cu})

    post_url = f"https://x.com/{screen_name}/status/{tweet_id}" if screen_name and tweet_id else ""

    return {
        "source": "twitter",
        "post_url": post_url,
        "creator": f"@{screen_name}" if screen_name else "",
        "creator_name": name,
        "collection": "twitter",
        "date": date_str,
        "media_type": media_type,
        "caption_original": clean_text,
        "summary": "",
        "card_title": "",
        "type": "resource",
        "tools_mentioned": [],
        "repos_or_projects_mentioned": [],
        "links": outbound[:15],
        "likes": likes,
        "retweets": retweets,
        "views": views,
    }


def fetch_bookmarks(session, csrf_token, cursor=None):
    """Fetch a page of bookmarks from X's GraphQL API."""
    variables = {"count": 20, "includePromotedContent": False}
    if cursor:
        variables["cursor"] = cursor

    params = {
        "variables": json.dumps(variables),
        "features": json.dumps(BOOKMARKS_FEATURES),
    }

    headers = {
        "User-Agent": UA,
        "Authorization": f"Bearer {BEARER}",
        "x-csrf-token": csrf_token,
        "x-twitter-active-user": "yes",
        "x-twitter-auth-type": "OAuth2Session",
        "x-twitter-client-language": "en",
        "Referer": "https://x.com/i/bookmarks",
    }

    url = f"https://x.com/i/api/graphql/{BOOKMARKS_QUERY_ID}/Bookmarks"

    try:
        r = session.get(url, params=params, headers=headers, timeout=30)
    except requests.RequestException as e:
        print(f"[twitter] Request failed: {e}", file=sys.stderr)
        return [], None

    if r.status_code == 429:
        print("[twitter] Rate limited (429) — waiting 60s", file=sys.stderr)
        time.sleep(60)
        return [], None  # caller retries on next loop iteration

    if r.status_code != 200:
        print(f"[twitter] HTTP {r.status_code} (body omitted for security)", file=sys.stderr)
        return [], None

    data = r.json()

    # Navigate the response structure
    timeline = (data.get("data", {})
                .get("bookmark_timeline_v2", {})
                .get("timeline", {})
                .get("instructions", []))

    entries = []
    next_cursor = None

    for instruction in timeline:
        if instruction.get("type") == "TimelineAddEntries":
            for entry in instruction.get("entries", []):
                content = entry.get("content", {})
                entry_type = content.get("entryType", "")

                if entry_type == "TimelineTimelineItem":
                    tweet_result = (content.get("itemContent", {})
                                    .get("tweet_results", {})
                                    .get("result", {}))
                    parsed = parse_tweet(tweet_result)
                    if parsed:
                        entries.append(parsed)

                elif entry_type == "TimelineTimelineCursor":
                    if content.get("cursorType") == "Bottom":
                        next_cursor = content.get("value")

    return entries, next_cursor


def discover_query_id(session, csrf_token):
    """Try to discover the current Bookmarks query ID from X's JS bundles.
    Falls back to the hardcoded one if discovery fails."""
    headers = {
        "User-Agent": UA,
        "Authorization": f"Bearer {BEARER}",
        "x-csrf-token": csrf_token,
        "x-twitter-auth-type": "OAuth2Session",
    }
    try:
        r = session.get("https://x.com/i/bookmarks", headers={"User-Agent": UA}, timeout=15)
        if r.status_code != 200:
            return BOOKMARKS_QUERY_ID
        # Find main JS bundle URLs
        js_urls = re.findall(r'src="(https://abs\.twimg\.com/responsive-web/client-web[^"]*\.js)"', r.text)
        for js_url in js_urls[:5]:
            jr = session.get(js_url, headers={"User-Agent": UA}, timeout=15)
            if jr.status_code == 200:
                # Look for Bookmarks query ID pattern
                m = re.search(r'queryId:"([^"]+)"[^}]*operationName:"Bookmarks"', jr.text)
                if m:
                    print(f"[twitter] Discovered query ID: {m.group(1)}", file=sys.stderr)
                    return m.group(1)
    except Exception:
        pass
    return BOOKMARKS_QUERY_ID


def main():
    parser = argparse.ArgumentParser(description="Extract Twitter/X bookmarks to JSONL")
    parser.add_argument("--profile", type=str, default=None, help="Path to .profile-copy directory")
    parser.add_argument("--out", type=str, required=True, help="Output JSONL path")
    parser.add_argument("--limit", type=int, default=0, help="Max items to fetch (0 = all)")
    parser.add_argument("--pause", type=float, default=3.0, help="Seconds between API requests")
    parser.add_argument("--no-discover", action="store_true", help="Skip query ID discovery")
    args = parser.parse_args()

    profile_path = Path(args.profile) if args.profile else PROFILE
    cj = load_cookies(profile_path)

    session = requests.Session()
    session.cookies = cj

    csrf_token = get_csrf_token(cj)
    if not csrf_token:
        print("[twitter] No ct0 cookie found — cannot authenticate", file=sys.stderr)
        sys.exit(1)

    # Try to discover current query ID
    global BOOKMARKS_QUERY_ID
    if not args.no_discover:
        BOOKMARKS_QUERY_ID = discover_query_id(session, csrf_token)

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
    cursor = None
    page_num = 0

    while True:
        page_num += 1
        print(f"[twitter] Fetching page {page_num}...", file=sys.stderr)

        entries, next_cursor = fetch_bookmarks(session, csrf_token, cursor)

        new_items = [e for e in entries if e["post_url"] not in done]
        all_items.extend(new_items)

        print(f"[twitter]   Got {len(entries)} tweets, {len(new_items)} new", file=sys.stderr)

        if not entries or not next_cursor:
            break

        if args.limit and len(all_items) >= args.limit:
            all_items = all_items[:args.limit]
            break

        cursor = next_cursor
        time.sleep(args.pause)

    # Write output
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "a" if done else "w", encoding="utf-8") as f:
        for item in all_items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    total = len(done) + len(all_items)
    print(f"[twitter] Done: {len(all_items)} new bookmarks written, {total} total in {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
