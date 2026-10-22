#!/usr/bin/env python3
"""Generate site/start-here.html — the positioning page — with live counts.

All numbers come from site/catalog.json, data/prompt_systems.json and the
pages on disk, so the page never states a stale count. Idempotent: the file
is only rewritten when its content (ignoring the seo block) changes.

Usage: python3 scripts/build_start_here.py
"""
from __future__ import annotations

import html
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_seo import (BASE, DATA, REPO_URL, AUTHOR_URL, SITE, load_json,  # noqa: E402
                       parse_date, write_if_changed)

OUT = SITE / "start-here.html"
esc = lambda s: html.escape(str(s), quote=True)


def main() -> int:
    cat = load_json(SITE / "catalog.json", {}) or {}
    E = cat.get("entries", [])
    packs = load_json(DATA / "prompt_systems.json", {}) or {}
    n = len(E)
    colls = Counter(e.get("collection") for e in E if e.get("collection"))
    creators = len({e.get("creator") for e in E} - {None, ""})
    transcripts = sum(1 for e in E if (e.get("transcript") or "").strip())
    media = Counter(e.get("media_type") or "unknown" for e in E)
    tiers = Counter(e.get("tier") or "C" for e in E)
    guides = sorted(p.stem for p in (SITE / "guides").glob("*.html") if p.name != "index.html")
    deepers = list((SITE / "deeper").glob("*.html"))
    steps = sum(len(p.get("steps", [])) for p in packs.values())
    ds = sorted(d for d in (parse_date(e.get("date")) for e in E) if d)
    span = f"{ds[0]:%B %Y} to {ds[-1]:%B %Y}" if ds else "n/a"
    gen = parse_date(cat.get("generated"))
    gen_s = gen.isoformat() if gen else "unknown"
    year = gen.year if gen else ""

    # per-collection table: entries, S, A, top domains
    by = defaultdict(list)
    for e in E:
        if e.get("collection"):
            by[e["collection"]].append(e)
    rows = []
    for coll, items in sorted(by.items(), key=lambda kv: -len(kv[1])):
        t = Counter(i.get("tier") for i in items)
        dom = Counter(d for i in items for d in (i.get("domains") or []))
        top = ", ".join(d for d, _ in dom.most_common(3)) or "—"
        rows.append(f"<tr><td><code>{esc(coll)}</code></td><td class=n>{len(items)}</td>"
                    f"<td class=n>{t.get('S', 0)}</td><td class=n>{t.get('A', 0)}</td><td>{esc(top)}</td></tr>")

    bib = (f"@misc{{dejaviewed{year},\n"
           f"  title        = {{DejaViewed: a curated archive of practitioner AI posts}},\n"
           f"  author       = {{{{DejaViewed}}}},\n"
           f"  year         = {{{year}}},\n"
           f"  howpublished = {{\\url{{{BASE}/}}}},\n"
           f"  note         = {{Catalog version {gen_s}, {n} entries. Data: {BASE}/api/catalog.json}}\n"
           f"}}")
    plain = (f"DejaViewed ({year}). DejaViewed: a curated archive of practitioner AI posts "
             f"(catalog version {gen_s}, {n} entries). {BASE}/")

    page = f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Start here · DejaViewed</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="shared.css"><script src="shared.js"></script>
