#!/usr/bin/env python3
"""apply_ratings.py — score and (optionally) apply a blind re-rating from site/rate.html.

Usage:
    python3 scripts/apply_ratings.py <ratings.json>            # dry run: kappa + disagreements
    python3 scripts/apply_ratings.py <ratings.json> --apply    # set tier = owner tier in entries.parquet

The ratings file is the "Download JSON" output of rate.html:
    {"kind": "dejaviewed-ratings", "seed": "2026",
     "ratings": [{"id": ..., "owner_tier": "A", "model_tier": "B", "title": ..., "url": ...}, ...]}

The model tier used for scoring is the CURRENT tier in the parquet (falls back to the
model_tier recorded in the file if the id is missing). --apply only touches entries whose
owner tier differs from the current tier, stamping last_edited_at so cms upserts preserve it.
Run `python3 scripts/cms.py rebuild` afterwards to regenerate the site exports.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

TIERS = ["S", "A", "B", "C"]  # ordinal, best first


def confusion(pairs: list[tuple[str, str]]) -> list[list[int]]:
    """rows = owner tier, cols = model tier."""
    k = len(TIERS)
    m = [[0] * k for _ in range(k)]
    for o, md in pairs:
        if o in TIERS and md in TIERS:
            m[TIERS.index(o)][TIERS.index(md)] += 1
    return m


def kappa(pairs: list[tuple[str, str]], weighted: bool = True) -> float | None:
    """Cohen's kappa; weighted=True uses linear weights w_ij = 1 - |i-j|/(k-1)."""
    k = len(TIERS)
    m = confusion(pairs)
    n = sum(map(sum, m))
    if not n:
        return None
    row = [sum(m[i]) for i in range(k)]
    col = [sum(m[i][j] for i in range(k)) for j in range(k)]
    po = pe = 0.0
    for i in range(k):
        for j in range(k):
            w = 1 - abs(i - j) / (k - 1) if weighted else float(i == j)
            po += w * m[i][j] / n
            pe += w * (row[i] / n) * (col[j] / n)
    if abs(1 - pe) < 1e-12:  # degenerate: everything in one category
        return 1.0 if po >= 1 - 1e-12 else 0.0
    return (po - pe) / (1 - pe)


def load_ratings(path: Path) -> list[dict]:
    data = json.loads(path.read_text())
    rows = data.get("ratings") if isinstance(data, dict) else data
    if not isinstance(rows, list):
        sys.exit(f"[apply_ratings] {path}: no 'ratings' list found")
    out = []
    for r in rows:
        if not isinstance(r, dict) or not r.get("id"):
            continue
        ot = str(r.get("owner_tier", "")).upper()
        if ot not in TIERS:
            print(f"[apply_ratings] skip {r.get('id')}: bad owner_tier {r.get('owner_tier')!r}", file=sys.stderr)
            continue
        out.append({**r, "owner_tier": ot, "model_tier": str(r.get("model_tier", "")).upper()})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ratings", type=Path)
    ap.add_argument("--apply", action="store_true", help="write owner tiers into entries.parquet (default: dry run)")
    ap.add_argument("--parquet", type=Path, help="override entries.parquet path (testing)")
    args = ap.parse_args(argv)

    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import cms  # noqa: E402
    if args.parquet:
        cms.ENTRIES_PARQUET = args.parquet

    ratings = load_ratings(args.ratings)
    if not ratings:
        print("[apply_ratings] no valid ratings in file")
        return 1

    rows = cms.load_entries()
    by_id = {r["id"]: r for r in rows}

    pairs, disagreements, missing = [], [], []
    for r in ratings:
        cur = by_id.get(r["id"])
        model = (cur.get("tier") or "").upper() if cur else r["model_tier"]
        if cur is None:
            missing.append(r["id"])
        if cur and r["model_tier"] and model != r["model_tier"]:
            print(f"[apply_ratings] note: {r['id']} tier changed since rating ({r['model_tier']} -> {model}); scoring vs current")
        if model not in TIERS:
            continue
        pairs.append((r["owner_tier"], model))
        if r["owner_tier"] != model:
            title = (cur or r).get("title") or r["id"]
            disagreements.append((abs(TIERS.index(r["owner_tier"]) - TIERS.index(model)), r["id"], r["owner_tier"], model, title))

    n = len(pairs)
    exact = sum(o == m for o, m in pairs)
    within1 = sum(abs(TIERS.index(o) - TIERS.index(m)) <= 1 for o, m in pairs)
    kw, ku = kappa(pairs, True), kappa(pairs, False)
    fmt = lambda x: "n/a" if x is None else f"{x:.3f}"
    print(f"rated: {n}   exact agreement: {100*exact/n:.1f}%   within one tier: {100*within1/n:.1f}%")
    print(f"Cohen's kappa  linear-weighted: {fmt(kw)}   unweighted: {fmt(ku)}")
    if n < 20:
        print("  (fewer than 20 ratings: kappa is noisy, treat as directional)")
    print("\nconfusion (rows = owner, cols = model)")
    m = confusion(pairs)
    print("      " + "  ".join(f"{t:>3}" for t in TIERS))
    for i, t in enumerate(TIERS):
        print(f"  {t}   " + "  ".join(f"{v:>3}" for v in m[i]))

    if missing:
        print(f"\n{len(missing)} rated id(s) not in parquet (scored with file's model_tier, cannot apply): {', '.join(missing)}")

    print(f"\ndisagreements: {len(disagreements)}")
    for gap, rid, o, md, title in sorted(disagreements, key=lambda d: -d[0]):
        print(f"  {rid:<14} owner {o}  model {md}  (gap {gap})  {title[:70]}")

    to_apply = [(rid, o) for _, rid, o, _, _ in disagreements if rid in by_id]
    if not args.apply:
        print(f"\ndry run: {len(to_apply)} entr{'y' if len(to_apply)==1 else 'ies'} would change tier. Re-run with --apply to write.")
        return 0

    if not to_apply:
        print("\nnothing to apply.")
        return 0
    now = datetime.now().replace(microsecond=0).isoformat(timespec="seconds")
    for rid, o in to_apply:
        by_id[rid]["tier"] = o
        by_id[rid]["last_edited_at"] = now
    cms.write_entries(rows)
    print(f"\napplied: {len(to_apply)} tier change(s) written to {cms.ENTRIES_PARQUET} (last_edited_at={now}).")
    print("next: python3 scripts/cms.py rebuild")
    return 0


if __name__ == "__main__":
    sys.exit(main())
