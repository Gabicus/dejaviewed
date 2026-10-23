#!/usr/bin/env python3
"""Generate full guide pages for curated deep dives + rebuild site/guides/index.html.

Usage:
    python3 scripts/build_guides.py [--dry-run] [--dive-id ID] [--force] [--no-index] [--out-dir DIR]
    python3 scripts/build_guides.py --rerender-only     # just re-render every #guide-body from its md

- Source of dives: data/deep_dives.json (curated = suggested_by == "curated" or pinned).
  Missing why_it_matters / prerequisites fall back to data/manual_dives.json (same ids).
- Entries come from site/catalog.json (matched on id or post_id).
- Slug = dive id minus 'dd-insight-' -> site/guides/<slug>.html.
- Existing pages are skipped unless --force (hand-written pages may be richer).
- Every run ends with rerender_all(): #guide-body is server-rendered from each page's md script
  (markdown-it). Re-run it (or search_prep.py, which calls it) after anything edits the md script.
- index.html is static HTML, so it is regenerated from the real set of *.html files
  in site/guides (plus pages this run would create) and the dive metadata.
- Read-only on data/*. Never writes data files.
"""
from __future__ import annotations

import argparse
import html
import posixpath
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
GUIDES = SITE / "guides"
DEEPER = SITE / "deeper"
DEEP_DIVES = ROOT / "data" / "deep_dives.json"
MANUAL_DIVES = ROOT / "data" / "manual_dives.json"
CATALOG = SITE / "catalog.json"

SLUG_PREFIX = "dd-insight-"
CURATOR = "6ab3"
sys.path.insert(0, str(Path(__file__).resolve().parent))
from prompt_systems import load_packs, section_markdown, PS_CSS, GUIDE_COPY_JS  # noqa: E402
from markdown_it import MarkdownIt  # noqa: E402
from markdown_it.token import Token  # noqa: E402
PACKS = load_packs()

# Featured guides pinned to the top of the index (pink FEATURED card).
FEATURED = {
    "claude-mastery": (
        "From first install to advanced agent architecture — the definitive Claude reference. "
        "9 sections, 50+ sourced entries, model timeline, living document."
    ),
}

# --------------------------------------------------------------------------- guide page template
# Head/style copied verbatim from the curated-template pages (e.g. agent-architecture.html).
PAGE_HEAD = """<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title} · DejaViewed</title>
<link rel="stylesheet" href="../shared.css">
<script src="../shared.js"></script>
<style>
.chip.guide{{color:var(--c-guide);border-color:rgba(167,139,250,.28)}}
.chip.platform{{color:var(--c-platform);border-color:rgba(224,208,64,.28)}}
.chip.resource{{color:var(--c-resource);border-color:rgba(64,208,224,.28)}}
.card .actions{{display:flex;gap:8px;margin-top:14px;padding-top:14px;border-top:1px solid var(--border)}}
.btn{{flex:1;text-align:center;padding:8px 12px;border-radius:8px;font-size:12px;font-weight:700;border:1px solid var(--border);background:var(--panel);color:var(--text);transition:all .15s}}
.btn:hover{{background:var(--panel-2);border-color:var(--border-hi);color:#fff}}
.btn.primary{{background:linear-gradient(135deg,rgba(167,139,250,.2),rgba(244,114,182,.2));border-color:rgba(167,139,250,.4);color:#fff}}
.btn.primary:hover{{background:linear-gradient(135deg,rgba(167,139,250,.3),rgba(244,114,182,.3))}}
footer.site{{margin:60px 0 40px;padding-top:30px;border-top:1px solid var(--border);color:var(--text-mute);font-size:12.5px;text-align:center}}
footer.site a{{color:var(--text-dim)}}
footer.site code{{background:rgba(0,0,0,.5);border:1px solid var(--border);padding:2px 7px;border-radius:5px;color:var(--accent);font-family:'JetBrains Mono',Menlo,monospace;font-size:11.5px}}
.guide{{max-width:780px;margin:30px auto;padding:0 22px;font-size:16px;line-height:1.75}}
.guide h1,.guide h2,.guide h3{{letter-spacing:-0.015em;margin-top:1.7em}}
.guide h1{{font-size:34px;font-weight:900;margin-top:0;letter-spacing:-0.02em;background:linear-gradient(135deg,#fff 0%,#a78bfa 50%,#f472b6 100%);-webkit-background-clip:text;background-clip:text;color:transparent}}
.guide h2{{font-size:24px;color:var(--text);border-bottom:1px solid var(--border);padding-bottom:6px}}
.guide h3{{font-size:18px;color:#fff}}.guide p{{color:var(--text)}}
.guide code{{background:rgba(255,255,255,.07);padding:2px 6px;border-radius:4px;font-family:'JetBrains Mono',Menlo,monospace;font-size:.9em;color:var(--accent)}}
.guide pre{{background:rgba(0,0,0,.55);border:1px solid var(--border);padding:16px;border-radius:var(--radius-sm);overflow-x:auto}}
.guide pre code{{background:none;padding:0;color:var(--text)}}
.guide blockquote{{border-left:3px solid var(--accent);padding-left:16px;color:var(--text-dim);margin:16px 0}}
.guide a{{color:var(--accent);text-decoration:underline;text-decoration-color:rgba(167,139,250,.3)}}
.guide a:hover{{text-decoration-color:var(--accent)}}
.guide hr{{border:none;border-top:1px solid var(--border);margin:30px 0}}
.guide ul,.guide ol{{padding-left:24px}}
.confidence-badge{{display:inline-block;padding:4px 10px;border-radius:6px;font-size:11px;font-weight:900;text-transform:uppercase;letter-spacing:.08em;margin-bottom:18px}}
.confidence-badge.high{{background:rgba(76,218,140,.12);color:var(--c-repo);border:1px solid rgba(76,218,140,.4)}}
.confidence-badge.medium{{background:rgba(240,160,80,.12);color:var(--c-tool);border:1px solid rgba(240,160,80,.4)}}
@media(max-width:900px){{
  .layout{{grid-template-columns:1fr}}
  .sidebar{{position:relative;top:0;max-height:none}}
  .nav{{gap:4px}}
  .nav a{{padding:6px 10px;font-size:11px}}}}
</style></head><body>
<script>DV.mountHeader(document.body, 'home');</script>
<article class="guide">
  <div class="confidence-badge {confidence}">Source confidence: {confidence}</div>
{cross_link}  <div id="guide-body" data-pagefind-body data-pagefind-filter="kind:Guide"><!-- body:start --><!-- body:end --></div>
{entries_nav}</article>
<footer class="site"><div class="wrap"><a href="/">← Back to DejaViewed</a> · curated by <a href="https://instagram.com/{curator}">@{curator}</a> · <code>dejaviewed</code></div></footer>
<script id="md" type="text/markdown">"""

