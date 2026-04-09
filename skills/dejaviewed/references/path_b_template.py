#!/usr/bin/env python3
"""
Path B scraper — loads Instagram session cookies from a copied Chrome profile
and scrapes post HTML directly via requests. No browser, no MCP, no token echo.

Security:
- Cookie values are NEVER printed, logged, or written to any output file.
- Only existence checks ('session cookie present: yes/no').
- Cookies stay inside the requests.Session object and are garbage-collected on exit.

Usage:
    python3 path_b.py --collection ai1 --urls urls.txt --out ai1_posts_pathb.jsonl
    python3 path_b.py --collection ai1 --benchmark  # run on already-scraped urls for A/B
"""
import argparse, json, re, sys, time, sqlite3, os, html
from pathlib import Path
from http.cookiejar import Cookie, CookieJar

import requests

ROOT = Path(__file__).parent
PROFILE = ROOT / ".profile-copy"
DATA = ROOT / "data"

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Upgrade-Insecure-Requests": "1",
}


def load_cookies_from_profile() -> CookieJar:
    """Load Instagram cookies from the copied Chromium profile SQLite DB.
    Uses browser_cookie3 which handles Linux keyring decryption."""
    import browser_cookie3
    cookies_db = PROFILE / "Default" / "Cookies"
    if not cookies_db.exists():
        raise SystemExit(f"ERROR: cookies db not found at {cookies_db}")
    try:
        cj = browser_cookie3.chromium(cookie_file=str(cookies_db), domain_name="instagram.com")
    except Exception as e:
        raise SystemExit(f"ERROR: failed to load cookies from profile: {type(e).__name__}: {e}")
    # Don't print cookie values — just count.
    count = sum(1 for _ in cj)
    has_session = any(c.name == "sessionid" for c in cj)
    print(f"cookies loaded: {count} (sessionid present: {has_session})", file=sys.stderr)
    return cj


def extract_from_html(html_text: str, post_url: str) -> dict:
    """Parse an Instagram post HTML page for caption, handle, links, etc.
    Strategy: og: meta tags first, then embedded JSON (XDTMediaDict), then fallback regex."""
    rec = {
        "post_url": post_url,
        "creator": None,
        "date": None,
        "media_type": None,
        "caption": None,
        "outbound_links": [],
        "likes": None,
        "comments": None,
        "status": "ok",
    }

    # og:description usually = "N likes, M comments - @handle on DATE: "caption""
    m = re.search(r'<meta property="og:description" content="([^"]*)"', html_text)
    if m:
        desc = html.unescape(m.group(1))
        # likes/comments
        lm = re.search(r'([\d,KM.]+)\s+likes?', desc)
        cm = re.search(r'([\d,KM.]+)\s+comments?', desc)
        if lm:
            rec["likes"] = lm.group(1)
        if cm:
            rec["comments"] = cm.group(1)
        # handle
        hm = re.search(r'-\s*@?([\w._]+)\s+on', desc) or re.search(r'@([\w._]+)', desc)
        if hm:
            rec["creator"] = "@" + hm.group(1)
        # date
        dm = re.search(r'on (\w+ \d+, \d{4})', desc)
        if dm:
            rec["date"] = dm.group(1)
        # caption: strip "N likes, M comments - handle on DATE: " prefix, then unquote
        caption = re.sub(r'^[\d,KM.]+\s+likes?,?\s*[\d,KM.]*\s*comments?\s*-\s*[\w._]+\s*on\s+\w+\s+\d+,\s*\d{4}\u200e?\s*:\s*', '', desc)
        caption = caption.strip()
        caption = re.sub(r'^["\u201c\u201d]+|["\u201c\u201d.]+$', '', caption).strip()
        rec["caption"] = caption or desc

    # og:title sometimes has handle too
    if not rec["creator"]:
        tm = re.search(r'<meta property="og:title" content="([^"]*)"', html_text)
        if tm:
            hm = re.search(r'@([\w._]+)', tm.group(1))
            if hm:
                rec["creator"] = "@" + hm.group(1)

    # Media type: URL pattern is the most reliable
    if "/reel/" in post_url:
        rec["media_type"] = "reel"
    elif re.search(r'<meta property="og:video"', html_text):
        rec["media_type"] = "video"
    elif re.search(r'<meta property="og:image"', html_text):
        rec["media_type"] = "image"

    # Additional outbound link extraction: look for linkified anchors inside JSON blobs embedded in page
    # Instagram embeds its SSR data as JSON in <script type="application/json"> or inline script
    # Search for any http(s) URL in the raw HTML that's not instagram/facebook/fbcdn
    all_urls = set(rec.get("outbound_links") or [])
    for url_match in re.finditer(r'https?:\\?/\\?/[^\s"\'<>\\]+', html_text):
        u = url_match.group(0).replace('\\/', '/').rstrip('.,;!?)')
        if any(skip in u for skip in ("instagram.com", "facebook.com", "fbcdn.net", "cdninstagram", "fb.com", "w3.org", "schema.org", "gstatic", "googleapis")):
            continue
        if len(u) < 12 or len(u) > 300:
            continue
        all_urls.add(u)
    rec["outbound_links"] = sorted(all_urls)[:25]  # cap to avoid noise

    # Outbound links — search full caption text for URLs
    if rec["caption"]:
        urls = re.findall(r'https?://[^\s"<>\)]+', rec["caption"])
        rec["outbound_links"] = [u for u in urls if "instagram.com" not in u]

    # Also search the full HTML for outbound links in linkified anchor tags
    anchor_urls = re.findall(r'<a[^>]+href="(https?://[^"]+)"', html_text)
    for u in anchor_urls:
        if "instagram.com" not in u and "facebook.com" not in u and u not in rec["outbound_links"]:
            rec["outbound_links"].append(u)

    if not rec["caption"] and not rec["creator"]:
        rec["status"] = "failed_parse"

    return rec


