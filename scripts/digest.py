#!/usr/bin/env python3
"""dejaviewed digest pass — deterministic clustering + ranking over catalog.json.

Reads:  site/catalog.json
Writes: site/summaries.json, site/recommendations.json

No LLM calls. Clustering groups entries within a category by their strongest
shared technique/tool/domain. Recommendation scoring uses inverse-document-frequency
weighting so entries that share rare values rank above entries sharing common ones.

Pipeline: LOAD -> CLUSTER -> SUMMARY -> RECS -> EMIT -> VALIDATE.

Cache-aware: skips if outputs are newer than the input catalog unless --force is
passed. That lets rebuild.sh chain this without re-work on every call.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "site" / "catalog.json"
SUMMARIES_OUT = ROOT / "site" / "summaries.json"
RECS_OUT = ROOT / "site" / "recommendations.json"

# Weight of each dimension when computing cluster strength + recommendation score.
DIM_WEIGHTS = {"techniques": 1.0, "tools": 0.85, "domains": 0.55, "models": 0.5}
CLUSTER_DIMS = ("techniques", "tools", "domains")
TIER_WEIGHT = {"S": 1.0, "A": 0.7, "B": 0.35, "C": 0.1}

MIN_CLUSTER = 2          # skip singletons
MAX_CLUSTER = 8          # split big clusters; readability cap
MAX_CARDS_PER_CAT = 6    # cards shown per category on Core page
LATEST_BATCH_RECS = 5    # top recs in the newest batch
EVERGREEN_RECS = 4       # stable, high-value cross-batch recs
ARCHIVE_BATCHES = 4      # history depth


def load_catalog() -> dict:
    if not CATALOG.exists():
        die(f"catalog.json not found at {CATALOG}. Run build_catalog.py first.")
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def should_skip(force: bool) -> bool:
    if force:
        return False
    if not (SUMMARIES_OUT.exists() and RECS_OUT.exists()):
        return False
    return (
        min(SUMMARIES_OUT.stat().st_mtime, RECS_OUT.stat().st_mtime)
        >= CATALOG.stat().st_mtime
    )


def die(msg: str) -> None:
    print(f"[digest] error: {msg}", file=sys.stderr)
    sys.exit(1)


def build_dim_index(entries: list[dict]) -> dict[str, dict[str, list[str]]]:
    """dim -> value -> [entry_id, ...] across the whole catalog."""
    idx: dict[str, dict[str, list[str]]] = {d: defaultdict(list) for d in DIM_WEIGHTS}
    for e in entries:
        eid = e["id"]
        for dim in DIM_WEIGHTS:
            for v in e.get(dim, []) or []:
                idx[dim][v].append(eid)
    return {d: dict(m) for d, m in idx.items()}


def cluster_category(entries: list[dict]) -> list[dict]:
    """Group entries in a single category by their strongest shared dimension value.

    Greedy: walk entries tier-ordered, seed a cluster on the rarest unclaimed
    shared value, absorb matching entries up to MAX_CLUSTER. Leftover entries
    become a 'Top picks' bucket if big enough.
    """
    tier_key = {"S": 0, "A": 1, "B": 2, "C": 3}
    ordered = sorted(entries, key=lambda e: (tier_key.get(e.get("tier") or "C", 3), -len(e.get("takeaways") or [])))

    local_idx: dict[tuple[str, str], list[str]] = defaultdict(list)
    for e in ordered:
        for dim in CLUSTER_DIMS:
            for v in e.get(dim, []) or []:
                local_idx[(dim, v)].append(e["id"])

    claimed: set[str] = set()
    clusters: list[dict] = []
    entry_by_id = {e["id"]: e for e in entries}

    # Rank candidate seeds: dims with 2..MAX_CLUSTER entries, rarer first.
    candidates = [
        (dim, val, ids)
        for (dim, val), ids in local_idx.items()
        if MIN_CLUSTER <= len(ids) <= MAX_CLUSTER
    ]
    candidates.sort(key=lambda c: (len(c[2]), -DIM_WEIGHTS[c[0]]))

    for dim, val, ids in candidates:
        unclaimed = [i for i in ids if i not in claimed]
        if len(unclaimed) < MIN_CLUSTER:
            continue
        clusters.append({"dim": dim, "value": val, "entry_ids": unclaimed[:MAX_CLUSTER]})
        claimed.update(unclaimed[:MAX_CLUSTER])

    leftovers = [e["id"] for e in ordered if e["id"] not in claimed]
    # Chunk leftovers into multiple Top-picks cards so we don't silently drop entries.
    for i in range(0, len(leftovers), MAX_CLUSTER):
        chunk = leftovers[i : i + MAX_CLUSTER]
        if len(chunk) >= MIN_CLUSTER:
            clusters.append({"dim": "tier", "value": "top-picks", "entry_ids": chunk})

    # Cap per category, preserve seed-order (rarer clusters first).
    return [c for c in clusters if c["entry_ids"]][:MAX_CARDS_PER_CAT], entry_by_id


def summarize_cluster(cluster: dict, entry_by_id: dict[str, dict]) -> dict:
    members = [entry_by_id[i] for i in cluster["entry_ids"] if i in entry_by_id]
    if not members:
        return {}

    dim, val = cluster["dim"], cluster["value"]
    if dim == "tier":
        title = "Top picks in this collection"
    else:
        title = f"{val} — across {len(members)} posts"

    why = derive_why(members, dim, val)
    takeaways = top_takeaways(members)
    creators = [c for c, _ in Counter(m.get("creator") for m in members if m.get("creator")).most_common(4)]
    tools = [t for t, _ in Counter(t for m in members for t in (m.get("tools") or [])).most_common(5)]
    actionable = derive_actionable(members)

    return {
        "title": title,
        "why_it_matters": why,
        "key_takeaways": takeaways,
        "dominant_creators": creators,
        "dominant_tools": tools,
        "actionable": actionable,
        "entries": [m["id"] for m in members],
    }


def derive_why(members: list[dict], dim: str, val: str) -> str:
    tiers = Counter(m.get("tier") for m in members)
    s_count = tiers.get("S", 0)
    a_count = tiers.get("A", 0)
    strongest = "S-tier" if s_count else ("A-tier" if a_count else "mid-tier")
    if dim == "tier":
        return f"A mixed bag of {len(members)} posts worth revisiting — {strongest} picks without a single shared technique."
    kind_label = {"techniques": "technique", "tools": "tool", "domains": "domain"}[dim]
    return (
        f"{len(members)} posts converge on the {kind_label} \"{val}\" — "
        f"{strongest} signal that this pattern is showing up repeatedly. "
        "Pairing them surfaces the shared playbook."
    )


def top_takeaways(members: list[dict]) -> list[str]:
    """Concatenate unique takeaways across members, tier-biased, capped."""
    seen = set()
    out: list[str] = []
    tier_key = {"S": 0, "A": 1, "B": 2, "C": 3}
    for m in sorted(members, key=lambda m: tier_key.get(m.get("tier") or "C", 3)):
        for t in m.get("takeaways") or []:
            t = t.strip()
            if not t or t.lower() in seen:
                continue
            seen.add(t.lower())
            out.append(t)
            if len(out) >= 4:
                return out
    return out


def derive_actionable(members: list[dict]) -> list[dict]:
    """Pick the most clickable links across cluster members, preferring repos/guides/tools."""
    def rank(link: dict) -> int:
        kind = (link.get("kind") or "").lower()
        return {"repo": 0, "guide": 1, "tool": 2, "paper": 3}.get(kind, 4)

    seen_hrefs: set[str] = set()
    picked: list[dict] = []
    for m in members:
        for link in sorted(m.get("links") or [], key=rank):
            href = link.get("url") or link.get("href")
            label = link.get("label") or link.get("title") or href
            if not href or href in seen_hrefs:
                continue
            seen_hrefs.add(href)
            picked.append({"href": href, "label": label[:80]})
            if len(picked) >= 3:
                return picked
    return picked


def build_recommendations(
    entries: list[dict], dim_index: dict[str, dict[str, list[str]]]
) -> dict:
    """Rank entries via inverse-frequency score + tier weight, group by batch."""
    score_by_id: dict[str, float] = {}
    reason_by_id: dict[str, tuple[str, str]] = {}

    for e in entries:
        score = TIER_WEIGHT.get(e.get("tier") or "C", 0.1)
        best_dim_val: tuple[float, str, str] | None = None
        for dim, weight in DIM_WEIGHTS.items():
            for v in e.get(dim, []) or []:
                freq = len(dim_index.get(dim, {}).get(v, []))
                if freq <= 1:
                    continue
                contrib = weight * (1.0 / freq)
                score += contrib
                if best_dim_val is None or contrib > best_dim_val[0]:
                    best_dim_val = (contrib, dim, v)
        score_by_id[e["id"]] = score
        if best_dim_val:
            reason_by_id[e["id"]] = (best_dim_val[1], best_dim_val[2])

    ranked = sorted(entries, key=lambda e: score_by_id[e["id"]], reverse=True)

    batch_id = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    top = ranked[:LATEST_BATCH_RECS]
    latest_batch = {
        "batch_id": batch_id,
        "added_count": len(entries),
        "headline": build_headline(top),
        "top_recs": [
            {
                "rank": i + 1,
                "title": e.get("title") or e["id"],
                "rationale": rec_rationale(e, reason_by_id.get(e["id"])),
                "entries": [e["id"]],
            }
            for i, e in enumerate(top)
        ],
    }

    # Evergreen: highest-scoring S-tier entries not already in latest top.
    latest_ids = {e["id"] for e in top}
    evergreen_pool = [e for e in ranked if e["id"] not in latest_ids and (e.get("tier") == "S")]
    evergreen = [
        {
            "title": e.get("title") or e["id"],
            "rationale": rec_rationale(e, reason_by_id.get(e["id"])),
            "entries": [e["id"]],
        }
        for e in evergreen_pool[:EVERGREEN_RECS]
    ]

    return {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "latest_batch": latest_batch,
        "evergreen": evergreen,
        "archive": rotate_archive(latest_batch),
    }


def rotate_archive(new_batch: dict) -> list:
    """Push the previous run's latest_batch into archive[], dedup by batch_id.

    On first run, archive is []. On subsequent runs, yesterday's latest_batch
    becomes archive[0] — but only if its batch_id differs from the new one
    (rebuilding the same day shouldn't duplicate).
    """
    if not RECS_OUT.exists():
        return []
    try:
        prev = json.loads(RECS_OUT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    prev_latest = prev.get("latest_batch") or {}
    prev_archive = prev.get("archive") or []
    if not prev_latest:
        return prev_archive[:ARCHIVE_BATCHES]
    if prev_latest.get("batch_id") == new_batch.get("batch_id"):
        return prev_archive[:ARCHIVE_BATCHES]
    rolled = [prev_latest] + [a for a in prev_archive if a.get("batch_id") != prev_latest.get("batch_id")]
    return rolled[:ARCHIVE_BATCHES]


def build_headline(top: list[dict]) -> str:
    if not top:
        return "Nothing new this batch."
    techs = Counter(t for e in top for t in (e.get("techniques") or [])).most_common(2)
    if techs:
        joined = " and ".join(t for t, _ in techs)
        return f"This batch is heavy on {joined}."
    return f"{len(top)} fresh picks worth a look."


def rec_rationale(entry: dict, reason: tuple[str, str] | None) -> str:
    tier = entry.get("tier") or "C"
    creator = entry.get("creator") or "unknown creator"
    if reason:
        dim, val = reason
        kind_label = {"techniques": "technique", "tools": "tool", "domains": "domain", "models": "model"}.get(dim, dim)
        return f"{tier}-tier post from {creator} — rarest shared {kind_label} here is \"{val}\"."
    return f"{tier}-tier standalone from {creator}."


def emit(data: dict, path: Path) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[digest] wrote {path.relative_to(ROOT)} ({path.stat().st_size:,} bytes)")


def validate_summaries(d: dict) -> None:
    if not isinstance(d, dict) or "categories" not in d:
        die("summaries.json missing 'categories'")


def validate_recs(d: dict) -> None:
    for k in ("built_at", "latest_batch", "evergreen", "archive"):
        if k not in d:
            die(f"recommendations.json missing '{k}'")


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--force", action="store_true", help="rebuild even if outputs are fresh")
    args = ap.parse_args(argv)

    if should_skip(args.force):
        print("[digest] outputs are newer than catalog.json — skipping (use --force to rebuild).")
        return 0

    catalog = load_catalog()
    entries = catalog.get("entries") or []
    if not entries:
        die("catalog has no entries")

    dim_index = build_dim_index(entries)

    by_cat: dict[str, list[dict]] = defaultdict(list)
    for e in entries:
        cat = e.get("collection") or "uncategorized"
        by_cat[cat].append(e)

    summaries: dict[str, dict] = {}
    for cat, cat_entries in by_cat.items():
        clusters, entry_by_id = cluster_category(cat_entries)
        cards = [summarize_cluster(c, entry_by_id) for c in clusters]
        cards = [c for c in cards if c]
        summaries[cat] = {"cards": cards, "entry_count": len(cat_entries)}

    summaries_doc = {
        "built_at": datetime.now(timezone.utc).isoformat(),
        "categories": summaries,
    }
    recs_doc = build_recommendations(entries, dim_index)

    validate_summaries(summaries_doc)
    validate_recs(recs_doc)
    emit(summaries_doc, SUMMARIES_OUT)
    emit(recs_doc, RECS_OUT)

    print(
        f"[digest] done: {len(entries)} entries -> "
        f"{sum(len(v['cards']) for v in summaries.values())} cards, "
        f"{len(recs_doc['latest_batch']['top_recs'])} batch recs, "
        f"{len(recs_doc['evergreen'])} evergreen."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
