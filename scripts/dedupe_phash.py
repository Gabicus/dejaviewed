#!/usr/bin/env python3
"""Perceptual-hash duplicate detection across catalog entries.

Read-only on data/entries.parquet. Writes:
  data/dedupe_report.json   all candidate groups (confirmed + possible + title)
  data/dedupe_patch.json    keeper/drop plan for CONFIRMED groups only (not applied)
  data/dedupe_phash_cache.json  hash cache keyed by file path + mtime + size

Rules:
  thumb pHash Hamming <= THUMB_MAX                      -> candidate
  video: >= 2 of 3 frames (10/50/90%) Hamming <= FRAME_MAX -> candidate
  Confirmed = video pair with frame-set match, or same post_id, or image-vs-image
              thumb match (thumb IS the content for single images).
  Possible  = thumb match without frame confirmation (missing video on one side,
              or frames differ = likely same cover, different reel), carousel thumb match.
  Title     = exact case-insensitive title match (weak; listed separately).
Low-information images (near-uniform, e.g. black frames) are not hashed-compared.
"""
import json, os, subprocess, sys, time, io
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from itertools import combinations

import pandas as pd
import imagehash
from PIL import Image, ImageStat

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PARQUET = os.path.join(ROOT, "data/entries.parquet")
THUMB_DIR = os.path.join(ROOT, "site/thumb")
MEDIA_DIR = os.path.join(ROOT, "data/media")
REPORT = os.path.join(ROOT, "data/dedupe_report.json")
PATCH = os.path.join(ROOT, "data/dedupe_patch.json")
CACHE = os.path.join(ROOT, "data/dedupe_phash_cache.json")

THUMB_MAX = 6
FRAME_MAX = 8
FRAME_NEED = 2
FRAME_POS = (0.10, 0.50, 0.90)
MIN_STDDEV = 8.0  # grayscale stddev below this = uniform image, hash unreliable
TIER_RANK = {"S": 0, "A": 1, "B": 2, "C": 3}


def load_cache():
    try:
        with open(CACHE) as f:
            return json.load(f)
    except Exception:
        return {}


def file_key(path):
    st = os.stat(path)
    return f"{path}|{int(st.st_mtime)}|{st.st_size}"


def hash_image(img):
    """Return (hex_hash, informative_bool)."""
    g = img.convert("L")
    std = ImageStat.Stat(g).stddev[0]
    return str(imagehash.phash(img)), std >= MIN_STDDEV


def thumb_hash(path, cache):
    k = file_key(path)
    if k in cache:
        return cache[k]
    try:
        with Image.open(path) as im:
            h, ok = hash_image(im)
        cache[k] = {"h": h, "ok": ok}
    except Exception as e:
        cache[k] = {"h": None, "ok": False, "err": str(e)[:100]}
    return cache[k]


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                        "-of", "csv=p=0", path], capture_output=True, text=True, timeout=30)
    return float(r.stdout.strip())


def grab_frame(path, t):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", path, "-frames:v", "1",
                        "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, timeout=60)
    if not r.stdout:
        raise RuntimeError("no frame")
    return Image.open(io.BytesIO(r.stdout))


def video_hashes(path):
    try:
        d = duration(path)
        out = []
        for p in FRAME_POS:
            img = grab_frame(path, d * p)
            h, ok = hash_image(img)
            out.append({"h": h, "ok": ok})
        return {"frames": out, "dur": round(d, 2)}
    except Exception as e:
        return {"frames": None, "err": str(e)[:100]}


def hd(a, b):
    return int(imagehash.hex_to_hash(a) - imagehash.hex_to_hash(b))


class UF:
    def __init__(self):
        self.p = {}

    def find(self, x):
        self.p.setdefault(x, x)
        while self.p[x] != x:
            self.p[x] = self.p[self.p[x]]
            x = self.p[x]
        return x

    def union(self, a, b):
        self.p[self.find(a)] = self.find(b)


def text_len(r):
    n = 0
    for c in ("title", "summary", "caption", "transcript"):
        v = r.get(c)
        if isinstance(v, str):
            n += len(v)
    tk = r.get("takeaways")
    if tk is not None and not isinstance(tk, str):
        try:
            n += sum(len(str(x)) for x in tk)
        except TypeError:
            pass
    return n


def as_list(v):
    if v is None:
        return []
    if isinstance(v, str):
        return [v]
    try:
        return [str(x) for x in v]
    except TypeError:
        return [str(v)]


