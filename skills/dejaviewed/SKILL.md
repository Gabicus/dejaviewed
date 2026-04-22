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
      repo: github.com/Gabicus/graph-node
      purpose: D3 force-directed graph visualization
      data_contract: generic (nodes/edges with group/weight/tags/metadata)
    - name: graph-cosmos
      repo: github.com/Gabicus/graph-cosmos
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
scripts/rebuild.sh \
  --collections ai1=<url> ai2=<url> ai3=<url> ai4=<url> ai5=<url> \
                quant=<url> art-inspiration=<url> art-i-like=<url>
```

Skip phases with `--skip <phase>[,<phase>...]`. Phases (in order):

| Phase | Script | What it does |
|-------|--------|--------------|
| `scrape` | Playwright MCP | Extract URLs from saved collection pages |
| `process` | `scripts/process_raw.py` | Convert raw scraped JSON into catalog entries |
| `migrate` | `scripts/cms.py migrate` | Seed/update parquet from catalog.json |
| `enrich` | `scripts/enrich_entries.py --sweep` | Classify, tier, extract metadata |
| `dives` | `scripts/deep_dives.py` | Auto-detect deep dive clusters |
| `deeper` | `scripts/deeper_dives.py` | Generate narrative deeper dive pages |
| `thumbs` | `scripts/download_thumbs.py` | Download thumbnails locally |
| `digest` | `scripts/digest.py` | Cluster + rank into summaries + recommendations |
| `rebuild` | `scripts/cms.py rebuild` | Recompute crosslinks + refresh exports |
| `context` | `build_context.py` | Agent context layer (context.md, llms.txt) |
| `api` | `scripts/build_api.py` | API JSON files + per-entry pages + sitemap |
| `render` | `scripts/render_template.py` | Refresh collection page HTML |
| `js` | `scripts/catalog_js.py` | JS wrappers for file:// previews |

Missing scripts are skipped with a warning — the pipeline degrades gracefully.

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
  index.html           Landing: bar chart + deep dive cards
  ai1.html             Per-collection catalog page
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
  thumb/               Downloaded thumbnails (338+)
  api/                 Machine-readable JSON exports
    catalog.json
    creators.json
    tools.json
    collections.json
    deep_dives.json
  guides/              Deep dive guide pages
  deeper/              Deeper dive narrative pages
  legacy/              Archived pages (ai2-4, catalog, dejaviewed, etc.)
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

**graph-node** (`github.com/Gabicus/graph-node`):
- D3 force-directed SVG graph
- Sidebar filters by group, search, node detail panel
- Data: `{ nodes: [...], edges: [...], config: { title, groupColors } }`

**graph-cosmos** (`github.com/Gabicus/graph-cosmos`):
- Canvas-based orbital physics with hierarchical orbits
- Presets, responsive breakpoints, tooltip overlays
- Same data contract as graph-node

**Relationship:** DejaViewed ships its own graph pages (`site/graph.html`, `site/graph-cosmos.html`) with DejaViewed-specific UX (shared.css theme, nav, tier colors, catalog.json loading). The standalone repos (`graph-node`, `graph-cosmos`) are clean-room implementations of the same visualizations using a generic data contract — usable by anyone with any dataset. They share the same data contract spec but are independent codebases, not runtime imports.

---

## Prerequisites

### What the user provides:
1. **One or more saved collection URLs** — e.g., `https://www.instagram.com/user/saved/quant/12345/`
2. **A copied Chrome/Chromium profile** (one-time setup, already done for returning users)

### What must exist on disk:
1. **Chrome profile copy** at `<project>/.profile-copy/Default/Cookies`
   - User copies their Chrome profile directory while Chrome is CLOSED
   - Linux: `cp -r ~/.config/google-chrome/Default <project>/.profile-copy/Default`
   - macOS: `cp -r ~/Library/Application\ Support/Google/Chrome/Default <project>/.profile-copy/Default`
   - This profile must have an active Instagram session

2. **Python 3.10+** with packages:
   ```bash
   pip install requests browser-cookie3 pyarrow duckdb
   ```

3. **Playwright MCP server** must be available (standard Claude Code plugin)
   - Verify: check if `mcp__plugin_playwright_playwright__browser_navigate` tool exists
   - If not available, fall back to asking user for URLs (last resort only)

### First-time project setup:
```bash
mkdir -p <project>/data <project>/guides <project>/site/thumb <project>/site/guides <project>/site/deeper <project>/site/api <project>/.playwright-mcp
```

---

## Phase 0: URL Extraction via Playwright MCP

**THIS IS THE CRITICAL AUTOMATION STEP. NEVER SKIP IT. NEVER ASK THE USER TO DO THIS MANUALLY.**

The user gives a collection URL. Claude uses Playwright MCP to:
1. Navigate to the saved collection page
2. Scroll to load all posts (infinite scroll)
3. Extract every post URL from the DOM
4. Write URLs to `data/<collection>_urls.json`

### Step 0.1: Extract cookies from Chrome profile

