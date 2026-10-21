#!/usr/bin/env python3
"""Re-fetch caption + creator + date for catalog entries straight from each post page, verified.

Why: the July-2026 caption scrape read the page before navigation finished, so some entries carry the
PREVIOUS post's caption/creator ("Edited" creators, cross-wired captions). This script:
  1. opens /p/<code>/ via agent-browser (attached to a logged-in Chrome over CDP),
  2. waits until the page's `instagram://media?id=<pk>` equals the shortcode-decoded pk (proves the
     page is for THIS post),
  3. tries /api/v1/media/<pk>/info/ (caption, creator, taken_at, media_type); if that 404s, parses
     `get text main` with ab_scrape_posts.parse_post_text as a fallback,
  4. writes data/caption_refresh.json  {code: {creator, caption, taken_at, media_type, source}}.
Resume-safe; never writes parquet. Apply with:  python3 scripts/ig_refresh_captions.py --apply

    python3 scripts/ig_refresh_captions.py [--collections ai7 quant] [--codes-file f] [--limit N]
"""
import argparse, json, re, subprocess, sys, time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from ab_scrape_posts import parse_post_text  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "caption_refresh.json"
A = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"


def pk(code):
    n = 0
    for ch in code:
        n = n * 64 + A.index(ch)
    return n


def ab(*args, timeout=45):
    r = subprocess.run(["npx", "agent-browser", *args], capture_output=True, text=True, timeout=timeout)
    out = r.stdout.strip().splitlines()
    return out[-1] if out else ""


def ab_eval(js, timeout=45):
    raw = ab("eval", js, timeout=timeout)
    try:
        j = json.loads(raw)
        return json.loads(j) if isinstance(j, str) else j
    except Exception:
        return None


JS_ONE = '''(async()=>{const want="%s";const t0=Date.now();let pk=null;
 while(Date.now()-t0<12000){const m=document.documentElement.outerHTML.match(/instagram:\\/\\/media\\?id=(\\d+)/);pk=m&&m[1];if(pk===want)break;await new Promise(r=>setTimeout(r,400));}
 if(pk!==want)return JSON.stringify({err:"pk-mismatch",pk:pk,t:document.title});
 try{const r=await fetch("/api/v1/media/"+want+"/info/",{headers:{"x-ig-app-id":"936619743392459","x-requested-with":"XMLHttpRequest"}});
  if(r.status===200){const j=await r.json();const m=(j.items||[])[0]||{};if(m.code)return JSON.stringify({src:"api",code:m.code,creator:(m.user||{}).username||null,caption:((m.caption||{}).text)||"",taken_at:m.taken_at,media_type:m.media_type});}
 }catch(e){}
 const main=document.querySelector("main");return JSON.stringify({src:"text",text:main?main.innerText.slice(0,6000):""});})()'''
MT = {"1": "image", "2": "video", "8": "carousel"}


def fetch_one(code):
    want = str(pk(code))
    for attempt in range(2):
        ab("open", f"https://www.instagram.com/p/{code}/", timeout=60)
        j = ab_eval(JS_ONE % want, timeout=60) or {"err": "noresp"}
        if j.get("src") == "api" and j.get("code") == code:
            return {"creator": j.get("creator"), "caption": j.get("caption") or "",
                    "taken_at": j.get("taken_at"), "media_type": MT.get(str(j.get("media_type")), ""),
                    "source": "api"}
        if j.get("src") == "text":
            text = j.get("text") or ""
            if "isn't available" in text.lower()[:300]:
                return {"err": "unavailable"}
            d = parse_post_text(text)
            if d.get("caption") or d.get("creator"):
                return {"creator": (d.get("creator") or "").lstrip("@") or None, "caption": d.get("caption") or "",
                        "taken_at": None, "media_type": "", "source": "page-text"}
        if j.get("err") == "pk-mismatch" and "available" in (j.get("t") or "").lower():
            return {"err": "unavailable"}
        ab("open", "about:blank"); time.sleep(1)
    return {"err": j.get("err") or "no-data"}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--collections", nargs="*")
    p.add_argument("--codes-file")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--apply", action="store_true", help="apply caption_refresh.json to parquet and exit")
    a = p.parse_args()
    from cms import load_entries, write_entries
    rows = load_entries()
    if a.apply:
        res = json.load(open(OUT))
        by = {r["post_id"]: r for r in rows}
        changed = []
        for code, j in res.items():
            r = by.get(code)
            if not r or j.get("err"):
                continue
            diff = {}
            cap = (j.get("caption") or "").strip()
            if cap and cap[:60].lower() != (r.get("caption") or "").strip()[:60].lower():
                diff["caption"] = (r.get("caption") or "")[:50]; r["caption"] = cap
            cr = j.get("creator")
            if cr and (r.get("creator") or "").lstrip("@") != cr:
                diff["creator"] = r.get("creator"); r["creator"] = cr
            if j.get("media_type") and j["media_type"] != r.get("media_type") and not (r.get("media_type") == "carousel"):
                diff["media_type"] = r.get("media_type"); r["media_type"] = j["media_type"]
            if diff:
                changed.append({"id": r["id"], "post_id": code, "diff": diff})
        write_entries(rows)
        json.dump(changed, open(ROOT / "data" / "caption_refresh_changed.json", "w"), indent=1, ensure_ascii=False)
        print(f"[apply] changed {len(changed)} entries -> data/caption_refresh_changed.json")
        return
    res = json.load(open(OUT)) if OUT.exists() else {}
    targets = [r for r in rows if "instagram.com/p/" in (r.get("url") or "")]
    if a.collections:
        targets = [r for r in targets if r.get("source_collection") in a.collections]
    if a.codes_file:
        want = set(open(a.codes_file).read().split()); targets = [r for r in targets if r["post_id"] in want]
    codes = [r["post_id"] for r in targets if r["post_id"] not in res or res[r["post_id"]].get("err") in ("noresp", "no-data")]
    if a.limit:
        codes = codes[: a.limit]
    print(f"[refresh] {len(codes)} to fetch ({len(res)} cached)", flush=True)
    for i, code in enumerate(codes, 1):
        try:
            res[code] = fetch_one(code)
        except Exception as e:  # noqa: BLE001
            res[code] = {"err": f"exc:{type(e).__name__}"}
        print(f"[refresh] {i}/{len(codes)} {code} {res[code].get('source') or res[code].get('err')}", flush=True)
        if i % 10 == 0:
            json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)
        time.sleep(1.0)
    json.dump(res, open(OUT, "w"), indent=1, ensure_ascii=False)
    ok = sum(1 for v in res.values() if not v.get("err"))
    print(f"[refresh] done: {ok} ok / {len(res)} total", flush=True)


if __name__ == "__main__":
    main()
