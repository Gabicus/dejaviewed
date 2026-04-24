# DejaViewed · primer

Updated: 2026-04-24 1:45am EDT

## Current status

334 entries across 8 collections. 103 deep dives. 8 deeper dives. 43.5K crosslinks. 367 thumbnails. CMS parquet is source of truth. Site live at dejaviewed.dev via Cloudflare Pages (auto-deploy from main).

**New: Social media pipeline built.** Voice bible, 4 templates, 5 automation scripts, AI pulse monitor live, 7 drafts generated, story lifecycle tracker building.

### Repo locations
- `~/Desktop/Projects/dejaviewed-plugin/` — main project (github.com/Gabicus/dejaviewed)
- `~/Desktop/Projects/graph-node/` — D3 force graph (github.com/Gabicus/graph-node)
- `~/Desktop/Projects/graph-cosmos/` — Canvas orbital graph (github.com/Gabicus/graph-cosmos)
- `~/Desktop/Projects/wordpress/` — WP REST API reference for 1gabe.com

### Active pages
- index.html (unified catalog — all collections, filters, deep dive cards)
- graph.html, graph-cosmos.html, board.html, admin.html
- guides/ (18 deep dive guide pages), deeper/ (8 deeper dive narrative pages)
- links/index.html (personal bio/links page)

### Hosting
- **Cloudflare Pages** — auto-deploy from main branch, output dir `site/`
- Custom domain: dejaviewed.dev (Cloudflare DNS)
- Manual fallback: `scripts/deploy.sh` (wrangler)

### Tools installed
- `gh` CLI (SSH auth as Gabicus)
- `wrangler` CLI (Cloudflare OAuth as gabe.dewitt@gmail.com)

## Social media pipeline (NEW — Apr 24)

### Voice & Templates
- `social/VOICE.md` — brand voice bible (anti-pander, devil's advocate, can't-misunderstand rule)
- `social/templates/` — 4 templates: tool-spotlight, technique-howto, deep-dive-synthesis, art-visual

### Scripts
- `scripts/social_tracker.py` — post tracker (parquet CRUD, engagement tracking, unposted finder)
- `scripts/freshness.py` — time-weighted decay scoring (λ=0.01, 47 evergreens identified)
- `scripts/content_calendar.py` — auto-generate posting schedule (type mix: 40/30/20/10)
- `scripts/ai_pulse.py` — GitHub+HN+ArXiv trend aggregation (live data: claude, agent, llm trending)
- `scripts/fill_template.py` — entry → ready-to-post draft (7 drafts in social/drafts/)
- `scripts/story_lifecycle.py` — living story tracker: merge, split, evolve, version (building)

### Pipeline flow
```
ai_pulse.py scan → freshness.py score → story_lifecycle.py evolve →
content_calendar.py generate → fill_template.py --auto →
social_tracker.py add → POST → social_tracker.py update (engagement)
```

### Content philosophy
- Stories are living entities: seed → growing → mature → posted → evolving → archived
- Stories merge (B+B=A), split (broad → children), and version (thesis changes tracked)
- Every post gets: breakpoint disclosure + devil's advocate + counter-argument
- "Make things so people CAN'T misunderstand them" — permanent rule

### Skills installed (7 kept of 14 evaluated)
copywriting-core, youtube-pipeline, course-material-creator, book-marketing, brand-voice, industry-pulse, social-media-analyzer

### Still ahead
1. Story lifecycle script completion + init from deep_dives.json
2. `dejaviewed-social` orchestrator skill (one-command pipeline)
3. Platform API integration (instagrapi / Meta Graph API)
4. Phase space viz — dragon plots from Unicron project (pynamical + plotly)
5. `/schedule` routines for automated daily runs
6. Feedback loop: engagement data → adjust recommendations

## Key architecture

- **shared.css** — 900px global mobile breakpoint (NEVER change for page-specific issues)
- **index.html** — 1100px override via inline `<style>` for home page sidebar
- **graph.html** — D3 handles touch natively via d3.drag() and d3.zoom()
- **graph-cosmos.html** — manual Canvas + custom touch event listeners
- **shared.js** — DV.isMobile() at 900px, DV.mountMobileToggles() adds panel buttons + Done close

## Prior work (Apr 23)
- Mobile panel fix, cosmos touch controls, blog post published, SEO updates, WordPress reference

## Don't forget

- NEVER change shared.css breakpoints for single-page issues (broke graphs 3x)
- WordPress username is email (gabe.dewitt@gmail.com), not display name
- Yoast SEO meta desc NOT writable via REST — use excerpt field
- ALWAYS push before destructive operations
- DESIGN.md is UI authority for all page styling
- session-log.md has full tables/plans/tool audits from this session
- social/VOICE.md is authority for ALL content tone and style
