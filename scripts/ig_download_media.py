#!/usr/bin/env python3
"""Download thumbnails, videos and carousel slides for items in an ig_collection_api.py dump.

    python3 scripts/ig_download_media.py data/ai8_api.json [data/creative_api.json ...]

Signed CDN URLs expire within hours — run this immediately after the pull.
Thumbs -> site/thumb/<code>.jpg ; videos -> data/media/<code>.mp4 ;
carousel slides -> data/media/<code>_slide<N>.jpg|mp4 (data/media is gitignored).
Resume-safe: existing files are skipped.
"""
import concurrent.futures as cf
import json
import os
import sys
from collections import Counter
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
H = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/149.0 Safari/537.36",
     "Referer": "https://www.instagram.com/"}


def get(url, path):
    if not url or os.path.exists(path):
        return "skip"
    try:
        r = requests.get(url, headers=H, timeout=120, stream=True)
        if r.status_code != 200:
            return f"http{r.status_code}"
        with open(str(path) + ".part", "wb") as f:
            for ch in r.iter_content(1 << 16):
                f.write(ch)
        os.rename(str(path) + ".part", path)
        return "ok"
    except Exception as e:
        return f"err:{type(e).__name__}"


def main():
    (ROOT / "site" / "thumb").mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "media").mkdir(parents=True, exist_ok=True)
    jobs = []
    for p in sys.argv[1:]:
        d = json.load(open(p))
        items = d["items"] if isinstance(d, dict) else d
        for i in items:
            c = i["code"]
            jobs.append((i.get("thumb_url"), ROOT / "site" / "thumb" / f"{c}.jpg"))
            jobs.append((i.get("video_url"), ROOT / "data" / "media" / f"{c}.mp4"))
            for k, s in enumerate(i.get("carousel") or []):
                jobs.append((s.get("img"), ROOT / "data" / "media" / f"{c}_slide{k}.jpg"))
                jobs.append((s.get("vid"), ROOT / "data" / "media" / f"{c}_slide{k}.mp4"))
    jobs = [j for j in jobs if j[0]]
    res = Counter()
    with cf.ThreadPoolExecutor(6) as ex:
        for (u, path), r in zip(jobs, ex.map(lambda j: get(*j), jobs)):
            res[(path.suffix, r)] += 1
            if r not in ("ok", "skip"):
                print("FAIL", path.name, r)
    print(dict(res))


if __name__ == "__main__":
    main()
