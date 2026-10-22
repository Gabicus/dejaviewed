#!/usr/bin/env python3
"""Submit dejaviewed.dev sitemap URLs to IndexNow (Bing, Yandex, Seznam, Naver...).

The IndexNow key is public by design (it is served at https://dejaviewed.dev/<key>.txt),
so it is committed: data/seo/indexnow.key + site/<key>.txt.

Usage:
  python3 scripts/indexnow.py --init-key          # generate key files once (no network)
  python3 scripts/indexnow.py --dry-run           # show what would be submitted (no network)
  python3 scripts/indexnow.py                     # submit all sitemap URLs (after deploy)
  python3 scripts/indexnow.py --changed-since 2026-10-20
  python3 scripts/indexnow.py --skip-verify       # don't check the live key file first

--changed-since uses <lastmod> from site/sitemap.xml; URLs without lastmod are
included (we can't prove they're unchanged).
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import secrets
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEY_FILE = ROOT / "data" / "seo" / "indexnow.key"
SITE = ROOT / "site"
SITEMAP = SITE / "sitemap.xml"
HOST = "dejaviewed.dev"
ENDPOINT = "https://api.indexnow.org/indexnow"
BATCH = 10_000


def read_key() -> str | None:
    if KEY_FILE.exists():
        k = KEY_FILE.read_text().strip()
        if re.fullmatch(r"[A-Za-z0-9-]{8,128}", k):
            return k
    return None


def init_key() -> str:
    k = read_key()
    if not k:
        k = secrets.token_hex(16)
        KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
        KEY_FILE.write_text(k + "\n")
        print(f"generated new key -> {KEY_FILE.relative_to(ROOT)}")
    kf = SITE / f"{k}.txt"
    if not kf.exists() or kf.read_text().strip() != k:
        kf.write_text(k)
        print(f"wrote {kf.relative_to(ROOT)} (deploy it, then submit)")
    return k


def sitemap_urls(since: dt.date | None) -> list[str]:
    xml = SITEMAP.read_text()
    out = []
    for block in re.findall(r"<url>(.*?)</url>", xml, re.S):
        loc = re.search(r"<loc>\s*([^<\s]+)\s*</loc>", block)
        if not loc:
            continue
        url = loc.group(1)
        if not url.startswith(f"https://{HOST}/"):
            continue
        if since:
            lm = re.search(r"<lastmod>\s*([0-9]{4}-[0-9]{2}-[0-9]{2})", block)
            if lm and dt.date.fromisoformat(lm.group(1)) < since:
                continue
        out.append(url)
    return list(dict.fromkeys(out))


def key_live(key: str) -> bool:
    try:
        with urllib.request.urlopen(f"https://{HOST}/{key}.txt", timeout=20) as r:
            return r.read().decode().strip() == key
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--init-key", action="store_true", help="create key files and exit (no network)")
    ap.add_argument("--dry-run", action="store_true", help="no network, no file writes")
    ap.add_argument("--changed-since", type=dt.date.fromisoformat, metavar="YYYY-MM-DD")
    ap.add_argument("--skip-verify", action="store_true", help="skip checking the live key file")
    args = ap.parse_args()

    if args.init_key:
        init_key()
        return 0
    key = read_key()
    if not SITEMAP.exists():
        print(f"missing: {SITEMAP.relative_to(ROOT)} -- do: run scripts/rebuild.sh")
        return 1
    urls = sitemap_urls(args.changed_since)
    has_lastmod = "<lastmod>" in SITEMAP.read_text()
    if args.changed_since and not has_lastmod:
        print("note: sitemap has no <lastmod>; --changed-since cannot filter, submitting all URLs")
    batches = [urls[i:i + BATCH] for i in range(0, len(urls), BATCH)]

    if args.dry_run:
        print(f"[dry-run] key: {'present (' + KEY_FILE.relative_to(ROOT).as_posix() + ')' if key else 'MISSING -- run --init-key'}")
        if key:
            print(f"[dry-run] keyLocation: https://{HOST}/{key}.txt  (local copy {'ok' if (SITE / f'{key}.txt').exists() else 'MISSING'})")
        print(f"[dry-run] {len(urls)} URLs in {len(batches)} batch(es) -> POST {ENDPOINT}")
        for u in urls[:5]:
            print(f"  {u}")
        if len(urls) > 5:
            print(f"  ... {len(urls) - 5} more")
        return 0

    if not key:
        print("missing: IndexNow key -- do: python3 scripts/indexnow.py --init-key, commit, deploy, then re-run")
        return 0
    if not args.skip_verify and not key_live(key):
        print(f"missing: live key file https://{HOST}/{key}.txt -- do: deploy site/ (the key file must be served "
              f"before submitting), then re-run")
        return 0
    ok = True
    for i, b in enumerate(batches, 1):
        body = json.dumps({"host": HOST, "key": key, "keyLocation": f"https://{HOST}/{key}.txt",
                           "urlList": b}).encode()
        req = urllib.request.Request(ENDPOINT, data=body, method="POST",
                                     headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                print(f"batch {i}/{len(batches)}: {len(b)} URLs -> HTTP {r.status}")
        except urllib.error.HTTPError as e:
            # 202 = accepted pending key check; 400 bad request; 403 key invalid; 422 URLs not for host; 429 too many
            print(f"batch {i}/{len(batches)}: HTTP {e.code} {e.reason}")
            ok = False
        except urllib.error.URLError as e:
            print(f"batch {i}/{len(batches)}: network error {e.reason}")
            ok = False
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
