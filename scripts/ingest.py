#!/usr/bin/env python3
"""DejaViewed ingestion CLI.

Reads URLs from stdin, a file, or args; dedupes against the parquet store
(scripts/cms.py); scrapes new ones; upserts rows; recomputes crosslinks.

Usage:
  python scripts/ingest.py --urls-file urls.txt --collection ai5
  echo https://instagram.com/p/X/ | python scripts/ingest.py --collection ai5
  python scripts/ingest.py --url https://... --collection quant

If Instagram cookies / scraper config are missing, prompts for them rather
than failing. Scraped fields are minimal (url + post_id + source_collection);
enrichment (tier/type/domains) is queued as TODO rows in user_notes, ready
for manual admin editing or an LLM pass later.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from cms import (  # noqa: E402
    SCHEMA, load_entries, write_entries, write_crosslinks, compute_crosslinks,
    entry_from_catalog, has_entry, upsert, derive_post_id, stable_id,
    _write_catalog_exports,
)

CONFIG_PATH = ROOT / "data" / "ingest.config.json"


def _prompt(msg: str, default: str = "") -> str:
    v = input(f"{msg}{f' [{default}]' if default else ''}: ").strip()
    return v or default


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def save_config(cfg: dict) -> None:
    CONFIG_PATH.parent.mkdir(exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def ensure_scraper_config(cfg: dict, interactive: bool) -> dict:
    """Fill in missing scraper-config keys by prompting. Keys are platform-
    specific; we record what we have so future runs don't re-ask."""
    changed = False
    if not cfg.get("ig_session_id") and interactive:
        print("\n[ingest] Instagram session cookie not set.")
        print("  (Open instagram.com in a logged-in browser, copy the "
              "'sessionid' cookie value. Leave blank to skip IG scraping.)")
        v = _prompt("ig_session_id")
        if v:
            cfg["ig_session_id"] = v
            changed = True
    if changed:
        save_config(cfg)
    return cfg


def scrape_url(url: str, cfg: dict) -> dict | None:
    """Platform-router. Returns a raw entry dict or None on failure.

    Creates a minimal placeholder entry from the URL. Real metadata comes from
    either Playwright scraping (process_raw.py path) or enrichment passes.
    The entry is marked [NEEDS ENRICHMENT] so it's obvious in the admin UI.
    """
    post_id = derive_post_id(url) or ""
    print(f"  [ingest] No scraper configured for {url} — creating placeholder entry",
          file=sys.stderr)
    return {
        "url": url,
        "post_id": post_id,
        "title": f"[NEEDS ENRICHMENT] {post_id or url[:60]}",
        "caption": "",
        "summary": "",
        "creator": "",
        "date": "",
        "tier": "C",
        "type": "resource",
        "media_type": "image",
        "user_notes": "Auto-ingested placeholder — run enrichment or edit via admin UI",
        "domains": [], "tools": [], "techniques": [],
        "models": [], "repos": [], "takeaways": [],
        "has_guide": False, "deep_dive": "",
    }


def ingest_one(url: str, collection: str, rows: list[dict],
               cfg: dict) -> tuple[list[dict], str]:
    """Returns (rows, action) where action ∈ {skipped-duplicate, merged-collection,
    scraped-new, scrape-failed}."""
    existing = has_entry(rows, url, derive_post_id(url))
    if existing:
        # Already scraped before — just record the new collection membership.
        existing_cols = set(existing.get("collections") or [])
        if collection and collection not in existing_cols:
            existing_cols.add(collection)
            existing["collections"] = sorted(existing_cols)
            for i, r in enumerate(rows):
                if r["id"] == existing["id"]:
                    rows[i] = existing
                    break
            return rows, "merged-collection"
        return rows, "skipped-duplicate"
    raw = scrape_url(url, cfg)
    if not raw:
        return rows, "scrape-failed"
    raw["collection"] = collection
    row = entry_from_catalog(raw)
    rows, _ = upsert(rows, row)
    return rows, "scraped-new"


def collect_urls(args) -> list[str]:
    urls: list[str] = []
    if args.url:
        urls.append(args.url)
    if args.urls_file:
        for line in Path(args.urls_file).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    if not sys.stdin.isatty():
        for line in sys.stdin:
            line = line.strip()
            if line and not line.startswith("#"):
                urls.append(line)
    # Dedupe preserving order
    seen = set(); out = []
    for u in urls:
        if u not in seen:
            seen.add(u); out.append(u)
    return out


def main():
    p = argparse.ArgumentParser(prog="ingest")
    p.add_argument("--url", help="single URL to ingest")
    p.add_argument("--urls-file", help="path to file with one URL per line")
    p.add_argument("--collection", required=True,
                   help="bookmark folder name (ai1..ai5, quant, art-*, or a new slug)")
    p.add_argument("--non-interactive", action="store_true",
                   help="fail rather than prompt for missing config")
    args = p.parse_args()

    cfg = ensure_scraper_config(load_config(), interactive=not args.non_interactive)
    urls = collect_urls(args)
    if not urls:
        print("[ingest] no URLs provided (use --url, --urls-file, or stdin)",
              file=sys.stderr)
        return 1

    rows = load_entries()
    counts = {"skipped-duplicate": 0, "merged-collection": 0,
              "scraped-new": 0, "scrape-failed": 0}
    for u in urls:
        rows, action = ingest_one(u, args.collection, rows, cfg)
        counts[action] += 1
        tag = {"skipped-duplicate": "DUP", "merged-collection": "ADD-COL",
               "scraped-new": "NEW", "scrape-failed": "FAIL"}[action]
        print(f"  [{tag}] {u}")

    write_entries(rows)
    write_crosslinks(compute_crosslinks(rows))
    _write_catalog_exports(rows)
    print(f"\n[ingest] {counts['scraped-new']} new, "
          f"{counts['merged-collection']} added to '{args.collection}', "
          f"{counts['skipped-duplicate']} already present, "
          f"{counts['scrape-failed']} failed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
