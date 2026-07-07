#!/usr/bin/env python3
"""Download thumbnails via agent-browser by extracting og:image from each post page."""
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from cms import load_entries, write_entries

THUMB_DIR = ROOT / "site" / "thumb"
THUMB_DIR.mkdir(parents=True, exist_ok=True)


def ab_cmd(args, timeout=15):
    result = subprocess.run(
        ["npx", "agent-browser"] + args,
        capture_output=True, text=True, timeout=timeout,
        cwd=str(ROOT)
    )
    return (result.stdout + result.stderr).strip()


def get_og_image():
    js = 'document.querySelector("meta[property=\\"og:image\\"]")?.getAttribute("content") || ""'
    raw = ab_cmd(["eval", js], timeout=10)
    url = raw.strip().strip('"')
    if url and url.startswith("http"):
        return url
    return None


def download_image(url, dest):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        dest.write_bytes(resp.read())
    return dest.stat().st_size


def main():
    entries = load_entries()
    existing = set(os.listdir(THUMB_DIR))

    need = [
        e for e in entries
        if e.get("post_id")
        and f'{e["post_id"]}.jpg' not in existing
        and e.get("url", "").startswith("https://www.instagram.com/")
    ]
    print(f"Need thumbnails for {len(need)} entries")

    ok = 0
    fail = 0
    for i, e in enumerate(need):
        pid = e["post_id"]
        url = e["url"]
        dest = THUMB_DIR / f"{pid}.jpg"
        print(f"[{i+1}/{len(need)}] {pid}", end=" ", flush=True)

        try:
            ab_cmd(["open", url], timeout=20)
            time.sleep(1.5)
            img_url = get_og_image()
            if img_url:
                size = download_image(img_url, dest)
                e["thumb_path"] = f"thumb/{pid}.jpg"
                e["media_url"] = img_url
                ok += 1
                print(f"✓ {size//1024}KB")
            else:
                print("✗ no og:image")
                fail += 1
        except Exception as ex:
            print(f"✗ {ex}")
            fail += 1

        if (i + 1) % 20 == 0:
            write_entries(entries)
            print(f"  [checkpoint] saved {ok} thumbs so far")

        time.sleep(0.5)

    write_entries(entries)
    print(f"\nDone: {ok} downloaded, {fail} failed out of {len(need)}")


if __name__ == "__main__":
    main()
