# DejaViewed · primer

Updated: 2026-05-08

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

## What changed (May 7-8)

### Vox Machina blog post (6702) — PUBLISHED
- Full post about building sardonic AI voice system (IRIS & SILAS)
- 10 matplotlib images (dark DejaViewed theme, SEO-named, clickable/zoomable)
- 4 audio embeds: IRIS demo, SILAS demo, raw TTS, IRIS final output
- Hero: cinematic split spectrogram (raw vs IRIS staircase pitch contour)
- Audio fix: 24kHz→44.1kHz resample (MPEG-2 silent in browsers), wp:html blocks not wp:audio
- SEO "Good", Readability "Good", keyphrase "sardonic AI voice"
- Timeline: "an evening and most of the night" (not "two weeks")

### Yoast SEO set on all 3 posts
- Vox Machina (6702) — keyphrase "sardonic AI voice", SEO Good, Readability Good
- AI Trading Agents (6682) — keyphrase "AI trading agents", SEO OK, Readability OK
- DejaViewed (6593) — keyphrase "Instagram saved knowledge graph", SEO OK, Readability Good
- Meta descriptions set via Draft.js execCommand in wp-admin
- Compact Audio Player plugin installed on WordPress

### WordPress skill overhauled
- 25 lessons learned (audio encoding, wp:html blocks, voice calibration, Yoast workflow)
- Full readability checklist (transition words 30%+, sentence/paragraph length, Flesch targets)
- SEO checklist (keyphrase placement, density, meta desc, alt text)
- Victor's real voice patterns documented from adventure/photo posts
- 10-step post composition workflow
- Skill now tracked in .claude git repo

### .claude brain committed
- wordpress-post skill added to git (was untracked)
- Caveman hooks added (activate, config, mode-tracker, statusline, fix-plugin-hooks)
- CLAUDE.md, settings.json, dejaviewed skill updated

## Previous session (May 6)

### Bulk ingest (103 entries from 6 collections)
- agent-browser replaced Playwright MCP for IG scraping
- Deep dives: 8→14 curated, 114 total, all with guide pages
- Guide index page, dynamic collection pills, tutorial→skill merge

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

## Don't forget

- NEVER change shared.css breakpoints for single-page issues
- ALWAYS push before destructive operations
- DESIGN.md is UI authority for all page styling
- agent-browser needs Chrome closed to read profile cookies
- Collection pills are dynamic — no HTML changes for new collections
- Graph pages are standalone in site/ — separate from graph-node/graph-cosmos repos
- "tutorial" merged into "skill" — don't add it back
- Verify entry IDs exist before writing manual_dives.json
- Guide pages use markdown-in-script-tag + marked.js + DOMPurify
- WordPress: curl not Python requests (WAF), `/wordpress-post` skill has full workflow
- WordPress voice: read Victor's REAL adventure/photo posts, not AI-written tech posts
- WordPress audio: always 44.1kHz MP3, use wp:html blocks, 3+ second demos
- WordPress images: `{post-slug}-{descriptive}.jpg`, clickable `<a href>` wraps
- Yoast keyphrase: wp-admin via Playwright, navigate dashboard first then window.location.href
