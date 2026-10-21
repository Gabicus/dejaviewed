#!/usr/bin/env python3
"""Export entries for LLM enrichment in batches, and merge the results back.

Export:
    python3 scripts/llm_enrich_batches.py export --since 2026-10-21 --size 25
        -> data/llm_batches/batch_NN.json  (input: id, post_id, collection, creator,
           caption, transcript, ocr, current heuristic fields)
Merge:
    python3 scripts/llm_enrich_batches.py merge data/llm_batches/out_*.json
        -> applies title/summary/tier/type/tags/domains/tools/techniques/models/
           repos/takeaways to parquet via cms upsert semantics, sets last_edited_at.

Output file schema (one object per entry):
  {"id": "...", "title": "Subject — angle", "summary": "1-3 sentences",
   "tier": "S|A|B|C", "type": "technique|tool|repo|guide|platform|resource|art|design|uiux|skill",
   "tags": [...], "domains": [...], "tools": [...], "techniques": [...],
   "models": [...], "repos": [...], "takeaways": [...], "links": [...],
   "drop": false, "drop_reason": ""}
"""
import argparse
import glob
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from cms import load_entries, write_entries, write_crosslinks, compute_crosslinks, _write_catalog_exports  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "llm_batches"
FIELDS = ["title", "summary", "tier", "type", "tags", "domains", "tools",
          "techniques", "models", "repos", "takeaways"]
LIST_FIELDS = {"tags", "domains", "tools", "techniques", "models", "repos", "takeaways"}


def cmd_export(a):
    rows = load_entries()
    if a.ids:
        want = set(open(a.ids).read().split())
        rows = [r for r in rows if r.get("id") in want or r.get("post_id") in want]
    elif a.since:
        rows = [r for r in rows if (r.get("last_scraped_at") or "") >= a.since]
    ocr = {}
    p = ROOT / "data" / "slides_ocr.json"
    if p.exists():
        ocr = json.load(open(p))
    OUT.mkdir(exist_ok=True)
    for f in OUT.glob("batch_*.json"):
        f.unlink()
    for n, i in enumerate(range(0, len(rows), a.size), 1):
        batch = []
        for r in rows[i:i + a.size]:
            batch.append({
                "id": r["id"], "post_id": r.get("post_id"), "url": r.get("url"),
                "collection": r.get("source_collection"), "creator": r.get("creator"),
                "date": r.get("date"), "media_type": r.get("media_type"),
                "caption": r.get("caption") or "", "transcript": r.get("transcript") or "",
                "ocr": ocr.get(r.get("post_id") or "", ""),
                "heuristic": {k: r.get(k) for k in FIELDS},
            })
        json.dump(batch, open(OUT / f"batch_{n:02d}.json", "w"), indent=1)
    print(f"[export] {len(rows)} entries -> {n} batches in {OUT}")


def cmd_merge(a):
    rows = load_entries()
    by_id = {r["id"]: r for r in rows}
    now = datetime.now().replace(microsecond=0).isoformat(timespec="seconds")
    n_ok = n_drop = n_miss = 0
    for path in a.files:
        for o in json.load(open(path)):
            r = by_id.get(o.get("id"))
            if not r:
                n_miss += 1
                continue
            if o.get("drop"):
                r["tier"] = "C"
                r["user_notes"] = f"LLM drop candidate: {o.get('drop_reason','')}"
                n_drop += 1
            for k in FIELDS:
                v = o.get(k)
                if v in (None, "", []):
                    continue
                if k in LIST_FIELDS:
                    merged = sorted(set((r.get(k) or []) + [str(x) for x in v]))
                    r[k] = merged
                else:
                    r[k] = str(v)
            if o.get("links"):
                r["takeaways"] = sorted(set((r.get("takeaways") or []) + [f"link: {u}" for u in o["links"]]))
            r["last_edited_at"] = now
            r["is_new"] = False
            n_ok += 1
    write_entries(rows)
    write_crosslinks(compute_crosslinks(rows))
    _write_catalog_exports(rows)
    print(f"[merge] applied={n_ok} drops={n_drop} missing_ids={n_miss}")


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export")
    e.add_argument("--since", help="last_scraped_at >= this ISO date")
    e.add_argument("--ids", help="file of ids/post_ids, whitespace separated")
    e.add_argument("--size", type=int, default=25)
    m = sub.add_parser("merge")
    m.add_argument("files", nargs="+")
    a = p.parse_args()
    if a.cmd == "export":
        cmd_export(a)
    else:
        a.files = [f for pat in a.files for f in sorted(glob.glob(pat))]
        cmd_merge(a)


if __name__ == "__main__":
    main()
