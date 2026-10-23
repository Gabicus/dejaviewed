#!/usr/bin/env python3
"""Mark guide + deeper pages for Pagefind indexing. Idempotent; run before pagefind.

Pagefind only indexes pages that carry a `data-pagefind-body` region (once any
page does), so everything not marked here or by render_entries.py — admin,
board, graphs, legacy/, e/index.html, guides/index.html — stays out of the index.

  guides/*.html with <script id="md" type="text/markdown">
      #guide-body is server-rendered from the markdown (build_guides.rerender_all,
      called first here so the body is never stale — e.g. after build_monetize.py
      rewrote the markdown). #guide-body carries the pagefind attrs. Any legacy
      hidden `.sr-index` prerender block is removed.
  guides/*.html without markdown (hand-written)  -> first <article> gets the attrs
  deeper/*.html                                  -> <main class="deeper-wrap"> gets the attrs
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_guides import rerender_all  # noqa: E402

SITE = Path(__file__).resolve().parent.parent / "site"
START, END = "<!--pagefind:start-->", "<!--pagefind:end-->"
MD_RE = re.compile(r'<script id="md" type="text/markdown">(.*?)</script>', re.S)
BLOCK_RE = re.compile(re.escape(START) + r".*?" + re.escape(END) + r"\n?", re.S)


def mark_tag(page: str, tag_re: str, kind: str) -> str | None:
    m = re.search(tag_re, page)
    if not m:
        return None
    tag = m.group(0)
    if "data-pagefind-body" in tag:
        return page
    new = tag[:-1] + f' data-pagefind-body data-pagefind-filter="kind:{kind}">'
    return page[:m.start()] + new + page[m.end():]


def prep_guide(p: Path) -> str:
    orig = p.read_text(encoding="utf-8")
    page = BLOCK_RE.sub("", orig)               # legacy hidden prerender
    if MD_RE.search(page):
        new = mark_tag(page, r'<div id="guide-body"[^>]*>', "Guide")
        if new is None:
            return "skip (md but no #guide-body)"
        page, status = new, "md"
    else:
        if not re.search(r"<html\b", page, re.I):
            # Hand-written fragment pages: Pagefind skips documents without <html>.
            # No doctype added on purpose — keeps their current (quirks-mode) rendering.
            page = ('<html lang="en">\n<meta charset="utf-8">\n' + page.rstrip("\n") + "\n</html>\n")
        new = mark_tag(page, r"<article\b[^>]*>", "Guide")
        if new is None:
            return "skip (no <article>)"
        page, status = new, "static"
    if page != orig:
        p.write_text(page, encoding="utf-8")
    return status


def main() -> int:
    n_pages, n_changed = rerender_all()
    print(f"[search_prep] rendered #guide-body: {n_pages} pages ({n_changed} changed)")
    counts: dict[str, int] = {}
    for p in sorted((SITE / "guides").glob("*.html")):
        if p.name == "index.html":
            continue
        st = prep_guide(p)
        counts["guide " + st] = counts.get("guide " + st, 0) + 1
        if st.startswith("skip"):
            print(f"[search_prep] WARNING {p.name}: {st}", file=sys.stderr)
    for p in sorted((SITE / "deeper").glob("*.html")):
        page = p.read_text(encoding="utf-8")
        new = mark_tag(page, r'<main class="deeper-wrap"[^>]*>', "Deep dive")
        if new is None:
            print(f"[search_prep] WARNING {p.name}: no deeper-wrap main", file=sys.stderr)
            counts["deeper skip"] = counts.get("deeper skip", 0) + 1
            continue
        if new != page:
            p.write_text(new, encoding="utf-8")
        counts["deeper"] = counts.get("deeper", 0) + 1
    print("[search_prep] " + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
