# DejaViewed · primer

Updated: 2026-04-22 2:50pm EDT

## Current status

334 entries across 8 collections. 103 deep dives. 8 deeper dives. 43.5K crosslinks. 367 thumbnails — all entries covered. CMS parquet is source of truth. Site live at dejaviewed.dev via Cloudflare Pages.

### Repo locations
- `~/Desktop/Projects/dejaviewed-plugin/` — main project (github.com/Gabicus/dejaviewed)
- `~/Desktop/Projects/graph-node/` — D3 force graph (github.com/Gabicus/graph-node) — pushed
- `~/Desktop/Projects/graph-cosmos/` — Canvas orbital graph (github.com/Gabicus/graph-cosmos) — pushed

### Active pages
- index.html (unified catalog — all collections, filters, deep dive cards)
- graph.html, graph-cosmos.html, board.html, admin.html
- guides/ (18 deep dive guide pages)
- deeper/ (8 deeper dive narrative pages)
- Legacy pages in site/legacy/

### Hosting
- **Cloudflare Pages** — auto-deploy from main branch, output dir `site/`
- Custom domain: dejaviewed.dev (Cloudflare DNS)
- Manual fallback: `scripts/deploy.sh` (wrangler)
- Auto-deploy may need GitHub OAuth re-auth in Cloudflare dashboard

### Tools installed
- `gh` CLI (SSH auth as Gabicus)
- `wrangler` CLI (Cloudflare OAuth as gabe.dewitt@gmail.com)

## What changed this session

1. Pushed main to GitHub (full recovery commit a9362c6, 436 files)
2. Deployed site to gh-pages branch via safe temp-clone script
3. Set up Cloudflare Pages — Git-connected, auto-deploy from main, custom domain dejaviewed.dev
4. Installed + authed gh CLI and wrangler CLI
5. Fixed clickable links everywhere:
   - Deeper dive entries: thumb + title link to posts
   - index.html connection cards: clickable, open post in new tab
   - Both graph pages: removed broken "View in catalog", kept "Open post ↗"
6. Moved ai1-4, quant, catalog → site/legacy/
7. Rewrote sitemap.xml — active pages only, dejaviewed.dev domain
8. Fixed thumbnail display — shortcode() falls back to entry ID for non-IG entries
9. Scraped 29 missing thumbnails via Playwright embed endpoint (26 quant IG + 3 web)
10. All 334 entries now have thumbnails (367 files on disk)
11. Updated SKILL.md — site structure, Cloudflare deploy docs
12. Deleted dejaviewed-plugin-sitebackup/
13. Created scripts/deploy.sh (wrangler manual fallback)

## Next up

1. **Verify Cloudflare auto-deploy** — re-auth GitHub OAuth in Cloudflare dashboard if needed
2. **HTTPS enforcement** — enable once SSL cert provisions
3. **render_template.py cleanup** — dead per-collection page logic
4. **rebuild.sh audit** — 4 of 7 pipeline phases reference scripts that don't exist yet
5. **Graph data contract sync** — consider if graph pages should consume generic contract from repos

## Blockers

- Cloudflare GitHub OAuth token may be expired — auto-deploy may not trigger until re-authed

## Don't forget

- ALWAYS push before destructive operations
- DESIGN.md is UI authority for all page styling
- Admin page is safe on public site (localStorage only)
- `--reclassify` needed when enrichment dictionaries expand
- Thumbnail scraping: use `/embed/` endpoint for IG (no login required)
- wrangler and gh CLI both installed and authed