<style>
.wrap{{max-width:900px;margin:30px auto 80px;padding:0 20px}}
h1{{font-size:34px;font-weight:900;letter-spacing:-.02em;background:linear-gradient(135deg,#fff 0%,#a78bfa 50%,#f472b6 100%);-webkit-background-clip:text;background-clip:text;color:transparent;margin:0 0 12px}}
h2{{font-size:20px;font-weight:900;letter-spacing:-.015em;color:#fff;margin:44px 0 12px}}
p,li{{color:var(--text-dim);font-size:15px;line-height:1.7}}
p b,li b{{color:var(--text)}}
.lead{{font-size:17px;color:var(--text);max-width:760px}}
.stats{{display:flex;gap:10px;flex-wrap:wrap;margin:22px 0 0}}
.stat{{background:var(--panel);border:1px solid var(--border);border-radius:10px;padding:12px 14px;min-width:120px}}
.stat .v{{font:900 24px/1 'Inter',sans-serif;color:#fff;font-variant-numeric:tabular-nums}}
.stat .l{{font:700 10.5px/1.3 'Inter',sans-serif;letter-spacing:.09em;text-transform:uppercase;color:var(--text-mute);margin-top:6px}}
code{{background:rgba(255,255,255,.07);padding:2px 6px;border-radius:4px;font-family:'JetBrains Mono',monospace;font-size:.88em;color:var(--accent)}}
pre{{background:rgba(0,0,0,.45);border:1px solid var(--border);border-radius:10px;padding:14px 16px;overflow-x:auto;font:500 12.5px/1.6 'JetBrains Mono',monospace;color:var(--text);white-space:pre}}
.tw{{overflow-x:auto;border:1px solid var(--border);border-radius:10px}}
table{{border-collapse:collapse;width:100%;font-size:13.5px}}
th,td{{text-align:left;padding:8px 12px;border-bottom:1px solid var(--border);color:var(--text-dim)}}
th{{font:800 10.5px/1 'Inter',sans-serif;letter-spacing:.09em;text-transform:uppercase;color:var(--text-mute);background:var(--panel)}}
td.n{{text-align:right;font-variant-numeric:tabular-nums;color:var(--text)}}
tr:last-child td{{border-bottom:0}}
pre.soft{{white-space:pre-wrap;overflow-wrap:anywhere}}
.two{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:14px}}
.card{{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:16px 18px}}
.card h3{{margin:0 0 6px;font-size:15px;color:#fff}}
.card ul{{margin:0;padding-left:18px}}
</style></head><body>
<script>DV.mountHeader(document.body,'start');</script>
<main class="wrap" data-pagefind-body>
<h1>Start here</h1>

<h2 id="what">What this is</h2>
<p class="lead">DejaViewed is a curated archive of <b>{n}</b> saved posts from {creators} practitioners on AI tools, agents, creative code, art and quant, with <b>{transcripts}</b> speech transcripts and a runnable prompt system for every one of its <b>{len(guides)}</b> guides.</p>
<div class="stats">
<div class="stat"><div class="v">{n}</div><div class="l">entries</div></div>
<div class="stat"><div class="v">{len(colls)}</div><div class="l">collections</div></div>
<div class="stat"><div class="v">{transcripts}</div><div class="l">transcripts</div></div>
<div class="stat"><div class="v">{len(guides)}</div><div class="l">guides</div></div>
<div class="stat"><div class="v">{len(deepers)}</div><div class="l">deeper dives</div></div>
<div class="stat"><div class="v">{len(packs)}</div><div class="l">prompt systems</div></div>
</div>
<p>Posts date from {span}. Media mix: {media.get('video', 0)} videos, {media.get('carousel', 0)} carousels, {media.get('image', 0)} images. Every entry is tiered S, A, B or C ({tiers.get('S', 0)} S, {tiers.get('A', 0)} A, {tiers.get('B', 0)} B, {tiers.get('C', 0)} C) and tagged with tools, techniques and domains. Each entry links to the original post, which stays the property of its creator.</p>

<h2 id="who">Who it's for</h2>
<ul>
<li><b>People starting with AI agents</b> who want the practices that working builders actually use, with sources.</li>
<li><b>Builders</b> who want a step-by-step prompt system they can paste into Claude Code or another agent.</li>
<li><b>Researchers</b> tracking how practitioners talk about tools, with transcripts and structured tags to filter on.</li>
<li><b>Agents</b> that need a machine-readable index: plain-text and JSON endpoints, no login, no rate wall.</li>
</ul>

<h2 id="how">How to use it</h2>
<div class="two">
<div class="card"><h3>Humans</h3><ul>
<li>Read a <a href="guides/">guide</a>: thesis, evidence posts, then the prompt system at the bottom.</li>
<li>Copy the prompts from <a href="prompts.html">Prompts</a> into your agent and follow the step audits.</li>
<li>Browse the <a href="catalog.html">catalog</a> by tier, tool or creator, or use <a href="search.html">search</a>.</li>
<li>Subscribe to the <a href="feed.xml">RSS feed</a> for new entries and guides.</li>
</ul></div>
<div class="card"><h3>Agents</h3><ul>
<li><a href="llms.txt"><code>/llms.txt</code></a>: site map for language models.</li>
<li><a href="llms-full.txt"><code>/llms-full.txt</code></a>: every entry and deep dive as plain text.</li>
<li><a href="api/catalog.json"><code>/api/catalog.json</code></a>, <a href="api/prompts.json"><code>/api/prompts.json</code></a>, <a href="api/tools.json"><code>/api/tools.json</code></a>, <a href="api/creators.json"><code>/api/creators.json</code></a>.</li>
<li><a href="context.md"><code>/context.md</code></a>: domain-triggered context layer for session start.</li>
</ul></div>
</div>

<h2 id="cite">How to cite</h2>
<p>Plain text:</p>
<pre class="soft">{esc(plain)}</pre>
<p>BibTeX:</p>
<pre>{esc(bib)}</pre>
<p>When citing a single entry or guide, link its own page; when quoting a post, credit its creator and link the original.</p>

<h2 id="inside">What's inside</h2>
<p>Collections are the original save folders. Top domains are the three most frequent domain tags in each.</p>
<div class="tw"><table>
<thead><tr><th>Collection</th><th>Entries</th><th>S</th><th>A</th><th>Top domains</th></tr></thead>
<tbody>
{chr(10).join(rows)}
</tbody></table></div>
<p>Guides: {len(guides)}. Deeper dives: {len(deepers)}. Prompt systems: {len(packs)} with {steps} step prompts in total.</p>

<h2 id="cadence">Update cadence</h2>
<p>The site is rebuilt when a new batch of saves is pulled: each batch is captioned, transcribed, summarized, tiered and cross-linked before it is published. This catalog version was generated on <b>{gen_s}</b>. New entries and guides appear in the <a href="feed.xml">feed</a> and the <a href="sitemap.xml">sitemap</a>.</p>

<h2 id="contact">Contact and source</h2>
<ul>
<li>Curator: <a href="{AUTHOR_URL}" rel="noopener">@6ab3</a> on Instagram.</li>
<li>Site: <a href="{BASE}/">dejaviewed.dev</a>.</li>
<li>Source and the Claude Code skill that builds this site: <a href="{REPO_URL}" rel="noopener">github.com/Gabicus/dejaviewed</a>.</li>
</ul>
</main>
<footer class="site" style="margin:60px 0 40px;padding-top:30px;border-top:1px solid var(--border);color:var(--text-mute);font-size:12.5px;text-align:center"><a href="index.html" style="color:var(--text-dim)">← Back to DejaViewed</a></footer>
</body></html>
"""
    changed = write_if_changed(OUT, page, ignore_seo_block=True)
    print(f"start-here: {'written' if changed else 'unchanged'} ({n} entries, {len(colls)} collections, "
          f"{len(guides)} guides, {len(packs)} prompt systems)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