def scrape_url(session: requests.Session, url: str, retries: int = 2) -> dict:
    for attempt in range(retries + 1):
        try:
            r = session.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
            if r.status_code == 200:
                return extract_from_html(r.text, url)
            if r.status_code in (404, 410):
                return {"post_url": url, "status": f"http_{r.status_code}"}
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(5 * (attempt + 1))
                continue
            return {"post_url": url, "status": f"http_{r.status_code}"}
        except requests.RequestException as e:
            if attempt < retries:
                time.sleep(3 * (attempt + 1))
                continue
            return {"post_url": url, "status": f"error:{type(e).__name__}"}
    return {"post_url": url, "status": "exhausted_retries"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--collection", required=True, choices=["ai1", "ai2", "ai4"])
    ap.add_argument("--urls-file", help="JSON file with a 'urls' array")
    ap.add_argument("--benchmark", action="store_true", help="scrape URLs already in path A jsonl (for A/B diff)")
    ap.add_argument("--out", help="output JSONL path (default: data/<collection>_posts_pathb.jsonl)")
    ap.add_argument("--pause", type=float, default=1.5, help="seconds between requests")
    ap.add_argument("--limit", type=int, default=0, help="cap number of requests (0 = no cap)")
    args = ap.parse_args()

    cj = load_cookies_from_profile()
    session = requests.Session()
    session.cookies = cj  # type: ignore

    # Determine URL list
    if args.benchmark:
        path_a = DATA / f"{args.collection}_posts.jsonl"
        if not path_a.exists():
            raise SystemExit(f"no path A jsonl at {path_a}")
        urls = []
        for line in path_a.read_text().splitlines():
            if not line.strip():
                continue
            try:
                urls.append(json.loads(line)["post_url"])
            except Exception:
                pass
        out_path = DATA / f"{args.collection}_posts_pathb_benchmark.jsonl"
    elif args.urls_file:
        urls = json.loads(Path(args.urls_file).read_text())["urls"]
        out_path = Path(args.out) if args.out else DATA / f"{args.collection}_posts_pathb.jsonl"
    else:
        raise SystemExit("need --benchmark or --urls-file")

    if args.limit:
        urls = urls[: args.limit]

    # Resume: skip urls already in out
    done = set()
    if out_path.exists():
        for line in out_path.read_text().splitlines():
            if not line.strip():
                continue
            try:
                done.add(json.loads(line)["post_url"])
            except Exception:
                pass

    todo = [u for u in urls if u not in done]
    print(f"collection={args.collection} total={len(urls)} done={len(done)} todo={len(todo)} out={out_path}", file=sys.stderr)

    t0 = time.time()
    ok = 0
    fail = 0
    with out_path.open("a") as f:
        for i, url in enumerate(todo, 1):
            rec = scrape_url(session, url)
            rec["collection"] = args.collection
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            status = rec.get("status", "ok")
            if status == "ok":
                ok += 1
            else:
                fail += 1
            print(f"[{i}/{len(todo)}] {status} {url[-20:]}", file=sys.stderr)
            time.sleep(args.pause)

    dt = time.time() - t0
    print(f"\ndone: ok={ok} fail={fail} total={ok+fail} elapsed={dt:.1f}s", file=sys.stderr)


if __name__ == "__main__":
    main()