```python
import sqlite3, json
from pathlib import Path

profile = Path("<project>/.profile-copy/Default")
cookies_db = profile / "Cookies"

conn = sqlite3.connect(str(cookies_db))
rows = conn.execute("""
    SELECT name, value, host_key, path, is_secure, is_httponly,
           CASE WHEN expires_utc = 0 THEN -1
                ELSE (expires_utc / 1000000) - 11644473600 END as expires
    FROM cookies
    WHERE host_key LIKE '%instagram.com'
""").fetchall()
conn.close()

cookies = []
for name, value, host, path, secure, httponly, expires in rows:
    cookies.append({
        "name": name, "value": value,
        "domain": host, "path": path,
        "secure": bool(secure), "httpOnly": bool(httponly),
        "expires": expires
    })

(Path("<project>/.playwright-mcp") / "ig_cookies.json").write_text(json.dumps(cookies))
print(f"Extracted {len(cookies)} cookies")

required = {"sessionid", "csrftoken", "ds_user_id"}
found = {c["name"] for c in cookies} & required
print(f"Session cookies present: {found}")
assert found == required, f"Missing: {required - found}"
```

### Step 0.2: Playwright scroll-and-extract

Use Playwright MCP tools:
1. `browser_navigate` to the collection URL (with `waitUntil: 'domcontentloaded'`)
2. Inject cookies via `browser_run_code` using `context.addCookies()`
3. Scroll loop: `browser_run_code` to scroll + extract `a[href*="/p/"]` links
4. Collect all URLs, write to `data/<collection>_urls.json`

### Step 0.3: Handle the result

```python
import json
from pathlib import Path
from scripts.cms import load_entries, has_entry, derive_post_id

urls = json.loads(Path(f"data/{collection}_urls.json").read_text())
existing = load_entries()
new_urls = [u for u in urls if not has_entry(existing, u, derive_post_id(u))]
print(f"Extracted {len(urls)} URLs — {len(new_urls)} new, {len(urls) - len(new_urls)} already scraped")
```

### Playwright Troubleshooting

- **`require()` blocked:** Cannot use `require('fs')` inside `browser_run_code`. Write scripts to `.playwright-mcp/` files and use the `filename` parameter.
- **File path rejected:** Scripts must live in `.playwright-mcp/` or the project directory. `/tmp/` paths are rejected.
- **Use `domcontentloaded`, never `networkidle`:** Instagram streams analytics forever. `networkidle` always times out.
- **Cookies must use `context.addCookies()`:** `document.cookie` cannot set HttpOnly cookies. Session will fail silently.
- **Login wall detection:** Some posts return 200 but contain `"loginRequired"` in the body. Check for it.

### Cookie injection — why

Instagram requires HttpOnly cookies (`sessionid`, `csrftoken`, `ds_user_id`). These cannot be set via JavaScript `document.cookie`. The only way is `context.addCookies()` in Playwright, which requires extracting them from the user's Chrome profile SQLite database.

---

## Phase 1: Ingest (scripts/ingest.py)

The unified ingestion CLI. Reads URLs, dedupes against parquet, scrapes new ones, upserts.

```bash
python scripts/ingest.py --urls-file data/ai5_urls.json --collection ai5
python scripts/ingest.py --url https://instagram.com/p/XXX/ --collection quant
echo "https://instagram.com/p/XXX/" | python scripts/ingest.py --collection ai5
```

**What ingest.py does:**
1. Loads existing entries from `data/entries.parquet` via cms.py
2. Dedupes incoming URLs against existing entries
3. For new URLs: scrapes post metadata (cookies from `.profile-copy/`)
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
python scripts/process_raw.py --raw data/ai5_raw.json --collection ai5
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

---

## Phase 6: Download Thumbnails (scripts/download_thumbs.py)

```bash
python scripts/download_thumbs.py
```

For each entry with a `media_url`: download JPEG to `site/thumb/<post_id>.jpg`.
Resume-safe (skips existing). 1.5s pacing.

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

Transforms the catalog into a structured knowledge base for AI agents.

### site/catalog.json — Queryable Structured Index

Complete JSON with pre-built indices:

```json
{
  "version": "1.0",
  "stats": { "total_entries": 334, "tiers": {"S": 8, "A": 33} },
  "indices": {
    "by_domain": { "quant": ["id1", "id2"] },
    "by_tool": { "python": ["id1"] },
    "by_technique": {},
    "by_tier": { "S": [], "A": [] },
    "by_collection": { "quant": [], "ai1": [] }
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
python scripts/transcribe.py
```

Downloads media + transcribes via local Whisper (faster-whisper + yt-dlp + imageio-ffmpeg). 129/130 videos done. Supports IG CC captions as fast path.

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
      "ai1": "#a78bfa", "ai5": "#f0a050", "quant": "#4cda8c",
      "art-inspiration": "#f472b6", "art-i-like": "#60a5fa"
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

**GitHub Pages (dejaviewed.dev):**
1. Run `scripts/rebuild.sh`
2. Run `scripts/deploy-gh-pages.sh` to push site/ to gh-pages branch
3. GitHub Pages auto-deploys

**Local:**
```bash
cd site && python3 -m http.server 8765
```

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
- Nav: Graph · Force | Graph · Cosmos | Board | Admin
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

---

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
- [ ] Deeper dive pages in site/deeper/
- [ ] Curated dives survive regeneration (manual_dives.json)

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
- [ ] Nav: Graph · Force | Graph · Cosmos | Board | Admin
- [ ] Active page gets gradient highlight
- [ ] Tested at desktop (1440px), tablet (768px), mobile (375px)