# The markdown block above is the editing surface; #guide-body is rendered from it at build time
# (render_guide_html / rerender_all). No client-side markdown renderer.
PAGE_TAIL = """</script>
<style>""" + PS_CSS + "</style>" + GUIDE_COPY_JS + "</body></html>"

# Same markup the hand-written pages use for the deeper-dive cross-link.
CROSS_LINK = (
    '<div class="cross-link" style="margin:1.5rem 0;padding:12px 16px;background:rgba(251,191,36,0.06);'
    'border:1px solid rgba(251,191,36,0.2);border-radius:8px;font-size:0.9rem;">'
    '<strong style="color:#fbbf24;">See also:</strong> '
    '<a href="/deeper/{file}" style="color:#fbbf24;text-decoration:none;font-weight:600;">'
    'Deeper Dive — {title} →</a></div>\n'
)


# --------------------------------------------------------------------------- server-side markdown render
# Every guide page keeps its markdown in <script id="md" type="text/markdown"> (edited by apply_answers,
# prompt_systems.inject_guide, build_monetize.link_guide_md; read by build_seo). #guide-body holds the
# HTML rendered from it, between BODY_START/BODY_END, regenerated by rerender_all() — idempotent.
BODY_START, BODY_END = "<!-- body:start -->", "<!-- body:end -->"
GUIDE_BODY_OPEN = '<div id="guide-body" data-pagefind-body data-pagefind-filter="kind:Guide">'
MD_SRC_RE = re.compile(r'<script id="md" type="text/markdown">(.*?)</script>', re.S)
BODY_REGION_RE = re.compile(re.escape(BODY_START) + r".*?" + re.escape(BODY_END), re.S)
EMPTY_BODY_RE = re.compile(r'<div id="guide-body"[^>]*>\s*</div>')
# Legacy client-side renderer + hidden search prerender, removed on migration.
LEGACY_RENDER_RE = re.compile(
    r'\n?<script src="https://cdn\.jsdelivr\.net/npm/marked/marked\.min\.js"></script>\n?'
    r'<script src="https://cdn\.jsdelivr\.net/npm/dompurify@3/dist/purify\.min\.js"></script>\n?'
    r"<script>\nconst raw=document\.getElementById\('md'\)\.textContent;\n.*?</script>", re.S)
LEGACY_WRAP_RE = re.compile(r"<script>\ndocument\.querySelectorAll\('#guide-body h2'\).*?</script>", re.S)
LEGACY_SR_RE = re.compile(r"<!--pagefind:start-->.*?<!--pagefind:end-->\n?", re.S)

# Raw HTML in guide markdown is escaped, except: HTML comments (dropped) and the /go/ tool links that
# build_monetize.py writes into the markdown. Those are re-emitted in a normalised attribute order
# (href first) so build_monetize.strip_links — which matches `<a class="go" href=` — leaves the
# rendered body alone; the markdown copy stays its single source.
GO_OPEN_RE = re.compile(r'<a class="go" href="(/go/[a-z0-9][a-z0-9-]*)" rel="([a-z ]+)">\Z')
SUP_OPEN = '<sup class="aff">'
COMMENT_RE = re.compile(r"\s*(<!--.*?-->\s*)+\Z", re.S)
AUTOLINK_RE = re.compile(r"https?://[^\s<>\"'`]+")
SITE_HOST_RE = re.compile(r"^https?://(www\.)?dejaviewed\.dev(/|$)")

_MD = MarkdownIt("commonmark", {"html": True}).enable("table").enable("strikethrough")


def _slugify(text: str) -> str:
    s = re.sub(r"[^\w\s-]", "", text.lower(), flags=re.UNICODE)
    return re.sub(r"[\s_-]+", "-", s).strip("-") or "section"


def _inline_text(tok: Token) -> str:
    return "".join(c.content for c in (tok.children or []) if c.type in ("text", "code_inline"))


def _text_token(content: str) -> Token:
    t = Token("text", "", 0)
    t.content = content
    return t


