---
name: dejaviewed
description: >
  Turn saved posts and bookmarks from ANY platform into a searchable, curated dark-mode
  catalog site with an auto-generated Action Plan. Supports Instagram, TikTok, Twitter/X,
  Chrome/Edge/Firefox bookmarks, Pinterest, Reddit, YouTube. Full pipeline: ingest from
  any source → classify → tier → extract links → thumbnails → deep-dive guides → Action
  Plan → render static HTML. Triggers: "dejaviewed", "instagram catalog", "saved posts",
  "curate my saves", "bookmark catalog", "action plan from saves".
skill_api_version: 1
user-invocable: true
allowed-tools: Read, Grep, Glob, Bash, Write, Edit, Agent, WebFetch, WebSearch
metadata:
  tier: execution
  dependencies: []
context:
  window: inherit
  intent:
    mode: task
  intel_scope: none
---

# /dejaviewed — Turn Your IG Saves Into a Real Site

> **Tagline:** "You've saved this before."
>
> You scroll, you tap save, you swear you'll come back. You don't. Your Saved tab fills up
> with posts you half-remember. DejaViewed hands the whole pile to Claude: every save gets
> read, classified, tiered, and — for the ones worth the dig — turned into a real deep-dive
> guide with the links the creator wouldn't give you.

**YOU MUST EXECUTE THIS WORKFLOW. Do not just describe it.**

## Quick Start

```bash
/dejaviewed                                    # interactive — prompts for everything
/dejaviewed --urls saved_urls.json             # provide URL list, auto-configure
/dejaviewed --collection mytheme --urls urls.json --title "MyTheme" --handle "@myig"
```

## Prerequisites

The user MUST provide or set up before the skill runs:

1. **A JSON file of Instagram post URLs** — format: `{"collection":"name","count":N,"urls":["https://www.instagram.com/p/XXX/",...]}`
   - User gets these by: going to IG Saved tab, scrolling to load all, extracting URLs from page source or using a browser extension
   - Multiple collections are supported (e.g., `ai1_urls.json`, `ai2_urls.json`)

2. **A copied Chrome/Chromium profile** with an active Instagram session cookie
   - Path: `<project>/.profile-copy/Default/Cookies`
   - User copies their Chrome profile directory (NOT while Chrome is running)
   - Required for authenticated scraping (IG blocks anonymous requests)
   - Needs `browser_cookie3` pip package for cookie decryption

3. **Python 3.10+** with packages: `requests`, `browser_cookie3`

## Architecture Overview

```
<project>/
├── adapters/
│   ├── chrome_bookmarks.py         # Chrome bookmark extractor
│   ├── edge_bookmarks.py           # Edge bookmark extractor
│   ├── firefox_bookmarks.py        # Firefox bookmark extractor (SQLite)
│   └── merge_sources.py            # Cross-source merger + dedup
├── data/
│   ├── <collection>_urls.json      # input: IG URLs per collection
│   ├── <collection>_posts_pathb.jsonl  # raw scrape results (full captions)
│   ├── chrome_bookmarks.jsonl      # extracted Chrome bookmarks
│   ├── firefox_bookmarks.jsonl     # extracted Firefox bookmarks
│   ├── catalog.jsonl               # enriched+classified records (ALL sources merged)
│   ├── curation.json               # tiers, buckets, stacks, themes
│   └── actions.json                # auto-generated action plan data
├── guides/
│   └── <slug>.md                   # deep-dive markdown guides
├── site/
│   ├── index.html                  # main catalog (all sources)
│   ├── dejaviewed.html              # THE DEJAVIEWED PAGE — summary + actions + install
│   ├── <collection>.html           # per-collection pages
│   ├── guides/<slug>.html          # rendered guide pages
│   └── thumb/<shortcode>.jpg       # post thumbnails
├── path_b.py                       # cookie-based IG scraper
├── build_actions.py                # action plan generator
├── render.py                       # static site renderer
└── fetch_thumbs.py                 # thumbnail downloader
```

## Supported Sources

