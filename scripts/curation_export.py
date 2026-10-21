#!/usr/bin/env python3
"""Export a compact catalog digest + existing curated dives for the researcher curation pass.

    python3 scripts/curation_export.py
      -> data/curation/catalog_digest.json   (one compact object per entry)
      -> data/curation/existing_dives.json   (id, title, class, thesis, entry_ids)
"""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "curation"


def _l(v):
    try:
        return [str(x) for x in list(v)] if v is not None else []
    except TypeError:
        return []


def main():
    OUT.mkdir(exist_ok=True)
    df = pd.read_parquet(ROOT / "data" / "entries.parquet")
    df = df[~df.title.fillna("").str.contains(r"\[NEEDS ENRICHMENT\]")]
    rows = []
    for _, r in df.iterrows():
        rows.append({
            "id": r["id"], "title": r.get("title") or "", "summary": (r.get("summary") or "")[:400],
            "tier": r.get("tier"), "type": r.get("type"), "collection": r.get("source_collection"),
            "creator": r.get("creator"), "date": (r.get("date") or "")[:10],
            "tools": _l(r.get("tools")), "techniques": _l(r.get("techniques")),
            "domains": _l(r.get("domains")), "models": _l(r.get("models")),
            "takeaways": _l(r.get("takeaways"))[:4],
        })
    json.dump(rows, open(OUT / "catalog_digest.json", "w"), indent=0, ensure_ascii=False)
    m = json.load(open(ROOT / "data" / "manual_dives.json"))["manual_dives"]
    ex = [{k: d.get(k) for k in ("id", "title", "class", "thesis", "entry_ids")} for d in m]
    json.dump(ex, open(OUT / "existing_dives.json", "w"), indent=1, ensure_ascii=False)
    print(f"[curation] {len(rows)} entries, {len(ex)} existing curated dives -> {OUT}")


if __name__ == "__main__":
    main()
