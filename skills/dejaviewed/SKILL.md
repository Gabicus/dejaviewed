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
2. Scrapes each post with cookie-based requests
3. Classifies, enriches, tiers every post
4. Writes deep-dive guides for high-signal posts
5. Renders a complete static dark-mode catalog site

**The user should NEVER need to:**
- Open DevTools or run console scripts
- Manually extract URLs from any page
- Copy-paste data from their browser
- Do any step that Claude can automate

---

## Prerequisites

### What the user provides:
1. **One or more saved collection URLs** — e.g., `https://www.instagram.com/user/saved/quant/12345/`
2. **A copied Chrome/Chromium profile** (one-time setup, already done for returning users)

### What must exist on disk:
1. **Chrome profile copy** at `<project>/.profile-copy/Default/Cookies`
   - User copies their Chrome profile directory while Chrome is CLOSED
   - Linux default source: `~/.config/google-chrome/Default/`
   - macOS: `~/Library/Application Support/Google/Chrome/Default/`
   - Command: `cp -r ~/.config/google-chrome/Default <project>/.profile-copy/Default`
   - This profile must have an active Instagram session (user logged in via Chrome)

2. **Python 3.10+** with packages:
   ```bash
   pip install requests browser-cookie3
   ```

3. **Playwright MCP server** must be available (standard Claude Code plugin)
   - Verify: check if `mcp__plugin_playwright_playwright__browser_navigate` tool exists
   - If not available, fall back to asking user for URLs (last resort only)

### First-time project setup:
```bash
mkdir -p <project>/data <project>/guides <project>/site/thumb <project>/site/guides <project>/.playwright-mcp
```

---

## Phase 0: URL Extraction via Playwright MCP

**THIS IS THE CRITICAL AUTOMATION STEP. NEVER SKIP IT. NEVER ASK THE USER TO DO THIS MANUALLY.**

The user gives you a saved collection URL like:
```
https://www.instagram.com/6ab3/saved/quant/17896187445432291/
```

You must use the Playwright MCP server to:
1. Load the user's Instagram session cookies
2. Inject them into the Playwright browser context
3. Navigate to the saved collection
4. Scroll to load all posts
5. Extract every post URL
6. Save to `data/<collection>_urls.json`

### Step 0.1: Extract cookies from Chrome profile

Run this Python script via Bash to export cookies to a temp JSON file:

```python
# Run via Bash tool — outputs cookies to a file for Playwright injection
python3 -c "
import browser_cookie3, json
cj = browser_cookie3.chrome(
    cookie_file='<project>/.profile-copy/Default/Cookies',
    domain_name='.instagram.com'
)
cookies = []
for c in cj:
    if 'instagram' in c.domain:
        cookies.append({
            'name': c.name,
            'value': c.value,
            'domain': c.domain,
            'path': c.path or '/',
            'secure': bool(c.secure),
            'httpOnly': False,
        })
with open('/tmp/ig_cookies.json', 'w') as f:
    json.dump(cookies, f)
# Security: only print count and session presence, NEVER print cookie values
has_session = any(c['name'] == 'sessionid' for c in cookies)
print(f'Exported {len(cookies)} cookies (sessionid present: {has_session})')
"
```

**CRITICAL SECURITY:** Cookie VALUES must NEVER be printed, logged, or written to any file other than the temp injection file. Only existence checks are allowed.

**If `browser_cookie3.chrome()` fails**, try `browser_cookie3.chromium()` instead — some Linux systems use the Chromium keyring path.

### Step 0.2: Generate the Playwright injection script

You CANNOT use `require()` or dynamic `import()` inside Playwright's `browser_run_code` sandbox — they will throw `ReferenceError: require is not defined` or `ERR_VM_DYNAMIC_IMPORT_CALLBACK_MISSING`.

Instead, generate a complete JavaScript file via Python that embeds the cookie data inline, then execute it via `browser_run_code` with the `filename` parameter.

