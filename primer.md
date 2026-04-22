# DejaViewed · primer

Updated: 2026-04-22 10:30 EDT

## Current status

334 entries across 8 collections. 103 deep dives. 43.5K crosslinks. CMS parquet is source of truth. Fully recovered from deploy script incident.

### Repo locations
- `~/Desktop/Projects/dejaviewed-plugin/` — main project (github.com/Gabicus/dejaviewed)
- `~/Desktop/Projects/graph-node/` — D3 force graph (github.com/Gabicus/graph-node) — pushed
- `~/Desktop/Projects/graph-cosmos/` — Canvas orbital graph (github.com/Gabicus/graph-cosmos) — pushed

### Active pages
- index.html, ai1.html, graph.html, graph-cosmos.html, board.html, admin.html
- Legacy pages in site/legacy/

## What changed this session

1. Pushed graph-node and graph-cosmos repos to GitHub
2. SKILL.md fully rewritten — 903 lines, 15 phases, matches actual scripts
3. plugin.json bumped to v2.0.0 with graph repo dependencies
4. Added site/CNAME for dejaviewed.dev custom domain
5. INCIDENT: deploy script wiped .git — recovered all files from USB + sitebackup
6. Added CLAUDE.md rule: ALWAYS push before destructive operations
7. Legacy files moved to site/legacy/

## Next up

1. **Commit + push everything on main** (CRITICAL — push before any deploy attempt)
2. **Fix deploy script** — safe gh-pages deploy that can't kill .git
3. **Run deploy** — gh-pages branch for GitHub Pages
4. **Configure GitHub Pages** — custom domain dejaviewed.dev
5. **Verify DNS** — Cloudflare pointing to GitHub Pages

## Blockers

- None. All data recovered from USB.

## Don't forget

- ALWAYS push before destructive operations (deploy scripts, branch switches)
- DESIGN.md is UI authority for all page styling
- Admin page is safe on public site (localStorage only)
- `--reclassify` needed when enrichment dictionaries expand
