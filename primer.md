# DejaViewed · primer

Updated: 2026-04-23 4:30pm EDT

## Current status

334 entries across 8 collections. 103 deep dives. 8 deeper dives. 43.5K crosslinks. 367 thumbnails — all entries covered. CMS parquet is source of truth. Site live at dejaviewed.dev via Cloudflare Pages (auto-deploy from main).

### Repo locations
- `~/Desktop/Projects/dejaviewed-plugin/` — main project (github.com/Gabicus/dejaviewed)
- `~/Desktop/Projects/graph-node/` — D3 force graph (github.com/Gabicus/graph-node)
- `~/Desktop/Projects/graph-cosmos/` — Canvas orbital graph (github.com/Gabicus/graph-cosmos)

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

### Tools installed
- `gh` CLI (SSH auth as Gabicus)
- `wrangler` CLI (Cloudflare OAuth as gabe.dewitt@gmail.com)

## What changed this session

1. **Mobile responsive overhaul** (shared.css + shared.js):
   - Hamburger menu on mobile (≤900px), nav hidden by default
   - Bottom-sheet pattern with backdrop for controls + U-menu panels
   - Floating toggle buttons (Filters/Utils) for mobile panel access
   - Mid-range breakpoint (901-1100px): narrower sidebar, collapsed about grid
   - Compact U-menu on desktop (no scroll needed)
2. **Removed all "Victor" references** — replaced with generic user language across 28 files
3. **Removed all local path leaks** — `/home/victor/Desktop/Projects/...` → `~/projects/...`
4. **Fixed mid-range squash** — about-row grid collapse bumped to 1100px on index.html
5. Removed duplicate U-menu CSS from graph.html (now uses shared.css)
6. Committed ac7a08e, pushed to main → Cloudflare auto-deploy

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
