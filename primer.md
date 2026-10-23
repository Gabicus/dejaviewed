# DejaViewed · primer

Updated: 2026-10-23 (early)

## PARKED, FRONT OF MIND — pay-to-crawl / data-as-the-asset (own session)

Victor's thesis (2026-10-22): "the knowledge isn't what's valuable anymore, it's the data behind it" — the
aggregated, transcribed, enriched corpus is what people own now. Keep iterating; decide viability with data.
- **Shape that doesn't kill visibility:** HTML, llms.txt, sitemap, sample API stay free (that's how LLMs and
  Google find us). Paid = bulk machine data: full `api/prompts.json`, `llms-full.txt`, full catalog +
  transcripts, packaged as a **versioned dataset release** (one tarball/parquet per release) behind a 402.
- **Rails, ranked:** x402 (Coinbase open standard, USDC on Base, agents already speak it, ~$0 fees, 50¢ works)
  → Cloudflare Pay Per Crawl (apply; fiat, zero code, covers big crawlers that won't pay custom 402s) →
  L402/Lightning only if BTC specifically wanted.
- **Build when ready:** Cloudflare Worker on `/api/v1/*` and `/dataset/*`: free sample tier, 402 with price
  for full; receiving address = PUBLIC address only, ever, in repo/config. Measure demand with analytics
  first (which crawlers hit /api/ and llms-full.txt → that's the buyer list).
- **Open questions:** price (50¢–$1 per pull vs per release), USDC-on-Base vs BTC, licence text for the
  dataset (creators' captions/transcripts are theirs — sell only our enrichment fields + links, see the
  selling-to-agents prompt pack), whether to list on a data marketplace too.
- Honest expectation: pocket change for months at current traffic; worth it as experiment + story.

## Current status

846 entries · 18 collections · 324K crosslinks · 219 deep dives (45 curated) · 64 guide pages · 45 deeper pages · 64 prompt systems · 18 indexed tool hubs (+22 noindex) · 2 comparisons · 2 best-of lists · system-prompt library · 18 collection hubs · method page · **SEO layer on all 961 public pages** (canonical, descriptions, OG images, JSON-LD, FAQ) · start-here page · RSS · IndexNow · entry pages are linked hubs (~17 internal links each) · monetize layer (/go/ redirects, 0 affiliates active) · **analytics LIVE** (Cloudflare + Search Console + Bing; baseline `reports/analytics_2026-10-22.md`) · 63 IG content kits · site search · 0 broken links. Site live at dejaviewed.dev (Cloudflare Pages, auto-deploy from main). Quality gate passes. Everything from the Oct 21 pull is captioned, Whisper-transcribed (medium, GPU), thumbed, LLM-enriched and indexed (api/, sitemap 957 URLs, llms.txt, context.md all live-computed).

### Oct 21 pull (what changed)
- **New pipeline path (Phase 0 v3):** Instagram collection-feed API via agent-browser attached to real Chrome over CDP. Scroll-scrape was lossy (quant showed 12 of 31). 340 items pulled, 265 unique new entries ingested with caption/creator/date/media already filled (`ig_collection_api.py` → `ig_download_media.py` → `ingest_api.py`).
- **Whisper:** 263 new videos + 3 recovered old ones, local mp4 → CUDA int8_float32 (GTX 1050 has no fp16). Model cached, `--local-only` flag.
- **Carousels:** 6 posts vision-read into `data/slides_ocr.json`. Four old "video failures" were carousels.
- **LLM enrichment:** 269 entries titled/summarized/tiered/tagged by Opus agents from caption+transcript+OCR (`llm_enrich_batches.py`, spec in `data/llm_batches/SPEC.md`). 7 drops → tier C with note.
- **Data bugs fixed:** 48 entries had creator "Edited" (scrape artifact) → true creators via media-info API; 7 of those also had captions from the wrong post → corrected + re-enriched. 10 "tutorial" types → "skill".
- **Researcher curation pass (Phase 5c):** 4 Opus lenses (creative fusion, agentic leverage, capital & markets, physical+knowledge) read all 846 entries → 26 proposals → 17 kept (rated ≥4), 2 merged dupes, 7 parked (`data/curation/parked_q3_2026-10-21.json`). Spec: `data/curation/RESEARCHER_SPEC.md` (also in skill references).
- **New scripts:** `ig_collection_api.py`, `ig_download_media.py`, `ingest_api.py`, `llm_enrich_batches.py`, `quality_gate.py`, `curation_export.py`, `build_guides.py`; `rebuild.sh` rewritten to the real phase list; `build_context.py` fixed (reads catalog.json, live counts); sitemap now covers guides/deeper/about/links; domain typo dejaviewed.com → .dev.
- **Skill:** Phase 0 v3, Phase 5c, phase table, lessons #45–50. Public copy synced (`skills/dejaviewed/`), overlay updated with collection ids + coverage.
- Outreach files + dev screenshots moved out of `site/` into `outreach/`.

### Oct 22 (resume) — what changed
- **Caption integrity:** 139/551 pre-October entries had the wrong caption (July stale-page scrape). All verified per post (`ig_refresh_captions.py`), corrected, re-enriched. 13 mis-typed posts (10 carousels, 3 videos) now slide-read/transcribed. 19 unverifiable, flagged.
- **Re-tier:** ai2/ai4/ai7/quant re-rated tier-only (209 entries, 142 changed). S 98 → 55.
- **Built:** Pagefind site search, link checker (0 internal breakages), pHash dedupe (0 confirmed dupes), rate.html + apply_ratings.py, reconcile_ig_export.py, carousel slide-video transcription, 7 parked dives promoted (45 curated).
- All of the above pushed and live.

### Oct 22 (evening) — discoverability + content loop
- **SEO (Phase 14):** `build_seo.py` post-processes every public page (961): canonical clean URL, 150-160 char description, OG/Twitter, JSON-LD (WebSite+SearchAction, Dataset, CollectionPage, Article, FAQPage from prompt-system self-questions, Breadcrumb). 112 share images (`site/og/`). `start-here.html` positioning page (live counts). `feed.xml`. Sitemap lastmod/changefreq, 974 clean URLs. robots.txt allows AI crawlers. 25 target queries → titles (`data/seo/queries.json`, 5 retitled).
- **Analytics:** `analytics_report.py` (Cloudflare GraphQL + Search Console, deltas, AI-crawler table), `indexnow.py` (key served at site root), `analytics_check.sh`, click-paths in `data/analytics/SETUP.md`. Runs clean with no creds; prints exact missing steps.
- **Content kits:** `content_kit.py` → `content/<slug>/` carousel PNGs (1080×1350), caption.md, reel_script.md, optional reel.mp4; `content/INDEX.md` with posted/unposted + next 7. Skill: `dejaviewed-content`.
- Parked: pay-to-crawl (top of this file).

### Oct 22 (pm) — prompt systems
- **Phase 5d built:** every curated dive (45) and hand-written guide (18) now carries a full prompting system: deeper-not-bigger block (pro would / rawest material / methods+tools / external proof / rewritten prompt), one-shot prompt (500-1000 w), 5-9 step prompts each with expect+audit, gap-audit prompt, self-questions, validation oracles, failure modes, agent direction. Written by 10 Opus agents to `data/prompt_systems/SPEC.md`; validator in `scripts/prompt_systems.py`.
- **Rendered:** bottom of every guide page (marked + copy buttons, anchor `#prompt-system`), every deeper page, `site/prompts.html` index, `site/api/prompts.json`, Prompts nav item, landing tile, llms.txt + sitemap entries.
- **Pipeline:** `rebuild.sh` has a `prompts` phase that stops when any target lacks a pack; `build_guides.py --force` and `deeper_dives.py` embed packs; hand-written guides are patched in place between `<!-- prompt-system:start|end -->` markers (lesson #52).
- Security-adjacent packs (jailbreak repo, leaked system prompt, injection-CI, headless, OSINT) are defensive-only; money packs carry paper arms + caps + "no real money" gate.

### Oct 22 (night) — measurement live, indexing pass, monetize layer
- **Creds in:** Cloudflare token (`~/.config/cloudflare/dejaviewed.env`), Search Console service account (Full user on `sc-domain:dejaviewed.dev`, sitemap submitted via API: 974 URLs, 0 errors), Bing (manual add + sitemap processing). `analytics_report.py` runs end-to-end. Bot-score fields are Enterprise-only → UA classes (added `scanner` class).
- **Baseline (7d):** 290 real page views / 280 visits; human-UA share 58%; AI crawlers weekly: ChatGPT-User 119, ClaudeBot 116, PerplexityBot 79, GPTBot 57, OAI-SearchBot 56, CCBot 45; nobody fetches llms-full.txt or /prompts yet. GSC: 0 impressions (new property), URL-inspection sample 6/20 indexed, 13 "discovered, not indexed".
- **Indexing pass (Phase A):** 847 entry pages were orphans (2 links each). Now: breadcrumb, Related (crosslink-weighted, top 6), Appears-in (guides/deeper), More-from-creator, prev/next → avg 16.8 internal links; every guide/deeper links `../e/<id>.html` (static nav for crawlers since guide markdown is client-rendered). noindex on admin/rate/legacy; robots.txt no longer Disallows them (noindex must be crawlable). 55 stub summaries re-enriched by Opus (3 drops). IndexNow re-pinged 969 URLs.
- **Monetize layer (Phase B):** `scripts/build_monetize.py` (idempotent, after `seo`): `site/_redirects` with `/go/<slug>` 302s for 26 tools (clicks measurable in Cloudflare path analytics from day one; `analytics_report.py` has a /go/ table), tool pills/lists link via /go/, footer CTA on 961 pages (DIY GitHub · done-for-you → www.1gabe.com/contact/), FTC disclosure + "affiliate link" label + tip-jar/sponsors/prompt-pack links render ONLY when set. Config: `data/monetize/affiliates.json` (all `pending`), `config.json`, README with activation steps. Research: `data/monetize/affiliates_research.json` (62 tools).
- Ads: rejected (Victor, breaks the design). Pay-to-crawl: still parked (top of file).

### Oct 23 (early) — full SEO review, 3 waves (all live)
- **Audits (read-only, committed):** `data/seo/audit_2026-10-22.json` (25 technical findings, Lighthouse) and `data/seo/content_gaps_2026-10-22.json` (8 pillars, 20-item build list, affiliate/corpus mismatch).
- **Wave 2 technical:** guides server-rendered via markdown-it (`build_guides.render_guide_html`, `--rerender-only`; no marked/DOMPurify/hidden prerender; 780→3,043 crawlable links; 1 H1 each); clean root-absolute URLs everywhere (`normalize_links.py`, LAST html-touching phase; 16,486 `.html` links→0; `serve.py` dev server for clean URLs); static footer nav; `/collections/` 18 hubs → every page ≤2 clicks from home; `/method` (how it works, tiers, affiliate policy, Victor as Person author); entry VideoObject/CreativeWork schema + 846 share cards (`site/og/e/`, hashed); content-hash freshness (`data/seo/content_hashes.json`) drives sitemap lastmod + dateModified; sitemap = indexable HTML only; titles ≤65; FAQPage removed (no rich result since 2023); agent-note lint in quality_gate; Lighthouse mobile home 49→100, catalog 55→93 (`catalog.slim.js`, prerendered first 24 cards + landing sections, self-hosted fonts `site/fonts/`, `site/_headers` HSTS/nosniff/caching); thumbs ≤640px; real 404 page (`site/404.html`, suggests nearest entry/guide); "In short" answer block atop every guide (+ Article.abstract).
- **Wave 3 content:** `/tools/<slug>` hubs (`build_tools.py`, thresholds ≥5 entries, ≥2 S/A, ≥1 curated guide → indexed; 3–4 entries → noindex; takes in `data/tools/*.json`, every paragraph cites /e/; FALSE_TAGS strips word-match mis-tags Cursor/Runway/Llama); `/compare/` (Claude Code vs Codex vs Gemini CLI, AI video generators) and `/best/` (Claude Code skills/plugins 35 items, MCP servers 25) from `data/compare/*.json` via `build_compare.py` with dated sources; `/system-prompts` library (64); Key-facts table on all 64 guides (`data/guides/facts_state.json` last-verified); hooks cookbook rewritten (33 events verified against code.claude.com docs 2026-10-22); new guide `claude-md-examples` (8 pinned public CLAUDE.md files) + pack #64.
- **Facts verified Oct 22 (sources on pages):** Gemini CLI free tier ended 2026-06-18 (→ Antigravity CLI); Claude Code starts at Pro $20; Anthropic's Jun-15 billing split was paused; Codex on ChatGPT Free/Go $8, CLI Apache-2.0; Sora discontinued (app Apr 26, API Sep 24 2026); Kling 4.0 Oct 15 2026.
- **Pipeline order now:** … render → collections → tools → compare → … → seo → monetize → links → gate. `build_api.py` strips blocks from entry pages; always followed by seo+monetize+links. `build_guides.py --force` must be followed by `search_prep.py`/`build_search.sh`.
- Victor's dashboard items (optional): Cloudflare AI Labyrinth off (we WANT AI crawlers), Email Obfuscation off (blocking script), Early Hints on, Rocket Loader off.

## Next up

**MASTER PLAN:** `docs/plans/GROWTH_PLAN_2026-10-23.md` (12 workstreams, 90-day timeline, KPIs). Status report: `docs/reports/dejaviewed_status_2026-10-23.html` (regen: `scripts/build_report.py`). Week-0 Fable items: hooks.json, no-slop gate + word caps in content_kit, 5 new kit formats + 7-day rotation queue, creator outreach file, UTM tags, /api/ index page.

**Victor (needs his logins):**
1. Affiliate signups, in order of (links on site × payout): Runway (36 links, $15/sub), Higgsfield (30, 25% rec.), ElevenLabs (18, 22% rec.), n8n (17, 30% rec.), then TradingView, Kling (verify program). For each: sign up → paste tracking URL into `data/monetize/affiliates.json` `affiliate_url`, set `status: active` → tell Fable (or run `python3 scripts/build_monetize.py` + push). Signup URLs are in that file. Rules: no paid ads, no brand bidding, no coupon framing.
2. Tip jar / GitHub Sponsors handle → `data/monetize/config.json` (`tip_jar_url`, `sponsors_url`). Empty = nothing renders.
3. Post the first content kit (content/INDEX.md "Next 7"); mark in `content/status.json`.

**Fable:**
4a. Fix the enricher's word-match tool tagger upstream (Cursor=pointer, Runway=fashion, Llama=Spanish) — `build_tools.FALSE_TAGS` is the stopgap list.
4b. Confirm with Victor the two /method policy promises (creator removal via contact; reuse with link-back).
4. Weekly (Mondays): `python3 scripts/analytics_report.py` → deltas; watch GSC indexed count (goal: 13 "discovered" → indexed; sitemap 974), impressions for the 5 query bets (`data/seo/queries.json`), /go/ clicks, AI-crawler hits on llms-full.txt (= pay-to-crawl demand signal).
5. ~~404~~ ~~answer blocks~~ DONE. llms.txt directory registrations, GitHub README → site, 1gabe.com cross-link.
6. Content build-list items 9–20 in `data/seo/content_gaps_2026-10-22.json` (token-usage case study, glossary, creator pages ≥4 entries, n8n MCP explained, 'new this week' page) — only after Search Console shows the first wave indexing.
7. Gumroad/offline prompt pack only if Victor wants it (set `prompt_pack_url`).

**Older queue:**

1. ~~Landing redesign~~ DONE Oct 21. ~~Parked dives, carousel videos, re-tier, search, dedupe, link check~~ DONE Oct 22.
2. ai2/ai5/stock2 still ~20% S (small collections, July tiers) — re-tier with `data/llm_retier/SPEC.md` if it bothers you.
3. 3 likely reposts (dedupe report "possible", same creator+title+thumb) — download the missing mp4 to confirm, then merge.
4. Blind re-rate: open /rate.html, rate 30, download JSON → `scripts/apply_ratings.py`.
5. IG data export → `scripts/reconcile_ig_export.py` for the authoritative save list.
6. Embedding-based clustering (replace keyword dives/crosslinks) — only remaining "deeper version" item.
7. Prompt systems: run 3 packs end-to-end for real (e.g. claude-second-brain, plotter-loop, polymarket-99c paper arm) and feed what breaks back into SPEC.md. New curated dives need a pack before publish (rebuild.sh enforces).

## Don't forget

- `cms.py rebuild` BEFORE `enrich_entries.py --sweep` (enrich reads catalog.json, clobbers parquet-only edits) — lesson #50
- Don't write parquet while transcribe.py runs — lesson #48
- pkill/pgrep -f patterns match your own tool shell → use helper scripts (exit 144 ×5 this session)
- Media-info API throttles after ~75 calls; per-post page nav gives stale pk unless you verify returned `code`
- agent-browser bundled Chromium can't decrypt Chrome ≥136 cookies → CDP attach (Phase 0 v3)
- Signed CDN URLs expire in hours → download media right after the pull
- `build_guides.py --force` wipes guide search text → run `search_prep.py` after (rebuild.sh does)
- Secrets only in `~/.config/{cloudflare,google}/` (mode 600); never in chat, never in repo
- NEVER commit `references/site-deployment.md`; `data/media/` and `data/*.bak*` are gitignored
- Chrome window driven over CDP keeps playing whatever post was last opened — park it on about:blank
