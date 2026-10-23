#!/usr/bin/env python3
"""Normalize internal links to root-absolute clean URLs + inject a static site nav.

Cloudflare Pages 308-redirects /x.html -> /x and /dir/index.html -> /dir/, so every
internal `href="../catalog.html"` costs crawlers a redirect hop. This post-processor
rewrites the href of every static <a> in site/ HTML to the URL Cloudflare actually serves:

    ../catalog.html          -> /catalog          index.html (root)   -> /
    ../e/DXYSxNLpIAY.html    -> /e/DXYSxNLpIAY    e/index.html        -> /e/
    /guides/x.html?y#z       -> /guides/x?y#z     ../guides/          -> /guides/
    ../feed.xml              -> /feed.xml         (existing non-HTML files: root-absolute only)

Only links whose target exists on disk are rewritten (a broken link stays visibly broken for
check_links.py). Never touched: external URLs, mailto:/tel:/data:/javascript:, pure #/?
links, templated hrefs (${...}), src= attributes, anything that is not an <a> tag, and
everything inside <script>, <style>, <pre>, <code>, <textarea>, HTML comments, and the
generated <!-- seo:* -->, <!-- monetize:* --> and <!-- monetize-prompts:* --> blocks (those
generators own their markup and must stay idempotent). Markdown guide sources live in
<script id="md" type="text/markdown"> and are therefore untouched; a server-rendered
#guide-body is plain HTML and is normalized.

It also strips-then-inserts one static, crawlable footer nav on every public page:
    <!-- sitenav:start --><nav class="sitenav" aria-label="Site">...</nav><!-- sitenav:end -->
placed before the monetize footer (or </body>), so build_monetize.py's own
strip-then-insert before </body> keeps producing the same bytes.

Idempotent. Run it LAST among HTML-touching steps (after seo + monetize).

Usage:
  python3 scripts/normalize_links.py            # apply
  python3 scripts/normalize_links.py --check    # dry run; exit 1 if any file would change
"""
from __future__ import annotations

import argparse
import posixpath
import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
SITE_HOST = "dejaviewed.dev"

# directories never processed (framework exports / search index / superseded pages /
# standalone presentation apps with their own relative structure)
SKIP_DIRS = {"legacy", "about", "pagefind", "ai_presentation", "doetug", "og", "thumb", "api"}
# processed for links but no static nav (private pages)
NO_NAV = {"admin.html", "rate.html"}

NAV_START, NAV_END = "<!-- sitenav:start -->", "<!-- sitenav:end -->"
NAV_RE = re.compile(re.escape(NAV_START) + r".*?" + re.escape(NAV_END) + r"\n?", re.S)

NAV_LINKS = [
    ("/", "Home"), ("/start-here", "Start here"), ("/catalog", "Catalog"),
    ("/guides/", "Guides"), ("/prompts", "Prompts"), ("/e/", "All entries"),
    ("/collections/", "Collections"), ("/search", "Search"), ("/graph", "Graph"),
    ("/graph-cosmos", "Cosmos"), ("/board", "Board"), ("/links/", "Links"),
    ("/method", "How it works"), ("/feed.xml", "RSS"), ("/llms.txt", "llms.txt"),
]
NAV_CSS = (".sitenav{max-width:1100px;margin:28px auto 0;padding:14px 16px 6px;border-top:1px solid "
           "var(--border,rgba(255,255,255,.08));text-align:center;font:400 11px/2 'JetBrains Mono',"
           "ui-monospace,monospace;letter-spacing:.02em;color:var(--text-mute,#6a6a80)}"
           ".sitenav a{color:var(--text-mute,#6a6a80);text-decoration:none;margin:0 7px;white-space:nowrap}"
           ".sitenav a:hover{color:var(--accent,#a78bfa)}")

# Protected regions are consumed whole by the scanner; <a ...> tags outside them get rewritten.
SCAN_RE = re.compile(
    r"<!--\s*(seo|monetize|monetize-prompts|sitenav):start\s*-->.*?<!--\s*\1:end\s*-->"
    r"|<!--.*?-->"
    r"|<(script|style|pre|code|textarea)\b[^>]*>.*?</\2\s*>"
    r"|<a\b[^>]*>",
    re.S | re.I)
HREF_RE = re.compile(r"""(\shref\s*=\s*)(?:"([^"]*)"|'([^']*)'|([^\s>"']+))""", re.I)
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


def nav_html(active: str = "") -> str:
    links = "".join(f'<a href="{h}"' + (' aria-current="page"' if h == active else "") + f">{t}</a>"
                    for h, t in NAV_LINKS)
    return (f'{NAV_START}<nav class="sitenav" aria-label="Site" data-pagefind-ignore>'
            f"<style>{NAV_CSS}</style>{links}</nav>{NAV_END}\n")