def _sanitize_inline(children: list[Token]) -> list[Token]:
    """Allow-list raw inline HTML; autolink bare URLs in text outside links (GFM parity with marked)."""
    out, open_tags, in_link = [], [], 0
    for c in children:
        if c.type == "html_inline":
            raw = c.content
            m = GO_OPEN_RE.match(raw)
            if m:
                c.content = f'<a href="{m.group(1)}" class="go" rel="{m.group(2)}">'
                open_tags.append("a"); in_link += 1
                out.append(c); continue
            if raw == SUP_OPEN:
                open_tags.append("sup"); out.append(c); continue
            if raw in ("</a>", "</sup>") and open_tags and open_tags[-1] == raw[2:-1]:
                if open_tags.pop() == "a":
                    in_link -= 1
                out.append(c); continue
            if COMMENT_RE.match(raw):
                continue
            out.append(_text_token(raw))   # escaped on render
            continue
        if c.type == "link_open":
            in_link += 1
        elif c.type == "link_close":
            in_link -= 1
        if c.type == "text" and not in_link and AUTOLINK_RE.search(c.content):
            pos = 0
            for m in AUTOLINK_RE.finditer(c.content):
                url = m.group(0).rstrip(".,;:!?*_)]")
                if url.count("(") > url.count(")") and m.group(0)[len(url):].startswith(")"):
                    url += ")"
                if m.start() > pos:
                    out.append(_text_token(c.content[pos:m.start()]))
                lo = Token("link_open", "a", 1); lo.attrs = {"href": url}
                out += [lo, _text_token(url), Token("link_close", "a", -1)]
                pos = m.start() + len(url)
            if pos < len(c.content):
                out.append(_text_token(c.content[pos:]))
            continue
        out.append(c)
    for tag in reversed(open_tags):   # close anything the markdown left open
        t = Token("html_inline", "", 0); t.content = f"</{tag}>"; out.append(t)
    return out


def _render_fence(self, tokens, idx, options, env):
    t = tokens[idx]
    lang = (t.info or "").strip().split()[0] if (t.info or "").strip() else ""
    cls = f' class="language-{html.escape(lang)}"' if lang else ""
    return ('<div class="ps-pre"><button type="button" class="md-copy ps-copy" data-pagefind-ignore>Copy</button>'
            f"<pre><code{cls}>{html.escape(t.content, quote=False)}</code></pre></div>\n")


def clean_href(href: str, base: str = "/guides/") -> str:
    """Relative internal href (as written in guide markdown, e.g. ../e/X.html, ../catalog.html#post-X)
    -> the root-absolute clean URL Cloudflare serves (/e/X, /catalog#post-X, /guides/, /deeper/X).
    Same rules as normalize_links.py: only rewritten when the target exists under site/ (a broken link
    stays visibly broken for check_links.py); external, scheme, #-only and /go/ links are untouched."""
    if not href or href.startswith(("#", "?", "/go/", "//")) or re.match(r"[a-zA-Z][a-zA-Z0-9+.-]*:", href):
        return href
    m = re.match(r"([^?#]*)(.*)", href, re.S)
    path, rest = m.group(1), m.group(2)
    if not path:
        return href
    ab = posixpath.normpath(posixpath.join(base, path)) + ("/" if path.endswith("/") else "")
    disk = SITE / ab.lstrip("/")
    if ab.endswith("/"):
        out = ab if (disk / "index.html").is_file() else None
    elif ab.endswith("/index.html"):
        out = ab[: -len("index.html")] if disk.is_file() else None
    elif ab.endswith(".html"):
        out = ab[: -len(".html")] if disk.is_file() else None
    elif disk.with_name(disk.name + ".html").is_file():
        out = ab
    elif (disk / "index.html").is_file():
        out = ab + "/"
    elif disk.is_file():
        out = ab
    else:
        out = None
    return (out + rest) if out else href


def _render_link_open(self, tokens, idx, options, env):
    t = tokens[idx]
    href = clean_href(t.attrGet("href") or "")
    t.attrSet("href", href)
    if re.match(r"https?://", href) and not SITE_HOST_RE.match(href):
        t.attrSet("target", "_blank")
        t.attrSet("rel", "noopener")
    return self.renderToken(tokens, idx, options, env)


def _render_image(self, tokens, idx, options, env):
    t = tokens[idx]
    t.attrSet("loading", "lazy")
    t.attrSet("decoding", "async")
    t.attrSet("alt", self.renderInlineAsText(t.children or [], options, env))
    return self.renderToken(tokens, idx, options, env)


_MD.add_render_rule("fence", _render_fence)
_MD.add_render_rule("code_block", _render_fence)
_MD.add_render_rule("link_open", _render_link_open)
_MD.add_render_rule("image", _render_image)


def render_guide_html(md: str) -> str:
    """Guide markdown (as stored in the md script) -> static HTML for #guide-body.

    Exactly one <h1>: the first H1 is the page title; any later H1 is demoted to H2.
    h2/h3 get slug ids (deduped); the '## Prompt system …' heading gets id="prompt-system".
    Code fences become copy-button blocks (.ps-pre, styled by PS_CSS, wired by COPY_JS)."""
    tokens = _MD.parse(md)
    seen_h1, used = False, set()
    for i, t in enumerate(tokens):
        if t.type == "html_block":
            if COMMENT_RE.match(t.content):
                t.type, t.content = "html_block", ""
            else:   # escape: render as a paragraph of literal text
                t.content = f"<p>{html.escape(t.content.strip(), quote=False)}</p>\n"
        elif t.type == "inline" and t.children is not None:
            t.children = _sanitize_inline(t.children)
        elif t.type == "heading_open":
            if t.tag == "h1":
                if seen_h1:
                    t.tag = "h2"
                    for j in range(i + 1, len(tokens)):
                        if tokens[j].type == "heading_close":
                            tokens[j].tag = "h2"
                            break
                seen_h1 = True
    for i, t in enumerate(tokens):
        if t.type == "heading_open" and t.tag in ("h2", "h3"):
            text = _inline_text(tokens[i + 1])
            slug = "prompt-system" if t.tag == "h2" and text.startswith("Prompt system") else _slugify(text)
            base, n = slug, 2
            while slug in used:
                slug, n = f"{base}-{n}", n + 1
            used.add(slug)
            t.attrSet("id", slug)
    return _MD.renderer.render(tokens, _MD.options, {})


