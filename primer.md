# DejaViewed · primer

Updated: 2026-05-06

## Current status

437 entries across 14 collections. 71,547 crosslinks. 14 curated insight dives. 24 guide pages. 14 deeper dive pages. CMS parquet is source of truth. Site live at dejaviewed.dev via Cloudflare Pages (auto-deploy from main).

### Collections (14)
ai1, ai2, ai3, ai4, ai5, ai6, quant, stock2, music, creative, prompts, game-theory, art-inspiration, art-i-like

### Active pages
- index.html — unified catalog, dynamic filters, deep dive cards, collection pills
- guides/index.html — filterable grid of all 24 guide pages
- guides/*.html — 6 insight analyses + 18 tool/workflow guides
- deeper/*.html — 14 narrative deeper dive pages
- graph.html, graph-cosmos.html — standalone graph visualizations (D3 + Canvas)
- board.html, admin.html
- links/index.html, about/index.html

### Repo locations
- `~/Desktop/Projects/dejaviewed-plugin/` — main project (github.com/Gabicus/dejaviewed)
- `~/Desktop/Projects/dejaviewed.social/` — PRIVATE social pipeline
- `~/Desktop/Projects/graph-node/` — D3 force graph (generic, separate repo)
- `~/Desktop/Projects/graph-cosmos/` — Canvas orbital graph (generic, separate repo)

### Hosting
- **Cloudflare Pages** — auto-deploy from main branch, output dir `site/`
- Custom domain: dejaviewed.dev (Cloudflare DNS)

## What changed this session (May 6)

### New collections ingested (103 entries)
- agent-browser (`npx agent-browser`) replaced Playwright MCP for IG scraping
- 6 stock2, 28 music, 30 ai6, 28 creative, 5 prompts, 6 game-theory

### Deep dives overhauled
- 14 curated insight dives (was 8) in manual_dives.json
- 6 new: agent-architecture, ai-trading-agents, claude-code-mastery, prompt-engineering, game-theory-ai, one-person-creative-studio
- 114 total dives (14 curated + 100 auto-detected)
- All 14 curated dives have deeper pages + full guide pages

### Guide pages system
- 24 total guide pages in site/guides/
- Guide index page at site/guides/index.html with filterable grid
- "Guides" nav pill added to shared.js (site-wide)
- Index deep dive cards link to both "Deeper Dive →" and "Full Guide →"

### Index page dynamic
- Collection pills generated from data (buildCollPills())
- Stats tagline computed at runtime
- "tutorial" type merged into "skill" (sidebar shows Skills: 50)
- Tutorials button removed from sidebar

### Enrichment improvements
- build_title() generates "Subject — angle" titles from captions
- classify_type_from_caption returns "skill" instead of "tutorial"
- Crosslinks jumped 70,810 → 71,547 from reclassification

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
# Generate guide pages for new curated dives

# 7. Rebuild CMS
python3 scripts/cms.py rebuild
```

## Don't forget

- NEVER change shared.css breakpoints for single-page issues
- ALWAYS push before destructive operations
- DESIGN.md is UI authority for all page styling
- agent-browser needs Chrome closed to read profile cookies
- `agent-browser close` between profile/session changes
- Collection pills are dynamic — no HTML changes for new collections
- Graph pages are standalone in site/ — separate from graph-node/graph-cosmos repos
- "tutorial" merged into "skill" — don't add it back
- Verify entry IDs exist before writing manual_dives.json
- Guide pages use markdown-in-script-tag + marked.js + DOMPurify
