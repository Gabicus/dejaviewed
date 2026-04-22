#!/usr/bin/env python3
"""DejaViewed CMS — parquet data layer.

Single source of truth for all entries. Backs the static site, the cosmos/
graph visualizations, the admin editor, and the agent context layer.

Files:
  data/entries.parquet     one row per post/resource
  data/crosslinks.parquet  precomputed a/b/dim/weight pairs (for graphs)
  data/patches.json        pending admin-UI edits, merged on next ingest

Schema lives in SCHEMA below. Use `python scripts/cms.py migrate` to seed
from site/catalog.json. Use `python scripts/cms.py rebuild` to recompute
crosslinks + refresh catalog.json/catalog.js from parquet.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import duckdb

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)

ENTRIES_PARQUET = DATA / "entries.parquet"
CROSSLINKS_PARQUET = DATA / "crosslinks.parquet"
DEEP_DIVES_PARQUET = DATA / "deep_dives.parquet"
PATCHES_JSON = DATA / "patches.json"

# ── Schema ──────────────────────────────────────────────────────────────
SCHEMA = pa.schema([
    ("id",                pa.string()),
    ("post_id",           pa.string()),
    ("url",               pa.string()),
    ("source_collection", pa.string()),
    ("collections",       pa.list_(pa.string())),  # multi-collection (post may live in many)
    ("creator",           pa.string()),
    ("date",              pa.string()),
    ("title",             pa.string()),
    ("summary",           pa.string()),
    ("caption",           pa.string()),
    ("media_type",        pa.string()),
    ("type",              pa.string()),
    ("tier",              pa.string()),
    ("audience",          pa.string()),
    ("tags",              pa.list_(pa.string())),
    ("domains",           pa.list_(pa.string())),
    ("tools",             pa.list_(pa.string())),
    ("techniques",        pa.list_(pa.string())),
    ("models",            pa.list_(pa.string())),
    ("repos",             pa.list_(pa.string())),
    ("takeaways",         pa.list_(pa.string())),
    ("has_guide",         pa.bool_()),
    ("deep_dive_slug",    pa.string()),
    ("favorited",         pa.bool_()),
    ("user_notes",        pa.string()),
    ("last_edited_at",    pa.string()),
    ("last_scraped_at",   pa.string()),
    ("transcript",        pa.string()),
    ("transcript_source", pa.string()),  # "ig_cc" | "whisper_local" | "whisper_api"
    ("transcript_at",     pa.string()),
    ("media_url",         pa.string()),  # direct mp4/audio URL for transcription
    ("thumb_path",        pa.string()),  # local path: thumb/{post_id}.jpg
    ("medium",            pa.string()),  # art: oil|acrylic|3d|photo|digital|unknown
    ("style_tags",        pa.list_(pa.string())),
    ("subject_matter",    pa.string()),
    ("reference_for",     pa.list_(pa.string())),
    ("color_palette",     pa.list_(pa.string())),
    ("is_new",            pa.bool_()),
    ("collection",        pa.string()),  # legacy compat: primary collection
])

CROSSLINK_SCHEMA = pa.schema([
    ("a_id",   pa.string()),
    ("b_id",   pa.string()),
    ("dim",    pa.string()),
    ("weight", pa.float32()),
])

DEEP_DIVE_SCHEMA = pa.schema([
    ("id",                   pa.string()),
    ("title",                pa.string()),
    ("dive_type",            pa.string()),      # auto type: tool|technique|creator|domain|guide
    ("dive_class",           pa.string()),      # insight class: emergent_capability|workflow_multiplier|etc
    ("thesis",               pa.string()),
    ("summary",              pa.string()),
    ("entry_ids",            pa.list_(pa.string())),
    ("entry_count",          pa.int32()),
    ("connection_map",       pa.string()),      # JSON string of {entry_id: role_description}
    ("anchor_tag",           pa.string()),
    ("tier",                 pa.string()),
    ("quality_rating",       pa.int32()),        # 1-5 stars
    ("execution_difficulty", pa.string()),       # Easy|Medium|Hard|Experimental
    ("value_type",           pa.string()),       # creative_fusion|workflow_multiplier|etc
    ("action_sketch",        pa.string()),
    ("creators",             pa.list_(pa.string())),
    ("tools",                pa.list_(pa.string())),
    ("suggested_by",         pa.string()),       # auto|manual|curated
    ("pinned",               pa.bool_()),
    ("created_at",           pa.string()),
])

CROSS_DIMS = ("creator", "tool", "technique", "domain", "tier", "type", "collection", "medium", "style_tag")


# ── Helpers ─────────────────────────────────────────────────────────────
POST_ID_PATTERNS = [
    re.compile(r"instagram\.com/(?:p|reel|tv)/([^/?#]+)", re.I),
    re.compile(r"github\.com/([^/]+/[^/?#]+)", re.I),
    re.compile(r"x\.com/[^/]+/status/(\d+)", re.I),
    re.compile(r"twitter\.com/[^/]+/status/(\d+)", re.I),
    re.compile(r"youtu\.be/([^/?#]+)", re.I),
    re.compile(r"youtube\.com/watch\?v=([^&]+)", re.I),
]


def derive_post_id(url: str | None) -> str | None:
    if not url:
        return None
    for p in POST_ID_PATTERNS:
        m = p.search(url)
        if m:
            return m.group(1)
    return None


def stable_id(url: str | None, post_id: str | None, fallback_id: str | None) -> str:
    """Deterministic row id. Prefers post_id, then url hash, then fallback."""
    if post_id:
        return post_id
    if url:
        return hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    if fallback_id:
        return fallback_id
    return hashlib.sha1(str(datetime.now().replace(microsecond=0)).encode()).hexdigest()[:12]


def _clean(v, default=""):
    return v if v else default


def _list(v):
    return list(v) if isinstance(v, (list, tuple)) else []


def entry_from_catalog(e: dict) -> dict:
    """Map a catalog.json entry → CMS row."""
    url = _clean(e.get("url"), "")
    post_id = _clean(e.get("post_id")) or derive_post_id(url)
    rid = stable_id(url, post_id, e.get("id"))
    source_col = _clean(e.get("collection"))
    tags = sorted(set(
        [*_list(e.get("domains")), *_list(e.get("tools")),
         *_list(e.get("techniques")), *_list(e.get("models"))]
    ))
    return {
        "id": rid,
        "post_id": post_id or "",
        "url": url,
        "source_collection": source_col,
        "collections": [source_col] if source_col else [],
        "creator": _clean(e.get("creator")),
        "date": _clean(e.get("date")),
        "title": _clean(e.get("title")),
        "summary": _clean(e.get("summary")),
        "caption": _clean(e.get("caption")),
        "media_type": _clean(e.get("media_type"), "image"),
        "type": _clean(e.get("type"), "resource"),
        "tier": _clean(e.get("tier"), "C").upper(),
        "audience": _clean(e.get("audience"), "intermediate"),
        "tags": tags,
        "domains": _list(e.get("domains")),
        "tools": _list(e.get("tools")),
        "techniques": _list(e.get("techniques")),
        "models": _list(e.get("models")),
        "repos": _list(e.get("repos")),
        "takeaways": _list(e.get("takeaways")),
        "has_guide": bool(e.get("has_guide")),
        "deep_dive_slug": _clean(e.get("deep_dive")),
        "favorited": False,
        "user_notes": "",
        "last_edited_at": "",
        "last_scraped_at": datetime.now().replace(microsecond=0).isoformat(timespec="seconds"),
        "transcript": _clean(e.get("transcript")),
        "transcript_source": _clean(e.get("transcript_source")),
        "transcript_at": _clean(e.get("transcript_at")),
        "media_url": _clean(e.get("media_url")),
        "thumb_path": f'thumb/{e.get("post_id", "")}.jpg' if e.get("post_id") else "",
        "medium": _clean(e.get("medium")),
        "style_tags": _list(e.get("style_tags")),
        "subject_matter": _clean(e.get("subject_matter")),
        "reference_for": _list(e.get("reference_for")),
        "color_palette": _list(e.get("color_palette")),
        "is_new": bool(e.get("is_new")),
        "collection": _clean(e.get("collection")) or _clean(e.get("source_collection")),
    }


# ── Crosslinks ──────────────────────────────────────────────────────────
def compute_crosslinks(rows: list[dict]) -> list[dict]:
    """O(N·K) crosslink precompute — group entries by each dim's values,
    then emit all pairs within each group. Weight = 1 for single-value
    dims, count-of-shared-tags for list dims."""
    links: list[dict] = []

    def pairs_for_dim(dim: str, index: dict[str, list[str]]):
        for _val, ids in index.items():
            if len(ids) < 2:
                continue
            ids = sorted(set(ids))
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    links.append({"a_id": ids[i], "b_id": ids[j],
                                  "dim": dim, "weight": 1.0})

    # Single-valued dims
    for dim, key in (("creator", "creator"), ("tier", "tier"),
                     ("type", "type"), ("medium", "medium"),
                     ("subject", "subject_matter")):
        idx: dict[str, list[str]] = defaultdict(list)
        for r in rows:
            v = r.get(key) or ""
            if v:
                idx[v].append(r["id"])
        pairs_for_dim(dim, idx)

    # Collections (multi)
    idx = defaultdict(list)
    for r in rows:
        for c in r.get("collections") or []:
            if c:
                idx[c].append(r["id"])
    pairs_for_dim("collection", idx)

    # List dims — weight = number of shared values between the pair
    for dim, key in (("tool", "tools"), ("technique", "techniques"),
                     ("domain", "domains"), ("style_tag", "style_tags"),
                     ("reference", "reference_for")):
        idx = defaultdict(list)
        for r in rows:
            for v in r.get(key) or []:
                if v:
                    idx[v].append(r["id"])
        # Count-weighted pairs
        pair_w: dict[tuple[str, str], float] = defaultdict(float)
        for _v, ids in idx.items():
            ids = sorted(set(ids))
            for i in range(len(ids)):
                for j in range(i + 1, len(ids)):
                    pair_w[(ids[i], ids[j])] += 1.0
        for (a, b), w in pair_w.items():
            links.append({"a_id": a, "b_id": b, "dim": dim, "weight": w})

    return links


# ── I/O ─────────────────────────────────────────────────────────────────
def load_entries() -> list[dict]:
    """Read entries parquet and fill any schema fields the file is missing.
    Tolerant to older parquet files written before schema extensions."""
    if not ENTRIES_PARQUET.exists():
        return []
    t = pq.read_table(ENTRIES_PARQUET)
    rows = t.to_pylist()
    for r in rows:
        for field in SCHEMA:
            if field.name in r:
                continue
            if field.type == pa.bool_():
                r[field.name] = False
            elif pa.types.is_list(field.type):
                r[field.name] = []
            else:
                r[field.name] = ""
    return rows


def write_entries(rows: list[dict]) -> None:
    # Ensure every row has every schema field
    normalized = []
    for r in rows:
        out = {}
        for field in SCHEMA:
            if field.type == pa.bool_():
                out[field.name] = bool(r.get(field.name, False))
            elif pa.types.is_list(field.type):
                out[field.name] = list(r.get(field.name) or [])
            else:
                out[field.name] = r.get(field.name) or ""
        normalized.append(out)
    t = pa.Table.from_pylist(normalized, schema=SCHEMA)
    pq.write_table(t, ENTRIES_PARQUET, compression="zstd")


def load_deep_dives() -> list[dict]:
    if not DEEP_DIVES_PARQUET.exists():
        return []
    t = pq.read_table(DEEP_DIVES_PARQUET)
    dives = t.to_pylist()
    for d in dives:
        if d.get("connection_map"):
            try:
                d["connection_map"] = json.loads(d["connection_map"])
            except (json.JSONDecodeError, TypeError):
                pass
    return dives


def write_deep_dives(dives: list[dict]) -> None:
    normalized = []
    for d in dives:
        row = {}
        for field in DEEP_DIVE_SCHEMA:
            v = d.get(field.name)
            if field.name == "connection_map" and isinstance(v, dict):
                v = json.dumps(v, ensure_ascii=False)
            if field.name == "entry_count" and v is None:
                v = len(d.get("entry_ids", []))
            if v is None:
                if pa.types.is_list(field.type):
                    v = []
                elif pa.types.is_boolean(field.type):
                    v = False
                elif pa.types.is_int32(field.type):
                    v = 0
                else:
                    v = ""
            row[field.name] = v
        normalized.append(row)
    if not normalized:
        pq.write_table(pa.Table.from_pylist([], schema=DEEP_DIVE_SCHEMA),
                       DEEP_DIVES_PARQUET, compression="zstd")
        return
    t = pa.Table.from_pylist(normalized, schema=DEEP_DIVE_SCHEMA)
    pq.write_table(t, DEEP_DIVES_PARQUET, compression="zstd")
    print(f"[cms] wrote {len(normalized)} deep dives to {DEEP_DIVES_PARQUET}")


def load_crosslinks() -> list[dict]:
    if not CROSSLINKS_PARQUET.exists():
        return []
    return pq.read_table(CROSSLINKS_PARQUET).to_pylist()


def write_crosslinks(links: list[dict]) -> None:
    if not links:
        pq.write_table(pa.Table.from_pylist([], schema=CROSSLINK_SCHEMA),
                       CROSSLINKS_PARQUET, compression="zstd")
        return
    t = pa.Table.from_pylist(links, schema=CROSSLINK_SCHEMA)
    pq.write_table(t, CROSSLINKS_PARQUET, compression="zstd")


# ── Dedupe ──────────────────────────────────────────────────────────────
def has_entry(rows: list[dict], url: str | None, post_id: str | None) -> dict | None:
    """Used before scraping: check for an existing row by post_id or URL."""
    if not rows:
        return None
    pid = post_id or derive_post_id(url or "")
    if pid:
        for r in rows:
            if r.get("post_id") == pid:
                return r
    if url:
        for r in rows:
            if r.get("url") == url:
                return r
    return None


def upsert(rows: list[dict], new_row: dict) -> tuple[list[dict], str]:
    """Insert or merge. Returns (rows, action) where action ∈ {'inserted','merged','unchanged'}.
    Merge preserves manual edits (user_notes, favorited, last_edited_at, tier if edited)."""
    existing = has_entry(rows, new_row.get("url"), new_row.get("post_id"))
    if not existing:
        rows.append(new_row)
        return rows, "inserted"
    # Merge: keep edited fields, take fresh scrape for the rest
    merged = dict(existing)
    for k, v in new_row.items():
        if k in ("favorited", "user_notes"):
            continue  # never overwrite user edits
        if k == "last_edited_at" and existing.get("last_edited_at"):
            continue  # keep edit timestamp
        if existing.get("last_edited_at"):
            # If a field was manually edited, don't clobber it with scraped data.
            # Heuristic: if the user edited anything, preserve tier/title/summary.
            if k in ("tier", "title", "summary"):
                if existing.get(k):
                    continue
        merged[k] = v
    # Merge collections (multi-membership)
    merged["collections"] = sorted(set(
        (existing.get("collections") or []) + (new_row.get("collections") or [])
    ))
    # Replace in rows
    for i, r in enumerate(rows):
        if r.get("id") == existing.get("id"):
            rows[i] = merged
            return rows, "merged"
    return rows, "merged"


# ── Commands ────────────────────────────────────────────────────────────
def cmd_migrate(args):
    src = SITE / "catalog.json"
    if not src.exists():
        print(f"[cms] error: {src} not found", file=sys.stderr)
        return 1
    catalog = json.loads(src.read_text(encoding="utf-8"))
    entries = catalog.get("entries") or []
    rows = [entry_from_catalog(e) for e in entries]
    # Collapse duplicates by id, merging collections
    by_id: dict[str, dict] = {}
    for r in rows:
        if r["id"] in by_id:
            by_id[r["id"]]["collections"] = sorted(set(
                by_id[r["id"]]["collections"] + r["collections"]
            ))
        else:
            by_id[r["id"]] = r
    deduped = list(by_id.values())
    write_entries(deduped)
    links = compute_crosslinks(deduped)
    write_crosslinks(links)
    _write_catalog_exports(deduped)
    print(f"[cms] migrated {len(deduped)} entries "
          f"({len(entries) - len(deduped)} duplicates collapsed) + "
          f"{len(links)} crosslinks to {DATA}")
    return 0


def cmd_rebuild(args):
    rows = load_entries()
    if not rows:
        print("[cms] no entries.parquet — run migrate first", file=sys.stderr)
        return 1
    links = compute_crosslinks(rows)
    write_crosslinks(links)
    # Write a fresh catalog.json + catalog.js for legacy consumers
    _write_catalog_exports(rows)
    print(f"[cms] rebuilt {len(rows)} entries + {len(links)} crosslinks + catalog.json/js")
    return 0


def cmd_check(args):
    """Dedupe check: given --url or --post-id, report if already present."""
    rows = load_entries()
    hit = has_entry(rows, args.url, args.post_id)
    if hit:
        print(f"[cms] DUPLICATE: id={hit['id']} creator={hit.get('creator')} "
              f"title={hit.get('title')[:80]!r}")
        return 0
    print("[cms] NEW — safe to scrape")
    return 2  # exit 2 = not found (scripts can condition on this)


def cmd_apply_patch(args):
    """Merge an admin patch (edits/adds/deletes) into parquet."""
    path = Path(args.path)
    if not path.exists():
        print(f"[cms] error: {path} not found", file=sys.stderr)
        return 1
    patch = json.loads(path.read_text(encoding="utf-8"))
    rows = load_entries()
    by_id = {r["id"]: r for r in rows}
    now = datetime.now().replace(microsecond=0).isoformat(timespec="seconds")

    edits = patch.get("edits") or {}
    adds = patch.get("adds") or []
    deletes = patch.get("deletes") or []

    n_edit = n_add = n_del = 0
    for rid, patch_row in edits.items():
        if rid not in by_id:
            print(f"[cms] warn: edit for unknown id {rid} — skipping", file=sys.stderr)
            continue
        merged = dict(by_id[rid])
        for k, v in patch_row.items():
            if k == "id": continue
            merged[k] = v
        merged["last_edited_at"] = now
        by_id[rid] = merged
        n_edit += 1

    for add in adds:
        row = entry_from_catalog({
            "id": add.get("id"),
            "url": add.get("url", ""),
            "title": add.get("title", ""),
            "creator": add.get("creator", ""),
            "summary": add.get("summary", ""),
            "tier": add.get("tier", "C"),
            "type": add.get("type", "resource"),
            "collection": (add.get("collections") or [""])[0] if add.get("collections") else "",
            "collections": add.get("collections") or [],
            "tools": add.get("tools") or [],
            "techniques": add.get("techniques") or [],
            "domains": add.get("domains") or [],
            "models": add.get("models") or [],
            "favorited": bool(add.get("favorited")),
            "user_notes": add.get("user_notes", ""),
        })
        row["last_edited_at"] = now
        by_id[row["id"]] = row
        n_add += 1

    for rid in deletes:
        if by_id.pop(rid, None):
            n_del += 1

    new_rows = list(by_id.values())
    write_entries(new_rows)
    links = compute_crosslinks(new_rows)
    write_crosslinks(links)
    _write_catalog_exports(new_rows)
    print(f"[cms] applied patch: {n_edit} edits, {n_add} adds, {n_del} deletes "
          f"-> {len(new_rows)} entries, {len(links)} crosslinks")
    return 0


def cmd_stats(args):
    rows = load_entries()
    if not rows:
        print("[cms] empty")
        return 0
    con = duckdb.connect(":memory:")
    con.register("e", pa.Table.from_pylist(rows, schema=SCHEMA))
    for q, label in [
        ("SELECT count(*) FROM e", "total"),
        ("SELECT tier, count(*) FROM e GROUP BY tier ORDER BY tier", "by tier"),
        ("SELECT type, count(*) FROM e GROUP BY type ORDER BY 2 DESC", "by type"),
        ("SELECT source_collection, count(*) FROM e GROUP BY 1 ORDER BY 2 DESC", "by collection"),
    ]:
        print(f"\n-- {label} --")
        for row in con.execute(q).fetchall():
            print(" ", row)
    return 0


def _write_catalog_exports(rows: list[dict]) -> None:
    """Keep legacy catalog.json/catalog.js in sync with parquet."""
    entries_out = [
        {
            # Legacy compat: keep singular `collection` for old renderers
            # that filter by it. Populated from source_collection.
            **{k: r[k] for k in r if k not in ("last_scraped_at", "last_edited_at")},
            "collection": r.get("source_collection", ""),
            "deep_dive": r.get("deep_dive_slug", ""),
        }
        for r in rows
    ]
    # Rebuild stats + indices that graph.html / catalog.html consume
    from collections import Counter, defaultdict
    coll_counts = Counter(e.get("collection", "") for e in entries_out if e.get("collection"))
    tier_counts = Counter(e.get("tier", "") for e in entries_out if e.get("tier"))
    type_counts = Counter(e.get("type", "") for e in entries_out if e.get("type"))
    by_tool = defaultdict(list); by_technique = defaultdict(list)
    by_domain = defaultdict(list); by_creator = defaultdict(list)
    by_medium = defaultdict(list); by_style = defaultdict(list)
    by_subject = defaultdict(list); by_reference = defaultdict(list)
    for e in entries_out:
        if not e.get("id"): continue
        for t in (e.get("tools") or []): by_tool[t].append(e["id"])
        for t in (e.get("techniques") or []): by_technique[t].append(e["id"])
        for t in (e.get("domains") or []): by_domain[t].append(e["id"])
        if e.get("creator"): by_creator[e["creator"]].append(e["id"])
        if e.get("medium"): by_medium[e["medium"]].append(e["id"])
        for s in (e.get("style_tags") or []): by_style[s].append(e["id"])
        if e.get("subject_matter"): by_subject[e["subject_matter"]].append(e["id"])
        for r in (e.get("reference_for") or []): by_reference[r].append(e["id"])
    legacy = {
        "version": "2.0",
        "generated": datetime.now().replace(microsecond=0).isoformat(timespec="seconds"),
        "description": "DejaViewed catalog — generated from data/entries.parquet by scripts/cms.py",
        "stats": {
            "total": len(entries_out),
            "collections": dict(coll_counts),
            "tiers": dict(tier_counts),
            "types": dict(type_counts),
        },
        "indices": {
            "by_tool": {k: v for k, v in by_tool.items()},
            "by_technique": {k: v for k, v in by_technique.items()},
            "by_domain": {k: v for k, v in by_domain.items()},
            "by_creator": {k: v for k, v in by_creator.items()},
            "by_medium": {k: v for k, v in by_medium.items()},
            "by_style": {k: v for k, v in by_style.items()},
            "by_subject": {k: v for k, v in by_subject.items()},
            "by_reference": {k: v for k, v in by_reference.items()},
        },
        "entries": entries_out,
    }
    (SITE / "catalog.json").write_text(
        json.dumps(legacy, ensure_ascii=False, indent=2), encoding="utf-8")
    (SITE / "catalog.js").write_text(
        "window.__CATALOG = " + json.dumps(legacy, ensure_ascii=False) + ";",
        encoding="utf-8")
    # Crosslinks: grouped by dim, compact shape {a,b,w}
    try:
        links = load_crosslinks()
    except Exception:
        links = []
    grouped: dict[str, list] = {}
    for L in links:
        grouped.setdefault(L["dim"], []).append(
            {"a": L["a_id"], "b": L["b_id"], "w": round(float(L["weight"]), 3)}
        )
    (SITE / "crosslinks.js").write_text(
        "window.__CROSSLINKS = " + json.dumps(grouped, ensure_ascii=False) + ";",
        encoding="utf-8")
    # Deep dives: load from parquet, export to deep_dives.js + data/deep_dives.json
    try:
        dives = load_deep_dives()
    except Exception:
        dives = []
    if dives:
        # Restore frontend-friendly 'type' field from parquet fields
        for d in dives:
            if not d.get("type"):
                d["type"] = d.get("dive_type") or d.get("dive_class") or d.get("value_type") or "insight"
            if not d.get("class"):
                d["class"] = d.get("dive_class") or d.get("value_type") or ""
        by_class = defaultdict(list)
        by_dive_type = defaultdict(list)
        for d in dives:
            cls = d.get("dive_class") or d.get("value_type") or ""
            if cls:
                by_class[cls].append(d["id"])
            dt = d.get("dive_type") or d.get("type") or ""
            if dt:
                by_dive_type[dt].append(d["id"])
        dive_classes = {}
        try:
            manual_path = DATA / "manual_dives.json"
            if manual_path.exists():
                dive_classes = json.loads(manual_path.read_text(encoding="utf-8")).get("classes", {})
        except Exception:
            pass
        dive_wrapper = {
            "deep_dives": dives,
            "classes": dive_classes,
            "stats": {
                "total": len(dives),
                "curated": sum(1 for d in dives if d.get("pinned")),
                "auto": sum(1 for d in dives if not d.get("pinned")),
                "by_class": {k: len(v) for k, v in by_class.items()},
                "by_type": {k: len(v) for k, v in by_dive_type.items()},
            },
            "generated_at": datetime.now().replace(microsecond=0).isoformat(timespec="seconds"),
            "attribution": "Curated by Claude for Gabe (@6ab3) — dejaviewed.com",
        }
        (DATA / "deep_dives.json").write_text(
            json.dumps(dive_wrapper, ensure_ascii=False, indent=2), encoding="utf-8")
        (SITE / "deep_dives.js").write_text(
            "window.__DEEP_DIVES = " + json.dumps(dive_wrapper, ensure_ascii=False) + ";",
            encoding="utf-8")


def main(argv=None):
    p = argparse.ArgumentParser(prog="cms")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("migrate", help="seed parquet from site/catalog.json")
    sub.add_parser("rebuild", help="recompute crosslinks + export catalog.json/js")
    c = sub.add_parser("check", help="dedupe-check a URL or post_id")
    c.add_argument("--url"); c.add_argument("--post-id")
    a = sub.add_parser("apply-patch", help="apply an admin-UI patch JSON")
    a.add_argument("path", help="path to patch JSON from admin.html")
    sub.add_parser("stats", help="print dataset stats")
    args = p.parse_args(argv)
    return {"migrate": cmd_migrate, "rebuild": cmd_rebuild,
            "check": cmd_check, "apply-patch": cmd_apply_patch,
            "stats": cmd_stats}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