| Source | Adapter | Auth Required | Status |
|--------|---------|---------------|--------|
| **Instagram** | `path_b.py` | Chrome profile copy | ✅ Built |
| **Chrome Bookmarks** | `adapters/chrome_bookmarks.py` | None (local JSON) | ✅ Built |
| **Firefox Bookmarks** | `adapters/firefox_bookmarks.py` | None (local SQLite) | ✅ Built |
| **Edge Bookmarks** | `adapters/edge_bookmarks.py` | None (local JSON) | ✅ Built |
| **TikTok** | `adapters/tiktok_adapter.py` | Chrome profile copy | 🔜 Planned |
| **Twitter/X Bookmarks** | `adapters/twitter_adapter.py` | API bearer token | 🔜 Planned |
| **Pinterest Boards** | `adapters/pinterest_adapter.py` | Chrome profile copy | 🔜 Planned |
| **Reddit Saved** | `adapters/reddit_adapter.py` | OAuth token | 🔜 Planned |
| **YouTube Watch Later** | `adapters/youtube_adapter.py` | Chrome profile copy | 🔜 Planned |

All adapters normalize into the same JSONL schema. Use `adapters/merge_sources.py` to combine with cross-source dedup.

---

## Execution Steps

### Phase 1: Project Setup

```bash
mkdir -p <project>/data <project>/guides <project>/site/thumb <project>/site/guides
```

Ask user for:
- **Project name/title** (e.g., "DejaViewed", "My AI Bookmarks")
- **Tagline** (one sentence)
- **Their IG handle** (for credits — goes in footer, NOT in creator graph)
- **URL JSON files** — one per collection. Validate format.
- **Chrome profile path** — verify `.profile-copy/Default/Cookies` exists

Set brand constants at top of render.py:
```python
HANDLE = "@userhandle"
TITLE = "Their Title"
TAGLINE = "Their tagline."
```

### Phase 2: Scrape (path_b.py)

**CRITICAL SECURITY RULES:**
- Cookie values are NEVER printed, logged, written to any file, or echoed
- Only existence checks: `sessionid present: yes/no`
- Cookies stay inside `requests.Session` and are garbage-collected on exit

For each collection URL file:
```bash
python3 path_b.py --collection <name> --urls-file data/<name>_urls.json --pause 1.5
```

**What path_b.py does:**
1. Load cookies from copied Chrome profile via `browser_cookie3`
2. For each URL: GET with browser-like headers, extract from HTML:
   - `og:description` → likes, comments, handle, date, caption
   - `og:image` → thumbnail URL (used later)
   - `og:video` / URL pattern → media_type (reel/video/image)
   - Full caption from embedded JSON blobs
   - Outbound URLs from anchors + JSON
3. Write JSONL: one record per post with full caption text
4. Resume support: skip already-scraped URLs
5. Rate limit: 1.5s between requests (configurable)

**Retry logic:** 429/5xx → exponential backoff (5s × attempt). 404/410 → record as dead. 3 attempts max.

**LESSONS LEARNED (mistakes to avoid):**
- `og:description` is TRUNCATED (~150 chars). The real caption lives in `<script type="application/json">` embedded JSON blobs as `"text"` field inside media objects. ALWAYS extract from embedded JSON first, fall back to og:description.
- IG signed CDN URLs (`scontent.cdninstagram.com`) expire within hours and have referer protection. NEVER hotlink them — download to local `site/thumb/`.
- Some posts return 200 but contain a login wall. Check for `"loginRequired"` in the response body.

### Phase 3: Classify + Enrich (catalog building)

Build `data/catalog.jsonl` — the master record for every post across all collections.

**For each scraped record**, produce these fields:

