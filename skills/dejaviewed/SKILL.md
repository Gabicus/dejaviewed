---
name: dejaviewed
description: >
  Turn saved posts and bookmarks from ANY platform into a searchable, curated dark-mode
  catalog site with deep-dive guides, knowledge graphs, and an agent context layer.
  Supports Instagram, TikTok, Twitter/X, Chrome/Edge/Firefox bookmarks, Pinterest, Reddit,
  YouTube. Full pipeline: ingest → classify → enrich → tier → deep dives → graphs → render.
  Triggers: "dejaviewed", "instagram catalog", "saved posts", "curate my saves",
  "bookmark catalog", "action plan from saves".
skill_api_version: 1
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash, Write, Edit, Agent, WebFetch, WebSearch
metadata:
  tier: execution
  dependencies:
    - name: graph-node
      purpose: D3 force-directed graph visualization
      data_contract: generic (nodes/edges with group/weight/tags/metadata)
    - name: graph-cosmos
      purpose: Canvas orbital physics visualization
      data_contract: generic (nodes/edges with group/weight/tags/metadata)
context:
  window: inherit
  intent:
    mode: task
  intel_scope: none
---

# /dejaviewed — Turn Your Saves Into a Real Site

> **Tagline:** "You've saved this before."
>
> You scroll, you tap save, you swear you'll come back. You don't. Your Saved tab fills up
> with posts you half-remember. DejaViewed hands the whole pile to Claude: every save gets
> read, classified, tiered, and — for the ones worth the dig — turned into a real deep-dive
> guide with the links the creator wouldn't give you.

**YOU MUST EXECUTE THIS WORKFLOW. Do not just describe it.**

---

## Two Modes: Public vs Operator

**Check FIRST, before any pipeline work:** does `references/site-deployment.md` exist in this installed skill?

| | **Public Mode** (file absent) | **Operator Mode** (file present) |
|---|---|---|
| Who | Anyone who installed the skill from GitHub | The site owner's own machine |
| Builds | User's OWN local catalog site from THEIR saves | Owner's established instance |
| Deploy | Local preview by default; OFFER static hosting options, never assume a target | Read `references/site-deployment.md` for hosting, domain, collections, deploy workflow — deploy there when asked |
| First run | Offer to create their own `site-deployment.md` from `site-deployment.example.md` once they pick hosting | Overlay already exists — follow it |

**Public Mode rules:**
- NEVER reference or deploy to any pre-existing site (e.g. dejaviewed.dev) — that is the original author's instance, not yours
- Everything is built locally in the user's project dir; `site/` is self-contained static files
- The user's collections, counts, and gaps are THEIRS — discover them from their data, don't assume any

**Operator Mode rules:**
- `references/site-deployment.md` is the single source of truth for instance-specific facts (hosting, domain, collections, coverage stats, known gaps)
- Keep that file updated after big pipeline runs — never write instance-specific facts into this SKILL.md
- The overlay file is private. Never commit it to the public skill distribution.

---

## Quick Start

```bash
/dejaviewed https://www.instagram.com/<user>/saved/<collection>/<id>/
/dejaviewed https://www.instagram.com/<user>/saved/<coll1>/<id1>/ https://www.instagram.com/<user>/saved/<coll2>/<id2>/
```

The user provides one or more saved collection URLs. Claude does everything else:
1. Extracts all post URLs via Playwright MCP (automated browsing)
2. Ingests each post via `scripts/ingest.py` (scrape + dedupe + upsert into parquet)
3. Enriches with `scripts/enrich_entries.py` (classify, tier, extract tools/techniques/domains)
4. Generates deep dives + deeper dives (cluster analysis + narrative pages)
5. Rebuilds CMS exports, graphs, digest, API, and static site

### One-Call Rebuild (end-to-end)

```bash
scripts/rebuild.sh --collections ai8=2012637673459860 creative=18530277145076636   # name=<collection_id>
```

Skip phases with `--skip <phase>[,<phase>...]`. Phases (in order):