def rerender_page(path: Path) -> bool:
    """Re-render #guide-body of one guide page from its md script. Returns True if the file changed."""
    text = path.read_text(encoding="utf-8")
    m = MD_SRC_RE.search(text)
    if not m:
        return False
    region = f"{BODY_START}\n{render_guide_html(m.group(1))}{BODY_END}"
    new = text
    if BODY_REGION_RE.search(new):
        new = BODY_REGION_RE.sub(lambda _: region, new, count=1)
    elif EMPTY_BODY_RE.search(new):
        new = EMPTY_BODY_RE.sub(lambda _: f"{GUIDE_BODY_OPEN}{region}</div>", new, count=1)
    else:
        print(f"[rerender] WARNING {path.name}: no #guide-body", file=sys.stderr)
        return False
    new = LEGACY_RENDER_RE.sub("", new)
    new = LEGACY_WRAP_RE.sub("", new)
    new = LEGACY_SR_RE.sub("", new)
    if new != text:
        path.write_text(new, encoding="utf-8")
        return True
    return False


def rerender_all(guides_dir: Path = GUIDES) -> tuple[int, int]:
    """Re-render every guide page's body from its markdown. Returns (pages, changed)."""
    pages = changed = 0
    for p in sorted(guides_dir.glob("*.html")):
        if p.name == "index.html":
            continue
        pages += 1
        changed += rerender_page(p)
    return pages, changed


# --------------------------------------------------------------------------- helpers
ENTRY_DIR = SITE / "e"


def entry_page(e: dict) -> str | None:
    """Clean URL '/e/<slug>' when that entry page exists on disk (render_entries.safe_slug)."""
    rid = e.get("id") or e.get("post_id") or e.get("_dive_key") or ""
    slug = "".join(c if c.isalnum() or c in "-_" else "_" for c in rid)
    return f"/e/{slug}" if slug and (ENTRY_DIR / f"{slug}.html").exists() else None


def entries_nav_html(entries: list[dict]) -> str:
    """Static (no-JS) list of entry-page links so crawlers see them; the
    markdown body is rendered client-side."""
    items = []
    for e in entries:
        href = entry_page(e)
        if href:
            items.append(f'<li><a href="{html.escape(href, quote=True)}">'
                         f'{html.escape(e.get("title") or e.get("id") or "entry")}</a></li>')
    if not items:
        return ""
    return ('  <nav class="guide-entries" aria-label="Entries in this guide" '
            'style="margin:40px 0 0;padding-top:18px;border-top:1px solid var(--border);font-size:14px">'
            '<h2 style="font-size:16px;margin:0 0 8px;border:none">Entries in this guide</h2>'
            '<ul style="margin:0;padding-left:20px">' + "".join(items) + "</ul></nav>\n")


STANDALONE_LINK_RE = re.compile(
    r'(<a href="(?:\.\./catalog\.html|/catalog)#post-([A-Za-z0-9_-]+)">[^<]*</a>)(?! · <a href="(?:\.\./|/)e/)')


def link_standalone_guides(by_id: dict, skip: set[str], dry_run: bool) -> int:
    """Hand-written single-entry guides link only to catalog.html#post-<id>;
    add the entry page next to that link. Idempotent (negative lookahead)."""
    n = 0
    for path in sorted(GUIDES.glob("*.html")):
        if path.stem == "index" or path.stem in skip:
            continue
        text = path.read_text(encoding="utf-8")

        def sub(m):
            e = by_id.get(m.group(2)) or {"id": m.group(2)}
            href = entry_page(e)
            return f'{m.group(1)} · <a href="{href}">Entry page</a>' if href else m.group(0)

        new = STANDALONE_LINK_RE.sub(sub, text)
        if new != text:
            n += 1
            if not dry_run:
                path.write_text(new, encoding="utf-8")
    return n


def load_json(p: Path):
    with p.open() as f:
        return json.load(f)


def slug_of(dive_id: str) -> str:
    return dive_id[len(SLUG_PREFIX):] if dive_id.startswith(SLUG_PREFIX) else dive_id


def is_curated(d: dict) -> bool:
    return d.get("suggested_by") == "curated" or bool(d.get("pinned"))


def class_label(cls: str, classes: dict) -> str:
    meta = classes.get(cls) if isinstance(classes, dict) else None
    if isinstance(meta, dict) and meta.get("label"):
        return meta["label"]
    return (cls or "").replace("_", " ").title()


def escape_script(md: str) -> str:
    """Neutralise any closing script tag inside the text/markdown block."""
    return re.sub(r"</(script)", r"&lt;/\1", md, flags=re.IGNORECASE)


def text_block(v) -> str:
    """Dive text fields may be a string or a list of strings (rendered as bullets)."""
    if isinstance(v, (list, tuple)):
        return "\n".join(f"- {str(x).strip()}" for x in v if str(x).strip())
    return str(v or "").strip()


# --------------------------------------------------------------------------- "In two sentences" answer block
# A short, quotable answer at the top of every guide (chatbots that fetch guides cite the opening lines).
# Source order: prompt-system pack mission -> dive thesis -> first prose paragraph of a hand-written guide.
# Up to two sentences, hard cap ANSWER_MAX chars, always cut at a sentence boundary; only if no source has a
# first sentence that fits is the shortest one cut at a clause boundary with an ellipsis.
ANSWER_MAX = 320
ANSWER_LABEL = "**In short:**"
ANSWER_START = "<!-- answer:start -->"
ANSWER_END = "<!-- answer:end -->"
MD_SCRIPT_RE = re.compile(r'(<script id="md" type="text/markdown">)(.*?)(</script>)', re.S)
_ABBR = {"e.g", "i.e", "etc", "vs", "mr", "mrs", "ms", "dr", "st", "jr", "sr", "inc", "ltd", "co",
         "approx", "fig", "no", "u.s", "cf", "al", "ca", "est", "min", "max", "ver", "v"}
