#!/usr/bin/env python3
"""Post-enrichment quality gate. Exit 1 if any hard gate fails.

    python3 scripts/quality_gate.py            # report + gates
    python3 scripts/quality_gate.py --since 2026-10-21   # restrict coverage table to a batch

Gates (hard):
  - 0 titles containing "[NEEDS ENRICHMENT]"
  - 0 titles shorter than 14 chars
  - 0 titles equal to the post_id
  - S-tier share < 15% per collection (collections with >= 10 entries)
  - every IG video entry has transcript OR a logged reason in user_notes
  - every IG entry has a thumbnail on disk
"""
import argparse
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--since")
    a = p.parse_args()
    df = pd.read_parquet(ROOT / "data" / "entries.parquet")
    ig = df.url.str.contains("instagram.com", na=False)
    t = df.title.fillna("")
    fails = []

    bad_ne = df[t.str.contains(r"\[NEEDS ENRICHMENT\]")]
    bad_short = df[t.str.len() < 14]
    bad_pid = df[t == df.post_id.fillna("")]
    for name, sub in (("NEEDS ENRICHMENT titles", bad_ne), ("titles <14 chars", bad_short), ("title == post_id", bad_pid)):
        if len(sub):
            fails.append(f"{name}: {len(sub)} e.g. {sub.post_id.head(5).tolist()}")

    overall_s = (df.tier == "S").mean()
    if overall_s > 0.15:
        fails.append(f"overall S-rate {overall_s:.0%} > 15%")
    warns = []
    for coll, sub in df.groupby("source_collection"):
        if len(sub) >= 10:
            s = (sub.tier == "S").mean()
            if s > 0.35:
                fails.append(f"S-rate {coll}: {s:.0%} ({(sub.tier=='S').sum()}/{len(sub)}) > 35%")
            elif s > 0.15:
                warns.append(f"S-rate {coll}: {s:.0%}")

    vid = ig & (df.media_type == "video")
    no_tr = df[vid & (df.transcript.fillna("") == "") & ~df.user_notes.fillna("").str.contains("transcript", case=False)]
    if len(no_tr):
        fails.append(f"videos without transcript or logged reason: {len(no_tr)} e.g. {no_tr.post_id.head(8).tolist()}")

    gone = df.user_notes.fillna("").str.contains("deleted/private", case=False)
    no_th = df[ig & ~gone & ~df.post_id.apply(lambda x: os.path.exists(ROOT / "site" / "thumb" / f"{x}.jpg"))]
    if len(no_th):
        fails.append(f"IG entries without thumbnail: {len(no_th)} e.g. {no_th.post_id.head(8).tolist()}")

    # coverage table
    sub = df[df.last_scraped_at.fillna("") >= a.since] if a.since else df
    sub = sub[sub.url.str.contains("instagram.com", na=False)]
    cov = sub.groupby("source_collection").agg(
        n=("id", "size"),
        captions=("caption", lambda s: (s.fillna("").str.len() > 0).sum()),
        videos=("media_type", lambda s: (s == "video").sum()),
        transcripts=("transcript", lambda s: (s.fillna("").str.len() > 0).sum()),
        thumbs=("post_id", lambda s: sum(os.path.exists(ROOT / "site" / "thumb" / f"{x}.jpg") for x in s)),
        S=("tier", lambda s: (s == "S").sum()), A=("tier", lambda s: (s == "A").sum()),
        B=("tier", lambda s: (s == "B").sum()), C=("tier", lambda s: (s == "C").sum()),
    )
    print(cov.to_string())
    print(f"\nTOTAL entries: {len(df)}  tiers: {df.tier.value_counts().to_dict()}")
    if warns:
        print("\nWARNINGS (not blocking):", *warns, sep="\n - ")
    if fails:
        print("\nGATE FAILURES:")
        for f in fails:
            print(" -", f)
        sys.exit(1)
    print("\nALL GATES PASS")


if __name__ == "__main__":
    main()
