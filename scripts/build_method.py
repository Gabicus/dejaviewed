#!/usr/bin/env python3
"""Generate site/method.html — "How DejaViewed works": pipeline, tiers, update cadence,
affiliate policy, who runs it, and the data/API usage terms.

Every number is live: site/catalog.json, data/prompt_systems.json, data/slides_ocr.json,
data/monetize/*.json and the pages on disk. The tier rubric is read from
data/llm_batches/SPEC.md (the same text the enrichment agents follow).

Idempotent: the file is only rewritten when its content changes, ignoring the blocks other
post-processors own (seo, monetize, sitenav).

Usage: python3 scripts/build_method.py
"""
from __future__ import annotations

import html
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_seo import (AUTHOR_URL, CONTACT_URL, DATA, GEN_BLOCK_RE, OWNER_GITHUB, OWNER_NAME,  # noqa: E402
                       OWNER_URL, REPO_URL, SITE, load_json, parse_date, write_if_changed)

OUT = SITE / "method.html"
SPEC = DATA / "llm_batches" / "SPEC.md"
esc = lambda s: html.escape(str(s), quote=True)

TIER_FALLBACK = {
    "S": "exceptional: deep, specific, linkable (a real repo, tool or paper), something you would build on this week.",
    "A": "solid and actionable, names real things, worth a guide.",
    "B": "useful reference, one idea, or a good example without depth.",
    "C": "thin, hype-only, promotional, no subject, or sponsored content dressed as news.",
}


def tier_rubric() -> dict[str, str]:
    out = dict(TIER_FALLBACK)
    try:
        spec = SPEC.read_text(encoding="utf-8")
    except OSError:
        return out
    for t, text in re.findall(r"(?m)^- ([SABC]): (.+)$", spec):
        text = text.strip().replace(" — ", ": ", 1).replace("—", ",")
        out[t] = text[0].lower() + text[1:] if text else out[t]
    return out


def strip_generated(s: str) -> str:
    return GEN_BLOCK_RE.sub("", s).replace("\n\n", "\n")


def main() -> int:
    cat = load_json(SITE / "catalog.json", {}) or {}
    E = cat.get("entries", [])
    packs = load_json(DATA / "prompt_systems.json", {}) or {}
    ocr = load_json(DATA / "slides_ocr.json", {}) or {}
    mon = load_json(DATA / "monetize" / "config.json", {}) or {}
    aff = load_json(DATA / "monetize" / "affiliates.json", {}) or {}

    n = len(E)
    colls = Counter(e.get("collection") for e in E if e.get("collection"))
    creators = len({e.get("creator") for e in E} - {None, ""})
    media = Counter(e.get("media_type") or "unknown" for e in E)
    transcripts = sum(1 for e in E if (e.get("transcript") or "").strip())
    captions = sum(1 for e in E if (e.get("caption") or "").strip())
    tiers = Counter(e.get("tier") or "C" for e in E)
    guides = sorted(p.stem for p in (SITE / "guides").glob("*.html") if p.name != "index.html")
    deepers = sorted(p.stem for p in (SITE / "deeper").glob("*.html") if p.name != "index.html")
    steps = sum(len(p.get("steps", [])) for p in packs.values())
    ds = sorted(d for d in (parse_date(e.get("date")) for e in E) if d)
    span = f"{ds[0]:%B %Y} to {ds[-1]:%B %Y}" if ds else "n/a"
    gen = parse_date(cat.get("generated"))
    gen_s = f"{gen:%B %-d, %Y}" if gen else "unknown"
    aff_status = Counter((a or {}).get("status") for a in (aff.values() if isinstance(aff, dict) else []))
    rubric = tier_rubric()
    disclosure = (mon.get("disclosure_footer") or "").strip()

    tier_rows = "\n".join(
        f'<tr><td><span class="tb t{t}">{t}</span></td><td>{esc(rubric[t])}</td>'
        f'<td class="n">{tiers.get(t, 0)}</td><td class="n">{(100 * tiers.get(t, 0) / n if n else 0):.0f}%</td></tr>'
        for t in "SABC")

    page = f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>How DejaViewed works · DejaViewed</title>