_SENT_END = re.compile(r'[.!?]["\')\]*]*\s+')


def split_sentences(text: str) -> list[str]:
    """Sentence split that keeps 'e.g.', 'i.e.', 'vs.', single initials and decimals ('3.5') intact."""
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    out, start = [], 0
    for m in _SENT_END.finditer(t):
        stop = m.start()
        w = re.search(r"([A-Za-z.]+)$", t[start:stop])
        word = (w.group(1) if w else "").lower().strip(".")
        if t[stop] == "." and (word in _ABBR or re.fullmatch(r"[a-z]", word)):
            continue
        nxt = t[m.end():m.end() + 1]
        if nxt and nxt.islower():          # "... approx. three" style continuation
            continue
        out.append(t[start:m.end()].strip())
        start = m.end()
    if t[start:].strip():
        out.append(t[start:].strip())
    return out


def strip_md(s: str) -> str:
    s = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", str(s or ""))
    s = re.sub(r"(\*\*|__|`)", "", s)
    s = re.sub(r"(?<![\w*])\*(?!\s)([^*]+?)\*(?!\w)", r"\1", s)
    return re.sub(r"\s+", " ", s).strip()


def intro_paragraph(md: str) -> str:
    """First prose paragraph after the H1 of a hand-written guide ('**Why it matters:** ...' label stripped)."""
    body = md
    if ANSWER_START in md and ANSWER_END in md:   # ignore our own block (keeps the result idempotent)
        body = md[:md.index(ANSWER_START)] + md[md.index(ANSWER_END) + len(ANSWER_END):]
    paras = re.split(r"\n\s*\n", body)
    seen_h1 = False
    for p in paras:
        p = p.strip()
        if not p:
            continue
        if p.startswith("# "):
            seen_h1 = True
            continue
        if not seen_h1 or p.startswith(("#", ">", "-", "*  ", "|", "`", "<", "---", "1.")):
            continue
        lines = p.split("\n")
        if len(lines) > 1 and all(ln.startswith("**") for ln in lines):
            continue                          # a block of '**Label:** value' metadata lines
        lab = re.match(r"^\*\*([^*]{1,40}):\*\*\s*", p)
        if lab:
            if lab.group(1).strip().lower() not in ("why it matters", "tl;dr", "tldr", "summary", "what it is"):
                continue                      # '**Author:** ...', '**Repo:** ...' etc. are metadata, not an answer
            p = p[lab.end():]
        t = strip_md(p)
        if len(t) >= 60:
            return t
    return ""


def _fit(sents: list[str]) -> str:
    if len(sents) >= 2 and len(sents[0]) + 1 + len(sents[1]) <= ANSWER_MAX:
        return f"{sents[0]} {sents[1]}"
    if sents and len(sents[0]) <= ANSWER_MAX:
        return sents[0]
    return ""


def answer_text(slug: str, dive: dict | None = None, md: str = "") -> str:
    sources = [(PACKS.get(slug) or {}).get("mission", ""),
               text_block((dive or {}).get("thesis")).replace("\n- ", " ").lstrip("- "),
               intro_paragraph(md) if md else ""]
    split = [split_sentences(strip_md(s)) for s in sources if s and str(s).strip()]
    for sents in split:
        a = _fit(sents)
        if a:
            break
    else:
        if not split:
            return ""
        first = min((s[0] for s in split if s), key=len)
        cut = first[:ANSWER_MAX - 1]
        pos = max(cut.rfind(sep) for sep in (", ", "; ", " — ", ": ", " - "))
        a = (cut[:pos] if pos > ANSWER_MAX // 2 else cut[:cut.rfind(" ")]).rstrip(" ,;:—-") + "…"
    return a.replace("<", "&lt;")


def answer_block(answer: str) -> str:
    return f"{ANSWER_START}\n\n> {ANSWER_LABEL} {answer}\n\n{ANSWER_END}"


def put_answer(md: str, block: str) -> str:
    """Replace the marked block, or insert it right after the first H1 line. Idempotent."""
    if ANSWER_START in md and ANSWER_END in md:
        a, b = md.index(ANSWER_START), md.index(ANSWER_END) + len(ANSWER_END)
        return md[:a] + block + md[b:]
    m = re.search(r"(?m)^# .*$", md)
    if not m:
        return md
    return md[:m.end()] + "\n\n" + block + md[m.end():]


def apply_answers(curated: dict[str, dict], dry_run: bool) -> tuple[int, int]:
    """Refresh the answer block in every guide page (generated ones already carry it; hand-written ones
    get it inserted after their H1). Returns (pages with a block, pages changed)."""
    have = changed = 0
    for path in sorted(GUIDES.glob("*.html")):
        if path.stem == "index":
            continue
        txt = path.read_text(encoding="utf-8")
        m = MD_SCRIPT_RE.search(txt)
        if not m:
            continue
        md = m.group(2)
        # generated pages: same inputs as build_markdown (no intro fallback) so both paths agree
        ans = answer_text(path.stem, curated.get(path.stem), "" if path.stem in curated else md)
        if not ans:
            print(f"WARNING: no answer source for guide {path.stem}")
            continue
        new_md = put_answer(md, escape_script(answer_block(ans)))
        have += 1
        if new_md != md:
            changed += 1
            if not dry_run:
                path.write_text(txt[:m.start(2)] + new_md + txt[m.end(2):], encoding="utf-8")
    return have, changed


HANDLE_RE = re.compile(r"[a-z0-9._]{1,30}")


def clean_handle(handle) -> str:
    """Valid lowercase IG handle or "" (catalog has scrape artifacts like creator='Edited')."""
    h = str(handle or "").lstrip("@").strip()
    return h if HANDLE_RE.fullmatch(h) else ""


def creator_link(handle: str) -> str:
    h = clean_handle(handle)
    return f"[@{h}](https://instagram.com/{h})" if h else "unknown"


def deeper_file(slug: str) -> str | None:
    for name in (f"deeper-insight-{slug}.html", f"{slug}.html"):
        if (DEEPER / name).exists():
            return name
    return None


def parse_date(s):
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).date()
    except ValueError:
        return None


