#!/usr/bin/env python3
"""Fetch Open Graph thumbnails for Instagram posts in catalog.jsonl."""
import json, re, sys, time, html
from pathlib import Path
import requests

sys.path.insert(0, str(Path(__file__).parent))
from path_b import load_cookies_from_profile, HEADERS

ROOT = Path(__file__).parent
CATALOG = ROOT / "data" / "catalog.jsonl"
THUMB_DIR = ROOT / "site" / "thumb"
THUMB_DIR.mkdir(parents=True, exist_ok=True)

SHORTCODE_RE = re.compile(r"instagram\.com/(?:p|reel|tv)/([^/?#]+)")
OG_RE = re.compile(r'<meta property="og:image" content="([^"]+)"')


def shortcode_of(url: str):
    m = SHORTCODE_RE.search(url)
    return m.group(1) if m else None


def main():
    urls = []
    for line in CATALOG.read_text().splitlines():
        if not line.strip():
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        u = rec.get("post_url", "")
        if u.startswith("https://www.instagram.com/"):
            urls.append(u)

    # dedupe by shortcode
    seen = {}
    for u in urls:
        sc = shortcode_of(u)
        if sc and sc not in seen:
            seen[sc] = u
    items = list(seen.items())
    n = len(items)
    print(f"total instagram posts: {n}", file=sys.stderr)

    cj = load_cookies_from_profile()
    session = requests.Session()
    session.cookies = cj  # type: ignore

    downloaded = skipped = failed = 0
    for i, (sc, url) in enumerate(items, 1):
        out = THUMB_DIR / f"{sc}.jpg"
        if out.exists() and out.stat().st_size > 0:
            skipped += 1
            print(f"[{i}/{n}] {sc} skip", file=sys.stderr)
            continue
        try:
            r = session.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
            if r.status_code != 200:
                failed += 1
                print(f"[{i}/{n}] {sc} http_{r.status_code}", file=sys.stderr)
                time.sleep(1.5)
                continue
            m = OG_RE.search(r.text)
            if not m:
                failed += 1
                print(f"[{i}/{n}] {sc} no_og", file=sys.stderr)
                time.sleep(1.5)
                continue
            img_url = html.unescape(m.group(1))
            ir = session.get(img_url, headers=HEADERS, timeout=30)
            if ir.status_code != 200 or not ir.content:
                failed += 1
                print(f"[{i}/{n}] {sc} img_http_{ir.status_code}", file=sys.stderr)
                time.sleep(1.5)
                continue
            out.write_bytes(ir.content)
            downloaded += 1
            print(f"[{i}/{n}] {sc} ok ({len(ir.content)}B)", file=sys.stderr)
        except requests.RequestException as e:
            failed += 1
            print(f"[{i}/{n}] {sc} err:{type(e).__name__}", file=sys.stderr)
        time.sleep(1.5)

    print(f"\ndone: downloaded={downloaded} skipped={skipped} failed={failed} total={n}", file=sys.stderr)


if __name__ == "__main__":
    main()