def clean_url(rel_page: str, href: str) -> str | None:
    """Clean root-absolute replacement for an internal href, or None to leave it alone."""
    raw = href.strip()
    if not raw or raw[0] in "#?" or "${" in raw or "{{" in raw:
        return None
    if raw.startswith("//") or SCHEME_RE.match(raw):
        sp = urlsplit(raw)
        if sp.scheme not in ("http", "https", "") or sp.netloc.lower().removeprefix("www.") != SITE_HOST:
            return None
        raw = raw[raw.find(sp.netloc) + len(sp.netloc):] or "/"
    cut = min([i for i in (raw.find("?"), raw.find("#")) if i >= 0], default=len(raw))
    path, tail = raw[:cut], raw[cut:]
    if not path:
        return None
    trailing = path.endswith("/")
    if path.startswith("/"):
        ab = posixpath.normpath(path)
    else:
        ab = posixpath.normpath(posixpath.join("/" + posixpath.dirname(rel_page), path))
    if ab.startswith("//"):
        ab = "/" + ab.lstrip("/")
    if not ab.startswith("/") or ab.startswith("/.."):
        return None
    disk = SITE / unquote(ab).lstrip("/")
    name = ab.rsplit("/", 1)[-1]
    if ab == "/" or trailing or disk.is_dir():
        if not (disk / "index.html").is_file():
            return None
        out = "/" if ab == "/" else ab.rstrip("/") + "/"
    elif name == "index.html":
        if not disk.is_file():
            return None
        out = ab[: -len("index.html")] or "/"
    elif name.endswith(".html"):
        if not disk.is_file():
            return None
        out = ab[: -len(".html")]
    elif "." not in name:
        if disk.with_name(disk.name + ".html").is_file():
            out = ab
        elif (disk / "index.html").is_file():
            out = ab + "/"
        else:
            return None
    else:  # other existing file (feed.xml, llms.txt, api/*.json): root-absolute, path unchanged
        if not disk.is_file():
            return None
        out = ab
    return out + tail


def rewrite_links(rel_page: str, text: str, stats: dict) -> str:
    out, pos = [], 0
    for m in SCAN_RE.finditer(text):
        tag = m.group(0)
        if not tag[:2].lower() == "<a":
            continue

        def fix(hm):
            val = hm.group(2) if hm.group(2) is not None else (hm.group(3) if hm.group(3) is not None else hm.group(4))
            new = clean_url(rel_page, val)
            if new is None or new == val:
                return hm.group(0)
            stats["rewritten"] += 1
            q = "'" if hm.group(3) is not None else '"'
            return f"{hm.group(1)}{q}{new}{q}"

        new_tag = HREF_RE.sub(fix, tag, count=1)
        if new_tag != tag:
            out.append(text[pos:m.start()])
            out.append(new_tag)
            pos = m.end()
    out.append(text[pos:])
    return "".join(out)


def page_url(rel: str) -> str:
    if rel == "index.html":
        return "/"
    if rel.endswith("/index.html"):
        return "/" + rel[: -len("index.html")]
    return "/" + rel[: -len(".html")]


def add_nav(rel: str, text: str) -> str:
    text = NAV_RE.sub("", text)
    if rel in NO_NAV:
        return text
    low = text.lower()
    i = low.rfind("</body>")
    if i < 0:
        return text
    j = text.rfind("<!-- monetize:start -->", 0, i)
    # sit right before the monetize footer when it's the last thing before </body>
    if j >= 0 and text[j:i].rstrip().endswith("<!-- monetize:end -->"):
        i = j
    return text[:i] + nav_html(page_url(rel)) + text[i:]


def pages() -> list[Path]:
    out = []
    for p in sorted(SITE.rglob("*.html")):
        rel = p.relative_to(SITE)
        if rel.parts[0] in SKIP_DIRS:
            continue
        out.append(p)
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="dry run; exit 1 if anything would change")
    args = ap.parse_args()
    stats = {"rewritten": 0}
    changed, navved = [], 0
    for p in pages():
        rel = str(p.relative_to(SITE))
        orig = p.read_bytes().decode("utf-8", errors="replace")
        text = add_nav(rel, rewrite_links(rel, orig, stats))
        if NAV_START in text:
            navved += 1
        if text != orig:
            changed.append(rel)
            if not args.check:
                p.write_bytes(text.encode("utf-8"))
    verb = "would change" if args.check else "changed"
    print(f"[normalize_links] {len(pages())} pages scanned, {stats['rewritten']} hrefs rewritten, "
          f"{navved} pages with static nav, {verb} {len(changed)} file(s)"
          + (f": {changed[:8]}" if args.check and changed else ""))
    return 1 if (args.check and changed) else 0


if __name__ == "__main__":
    sys.exit(main())
