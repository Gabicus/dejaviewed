# DejaViewed · primer

Updated: 2026-07-07

## Current status

581 entries across 15 collections. 146,252 crosslinks. 150 deep dives (21 curated, 1 featured). 31 guide pages. 21 deeper dive pages. CMS parquet is source of truth. Site live at dejaviewed.dev via Cloudflare Pages (auto-deploy from main).

### Coverage (as of July 8, 2026)
- Captions: 546/581 (5 IG failures, 30 non-IG URLs — expected)
- Transcripts: 510/581 (13 video failures, 58 images — no audio)
- Thumbnails: 570/581 (4 no og:image, 7 other)

### Collections (15)
ai1, ai2, ai3, ai4, ai5, ai6, ai7, quant, stock2, music, creative, prompts, game-theory, art-inspiration, art-i-like

### Active pages
- index.html — unified catalog, dynamic filters, deep dive cards with tier badges + date sort
- guides/index.html — filterable grid of all 31 guide pages (Featured/Guide/Standalone pills)
- guides/claude-mastery.html — FEATURED: comprehensive 9-section Claude reference (157 entries)
- guides/*.html — 13 curated insight guides + 18 tool/workflow guides
- deeper/*.html — 21 narrative deeper dive pages
- All guide + deeper pages have shared nav header + cross-links to siblings
- graph.html, graph-cosmos.html — standalone graph visualizations (D3 + Canvas)
- board.html, admin.html
- links/index.html, about/index.html

### Deep dive visual hierarchy
- **FEATURED** badge (pink gradient, pulse) — Claude Mastery, always sorted first
- **GUIDE** badge (purple) — 21 curated dives with full guide pages
- **DEEPER** badge (gold) — deeper dive narrative pages
- **AUTO** badge (dim) — 122 auto-detected dives
- Sort controls: Quality / Newest / Oldest / Most entries
- Date ranges computed from entry post dates

### Repo locations
- `~/Desktop/Projects/dejaviewed-plugin/` — main project (github.com/Gabicus/dejaviewed)
- `~/Desktop/Projects/dejaviewed.social/` — PRIVATE social pipeline
- `~/Desktop/Projects/graph-node/` — D3 force graph (generic, separate repo)
- `~/Desktop/Projects/graph-cosmos/` — Canvas orbital graph (generic, separate repo)

### Hosting
- **Cloudflare Pages** — auto-deploy from main branch, output dir `site/`
- Custom domain: dejaviewed.dev (Cloudflare DNS)

## What changed (July 6-7)

### AI7 + Creative bulk ingest (144 new entries)
- 99 ai7 + 73 creative entries ingested, enriched, deployed
- Fixed critical [NEEDS ENRICHMENT] parquet↔catalog.json sync bug (3-layer defense in cms.py)
- 364/581 entries transcribed via Whisper (remaining ~100 need IG auth cookies)
- Fixed deeper_dives.py `_esc()` to handle list prerequisites

### 7 new curated deep dives (14→21 total)
1. The Claude Harness Pattern (9 entries) — context/memory/harness engineering
2. MediaPipe × TouchDesigner Pipeline (10 entries) — body-to-art creative coding
3. The One-Person Studio (23 entries) — creative tech stack replacing teams
4. Beyond Prompting: Prompt Architecture (13 entries) — prompt engineering as discipline
5. Art Without Gatekeepers (12 entries) — AI disrupting art market
6. Autonomous Agents in the Wild (22 entries) — what works/fails in agent deployment
7. Claude Mastery (50 entries, FEATURED) — comprehensive setup-to-advanced guide

### Claude Mastery guide page
- 9 sections: Getting Started → CLAUDE.md → Skills/Hooks/MCP → Memory/Context → Prompts → Agents → Creative → Model Timeline → Reference Library
- 157 sourced entries with thumbnails and dates
- Strikethroughs for deprecated patterns with "replaced by" annotations
- Model timeline: Claude Code launch → Opus 4.6 → 4.7 → 4.8 → Fable 5
- JSON-LD structured data for AI crawler consumption
- Sticky nav jump bar, collapsible reference sections

### UI improvements
- Tier badges on all deep dive cards (FEATURED/GUIDE/DEEPER/AUTO)
- Date ranges on cards computed from entry post dates
- Sort controls (Quality/Newest/Oldest/Most entries)
- Guides index with tier filter pills (Featured/Guide/Standalone)
- Nav header mounted on all guide + deeper dive pages (was missing)
- Cross-links between 13 guide↔deeper dive pairs

## Scraping workflow (agent-browser)

```bash
# 1. Close Chrome (profile locked while running)
npx agent-browser close
npx agent-browser --profile Default --headed open "<collection_url>"

# 2. Extract URLs
bash scripts/ab_extract_urls.sh <name> "<url>"

# 3. Ingest
python3 scripts/ingest.py --urls-file data/<name>_urls.json --collection <name> --non-interactive

# 4. Scrape captions
python3 scripts/ab_scrape_posts.py

# 5. Enrich
python3 scripts/enrich_entries.py --sweep

# 6. Deep dives + guides
python3 scripts/deep_dives.py
python3 scripts/deeper_dives.py --all-curated

# 7. Rebuild CMS
python3 scripts/cms.py rebuild
```

## Next up

### High priority (COMPLETED July 8)
- ~~**Caption gaps:**~~ 161 scraped via `ab_scrape_posts.py --missing-captions`. 546/581 now have captions.
- ~~**Whisper transcription:**~~ 146 transcribed via `transcribe.py --all --model small`. 510/581 total.
- ~~**Thumbnails:**~~ 570/581. 4 remaining have no og:image (carousel/non-standard posts).
- ~~**Re-enrichment:**~~ All 581 re-enriched with new text data. Crosslinks 131K → 146K.
- ~~**Deep dive refresh:**~~ 150 dives regenerated, 21 curated deeper pages rebuilt.

### High priority (current)
- **R1 — Catalog→Claude recall loop:** Fix `build_context.py` (reads legacy catalog.jsonl, predates parquet) then wire catalog.json querying into session starts. See session-log.md 2026-07-13 for full recommendations R1-R6.
- **Skill published on site:** Ensure dejaviewed.dev advertises the skill and how to use it

### Skill architecture (July 13)
- ONE generic skill, TWO modes: `references/site-deployment.md` present = Operator Mode (Victor's install, deploys to dejaviewed.dev); absent = Public Mode (user builds own local site)
- Personal overlay is gitignored — NEVER commit it to the public repo
- Public repo ships `site-deployment.example.md` template instead
- Title-quality gate after any bulk enrichment: `title.len<14` count must be 0, S-rate <15%/collection (lesson #43)

### Medium priority
- **Claude Mastery guide maintenance:** Living document — update with new model releases, features, skills as they ship. Add new entries as they're ingested.
- **Re-enrich after transcription:** Once Whisper transcripts land, re-run `enrich_entries.py --sweep --reclassify` — transcripts dramatically improve tier/type/domain classification.
- **Deep dive refresh:** After caption + transcript gaps filled, regenerate deep dives — new connections will surface from richer text data.

### Low priority / ideas
- Consider auto-generating Claude Mastery guide sections from catalog data (currently hand-written HTML)
- Explore RSS/atom feed for new entries
- Keywords engine integration (parquet + spaCy + NetworkX from keyword-engine project)

## Don't forget

- NEVER change shared.css breakpoints for single-page issues
- ALWAYS push before destructive operations
- DESIGN.md is UI authority for all page styling
- agent-browser needs Chrome closed to read profile cookies
- Collection pills are dynamic — no HTML changes for new collections
- Graph pages are standalone in site/ — separate from graph-node/graph-cosmos repos
- "tutorial" merged into "skill" — don't add it back
- Verify entry IDs exist before writing manual_dives.json
- Guide/deeper pages must call `DV.mountHeader()` for nav
- Cross-links between guide↔deeper siblings via inline div (not template)
- [NEEDS ENRICHMENT] bug: 3-layer defense in cms.py (strip on read, strip on write, allow overwrite in upsert) — documented in dejaviewed skill
- Enrichment deletes parquet before internal migrate to avoid stale title merge