def date_range(entries: list[dict]) -> str:
    ds = sorted(d for d in (parse_date(e.get("date")) for e in entries) if d)
    if not ds:
        return ""
    return f"{ds[0].strftime('%b %Y')} – {ds[-1].strftime('%b %Y')}"


# --------------------------------------------------------------------------- markdown body
def build_markdown(d: dict, entries: list[dict], classes: dict, catalog_total: int) -> str:
    cmap = d.get("connection_map") or {}
    tools = sorted({t for e in entries for t in (e.get("tools") or []) if t})
    creators = sorted({clean_handle(e.get("creator")) for e in entries} - {""})

    out = [f"# {d['title']}", ""]
    out.append(
        f"**Insight class:** {class_label(d.get('class') or d.get('dive_class'), classes)} · "
        f"**Difficulty:** {d.get('execution_difficulty') or 'Unknown'} · "
        f"**Quality:** {d.get('quality_rating') or '?'}/5"
    )
    line = f"**Connected entries:** {len(entries)}"
    if tools:
        line += f" · **Tools:** {', '.join(tools)}"
    out += [line, "", answer_block(answer_text(slug_of(d["id"]), d)), "", "---", ""]

    out += ["## Thesis", "", text_block(d.get("thesis")), "", "---", ""]
    if d.get("why_it_matters"):
        out += ["## Why it matters", "", text_block(d["why_it_matters"]), "", "---", ""]

    out += ["## The evidence — connected entries", ""]
    for e in entries:
        eid = e.get("_dive_key")
        href = entry_page(e)
        ttl = e.get('title') or eid
        ttl_md = str(ttl).replace("[", "\\[").replace("]", "\\]")
        out.append(f"### [{ttl_md}]({href})" if href else f"### {ttl}")
        out.append(f"**Creator:** {creator_link(e.get('creator'))} · **Tier:** {e.get('tier') or '?'}")
        if e.get("tools"):
            out.append(f"**Tools:** {', '.join(e['tools'])}")
        out.append("")
        role = cmap.get(eid) or cmap.get(e.get("id")) or cmap.get(e.get("post_id"))
        if role:
            out += [f"> {role}", ""]
        if e.get("summary"):
            out += [text_block(e["summary"]), ""]
        if e.get("url"):
            out.append(f"[View original post]({e['url']})")
    out += ["", "---", ""]

    if d.get("action_sketch"):
        out += ["## Action sketch — how to implement this", "", text_block(d["action_sketch"]), "", "---", ""]
    if d.get("prerequisites"):
        out += ["## Prerequisites", "", text_block(d["prerequisites"]), "", "---", ""]

    if tools:
        out += ["## Key tools and resources", ""] + [f"- **{t}**" for t in tools] + [""]
    if creators:
        out += ["## Creators to follow", ""] + [f"- {creator_link(c)}" for c in creators] + [""]
    out += ["---", ""]

    pack = PACKS.get(slug_of(d["id"]))
    if pack:
        out += [section_markdown(pack), ""]

    out += [
        "## Related deep dives", "",
        f"Browse more deep dives at [DejaViewed](/catalog) — {catalog_total} entries across the full catalog.",
        "", "---", "",
        f"*Generated {date.today().isoformat()} · curated by [@{CURATOR}](https://instagram.com/{CURATOR}) for DejaViewed*",
        "",
    ]
    return "\n".join(out)


def build_page(d: dict, entries: list[dict], classes: dict, catalog_total: int) -> str:
    slug = slug_of(d["id"])
    q = d.get("quality_rating") or 0
    confidence = "high" if isinstance(q, (int, float)) and q >= 5 else "medium"
    df = deeper_file(slug)
    cross = "  " + CROSS_LINK.format(file=Path(df).stem, title=html.escape(d["title"])) if df else ""
    head = PAGE_HEAD.format(
        title=html.escape(d["title"]),
        confidence=confidence,
        cross_link=cross,
        curator=CURATOR,
        entries_nav=entries_nav_html(entries),
    )
    return head + escape_script(build_markdown(d, entries, classes, catalog_total)) + PAGE_TAIL


# --------------------------------------------------------------------------- index page
INDEX_HEAD = """<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Guides — DejaViewed</title>
<link rel="stylesheet" href="../shared.css">
<style>
  .guides-container { max-width: 900px; margin: 2rem auto; padding: 0 1.5rem; }
  .guides-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; margin-top: 1.5rem; }
  .guide-card:hover { border-color: rgba(125,211,252,0.3) !important; }
  .filter-bar { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 1rem; }
  .filter-pill.active { background: rgba(125,211,252,0.15) !important; border-color: rgba(125,211,252,0.3) !important; color: #7dd3fc !important; }
</style>
<script src="../shared.js" defer></script>
<script>document.addEventListener("DOMContentLoaded",()=>window.DV&&DV.mountHeader(document.body,"guides"))</script>
</head><body>
"""

INDEX_TAIL = """  </div>
</div>

<script>
document.querySelectorAll('.filter-pill').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    const tier = btn.dataset.tier;
    document.querySelectorAll('.guide-card').forEach(card => {
      card.style.display = (tier === 'all' || card.dataset.tier === tier) ? 'block' : 'none';
    });
  });
});
</script>"""

