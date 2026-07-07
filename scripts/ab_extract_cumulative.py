#!/usr/bin/env python3
"""Cumulative URL extraction from Instagram saved collections via agent-browser.
Collects URLs at each scroll position and merges, handling IG DOM unloading."""
import subprocess, json, sys, time

def ab(args):
    result = subprocess.run(["npx", "agent-browser"] + args, capture_output=True, text=True, timeout=15)
    return result.stdout.strip()

def extract_urls():
    js = '(() => { const s = new Set(); document.querySelectorAll("a[href*=\\"/p/\\"], a[href*=\\"/reel/\\"]").forEach(a => { const h = a.getAttribute("href"); if (h) s.add(h); }); return JSON.stringify([...s]); })()'
    raw = ab(["eval", js])
    try:
        urls = json.loads(json.loads(raw))
    except Exception:
        try:
            urls = json.loads(raw)
        except Exception:
            return []
    return urls

def main():
    collection = sys.argv[1]
    url = sys.argv[2]
    outfile = f"data/{collection}_urls.json"

    all_urls = set()
    stable = 0
    prev_count = 0

    for i in range(1, 50):
        batch = extract_urls()
        for u in batch:
            full = u if u.startswith("http") else f"https://www.instagram.com{u}"
            all_urls.add(full)

        print(f"[extract] scroll {i}: batch={len(batch)}, cumulative={len(all_urls)}")

        if len(all_urls) == prev_count:
            stable += 1
        else:
            stable = 0

        if stable >= 4:
            print(f"[extract] {collection}: stable at {len(all_urls)} URLs after 4 rounds")
            break

        prev_count = len(all_urls)
        ab(["scroll", "down", "800"])
        time.sleep(1.5)

    urls_list = sorted(all_urls)
    with open(outfile, "w") as f:
        json.dump(urls_list, f, indent=2)
    print(f"[extract] {collection}: saved {len(urls_list)} URLs to {outfile}")

if __name__ == "__main__":
    main()