| Field | Source | Notes |
|-------|--------|-------|
| `post_url` | scrape | Original IG URL |
| `creator` | scrape | `@handle` from og:description |
| `collection` | input | Which URL file it came from |
| `date` | scrape | From og:description pattern |
| `media_type` | scrape | reel/video/image from URL + og tags |
| `caption_original` | scrape | Full caption text |
| `summary` | **LLM** | 1-3 sentences, ≤320 chars. Concrete. |
| `card_title` | **LLM** | ≤70 chars. `Subject — value/angle` format. |
| `type` | **LLM** | repo/tool/technique/tutorial/inspiration/resource |
| `domains` | **LLM** | e.g., ["3d","design","crypto","coding"] |
| `audience` | **LLM** | beginner/intermediate/advanced |
| `tools_mentioned` | **LLM** | Named tools from caption |
| `repos_or_projects_mentioned` | **LLM** | Named repos/projects |
| `models_mentioned` | **LLM** | Named AI models |
| `techniques_mentioned` | **LLM** | Named techniques |
| `key_takeaways` | **LLM** | 1-3 bullet points |
| `deep_dive_candidate` | **LLM** | true/false — is there enough substance for a guide? |
| `deep_dive_topic` | **LLM** | slug for guide filename if candidate |
| `links` | extraction | Array of `{label, url}` — all outbound links |
| `drop` | **LLM** | true if post has zero identifiable substance |
| `tier` | curation | S/A/B/C assigned during curation phase |