```python
# Run via Bash tool — generates the Playwright script with embedded cookies
python3 << 'PYEOF'
import json

# Read the exported cookies
with open('/tmp/ig_cookies.json') as f:
    cookies = json.load(f)

# Set your collection URL and name
COLLECTION_URL = "https://www.instagram.com/6ab3/saved/quant/17896187445432291/"
COLLECTION_NAME = "quant"

# Generate the Playwright script
script = f"""async (page) => {{
  // Step 1: Inject cookies into browser context
  const cookies = {json.dumps(cookies)};
  const context = page.context();
  await context.addCookies(cookies);

  // Step 2: Navigate to saved collection
  // IMPORTANT: Use 'domcontentloaded', NOT 'networkidle' — Instagram never stops streaming
  await page.goto('{COLLECTION_URL}', {{ waitUntil: 'domcontentloaded', timeout: 30000 }});

  // Step 3: Wait for initial content to render
  await page.waitForTimeout(5000);

  // Step 4: Scroll to load ALL posts (IG lazy-loads on scroll)
  let previousHeight = 0;
  let scrollAttempts = 0;
  const maxAttempts = 50; // Safety cap — most collections finish in <10 scrolls

  while (scrollAttempts < maxAttempts) {{
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.waitForTimeout(2000);

    const currentHeight = await page.evaluate(() => document.body.scrollHeight);
    if (currentHeight === previousHeight) {{
      // Double-check: wait a bit more and try once more
      await page.waitForTimeout(3000);
      const finalHeight = await page.evaluate(() => document.body.scrollHeight);
      if (finalHeight === currentHeight) break;
    }}
    previousHeight = currentHeight;
    scrollAttempts++;
  }}

  // Step 5: Extract all post URLs
  const urls = await page.evaluate(() => {{
    const links = document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]');
    const uniqueUrls = [...new Set([...links].map(a => {{
      const href = a.href;
      return href.startsWith('http') ? href : 'https://www.instagram.com' + href;
    }}))];
    return uniqueUrls;
  }});

  return JSON.stringify({{ collection: '{COLLECTION_NAME}', count: urls.length, scrollAttempts, urls }});
}}"""

# IMPORTANT: Write to .playwright-mcp/ directory — Playwright sandbox blocks files outside
# the project root and .playwright-mcp/ directory
output_path = '<project>/.playwright-mcp/extract_urls.js'
with open(output_path, 'w') as f:
    f.write(script)
print(f"Script written to {output_path}")
PYEOF
```

### Step 0.3: Execute the Playwright script

Use the `browser_run_code` tool with the `filename` parameter (NOT inline `code`):

```
mcp__plugin_playwright_playwright__browser_run_code(
  filename=".playwright-mcp/extract_urls.js"
)
```

**IMPORTANT FILE PATH RULES:**
- The `filename` parameter uses paths RELATIVE to the project root
- Files MUST be inside the project directory or `.playwright-mcp/` subdirectory
- Files in `/tmp/` or other system paths will be REJECTED with: `"File access denied: /tmp/... is outside allowed roots"`
- Always write generated scripts to `.playwright-mcp/<name>.js`

### Step 0.4: Handle the result

The script returns a JSON string. Parse it and save to `data/<collection>_urls.json`:

```python
# The result from browser_run_code is a JSON string — parse and save
import json
result = json.loads(RESULT_FROM_PLAYWRIGHT)
with open('data/<collection>_urls.json', 'w') as f:
    json.dump(result, f, indent=2)
print(f"Saved {result['count']} URLs for collection '{result['collection']}'")
```

### Playwright Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `ReferenceError: require is not defined` | Used `require()` in browser_run_code | Write script to file, use `filename` parameter |
| `ERR_VM_DYNAMIC_IMPORT_CALLBACK_MISSING` | Used dynamic `import()` | Same — write to file |
| `File access denied: ... outside allowed roots` | Script file not in project dir | Write to `.playwright-mcp/` subdirectory |
| `TimeoutError: page.goto: Timeout exceeded` | Used `networkidle` wait strategy | Use `domcontentloaded` — IG never stops streaming |
| Redirected to `/accounts/login/` | Cookies not injected or expired | Re-export cookies, verify `sessionid` exists |
| Redirected to `facebook.com/login` | Session fully expired | User needs to log into IG in Chrome, then re-copy profile |
| `0 URLs extracted` | Page didn't fully load | Increase `waitForTimeout` to 8000ms after navigation |
| Only partial URLs | Didn't scroll enough | Increase `maxAttempts` or add longer delays between scrolls |
| `context.addCookies is not a function` | Wrong Playwright API | Use `page.context().addCookies(cookies)` — exact syntax |

### Cookie injection — why `context.addCookies()`, not `document.cookie`

Instagram session cookies are `HttpOnly` and `Secure`. Browser-side `document.cookie` cannot set `HttpOnly` cookies — they're invisible to JavaScript. You MUST use the Playwright context API (`page.context().addCookies()`) which operates at the browser engine level and can set any cookie attribute.

