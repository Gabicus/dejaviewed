# DejaViewed.dev — Site-Specific Deployment Reference

This file contains deployment and state info specific to Victor's dejaviewed.dev instance.
The main SKILL.md is kept generic/platform-agnostic for public use.

## Hosting

- **Cloudflare Pages** — auto-deploy from main branch, output dir `site/`
- Custom domain: dejaviewed.dev (Cloudflare DNS)
- Repo: github.com/Gabicus/dejaviewed
- Graph engine repos: github.com/Gabicus/graph-node, github.com/Gabicus/graph-cosmos

## Current State (July 8, 2026)

- 581 entries across 15 collections
- 546/581 captions populated (35 missing: 5 IG failures, 30 non-IG URLs)
- 510/581 transcripts (13 video failures, 58 images with no audio)
- 570/581 thumbnails (4 no og:image, 7 other)
- 146,252 crosslinks across 9 dimensions
- 150 deep dives (21 curated, rest auto-detected)
- 31 guide pages (13 curated insight + 18 tool/workflow)
- 21 deeper dive narrative pages

## Collections (15)

ai1, ai2, ai3, ai4, ai5, ai6, ai7, quant, stock2, music, creative, prompts, game-theory, art-inspiration, art-i-like

## Active Pages

- index.html — unified catalog, dynamic filters, deep dive cards with tier badges + date sort
- guides/index.html — filterable grid of all guide pages (Featured/Guide/Standalone pills)
- guides/claude-mastery.html — FEATURED: comprehensive 9-section Claude reference (157 entries)
- guides/*.html — 13 curated insight guides + 18 tool/workflow guides
- deeper/*.html — 21 narrative deeper dive pages
- graph.html, graph-cosmos.html — standalone graph visualizations
- board.html, admin.html
- links/index.html, about/index.html

## Deep Dive Visual Hierarchy

- **FEATURED** badge (pink gradient, pulse) — Claude Mastery, always sorted first
- **GUIDE** badge (purple) — 21 curated dives with full guide pages
- **DEEPER** badge (gold) — deeper dive narrative pages
- **AUTO** badge (dim) — auto-detected dives
- Sort controls: Quality / Newest / Oldest / Most entries
- Date ranges computed from entry post dates

## Tier Distribution

S: 92, A: 178, B: 259, C: 52

## Deploy Workflow

1. Run pipeline steps as needed (scrape, enrich, deep dives, rebuild)
2. `git add` changed files
3. `git commit`
4. `git push origin main` — Cloudflare auto-deploys

## Private Pipeline Repo

- `~/Desktop/Projects/dejaviewed.social/` — PRIVATE social pipeline (not public)

## Known Gaps (non-fixable)

- 30 non-IG entries (GitHub repos, archive.org, etc.) will never have IG-style captions
- 5 IG posts that return no text from `get text "main"` (private/deleted/login-walled)
- 13 video download failures (images mis-tagged as video, private posts)
- 4 thumbnails with no og:image (carousels/non-standard IG rendering)
