#!/usr/bin/env python3
"""Download thumbnails for catalog entries that have media_url."""
import json, os, sys, urllib.request, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "site" / "catalog.json"
THUMB_DIR = ROOT / "site" / "thumb"

def main():
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    entries = data["entries"]
    existing = set(os.listdir(THUMB_DIR))

    need = [e for e in entries if e.get("media_url") and f'{e["post_id"]}.jpg' not in existing]
    print(f"Downloading {len(need)} thumbnails...")

    ok = 0
    fail = 0
    for i, e in enumerate(need):
        dest = THUMB_DIR / f'{e["post_id"]}.jpg'
        try:
            req = urllib.request.Request(e["media_url"], headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=15) as resp:
                dest.write_bytes(resp.read())
            ok += 1
        except Exception as ex:
            print(f"  FAIL {e['post_id']}: {ex}", file=sys.stderr)
            fail += 1
        if (i + 1) % 20 == 0:
            print(f"  Progress: {i+1}/{len(need)} (ok={ok}, fail={fail})")
            time.sleep(1)

    print(f"Done: {ok} downloaded, {fail} failed")

if __name__ == "__main__":
    main()
