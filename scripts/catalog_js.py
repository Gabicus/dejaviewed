#!/usr/bin/env python3
"""Emit site/catalog.js and site/summaries.js for file:// previews.

Wraps the JSON blobs in `window.__CATALOG` / `window.__SUMMARIES` /
`window.__RECOMMENDATIONS` so pages work when opened directly from disk
(fetch() is blocked on file:// in most browsers). Pages check window.__X
first, fall back to fetch().
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

PAIRS = [
    (SITE / "catalog.json",         SITE / "catalog.js",         "__CATALOG"),
    (SITE / "summaries.json",       SITE / "summaries.js",       "__SUMMARIES"),
    (SITE / "recommendations.json", SITE / "recommendations.js", "__RECOMMENDATIONS"),
]


def wrap(src: Path, dst: Path, var: str) -> None:
    if not src.exists():
        print(f"[catalog_js] skip {src.name} (missing)")
        return
    data = json.loads(src.read_text(encoding="utf-8"))
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    banner = f"// Auto-generated from {src.name} for file:// previews. Do not edit by hand.\n"
    dst.write_text(banner + f"window.{var} = {body};\n", encoding="utf-8")
    print(f"[catalog_js] wrote {dst.relative_to(ROOT)} ({dst.stat().st_size:,} bytes)")


def main() -> int:
    for src, dst, var in PAIRS:
        wrap(src, dst, var)
    return 0


if __name__ == "__main__":
    sys.exit(main())