<link rel="stylesheet" href="/shared.css"><script src="/shared.js"></script>
<style>
.wrap{{max-width:860px;margin:30px auto 80px;padding:0 20px}}
h1{{font-size:34px;font-weight:900;letter-spacing:-.02em;background:linear-gradient(135deg,#fff 0%,#a78bfa 50%,#f472b6 100%);-webkit-background-clip:text;background-clip:text;color:transparent;margin:0 0 12px}}
h2{{font-size:20px;font-weight:900;letter-spacing:-.015em;color:#fff;margin:44px 0 12px}}
p,li{{color:var(--text-dim);font-size:15px;line-height:1.7}}
p b,li b{{color:var(--text)}}
.lead{{font-size:17px;color:var(--text)}}
ol.steps{{counter-reset:s;list-style:none;padding:0;margin:0}}
ol.steps li{{counter-increment:s;position:relative;padding:12px 14px 12px 52px;margin:0 0 10px;background:var(--panel);border:1px solid var(--border);border-radius:10px}}
ol.steps li::before{{content:counter(s);position:absolute;left:14px;top:12px;width:26px;height:26px;border-radius:50%;background:rgba(167,139,250,.18);color:var(--accent);font:800 13px/26px 'Inter',sans-serif;text-align:center}}
code{{background:rgba(255,255,255,.07);padding:2px 6px;border-radius:4px;font-family:'JetBrains Mono',monospace;font-size:.88em;color:var(--accent)}}
.tw{{overflow-x:auto;border:1px solid var(--border);border-radius:10px}}
table{{border-collapse:collapse;width:100%;font-size:14px}}
th,td{{text-align:left;padding:9px 12px;border-bottom:1px solid var(--border);color:var(--text-dim);vertical-align:top}}
th{{font:800 10.5px/1 'Inter',sans-serif;letter-spacing:.09em;text-transform:uppercase;color:var(--text-mute);background:var(--panel)}}
td.n{{text-align:right;font-variant-numeric:tabular-nums;color:var(--text);white-space:nowrap}}
tr:last-child td{{border-bottom:0}}
.tb{{display:inline-block;min-width:24px;text-align:center;border-radius:6px;font:800 12px/22px 'Inter',sans-serif;color:#0a0a0f}}
.tS{{background:#f472b6}}.tA{{background:#a78bfa}}.tB{{background:#60a5fa}}.tC{{background:#6a6a80}}
.card{{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:16px 18px;margin:12px 0}}
</style></head><body>
<script>DV.mountHeader(document.body,'method');</script>
<main class="wrap" data-pagefind-body>
<h1>How DejaViewed works</h1>
<p class="lead">DejaViewed turns <b>{n}</b> saved social posts from <b>{creators}</b> creators into a searchable catalog, <b>{len(guides)}</b> guides and <b>{len(packs)}</b> runnable prompt systems. This page explains how each piece is made, what the tiers mean, how often it changes, how links make money, and who is behind it.</p>

<h2 id="pipeline">The pipeline, in plain words</h2>
<ol class="steps">
<li><b>Saves.</b> Posts start as saved folders on Instagram and other platforms. Each folder becomes a collection; there are {len(colls)} of them, with posts dating from {span}.</li>
<li><b>Capture.</b> For every post the caption ({captions} captured) and a thumbnail are stored. Videos ({media.get('video', 0)}) are transcribed locally with Whisper ({transcripts} transcripts), and carousel slides with text are read with OCR ({len(ocr)} posts so far).</li>
<li><b>Enrichment.</b> A language model (Claude, working from a written spec) reads the caption, transcript and slide text and writes the title, a summary, the type, tags, tools, techniques and domains. A quality gate then rejects placeholder titles, missing transcripts and missing thumbnails before anything is published.</li>
<li><b>Tiers.</b> The same pass grades each post S, A, B or C against the rubric below, with a cap on how many S grades a collection can have.</li>
<li><b>Curated dives.</b> A researcher pass reads across the catalog and connects posts that make one argument together. Each survivor becomes a guide ({len(guides)}) with its thesis, evidence posts and sources, and many get a deeper dive ({len(deepers)}) listing every connected post.</li>
<li><b>Prompting systems.</b> Every guide ships with a prompt system: a one-shot prompt, {steps} step prompts in total with an audit after each step, a gap audit and validation checks, so you can rebuild the idea with your own agent.</li>
</ol>
<p>What goes in is a human choice: every entry is a post {esc(OWNER_NAME)} saved. AI agents, working from written specs and checked by automated quality gates, write most of the descriptive text, the tiers and the guide drafts. Each entry links to its original post so you can check the source.</p>

<h2 id="tiers">What the tiers mean</h2>
<div class="tw"><table>
<thead><tr><th>Tier</th><th>Meaning</th><th>Entries</th><th>Share</th></tr></thead>
<tbody>
{tier_rows}
</tbody></table></div>
<p>Tiers rank usefulness to a builder, not the quality of the creator's work. A C-tier art post can be beautiful; it just teaches less.</p>

<h2 id="cadence">How often it updates</h2>
<p>The site is rebuilt whenever a new batch of saves is pulled. Each batch goes through every step above before it is published. This catalog version was generated on <b>{gen_s}</b> and holds {n} entries. Pages carry a "last changed" date that moves only when their content changes, and new entries and guides appear in the <a href="/feed.xml">RSS feed</a>.</p>

<h2 id="money">Affiliate links and money</h2>
<div class="card"><p>{esc(disclosure)}</p></div>
<ul>
<li>Tool links that go through <code>/go/</code> are measured redirects: they count the click, then send you on. Tools without an approved affiliate program point at the official site; today that is {aff_status.get('pending', 0)} of {sum(aff_status.values())} listed tools, and {aff_status.get('active', 0)} are live affiliate links.</li>
<li>Whether a tool appears, and how its posts are tiered, is decided before and apart from any affiliate program.</li>
<li>The free, open-source skill that builds this site is on <a href="{REPO_URL}" rel="noopener">GitHub</a>; a done-for-you build is available through the contact link below.</li>
</ul>

<h2 id="who">Who runs it</h2>
<p>DejaViewed is built and curated by <b>{esc(OWNER_NAME)}</b>, who writes at <a href="{OWNER_URL}" rel="noopener">1gabe.com</a> and publishes the code at <a href="{OWNER_GITHUB}" rel="noopener">github.com/Gabicus</a>. The saves come from the <a href="{AUTHOR_URL}" rel="noopener">@6ab3</a> Instagram account.</p>
<ul>
<li>Contact, corrections and takedown requests: <a href="{CONTACT_URL}" rel="noopener">1gabe.com/contact</a>.</li>
<li>Source code and the Claude Code skill: <a href="{REPO_URL}" rel="noopener">github.com/Gabicus/dejaviewed</a>.</li>
</ul>

<h2 id="terms">Data, API and usage terms</h2>
<ul>
<li><b>Creators own their posts.</b> Captions, transcripts, images and videos belong to the people who made them. DejaViewed stores them to make the catalog searchable and links every entry to its source. Creators can ask for an entry to be removed through the contact link.</li>
<li><b>The curation is ours.</b> Titles, summaries, tiers, tags, guides, deeper dives and prompt systems are DejaViewed's own work. You may use them with a link back to the page you used.</li>
<li><b>Machine access is open.</b> No login and no key: <a href="/api/catalog.json"><code>/api/catalog.json</code></a>, <a href="/api/prompts.json"><code>/api/prompts.json</code></a>, <a href="/api/tools.json"><code>/api/tools.json</code></a>, <a href="/api/creators.json"><code>/api/creators.json</code></a>, <a href="/api/collections.json"><code>/api/collections.json</code></a>, plus <a href="/llms.txt"><code>/llms.txt</code></a> and <a href="/llms-full.txt"><code>/llms-full.txt</code></a> for language models.</li>
<li>When you quote a post, credit its creator and link the original. When you cite DejaViewed, link the entry or guide page; <a href="/start-here#cite">Start here</a> has a citation format.</li>
</ul>
</main>
<footer class="site" style="margin:60px 0 40px;padding-top:30px;border-top:1px solid var(--border);color:var(--text-mute);font-size:12.5px;text-align:center"><a href="/" style="color:var(--text-dim)">← Back to DejaViewed</a></footer>
</body></html>
"""
    old = OUT.read_text(encoding="utf-8") if OUT.exists() else None
    if old is not None and strip_generated(old) == strip_generated(page):
        changed = False
    else:
        changed = write_if_changed(OUT, page)
    print(f"method: {'written' if changed else 'unchanged'} ({n} entries, {len(guides)} guides, "
          f"{len(packs)} prompt systems, tiers {dict(sorted(tiers.items()))})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