def main():
    t0 = time.time()
    df = pd.read_parquet(PARQUET)
    rows = {r["id"]: r for r in df.to_dict("records")}
    cache = load_cache()

    # --- hashing ---
    thumbs, vids, missing_both = {}, {}, []
    vid_jobs = []
    for eid, r in rows.items():
        pid = r["post_id"]
        tp = os.path.join(THUMB_DIR, f"{pid}.jpg")
        if not os.path.exists(tp) and isinstance(r.get("thumb_path"), str):
            alt = os.path.join(ROOT, "site", r["thumb_path"])
            tp = alt if os.path.exists(alt) else tp
        vp = os.path.join(MEDIA_DIR, f"{pid}.mp4")
        has_t, has_v = os.path.exists(tp), os.path.exists(vp)
        if has_t:
            thumbs[eid] = thumb_hash(tp, cache)
        if has_v:
            k = "V|" + file_key(vp)
            if k in cache:
                vids[eid] = cache[k]
            else:
                vid_jobs.append((eid, k, vp))
        if not has_t and not has_v:
            missing_both.append(eid)

    with ThreadPoolExecutor(max_workers=8) as ex:
        for (eid, k, vp), res in zip(vid_jobs, ex.map(lambda j: video_hashes(j[2]), vid_jobs)):
            cache[k] = res
            vids[eid] = res
    with open(CACHE, "w") as f:
        json.dump(cache, f)
    t_hash = time.time() - t0

    # --- pairwise ---
    ids = list(rows)
    edges = []  # (a, b, kind, info)
    uninformative = [e for e, h in thumbs.items() if h.get("h") and not h["ok"]]
    for a, b in combinations(ids, 2):
        ra, rb = rows[a], rows[b]
        info = {}
        same_post = bool(ra["post_id"]) and ra["post_id"] == rb["post_id"]
        ta, tb = thumbs.get(a), thumbs.get(b)
        thumb_d = None
        if ta and tb and ta.get("h") and tb.get("h") and ta["ok"] and tb["ok"]:
            thumb_d = hd(ta["h"], tb["h"])
        va, vb = vids.get(a), vids.get(b)
        frame_d, frame_hits = None, None
        if va and vb and va.get("frames") and vb.get("frames"):
            frame_d, frame_hits = [], 0
            for fa, fb in zip(va["frames"], vb["frames"]):
                if fa["ok"] and fb["ok"]:
                    d = hd(fa["h"], fb["h"])
                    frame_d.append(d)
                    frame_hits += d <= FRAME_MAX
                else:
                    frame_d.append(None)
        thumb_hit = thumb_d is not None and thumb_d <= THUMB_MAX
        frame_hit = frame_hits is not None and frame_hits >= FRAME_NEED
        if not (same_post or thumb_hit or frame_hit):
            ttl_a = (ra.get("title") or "").strip().lower()
            if ttl_a and ttl_a == (rb.get("title") or "").strip().lower():
                edges.append((a, b, "title", {"reason": "exact_title", "thumb": thumb_d, "frames": frame_d}))
            continue
        info = {"thumb": thumb_d, "frames": frame_d}
        both_video = ra["media_type"] == "video" and rb["media_type"] == "video"
        both_image = ra["media_type"] == "image" and rb["media_type"] == "image"
        if same_post:
            edges.append((a, b, "confirmed", {**info, "reason": "same_post_id"}))
        elif frame_hit:
            edges.append((a, b, "confirmed", {**info, "reason": "frame_set_match"}))
        elif thumb_hit and both_image:
            edges.append((a, b, "confirmed", {**info, "reason": "image_thumb_match"}))
        elif thumb_hit and frame_d is not None:
            edges.append((a, b, "possible", {**info, "reason": "thumb_match_frames_differ"}))
        elif thumb_hit and both_video:
            edges.append((a, b, "possible", {**info, "reason": "thumb_match_no_video_to_confirm"}))
        else:
            edges.append((a, b, "possible", {**info, "reason": "thumb_match_mixed_media"}))

    # --- grouping ---
    def groups_for(kinds):
        uf = UF()
        es = [e for e in edges if e[2] in kinds]
        for a, b, *_ in es:
            uf.union(a, b)
        g = defaultdict(set)
        for a, b, *_ in es:
            g[uf.find(a)].update((a, b))
        out = []
        for members in g.values():
            m = sorted(members)
            pe = [{"a": a, "b": b, "kind": k, **i} for a, b, k, i in es if a in members]
            out.append((m, pe))
        return out

    def describe(members, pe, kind):
        return {
            "group": members, "kind": kind,
            "reason": sorted({p["reason"] for p in pe}),
            "distances": pe,
            "titles": [rows[m].get("title") for m in members],
            "creators": [rows[m].get("creator") for m in members],
            "collections": [as_list(rows[m].get("collections")) for m in members],
            "tiers": [rows[m].get("tier") for m in members],
            "media_types": [rows[m].get("media_type") for m in members],
        }

    confirmed = [describe(m, pe, "confirmed") for m, pe in groups_for({"confirmed"})]
    conf_sets = [set(g["group"]) for g in confirmed]
    possible = []
    for m, pe in groups_for({"possible"}):
        # drop possible groups fully contained in one confirmed group
        if any(set(m) <= s for s in conf_sets):
            continue
        possible.append(describe(m, pe, "possible"))
    titles = [describe(m, pe, "title") for m, pe in groups_for({"title"})]
    confirmed.sort(key=lambda g: (-len(g["group"]), g["titles"][0] or ""))
    possible.sort(key=lambda g: (-len(g["group"]), g["titles"][0] or ""))

    # --- patch (confirmed only) ---
    def keeper_key(eid):
        r = rows[eid]
        return (TIER_RANK.get(r.get("tier"), 9), -text_len(r), str(r.get("date") or "9999"))

    patch = []
    for g in confirmed:
        mem = sorted(g["group"], key=keeper_key)
        merged = []
        for m in mem:
            for c in as_list(rows[m].get("collections")) + as_list(rows[m].get("source_collection")):
                if c and c not in merged:
                    merged.append(c)
        patch.append({"keep_id": mem[0], "drop_ids": mem[1:], "merged_collections": merged,
                      "keep_tier": rows[mem[0]].get("tier"), "reason": g["reason"]})

    report = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "params": {"thumb_max": THUMB_MAX, "frame_max": FRAME_MAX, "frame_need": FRAME_NEED,
                   "frame_pos": FRAME_POS, "min_stddev": MIN_STDDEV},
        "counts": {"entries": len(rows), "thumbs_hashed": len(thumbs),
                   "videos_hashed": sum(1 for v in vids.values() if v.get("frames")),
                   "video_errors": sum(1 for v in vids.values() if not v.get("frames")),
                   "uninformative_thumbs": len(uninformative),
                   "missing_thumb_and_video": len(missing_both),
                   "confirmed_groups": len(confirmed),
                   "confirmed_drop_entries": sum(len(p["drop_ids"]) for p in patch),
                   "possible_groups": len(possible), "title_groups": len(titles)},
        "confirmed": confirmed, "possible": possible, "title_matches": titles,
        "missing_thumb_and_video": [{"id": e, "title": rows[e].get("title"), "url": rows[e].get("url")}
                                    for e in missing_both],
        "uninformative_thumbs": uninformative,
    }
    with open(REPORT, "w") as f:
        json.dump(report, f, indent=1, default=str)
    with open(PATCH, "w") as f:
        json.dump({"applied": False, "note": "Not applied. Review before merging.", "groups": patch},
                  f, indent=1, default=str)

    # --- summary ---
    c = report["counts"]
    print(f"entries={c['entries']} thumbs={c['thumbs_hashed']} videos={c['videos_hashed']} "
          f"video_err={c['video_errors']} uninformative_thumbs={c['uninformative_thumbs']}")
    print(f"CONFIRMED groups={c['confirmed_groups']} (drops={c['confirmed_drop_entries']})  "
          f"POSSIBLE groups={c['possible_groups']}  TITLE-only groups={c['title_groups']}")
    rc = defaultdict(int)
    for g in possible:
        for r in g["reason"]:
            rc[r] += 1
    print("possible by reason:", dict(rc))
    print("missing thumb AND video:", len(missing_both), missing_both[:20])
    print("\nTop confirmed groups:")
    for g in confirmed[:10]:
        print(f"  {g['group']} {g['reason']} tiers={g['tiers']} creators={g['creators']}")
        for t in g["titles"]:
            print(f"     - {t}")
    print(f"\nhash time {t_hash:.1f}s, total {time.time()-t0:.1f}s")


if __name__ == "__main__":
    sys.exit(main())