PILL = ('<button class="filter-pill{active}" data-tier="{tier}" style="padding:6px 14px;border-radius:20px;'
        'border:1px solid {border};background:{bg};color:{color};cursor:pointer;font-size:0.85rem;">{label} ({n})</button>')

BADGE_STYLE = {
    "featured": "background:linear-gradient(135deg,rgba(167,139,250,.25),rgba(244,114,182,.25));color:#f472b6;border:1px solid rgba(244,114,182,.4);",
    "guide": "background:rgba(167,139,250,.18);color:#a78bfa;border:1px solid rgba(167,139,250,.35);",
    "standalone": "background:rgba(125,211,252,.12);color:#7dd3fc;border:1px solid rgba(125,211,252,.25);",
}
CARD_STYLE = {
    "featured": "background:linear-gradient(135deg,rgba(167,139,250,.04),rgba(244,114,182,.04));border-radius:12px;border:1px solid rgba(244,114,182,.35);",
    "guide": "background:rgba(255,255,255,0.03);border-radius:12px;border:1px solid rgba(167,139,250,0.25);",
    "standalone": "background:rgba(255,255,255,0.03);border-radius:12px;border:1px solid rgba(255,255,255,0.06);",
}


def card_html(c: dict) -> str:
    tier = c["tier"]
    featured = tier == "featured"
    title_style = ("font-weight:900;color:#fff;flex:1;min-width:0;font-size:1.1rem;" if featured
                   else "font-weight:600;color:#e2e8f0;flex:1;min-width:0;")
    dr = (f'<span style="color:#64748b;font-size:0.75rem;"> · {c["range"]}</span>' if c.get("range") else "")
    lines = [
        f'<a href="/guides/{c["slug"]}" class="guide-card" data-tier="{tier}" style="display:block;padding:16px;{CARD_STYLE[tier]}text-decoration:none;transition:border-color 0.2s;">',
        '  <div style="display:flex;align-items:flex-start;gap:8px;">',
        f'    <div style="{title_style}">{html.escape(c["title"], quote=False)}</div>',
        f'    <span style="display:inline-block;padding:2px 7px;border-radius:4px;font-size:9px;font-weight:900;letter-spacing:.06em;text-transform:uppercase;{BADGE_STYLE[tier]}margin-left:auto;flex-shrink:0;">{tier.upper()}</span>',
        "  </div>",
        f'  <div style="font-size:0.8rem;color:#94a3b8;margin-top:4px;">{c["meta"]}{dr}</div>',
    ]
    if featured and c.get("blurb"):
        lines.append(f'  <div style="font-size:0.8rem;color:#e2e8f0;margin-top:8px;line-height:1.5;padding:8px;background:rgba(244,114,182,0.05);border-radius:6px;">{html.escape(c["blurb"], quote=False)}</div>')
    lines.append("</a>")
    return "\n".join(lines)


def page_title(path: Path) -> str | None:
    try:
        m = re.search(r"<title>(.*?)</title>", path.read_text(errors="replace"), re.S)
    except OSError:
        return None
    if not m:
        return None
    t = html.unescape(m.group(1)).strip()
    return re.sub(r"\s*[·—|-]\s*DejaViewed\s*$", "", t).strip() or None


def build_index(page_slugs: set[str], curated: dict[str, dict], resolved: dict[str, list[dict]]) -> str:
    cards = []
    covered: set[str] = set()
    for slug in page_slugs:
        d = curated.get(slug)
        if d:
            ents = resolved.get(slug, [])
            covered.update(e["_dive_key"] for e in ents)
            tier = "featured" if slug in FEATURED else "guide"
            cards.append({
                "slug": slug, "tier": tier, "title": d["title"],
                "meta": f"{d.get('class') or d.get('dive_class') or 'guide'} · {len(ents)} entries",
                "range": date_range(ents), "blurb": FEATURED.get(slug), "count": len(ents),
            })
        else:
            title = page_title(GUIDES / f"{slug}.html") or slug.replace("-", " ").title()
            cards.append({"slug": slug, "tier": "standalone", "title": title,
                          "meta": "standalone guide", "count": 0})

    order = {"featured": 0, "guide": 1, "standalone": 2}
    cards.sort(key=lambda c: (order[c["tier"]], -c["count"] if c["tier"] != "standalone" else 0, c["slug"]))
    n = {t: sum(1 for c in cards if c["tier"] == t) for t in order}

    pills = [
        PILL.format(active=" active", tier="all", border="rgba(125,211,252,0.3)", bg="rgba(125,211,252,0.15)",
                    color="#7dd3fc", label="All", n=len(cards)),
        PILL.format(active="", tier="featured", border="rgba(244,114,182,0.3)", bg="transparent",
                    color="#f472b6", label="Featured", n=n["featured"]),
        PILL.format(active="", tier="guide", border="rgba(167,139,250,0.25)", bg="transparent",
                    color="#a78bfa", label="Guides", n=n["guide"]),
        PILL.format(active="", tier="standalone", border="rgba(125,211,252,0.15)", bg="transparent",
                    color="#7dd3fc", label="Standalone", n=n["standalone"]),
    ]
    body = [
        INDEX_HEAD,
        '<div class="guides-container">',
        '  <h1 style="font-size:1.8rem;margin-bottom:0.25rem;">Guides</h1>',
        f'  <p style="color:#94a3b8;margin-bottom:1rem;">{len(cards)} deep dive guides connecting ideas across {len(covered)} entries</p>',
        "  ",
        '  <div class="filter-bar">',
        "    " + "\n".join(pills),
        "  </div>",
        "  ",
        '  <div class="guides-grid" id="guides-grid">',
        "    " + "\n".join(card_html(c) for c in cards),
        INDEX_TAIL,
    ]
    body.append("</body></html>")
    return "\n".join(body)


