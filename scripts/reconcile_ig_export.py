#!/usr/bin/env python3
"""reconcile_ig_export.py — compare Instagram's "Download your information" export with entries.parquet.

Usage:
    python3 scripts/reconcile_ig_export.py <export-dir | export.zip | saved_*.json> [options]
    python3 scripts/reconcile_ig_export.py --demo [DIR]     # fabricate a tiny export and run on it

Reads (JSON format export) your_instagram_activity/saved/saved_collections.json and
saved_posts.json. Read-only against the parquet. Prints, per collection:
export count vs parquet count, URLs in the export missing from the parquet, URLs in
the parquet not in the export (likely unsaved or deleted), plus total agreement %.
Writes the missing URLs (one per line, canonical /p/<code>/ form) to
data/reconcile_missing.txt (or --out) so they can be fed to ingest.

Shapes handled (Instagram has changed these several times):
  * flat collections list: a header item {"string_map_data": {"Name": {"value": "ai1"},
    "Creation Time": ...}} followed by its posts {"string_map_data": {"Name": {"href": ...},
    "Added Time": {"timestamp": ...}}}
  * grouped collections: [{"title"/"name": "ai1", "items"|"media"|...: [posts]}] or {"ai1": [posts]}
  * label_values items: {"label_values": [{"label": "Collection name", "value": ...},
    {"label": "URL", "href": ...}], "timestamp": ...}
  * saved_posts: {"saved_saved_media": [{"title": user, "string_map_data": {"Saved on": {"href", "timestamp"}}}]}
Any string anywhere in an item that looks like instagram.com/(p|reel|reels|tv)/<code> counts as the
post URL. Matching is by shortcode. Unknown shapes print the keys found instead of guessing silently.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tempfile
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = ROOT / "data" / "reconcile_missing.txt"
UNCOLLECTED = "(saved, no collection)"
IG_POST_RE = re.compile(r"instagram\.com/(?:[A-Za-z0-9_.]+/)?(?:p|reel|reels|tv)/([A-Za-z0-9_-]+)")
CHILD_LIST_KEYS = ("items", "media", "posts", "saved_media", "saved_items", "children", "entries")
NAME_LABELS = {"name", "collection name", "collection", "title"}


def fix_mojibake(s: str) -> str:
    """IG exports double-encode UTF-8 as latin-1 escapes ('Ã©'). Undo when it round-trips."""
    try:
        return s.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return s


def norm_coll(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", fix_mojibake(name).lower())


def canon_url(code: str) -> str:
    return f"https://www.instagram.com/p/{code}/"


def strings_in(obj):
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from strings_in(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from strings_in(v)


def codes_in(obj) -> list[str]:
    seen, out = set(), []
    for s in strings_in(obj):
        for m in IG_POST_RE.finditer(s):
            if m.group(1) not in seen:
                seen.add(m.group(1))
                out.append(m.group(1))
    return out


def timestamps_in(obj) -> list[int]:
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "timestamp" and isinstance(v, (int, float)) and v > 0:
                out.append(int(v))
            elif isinstance(v, str) and k.lower() in ("timestamp", "saved on", "added time"):
                try:
                    out.append(int(datetime.fromisoformat(v.replace("Z", "+00:00")).timestamp()))
                except ValueError:
                    pass
            else:
                out.extend(timestamps_in(v))
    elif isinstance(obj, list):
        for v in obj:
            out.extend(timestamps_in(v))
    return out


def header_name(item) -> str | None:
    """Name of a collection-header item (an item that carries a name but no post URL)."""
    if not isinstance(item, dict) or codes_in(item):
        return None
    smd = item.get("string_map_data")
    if isinstance(smd, dict):
        for k in ("Name", "Collection name", "Collection Name"):
            v = smd.get(k)
            if isinstance(v, dict) and isinstance(v.get("value"), str) and v["value"].strip():
                return fix_mojibake(v["value"].strip())
    lv = item.get("label_values")
    if isinstance(lv, list):
        for d in lv:
            if isinstance(d, dict) and str(d.get("label", "")).lower() in NAME_LABELS and isinstance(d.get("value"), str):
                return fix_mojibake(d["value"].strip())
    for k in ("title", "name"):
        if isinstance(item.get(k), str) and item[k].strip() and ("Creation Time" in (smd or {}) or not smd):
            return fix_mojibake(item[k].strip())
    return None


def item_collection_label(item) -> str | None:
    """Collection name carried on the post item itself (label_values shape)."""
    lv = item.get("label_values") if isinstance(item, dict) else None
    if isinstance(lv, list):
        for d in lv:
            if isinstance(d, dict) and str(d.get("label", "")).lower() in ("collection name", "collection") and isinstance(d.get("value"), str):
                return fix_mojibake(d["value"].strip())
    return None


def top_list(data):
    """Return (list, key) for the main list in a saved_*.json document."""
    if isinstance(data, list):
        return data, None
    if isinstance(data, dict):
        lists = [(k, v) for k, v in data.items() if isinstance(v, list)]
        if len(lists) == 1:
            return lists[0][1], lists[0][0]
        for k, v in lists:
            if "saved" in k or "collection" in k:
                return v, k
    return None, None


def parse_collections(data, label: str, notes: list[str]) -> dict[str, dict[str, int]]:
    """-> {collection_name: {code: first_ts}}"""
    out: dict[str, dict[str, int]] = defaultdict(dict)

    def add(coll, item):
        ts = min(timestamps_in(item), default=0)
        for c in codes_in(item):
            out[coll].setdefault(c, ts)

    # dict-of-collections: {"ai1": [...], "music": [...]}
    if isinstance(data, dict) and data and all(isinstance(v, list) for v in data.values()) \
            and not any("saved" in k for k in data):
        for name, items in data.items():
            for it in items:
                add(fix_mojibake(name), it)
        notes.append(f"{label}: grouped dict shape, {len(data)} collections")
        return out

    items, key = top_list(data)
    if items is None:
        keys = list(data.keys()) if isinstance(data, dict) else type(data).__name__
        notes.append(f"{label}: UNKNOWN SHAPE, top-level keys: {keys}")
        return out

    grouped = [it for it in items if isinstance(it, dict) and any(isinstance(it.get(k), list) for k in CHILD_LIST_KEYS)]
    if grouped and len(grouped) >= len(items) / 2:
        for it in items:
            if not isinstance(it, dict):
                continue
            name = next((it[k] for k in ("title", "name", "collection_name", "collection") if isinstance(it.get(k), str)), None) \
                or header_name({k: v for k, v in it.items() if k not in CHILD_LIST_KEYS}) or "(unnamed)"
            for k in CHILD_LIST_KEYS:
                if isinstance(it.get(k), list):
                    for child in it[k]:
                        add(fix_mojibake(name), child)
        notes.append(f"{label}: grouped list shape under {key!r}, {len(grouped)} collections")
        return out

    current, n_headers, orphan = None, 0, 0
    for it in items:
        own = item_collection_label(it)
        h = header_name(it)
        if h is not None:
            current, n_headers = h, n_headers + 1
            out.setdefault(current, {})
            continue
        coll = own or current
        if coll is None:
            orphan += 1
            coll = UNCOLLECTED
        add(coll, it)
    notes.append(f"{label}: flat shape under {key!r}, {len(items)} items, {n_headers} collection headers"
                 + (f", {orphan} items before any header" if orphan else ""))
    if not out:
        sample = items[0] if items else {}
        notes.append(f"{label}: no post URLs found; first item keys: {list(sample.keys()) if isinstance(sample, dict) else type(sample).__name__}")
    return out


def parse_saved_posts(data, label: str, notes: list[str]) -> dict[str, int]:
    items, key = top_list(data)
    if items is None:
        keys = list(data.keys()) if isinstance(data, dict) else type(data).__name__
        notes.append(f"{label}: UNKNOWN SHAPE, top-level keys: {keys}")
        return {}
    out = {}
    for it in items:
        ts = min(timestamps_in(it), default=0)
        for c in codes_in(it):
            out.setdefault(c, ts)
    notes.append(f"{label}: {len(items)} items under {key!r}, {len(out)} post URLs")
    if items and not out:
        notes.append(f"{label}: no post URLs found; first item keys: {list(items[0].keys()) if isinstance(items[0], dict) else type(items[0]).__name__}")
    return out


def read_export(path: Path) -> list[tuple[str, object]]:
    """-> [(name, parsed_json)] for every saved-related JSON file."""
    docs = []

    def wanted(name: str) -> bool:
        n = name.lower().replace("\\", "/")
        return n.endswith(".json") and ("saved_collections" in n or "saved_posts" in n or "/saved/" in n)

    if path.is_file() and zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as z:
            for info in z.infolist():
                if not info.is_dir() and wanted("/" + info.filename) and info.file_size < 200_000_000:
                    docs.append((info.filename, json.loads(z.read(info).decode("utf-8"))))
    elif path.is_file():
        docs.append((path.name, json.loads(path.read_text(encoding="utf-8"))))
    elif path.is_dir():
        for p in sorted(path.rglob("*.json")):
            if wanted("/" + str(p.relative_to(path))):
                docs.append((str(p.relative_to(path)), json.loads(p.read_text(encoding="utf-8"))))
    else:
        sys.exit(f"[reconcile] not found: {path}")
    return docs


def load_parquet_side(parquet: Path | None):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import cms  # noqa: E402
    if parquet:
        cms.ENTRIES_PARQUET = parquet
    rows = cms.load_entries()
    by_code: dict[str, dict] = {}
    non_ig = 0
    for r in rows:
        m = IG_POST_RE.search(r.get("url") or "")
        code = m.group(1) if m else None
        if not code:
            non_ig += 1
            continue
        colls = list(dict.fromkeys(list(r.get("collections") or []) + ([r["source_collection"]] if r.get("source_collection") else [])))
        by_code[code] = {"id": r.get("id"), "collections": colls, "title": r.get("title") or ""}
    return by_code, non_ig, cms.ENTRIES_PARQUET


def fmt_ts(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d") if ts else "?"


def reconcile(export_path: Path, out_path: Path, parquet: Path | None, mapping: dict[str, str],
              include_uncollected: bool, show: int) -> int:
    docs = read_export(export_path)
    notes: list[str] = []
    if not docs:
        print(f"[reconcile] no saved_*.json files found in {export_path}. Expected your_instagram_activity/saved/ in a JSON-format export.")
        return 2

    export_colls: dict[str, dict[str, int]] = defaultdict(dict)
    all_saved: dict[str, int] = {}
    for name, data in docs:
        base = name.lower()
        if "saved_posts" in base:
            all_saved.update(parse_saved_posts(data, name, notes))
        else:
            for coll, codes in parse_collections(data, name, notes).items():
                export_colls[coll].update(codes)

    by_code, non_ig, pq_path = load_parquet_side(parquet)
    print(f"export: {export_path}")
    for n in notes:
        print(f"  · {n}")
    print(f"parquet: {pq_path}  ({len(by_code)} Instagram entries, {non_ig} non-Instagram skipped)\n")

    # map export collection names → parquet collection slugs
    pq_colls: dict[str, set[str]] = defaultdict(set)
    for code, info in by_code.items():
        for c in info["collections"]:
            pq_colls[c].add(code)
    slug_by_norm = {norm_coll(s): s for s in pq_colls}
    ex_by_slug: dict[str, dict[str, int]] = defaultdict(dict)
    unmatched_names = []
    for name, codes in export_colls.items():
        slug = mapping.get(name) or mapping.get(norm_coll(name)) or slug_by_norm.get(norm_coll(name))
        if name == UNCOLLECTED:
            slug = UNCOLLECTED
        elif slug is None:
            slug = name
            unmatched_names.append(name)
        ex_by_slug[slug].update(codes)

    collected = set().union(*[set(c) for s, c in ex_by_slug.items() if s != UNCOLLECTED]) if ex_by_slug else set()
    uncollected = (set(all_saved) | set(ex_by_slug.get(UNCOLLECTED, {}))) - collected
    if not export_colls and all_saved:
        include_uncollected = True  # only saved_posts.json present: the whole list is the export
    export_set = collected | (uncollected if include_uncollected else set())
    pq_set = set(by_code)

    # per-collection table
    print(f"{'collection':<26}{'export':>8}{'parquet':>9}{'both':>7}{'exp-only':>10}{'pq-only':>9}")
    slugs = sorted(set(ex_by_slug) | set(pq_colls), key=lambda s: (s == UNCOLLECTED, s))
    detail = []
    for s in slugs:
        if s == UNCOLLECTED:
            continue
        ex = set(ex_by_slug.get(s, {}))
        pq = pq_colls.get(s, set())
        both = ex & pq
        exp_only = ex - pq
        pq_only = pq - ex
        tag = "" if s in pq_colls and s in ex_by_slug else ("  [not in export]" if s not in ex_by_slug else "  [not in parquet]")
        print(f"{s[:25]:<26}{len(ex):>8}{len(pq):>9}{len(both):>7}{len(exp_only):>10}{len(pq_only):>9}{tag}")
        detail.append((s, ex, exp_only, pq_only))
    if uncollected:
        print(f"{UNCOLLECTED:<26}{len(uncollected):>8}{'':>9}{'':>7}{'':>10}{'':>9}"
              f"  [{'counted' if include_uncollected else 'excluded; --include-uncollected to count'}]")

    # detail per collection
    for s, ex, exp_only, pq_only in detail:
        if not exp_only and not pq_only:
            continue
        if s not in ex_by_slug:
            continue  # whole collection absent from export: the table row says so; no URL dump
        print(f"\n── {s}")
        if exp_only:
            elsewhere = [c for c in exp_only if c in by_code]
            truly = [c for c in exp_only if c not in by_code]
            print(f"   in export, missing from parquet: {len(truly)}")
            for c in sorted(truly, key=lambda c: -ex_by_slug[s].get(c, 0))[:show]:
                print(f"     {canon_url(c)}  saved {fmt_ts(ex_by_slug[s].get(c, 0))}")
            if len(truly) > show:
                print(f"     … {len(truly) - show} more (all in the missing file)")
            if elsewhere:
                print(f"   in export, in parquet under another collection: {len(elsewhere)}")
                for c in elsewhere[:show]:
                    print(f"     {canon_url(c)}  parquet: {', '.join(by_code[c]['collections']) or '—'}")
        if pq_only:
            print(f"   in parquet, not in this export collection (unsaved/moved/deleted?): {len(pq_only)}")
            for c in sorted(pq_only)[:show]:
                print(f"     {canon_url(c)}  {by_code[c]['title'][:60]}")
            if len(pq_only) > show:
                print(f"     … {len(pq_only) - show} more")

    if unmatched_names:
        print(f"\nexport collections with no parquet match (use --map 'IG Name=slug'): {', '.join(sorted(unmatched_names))}")

    missing = export_set - pq_set
    extra = pq_set - export_set
    union = export_set | pq_set
    agree = 100 * len(export_set & pq_set) / len(union) if union else 100.0
    print("\n── totals")
    print(f"   export posts (unique): {len(export_set)}   parquet IG entries: {len(pq_set)}   in both: {len(export_set & pq_set)}")
    print(f"   export-only (missing from parquet): {len(missing)}   parquet-only (not in export): {len(extra)}")
    print(f"   agreement (|both| / |union|): {agree:.1f}%")

    ts_by_code = {}
    for d in list(ex_by_slug.values()) + [all_saved]:
        for c, t in d.items():
            ts_by_code[c] = max(ts_by_code.get(c, 0), t)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(canon_url(c) + "\n" for c in sorted(missing, key=lambda c: -ts_by_code.get(c, 0))))
    print(f"\nwrote {len(missing)} missing URL(s) to {out_path} (newest save first). Parquet untouched.")
    return 0


DEMO_COLLECTIONS = {  # old flat shape: header item, then its posts
    "saved_saved_collections": [
        {"title": "Collection", "string_map_data": {"Name": {"value": "AI 1"}, "Creation Time": {"timestamp": 1700000000}}},
        {"title": "someuser", "string_map_data": {"Name": {"href": "{U0}", "value": "someuser"}, "Added Time": {"timestamp": 1757000000}}},
        {"title": "someuser", "string_map_data": {"Name": {"href": "{U1}", "value": "someuser"}, "Added Time": {"timestamp": 1757100000}}},
        {"title": "demo", "string_map_data": {"Name": {"href": "https://www.instagram.com/reel/DEMOfake001/", "value": "demo"}, "Added Time": {"timestamp": 1760000000}}},
        {"title": "Collection", "string_map_data": {"Name": {"value": "Music"}, "Creation Time": {"timestamp": 1700000000}}},
        {"title": "demo", "string_map_data": {"Name": {"href": "{U2}", "value": "demo"}, "Added Time": {"timestamp": 1758000000}}},
        {"title": "demo", "string_map_data": {"Name": {"href": "https://www.instagram.com/p/DEMOfake002/", "value": "demo"}, "Added Time": {"timestamp": 1761000000}}},
        {"title": "Collection", "string_map_data": {"Name": {"value": "Brand New CollÃ©"}, "Creation Time": {"timestamp": 1700000000}}},
        {"title": "demo", "string_map_data": {"Name": {"href": "https://www.instagram.com/p/DEMOfake003/", "value": "demo"}, "Added Time": {"timestamp": 1761500000}}},
    ]
}
DEMO_POSTS = {
    "saved_saved_media": [
        {"title": "someuser", "string_map_data": {"Saved on": {"href": "{U0}", "timestamp": 1757000000}}},
        {"title": "loner", "string_map_data": {"Saved on": {"href": "https://www.instagram.com/p/DEMOloose01/", "timestamp": 1761600000}}},
    ]
}
DEMO_GROUPED = [  # newer grouped + label_values shape (used for the zip variant)
    {"title": "AI 1", "items": [
        {"timestamp": 1757000000, "label_values": [{"label": "URL", "value": "{U0}", "href": "{U0}"}]},
        {"timestamp": 1760000000, "label_values": [{"label": "URL", "href": "https://www.instagram.com/reel/DEMOfake001/"}]},
    ]},
    {"title": "music", "items": [
        {"timestamp": 1758000000, "label_values": [{"label": "URL", "href": "{U2}"}]},
    ]},
]


def run_demo(demo_dir: Path | None, parquet: Path | None) -> int:
    by_code, _, _ = load_parquet_side(parquet)
    def codes_for(coll):
        return sorted(c for c, i in by_code.items() if coll in i["collections"]) or ["DEMOnone000", "DEMOnone001"]
    ai1, music = codes_for("ai1"), codes_for("music")
    # U1 uses the /reel/ form on purpose: matching must be by shortcode, not literal URL
    subs = {"{U0}": canon_url(ai1[0]), "{U1}": f"https://www.instagram.com/reel/{ai1[1 % len(ai1)]}/",
            "{U2}": canon_url(music[0])}
    def fill(obj):
        s = json.dumps(obj)
        for k, v in subs.items():
            s = s.replace(k, v)
        return json.loads(s)

    root = Path(demo_dir) if demo_dir else Path(tempfile.mkdtemp(prefix="ig_export_demo_"))
    saved = root / "export_flat" / "your_instagram_activity" / "saved"
    saved.mkdir(parents=True, exist_ok=True)
    (saved / "saved_collections.json").write_text(json.dumps(fill(DEMO_COLLECTIONS), indent=1))
    (saved / "saved_posts.json").write_text(json.dumps(fill(DEMO_POSTS), indent=1))
    zpath = root / "export_grouped.zip"
    with zipfile.ZipFile(zpath, "w") as z:
        z.writestr("your_instagram_activity/saved/saved_collections.json", json.dumps(fill(DEMO_GROUPED)))

    print(f"[demo] fabricated exports in {root}\n\n=== demo 1/2: flat shape, directory ===")
    rc1 = reconcile(root / "export_flat", root / "reconcile_missing_flat.txt", parquet, {}, False, 5)
    print("\n=== demo 2/2: grouped + label_values shape, zip ===")
    rc2 = reconcile(zpath, root / "reconcile_missing_zip.txt", parquet, {}, False, 5)
    return rc1 or rc2


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("export", nargs="?", type=Path, help="export directory, .zip, or a saved_*.json file")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"missing-URL file (default {DEFAULT_OUT.relative_to(ROOT)})")
    ap.add_argument("--map", action="append", default=[], metavar="'IG Name=slug'",
                    help="map an export collection name to a parquet collection slug (repeatable)")
    ap.add_argument("--include-uncollected", action="store_true",
                    help="also count saved posts that are in no collection (default: collections only)")
    ap.add_argument("--show", type=int, default=15, help="max URLs listed per bucket (default 15)")
    ap.add_argument("--parquet", type=Path, help="override entries.parquet path")
    ap.add_argument("--demo", nargs="?", const="", metavar="DIR", help="fabricate a tiny export (in DIR or a temp dir) and run on it")
    args = ap.parse_args(argv)

    if args.demo is not None:
        return run_demo(Path(args.demo) if args.demo else None, args.parquet)
    if not args.export:
        ap.error("export path required (or --demo)")
    mapping = {}
    for m in args.map:
        if "=" not in m:
            ap.error(f"--map expects 'IG Name=slug', got {m!r}")
        k, v = m.split("=", 1)
        mapping[k.strip()] = v.strip()
        mapping[norm_coll(k)] = v.strip()
    return reconcile(args.export, args.out, args.parquet, mapping, args.include_uncollected, args.show)


if __name__ == "__main__":
    sys.exit(main())
