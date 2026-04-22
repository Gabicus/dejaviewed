#!/usr/bin/env python3
"""Re-render the per-collection static pages (ai1..ai5, quant, art-*).

Each page has a line `<script>const POSTS=[...];</script>` near the top of
the body script block. This tool rewrites that single line with fresh data
derived from `site/catalog.json`, filtered by collection slug.

The rest of the page (layout, filter chrome, handlers) is preserved as-is —
this is an incremental migration, not a rewrite. The unified shared.js +
shared.css migration lives in Task #20 and happens later.

Mapping catalog → legacy POSTS schema handled in `to_legacy()`.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
CATALOG = SITE / "catalog.json"

# Collections this tool knows how to render. `file` is relative to site/.
COLLECTIONS = [
    ("ai1",             "ai1.html"),
    ("ai2",             "ai2.html"),
    ("ai3",             "ai3.html"),
    ("ai4",             "ai4.html"),
    ("ai5",             "ai5.html"),
    ("quant",           "quant.html"),
    ("art-inspiration", "art-inspiration.html"),
    ("art-i-like",      "art-i-like.html"),
]

# Regex: matches `<script>const POSTS=[...];` spanning a single line (the
# legacy pages emit the entire array on one line) OR a multi-line block.
POSTS_RE = re.compile(r"const\s+POSTS\s*=\s*\[.*?\]\s*;", re.DOTALL)


def to_legacy(e: dict) -> dict:
    """Map catalog.json entry shape to the per-page POSTS shape."""
    type_to_categories = {
        "repo": ["repo", "tool"],
        "tool": ["tool"],
        "tutorial": ["guide"],
        "guide": ["guide"],
        "skill": ["skill"],
        "platform": ["platform"],
        "resource": ["resource"],
    }
    return {
        "post_url": e.get("url"),
        "creator": e.get("creator"),
        "collection": e.get("collection"),
        "date": e.get("date"),
        "media_type": e.get("media_type") or "image",
        "caption_original": e.get("caption") or "",
        "summary": e.get("summary") or "",
        "type": e.get("type"),
        "domains": e.get("domains") or [],
        "audience": e.get("audience") or "intermediate",
        "medium": e.get("medium") or ("code" if e.get("type") in {"repo", "tool"} else "text"),
        "tools_mentioned": e.get("tools") or [],
        "repos_or_projects_mentioned": e.get("repos") or [],
        "models_mentioned": e.get("models") or [],
        "techniques_mentioned": e.get("techniques") or [],
        "key_takeaways": e.get("takeaways") or [],
        "deep_dive_candidate": bool(e.get("has_guide")),
        "deep_dive_topic": e.get("deep_dive") or "",
        "card_title": e.get("title") or e.get("id") or "",
        "drop": False,
        "links": e.get("links") or [],
        "tier": (e.get("tier") or "C").upper(),
        "guide_slug": e.get("deep_dive") or "" if e.get("has_guide") else "",
        "categories": type_to_categories.get(e.get("type") or "", [e.get("type") or "resource"]),
    }


def render_one(slug: str, page_name: str, entries: list[dict]) -> bool:
    page = SITE / page_name
    if not page.exists():
        print(f"[render] skip {page_name} (page not present)")
        return False

    subset = [to_legacy(e) for e in entries if e.get("collection") == slug]
    if not subset:
        print(f"[render] skip {page_name} (0 entries for {slug!r})")
        return False

    src = page.read_text(encoding="utf-8")
    posts_json = json.dumps(subset, ensure_ascii=False, separators=(",", ":"))
    replacement = f"const POSTS={posts_json};"

    new, n = POSTS_RE.subn(replacement, src, count=1)
    if n == 0:
        print(f"[render] warn: {page_name} has no POSTS block — skipped")
        return False

    if new == src:
        print(f"[render] {page_name} unchanged ({len(subset)} entries)")
        return True

    page.write_text(new, encoding="utf-8")
    print(f"[render] wrote {page_name} ({len(subset)} entries, {len(new):,} bytes)")
    return True


def main() -> int:
    if not CATALOG.exists():
        print(f"[render] error: {CATALOG} not found", file=sys.stderr)
        return 1

    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    entries = catalog.get("entries") or []
    print(f"[render] loaded {len(entries)} entries from catalog.json")

    touched = 0
    for slug, page in COLLECTIONS:
        if render_one(slug, page, entries):
            touched += 1
    print(f"[render] done: {touched} pages updated")
    return 0


if __name__ == "__main__":
    sys.exit(main())