If you try `document.cookie = "sessionid=..."` — it will silently fail and IG will redirect to login.

---

## Phase 1: Project Setup

```bash
mkdir -p <project>/data <project>/guides <project>/site/thumb <project>/site/guides
```

Ask user for:
- **Project name/title** (e.g., "DejaViewed", "My AI Bookmarks")
- **Tagline** (one sentence)
- **Their IG handle** (for credits — goes in footer, NOT in creator graph)
- **Collection name** — derived from URL path (e.g., `/saved/quant/` → "quant")
- **Chrome profile path** — verify `.profile-copy/Default/Cookies` exists

Set brand constants at top of render.py:
```python
HANDLE = "@userhandle"
TITLE = "Their Title"
TAGLINE = "Their tagline."
```

---

## Phase 2: Scrape (path_b.py)

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

**IMPORTANT:** The `--collection` argument is a free-form string (no hardcoded choices list). Any collection name works.

**Retry logic:** 429/5xx → exponential backoff (5s × attempt). 404/410 → record as dead. 3 attempts max.

**LESSONS LEARNED (mistakes to avoid):**
- `og:description` is TRUNCATED (~150 chars). The real caption lives in `<script type="application/json">` embedded JSON blobs as `"text"` field inside media objects. ALWAYS extract from embedded JSON first, fall back to og:description.
- IG signed CDN URLs (`scontent.cdninstagram.com`) expire within hours and have referer protection. NEVER hotlink them — download to local `site/thumb/`.
- Some posts return 200 but contain a login wall. Check for `"loginRequired"` in the response body.

---

## Phase 3: Classify + Enrich (catalog building)

Build `data/catalog.jsonl` — the master record for every post across all collections.

**ALWAYS backup before writing:** `cp data/catalog.jsonl data/catalog.jsonl.bakN`

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
| `medium` | fixed | "instagram" for IG posts |
| `tools_mentioned` | **LLM** | Named tools from caption |
| `repos_or_projects_mentioned` | **LLM** | Named repos/projects |
| `models_mentioned` | **LLM** | Named AI models |
| `techniques_mentioned` | **LLM** | Named techniques |
| `key_takeaways` | **LLM** | 1-3 bullet points |
| `deep_dive_candidate` | **LLM** | true/false — is there enough substance for a guide? |
| `deep_dive_topic` | **LLM** | slug for guide filename if candidate |
| `links` | extraction | Array of `{label, url}` — all outbound links |
| `drop` | **LLM** | true if post has zero identifiable substance |
| `tier` | **LLM** | S/A/B/C assigned based on actionability and substance |

