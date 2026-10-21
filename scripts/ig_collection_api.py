#!/usr/bin/env python3
"""Fetch a saved collection via Instagram's internal collection-feed API.

Runs fetch() inside the logged-in page through agent-browser eval, so cookies
and CSRF are handled by the browser. Paginates with next_max_id. Writes the
compact per-item JSON (code, caption, creator, taken_at, media_type, thumb_url,
video_url, ...) to data/<name>_api.json.

Usage:
    python3 scripts/ig_collection_api.py <name> <collection_id> [<name> <id> ...]

Prereq: agent-browser connected to a browser with an active Instagram session
and currently on an instagram.com page (same-origin fetch).
"""
import json
import subprocess
import sys
import time

JS = r"""
(async () => {
  const r = await fetch("/api/v1/feed/collection/%(cid)s/posts/%(q)s", {headers: {
    "x-ig-app-id": "936619743392459",
    "x-csrftoken": (document.cookie.match(/csrftoken=([^;]+)/) || [])[1] || "",
    "x-requested-with": "XMLHttpRequest"}});
  const j = await r.json();
  const pick = (it) => {
    const m = it.media || it;
    const img = ((m.image_versions2 || {}).candidates || [])[0] || {};
    const vid = (m.video_versions || [])[0] || {};
    const car = (m.carousel_media || []).map(c => ({
      img: (((c.image_versions2 || {}).candidates || [])[0] || {}).url || null,
      vid: ((c.video_versions || [])[0] || {}).url || null}));
    return {
      code: m.code, pk: String(m.pk || ""), taken_at: m.taken_at,
      media_type: m.media_type, product_type: m.product_type,
      creator: (m.user || {}).username || null,
      creator_full: (m.user || {}).full_name || null,
      caption: ((m.caption || {}).text) || "",
      like_count: m.like_count, comment_count: m.comment_count,
      play_count: m.play_count || m.ig_play_count || null,
      video_duration: m.video_duration || null,
      thumb_url: img.url || null, video_url: vid.url || null,
      carousel: car, location: (m.location || {}).name || null,
      accessibility_caption: m.accessibility_caption || null,
    };
  };
  return JSON.stringify({status: j.status, more: j.more_available,
    next: j.next_max_id || null, items: (j.items || []).map(pick)});
})()
"""


def ab_eval(js: str, timeout: int = 60) -> str:
    r = subprocess.run(["npx", "agent-browser", "eval", js],
                       capture_output=True, text=True, timeout=timeout)
    out = r.stdout.strip().splitlines()
    raw = out[-1] if out else ""
    try:
        raw = json.loads(raw)  # agent-browser wraps result as JSON string
    except Exception:
        pass
    return raw


def fetch_collection(name: str, cid: str) -> list:
    items, max_id, page = [], None, 0
    while True:
        page += 1
        q = f"?max_id={max_id}" if max_id else ""
        raw = ab_eval(JS % {"cid": cid, "q": q})
        try:
            j = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            print(f"[api] {name} page {page}: bad response: {str(raw)[:200]}")
            break
        if j.get("status") != "ok":
            print(f"[api] {name} page {page}: status={j.get('status')} {str(j)[:200]}")
            break
        items.extend(j["items"])
        print(f"[api] {name} page {page}: +{len(j['items'])} = {len(items)}")
        if not j.get("more") or not j.get("next"):
            break
        max_id = j["next"]
        time.sleep(1.2)
    # dedupe by code, keep first
    seen, out = set(), []
    for it in items:
        if it["code"] and it["code"] not in seen:
            seen.add(it["code"])
            out.append(it)
    path = f"data/{name}_api.json"
    with open(path, "w") as f:
        json.dump({"collection": name, "collection_id": cid,
                   "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                   "items": out}, f, indent=1)
    print(f"[api] {name}: {len(out)} unique posts -> {path}")
    return out


def main():
    args = sys.argv[1:]
    if len(args) < 2 or len(args) % 2:
        print(__doc__)
        sys.exit(1)
    for name, cid in zip(args[::2], args[1::2]):
        fetch_collection(name, cid)


if __name__ == "__main__":
    main()