# --------------------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="print what would be written; write nothing")
    ap.add_argument("--dive-id", help="only build this dive (full id, e.g. dd-insight-agent-architecture)")
    ap.add_argument("--force", action="store_true", help="overwrite existing guide pages")
    ap.add_argument("--no-index", action="store_true", help="do not regenerate guides/index.html")
    ap.add_argument("--out-dir", type=Path, help="write pages here instead of site/guides (preview/diff)")
    ap.add_argument("--rerender-only", action="store_true",
                    help="only re-render #guide-body of every site/guides page from its md script, then exit")
    args = ap.parse_args()

    if args.rerender_only:
        n_pages, n_changed = rerender_all(args.out_dir or GUIDES)
        print(f"rendered #guide-body: {n_pages} pages ({n_changed} changed)")
        return 0

    dd = load_json(DEEP_DIVES)
    classes = dd.get("classes") or {}
    manual = {m["id"]: m for m in load_json(MANUAL_DIVES).get("manual_dives", [])} if MANUAL_DIVES.exists() else {}
    cat = load_json(CATALOG)
    entries = cat["entries"] if isinstance(cat, dict) else cat
    by_id: dict[str, dict] = {}
    for e in entries:
        for k in (e.get("id"), e.get("post_id")):
            if k:
                by_id.setdefault(k, e)

    curated: dict[str, dict] = {}
    for d in dd.get("deep_dives", []):
        if not is_curated(d):
            continue
        merged = dict(d)
        for k, v in manual.get(d["id"], {}).items():
            if not merged.get(k) and v:
                merged[k] = v  # fill gaps (why_it_matters, prerequisites) from manual_dives
        curated[slug_of(d["id"])] = merged

    # resolve entries + validate ids
    resolved: dict[str, list[dict]] = {}
    bad: dict[str, list[str]] = {}
    bad_creators: dict[str, list[str]] = {}
    for slug, d in curated.items():
        ents = []
        for eid in d.get("entry_ids") or []:
            e = by_id.get(eid)
            if e is None:
                bad.setdefault(d["id"], []).append(eid)
                continue
            if e.get("creator") and not clean_handle(e.get("creator")):
                bad_creators.setdefault(d["id"], []).append(f"{eid}={e.get('creator')!r}")
            ents.append({**e, "_dive_key": eid})
        resolved[slug] = ents

    targets = list(curated)
    if args.dive_id:
        s = slug_of(args.dive_id)
        if s not in curated:
            print(f"error: {args.dive_id} is not a curated dive in {DEEP_DIVES.relative_to(ROOT)}", file=sys.stderr)
            return 2
        targets = [s]

    out_dir = args.out_dir or GUIDES
    new, overwrite, skipped = [], [], []
    for slug in targets:
        exists = (GUIDES / f"{slug}.html").exists()
        if exists and not args.force:
            skipped.append(slug)
            continue
        (overwrite if exists else new).append(slug)
        page = build_page(curated[slug], resolved[slug], classes, len(entries))
        dest = out_dir / f"{slug}.html"
        if args.dry_run:
            print(f"[dry-run] would {'overwrite' if exists else 'create'} {dest.relative_to(ROOT) if dest.is_relative_to(ROOT) else dest} "
                  f"({len(resolved[slug])} entries, {len(page):,} bytes"
                  f"{', deeper link' if deeper_file(slug) else ''})")
        else:
            out_dir.mkdir(parents=True, exist_ok=True)
            dest.write_text(page)
            print(f"wrote {dest}")

    print()
    print(f"curated dives: {len(curated)}  | targeted: {len(targets)}")
    print(f"new: {len(new)}  overwrite: {len(overwrite)}  skipped (exists, no --force): {len(skipped)}")
    if new:
        print("  new:", ", ".join(new))
    if skipped:
        print("  skipped:", ", ".join(skipped))
    if bad:
        print("\nWARNING: entry ids missing from site/catalog.json:")
        for did, ids in bad.items():
            print(f"  {did}: {', '.join(ids)}")
    else:
        print("entry ids: all resolve in site/catalog.json")
    if bad_creators:
        print("\nWARNING: malformed creator handles (rendered as 'unknown'; fix in catalog):")
        for did, ids in bad_creators.items():
            print(f"  {did}: {', '.join(ids)}")

    if out_dir == GUIDES and not args.dive_id:
        n_sa = link_standalone_guides(by_id, set(curated), args.dry_run)
        print(f"standalone guides given an entry-page link: {n_sa}")
        n_ans, n_ch = apply_answers(curated, args.dry_run)
        print(f"answer blocks: {n_ans} guides ({n_ch} {'would change' if args.dry_run else 'updated'})")

    if not args.no_index:
        page_slugs = {p.stem for p in GUIDES.glob("*.html") if p.stem != "index"} | set(new)
        idx = build_index(page_slugs, curated, resolved)
        dest = out_dir / "index.html"
        n_feat = sum(1 for s in page_slugs if s in curated and s in FEATURED)
        n_guide = sum(1 for s in page_slugs if s in curated) - n_feat
        summary = f"{len(page_slugs)} cards (featured {n_feat}, guide {n_guide}, standalone {len(page_slugs) - n_feat - n_guide})"
        if args.dry_run:
            print(f"\n[dry-run] would regenerate {dest.relative_to(ROOT) if dest.is_relative_to(ROOT) else dest}: {summary}")
        else:
            dest.write_text(idx)
            print(f"\nwrote {dest}: {summary}")

    # Always last: the md scripts may have changed above (pages, answers); #guide-body follows them.
    if not args.dry_run:
        n_pages, n_changed = rerender_all(out_dir)
        print(f"rendered #guide-body: {n_pages} pages ({n_changed} changed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