**TITLE RULES (critical — user will complain if you get this wrong):**
- Format: `Subject — value/angle` (≤70 chars)
- Subject = the NAMED thing (repo name, tool name, technique, person)
- Angle = why someone saved it (2-6 words)
- GOOD: `SentrySearch — local Qwen3-VL dashcam search engine`
- GOOD: `GeoSpy.ai — geolocate any photo from buildings/shadows`
- BAD: `Claude Code` (what about it??)
- BAD: `AI tool` (which one??)
- BAD: `@creator: first words of caption...` (lazy, don't do this)
- Every title must answer: "WHAT is this and WHY did I save it?"

**SUMMARY RULES:**
- Concrete. Name the tools/repos/handles.
- If it's DM-bait ("comment X for the link"), say so honestly: "DM-only — caption claims it's a Hyperliquid bot setup"
- If the content is thin, say it's thin. Don't invent.

**DROP RULES:**
- Drop if: pure emoji/hashtags, empty caption, off-topic meme with zero domain substance, DM-bait that doesn't even name the subject
- Keep if: names a real tool/repo/technique, teaches a concept even briefly, is a teaser that NAMES the valuable thing behind the DM
- Be reasonably generous. 10-20% drop rate is normal. 40%+ means you're too aggressive.

**LINK EXTRACTION (every card needs links):**
Extract from the FULL caption text + tools_mentioned + repos fields:
1. Explicit `https://` URLs (skip IG/FB self-links)
2. `github.com/owner/repo` mentions (with or without https)
3. Bare domain mentions (`prompt-genie.com`, `n8n.io`)
4. Known tool → URL mappings (maintain a dictionary of ~50 common tools → their websites)
5. `@handle` mentions → `https://instagram.com/<handle>` (skip the post's own creator)
6. Cap at 15 links per card, prioritize specificity

### Phase 4: Curate (tiers + structure)

Build `data/curation.json`:

```json
{
  "tiers": { "<post_url>": "S|A|B|C", ... },
  "buckets": { "bucket_name": ["<post_url>", ...], ... },
  "stacks": [ { "name": "...", "why": "...", "posts": ["<url>", ...] } ],
  "cross_collection_themes": [ ... ]
}
```

**Tier criteria:**
- **S** — actionable right now, links to real repos/tools, teaches a complete technique
- **A** — high value, good substance, named tools/repos
- **B** — decent reference, partial info, worth keeping
- **C** — thin but not droppable, mostly teasers or vague

Aim for: ~10% S, ~25% A, ~40% B, ~25% C

### Phase 5: Deep-Dive Guides (for S/A tier candidates)

For posts flagged `deep_dive_candidate: true` (typically 10-25 posts):

1. Research the actual tool/repo/technique beyond what the IG caption says
2. Write a markdown guide (`guides/<slug>.md`) with:
   - H1 title
   - What it is + why it matters
   - How to install/use it
   - Code examples if relevant
   - Links to source repos, docs, alternatives
   - Honest assessment (limitations, gotchas)
3. Track confidence: `high` (verified from primary sources) vs `medium` (extrapolated)

### Phase 6: Download Thumbnails

```bash
python3 fetch_thumbs.py
```

For each IG post: GET page → extract `og:image` URL → download JPEG to `site/thumb/<shortcode>.jpg`.
Resume-safe (skip existing). 1.5s pacing. Cookie session required.

**WHY LOCAL:** IG CDN URLs are signed + expire + referer-blocked. Hotlinking will 403 within hours. Always download.

### Phase 7: Render Static Site (render.py)

render.py is the main output generator. It builds:
- `site/dejaviewed.html` — summary page: hero + install/sources sidebar + action plan sections
- `site/index.html` — all posts, all collections
- `site/<collection>.html` — per-collection views
- `site/guides/<slug>.html` — deep-dive guide pages

**DESIGN SPEC (the user expects ALL of these):**

**Layout:**
- Two-panel: sticky left sidebar (280px) + right main content
- Main content: CSS masonry 3-column layout (`column-count: 3`)
- Breaks to 2 columns at 1200px, 1 column at 900px
- Cards break-inside: avoid for clean masonry flow

**Theme:**
- Dark mode: `--bg: #0a0a12`, `--panel: #12121f`, `--border: #1e1e35`
- Body font: `'SF Mono', 'Fira Code', 'JetBrains Mono', Menlo, monospace`
- Line-height: 1.6, good letter spacing for readability
- Gradient text headlines: white → violet → pink
- Radial gradient backdrop on hero

**Hero Block (top of every page):**
- 1/2 + 1/2 horizontal grid (`hero-grid`)
- Left half (`hero-left`): title (gradient text), WHY paragraph, BAN stats strip
- Right half: Creators panel (catalog pages) OR install/sources sidebar (dejaviewed page)
- Responsive: stacks to single column at 900px

**Creators Panel:**
- Every creator who contributed posts (EXCLUDE the catalog owner/curator from graph)
- Horizontal bar per creator: segments colored by tier (S=gold, A=violet, B=blue, C=gray)
- Bar width scales proportionally: max-count creator fills 100% width, others proportional
- Click a bar segment → reset all filters, scroll to that card with highlight animation
- Sorted by post count descending, then S/A density

**Sidebar:**
- Search box (filters by text across title, summary, tools, repos, creator)
- Category filter buttons: All, Repos, Guides, Skills, Tools, Platforms, Resources, Art, Design, UI/UX
- Multi-select OR logic (selecting Repos+Tools shows anything categorized as either)
- Color-coded category tokens with counts
- Tier filter pills: S, A, B, C (multi-select OR)
- Collection pills (if multiple collections)
- Sort dropdown: Tier, Collection, Date, Creator

**Cards:**
- Title (h4, monospace, 13px)
- Creator handle → links to IG profile
- Collection + date + tier badge
- Summary paragraph
- Action buttons: "Open post ↗" (for IG) or "Browse ↗" (green, for non-IG URLs) + "Deep dive →" (if guide exists)
- **Links row** at bottom: every extracted link as a small pill/chip, clickable, labeled by domain
- **Thumbnail** at very bottom: aspect-ratio 5:2, lazy-loaded, click opens post, onerror hides element
- Left border colored by primary category

**Category Colors:**
```
--c-repo: #4cda8c    --c-tool: #f0a050    --c-skill: #e060a0
--c-guide: #a78bfa   --c-platform: #e0d040 --c-resource: #40d0e0
--c-art: #f05060     --c-design: #fb7185   --c-uiux: #60a5fa
```

**Tier Colors:**
```
S: #fbbf24 (gold)    A: #a78bfa (violet)
B: #60a5fa (blue)    C: #6a6a80 (gray)
```

**Section Grouping:**
When "All" category filter is active, group cards under section headers:
Guides → Repos → Skills → Tools → Platforms → Art → Design → UI/UX → Resources

**Navigation:**
- `DEJAVIEWED` tab (gold gradient) → `ALL` → source group labels with sub-page pills
- Source groups: platform label (e.g., "Instagram") with collection sub-links (AI1/AI2/etc.) nested inline
- `.src-group` container wraps `.src-label` + `.sub-links` with pill-shaped sub-nav items
- Active tab/sub-tab gets gradient highlight

**Skill Callout (on catalog pages, below hero):**
- Show install + invoke commands
- Collapsible example prompt

**Guide Pages:**
- Render markdown with `marked.js` + `DOMPurify` (security: no raw innerHTML)
- Confidence badge: high (green) or medium (amber)
- Back link to catalog
- Same dark theme

**SECURITY:**
- ALL card rendering via DOM `createElement` — NO innerHTML (except DOMPurify-sanitized guide markdown)
- This is enforced by pre-commit hooks. innerHTML usage will be blocked.

**JavaScript Rendering:**
- Posts embedded as JSON in `<script>` tag
- Cards built via `el()` helper that creates DOM elements safely
- Filter state managed via `Set` objects for categories and tiers
- Segment click: extract post ID from href anchor, reset filters, smooth scroll + brief outline highlight

### Phase 8: Browser Bookmarks + Other Sources

**Auto-detect available sources:**
```bash
# Check for Chrome bookmarks
python3 adapters/chrome_bookmarks.py --out data/chrome_bookmarks.jsonl

# Check for Firefox bookmarks  
python3 adapters/firefox_bookmarks.py --out data/firefox_bookmarks.jsonl

# Check for Edge bookmarks
python3 adapters/edge_bookmarks.py --out data/edge_bookmarks.jsonl

# Merge all sources (dedup by URL, keep richer metadata)
python3 adapters/merge_sources.py \
  --sources data/catalog.jsonl data/chrome_bookmarks.jsonl data/firefox_bookmarks.jsonl \
  --out data/catalog_merged.jsonl --dedup-by url
```

Each adapter normalizes bookmarks into the same schema as IG records. Cross-source dedup: if the same URL appears from Chrome AND Instagram, the merger keeps the richer record (IG caption > bookmark title) and adds `sources: ["instagram", "chrome"]`.

If the user has additional curated content beyond saves/bookmarks (repos, guides, archive collections, tools):
- Merge into catalog.jsonl with `creator: "@userhandle"`, `media_type: "catalog"`
- Type field: `repo`, `skill`, `tool`, `guide`, `platform`, `resource`
- These get "Browse ↗" buttons (green) instead of "Open post ↗"
- Same title/summary/link quality standards apply

### Phase 9: The DejaViewed Page (THE KILLER FEATURE)

The catalog answers "what did I save?" — the DejaViewed page answers **"what should I actually DO?"**

```bash
python3 build_actions.py
```

This reads catalog.jsonl and generates `data/actions.json` — a structured rollup that groups the best items by action type:

| Section | What it shows |
|---------|--------------|
| **Clone These Repos** | S/A tier repos with git clone commands |
| **Install These Tools** | Tools with pip/npm/brew install commands |
| **Read These Deep-Dives** | Our written guides, linked to guide pages |
| **Try These Techniques** | Techniques with what you'd need to try them |
| **Bookmark These Platforms** | Services/platforms worth keeping |
| **Design & Art Resources** | Archives, collections, inspiration |
| **Teasers & DM-Bait** | Honest notes on gated/thin content |

Each action item:
- Has a concrete title and "why" sentence
- Links back to the source catalog card(s)
- Includes runnable commands where applicable (click-to-copy)
- Shows tier badge and outbound links

Also generates a **Save Profile** — a witty 1-2 sentence assessment of the user's hoarding habits based on the distribution (e.g., "You save mostly repos and tools but only 5% are guides — you hoard more than you study.")

**Page layout — matches the catalog pages:**
- Same hero-grid: left column = title + WHY + BAN stats, right column = sidebar with Install card + Sources card + Save Profile
- Section jump pills below hero (one per action category, with item counts)
- Action items in 3-column masonry cards with tier-colored left borders
- Click-to-copy on all command code blocks

**Nav structure:**
- `DEJAVIEWED` (gold gradient, first position) → `ALL` → source groups (e.g., "Instagram" label with AI1/AI2/AI3/AI4 sub-links)
- Source groups are expandable — each platform gets a label with its collection sub-pages nested inline

The DejaViewed page renders as `site/dejaviewed.html` — the primary landing page and first nav tab.

---

## Mistakes to Avoid (Learned the Hard Way)

1. **Generic titles will get you yelled at.** "Claude Code" as a title is useless. ALWAYS "Subject — why it matters". Every. Single. Card.

2. **Don't render category chips on cards.** The colored left border + section grouping already conveys category. Chips rendered as tall ugly boxes despite CSS fixes. Just don't.

3. **Don't over-drop.** First pass dropped 74/170 posts (43%). User wanted them back. 10-20% is the sweet spot. Be generous when a subject is named.

4. **Don't put the catalog owner in the creator graph.** They're the curator, not a creator. It inflates the bars and looks wrong.

5. **Don't use flex-fill bars.** If every creator's bar fills 100% width, you can't compare. Use proportional width where max-count = 100%.

6. **IG CDN URLs expire.** Download thumbnails locally. Always. No exceptions.

7. **og:description is truncated.** The good stuff is in embedded JSON. Extract from `<script type="application/json">` blocks.

8. **innerHTML gets blocked by security hooks.** Use DOM createElement for everything. DOMPurify+marked for guide markdown only.

9. **Don't forget links.** Every card should have clickable links to repos, tools, websites mentioned. Use known-tool URL dictionary + caption URL extraction + @handle → IG profile links.

10. **Backup before enrichment passes.** Every rewrite of catalog.jsonl should `cp catalog.jsonl catalog.jsonl.bakN` first. You WILL need to diff or rollback.

11. **Thumbnail goes BELOW title/summary, not above.** Title and description are the hook; thumbnail is supporting visual.

12. **Monospace body font reads better** for this kind of technical catalog than sans-serif (Inter). Match ai3-catalog's `SF Mono` stack.

13. **The DejaViewed summary page must match the catalog page layout.** Use the same `hero-grid` with left/right columns — NOT a centered hero block. Left = title + WHY + BANs. Right = install/sources sidebar. Section jump pills below. Keep it compact — don't waste vertical space with big centered text blocks.

14. **Long code commands in narrow grid columns will overlap.** Use `white-space:nowrap;overflow-x:auto` on code blocks in sidebars/cards — they scroll instead of overlapping adjacent elements.

15. **NEVER unconditionally overwrite card_title in render.py.** The enriched title in catalog.jsonl IS the title. Render.py must only set card_title as a FALLBACK when the field is empty/missing. If you write `p["card_title"] = derived_title` without checking first, you'll stomp every enriched title back to garbage like "Claude" on every render. This was the single most repeated bug in the original build — caught and asked to fix THREE times.

---

## Output Checklist

Before declaring done, verify:

- [ ] Every card has a "Subject — angle" title (no bare names, no `@creator:` prefixes)
- [ ] Every card has a 1-3 sentence summary that names concrete things
- [ ] Links extracted and displayed for every card that has linkable content
- [ ] Thumbnails downloaded locally (not hotlinked)
- [ ] Creator graph excludes the catalog owner
- [ ] Creator graph bars scale proportionally (max = 100% width)
- [ ] Category filters work (multi-select OR logic)
- [ ] Tier pills filter correctly
- [ ] Search filters across title, summary, tools, repos, creator
- [ ] Section grouping appears when "All" is selected
- [ ] Guide pages render with confidence badges
- [ ] No innerHTML usage except DOMPurify-sanitized markdown
- [ ] Cookie values never appear in any output
- [ ] Drop rate is 10-20%, not 40%+
- [ ] Masonry layout with 3 columns, responsive breakpoints
- [ ] DejaViewed summary page has hero-grid layout (not centered hero block)
- [ ] DejaViewed page has install/sources sidebar, section jump pills, action cards
- [ ] Nav order: DEJAVIEWED (gold) → ALL → source groups with sub-links
- [ ] File is `dejaviewed.html` (not playbook.html or actions.html)
