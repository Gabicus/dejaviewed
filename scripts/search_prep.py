#!/usr/bin/env python3
"""Mark guide + deeper pages for Pagefind indexing. Idempotent; run before pagefind.

Pagefind only indexes pages that carry a `data-pagefind-body` region (once any
page does), so everything not marked here or by render_entries.py — admin,
board, graphs, legacy/, e/index.html, guides/index.html — stays out of the index.

  guides/*.html with <script id="md" type="text/markdown">
      The visible body is rendered client-side, which Pagefind never sees. We
      render the markdown to plain static HTML at build time into a visually
      clipped, aria-hidden `.sr-index` div (between marker comments, replaced
      on every run). No markdown dependency: the copy only has to be indexable.
  guides/*.html without markdown (hand-written)  -> first <article> gets the attrs
  deeper/*.html                                  -> <main class="deeper-wrap"> gets the attrs
"""
from __future__ import annotations

import html
import re
import sys
from pathlib import Path

SITE = Path(__file__).resolve().parent.parent / "site"
START, END = "<!--pagefind:start-->", "<!--pagefind:end-->"
MD_RE = re.compile(r'<script id="md" type="text/markdown">(.*?)</script>', re.S)
BLOCK_RE = re.compile(re.escape(START) + r".*?" + re.escape(END) + r"\n?", re.S)
CLIP = ("position:absolute;width:1px;height:1px;margin:-1px;padding:0;border:0;"
        "overflow:hidden;clip:rect(0 0 0 0);clip-path:inset(50%);white-space:nowrap")


def inline(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", text)                       # raw HTML in markdown
    text = re.sub(r"!\[([^\]]*)\]\([^)]*\)", r"\1", text)      # images -> alt
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)       # links -> label
    text = re.sub(r"(\*\*|__|\*|`)", "", text)
    text = text.replace("|", " ")
    return html.escape(" ".join(text.split()), quote=False)


def md_to_html(md: str) -> str:
    out, para = [], []

    def flush():
        if para:
            t = inline(" ".join(para))
            if t.strip("- "):
                out.append(f"<p>{t}</p>")
            para.clear()

    for line in md.splitlines():
        s = line.strip()
        m = re.match(r"(#{1,6})\s+(.*)", s)
        if m:
            flush()
            n = len(m.group(1))
            out.append(f"<h{n}>{inline(m.group(2))}</h{n}>")
        elif not s or s.startswith("```") or re.fullmatch(r"[-*_|: ]{3,}", s):
            flush()
        elif re.match(r"([-*+]|\d+\.)\s+", s):
            flush()
            para.append(re.sub(r"^([-*+]|\d+\.)\s+", "", s))
            flush()
        else:
            para.append(s.lstrip("> "))
    flush()
    return "\n".join(out)


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
    page = p.read_text(encoding="utf-8")
    page = BLOCK_RE.sub("", page)
    m = MD_RE.search(page)
    if m:
        block = (f'{START}<div class="sr-index" aria-hidden="true" data-pagefind-body '
                 f'data-pagefind-filter="kind:Guide" style="{CLIP}">\n'
                 f'{md_to_html(html.unescape(m.group(1)))}\n</div>{END}\n')
        page = page[:m.start()] + block + page[m.start():]
        status = "md"
    else:
        if not re.search(r"<html\b", page, re.I):
            # Hand-written fragment pages: Pagefind skips documents without <html>.
            # No doctype added on purpose — keeps their current (quirks-mode) rendering.
            page = ('<html lang="en">\n<meta charset="utf-8">\n' + page.rstrip("\n") + "\n</html>\n")
        new = mark_tag(page, r"<article\b[^>]*>", "Guide")
        if new is None:
            return "skip (no <article>)"
        page, status = new, "static"
    p.write_text(page, encoding="utf-8")
    return status


def main() -> int:
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