| Phase | Script | What it does |
|-------|--------|--------------|
| `pull` | `scripts/ig_collection_api.py` | Collection-feed API → `data/<name>_api.json` (captions, creator, date, media URLs) |
| `media` | `scripts/ig_download_media.py` | Thumbs → `site/thumb/`, videos + carousel slides → `data/media/` (URLs expire in hours) |
| `ingest` | `scripts/ingest_api.py` | Upsert rows with caption/creator/date/media_type already filled; dedupe by shortcode |
| `transcribe` | `scripts/transcribe.py --all --local-only` | Whisper from local mp4 (GPU int8_float32 → CPU fallback) |
| `sync` | `scripts/cms.py rebuild` | parquet → catalog.json — MUST run before enrich (lesson #50) |
| `enrich` | `scripts/enrich_entries.py --sweep` | Heuristic tools/techniques/domains/tier/title pass |
| `verify` | `scripts/ig_refresh_captions.py [--apply]` | Re-fetch caption/creator/date per post with page-id verification; fixes stale-page scrapes |
| `llm` | `scripts/llm_enrich_batches.py export/merge` | Batches for enrichment agents (title/summary/tier/tags from caption+transcript+OCR); merge back |
| `gate` | `scripts/quality_gate.py` | Hard gates: 0 bad titles, S ≤15%, every video transcribed or reason logged, every entry thumbed |
| `curate` | `scripts/curation_export.py` | Digest for the researcher curation pass (Phase 5c) |
| `dives` | `scripts/deep_dives.py` | Auto-detect + merge curated dives |
| `deeper` | `scripts/deeper_dives.py --all-curated` | Narrative deeper-dive pages |
| `prompts` | `scripts/prompt_systems.py` | One prompting system per curated dive + hand-written guide (Phase 5d) — export, agents, merge, render |
| `guides` | `scripts/build_guides.py` | Full guide pages + `guides/index.html` (embeds prompt systems) |
| `start` | `scripts/build_start_here.py` | `start-here.html` positioning page with live counts (what/who/how to cite) |
| `feed` | `scripts/build_feed.py` | `feed.xml` RSS of newest entries + guides |
| `og` | `scripts/build_og.py` | 1200×630 share images for guides/deeper/top pages |
| `seo` | `scripts/build_seo.py` | canonical, description, OG/Twitter, JSON-LD (WebSite, Dataset, Article, FAQPage, Breadcrumb) on every public page — runs last, idempotent |
| `monetize` | `scripts/build_monetize.py` | `/go/<slug>` redirects (`site/_redirects`), tool links via /go/, footer CTA, disclosure/tip-jar only when configured in `data/monetize/` — after `seo`, idempotent |
| `collections` | `scripts/build_collections.py` | 18 static collection hubs; every page ≤2 clicks from home |
| `tools` | `scripts/build_tools.py` | /tools/<slug> hubs from `data/tools/*.json` takes; thresholds decide indexed vs noindex |
| `compare` | `scripts/build_compare.py` | /compare/, /best/, /system-prompts from `data/compare/*.json` (dated sources) |
| `links` | `scripts/normalize_links.py` | clean root-absolute URLs + static footer nav — LAST HTML-touching phase |
| `analytics` | `scripts/analytics_report.py` | Cloudflare GraphQL + Search Console report → `reports/analytics_<date>.md`; skips with exact setup steps when creds absent |
| `landing` | `scripts/build_landing_meta.py` | `site/landing_meta.js` — guide/deeper slugs the showcase `index.html` links to |
| `digest` | `scripts/digest.py` | summaries.json / recommendations.json |
| `rebuild` | `scripts/cms.py rebuild` | Crosslinks + exports |
| `api` | `scripts/build_api.py` | `site/api/*.json`, per-entry pages, sitemap.xml |
| `context` | `build_context.py` | context.md, llms.txt, llms-full.txt, ai-plugin.json (counts computed live) |
| `render` | `scripts/render_template.py` | Collection page HTML |
| `js` | `scripts/catalog_js.py` | `window.__CATALOG` wrappers for file:// previews |

`llm` and `curate` stop the script with instructions — they need agents in the loop. Legacy phases
(`scrape`/`captions`/`process`/`migrate`/`thumbs`) still exist as scripts for the v2 fallback path.

**The user should NEVER need to:**
- Open DevTools or run console scripts
- Manually extract URLs from any page
- Copy-paste data from their browser
- Do any step that Claude can automate

---

## Architecture Overview

### Data Layer (Parquet CMS)

Source of truth: `data/entries.parquet` (one row per post/resource).

```
scripts/cms.py — the CMS engine (688 lines)
  migrate      seed parquet from site/catalog.json
  rebuild      recompute crosslinks + refresh catalog.json/catalog.js
  check        validate parquet integrity
  stats        DuckDB-powered analytics over the store
  apply-patch  merge admin UI edits from data/patches.json
```

**Three parquet files:**

| File | Schema | Purpose |
|------|--------|---------|
| `data/entries.parquet` | 40 fields (SCHEMA) | Every post/resource |
| `data/crosslinks.parquet` | a_id, b_id, dim, weight | Precomputed pairs for graphs |
| `data/deep_dives.parquet` | 20 fields (DEEP_DIVE_SCHEMA) | Deep dive clusters |

**Entry schema** (key fields):

| Field | Type | Notes |
|-------|------|-------|
| id | string | Stable hash of url+post_id |
| post_id | string | Platform shortcode |
| url | string | Source URL |
| source_collection | string | Original collection |
| collections | list[string] | All collections containing this entry |
| creator | string | @handle |
| title | string | "Subject — angle" format |
| summary | string | 1-3 sentences |
| caption | string | Full original caption |
| type | string | technique, tool, repo, guide, etc. |
| tier | string | S, A, B, C |
| tags, domains, tools, techniques, models, repos | list[string] | Extracted metadata |
| transcript | string | Whisper/IG CC transcript |
| medium, style_tags, subject_matter, color_palette | various | Art-specific fields |
| thumb_path | string | Local thumbnail path |

**Crosslink dimensions:** creator, tool, technique, domain, tier, type, collection, medium, style_tag

### Site Structure

```
site/
  index.html           Showcase landing: live stats, destinations, curated insight dives, freshest saves, install
  catalog.html         Unified catalog: filters, creators chart, deep dive cards, all entries
  <collection>.html    Per-collection catalog page (legacy)
  graph.html           D3 force-directed graph (powered by graph-node)
  graph-cosmos.html    Canvas orbital graph (powered by graph-cosmos)
  board.html           Drag-to-connect thought board
  admin.html           Entry editor (patches to data/patches.json)
  shared.css           Design system tokens + component library
  shared.js            DV namespace: nav, loadCatalog, el(), tierPill
  catalog.json         Full catalog export
  summaries.json       Digest cluster summaries
  recommendations.json Digest ranked recommendations
  sitemap.xml          All URLs
  llms.txt             LLM discovery file
  llms-full.txt        Full LLM context
  robots.txt           Crawler rules
  thumb/               Downloaded thumbnails
  api/                 Machine-readable JSON exports
    catalog.json
    creators.json
    tools.json
    collections.json
    deep_dives.json
  guides/              Deep dive guide pages
  deeper/              Deeper dive narrative pages
  legacy/              Archived pages
```

### Graph Repos (External Dependencies)

Both graph repos use a **generic data contract**. DejaViewed maps its domain vocabulary into the generic schema:

| DejaViewed field | Graph contract field | Notes |
|-----------------|---------------------|-------|
| `source_collection` | `group` | Node grouping/color |
| `tier` (S=10, A=7, B=4, C=2) | `weight` | Node size |
| `[tools, techniques, domains, tags]` | `tags[]` | Merged tag array |
| `{title, summary, url, creator, tier}` | `metadata{}` | Free-form tooltip data |
| crosslinks (a_id, b_id, dim, weight) | `edges[]` | Direct mapping |

**graph-node** (D3 force-directed):
- D3 force-directed SVG graph
- Sidebar filters by group, search, node detail panel
- Data: `{ nodes: [...], edges: [...], config: { title, groupColors } }`

**graph-cosmos** (Canvas orbital):
- Canvas-based orbital physics with hierarchical orbits
- Presets, responsive breakpoints, tooltip overlays
- Same data contract as graph-node

**Relationship:** DejaViewed ships its own graph pages (`site/graph.html`, `site/graph-cosmos.html`) with DejaViewed-specific UX (shared.css theme, nav, tier colors, catalog.json loading). The graph engines are clean-room implementations using a generic data contract — usable by anyone with any dataset. They share the same data contract spec but are independent codebases, not runtime imports.

---

## Prerequisites

### What the user provides:
1. **One or more saved collection URLs** — e.g., `https://www.instagram.com/user/saved/mycollection/12345/`
2. **A Chrome install with an active Instagram session** (agent-browser reads its profile directly)

### What must exist on disk:
1. **Chrome with logged-in Instagram session**
   - agent-browser reads Chrome's profile via `--profile Default` — no profile copy needed
   - Chrome must be CLOSED when agent-browser (or yt-dlp cookie reads) run — the profile is locked while Chrome runs

2. **Python 3.10+** with packages:
   ```bash
   pip install requests pyarrow duckdb pandas
   pip install yt-dlp faster-whisper   # for video transcription
   ```

3. **Node.js with npx** — agent-browser installs on first `npx agent-browser` run

4. **ffmpeg on PATH** — for Whisper audio extraction (`ffmpeg` + `ffprobe`)

**Legacy (deprecated):** the old flow used a Chrome profile copy at `.profile-copy/Default/Cookies` + Playwright MCP. agent-browser replaced both. `browser-cookie3` is only needed if using the legacy adapters.

### First-time project setup:
```bash
mkdir -p <project>/data <project>/guides <project>/site/thumb <project>/site/guides <project>/site/deeper <project>/site/api <project>/.playwright-mcp
```

---


## Phase 0 (v3, preferred): Collection-Feed API via CDP-attached Chrome

**Use this instead of scroll-scraping.** Found 2026-10-21: scroll extraction stalls at 12 posts on
small collections and silently loses posts on large ones; Instagram's internal collection-feed API
returns everything, paginated, with caption, creator, date, media type, thumbnail URL and video URL
in one call — no per-post caption scrape needed.

### Why agent-browser's own Chromium can't see your login (Chrome ≥ 136)
agent-browser launches its bundled Chromium with `--password-store=basic --use-mock-keychain`, so it
cannot decrypt cookies from a real Chrome profile (KDE wallet / GNOME keyring encrypted). `--profile
Default` therefore shows a logged-out Instagram even though `sessionid` exists. Fix: drive the REAL
Chrome over CDP.

```bash
# 1. Quit Chrome completely (pgrep -c chrome must be 0)
# 2. Copy the profile essentials to a scratch user-data-dir (Chrome ≥136 refuses --remote-debugging-port on the default dir)
D=$SCRATCH/chrome-cdp; mkdir -p $D/Default; cp ~/.config/google-chrome/"Local State" $D/
for f in Cookies Network Preferences "Secure Preferences" "Login Data" "Web Data"; do cp -r ~/.config/google-chrome/Default/"$f" $D/Default/; done
# 3. Launch real Chrome with a debug port (setsid so the tool shell can return)
setsid nohup /opt/google/chrome/chrome --remote-debugging-port=9222 --user-data-dir=$D --no-first-run "https://www.instagram.com/<user>/saved/" >/dev/null 2>&1 < /dev/null & disown
# 4. Attach
npx agent-browser connect 9222
npx agent-browser get text "main"     # must show "Edit profile" + collection names, not "Log In"
```
If the saved page shows "Log In": log into Instagram in regular Chrome first, quit Chrome, redo steps 2-4.

### Discover collections + ids
```bash
npx agent-browser eval 'JSON.stringify([...document.querySelectorAll("a[href*=\"/saved/\"]")].map(a=>a.getAttribute("href")).filter(h=>!h.includes("?hl=")))'
# -> "/<user>/saved/<name>/<collection_id>/"
```

### Pull every post in a collection (paginated API, run from page context)
```bash
python3 scripts/ig_collection_api.py ai8 2012637673459860 creative 18530277145076636 ...
# -> data/<name>_api.json  {items:[{code, pk, taken_at, media_type(1 img|2 video|8 carousel), creator,
#    caption, like/comment/play counts, video_duration, thumb_url, video_url, carousel:[{img,vid}], ...}]}
```
Endpoint: `/api/v1/feed/collection/<id>/posts/?max_id=<next_max_id>` with headers
`x-ig-app-id: 936619743392459`, `x-csrftoken` from cookie. 12 items/page.

### Download media IMMEDIATELY (signed CDN URLs expire in hours)
thumbs → `site/thumb/<code>.jpg`; videos → `data/media/<code>.mp4` (gitignored); carousel slides →
`data/media/<code>_slide<N>.jpg|mp4`. Plain `requests` with a browser UA + instagram Referer works.

### Ingest with fields already populated
```bash
python3 scripts/ingest_api.py data/<name>_api.json --collection <name>
# or a merged list with per-item "collection" keys
```
Dedupe is by shortcode: new IG URLs look like `/<creator>/reel/<code>/`; parquet stores `/p/<code>/`.
Same post saved in two collections → one row, `collections` merged.

### Transcribe from local files on the GPU
`transcribe.py` now prefers `data/media/<post_id>.mp4` (no yt-dlp, no cookies), caches the model,
and tries CUDA `int8_float32` (fp16 is NOT supported on Pascal cards like GTX 1050) before CPU int8.
`--local-only` skips entries whose mp4 isn't downloaded yet. `medium` model ≈ 5× realtime on a 1050.
Run it detached (`setsid nohup ... &`) — it saves to parquet after every file.

**Parquet write race:** transcribe.py holds its own row list and writes the full set after each file.
Do NOT run anything else that writes `entries.parquet` (ingest, enrich, media_type fixes) while it runs —
the next transcribe save will clobber your change. Queue those edits until the loop ends.

### Old posts that are no longer in any collection
Open the post page, read `instagram://media?id=<pk>` from the HTML, then
`/api/v1/media/<pk>/info/` gives video_url / carousel_media. Posts returning `media_type: 8` that the
catalog tagged "video" are carousels — fix `media_type` and OCR the slides instead of Whisper.

### Carousel / image posts: read the slides
No audio → no Whisper. Download slides, then have a vision-capable agent Read each image and write
verbatim text to `data/slides_ocr.json` (`{code: text}`); `llm_enrich_batches.py export` picks it up.

## Phase 0 (v2, fallback): URL Extraction via agent-browser

**THIS IS THE CRITICAL AUTOMATION STEP. NEVER SKIP IT. NEVER ASK THE USER TO DO THIS MANUALLY.**

**agent-browser** (`npx agent-browser`) replaces Playwright MCP for Instagram scraping. It reads Chrome's login state directly via `--profile Default`.

### Prerequisites
- Chrome must be CLOSED (profile is locked while Chrome runs)
- User must be logged into Instagram in Chrome
- `npx agent-browser` available (installs on first run)

### Step 0.1: Open collection and extract URLs

```bash
# Close any existing agent-browser daemon
npx agent-browser close

# Open collection page with Chrome's login state
npx agent-browser --profile Default --headed open "<collection_url>"

# Run the scroll-and-extract script
bash scripts/ab_extract_urls.sh <collection_name> "<collection_url>"
```

`ab_extract_urls.sh` scrolls the collection page, waits for stability (3 rounds same count = done), extracts all `a[href*="/p/"]` and `a[href*="/reel/"]` links, writes to `data/<name>_urls.json`.

### Step 0.2: If login is needed

If agent-browser shows a login page:
```bash
npx agent-browser close
npx agent-browser --profile Default --headed open "https://www.instagram.com/"
# Tell user to log in manually in the headed browser window
# After login confirmed, re-run extraction
```

### Step 0.3: Ingest URLs into parquet

```bash
python3 scripts/ingest.py --urls-file data/<name>_urls.json --collection <name> --non-interactive
```

### Step 0.4: Scrape captions from posts

```bash
python3 scripts/ab_scrape_posts.py                          # targets [NEEDS ENRICHMENT] entries only
python3 scripts/ab_scrape_posts.py --missing-captions       # targets ALL entries with empty captions
python3 scripts/ab_scrape_posts.py --missing-captions --collection col1 col2  # specific collections only
```

Uses `get text "main"` (not JS eval — IG DOM is obfuscated). Python text parsing finds time markers, extracts creator + caption. Saves progress every 20 posts.

**IMPORTANT:** After initial enrichment, entries get titles but may still have empty captions. The default filter (`[NEEDS ENRICHMENT]` title check) will skip them. Use `--missing-captions` to target enriched entries that still lack captions. This is the normal second-pass workflow.

### agent-browser Troubleshooting

- **Daemon stale / profile ignored:** `npx agent-browser close` then restart with `--profile Default`
- **Double-encoded JSON from eval:** agent-browser `eval` wraps return in JSON string. Unwrap: `json.loads(json.loads(raw))`
- **JS eval returns 0 results:** IG DOM is obfuscated. Use `get text "main"` + Python text parsing instead
- **URL file has brackets/quotes:** Strip with `url.strip().strip('"').strip(',').strip('"')`
- **ingest.py EOF error:** Use `--non-interactive` flag to skip ig_session_id prompt
- **Chrome locked:** Close Chrome before running agent-browser with `--profile Default`
- **IG DOM unloading:** Use `scripts/ab_extract_cumulative.py` (NOT `ab_extract_urls.sh`) — cumulative extraction handles DOM element recycling during scroll
- **URL format:** `ab_extract_cumulative.py` outputs JSON arrays. Convert to one-URL-per-line .txt before `ingest.py`, or pipe through: `python3 -c "import json,sys;[print(u) for u in json.load(open(sys.argv[1]))]" data/urls.json > data/urls.txt`

### Legacy: Playwright MCP approach (deprecated)

The old approach used Playwright MCP + Chrome profile copy (`.profile-copy/Default/Cookies` SQLite extraction). This fails when Chrome is running (locked profile). agent-browser replaced it entirely.

---

## Phase 1: Ingest (scripts/ingest.py)

The unified ingestion CLI. Reads URLs, dedupes against parquet, scrapes new ones, upserts.

```bash
python scripts/ingest.py --urls-file data/<collection>_urls.json --collection <collection>
python scripts/ingest.py --url https://instagram.com/p/XXX/ --collection <collection>
echo "https://instagram.com/p/XXX/" | python scripts/ingest.py --collection <collection>
```

**What ingest.py does:**
1. Loads existing entries from `data/entries.parquet` via cms.py
2. Dedupes incoming URLs against existing entries
3. For new URLs: creates placeholder entries; captions come from `ab_scrape_posts.py` (Phase 0.4)
4. Upserts each row into the parquet store
5. Recomputes crosslinks
6. Refreshes catalog exports (`site/catalog.json`, `site/catalog.js`)

Scraped fields are minimal — url, post_id, source_collection, caption, creator, date, media_type. Enrichment (tier, type, domains, tools, techniques) happens in Phase 3.

**CRITICAL SECURITY RULES:**
- Cookie values are NEVER printed, logged, written to any file, or echoed
- Only existence checks: `sessionid present: yes/no`
- Cookies stay inside `requests.Session` and are garbage-collected on exit

**Retry logic:** 429/5xx — exponential backoff (5s * attempt). 404/410 — record as dead. 3 attempts max.

**LESSONS LEARNED:**
- `og:description` is TRUNCATED (~150 chars). Real caption lives in `<script type="application/json">` embedded JSON blobs. ALWAYS extract from embedded JSON first, fall back to og:description.
- IG signed CDN URLs (`scontent.cdninstagram.com`) expire within hours. NEVER hotlink — download to local `site/thumb/`.
- Some posts return 200 but contain a login wall. Check for `"loginRequired"` in response body.

---

## Phase 2: Process Raw Data (scripts/process_raw.py)

Converts Playwright-scraped raw JSON into catalog entries, dedupes, merges.

```bash
python scripts/process_raw.py --raw data/<collection>_raw.json --collection <collection>
```

For batch scrapes that produce raw JSON dumps, this normalizes data into the catalog schema before CMS migration. For single-URL ingestion, `ingest.py` handles this internally.

---

## Phase 3: CMS Migration (scripts/cms.py migrate)

Migrates data from `site/catalog.json` into the parquet layer.

```bash
python scripts/cms.py migrate
```

Seeds `data/entries.parquet` from catalog.json. Existing entries are matched by URL/post_id and updated (not duplicated). New entries are appended.

### CMS Operations Reference

| Command | What it does |
|---------|-------------|
| `cms.py migrate` | Seed/update parquet from site/catalog.json |
| `cms.py rebuild` | Recompute crosslinks + refresh catalog.json/catalog.js from parquet |
| `cms.py check` | Validate parquet integrity |
| `cms.py stats` | DuckDB analytics: counts by collection, tier, type, top creators |
| `cms.py apply-patch` | Merge admin UI edits from data/patches.json |

### Admin Patches

The admin page (`site/admin.html`) writes edits to `data/patches.json`. On next `cms.py apply-patch` (or during rebuild), patches are merged into parquet. Fields: title, summary, tier, type, tags, user_notes, favorited.

---

## Phase 4: Enrich (scripts/enrich_entries.py)

Classifies, tiers, and extracts structured metadata from every entry.

```bash
python scripts/enrich_entries.py --sweep              # enrich all un-enriched
python scripts/enrich_entries.py --sweep --reclassify  # re-evaluate ALL entries
```

**What enrichment does** (447 lines of heuristic rules + keyword matching):
- **Tier assignment:** S (exceptional, deep, linkable), A (solid, actionable), B (useful reference), C (thin/low-signal)
- **Type classification:** technique, tool, repo, guide, platform, resource, art, design, ui/ux
- **Metadata extraction:** domains, tools (80+), techniques (45+), models (40+), repos, takeaways
- **Title generation:** "Subject — angle" format (never bare names, never `@creator:` prefixes)
- **Summary writing:** 1-3 sentences naming concrete things

### TITLE RULES (critical — user WILL complain if you get this wrong):

- Format: `Subject — angle` (em-dash, not hyphen)
- Subject = the actual tool/technique/concept
- Angle = why it matters or what it enables
- BAD: "Claude Code", "Python Tips", "@johndoe: cool stuff"
- GOOD: "Claude Code — real-time terminal agent for any codebase"
- GOOD: "Heston Model — closed-form vol surface from 5 parameters"

### SUMMARY RULES:

- 1-3 sentences. Name concrete things (tools, techniques, repos).
- No marketing fluff. No "In this post, the creator discusses..."
- What is it, what does it do, why should you care.

### DROP RULES:

- Drop only if: no subject named, pure self-promo with no content, duplicate of richer entry
- 10-20% drop rate max. Be generous when a subject is named.
- First pass dropped 74/170 (43%) — user wanted them back. Don't over-drop.

### LINK EXTRACTION (every card needs links):

- URLs from caption text
- @handles — Instagram profile links
- Known-tool URL dictionary (tool name — official site/repo)
- Links from embedded JSON blobs

`--reclassify` re-evaluates type/tier/domains for ALL entries. Required when enrichment dictionaries expand.

`--sweep` merges new keywords (union), never overwrites manual edits.

---

## Phase 5: Deep Dives + Deeper Dives

### Deep Dives (scripts/deep_dives.py)

Auto-detects natural groupings by analyzing crosslinks and entry metadata.

```bash
python scripts/deep_dives.py
```

**6 insight classes:** emergent_capability, workflow_multiplier, arbitrage_opportunity, creative_fusion, expression_amplifier, life_leverage

**Output:** `data/deep_dives.parquet` + `data/deep_dives.json`

Each deep dive has:
- Title, thesis, summary
- Entry IDs + connection map (entry to role description)
- Anchor tag, tier, quality rating (1-5)
- Execution difficulty (Easy/Medium/Hard/Experimental)
- Action sketch (concrete next steps)
- Curated flag (pinned dives survive regeneration via `manual_dives.json`)

**Display:** Index page shows deep dive cards in a grid. Click opens inline detail panel (thesis, connected entries with thumbnails, action sketch). Category filters across dive types.

### Deeper Dives (scripts/deeper_dives.py)

Full narrative pages generated from selected deep dives. Tier 2 of the insight system.

```bash
python scripts/deeper_dives.py                     # all curated dives
python scripts/deeper_dives.py --dive-id dd-xxx    # specific dive
python scripts/deeper_dives.py --all-curated       # all pinned dives
python scripts/deeper_dives.py --dry-run            # preview without writing
```

**Produces:** Full HTML pages in `site/deeper/` with:
- Narrative: thesis, evidence (connected entries), synthesis, action plan
- Embedded entry cards with thumbnails
- Cross-references to related deep dives
- Same dark theme as all other pages

### Deep Dive Curation Workflow (IMPORTANT — do this every session)

After enrichment, curate the best cross-cutting themes as insight dives:

1. **Identify themes:** Find S/A-tier entries sharing tools/techniques across collections
2. **Create curated dives** in `data/manual_dives.json` with full schema:
   - id, title, class (6 insight classes), thesis, entry_ids, connection_map
   - quality_rating (1-5), execution_difficulty, value_type, action_sketch
   - suggested_by: "curated", pinned: true, why_it_matters, prerequisites
3. **Verify entry IDs exist** in catalog before saving
4. **Regenerate:** `python3 scripts/deep_dives.py` (merges curated + auto-detected)
5. **Generate deeper pages:** `python3 scripts/deeper_dives.py --all-curated`
6. **Generate guide pages:** Run the guide page generator (see Phase 5b below)

### Phase 5b: Guide Page Generation

Every curated dive gets a full guide page in `site/guides/`. Template:

```
HTML shell: shared.css + shared.js + inline guide styles
<article class="guide">
  <div class="confidence-badge {high|medium}">Source confidence: {level}</div>
  <div id="guide-body"></div>
</article>
<script id="md" type="text/markdown">
  # Title
  ## Thesis / ## Why it matters / ## The evidence / ## Action sketch / ## Prerequisites
</script>
<script src="marked.min.js"></script> + DOMPurify
```

- Slug: `d.id.replace('dd-insight-', '')` → `{slug}.html`
- Confidence: high if quality_rating >= 5, medium otherwise
- Guide index page at `site/guides/index.html` lists all guides with filters
- Nav link "Guides" in shared.js DV.nav links to `guides/`
- Index.html deep dive detail panel shows "Full Guide →" for curated dives


### Phase 5c: Researcher Curation Pass (REQUIRED before every publish)

Auto-detected dives cluster by shared tags. That is filing, not insight. Before publishing, run a
**researcher pass** that reads across *every* entry and looks for novel ideas that live *between*
the technologies — combinations of captured capabilities that let one person create or pioneer
something not possible (or not obvious) before.

1. Export a compact digest of the whole catalog + the existing curated dives:
   ```bash
   python3 scripts/curation_export.py        # -> data/curation/catalog_digest.json, existing_dives.json
   ```
2. Spawn 2–4 researcher agents (strong model), each with a different **lens** and the same spec
   `data/curation/RESEARCHER_SPEC.md` (ships with the skill as `references/RESEARCHER_SPEC.md`).
   Suggested lenses: *creative fusion* (art × code × music × 3D), *agentic leverage* (agents ×
   harnesses × local models), *capital & markets* (finance × AI × data), *physical world*
   (hardware × robotics × fabrication × AI), *knowledge systems* (second brain × skills × memory).
   Each returns `data/curation/proposals_<lens>.json` with 4–7 proposals in the manual_dives schema
   plus a `novelty` field and a falsifier in the action sketch.
3. **Review as the lead** (adversarial): drop proposals that are categories in disguise, merge
   overlaps, verify every entry_id exists, demand cross-collection reach, cap at ~8 new dives per
   pass. Append survivors to `data/manual_dives.json` (`pinned: true`, `suggested_by: "curated"`).
4. Regenerate everything that renders dives: `deep_dives.py` → `deeper_dives.py --all-curated` →
   `build_guides.py` → `cms.py rebuild` → `build_api.py` (sitemap) → `build_context.py`. Confirm the
   new dives appear on index.html cards, guides/index.html, site/deeper/, api/deep_dives.json and
   sitemap.xml before pushing.

Why: a Jul-2026 review found the auto dives were tag buckets ("art", "agents") while the real value in
the saves was in intersections nobody had written down. Victor: "pretend you're an advanced researcher
looking across the spectrum… for novel ideas that exist between the technologies."

### Phase 5d: Prompt Systems (REQUIRED for every dive and guide before publish)

A dive that tells you *what* exists is not finished until it also hands you the prompts that *build*
it. Every curated dive and every hand-written guide carries a **prompt system**: a deeper-not-bigger
rewrite of the ask, a verbose one-shot prompt, 5–9 step prompts that each carry their own audit, a
post-build gap-analysis prompt, the questions the agent must ask itself, the external oracles that
prove the result right, failure modes, and direction for an unattended agent harness.

1. Export targets (curated dives from `deep_dives.json` + standalone pages in `site/guides/`):
   ```bash
   python3 scripts/prompt_systems.py export --size 8     # -> data/prompt_systems/batch_NN.json
   ```
2. One strong-model agent per batch writes `data/prompt_systems/out_NN.json` to the schema and laws in
   `data/prompt_systems/SPEC.md` (ships with the skill as `references/PROMPT_SYSTEM_SPEC.md`). Each pack
   must be specific to its dive (names the tools/repos/creators' claims from the transcripts), include
   a paper/backtest arm with caps for anything money-adjacent, and defensive framing only for anything
   security-adjacent. The agent runs `prompt_systems.validate` on its own output before returning.
3. Merge (validator rejects thin packs) and render:
   ```bash
   python3 scripts/prompt_systems.py merge 'data/prompt_systems/out_*.json'   # -> data/prompt_systems.json
   python3 scripts/prompt_systems.py render   # injects hand-written guides, writes api/prompts.json + prompts.html
   python3 scripts/build_guides.py --force && python3 scripts/deeper_dives.py --all-curated
   python3 scripts/build_landing_meta.py      # promptCount for the showcase tile
   ```
   `rebuild.sh` stops at the `prompts` phase whenever a target has no pack.
4. Review as the lead: open three packs at random; a prompt that could be pasted under a different dive
   unchanged fails. Confirm `prompts.html`, `api/prompts.json`, the `Prompts` nav item, and the
   "Prompt system" section at the bottom of a guide page and a deeper page all render.

The deeper-not-bigger block is the fixed core of every pack (Victor, 2026-10-22): *what would a top
professional do here that I'm not asking for; what is the rawest material; which methods and tools;
what, other than you or me, proves it right; now rewrite the prompt to ask for exactly that.*

### 6 Insight Classes

| Class | Description |
|-------|-------------|
| emergent_capability | Something that became possible only recently |
| workflow_multiplier | One person doing the work of a team |
| arbitrage_opportunity | Information/skill asymmetry creating value |
| creative_fusion | Cross-domain combination producing new medium |
| expression_amplifier | Tools that amplify creative output |
| life_leverage | Systems that compound over time |

---

## Phase 6: Download Thumbnails (scripts/ab_download_thumbs.py)

```bash
python3 scripts/ab_download_thumbs.py    # PRIMARY: agent-browser og:image extraction
python scripts/download_thumbs.py        # legacy: direct download from stored media_url
```

`ab_download_thumbs.py` navigates each post via agent-browser, extracts the `og:image` meta tag, downloads JPEG to `site/thumb/<post_id>.jpg`. Resume-safe (skips existing). Requires Chrome closed + agent-browser session.

The legacy `download_thumbs.py` (requests-based) only works for entries with a fresh `media_url` — IG CDN URLs are signed and expire within hours, so it fails on anything older than the current session.

**WHY LOCAL:** IG CDN URLs are signed + expire + referer-blocked. Hotlinking will 403 within hours. Always download.

---

## Phase 7: Digest Pass (scripts/digest.py)

Turns the flat catalog into clustered summaries and ranked recommendations.

```bash
python scripts/digest.py   # cached — re-runs are cheap
```

**Produces:**
- `site/summaries.json` — per-category summary cards (cluster title + why_it_matters + key_takeaways + actionable links + dominant creators/tools + entry IDs)
- `site/recommendations.json` — `latest_batch.top_recs[]`, `archive[]`, `evergreen[]`

**Algorithm (per category):**
1. Embed every entry's `title + summary + top-tags`. Cache by content hash.
2. Agglomerative-cluster by cosine distance. K is not fixed.
3. Per cluster: rank by `tier * recency * creator_authority`, take top 3, generate title + takeaways. Cache per cluster hash.
4. Master recs: rank batch by `tier * novelty * clustering-convergence` to top 10.
5. Archive: prior batches preserved verbatim.

**Cost:** <$1 full rebuild, <$0.10 incremental.

**Fallbacks** (site must still render):
- Rate-limited: skeleton card (top-3 entries, no LLM text)
- Embedding service down: reuse prior clustering
- Empty category: skip

---

## Phase 8: CMS Rebuild (scripts/cms.py rebuild)

Recomputes crosslinks and refreshes all exports.

```bash
python scripts/cms.py rebuild
```

1. Loads all entries from `data/entries.parquet`
2. Recomputes crosslinks across 9 dimensions
3. Writes `data/crosslinks.parquet`
4. Regenerates `site/catalog.json` and `site/catalog.js`
5. Applies any pending patches from `data/patches.json`

---

## Phase 9: Agent Context Layer (build_context.py)

```bash
python build_context.py
```

**KNOWN ISSUE:** `build_context.py` still reads legacy `data/catalog.jsonl` — it predates the parquet CMS. If it fails with `FileNotFoundError: catalog.jsonl`, either regenerate the jsonl from parquet first, or update the script to read `site/catalog.json`. Until fixed, `site/context.md` goes stale after pipeline runs — check its generated date before trusting it.

Transforms the catalog into a structured knowledge base for AI agents.

### site/catalog.json — Queryable Structured Index

Complete JSON with pre-built indices:

```json
{
  "version": "1.0",
  "stats": { "total_entries": N, "tiers": {"S": n, "A": n} },
  "indices": {
    "by_domain": { "domain1": ["id1", "id2"] },
    "by_tool": { "tool1": ["id1"] },
    "by_technique": {},
    "by_tier": { "S": [], "A": [] },
    "by_collection": { "collection1": [], "collection2": [] }
  },
  "entries": [{ "id": "...", "url": "...", "title": "..." }]
}
```

### site/context.md — Agent-Readable Knowledge Map

Structured markdown for agent session start: domain map, S/A-tier listings, tool directory, technique directory, usage patterns.

### site/llms.txt + llms-full.txt — LLM Discovery

Lightweight discovery files pointing LLMs to the structured data.

### site/.well-known/ai-plugin.json — Plugin Manifest

Standard AI plugin manifest for tool/agent discovery.

**The value:** Your saves become working memory for your AI tools. When building something, your agent already knows every tool, technique, and repo you've collected.

---

## Phase 10: API + Per-Entry Pages (scripts/build_api.py)

```bash
python scripts/build_api.py
```

**Generates:**
- `site/api/catalog.json` — full catalog with all fields
- `site/api/creators.json` — creator index with post counts
- `site/api/tools.json` — tool directory
- `site/api/collections.json` — collection metadata
- `site/api/deep_dives.json` — deep dive index
- `site/sitemap.xml` — all URLs for crawlers

---

## Phase 11: Render Static Site

### Collection Pages (scripts/render_template.py)

```bash
python scripts/render_template.py
```

Re-renders per-collection static pages. Each page has a `<script>const POSTS=[...];</script>` block refreshed from parquet.

#### Adding a new collection

Update 4 locations in render_template.py:
1. `NAV_SOURCES` list
2. `COLL_META` dict (display name, description, icon)
3. Render loop
4. Sidebar pills

### JS Wrappers (scripts/catalog_js.py)

```bash
python scripts/catalog_js.py
```

Wraps JSON blobs in `window.__CATALOG` / `window.__SUMMARIES` / `window.__RECOMMENDATIONS` for file:// previews.

### Per-Entry Pages (scripts/render_entries.py)

```bash
python scripts/render_entries.py
```

One `site/e/<id>.html` per entry. Currently archived in `site/legacy/e/` pending redesign.

### Transcription (scripts/transcribe.py)

```bash
python3 scripts/transcribe.py --all                    # all video entries without transcripts
python3 scripts/transcribe.py --all --model small      # specify whisper model (tiny/base/small/medium/large)
python3 scripts/transcribe.py --id <entry_id>          # single entry
python3 scripts/transcribe.py --all --limit 10         # cap at 10 entries
python3 scripts/transcribe.py --all --force            # overwrite existing transcripts
```

Downloads media via yt-dlp + transcribes via faster-whisper (CPU, int8). Chrome MUST be closed — yt-dlp uses `cookiesfrombrowser: ("chrome",)` for authenticated IG content.

**What it targets:** Entries where `media_type` ∈ {video, reel, mp4} and `transcript` is empty. Caption scraping (`ab_scrape_posts.py`) updates `media_type` from the DOM, so run captions BEFORE transcription — otherwise many videos appear as "image" and get skipped.

**Pipeline:** download audio (yt-dlp) → convert to wav (ffmpeg) → transcribe (faster-whisper) → persist to parquet. Saves incrementally after each successful transcription.

**Failure modes:** "No video formats found" = post is actually an image/carousel despite media_type. "Login required" = IG auth cookies expired or Chrome was open. ~8-10% failure rate is normal.

**Typical results:** ~90% of video entries transcribe successfully. Common failures: images mis-tagged as video (yt-dlp returns "No video formats found"), private/login-walled posts, expired cookies. Image entries have no audio to transcribe — this is expected, not a failure.

---

## Phase 12: Graph Visualizations

Two standalone repos provide the visualization engines. DejaViewed maps its data into their generic contract.

### Data Contract (shared by both)

```json
{
  "nodes": [
    {
      "id": "unique-id",
      "label": "Display Name",
      "group": "category-for-coloring",
      "weight": 10,
      "tags": ["tag1", "tag2"],
      "metadata": {
        "description": "Tooltip text",
        "url": "https://...",
        "creator": "@handle",
        "tier": "S"
      }
    }
  ],
  "edges": [
    { "source": "node-a", "target": "node-b", "weight": 2, "type": "related" }
  ],
  "config": {
    "title": "DejaViewed Knowledge Graph",
    "groupColors": {
      "collection1": "#a78bfa", "collection2": "#f0a050", "collection3": "#4cda8c",
      "collection4": "#f472b6", "collection5": "#60a5fa"
    }
  }
}
```

### DejaViewed to Generic Mapping

The graph pages read `site/catalog.json` and transform client-side:

```javascript
// Entry to Node
const node = {
  id: entry.id,
  label: entry.title,
  group: entry.source_collection,
  weight: { S: 10, A: 7, B: 4, C: 2 }[entry.tier] || 1,
  tags: [...(entry.tools||[]), ...(entry.techniques||[]), ...(entry.domains||[])],
  metadata: {
    description: entry.summary,
    url: entry.url,
    creator: entry.creator,
    tier: entry.tier,
    thumb: 'thumb/' + entry.post_id + '.jpg'
  }
};

// Crosslink to Edge
const edge = {
  source: crosslink.a_id,
  target: crosslink.b_id,
  weight: crosslink.weight,
  type: crosslink.dim
};
```

### graph.html — Force-Directed (graph-node)

D3 force-directed SVG graph:
- Sidebar filters by collection/group
- Search with highlight
- Node detail panel on click
- Zoom/pan, responsive layout

### graph-cosmos.html — Orbital Physics (graph-cosmos)

Canvas-based Cosmos visualization:
- Hierarchical orbital layouts
- Preset view modes, tooltip overlays
- Responsive breakpoints
- WebGL-accelerated for large datasets

---

## Phase 14d: SEO review loop (audit → fix → content)

- Guides are server-rendered (markdown-it) from `<script id="md">`; after any markdown edit run `build_guides.py --rerender-only`; after `--force` run `search_prep.py`. Never reintroduce client-side markdown or hidden prerenders.
- Programmatic pages (tools hubs, comparisons, best-of) need substance: ≥5 entries, ≥2 S/A, ≥1 curated guide, 150+ original words, every paragraph citing /e/<id>; below that → `noindex,follow` and out of the sitemap (build_api skips robots-noindex pages). External facts carry a source URL + date on the page.
- Generators own `<meta name="description">`; build_seo reuses it for tools/compare/best. `normalize_links.py` runs last. `build_api.py` strips entry blocks → always followed by seo, monetize, links.
- Quality gate lints agent-note leaks ("sandbox blocked", "Repo path:", TODO…) and private machine paths.
- Re-audit cadence: re-run the technical audit + content gaps analysis quarterly or when Search Console deltas stall; audits live in `data/seo/audit_<date>.json`, `content_gaps_<date>.json`.

## Phase 14c: Indexing hubs + monetize layer

- Entry pages must be hubs, never orphans: `render_entries.py` adds breadcrumb, Related (crosslink-weighted), Appears-in (guides/deeper), same-creator, prev/next. Guides/deeper link `../e/<id>.html` with a static (non-JS) entry list so crawlers see it. `build_guides.py --force` wipes guide search text → run `search_prep.py` after.
- Private pages (admin, rate, legacy) get `noindex,follow` via `build_seo.py` and must stay CRAWLABLE (no robots Disallow) or the tag is never seen.
- Monetize: `scripts/build_monetize.py` runs after `seo`. All tool links route through `/go/<slug>` (`site/_redirects`, 302) so clicks are measurable before any affiliate is active. `data/monetize/affiliates.json` `status: pending|active|skip`; `config.json` tip-jar/sponsors/pack URLs. Nothing with an empty URL renders; FTC disclosure appears only once an affiliate is active. No ads (owner decision). Pay-to-crawl stays parked until llms-full.txt / api demand shows in analytics.

## Phase 14b: Discoverability — SEO, feeds, analytics (REQUIRED before publish)

Being indexed and cited is part of "done". After every build:

1. `scripts/build_start_here.py` → `site/start-here.html`: one factual positioning sentence with live
   counts, who it's for, how humans and agents use it, how to cite. No superlatives — numbers get
   quoted, adjectives don't.
2. `scripts/build_feed.py` → `feed.xml`; `scripts/build_og.py` → `site/og/*.jpg`;
   `scripts/build_seo.py` (LAST, after search) → canonical + description + OG + JSON-LD block between
   `<!-- seo:start|end -->` in every public page; FAQPage per guide from the prompt system's
   self-questions; titles for the 25 target queries in `data/seo/queries.json`.
3. `scripts/build_api.py` sitemap carries `lastmod`/`changefreq` and clean URLs; `robots.txt` allows
   GPTBot, ClaudeBot, PerplexityBot, Google-Extended, Bingbot, CCBot and blocks admin/rate.
4. After deploy: `python3 scripts/indexnow.py` (key file served from site root). Google has no ping
   API any more — Search Console reads the sitemap.
5. Measurement: `scripts/analytics_report.py` reads Cloudflare (`~/.config/cloudflare/dejaviewed.env`,
   mode 600) and Search Console (`~/.config/google/dejaviewed-gsc.json`) and writes a dated report with
   deltas. Setup click-paths: `data/analytics/SETUP.md`. Never print a token; existence checks only.
   Every SEO change is judged against the previous report, not by feel.

Why: as of 2026-10-22 the site had no analytics beacon, no Search Console, no meta descriptions on
guides/entries. You cannot improve what you cannot see.

---

## Phase 13: Board + Admin Pages

### Board (site/board.html — 773 lines)

Drag-to-connect thought board for exploring entry relationships.

**Layout:** Two-panel grid (320px sidebar + canvas)
- Left: entry list with search + filters
- Right: freeform canvas — drag cards, position them, draw connections
- Connections persist in localStorage

Uses shared.css + shared.js. Dark theme. Responsive.

### Admin (site/admin.html — 316 lines)

Entry editor for manual curation.

**Layout:** Two-panel grid (360px entry list + editor form)
- Left: searchable entry list with tier badges
- Right: edit form — title, summary, tier, type, tags, domains, tools, techniques, user_notes, favorited
- Edits write to `data/patches.json` (NOT parquet directly)
- Patches applied on next `cms.py apply-patch` or `cms.py rebuild`

---

## Phase 14: Browser Bookmarks + Social Platforms

**Browser bookmarks (no auth needed):**
```bash
python adapters/chrome_bookmarks.py --out data/chrome_bookmarks.jsonl
python adapters/firefox_bookmarks.py --out data/firefox_bookmarks.jsonl
python adapters/edge_bookmarks.py --out data/edge_bookmarks.jsonl
```

**Social platform saves (auth via Chrome profile copy):**
```bash
python adapters/reddit_saved.py --out data/reddit_saved.jsonl
python adapters/twitter_bookmarks.py --out data/twitter_bookmarks.jsonl
python adapters/tiktok_saved.py --out data/tiktok_saved.jsonl
python adapters/youtube_saved.py --playlists WL,LL --out data/youtube_saved.jsonl
python adapters/pinterest_boards.py --all-boards --out data/pinterest_saved.jsonl
```

**Merge all sources:**
```bash
python adapters/merge_sources.py \
  --sources data/catalog.jsonl data/chrome_bookmarks.jsonl data/firefox_bookmarks.jsonl \
    data/reddit_saved.jsonl data/twitter_bookmarks.jsonl data/tiktok_saved.jsonl \
    data/youtube_saved.jsonl data/pinterest_saved.jsonl \
  --out data/catalog_merged.jsonl --dedup-by url
```

All adapters share: `--profile` for custom Chrome profile path, `--limit` to cap items, `--pause` for rate limiting. All resume-safe. All output same JSONL schema.

Cross-source dedup: same URL from Chrome AND Instagram — merger keeps the richer record, adds `sources: ["instagram", "chrome"]`.

---

## Phase 15: Deploy

**Local preview:**
```bash
cd site && python3 -m http.server 8765
```

**Static hosting (any provider):**
The `site/` directory is fully self-contained static HTML/CSS/JS. Deploy to any static host:
- **Cloudflare Pages:** Connect repo, set output dir to `site/`, auto-deploys on push
- **GitHub Pages:** Push `site/` to gh-pages branch or use deploy script
- **Netlify/Vercel:** Point build output to `site/`
- **Manual:** Upload `site/` contents to any web server

No build step required — everything is pre-rendered static files.

---

## Design Authority

**All visual/layout decisions defer to `DESIGN.md` in the project root.**

- **Theme:** Dark `#0a0a0f` with violet+pink radial gradients. Glassmorphism surfaces.
- **Typography:** Monospace (`SF Mono`, `Fira Code`, `JetBrains Mono`, Menlo). Weight over size.
- **Layout:** Two-panel (sticky sidebar 280px + main). CSS masonry 3-col, 2 at 1200px, 1 at 900px.
- **Tier colors:** S=gold `#fbbf24`, A=violet `#a78bfa`, B=blue `#60a5fa`, C=gray `#6a6a80`
- **Category colors:** repo=`#4cda8c`, tool=`#f0a050`, skill=`#e060a0`, guide=`#a78bfa`, platform=`#e0d040`, resource=`#40d0e0`, art=`#f05060`, design=`#fb7185`, uiux=`#60a5fa`
- **Brand gradient:** `linear-gradient(135deg, #fff 0%, #a78bfa 50%, #f472b6 100%)`
- **Breakpoints:** 900px, 640px, 400px. `overflow-x:hidden` on html/body.
- **Voice:** Second-person, mildly conspiratorial. Em-dash with spaces.
- **Anti-patterns:** Not neon-cyberpunk. Not minimalist-startup-white. Not rounded-bouncy-friendly.

**Navigation (shared.js):**
- Header h1 links to index.html ("DejaViewed")
- Nav: Catalog | Guides | Graph · Force | Graph · Cosmos | Board | About (Admin reachable at admin.html, not in nav)
- Active tab gets gradient highlight
- `DV.nav(activeId)` / `DV.mountHeader(root, activeId)`

**Shared infrastructure:**
- `site/shared.css` — design tokens, component library
- `site/shared.js` — `DV` namespace: `loadCatalog`, `el()`, `nav()`, `mountHeader()`, `tierPill()`, `entryUrl()`
- **No innerHTML for user content** — always `DV.el()` or `createElement`. DOMPurify+marked for guide markdown only.

---

## Mistakes to Avoid (Learned the Hard Way)

1. **NEVER ask the user to manually extract URLs.** Use Playwright MCP. Corrected MULTIPLE times.
2. **Generic titles will get you yelled at.** ALWAYS "Subject — why it matters". Every card.
3. **Don't render category chips on cards.** Colored left border + section grouping is enough.
4. **Don't over-drop.** 10-20% drop rate. First pass dropped 43% — user wanted them back.
5. **Don't put the catalog owner in the creator graph.** Curator, not creator.
6. **Don't use flex-fill bars.** Proportional width, max-count = 100%.
7. **IG CDN URLs expire.** Download thumbnails locally. Always.
8. **og:description is truncated.** Extract from `<script type="application/json">` blocks.
9. **innerHTML gets blocked by security hooks.** DOM createElement for everything.
10. **Don't forget links.** Every card needs clickable links to repos, tools, websites.
11. **Backup before enrichment passes.** `cp catalog.jsonl catalog.jsonl.bakN` first.
12. **Thumbnail below title/summary.** Title is the hook, thumbnail is supporting.
13. **Monospace body font reads better** for technical catalogs.
14. **DejaViewed summary page must match catalog layout.** Same hero-grid with left/right columns.
15. **Long code commands overlap in narrow columns.** `white-space:nowrap;overflow-x:auto`.
16. **NEVER unconditionally overwrite card_title.** Enriched title IS the title. Only set as fallback when empty. Most repeated bug — caught THREE times.
17. **Keep parquet and exports in sync.** Always run `cms.py rebuild` after enrichment.
18. **Adding a collection: update ALL 4 locations in render_template.py.** Nav, COLL_META, render loop, sidebar pills.
19. **Playwright `require()` is blocked.** Write scripts to `.playwright-mcp/` files.
20. **Playwright paths must be in allowed roots.** `.playwright-mcp/` or project dir only.
21. **Use `domcontentloaded`, never `networkidle` for IG.** Analytics stream forever.
22. **Cookies must use `context.addCookies()`.** `document.cookie` can't set HttpOnly.
23. **deep_dives.js needs `type` field from parquet.** cms.py handles this.
24. **Legacy pages live in `site/legacy/`.** Don't link from active nav.
25. **ALWAYS push before destructive operations.** Deploy scripts, branch switches, bulk file moves — push first, delete later. No exceptions.
26. **agent-browser daemon persists.** `npx agent-browser close` between profile/session changes.
27. **agent-browser eval is double-encoded.** `json.loads(json.loads(raw))` to unwrap.
28. **JS eval fails on IG DOM.** Use `get text "main"` + Python text parsing for captions.
29. **ingest.py blocks on interactive prompt.** Use `--non-interactive` for batch runs.
30. **URL files from agent-browser have stray quotes/brackets.** Strip with `.strip().strip('"').strip(',').strip('"')`.
31. **Collection pills must be dynamic.** Never hardcode HTML — `buildCollPills()` generates from data.
32. **Stats tagline must be dynamic.** Entry count, collection count, creator count from POSTS array.
33. **"tutorial" type merged into "skill".** enrich_entries.py returns "skill", not "tutorial".
34. **Graph pages are standalone.** site/graph.html and site/graph-cosmos.html are self-contained. They don't import from graph-node/graph-cosmos repos at runtime.
35. **Guide pages need marked.js + DOMPurify.** Markdown-in-script-tag pattern, rendered client-side.
36. **Verify entry IDs before writing manual_dives.json.** Bad IDs cause silent broken links.
37. **enrich_sweep didn't generate titles.** Had to add build_title() and wire into both enrich_entry() and enrich_sweep().
38. **Caption scrape default filter misses enriched entries.** After enrichment gives titles, `[NEEDS ENRICHMENT]` filter finds 0. Use `--missing-captions` for second-pass.
39. **Run captions BEFORE Whisper.** Caption scrape corrects `media_type` field. Without it, Whisper skips videos tagged as "image".
40. **Non-IG entries won't have captions.** ~30 GitHub/archive.org URLs are expected gaps, not bugs.
41. **Re-enrich after bulk transcription.** New text data changes tier/type classification and grows crosslinks significantly.
42. **site/ is fully static.** Deploy to any static host (Cloudflare Pages, GitHub Pages, Netlify, Vercel). No build step.
43. **Engagement-bait captions poison title generation.** "Comment X for the guide" captions produce bare-name titles ("Claude") and inflated tiers. When a caption is bait, generate the title from the TRANSCRIPT — that's where the real content is. After any bulk re-enrichment, audit: `df[df['title'].str.len()<14]` should be empty, and S-tier should stay under ~15% per collection.
44. **Keep instance facts out of SKILL.md.** Entry counts, coverage stats, domains belong in `references/site-deployment.md` (Operator Mode overlay) — SKILL.md text goes stale and confuses public users.

---

45. **Scroll-scraping saved collections is lossy.** Stalls at 12 on small collections, drops posts on big ones. Use the collection-feed API (Phase 0 v3). Reconcile: API count vs parquet count per collection.
46. **agent-browser's bundled Chromium can't decrypt real Chrome cookies** (`--password-store=basic`). Attach to real Chrome via CDP on a scratch user-data-dir copy instead.
47. **`pkill -f` / `pgrep -f` in a tool shell kills the tool shell** when the pattern appears anywhere in the same command. Put restart/status logic in helper scripts and invoke them by path.
48. **Don't write parquet while transcribe.py runs.** It rewrites the whole row set after each file and clobbers concurrent edits.
49. **"video" in media_type can be a carousel.** Media-info API `media_type: 8` = carousel → OCR slides, not Whisper. Four such entries sat as "video download failures" for months.

50. **`enrich_entries.py` reads `site/catalog.json`, not parquet.** Any parquet-only edit (media_type fix, user_notes, recovered transcripts) made since the last export gets overwritten by the next sweep. ALWAYS `python3 scripts/cms.py rebuild` right before `enrich_entries.py --sweep`, and re-run the quality gate after.

51. **Page-text caption scrapes can read the PREVIOUS post.** The July-2026 `ab_scrape_posts.py` run attached the prior page's caption/creator to some entries ("Edited" as creator, caption contradicting the transcript). Transcripts from yt-dlp-by-URL were right. Any scrape that navigates then reads must verify the page's `instagram://media?id=` equals the shortcode-decoded pk first — `scripts/ig_refresh_captions.py` does this and prefers the media-info API; run it (`--apply`) on any collection scraped before Oct 2026 and re-enrich the entries it changes.

52. **Hand-written guide pages are patched in place, generated ones are regenerated.** `prompt_systems.py render` injects its block between `<!-- prompt-system:start|end -->` markers inside the page's `<script id="md">` markdown (idempotent; HTML comments, stripped by DOMPurify and search_prep), while curated-dive guides get the block from `build_guides.py --force`. Never hand-edit the injected block — edit `data/prompt_systems.json` and re-render.

## Output Checklist

Before declaring done, verify:

**Content quality:**
- [ ] Every card has "Subject — angle" title (no bare names, no `@creator:` prefixes)
- [ ] Every card has 1-3 sentence summary naming concrete things
- [ ] Links extracted and displayed for every card with linkable content
- [ ] Thumbnails downloaded locally (not hotlinked)
- [ ] Drop rate is 10-20%, not 40%+

**CMS integrity:**
- [ ] `data/entries.parquet` exists and `cms.py check` passes
- [ ] `data/crosslinks.parquet` has entries across all 9 dimensions
- [ ] `data/deep_dives.parquet` has auto-detected + curated dives
- [ ] `site/catalog.json` in sync with parquet (`cms.py rebuild` run)

**Site rendering:**
- [ ] All pages load clean (no console errors)
- [ ] Creator graph excludes catalog owner, bars scale proportionally
- [ ] Category filters work (multi-select OR logic)
- [ ] Tier pills filter correctly
- [ ] Search filters across title, summary, tools, repos, creator
- [ ] Section grouping appears when "All" selected
- [ ] Masonry 3 columns, responsive at 900/640/400px
- [ ] No horizontal overflow down to 320px
- [ ] No innerHTML except DOMPurify-sanitized markdown

**Graph pages:**
- [ ] graph.html loads catalog.json and renders force-directed graph
- [ ] graph-cosmos.html loads and renders orbital graph
- [ ] Both use generic data contract (group/weight/tags/metadata)
- [ ] Node click shows detail panel

**Deep dives:**
- [ ] Deep dive cards on index page
- [ ] Click opens inline detail panel (thesis, connections, action sketch)
- [ ] Deeper dive pages in site/deeper/ for all curated dives
- [ ] Full guide pages in site/guides/ for all curated dives
- [ ] Guide index page at site/guides/index.html with filters
- [ ] Curated dives survive regeneration (manual_dives.json)
- [ ] "Deeper Dive →" and "Full Guide →" links in detail panel

**Board + Admin:**
- [ ] Board loads entries, drag-to-connect works
- [ ] Admin loads entries, edits write to data/patches.json
- [ ] Patches applied on next cms.py rebuild

**Agent context:**
- [ ] site/context.md with domain map + tier listings
- [ ] site/llms.txt and llms-full.txt exist
- [ ] API files in site/api/ (catalog, creators, tools, collections, deep_dives)
- [ ] site/sitemap.xml covers all URLs

**Navigation:**
- [ ] Header: DejaViewed links to index.html
- [ ] Nav: Guides | Graph · Force | Graph · Cosmos | Board | Admin
- [ ] Active page gets gradient highlight
- [ ] Tested at desktop (1440px), tablet (768px), mobile (375px)

**Dynamic elements (must NOT be hardcoded):**
- [ ] Collection pills generated from POSTS data via buildCollPills()
- [ ] Stats tagline computed at runtime (entry count, collection count, creator count)
- [ ] Category sidebar counts computed from POSTS array
- [ ] No "tutorial" type in sidebar — merged into "skill"

---

## Known Errors & Pitfalls (MUST AVOID)

### CRITICAL: Parquet ↔ catalog.json Title Sync Loop

The CMS has a circular data flow that can trap stale titles:

1. `enrich_entries.py` writes catalog.json with heuristic titles (some `[NEEDS ENRICHMENT]`)
2. Enrichment's internal `cms.py migrate` creates parquet WITH `last_edited_at` set
3. `upsert()` merge guard (cms.py line 396-401) preserves existing title if `last_edited_at` is set
4. `cms.py rebuild` reads parquet → overwrites catalog.json → stale titles propagate back

**Fix applied:** cms.py `upsert()` now has an exception: titles containing `[NEEDS ENRICHMENT]` are ALWAYS overwritable regardless of `last_edited_at`.

**Prevention:** When fixing titles externally (not through enrichment), ALWAYS:
1. Fix titles in catalog.json
2. DELETE `data/entries.parquet` and `data/crosslinks.parquet`
3. Run `cms.py migrate` (creates fresh parquet from clean catalog.json)
4. NEVER run `cms.py rebuild` between steps 1-3 (it reads parquet → overwrites catalog.json)

### IG DOM Unloading During Scroll

Instagram removes DOM elements for posts scrolled past. Naive extraction captures only visible posts (~30).

**Fix:** Use `scripts/ab_extract_cumulative.py` — scrolls incrementally, extracts URLs at each position, merges into cumulative set. Stops after 4 stable rounds.

### ingest.py JSON vs TXT Format Mismatch

`ingest.py` reads one-URL-per-line TXT files. JSON arrays with brackets/quotes create garbage entries (`[`, `"url",` as URL values).

**Fix:** Always convert JSON URL arrays to plain .txt (one URL per line) before ingesting. Or use `--urls-file` with proper JSON handling.

### yt-dlp Authentication for Instagram

yt-dlp needs Chrome cookies for authenticated IG content. Without them, all downloads fail.

**Fix:** Add `"cookiesfrombrowser": ("chrome",)` to yt-dlp opts. Chrome MUST be closed (profile lock).

### Parquet Corruption via PyArrow

`pa.Table.from_pandas()` can produce invalid parquet files (thrift deserialization error). 

**Fix:** Use `pa.Table.from_pylist()` with explicit schema instead. If parquet corrupts, delete and rebuild from catalog.json via `cms.py migrate`.

### Enrichment Title Quality

`build_title()` heuristic fails on ~25% of entries (thin captions, hashtag-only, comment bait). Returns empty string → title stays as `[NEEDS ENRICHMENT] <post_id>`.

**Fix:** After enrichment sweep, run a second pass with more aggressive caption parsing: first meaningful sentence as subject, second as angle. Format: "Subject — angle" (em-dash).

### Thumbnail Download Requires agent-browser

`download_thumbs.py` (requests-based) fails on IG CDN signed URLs. `ab_download_thumbs.py` (agent-browser) navigates to each post page, extracts `og:image` meta tag, downloads JPEG.

**Fix:** Always use `scripts/ab_download_thumbs.py` for IG thumbnails. Requires agent-browser with Chrome profile.

### Caption Scraping: JS eval vs get text

IG DOM is heavily obfuscated. `document.querySelector` selectors break regularly.

**Fix:** Use `npx agent-browser get text "main"` + Python text parsing (find time markers, extract creator + caption). Never rely on CSS selectors for IG content.

### Caption Scrape: Two-Pass Workflow

First ingest creates entries with `[NEEDS ENRICHMENT]` titles. First enrichment gives them real titles but may NOT fill captions (enrichment generates titles from whatever text exists). After enrichment, `ab_scrape_posts.py` default filter (`[NEEDS ENRICHMENT]` title check) finds 0 entries — but captions are still empty.

**Fix:** Use `--missing-captions` flag for second-pass caption scraping. This targets all entries with empty captions regardless of title state. Added `--collection` flag to scope runs.

### Transcription Ordering: Captions Before Whisper

`ab_scrape_posts.py` updates `media_type` field from the DOM (detecting video vs image). `transcribe.py` filters by `media_type ∈ {video, reel, mp4}`. If you run Whisper BEFORE captions, many videos still show `media_type: "image"` and get skipped.

**Fix:** Always run caption scraping before transcription. Caption scrape → media_type gets corrected → Whisper sees all actual videos.

### Non-IG Entries Have No Captions

~30 entries are GitHub repos, archive.org pages, or other non-IG URLs. These will never have Instagram-style captions. Don't report them as gaps — they're expected. The 5 remaining IG failures are posts that return no text from `get text "main"` (private, deleted, or login-walled).

### Enrichment After Transcription

New captions + transcripts dramatically improve tier/type/domain classification. After bulk caption scraping or Whisper transcription, ALWAYS re-run `enrich_entries.py --sweep`. Crosslinks increase significantly with richer text data (typically 10-15% growth).

### Thumbnail og:image Failures

~4 posts return no `og:image` meta tag via agent-browser. These are typically carousels or posts with non-standard IG rendering. Not fixable via the current `ab_download_thumbs.py` approach. Acceptable loss.