### TITLE RULES (critical — user WILL complain if you get this wrong):
- Format: `Subject — value/angle` (≤70 chars)
- Subject = the NAMED thing (repo name, tool name, technique, person)
- Angle = why someone saved it (2-6 words)
- GOOD: `SentrySearch — local Qwen3-VL dashcam search engine`
- GOOD: `GeoSpy.ai — geolocate any photo from buildings/shadows`
- GOOD: `Heston Model — stochastic volatility for realistic options pricing`
- BAD: `Claude Code` (what about it??)
- BAD: `AI tool` (which one??)
- BAD: `@creator: first words of caption...` (lazy, don't do this)
- Every title must answer: "WHAT is this and WHY did I save it?"

### SUMMARY RULES:
- Concrete. Name the tools/repos/handles.
- If it's DM-bait ("comment X for the link"), say so honestly: "DM-only — caption claims it's a Hyperliquid bot setup"
- If the content is thin, say it's thin. Don't invent.

### DROP RULES:
- Drop if: pure emoji/hashtags, empty caption, off-topic meme with zero domain substance, DM-bait that doesn't even name the subject
- Keep if: names a real tool/repo/technique, teaches a concept even briefly, is a teaser that NAMES the valuable thing behind the DM
- Be reasonably generous. 10-20% drop rate is normal. 40%+ means you're too aggressive.

### LINK EXTRACTION (every card needs links):
Extract from the FULL caption text + tools_mentioned + repos fields:
1. Explicit `https://` URLs (skip IG/FB self-links)
2. `github.com/owner/repo` mentions (with or without https)
3. Bare domain mentions (`prompt-genie.com`, `n8n.io`)
4. Known tool → URL mappings (maintain a dictionary of ~50 common tools → their websites)
5. `@handle` mentions → `https://instagram.com/<handle>` (skip the post's own creator)
6. Cap at 15 links per card, prioritize specificity

---

## Phase 4: Curate (tiers + structure)

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

**IMPORTANT:** If you assign tiers during enrichment (Phase 3), you MUST also update `data/curation.json` with the new tiers. The render.py reads tiers from curation.json, NOT from catalog.jsonl's tier field. Both must be in sync.

---

## Phase 5: Deep-Dive Guides (for S/A tier candidates)

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

---

## Phase 6: Download Thumbnails

```bash
python3 fetch_thumbs.py
```

For each IG post: GET page → extract `og:image` URL → download JPEG to `site/thumb/<shortcode>.jpg`.
Resume-safe (skip existing). 1.5s pacing. Cookie session required.

**WHY LOCAL:** IG CDN URLs are signed + expire + referer-blocked. Hotlinking will 403 within hours. Always download.

---

## Phase 7: Render Static Site (render.py)

render.py is the main output generator. It builds:
- `site/index.html` — THE DEJAVIEWED PAGE: summary + actions + install (landing page)
- `site/catalog.html` — all posts, all collections
- `site/<collection>.html` — per-collection views
- `site/guides/<slug>.html` — deep-dive guide pages

### Adding a new collection to render.py

When adding a new collection (e.g., "quant"), you MUST update these 4 locations in render.py:

1. **Navigation sources list** — add to the Instagram sub-links tuple:
   ```python
   ("instagram", "Instagram", [("ai1","AI1"),("ai2","AI2"),...,("quant","Quant")]),
   ```

2. **COLL_META dictionary** — add the collection title and description:
   ```python
   "quant": ("Quant — Mathematical Trading Models", "Description here."),
   ```

3. **Render loop** — add to the collection list:
   ```python
   for coll in ["ai1","ai2","ai3","ai4","quant"]:
   ```

4. **Sidebar collection pills** — add to the pills list:
   ```python
   for c in ["ai1","ai2","ai3","ai4","quant"]
   ```

If you miss any of these, the collection page will either not render, not appear in the nav, crash with a KeyError on COLL_META, or not show in the sidebar filter.

### DESIGN SPEC (the user expects ALL of these):

**Layout:**
- Two-panel: sticky left sidebar (280px) + right main content
- Main content: CSS masonry 3-column layout (`column-count: 3`)
- Breaks to 2 columns at 1200px, 1 column at 900px
- Cards break-inside: avoid for clean masonry flow

**Responsive breakpoints (REQUIRED — site must work on all screen sizes):**
- `@media(max-width:900px)` — single column layout, sidebar inline (not sticky), hero-grid stacks, nav wraps
- `@media(max-width:640px)` — smaller fonts, nav horizontal scroll, code blocks wrap, card padding reduced
- `@media(max-width:400px)` — 2-column stats grid, action buttons stack vertically
- `overflow-x:hidden` on html/body to prevent horizontal scroll
- `min-width:0` on all flex/grid children to prevent overflow
- `overflow-wrap:break-word` on text blocks that could overflow narrow containers
- `.wrap` container gets `overflow:hidden` to clip any errant content

**Theme:**
- Dark mode: `--bg: #0a0a0f`, `--panel: rgba(255,255,255,0.03)`, `--border: rgba(255,255,255,0.08)`
- Body font: `'SF Mono', 'Fira Code', 'JetBrains Mono', Menlo, monospace`
- Line-height: 1.6, good letter spacing for readability
- Gradient text headlines: white → violet → pink
- Radial gradient backdrop on hero

**Hero Block (top of every page):**
- 1/2 + 1/2 horizontal grid (`hero-grid`)
- Left half (`hero-left`): title (gradient text), WHY paragraph, BAN stats strip
- Right half: Creators panel (catalog pages) OR install/sources sidebar (dejaviewed page)
- `hero-left` needs `min-width:0; overflow:hidden` to prevent text overflow on narrow screens
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
- **DO NOT render category chips on cards** — the colored left border + section grouping conveys category

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
- Source groups: platform label (e.g., "Instagram") with collection sub-links nested inline
- `.src-group` container wraps `.src-label` + `.sub-links` with pill-shaped sub-nav items
- Active tab/sub-tab gets gradient highlight
- On mobile (≤640px): nav gets `overflow-x:auto; flex-wrap:nowrap` for horizontal scrolling

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

---

## Phase 8: Browser Bookmarks + Other Sources

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

---

## Phase 9: The DejaViewed Page (THE KILLER FEATURE)

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

Also generates a **Save Profile** — a witty 1-2 sentence assessment of the user's hoarding habits.

**Page layout — matches the catalog pages:**
- Same hero-grid: left column = title + WHY + BAN stats, right column = sidebar with Install card + Sources card + Save Profile
- Section jump pills below hero (one per action category, with item counts)
- Action items in 3-column masonry cards with tier-colored left borders
- Click-to-copy on all command code blocks

**Nav structure:**
- `DEJAVIEWED` (gold gradient, first position) → `ALL` → source groups with collection sub-links
- The DejaViewed page renders as `site/index.html` (landing page)
- The "ALL" catalog renders as `site/catalog.html`

---

## Phase 10: Build the Agent Context Layer

```bash
python3 build_context.py
```

This transforms your static catalog into a **structured knowledge base that AI agents can query in real time.** Three files are generated:

### `site/catalog.json` — Queryable Structured Index

A complete JSON representation of every catalog entry with pre-built indices for fast lookup:

```json
{
  "version": "1.0",
  "stats": { "total_entries": 209, "tiers": {"S": 8, "A": 33, ...}, ... },
  "indices": {
    "by_domain": { "quant": ["shortcode1", "shortcode2", ...], ... },
    "by_tool": { "python": ["shortcode1", ...], ... },
    "by_technique": { "stochastic volatility": ["shortcode1", ...], ... },
    "by_model": { "heston model": ["shortcode1", ...], ... },
    "by_type": { "technique": [...], "tool": [...], ... },
    "by_tier": { "S": [...], "A": [...], ... },
    "by_collection": { "quant": [...], "ai1": [...], ... }
  },
  "entries": [
    {
      "id": "shortcode",
      "url": "https://instagram.com/p/...",
      "title": "Subject — angle",
      "summary": "...",
      "tier": "S",
      "domains": ["quant", "options"],
      "tools": ["Python"],
      "techniques": ["Stochastic Volatility"],
      "takeaways": ["..."],
      "links": [{"label": "...", "url": "..."}],
      "has_guide": true
    }
  ]
}
```

**Agent usage patterns:**
```python
import json
catalog = json.load(open('catalog.json'))

# Find all S-tier entries
s_ids = catalog['indices']['by_tier']['S']
s_entries = [e for e in catalog['entries'] if e['id'] in s_ids]

# Find entries about a specific domain
quant_ids = catalog['indices']['by_domain'].get('quant', [])

# Find entries mentioning a tool
python_ids = catalog['indices']['by_tool'].get('python', [])

# Full-text search
matches = [e for e in catalog['entries']
           if 'volatility' in (e['title'] + ' ' + e['summary']).lower()]
```

### `site/context.md` — Agent-Readable Knowledge Map

A structured markdown document that agents load at session start. Contains:
- **Domain map** — every domain with entry counts, tier distribution, and top items
- **S-tier and A-tier listings** — the highest-signal items with takeaways
- **Tool directory** — every tool mentioned with frequency, best tier, and domains
- **Technique directory** — every technique with frequency and tier
- **Usage patterns** — concrete examples of how agents should surface knowledge

When an agent loads this context, it knows: "The user has 27 quant entries including S-tier coverage of Heston Model, Random Matrix Theory, and Avellaneda-Stoikov. When they work on anything options/vol related, surface these first."

### `site/llms.txt` — LLM-Native Discovery

A lightweight discovery file (like robots.txt for AI) that tells LLMs what the catalog contains and where to find the structured data.

### What This Means for Users

**Without context layer:** You save posts → you get a catalog website → you search manually when you remember.

**With context layer:** You save posts → your AI agent already knows every tool, technique, and repo you've collected → when you're building something, it proactively surfaces relevant saves → "You saved an S-tier guide on this exact technique. Want me to pull it up?"

Your saves become working memory for your AI tools.

*Feature contributed by @Shellononback (Instagram)*

---

## Phase 11: Deploy (if applicable)

If the project has a deployment target:

**Cloudflare Pages (used by dejaviewed.dev):**
1. `python3 render.py` — rebuild the site
2. Copy `site/` to the plugin/deploy repo
3. `git add site/ && git commit && git push`
4. Cloudflare Pages auto-deploys from GitHub push

**GitHub Pages:**
1. `python3 render.py`
2. Push `site/` contents to `gh-pages` branch or `/docs` folder

**Manual / local:**
1. `python3 render.py`
2. `cd site && python3 -m http.server 8765`
3. Open `http://localhost:8765`

---

## Mistakes to Avoid (Learned the Hard Way)

1. **NEVER ask the user to manually extract URLs.** Use Playwright MCP. This has been corrected MULTIPLE times. The whole value prop is "give a link, get everything."

2. **Generic titles will get you yelled at.** "Claude Code" as a title is useless. ALWAYS "Subject — why it matters". Every. Single. Card.

3. **Don't render category chips on cards.** The colored left border + section grouping already conveys category. Chips rendered as tall ugly boxes despite CSS fixes. Just don't.

4. **Don't over-drop.** First pass dropped 74/170 posts (43%). User wanted them back. 10-20% is the sweet spot. Be generous when a subject is named.

5. **Don't put the catalog owner in the creator graph.** They're the curator, not a creator. It inflates the bars and looks wrong.

6. **Don't use flex-fill bars.** If every creator's bar fills 100% width, you can't compare. Use proportional width where max-count = 100%.

7. **IG CDN URLs expire.** Download thumbnails locally. Always. No exceptions.

8. **og:description is truncated.** The good stuff is in embedded JSON. Extract from `<script type="application/json">` blocks.

9. **innerHTML gets blocked by security hooks.** Use DOM createElement for everything. DOMPurify+marked for guide markdown only.

10. **Don't forget links.** Every card should have clickable links to repos, tools, websites mentioned. Use known-tool URL dictionary + caption URL extraction + @handle → IG profile links.

11. **Backup before enrichment passes.** Every rewrite of catalog.jsonl should `cp catalog.jsonl catalog.jsonl.bakN` first. You WILL need to diff or rollback.

12. **Thumbnail goes BELOW title/summary, not above.** Title and description are the hook; thumbnail is supporting visual.

13. **Monospace body font reads better** for this kind of technical catalog than sans-serif (Inter). Match ai3-catalog's `SF Mono` stack.

14. **The DejaViewed summary page must match the catalog page layout.** Use the same `hero-grid` with left/right columns — NOT a centered hero block. Left = title + WHY + BANs. Right = install/sources sidebar. Section jump pills below.

15. **Long code commands in narrow grid columns will overlap.** Use `white-space:nowrap;overflow-x:auto` on code blocks in sidebars/cards — they scroll instead of overlapping adjacent elements.

16. **NEVER unconditionally overwrite card_title in render.py.** The enriched title in catalog.jsonl IS the title. Render.py must only set card_title as a FALLBACK when the field is empty/missing. If you write `p["card_title"] = derived_title` without checking first, you'll stomp every enriched title back to garbage. This was the single most repeated bug — caught THREE times.

17. **Keep curation.json and catalog.jsonl tiers in sync.** render.py reads tiers from curation.json. If you add tier fields to catalog.jsonl during enrichment, you MUST also update curation.json or the tiers won't show up on the rendered site.

18. **When adding a new collection, update ALL 4 locations in render.py:** nav sources list, COLL_META dict, render loop, sidebar pills. Missing any one causes a crash or invisible collection.

19. **Playwright `require()` is blocked.** You cannot use `require('fs')` or `require('child_process')` inside `browser_run_code`. Write the full script to a file and use the `filename` parameter instead.

20. **Playwright file paths must be in allowed roots.** Scripts must live in `.playwright-mcp/` or the project directory. `/tmp/` paths will be rejected.

21. **Use `domcontentloaded`, never `networkidle` for IG.** Instagram keeps streaming analytics/tracking requests forever. `networkidle` will always timeout.

22. **Cookies must be injected via `context.addCookies()`.** `document.cookie` cannot set HttpOnly cookies. The session will fail silently and IG will redirect to login.

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
- [ ] Masonry layout with 3 columns, responsive breakpoints work at 900/640/400px
- [ ] No horizontal overflow on any viewport width down to 320px
- [ ] DejaViewed summary page has hero-grid layout (not centered hero block)
- [ ] DejaViewed page has install/sources sidebar, section jump pills, action cards
- [ ] Nav order: DEJAVIEWED (gold) → ALL → source groups with sub-links
- [ ] Landing page is `index.html` (the DejaViewed summary), catalog is `catalog.html`
- [ ] New collections added to ALL 4 locations in render.py
- [ ] curation.json tiers match catalog.jsonl tiers
- [ ] Site tested at desktop (1440px), tablet (768px), and mobile (375px) widths
