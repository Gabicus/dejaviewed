# DejaViewed — 48-hour status, Oct 21–23 2026

Window: 2026-10-21 00:00 to 2026-10-23 · generated 2026-10-23 · site https://dejaviewed.dev

Between Oct 21 and Oct 23 2026 there were 25 commits to the site. The catalog grew from 581 to 846 entries. Every guide now ships a prompt system (64 in total). The site gained tool hubs (18 / 22 indexed / noindex), 2 comparison pages and 2 best-of lists. Technical search-engine optimization (SEO) work brought the live sitemap to 1007 URLs and broken internal links to 0. Nothing earns money yet: affiliate programs active = 0 of 25 eligible (Polymarket skipped), Instagram kits posted = 63 (0) (total kits, posted in brackets). Traffic is small: 252 / 570 real visits (7 days / 28 days), and Google Search Console shows 0 clicks and 0 impressions so far.

## 1. The numbers

| Metric | Before | Now | Source |
|---|---|---|---|
| Catalog entries | 581 | **846** | primer.md; session-log 2026-07-13 |
| Collections |  | **18** |  |
| Deep dives (curated) |  | **219 (45)** |  |
| Guide pages |  | **64** | site/guides/*.html = 65 incl. index |
| Deeper pages |  | **45** |  |
| Prompt systems | 0 | **64** | site/api/prompts.json count |
| Tool hubs indexed / noindex |  | **18 / 22** | site/tools/*.html noindex scan |
| Comparisons |  | **2** |  |
| Best-of lists |  | **2** |  |
| Collection hubs |  | **18** |  |
| Sitemap URLs (live) | 957 (Oct 21) -&gt; 974 (Oct 22 submit) -&gt; 980 (wave 2) | **1007** | curl live sitemap.xml |
| Lighthouse mobile performance, home | 49 (wave-2 baseline run) / 66 (audit run) | **100** | commit 8eaa7f8; audit_2026-10-22.json; +-10 run variance |
| Lighthouse mobile performance, catalog | 55 (wave-2 baseline run) / 35 (audit run) | **93** |  |
| Crawlable links in guide HTML | 780 | **3043** |  |
| Internal links ending in .html | 16486 | **0 (40 remain inside noindex site/legacy/ and site/ai_presentation/)** |  |
| Avg internal links per entry page | 2 | **16.8** |  |
| Broken internal links | 11 | **0** |  |
| Instagram content kits (posted) |  | **63 (0)** |  |
| Affiliate programs active |  | **0 of 25 eligible (Polymarket skipped)** |  |
| Baseline real visits 7d / 28d (Web Analytics) [^1] |  | **252 / 570** |  |
| Edge requests 7d (all, incl. bots) |  | **20291** |  |
| Human-browser share of requests 7d |  | **51% (committed report; primer cites 58% from an earlier run)** |  |
| AI crawler hits 7d [^2] |  | **ChatGPT-User 117, ClaudeBot 116, PerplexityBot 81, Amazonbot 88, GPTBot 58, OAI-SearchBot 55, meta-externalagent 56, Bytespider 64, CCBot 45, Perplexity-User 25, cohere-ai 22, Claude-User 2** |  |
| Google Search Console |  | **0 clicks, 0 impressions (new property); URL-inspection sample: 6/20 indexed, 13 discovered-not-indexed, 1 unknown** |  |
| [/go/](https://dejaviewed.dev/go/) outbound clicks recorded [^3] |  | **0** |  |

[^1]: page views 266 / 760. primer.md cites 280 visits / 290 views from an earlier same-day run; committed report says 252/266.
[^2]: nobody fetched [/llms-full.txt](https://dejaviewed.dev/llms-full.txt) from an AI crawler user agent, the name string a browser or bot sends (UA); 52 hits on [/api/prompts.json](https://dejaviewed.dev/api/prompts.json) (all UAs)
[^3]: layer went live late Oct 22; first real reading comes with the next weekly report

## 2. What was delivered

> Groups follow primer.md's narrative. The 'Oct 23' wave-2/3 commits are timestamped 2026-10-22 22:07-23:27 local (-0400), i.e. 2026-10-23 UTC.

### 2026-10-21 (5 items)

#### October pull: 265 new entries from Instagram

New saves were pulled straight from Instagram's collection data (the old scroll-scraper missed most posts: it saw 12 of 31 in one collection). Every new post got its caption, creator, date and media downloaded, a Whisper speech-to-text transcript (263 videos, run on the local graphics processor (GPU)), and a thumbnail. The catalog grew from 581 to 846 entries across 18 collections.

- Evidence: commits `42b520a`
- Evidence: files `scripts/ig_collection_api.py`, `scripts/ig_download_media.py`, `scripts/ingest_api.py`, `scripts/transcribe.py`
- Evidence: counts items_pulled=340, new_unique_entries=265, videos_transcribed=263, old_videos_recovered=3, carousels_vision_read=6, total_entries=846
- Live: [dejaviewed.dev/catalog](https://dejaviewed.dev/catalog) · `/e/<id>`


#### AI enrichment, data-bug fixes and a quality gate

Opus agents wrote titles, summaries, tiers (S/A/B/C quality grade) and tags for 269 entries from caption + transcript + slide text. 48 entries whose creator showed as 'Edited' (a scrape artifact) got their true creators, and 7 that carried another post's caption were corrected. A hard quality gate (titles, S-tier rate, transcript-or-reason, thumbnails) now blocks bad builds.

- Evidence: commits `42b520a`
- Evidence: files `scripts/llm_enrich_batches.py`, `data/llm_batches/SPEC.md`, `scripts/quality_gate.py`
- Evidence: counts entries_enriched=269, dropped_to_tier_C=7, creator_fixes=48, caption_fixes=7
- Live: [dejaviewed.dev/catalog](https://dejaviewed.dev/catalog)


#### Researcher curation pass: 17 new insight dives

Four Opus 'lenses' (creative fusion, agentic leverage, capital and markets, physical and knowledge) read all 846 entries looking for ideas that live between technologies. 26 proposals were made, 17 shipped as curated deep dives with guide pages, 7 were parked (later promoted).

- Evidence: commits `42b520a`
- Evidence: files `data/curation/RESEARCHER_SPEC.md`, `data/curation/parked_q3_2026-10-21.json`, `scripts/curation_export.py`
- Evidence: counts proposals=26, shipped=17, parked=7, merged_dupes=2
- Live: [dejaviewed.dev/guides/](https://dejaviewed.dev/guides/) · [dejaviewed.dev/deeper/](https://dejaviewed.dev/deeper/)


#### Showcase landing page; catalog moved to [/catalog](https://dejaviewed.dev/catalog)

The home page became a showcase (hero stats, destinations, insight dives, freshest saves, how the pipeline works, install). The full catalog moved to its own page and the nav gained Catalog and About.

- Evidence: commits `746d7b1`, `2f6e509`, `05f9bec`, `a8e0b23`, `9097a51`
- Evidence: files `site/index.html`, `site/catalog.html`, `scripts/build_landing_meta.py`
- Live: [dejaviewed.dev/](https://dejaviewed.dev/) · [dejaviewed.dev/catalog](https://dejaviewed.dev/catalog)


#### Site search, link audit, dedupe, rating and reconcile tools

Pagefind static site search went live (940 pages indexed, search box in the hero and nav). A link checker found and fixed 11 broken internal links and 5 dead external ones (now 0 broken). A perceptual-hash duplicate scan found 0 confirmed duplicates; a blind re-rate page and an Instagram-export reconciler were built for Victor to use later.

- Evidence: commits `ad47f56`
- Evidence: files `site/search.html`, `scripts/check_links.py`, `scripts/dedupe_phash.py`, `site/rate.html`, `scripts/apply_ratings.py`, `scripts/reconcile_ig_export.py`
- Evidence: counts pages_indexed_for_search=940, internal_breakages_fixed=11, external_dead_fixed=5, confirmed_duplicates=0, likely_reposts_unconfirmed=3
- Live: [dejaviewed.dev/search](https://dejaviewed.dev/search) · [dejaviewed.dev/rate](https://dejaviewed.dev/rate)


### 2026-10-22 (10 items)

#### Caption integrity fix (139 wrong captions)

Re-tier agents noticed transcripts contradicting captions. A per-post check showed 139 of 551 older (July-scraped) entries, 25%, carried a different post's caption. All were corrected, along with 44 creators and 13 media types, and re-enriched; 19 posts could not be verified and are flagged.

- Evidence: commits `361c1b9`
- Evidence: files `scripts/ig_refresh_captions.py`
- Evidence: counts captions_fixed=139, creators_fixed=44, media_types_fixed=13, unverifiable_flagged=19
- Live: [dejaviewed.dev/catalog](https://dejaviewed.dev/catalog)


#### Re-tier of July collections

The four July-era collections that were too generous with S-tier (ai2, ai4, ai7, quant) were re-graded on tier only. 142 of 209 changed; site-wide S-tier went from 98 to 55. 'Comment X for the guide' bait posts that delivered nothing dropped to B/C.

- Evidence: commits `361c1b9`
- Evidence: counts entries_rerated=209, changed=142, s_tier_before=98, s_tier_after=55
- Live: [dejaviewed.dev/catalog](https://dejaviewed.dev/catalog)


#### 7 parked dives promoted (45 curated)

The 7 parked research proposals were promoted, bringing curated dives to 45 (219 dives total) with 64 guide pages and 45 deeper pages.

- Evidence: commits `ad47f56`, `361c1b9`
- Evidence: counts curated_dives=45, total_dives=219, guide_pages=64, deeper_pages=45
- Live: [dejaviewed.dev/guides/](https://dejaviewed.dev/guides/) · [dejaviewed.dev/deeper/](https://dejaviewed.dev/deeper/)


#### Prompt systems: one full prompting kit per guide (63, later 64)

Every curated dive and hand-written guide now ends with a full prompt system: a one-shot prompt, 5-9 step prompts each with what to expect and how to audit it, a gap-audit prompt, self-questions, validation checks, failure modes and agent direction. They render on every guide and deeper page, on a [/prompts](https://dejaviewed.dev/prompts) index and as JSON; the rebuild script refuses to publish a guide without one. The 64th pack came with the CLAUDE.md examples guide on Oct 23.

- Evidence: commits `f0d3035`, `06a92ae`
- Evidence: files `data/prompt_systems/SPEC.md`, `scripts/prompt_systems.py`, `site/api/prompts.json`
- Evidence: counts packs=64, words_per_pack=2,850-3,500, validator=63/63 pass at launch
- Live: [dejaviewed.dev/prompts](https://dejaviewed.dev/prompts) · [dejaviewed.dev/api/prompts.json](https://dejaviewed.dev/api/prompts.json) · [dejaviewed.dev/guides/claude-mastery#prompt-system](https://dejaviewed.dev/guides/claude-mastery#prompt-system)


#### Discoverability layer: search-engine optimization (SEO) head, start-here, Really Simple Syndication feed (RSS), share images, IndexNow

Every public page got a canonical URL, a written description, social share tags and structured data (schema.org JSON-LD structured-data markup for search engines (JSON-LD)). A start-here positioning page, an RSS feed and 112 share images were added; robots.txt explicitly allows AI crawlers. IndexNow (instant indexing pings to Bing, Yandex, Seznam) submitted 974 URLs.

- Evidence: commits `baf01ec`, `bac1daa`
- Evidence: files `scripts/build_seo.py`, `scripts/build_og.py`, `scripts/build_start_here.py`, `scripts/build_feed.py`, `scripts/indexnow.py`, `data/seo/queries.json`
- Evidence: counts pages_with_seo_layer=961, share_images=112, indexnow_urls=974, target_queries=25
- Live: [dejaviewed.dev/start-here](https://dejaviewed.dev/start-here) · [dejaviewed.dev/feed.xml](https://dejaviewed.dev/feed.xml) · [dejaviewed.dev/robots.txt](https://dejaviewed.dev/robots.txt) · [dejaviewed.dev/llms.txt](https://dejaviewed.dev/llms.txt)


#### Instagram content kits (63)

A generator turns each guide into a ready-to-post Instagram carousel (1080x1350 slides), caption with creator credits and hashtags, and a reel script. A queue file lists the next 7 to post; none have been posted yet.

- Evidence: commits `baf01ec`
- Evidence: files `scripts/content_kit.py`, `content/INDEX.md`, `content/status.json`, `skills/dejaviewed-content/SKILL.md`
- Evidence: counts kits=63, slides=549, with_video=1, posted=0


#### Analytics: instruments built, credentials connected, first baseline

A report script pulls Cloudflare traffic, real-visitor Web Analytics, AI-crawler hits and Google Search Console data into one weekly markdown report. Victor's Cloudflare token and Search Console service account are in place, the sitemap is submitted to Google and Bing, and the first baseline report is committed.

- Evidence: commits `baf01ec`, `70eda20`, `0e9a751`, `97464b6`, `812e876`
- Evidence: files `scripts/analytics_report.py`, `scripts/analytics_check.sh`, `data/analytics/SETUP.md`, `reports/analytics_2026-10-22.md`
- Evidence: counts sitemap_submitted_urls=974, sitemap_errors=0


#### Indexing pass: entry pages become linked hubs

847 entry pages had been orphans with 2 links each. They now carry breadcrumbs, related entries, 'appears in' guides, more-from-creator and previous/next, averaging about 17 internal links. Admin, rate and legacy pages are noindex; 55 thin summaries were re-written (3 dropped); 969 URLs re-pinged.

- Evidence: commits `8d298fa`
- Evidence: counts entry_pages=846, avg_internal_links_per_entry=16.8, stub_summaries_reenriched=55, indexnow_repinged=969
- Live: [dejaviewed.dev/e/DIO37tGNHiD](https://dejaviewed.dev/e/DIO37tGNHiD)


#### Monetize layer (all programs pending)

Every tool link now goes through a measured redirect ([/go](https://dejaviewed.dev/go)/&lt;tool&gt;) for 26 tools, so clicks are counted from day one and turning on an affiliate later changes only the redirect target. A footer on every public page offers the free do-it-yourself skill and a done-for-you contact link. The US Federal Trade Commission, the regulator that requires ad disclosures (FTC) disclosure, tip jar, sponsors and prompt-pack links render only once they are set; today 0 affiliates are active.

- Evidence: commits `d669c9c`, `0ef3832`
- Evidence: files `scripts/build_monetize.py`, `data/monetize/affiliates.json`, `data/monetize/config.json`, `data/monetize/README.md`, `data/monetize/affiliates_research.json`, `site/_redirects`
- Evidence: counts go_redirects=26, affiliates_active=0, tools_researched=62, footer_cta_pages=961
- Live: [dejaviewed.dev/go/runway](https://dejaviewed.dev/go/runway) · [dejaviewed.dev/go/diy](https://dejaviewed.dev/go/diy) · [dejaviewed.dev/go/service](https://dejaviewed.dev/go/service)


#### Real 404 page and 'In short' answer blocks

Missing URLs now get a real 404 page that suggests the nearest entry or guide. Every guide opens with a short direct-answer paragraph, also published as the article abstract for search and AI answer engines.

- Evidence: commits `e09e639`
- Evidence: files `site/404.html`
- Evidence: counts guides_with_answer_block=63
- Live: [dejaviewed.dev/this-does-not-exist](https://dejaviewed.dev/this-does-not-exist) (404) · [dejaviewed.dev/guides/gemini-cli](https://dejaviewed.dev/guides/gemini-cli)


### 2026-10-23 (4 items)

#### Full SEO audits (technical + content gaps)

A read-only technical audit (25 findings, Lighthouse speed scores, link graph) and a content/niche gap analysis (8 pillars, a 20-item build list, an affiliate-versus-catalog mismatch check) were committed. Waves 2 and 3 below executed the top items.

- Evidence: commits `7e70f49`
- Evidence: files `data/seo/audit_2026-10-22.json`, `data/seo/content_gaps_2026-10-22.json`
- Evidence: counts technical_findings=25, content_build_list=20, build_list_done=10


#### Wave 2 technical: crawlable, fast, clean URLs

Guide bodies are now rendered to HTML at build time instead of in the browser, so crawlers see the full text and links (780 to 3,043 crawlable links, one main page heading (H1) each). Every internal link uses a clean URL (16,486 '.html' links to 0 outside the legacy folder), a static footer nav and 18 collection hub pages put every page within 2 clicks of home, and a [/method](https://dejaviewed.dev/method) page names Victor as the author. Entry pages got video/creative-work structured data and 846 share cards; sitemap dates reflect real content changes; Lighthouse mobile speed rose to 100 (home) and 93 (catalog).

- Evidence: commits `8eaa7f8`, `f4c3e8c`
- Evidence: files `scripts/build_guides.py`, `scripts/normalize_links.py`, `scripts/serve.py`, `site/method.html`, `site/collections/`, `site/og/e/`, `data/seo/content_hashes.json`, `site/_headers`, `site/fonts/`
- Evidence: counts crawlable_guide_links_before=780, crawlable_guide_links_after=3043, html_links_before=16486, html_links_after=0, collection_hubs=18, entry_share_cards=846
- Live: [dejaviewed.dev/method](https://dejaviewed.dev/method) · [dejaviewed.dev/collections/](https://dejaviewed.dev/collections/) · [dejaviewed.dev/guides/gemini-cli](https://dejaviewed.dev/guides/gemini-cli)


#### Wave 3 content: tool hubs, comparisons, best-of lists

40 per-tool pages were built from the catalog; 18 with enough evidence (5+ entries, 2+ top-tier, a curated guide) are indexed and 22 thinner ones are noindex. Every editor-take paragraph cites catalog entries. Two dated comparisons (Claude Code vs Codex vs Gemini command-line tool (CLI); AI video generators) and two keep/try/skip best-of lists (Claude Code skills and plugins, 35 items; Model Context Protocol, the plug-in standard that lets AI agents use tools (MCP) servers, 25) went live with sources.

- Evidence: commits `06a92ae`
- Evidence: files `scripts/build_tools.py`, `data/tools/`, `scripts/build_compare.py`, `data/compare/`
- Evidence: counts tool_hubs_indexed=18, tool_hubs_noindex=22, comparisons=2, best_of_lists=2, best_skills_items=35, best_mcp_items=25
- Live: [dejaviewed.dev/tools/](https://dejaviewed.dev/tools/) · [dejaviewed.dev/tools/runway](https://dejaviewed.dev/tools/runway) · [dejaviewed.dev/compare/claude-code-vs-codex-vs-gemini-cli](https://dejaviewed.dev/compare/claude-code-vs-codex-vs-gemini-cli) · [dejaviewed.dev/compare/ai-video-generators](https://dejaviewed.dev/compare/ai-video-generators) · [dejaviewed.dev/best/claude-code-skills-and-plugins](https://dejaviewed.dev/best/claude-code-skills-and-plugins) · [dejaviewed.dev/best/mcp-servers](https://dejaviewed.dev/best/mcp-servers)


#### System-prompt library, key-facts tables, hooks cookbook, CLAUDE.md guide

A [/system-prompts](https://dejaviewed.dev/system-prompts) library lists all 64 prompt systems. Every guide got a key-facts table with a last-verified date. The Claude Code hooks guide became a cookbook of 18 recipes, with all 33 hook events checked against the official docs on Oct 22, and a new guide annotates 8 real public CLAUDE.md files (with its own prompt system, #64).

- Evidence: commits `06a92ae`, `deb7844`
- Evidence: files `site/system-prompts.html`, `data/guides/facts_state.json`, `site/guides/claude-code-hooks-system.html`, `site/guides/claude-md-examples.html`
- Evidence: counts system_prompts=64, guides_with_facts_table=64, hook_recipes=18, hook_events_verified=33, claude_md_examples=8
- Live: [dejaviewed.dev/system-prompts](https://dejaviewed.dev/system-prompts) · [dejaviewed.dev/guides/claude-code-hooks-system](https://dejaviewed.dev/guides/claude-code-hooks-system) · [dejaviewed.dev/guides/claude-md-examples](https://dejaviewed.dev/guides/claude-md-examples)


## 3. What you need to do

**Today** (the 5 highest-leverage items):

1. [ ] Post the first Instagram content kit (10 min per post). 63 kits are finished and 0 are posted.
1. [ ] Affiliate signup: Runway (week 1, priority 1) (10-15 min to apply; 5 min to activate after approval (or hand the link to Fable)). highest affiliate priority score; 57 links already on the site.
1. [ ] Affiliate signup: Higgsfield (week 1, priority 2) (10-15 min to apply; 5 min to activate after approval (or hand the link to Fable)). second-highest priority score; 46 links on the site.
1. [ ] Affiliate signup: ElevenLabs (week 1, priority 3) (10-15 min to apply; 5 min to activate after approval (or hand the link to Fable)). third-highest priority score; easiest approval.
1. [ ] Cloudflare: turn Email Address Obfuscation OFF (2 min). verified still ON in the live home page HTML.

### This week (10)

- [ ] **Affiliate signup: Runway (week 1, priority 1)** `to do`
   - Why: 57 [/go/runway](https://dejaviewed.dev/go/runway) links already on 21 pages; commission: $15 flat per new paid subscriber via unique code, uncapped; followers get 25% off. Honest value: $0-15/month. One paid signup = $15. At ~600 visits/month and 57 links, expect a sale every 1-3 months at best; Instagram posts with the code are the bigger lever.
   - Steps:
   1. Open [https://runway.com/affiliate-program](https://runway.com/affiliate-program) and apply (use the dejaviewed Instagram account as primary channel, dejaviewed.dev as website)
   2. Read the network/program terms page once logged in; tell Fable about any placement rule not listed in placement_rules.
   3. Wait for approval (typically days to 2 weeks).
   4. Copy the tracking link the program gives you (a URL; if Runway only gives a code, use the landing URL it gives with the code, and put the code itself in the Instagram captions).
   5. Open data/monetize/affiliates.json, find the row for this slug, paste the link into affiliate_url, change status from "pending" to "active". Save.
   6. Rebuild the affected pages in this exact order (tool hubs and comparison pages must be rebuilt BEFORE the search-engine optimization (SEO) and monetize passes, otherwise those pages lose their SEO head block).
   7. Run the checks: monetize --check must say 0 files would change; check_links must report 0 broken internal links.
   8. Commit by explicit paths and push to main (Cloudflare Pages deploys automatically). Or skip steps 2-5 and just tell Fable the slug and paste the link into a file Fable can read (never into chat if it contains a personal token).
   9. Verify live: open [https://dejaviewed.dev/go/](https://dejaviewed.dev/go/)&lt;slug&gt; and confirm it lands on the tracked URL; confirm the footer disclosure sentence now appears (it turns on automatically with the first active program).

   ```bash
   cd ~/Desktop/Projects/dejaviewed-plugin
   python3 scripts/build_method.py && python3 scripts/build_tools.py && python3 scripts/build_compare.py && python3 scripts/build_seo.py && python3 scripts/build_monetize.py && python3 scripts/normalize_links.py
   python3 scripts/build_monetize.py --check && python3 scripts/check_links.py --internal
   git add data/monetize/affiliates.json site/_redirects site/ && git commit -m "monetize: activate <slug>" && git push
   ```
   - Time: 10-15 min to apply; 5 min to activate after approval (or hand the link to Fable)
   - Unblocks: Earning on [/go/runway](https://dejaviewed.dev/go/runway); turns on site-wide US Federal Trade Commission, the regulator that requires ad disclosures (FTC) disclosure automatically with the first activation

- [ ] **Affiliate signup: Higgsfield (week 1, priority 2)** `to do`
   - Why: 46 [/go/higgsfield](https://dejaviewed.dev/go/higgsfield) links already on 22 pages; commission: Up to 25% of plan price, recurring up to 12 months (tiered by revenue; older ambassador page said 15%). Honest value: $0-10/month. Up to 25% recurring of a $10-50/month plan = roughly $3-12/month per retained subscriber. Expect 0 signups most months at current traffic; 11 tagged entries + indexed tool hub + video comparison carry the links.
   - Steps:
   1. Open [https://higgsfield.ai/affiliate](https://higgsfield.ai/affiliate) and apply (website: [https://dejaviewed.dev](https://dejaviewed.dev); describe it as a curated, transcribed archive of AI/creative tool posts with guides)
   2. Read the network/program terms page once logged in; tell Fable about any placement rule not listed in placement_rules.
   3. Wait for approval (typically days to 2 weeks).
   4. Copy the tracking link the program gives you (a URL; if Runway only gives a code, use the landing URL it gives with the code, and put the code itself in the Instagram captions).
   5. Open data/monetize/affiliates.json, find the row for this slug, paste the link into affiliate_url, change status from "pending" to "active". Save.
   6. Rebuild the affected pages in this exact order (tool hubs and comparison pages must be rebuilt BEFORE the SEO and monetize passes, otherwise those pages lose their SEO head block).
   7. Run the checks: monetize --check must say 0 files would change; check_links must report 0 broken internal links.
   8. Commit by explicit paths and push to main (Cloudflare Pages deploys automatically). Or skip steps 2-5 and just tell Fable the slug and paste the link into a file Fable can read (never into chat if it contains a personal token).
   9. Verify live: open [https://dejaviewed.dev/go/](https://dejaviewed.dev/go/)&lt;slug&gt; and confirm it lands on the tracked URL; confirm the footer disclosure sentence now appears (it turns on automatically with the first active program).

   ```bash
   cd ~/Desktop/Projects/dejaviewed-plugin
   python3 scripts/build_method.py && python3 scripts/build_tools.py && python3 scripts/build_compare.py && python3 scripts/build_seo.py && python3 scripts/build_monetize.py && python3 scripts/normalize_links.py
   python3 scripts/build_monetize.py --check && python3 scripts/check_links.py --internal
   git add data/monetize/affiliates.json site/_redirects site/ && git commit -m "monetize: activate <slug>" && git push
   ```
   - Time: 10-15 min to apply; 5 min to activate after approval (or hand the link to Fable)
   - Unblocks: Earning on [/go/higgsfield](https://dejaviewed.dev/go/higgsfield); turns on site-wide FTC disclosure automatically with the first activation

- [ ] **Affiliate signup: ElevenLabs (week 1, priority 3)** `to do`
   - Why: 30 [/go/elevenlabs](https://dejaviewed.dev/go/elevenlabs) links already on 10 pages; commission: 22% of payments for 12 months (Starter/Creator/Pro/Scale), 11% on Business, Enterprise excluded. Honest value: $0-5/month. Only 2 catalog entries are tagged ElevenLabs; the 30 links sit in tools lists of 4 guides + 4 deeper pages, not in ElevenLabs-focused content. Low value until content about voice/TTS exists.
   - Steps:
   1. Open [https://elevenlabs.io/affiliates](https://elevenlabs.io/affiliates) and apply (website: [https://dejaviewed.dev](https://dejaviewed.dev); describe it as a curated, transcribed archive of AI/creative tool posts with guides)
   2. Read the network/program terms page once logged in; tell Fable about any placement rule not listed in placement_rules.
   3. Wait for approval (typically days to 2 weeks).
   4. Copy the tracking link the program gives you (a URL; if Runway only gives a code, use the landing URL it gives with the code, and put the code itself in the Instagram captions).
   5. Open data/monetize/affiliates.json, find the row for this slug, paste the link into affiliate_url, change status from "pending" to "active". Save.
   6. Rebuild the affected pages in this exact order (tool hubs and comparison pages must be rebuilt BEFORE the SEO and monetize passes, otherwise those pages lose their SEO head block).
   7. Run the checks: monetize --check must say 0 files would change; check_links must report 0 broken internal links.
   8. Commit by explicit paths and push to main (Cloudflare Pages deploys automatically). Or skip steps 2-5 and just tell Fable the slug and paste the link into a file Fable can read (never into chat if it contains a personal token).
   9. Verify live: open [https://dejaviewed.dev/go/](https://dejaviewed.dev/go/)&lt;slug&gt; and confirm it lands on the tracked URL; confirm the footer disclosure sentence now appears (it turns on automatically with the first active program).

   ```bash
   cd ~/Desktop/Projects/dejaviewed-plugin
   python3 scripts/build_method.py && python3 scripts/build_tools.py && python3 scripts/build_compare.py && python3 scripts/build_seo.py && python3 scripts/build_monetize.py && python3 scripts/normalize_links.py
   python3 scripts/build_monetize.py --check && python3 scripts/check_links.py --internal
   git add data/monetize/affiliates.json site/_redirects site/ && git commit -m "monetize: activate <slug>" && git push
   ```
   - Time: 10-15 min to apply; 5 min to activate after approval (or hand the link to Fable)
   - Unblocks: Earning on [/go/elevenlabs](https://dejaviewed.dev/go/elevenlabs); turns on site-wide FTC disclosure automatically with the first activation

- [ ] **Cloudflare: turn AI Labyrinth OFF** `to do` (status: todo (state unverified from outside; live HTML shows a Cloudflare bot-challenge script, so some bot feature is on))
   - Why: AI Labyrinth feeds decoy pages to AI crawlers it suspects. We WANT AI crawlers (ChatGPT, Claude, Perplexity read us ~400 times/week) and the parked pay-to-crawl idea depends on their traffic.
   - Steps:
   1. Cloudflare dashboard ([https://dash.cloudflare.com](https://dash.cloudflare.com)) -&gt; select account -&gt; click the dejaviewed.dev domain
   2. Left menu: Security -&gt; Bots (newer dashboards: Security -&gt; Settings, filter 'Bot traffic')
   3. Find 'AI Labyrinth' and switch it Off.
   4. If the menu differs, press Ctrl+K (Cmd+K on Mac) in the dashboard and search 'AI Labyrinth'.
   - Time: 2 min
   - Unblocks: Clean AI-crawler data for pay-to-crawl demand signal

- [ ] **Cloudflare: turn Email Address Obfuscation OFF** `to do` (status: todo (verified still ON: live home HTML contains email-decode on 2026-10-23))
   - Why: It injects a render-blocking script (email-decode.min.js) on every page; the Lighthouse audit measured ~720 ms blocking on home. The site has no email addresses to protect.
   - Steps:
   1. Cloudflare dashboard ([https://dash.cloudflare.com](https://dash.cloudflare.com)) -&gt; select account -&gt; click the dejaviewed.dev domain
   2. Left menu: Scrape Shield -&gt; Email Address Obfuscation (newer dashboards: Security -&gt; Settings, or search 'Email Address Obfuscation' with Ctrl+K)
   3. Switch Off.
   4. Check: view-source of [https://dejaviewed.dev/](https://dejaviewed.dev/) no longer contains 'email-decode'.

   ```bash
   curl -s https://dejaviewed.dev/ | grep -c email-decode   # expect 0 after the change (was 1 on 2026-10-23)
   ```
   - Time: 2 min
   - Unblocks: Faster first render on every page

- [ ] **Cloudflare: turn Early Hints ON** `to do` (status: todo (low impact: Early Hints only acts on Link preload headers, and the site currently sends none; Fable can add them to site/_headers))
   - Why: Lets Cloudflare tell browsers to start fetching CSS/fonts before the HTML arrives.
   - Steps:
   1. Cloudflare dashboard ([https://dash.cloudflare.com](https://dash.cloudflare.com)) -&gt; select account -&gt; click the dejaviewed.dev domain
   2. Left menu: Speed -&gt; Optimization -&gt; Content Optimization tab
   3. Find 'Early Hints' and switch On.
   - Time: 1 min
   - Unblocks: Small speed gain

- [ ] **Cloudflare: make sure Rocket Loader is OFF** `to confirm` (status: likely already off (no rocket-loader script in live home HTML on 2026-10-23); confirm)
   - Why: Rocket Loader rewrites script loading and can break the catalog and search scripts.
   - Steps:
   1. Cloudflare dashboard ([https://dash.cloudflare.com](https://dash.cloudflare.com)) -&gt; select account -&gt; click the dejaviewed.dev domain
   2. Left menu: Speed -&gt; Optimization -&gt; Content Optimization tab
   3. Find 'Rocket Loader' and confirm it is Off.
   - Time: 1 min
   - Unblocks: Nothing; safety check

- [ ] **Confirm the two [/method](https://dejaviewed.dev/method) policy promises** `to do`
   - Why: The [/method](https://dejaviewed.dev/method) page (live, linked from every footer and named as publishingPrinciples in the site schema) makes two public commitments in Victor's name. They should be his decision.
   - Steps:
   1. Read [https://dejaviewed.dev/method](https://dejaviewed.dev/method), section on creators and reuse.
   2. Promise 1 (creator removal): "Creators own their posts. Captions, transcripts, images and videos belong to the people who made them. DejaViewed stores them to make the catalog searchable and links every entry to its source. Creators can ask for an entry to be removed through the contact link."
   3. Promise 2 (reuse with link-back): "The curation is ours. Titles, summaries, tiers, tags, guides, deeper dives and prompt systems are DejaViewed's own work. You may use them with a link back to the page you used."
   4. Reply to Fable: keep both / change wording / remove. Also confirm the affiliate sentence: "Whether a tool appears, and how its posts are tiered, is decided before and apart from any affiliate program."
   - Time: 5 min
   - Unblocks: Fable queue item 4b; trust signals for affiliate applications

- [ ] **Post the first Instagram content kit** `to do` (status: todo (0 of 63 posted))
   - Why: 63 kits are ready and 0 are posted. One a day covers about two months; the weekly analytics report can then compare guide traffic before/after each post.
   - Steps:
   1. Open content/INDEX.md and take #1 of 'Next 7 to post': agent-architecture ('Why Your Agent Sucks: Architecture Patterns That Actually Work').
   2. In content/agent-architecture/: post slide_01.png ... slide_09.png as one Instagram carousel, in order.
   3. Paste caption.md as the caption (credits and hashtags are already in it).
   4. Optional: record a reel from reel_script.md.
   5. Mark it posted: in content/status.json set "agent-architecture": "posted:YYYY-MM-DD" (today's date).
   6. Regenerate the queue (rewrites content/INDEX.md; existing PNGs are kept), then commit status.json and INDEX.md.
   7. Next day: take the new #1.

   ```bash
   cd ~/Desktop/Projects/dejaviewed-plugin
   python3 scripts/content_kit.py --all
   git add content/status.json content/INDEX.md && git commit -m "content: posted agent-architecture" && git push
   ```
   - Time: 10 min per post
   - Unblocks: Runway code-based affiliate value (Instagram channel); traffic to guides

- [ ] **Bing Webmaster: confirm sitemap processed** `partly done` (status: partly done (site added + sitemap submitted Oct 22); check pending)
   - Why: Bing was added manually and its sitemap submitted; Bing feeds ChatGPT search and Copilot, so its index matters more than its share suggests.
   - Steps:
   1. Go to [https://www.bing.com/webmasters](https://www.bing.com/webmasters) and pick dejaviewed.dev.
   2. Left menu: Sitemaps. Confirm [https://dejaviewed.dev/sitemap.xml](https://dejaviewed.dev/sitemap.xml) shows status Success and about 1,007 URLs discovered (it was 974 at first submit).
   3. If it shows an older count, click Resubmit.
   4. Optional: left menu URL Inspection -&gt; [https://dejaviewed.dev/tools/runway](https://dejaviewed.dev/tools/runway) to see if new pages are known.

   ```bash
   python3 scripts/indexnow.py   # re-pings Bing/Yandex/Seznam with all sitemap URLs after any deploy
   ```
   - Time: 3 min
   - Unblocks: Bing/Copilot indexing of the 33 new URLs from wave 3

### Next (weeks 2-6) (8)

- [ ] **Affiliate signup: n8n (week 2, priority 4)** `to do`
   - Why: 25 [/go/n8n](https://dejaviewed.dev/go/n8n) links already on 13 pages; commission: 30% of n8n Cloud revenue for the first 12 months. Honest value: $0-5/month, and nothing actually paid out until EUR 100 accrues (could take a year+ at current traffic). 30% of n8n Cloud revenue for 12 months.
   - Steps:
   1. Open [https://n8n.io/affiliates/](https://n8n.io/affiliates/) and apply (website: [https://dejaviewed.dev](https://dejaviewed.dev); describe it as a curated, transcribed archive of AI/creative tool posts with guides)
   2. Read the network/program terms page once logged in; tell Fable about any placement rule not listed in placement_rules.
   3. Wait for approval (typically days to 2 weeks).
   4. Copy the tracking link the program gives you (a URL; if Runway only gives a code, use the landing URL it gives with the code, and put the code itself in the Instagram captions).
   5. Open data/monetize/affiliates.json, find the row for this slug, paste the link into affiliate_url, change status from "pending" to "active". Save.
   6. Rebuild the affected pages in this exact order (tool hubs and comparison pages must be rebuilt BEFORE the SEO and monetize passes, otherwise those pages lose their SEO head block).
   7. Run the checks: monetize --check must say 0 files would change; check_links must report 0 broken internal links.
   8. Commit by explicit paths and push to main (Cloudflare Pages deploys automatically). Or skip steps 2-5 and just tell Fable the slug and paste the link into a file Fable can read (never into chat if it contains a personal token).
   9. Verify live: open [https://dejaviewed.dev/go/](https://dejaviewed.dev/go/)&lt;slug&gt; and confirm it lands on the tracked URL; confirm the footer disclosure sentence now appears (it turns on automatically with the first active program).

   ```bash
   cd ~/Desktop/Projects/dejaviewed-plugin
   python3 scripts/build_method.py && python3 scripts/build_tools.py && python3 scripts/build_compare.py && python3 scripts/build_seo.py && python3 scripts/build_monetize.py && python3 scripts/normalize_links.py
   python3 scripts/build_monetize.py --check && python3 scripts/check_links.py --internal
   git add data/monetize/affiliates.json site/_redirects site/ && git commit -m "monetize: activate <slug>" && git push
   ```
   - Time: 10-15 min to apply; 5 min to activate after approval (or hand the link to Fable)
   - Unblocks: Earning on [/go/n8n](https://dejaviewed.dev/go/n8n); turns on site-wide FTC disclosure automatically with the first activation

- [ ] **Affiliate signup: Kling (week 2, priority 5)** `to do`
   - Why: 49 [/go/kling](https://dejaviewed.dev/go/kling) links already on 17 pages; commission: unknown (a coupon site claims up to 30%). Honest value: $0-5/month. 49 links but only 3 tagged entries and the hub is noindex; commission unknown (a coupon site claims up to 30%).
   - Steps:
   1. No signup URL on file. signup_url is empty in affiliates.json: log into Impact (after the Higgsfield application creates the account) and search the marketplace for Kling AI.
   2. Read the network/program terms page once logged in; tell Fable about any placement rule not listed in placement_rules.
   3. Wait for approval (typically days to 2 weeks).
   4. Copy the tracking link the program gives you (a URL; if Runway only gives a code, use the landing URL it gives with the code, and put the code itself in the Instagram captions).
   5. Open data/monetize/affiliates.json, find the row for this slug, paste the link into affiliate_url, change status from "pending" to "active". Save.
   6. Rebuild the affected pages in this exact order (tool hubs and comparison pages must be rebuilt BEFORE the SEO and monetize passes, otherwise those pages lose their SEO head block).
   7. Run the checks: monetize --check must say 0 files would change; check_links must report 0 broken internal links.
   8. Commit by explicit paths and push to main (Cloudflare Pages deploys automatically). Or skip steps 2-5 and just tell Fable the slug and paste the link into a file Fable can read (never into chat if it contains a personal token).
   9. Verify live: open [https://dejaviewed.dev/go/](https://dejaviewed.dev/go/)&lt;slug&gt; and confirm it lands on the tracked URL; confirm the footer disclosure sentence now appears (it turns on automatically with the first active program).

   ```bash
   cd ~/Desktop/Projects/dejaviewed-plugin
   python3 scripts/build_method.py && python3 scripts/build_tools.py && python3 scripts/build_compare.py && python3 scripts/build_seo.py && python3 scripts/build_monetize.py && python3 scripts/normalize_links.py
   python3 scripts/build_monetize.py --check && python3 scripts/check_links.py --internal
   git add data/monetize/affiliates.json site/_redirects site/ && git commit -m "monetize: activate <slug>" && git push
   ```
   - Time: 10-15 min to apply; 5 min to activate after approval (or hand the link to Fable)
   - Unblocks: Earning on [/go/kling](https://dejaviewed.dev/go/kling); turns on site-wide FTC disclosure automatically with the first activation

- [ ] **Affiliate signup: Vercel (week 3, priority 6)** `to do`
   - Why: 27 [/go/vercel](https://dejaviewed.dev/go/vercel) links already on 10 pages; commission: Reported $5 per lead + 30% recurring for 6 months (v0 Ambassador Program). Honest value: $0-3/month. 27 links but 3 tagged entries; hub noindex. Reported $5/lead + 30% recurring for 6 months (third-party figures, unverified).
   - Steps:
   1. No signup URL on file. Official affiliate-marketing terms page exists (vercel.com/legal/affiliate-marketing-terms) but no signup URL was found; search Vercel's site/v0 for 'Ambassador'.
   2. Read the network/program terms page once logged in; tell Fable about any placement rule not listed in placement_rules.
   3. Wait for approval (typically days to 2 weeks).
   4. Copy the tracking link the program gives you (a URL; if Runway only gives a code, use the landing URL it gives with the code, and put the code itself in the Instagram captions).
   5. Open data/monetize/affiliates.json, find the row for this slug, paste the link into affiliate_url, change status from "pending" to "active". Save.
   6. Rebuild the affected pages in this exact order (tool hubs and comparison pages must be rebuilt BEFORE the SEO and monetize passes, otherwise those pages lose their SEO head block).
   7. Run the checks: monetize --check must say 0 files would change; check_links must report 0 broken internal links.
   8. Commit by explicit paths and push to main (Cloudflare Pages deploys automatically). Or skip steps 2-5 and just tell Fable the slug and paste the link into a file Fable can read (never into chat if it contains a personal token).
   9. Verify live: open [https://dejaviewed.dev/go/](https://dejaviewed.dev/go/)&lt;slug&gt; and confirm it lands on the tracked URL; confirm the footer disclosure sentence now appears (it turns on automatically with the first active program).

   ```bash
   cd ~/Desktop/Projects/dejaviewed-plugin
   python3 scripts/build_method.py && python3 scripts/build_tools.py && python3 scripts/build_compare.py && python3 scripts/build_seo.py && python3 scripts/build_monetize.py && python3 scripts/normalize_links.py
   python3 scripts/build_monetize.py --check && python3 scripts/check_links.py --internal
   git add data/monetize/affiliates.json site/_redirects site/ && git commit -m "monetize: activate <slug>" && git push
   ```
   - Time: 10-15 min to apply; 5 min to activate after approval (or hand the link to Fable)
   - Unblocks: Earning on [/go/vercel](https://dejaviewed.dev/go/vercel); turns on site-wide FTC disclosure automatically with the first activation

- [ ] **Affiliate signup: TradingView (week 2, priority 7)** `to do`
   - Why: 5 [/go/tradingview](https://dejaviewed.dev/go/tradingview) links already on 5 pages; commission: Flat one-time per new subscriber: monthly $10-$200, annual $60-$400 by plan (older rules page cited 30% recurring). Honest value: $0-5/month. Flat one-time $10-$400 per new subscriber, but only 5 links (4 C-tier entries + a noindex hub). Quant pages are YMYL-adjacent; keep builder framing.
   - Steps:
   1. Open [https://www.tradingview.com/partner-program/](https://www.tradingview.com/partner-program/) and apply (website: [https://dejaviewed.dev](https://dejaviewed.dev); describe it as a curated, transcribed archive of AI/creative tool posts with guides)
   2. Read the network/program terms page once logged in; tell Fable about any placement rule not listed in placement_rules.
   3. Wait for approval (typically days to 2 weeks).
   4. Copy the tracking link the program gives you (a URL; if Runway only gives a code, use the landing URL it gives with the code, and put the code itself in the Instagram captions).
   5. Open data/monetize/affiliates.json, find the row for this slug, paste the link into affiliate_url, change status from "pending" to "active". Save.
   6. Rebuild the affected pages in this exact order (tool hubs and comparison pages must be rebuilt BEFORE the SEO and monetize passes, otherwise those pages lose their SEO head block).
   7. Run the checks: monetize --check must say 0 files would change; check_links must report 0 broken internal links.
   8. Commit by explicit paths and push to main (Cloudflare Pages deploys automatically). Or skip steps 2-5 and just tell Fable the slug and paste the link into a file Fable can read (never into chat if it contains a personal token).
   9. Verify live: open [https://dejaviewed.dev/go/](https://dejaviewed.dev/go/)&lt;slug&gt; and confirm it lands on the tracked URL; confirm the footer disclosure sentence now appears (it turns on automatically with the first active program).

   ```bash
   cd ~/Desktop/Projects/dejaviewed-plugin
   python3 scripts/build_method.py && python3 scripts/build_tools.py && python3 scripts/build_compare.py && python3 scripts/build_seo.py && python3 scripts/build_monetize.py && python3 scripts/normalize_links.py
   python3 scripts/build_monetize.py --check && python3 scripts/check_links.py --internal
   git add data/monetize/affiliates.json site/_redirects site/ && git commit -m "monetize: activate <slug>" && git push
   ```
   - Time: 10-15 min to apply; 5 min to activate after approval (or hand the link to Fable)
   - Unblocks: Earning on [/go/tradingview](https://dejaviewed.dev/go/tradingview); turns on site-wide FTC disclosure automatically with the first activation

- [ ] **Affiliate signup: Descript (week 3, priority 8)** `to do`
   - Why: 2 [/go/descript](https://dejaviewed.dev/go/descript) links already on 2 pages; commission: $25 flat per new subscriber (older terms were 15% recurring year one). Honest value: $0-2/month. $25 flat per new subscriber, but only 2 links on 2 entry pages.
   - Steps:
   1. Open [https://www.descript.com/affiliate](https://www.descript.com/affiliate) and apply (website: [https://dejaviewed.dev](https://dejaviewed.dev); describe it as a curated, transcribed archive of AI/creative tool posts with guides)
   2. Read the network/program terms page once logged in; tell Fable about any placement rule not listed in placement_rules.
   3. Wait for approval (typically days to 2 weeks).
   4. Copy the tracking link the program gives you (a URL; if Runway only gives a code, use the landing URL it gives with the code, and put the code itself in the Instagram captions).
   5. Open data/monetize/affiliates.json, find the row for this slug, paste the link into affiliate_url, change status from "pending" to "active". Save.
   6. Rebuild the affected pages in this exact order (tool hubs and comparison pages must be rebuilt BEFORE the SEO and monetize passes, otherwise those pages lose their SEO head block).
   7. Run the checks: monetize --check must say 0 files would change; check_links must report 0 broken internal links.
   8. Commit by explicit paths and push to main (Cloudflare Pages deploys automatically). Or skip steps 2-5 and just tell Fable the slug and paste the link into a file Fable can read (never into chat if it contains a personal token).
   9. Verify live: open [https://dejaviewed.dev/go/](https://dejaviewed.dev/go/)&lt;slug&gt; and confirm it lands on the tracked URL; confirm the footer disclosure sentence now appears (it turns on automatically with the first active program).

   ```bash
   cd ~/Desktop/Projects/dejaviewed-plugin
   python3 scripts/build_method.py && python3 scripts/build_tools.py && python3 scripts/build_compare.py && python3 scripts/build_seo.py && python3 scripts/build_monetize.py && python3 scripts/normalize_links.py
   python3 scripts/build_monetize.py --check && python3 scripts/check_links.py --internal
   git add data/monetize/affiliates.json site/_redirects site/ && git commit -m "monetize: activate <slug>" && git push
   ```
   - Time: 10-15 min to apply; 5 min to activate after approval (or hand the link to Fable)
   - Unblocks: Earning on [/go/descript](https://dejaviewed.dev/go/descript); turns on site-wide FTC disclosure automatically with the first activation

- [ ] **Affiliate signup: Manus (week 3, priority 9)** `to do`
   - Why: 5 [/go/manus](https://dejaviewed.dev/go/manus) links already on 5 pages; commission: 10% of referred subscription payments for up to 365 days; followers get 1,000 bonus credits. Honest value: $0/month realistically. 10% for up to 365 days; 5 links; $100 minimum payout.
   - Steps:
   1. Open [https://manus.im/affiliate/terms](https://manus.im/affiliate/terms) and apply (website: [https://dejaviewed.dev](https://dejaviewed.dev); describe it as a curated, transcribed archive of AI/creative tool posts with guides)
   2. Read the network/program terms page once logged in; tell Fable about any placement rule not listed in placement_rules.
   3. Wait for approval (typically days to 2 weeks).
   4. Copy the tracking link the program gives you (a URL; if Runway only gives a code, use the landing URL it gives with the code, and put the code itself in the Instagram captions).
   5. Open data/monetize/affiliates.json, find the row for this slug, paste the link into affiliate_url, change status from "pending" to "active". Save.
   6. Rebuild the affected pages in this exact order (tool hubs and comparison pages must be rebuilt BEFORE the SEO and monetize passes, otherwise those pages lose their SEO head block).
   7. Run the checks: monetize --check must say 0 files would change; check_links must report 0 broken internal links.
   8. Commit by explicit paths and push to main (Cloudflare Pages deploys automatically). Or skip steps 2-5 and just tell Fable the slug and paste the link into a file Fable can read (never into chat if it contains a personal token).
   9. Verify live: open [https://dejaviewed.dev/go/](https://dejaviewed.dev/go/)&lt;slug&gt; and confirm it lands on the tracked URL; confirm the footer disclosure sentence now appears (it turns on automatically with the first active program).

   ```bash
   cd ~/Desktop/Projects/dejaviewed-plugin
   python3 scripts/build_method.py && python3 scripts/build_tools.py && python3 scripts/build_compare.py && python3 scripts/build_seo.py && python3 scripts/build_monetize.py && python3 scripts/normalize_links.py
   python3 scripts/build_monetize.py --check && python3 scripts/check_links.py --internal
   git add data/monetize/affiliates.json site/_redirects site/ && git commit -m "monetize: activate <slug>" && git push
   ```
   - Time: 10-15 min to apply; 5 min to activate after approval (or hand the link to Fable)
   - Unblocks: Earning on [/go/manus](https://dejaviewed.dev/go/manus); turns on site-wide FTC disclosure automatically with the first activation

- [ ] **Affiliate signups weeks 4-6 (low value today)** `deferred`
   - Why: Lovable, Framer, Webflow, Raycast, Coursera, Setapp, RunPod, Vast.ai, Skillshare, Udemy, Amazon, Hostinger, Warp, Perplexity have 0-2 links on the site. Signing up now earns nothing until content genuinely names them; Notion is closed; Blender has no program.
   - Steps:
   1. Skip until a guide or tool hub links them, or follow the week plan in affiliate_timeline.
   2. Recheck Notion's affiliate page around 2027-01-23.
   - Time: 0 now
   - Unblocks: nothing

- [ ] **Decide tip jar / GitHub Sponsors** `to do` (status: todo (tip_jar_url and sponsors_url empty))
   - Why: The footer 'Support this archive' link renders only when a URL is set. Empty = nothing shows (current state).
   - Steps:
   1. Decide yes/no. If yes: create a tip page (Ko-fi, Buy Me a Coffee) and/or enable GitHub Sponsors on the Gabicus account ([https://github.com/sponsors](https://github.com/sponsors)).
   2. Put the public URLs in data/monetize/config.json fields tip_jar_url and/or sponsors_url (both currently empty).
   3. Rebuild the footer and push.

   ```bash
   python3 scripts/build_monetize.py && python3 scripts/normalize_links.py && python3 scripts/build_monetize.py --check
   git add data/monetize/config.json site/ && git commit -m "monetize: tip jar" && git push
   ```
   - Time: 10-30 min (GitHub Sponsors approval can take days)
   - Unblocks: Direct reader support

### Optional (2)

- [ ] **Optional: npx wrangler login** `optional`
   - Why: Gives a fallback deploy path (direct upload to Cloudflare Pages) if the GitHub auto-deploy ever stalls. Not needed for normal work.
   - Steps:
   1. Run the command in a terminal (Claude session: type it with a leading '!').
   2. A browser opens; log in to Cloudflare and click Allow.
   3. Done; Fable can then run wrangler pages deploy if auto-deploy breaks.

   ```bash
   npx wrangler login
   ```
   - Time: 2 min
   - Unblocks: Fallback deploys only

- [ ] **Optional: Gumroad prompt pack** `optional` (status: optional (prompt_pack_url empty))
   - Why: All 64 prompt systems are free on the site; a paid offline bundle (PDF/markdown pack) is the one product we could sell without new content. The [/prompts](https://dejaviewed.dev/prompts) page shows a pack link only when prompt_pack_url is set.
   - Steps:
   1. Decide yes/no and price.
   2. If yes: ask Fable to export the pack bundle; create a Gumroad product ([https://gumroad.com](https://gumroad.com)) and upload it.
   3. Paste the product URL into data/monetize/config.json prompt_pack_url.
   4. Rebuild and push.

   ```bash
   python3 scripts/build_monetize.py && python3 scripts/normalize_links.py
   git add data/monetize/config.json site/ && git commit -m "monetize: prompt pack" && git push
   ```
   - Time: 1-2 h including Fable export
   - Unblocks: A first owned product

### Already done (1)

- [x] **Already done: analytics credentials and search-engine setup** `done`
   - Why: Recorded so nobody repeats it.
   - Steps:
   1. Cloudflare read-only API token saved (credential file exists, mode 600).
   2. Cloudflare Web Analytics on (real-visitor numbers appear in the report).
   3. Google Search Console domain property verified; service account added as Full user; sitemap submitted (974 URLs, 0 errors, last downloaded 2026-10-23 00:43 UTC).
   4. Bing site added and sitemap submitted.
   - Time: 0
   - Unblocks: -

## 4. Affiliate timeline

25 programs, grouped by the week to act. Every program is still pending. Links already sit on the site behind `/go/<slug>` redirects; activating a program swaps in the tracked link.

> Honest money estimate: ~600 human visits/month. Assume 2-4% of visits click any tool link (12-24 outbound clicks/month across ALL tools) and 1-3% of clicks become a paid signup. That is roughly 0.1-0.7 paid signups per month across every program combined, i.e. most months earn $0. Basis: 570 human visits and 760 page views in 28 days, 252 visits in the last 7 days, 0 [/go/](https://dejaviewed.dev/go/) clicks recorded so far.

### After approval: the same steps for every program

1. Copy the tracking link the program gives you (a URL; if Runway only gives a code, use the landing URL it gives with the code, and put the code itself in the Instagram captions).
2. Open data/monetize/affiliates.json, find the row for this slug, paste the link into affiliate_url, change status from "pending" to "active". Save.
3. Rebuild the affected pages in this exact order (tool hubs and comparison pages must be rebuilt BEFORE the search-engine optimization (SEO) and monetize passes, otherwise those pages lose their SEO head block).
4. Run the checks: monetize --check must say 0 files would change; check_links must report 0 broken internal links.
5. Commit by explicit paths and push to main (Cloudflare Pages deploys automatically). Or skip steps 2-5 and just tell Fable the slug and paste the link into a file Fable can read (never into chat if it contains a personal token).
6. Verify live: open [https://dejaviewed.dev/go/](https://dejaviewed.dev/go/)&lt;slug&gt; and confirm it lands on the tracked URL; confirm the footer disclosure sentence now appears (it turns on automatically with the first active program).

```bash
cd ~/Desktop/Projects/dejaviewed-plugin
python3 scripts/build_method.py && python3 scripts/build_tools.py && python3 scripts/build_compare.py && python3 scripts/build_seo.py && python3 scripts/build_monetize.py && python3 scripts/normalize_links.py
python3 scripts/build_monetize.py --check && python3 scripts/check_links.py --internal
git add data/monetize/affiliates.json site/_redirects site/ && git commit -m "monetize: activate <slug>" && git push
```

The order requested in the brief (monetize -&gt; tools -&gt; compare -&gt; normalize_links) would rebuild tool hubs and comparison pages AFTER the SEO pass, stripping their canonical/OG/JSON-LD block (build_tools.py and build_compare.py emit only title/description/canonical and rely on build_seo.py running after them). Corrected order follows rebuild.sh: method -&gt; tools -&gt; compare -&gt; seo -&gt; monetize -&gt; links (build_method.py regenerates the [/method](https://dejaviewed.dev/method) sentence that counts active affiliate links).

### Placement rules that apply to every program

- US Federal Trade Commission, the regulator that requires ad disclosures (FTC) disclosure: inline 'affiliate link' label + footer sentence turn on automatically when status=active; never remove either.
- Links carry rel="sponsored nofollow" when active (automatic).
- No paid ads pointing at affiliate links; no search ads on the brand name or typos; no coupon/cashback/'deal' framing; no unsolicited messages with links (applies site-wide, required explicitly by Higgsfield, Framer, n8n, TradingView).

### Week chart

■ = apply that week then wait for approval (typically days to 2 weeks); ▨ = conditional on content; · = recheck/optional/skip. W7-W8 show only approval spill-over.

| Program | W1 | W2 | W3 | W4 | W5 | W6 | W7 | W8 |
|---|---|---|---|---|---|---|---|---|
| Runway | ■ apply | ■ | ■ |  |  |  |  |  |
| Higgsfield | ■ apply | ■ | ■ |  |  |  |  |  |
| ElevenLabs | ■ apply | ■ | ■ |  |  |  |  |  |
| n8n |  | ■ apply | ■ | ■ |  |  |  |  |
| Kling |  | ■ verify program, then apply | ■ | ■ |  |  |  |  |
| TradingView |  | ■ apply | ■ | ■ |  |  |  |  |
| Vercel |  |  | ■ find signup, then apply | ■ | ■ |  |  |  |
| Descript |  |  | ■ apply | ■ | ■ |  |  |  |
| Manus |  |  | ■ request invite | ■ | ■ |  |  |  |
| Lovable |  |  |  | ▨ apply only if content will name it |  |  |  |  |
| Framer |  |  |  | ▨ defer until content exists |  |  |  |  |
| Webflow |  |  |  | ▨ defer until content exists |  |  |  |  |
| Raycast |  |  |  |  | ▨ defer until content exists |  |  |  |
| Coursera |  |  |  |  | ▨ defer until content exists |  |  |  |
| RunPod |  |  |  |  | · optional: personal referral credits |  |  |  |
| Setapp |  |  |  |  | ▨ defer until content exists |  |  |  |
| Perplexity |  |  |  |  |  | · recheck later |  |  |
| Blender |  |  |  |  |  | · no action (Blender is free) |  |  |
| Notion |  |  |  |  |  | · recheck in 3 months (closed) |  |  |
| Vast.ai |  |  |  |  |  | · optional |  |  |
| Warp |  |  |  |  |  | · skip (not a commission program) |  |  |
| Skillshare |  |  |  |  |  | · defer |  |  |
| Udemy |  |  |  |  |  | · defer |  |  |
| Amazon |  |  |  |  |  | · defer |  |  |
| Hostinger |  |  |  |  |  | · skip for now |  |  |

### Week 1 (3 programs)

| Tool · action | Program / network | Commission | Payout minimum | On site | Expected monthly now | Sign up |
|---|---|---|---|---|---|---|
| **Runway** #1 · apply | creator (direct) / direct (code-based creator program) | $15 flat per new paid subscriber via unique code, uncapped; followers get 25% off | not stated publicly (check dashboard) | 57 links on 21 pages, [/go/runway](https://dejaviewed.dev/go/runway) | $0-15/month. One paid signup = $15. At ~600 visits/month and 57 links, expect a sale every 1-3 months at best; Instagram posts with the code are the bigger lever. | [runway.com/affiliate-program](https://runway.com/affiliate-program) |
| ↳ Runway details | *Requirements:* Aimed at creators with an active social channel (Instagram, TikTok, YouTube, X, Substack); any audience size; 3-month pilot *Approval:* easy: any audience size, active social channel; 3-month pilot. Code-based, social-first. Fits the dejaviewed Instagram account better than the website. Active partners get a free Max plan. Don't confuse with Runway Catalog on Awin (different company). *Cookie:* n/a (code-based). *Confidence:* high. *Tagged entries:* 9 (AABABAABB). *Priority score:* 513. *Pages by section:* compare 1, deeper 5, e 9, guides 5, tools 1. *Pages:* [/compare/ai-video-generators](https://dejaviewed.dev/compare/ai-video-generators), [/deeper/deeper-insight-ai-video-production](https://dejaviewed.dev/deeper/deeper-insight-ai-video-production), [/deeper/deeper-insight-art-market-disruption](https://dejaviewed.dev/deeper/deeper-insight-art-market-disruption), [/deeper/deeper-insight-creative-tech-stack-2026](https://dejaviewed.dev/deeper/deeper-insight-creative-tech-stack-2026), [/deeper/deeper-insight-mediapipe-touchdesigner-pipeline](https://dejaviewed.dev/deeper/deeper-insight-mediapipe-touchdesigner-pipeline), [/deeper/deeper-insight-prompt-architecture](https://dejaviewed.dev/deeper/deeper-insight-prompt-architecture), [/guides/ai-video-production](https://dejaviewed.dev/guides/ai-video-production), [/guides/art-market-disruption](https://dejaviewed.dev/guides/art-market-disruption), [/guides/creative-tech-stack-2026](https://dejaviewed.dev/guides/creative-tech-stack-2026), [/guides/mediapipe-touchdesigner-pipeline](https://dejaviewed.dev/guides/mediapipe-touchdesigner-pipeline), [/guides/prompt-architecture](https://dejaviewed.dev/guides/prompt-architecture), [/tools/runway](https://dejaviewed.dev/tools/runway). *Program rules:* Runway: code-based; the audience discount (25% off) is part of the program, state it plainly if used, never as a 'deal' page.. *Notes:* Code-based, social-first: fits the @ Instagram content kits better than the website. Apply as the Instagram account and list dejaviewed.dev as the second channel. / Active partners get a free Max plan, which has real value if Victor uses Runway. / Don't confuse with 'Runway Catalog' on Awin (a different company). |  |  |  |  |  |
| **Higgsfield** #2 · apply | affiliate (Impact) / Impact | Up to 25% of plan price, recurring up to 12 months (tiered by revenue; older ambassador page said 15%) | not stated publicly (Impact default; check in account) | 46 links on 22 pages, [/go/higgsfield](https://dejaviewed.dev/go/higgsfield) | $0-10/month. Up to 25% recurring of a $10-50/month plan = roughly $3-12/month per retained subscriber. Expect 0 signups most months at current traffic; 11 tagged entries + indexed tool hub + video comparison carry the links. | [higgsfield.ai/affiliate](https://higgsfield.ai/affiliate) |
| ↳ Higgsfield details | *Requirements:* Open to 'anyone with an audience'; application review *Approval:* easy: open to 'anyone with an audience', application review. Terms forbid paid advertising, brand-name bidding, and coupon/cashback sites. Referrals get up to 50% off for 3 hours after landing. *Cookie:* unknown. *Confidence:* high. *Tagged entries:* 11 (BSBSCCCCBAB). *Priority score:* 414. *Pages by section:* compare 1, deeper 4, e 12, guides 4, tools 1. *Pages:* [/compare/ai-video-generators](https://dejaviewed.dev/compare/ai-video-generators), [/deeper/deeper-insight-autonomous-brand-machine](https://dejaviewed.dev/deeper/deeper-insight-autonomous-brand-machine), [/deeper/deeper-insight-claude-mastery](https://dejaviewed.dev/deeper/deeper-insight-claude-mastery), [/deeper/deeper-insight-natural-language-3d](https://dejaviewed.dev/deeper/deeper-insight-natural-language-3d), [/deeper/deeper-insight-one-person-creative-studio](https://dejaviewed.dev/deeper/deeper-insight-one-person-creative-studio), [/guides/autonomous-brand-machine](https://dejaviewed.dev/guides/autonomous-brand-machine), [/guides/claude-mastery](https://dejaviewed.dev/guides/claude-mastery), [/guides/natural-language-3d](https://dejaviewed.dev/guides/natural-language-3d), [/guides/one-person-creative-studio](https://dejaviewed.dev/guides/one-person-creative-studio), [/tools/higgsfield](https://dejaviewed.dev/tools/higgsfield). *Program rules:* Higgsfield terms: no paid advertising, no brand-name bidding, no coupon/cashback sites. / Full network terms (PartnerStack/Impact) were not readable without an account: read them at signup before activating.. *Notes:* Hard bans: no paid ads, no brand-name bidding, no coupon/cashback pages. Our pages comply (no coupon framing). / Referrals get up to 50% off for 3 hours after landing; do not advertise this as a 'deal' (coupon framing ban). |  |  |  |  |  |
| **ElevenLabs** #3 · apply | affiliate (PartnerStack) / PartnerStack | 22% of payments for 12 months (Starter/Creator/Pro/Scale), 11% on Business, Enterprise excluded | $5 | 30 links on 10 pages, [/go/elevenlabs](https://dejaviewed.dev/go/elevenlabs) | $0-5/month. Only 2 catalog entries are tagged ElevenLabs; the 30 links sit in tools lists of 4 guides + 4 deeper pages, not in ElevenLabs-focused content. Low value until content about voice/TTS exists. | [elevenlabs.io/affiliates](https://elevenlabs.io/affiliates) |
| ↳ ElevenLabs details | *Requirements:* Open to creators, publishers, bloggers; join PartnerStack *Approval:* easiest: open to creators, publishers, bloggers via PartnerStack. Commission payable 90 days after referral's first payment; $5 minimum. No placement bans found on public page; check PartnerStack terms. *Cookie:* 90 (third-party, Reditus). *Confidence:* high. *Tagged entries:* 2 (SB). *Priority score:* 270. *Pages by section:* deeper 4, e 2, guides 4. *Pages:* [/deeper/deeper-insight-autonomous-agents-wild](https://dejaviewed.dev/deeper/deeper-insight-autonomous-agents-wild), [/deeper/deeper-insight-claude-harness-pattern](https://dejaviewed.dev/deeper/deeper-insight-claude-harness-pattern), [/deeper/deeper-insight-claude-mastery](https://dejaviewed.dev/deeper/deeper-insight-claude-mastery), [/deeper/deeper-insight-creative-tech-stack-2026](https://dejaviewed.dev/deeper/deeper-insight-creative-tech-stack-2026), [/guides/autonomous-agents-wild](https://dejaviewed.dev/guides/autonomous-agents-wild), [/guides/claude-harness-pattern](https://dejaviewed.dev/guides/claude-harness-pattern), [/guides/claude-mastery](https://dejaviewed.dev/guides/claude-mastery), [/guides/creative-tech-stack-2026](https://dejaviewed.dev/guides/creative-tech-stack-2026). *Program rules:* Full network terms (PartnerStack/Impact) were not readable without an account: read them at signup before activating.. *Notes:* Lowest payout minimum ($5) and easiest approval, which is why it is in week 1 despite thin content. / Commission becomes payable 90 days after the referral's first payment. / PartnerStack terms were unreadable without an account: read them at signup. / Content idea that would raise value: the 'voiceover for reels' item in the content skill's ideas queue would use ElevenLabs genuinely. |  |  |  |  |  |

### Week 2 (3 programs)

| Tool · action | Program / network | Commission | Payout minimum | On site | Expected monthly now | Sign up |
|---|---|---|---|---|---|---|
| **n8n** #4 · apply | affiliate (PartnerStack) / PartnerStack | 30% of n8n Cloud revenue for the first 12 months | EUR 100, PayPal only | 25 links on 13 pages, [/go/n8n](https://dejaviewed.dev/go/n8n) | $0-5/month, and nothing actually paid out until EUR 100 accrues (could take a year+ at current traffic). 30% of n8n Cloud revenue for 12 months. | [n8n.io/affiliates/](https://n8n.io/affiliates/) |
| ↳ n8n details | *Requirements:* Application approval; Cloud plans only (no self-hosted/enterprise) *Approval:* medium: application approval; Cloud plans only. Paid ad campaigns prohibited. PayPal only, EUR 100 minimum. Self-hosted guides earn nothing; link to Cloud signup. *Cookie:* unknown (one directory says 90). *Confidence:* high. *Tagged entries:* 8 (SABCACAB). *Priority score:* 150. *Pages by section:* deeper 2, e 8, guides 2, tools 1. *Pages:* [/deeper/deeper-insight-claude-code-mastery](https://dejaviewed.dev/deeper/deeper-insight-claude-code-mastery), [/deeper/deeper-insight-claude-mastery](https://dejaviewed.dev/deeper/deeper-insight-claude-mastery), [/guides/claude-code-mastery](https://dejaviewed.dev/guides/claude-code-mastery), [/guides/claude-mastery](https://dejaviewed.dev/guides/claude-mastery), [/tools/n8n](https://dejaviewed.dev/tools/n8n). *Program rules:* n8n terms: no paid ad campaigns; link to n8n Cloud signup (self-hosted earns nothing). / Full network terms (PartnerStack/Impact) were not readable without an account: read them at signup before activating.. *Notes:* Self-hosted n8n earns nothing: links must go to n8n Cloud signup. / Paid ad campaigns prohibited. / 8 tagged entries, indexed [/tools/n8n](https://dejaviewed.dev/tools/n8n) hub; content-gap item 12 (n8n Model Context Protocol, the plug-in standard that lets AI agents use tools (MCP) explained) would strengthen it. |  |  |  |  |  |
| **Kling** #5 · verify program, then apply | affiliate (Impact) / Impact (listing exists, terms unverified) | unknown (a coupon site claims up to 30%) | unknown | 49 links on 17 pages, [/go/kling](https://dejaviewed.dev/go/kling) | $0-5/month. 49 links but only 3 tagged entries and the hub is noindex; commission unknown (a coupon site claims up to 30%). | no signup URL on file |
| ↳ Kling details | *Requirements:* unknown *Approval:* unknown: no signup URL on file; must find it inside Impact marketplace. Impact listing exists but terms unverified. Separate Kling Creative Partners Program is application-based for filmmakers/artists. *Cookie:* unknown. *Confidence:* low. *Tagged entries:* 3 (AAB). *Priority score:* 98. *Pages by section:* compare 1, deeper 6, e 3, guides 6, tools 1. *Pages:* [/compare/ai-video-generators](https://dejaviewed.dev/compare/ai-video-generators), [/deeper/deeper-insight-ai-video-production](https://dejaviewed.dev/deeper/deeper-insight-ai-video-production), [/deeper/deeper-insight-art-market-disruption](https://dejaviewed.dev/deeper/deeper-insight-art-market-disruption), [/deeper/deeper-insight-creative-tech-stack-2026](https://dejaviewed.dev/deeper/deeper-insight-creative-tech-stack-2026), [/deeper/deeper-insight-mediapipe-touchdesigner-pipeline](https://dejaviewed.dev/deeper/deeper-insight-mediapipe-touchdesigner-pipeline), [/deeper/deeper-insight-prompt-architecture](https://dejaviewed.dev/deeper/deeper-insight-prompt-architecture), [/deeper/deeper-insight-sketch-to-production](https://dejaviewed.dev/deeper/deeper-insight-sketch-to-production), [/guides/ai-video-production](https://dejaviewed.dev/guides/ai-video-production), [/guides/art-market-disruption](https://dejaviewed.dev/guides/art-market-disruption), [/guides/creative-tech-stack-2026](https://dejaviewed.dev/guides/creative-tech-stack-2026), [/guides/mediapipe-touchdesigner-pipeline](https://dejaviewed.dev/guides/mediapipe-touchdesigner-pipeline), [/guides/prompt-architecture](https://dejaviewed.dev/guides/prompt-architecture), [/guides/sketch-to-production](https://dejaviewed.dev/guides/sketch-to-production), [/tools/kling](https://dejaviewed.dev/tools/kling). *Program rules:* Full network terms (PartnerStack/Impact) were not readable without an account: read them at signup before activating.. *Notes:* signup_url is empty in affiliates.json: log into Impact (after the Higgsfield application creates the account) and search the marketplace for Kling AI. / Separate 'Kling Creative Partners Program' is for filmmakers/artists, not a publisher affiliate. / Fact on site: Kling 4.0 shipped 2026-10-15 (verified Oct 22). |  |  |  |  |  |
| **TradingView** #7 · apply | affiliate (direct) / direct | Flat one-time per new subscriber: monthly $10-$200, annual $60-$400 by plan (older rules page cited 30% recurring) | not stated; PayPal monthly; account + traffic verification before first payout | 5 links on 5 pages, [/go/tradingview](https://dejaviewed.dev/go/tradingview) | $0-5/month. Flat one-time $10-$400 per new subscriber, but only 5 links (4 C-tier entries + a noindex hub). Quant pages are YMYL-adjacent; keep builder framing. | [www.tradingview.com/partner-program/](https://www.tradingview.com/partner-program/) |
| ↳ TradingView details | *Requirements:* No minimum audience; account + traffic verification before first payout *Approval:* easy: no minimum audience. Prohibits brand-keyword bidding and unsolicited messaging. Web purchases only. PayPal monthly. *Cookie:* 90 to register + 90 to subscribe (up to 270 days). *Confidence:* high. *Tagged entries:* 4 (CCCC). *Priority score:* 30. *Pages by section:* e 4, tools 1. *Pages:* [/tools/tradingview](https://dejaviewed.dev/tools/tradingview). *Program rules:* TradingView terms: no brand-keyword bidding, no unsolicited messaging; web purchases only.. *Notes:* Bans brand-keyword bidding and unsolicited messaging. / Cookie: 90 days to register + 90 days to subscribe (up to 270 days), the longest window in the list. / Web purchases only. |  |  |  |  |  |

### Week 3 (3 programs)

| Tool · action | Program / network | Commission | Payout minimum | On site | Expected monthly now | Sign up |
|---|---|---|---|---|---|---|
| **Vercel** #6 · find signup, then apply | affiliate (unknown) / unknown (v0 Ambassador Program) | Reported $5 per lead + 30% recurring for 6 months (v0 Ambassador Program) | unknown | 27 links on 10 pages, [/go/vercel](https://dejaviewed.dev/go/vercel) | $0-3/month. 27 links but 3 tagged entries; hub noindex. Reported $5/lead + 30% recurring for 6 months (third-party figures, unverified). | no signup URL on file |
| ↳ Vercel details | *Requirements:* Acceptance at Vercel's discretion; Vercel account in good standing *Approval:* hard: acceptance at Vercel's discretion; signup URL not found. v0 Ambassador program; terms reported, not verified. Official terms page confirms the program exists; rates only from third parties. Signup URL not found. *Cookie:* unknown. *Confidence:* low. *Tagged entries:* 3 (BSA). *Priority score:* 54. *Pages by section:* deeper 3, e 3, guides 3, tools 1. *Pages:* [/deeper/deeper-insight-agent-injection-ci](https://dejaviewed.dev/deeper/deeper-insight-agent-injection-ci), [/deeper/deeper-insight-archive-trained-taste](https://dejaviewed.dev/deeper/deeper-insight-archive-trained-taste), [/deeper/deeper-insight-claude-mastery](https://dejaviewed.dev/deeper/deeper-insight-claude-mastery), [/guides/agent-injection-ci](https://dejaviewed.dev/guides/agent-injection-ci), [/guides/archive-trained-taste](https://dejaviewed.dev/guides/archive-trained-taste), [/guides/claude-mastery](https://dejaviewed.dev/guides/claude-mastery), [/tools/vercel](https://dejaviewed.dev/tools/vercel). *Notes:* Official affiliate-marketing terms page exists (vercel.com/legal/affiliate-marketing-terms) but no signup URL was found; search Vercel's site/v0 for 'Ambassador'. |  |  |  |  |  |
| **Descript** #8 · apply | affiliate (PartnerStack) / PartnerStack | $25 flat per new subscriber (older terms were 15% recurring year one) | unknown (PartnerStack default) | 2 links on 2 pages, [/go/descript](https://dejaviewed.dev/go/descript) | $0-2/month. $25 flat per new subscriber, but only 2 links on 2 entry pages. | [www.descript.com/affiliate](https://www.descript.com/affiliate) |
| ↳ Descript details | *Requirements:* Application with platform/audience info; approval ~1 week; no minimum sales *Approval:* medium: application with platform/audience info; approval ~1 week; no minimum sales. Program migrating to PartnerStack; existing affiliates must reapply. *Cookie:* unknown (sources say 30 or 90). *Confidence:* high. *Tagged entries:* 2 (AC). *Priority score:* 8. *Pages by section:* e 2. *Program rules:* Full network terms (PartnerStack/Impact) were not readable without an account: read them at signup before activating.. *Notes:* Program is migrating to PartnerStack; existing affiliates must reapply. |  |  |  |  |  |
| **Manus** #9 · request invite | affiliate (other) / Tapfiliate | 10% of referred subscription payments for up to 365 days; followers get 1,000 bonus credits | $100, PayPal | 5 links on 5 pages, [/go/manus](https://dejaviewed.dev/go/manus) | $0/month realistically. 10% for up to 365 days; 5 links; $100 minimum payout. | [manus.im/affiliate/terms](https://manus.im/affiliate/terms) |
| ↳ Manus details | *Requirements:* Invitation-only *Approval:* hard: invitation-only. Runs on Tapfiliate. $100 PayPal minimum. Enterprise and add-ons excluded. *Cookie:* unknown. *Confidence:* high. *Tagged entries:* 4 (BCCC). *Priority score:* 5. *Pages by section:* e 4, tools 1. *Pages:* [/tools/manus](https://dejaviewed.dev/tools/manus). *Notes:* Invitation-only per research; the signup URL is the terms page. Followers get 1,000 bonus credits. |  |  |  |  |  |

### Week 4 (3 programs)

| Tool · action | Program / network | Commission | Payout minimum | On site | Expected monthly now | Sign up |
|---|---|---|---|---|---|---|
| **Lovable** #11 · apply only if content will name it | affiliate (Impact) / Impact | Up to $100 per first-time subscriber, tiered bonuses (docs page separately mentions 20% of first 12 payments) | unknown (Impact default) | 0 links on 0 pages, [/go/lovable](https://dejaviewed.dev/go/lovable) | $0/month today: 0 links on site. Up to $100 per first-time subscriber (official pages disagree on structure). | [lovable.dev/affiliates](https://lovable.dev/affiliates) |
| ↳ Lovable details | *Requirements:* Application approval on Impact *Approval:* medium: application approval on Impact. Two official pages disagree on structure; confirm in Impact. *Cookie:* unknown. *Confidence:* medium. *Tagged entries:* 0 (-). *Priority score:* 0. *Pages by section:* -. *Program rules:* Full network terms (PartnerStack/Impact) were not readable without an account: read them at signup before activating.. *Notes:* Not tagged on any catalog entry. Building pages just to fit an affiliate would be thin affiliation under Google's spam policy (content-gap caveat). |  |  |  |  |  |
| **Framer** #12 · defer until content exists | affiliate (other) / other (tracking via Dub; Stripe payout) | 50% of subscription payments for first 12 months | $200 | 0 links on 0 pages, [/go/framer](https://dejaviewed.dev/go/framer) | $0/month today: 0 links. 50% for 12 months, 90-day cookie, but $200 minimum payout. | [www.framer.com/legal/affiliates](https://www.framer.com/legal/affiliates) |
| ↳ Framer details | *Requirements:* Age 16+; follow link-placement rules *Approval:* easy: age 16+, follow placement rules. Tracking via Dub; Stripe payout, $200 minimum. Bans coupon/cashback sites, Framer-term search bidding, search-ad placement, spam. Existing Framer users don't attribute. *Cookie:* 90. *Confidence:* high. *Tagged entries:* 0 (-). *Priority score:* 0. *Pages by section:* -. *Program rules:* Framer terms: no coupon/cashback sites, no Framer-term search bidding, no search-ad placement, no spam.. *Notes:* Bans coupon/cashback sites, Framer-term search bidding, search-ad placement, spam. / Existing Framer users don't attribute. |  |  |  |  |  |
| **Webflow** #13 · defer until content exists | affiliate (PartnerStack) / PartnerStack | 50% of first Site/Workspace subscription for up to 12 months (higher tiers add 10-15% renewal bonus) | unknown (PartnerStack default) | 0 links on 0 pages, [/go/webflow](https://dejaviewed.dev/go/webflow) | $0/month today: 0 links, 0 tagged entries. | [affiliates.webflow.com](https://affiliates.webflow.com) |
| ↳ Webflow details | *Requirements:* For bloggers/educators/creators; review 1-2 weeks; can't also be a Certified Partner *Approval:* medium: review 1-2 weeks; can't also be a Certified Partner. No commissions on client referrals or self-purchases. *Cookie:* 90 (third-party). *Confidence:* high. *Tagged entries:* 0 (-). *Priority score:* 0. *Pages by section:* -. *Program rules:* Full network terms (PartnerStack/Impact) were not readable without an account: read them at signup before activating.. *Notes:* No commissions on client referrals or self-purchases. Matters if Victor's done-for-you service ever builds Webflow sites for clients. |  |  |  |  |  |

### Week 5 (4 programs)

| Tool · action | Program / network | Commission | Payout minimum | On site | Expected monthly now | Sign up |
|---|---|---|---|---|---|---|
| **Raycast** #14 · defer until content exists | affiliate (Rewardful) / Rewardful | 30% of payments from referred Raycast Pro users; referees get 10% off | GBP 50 via Wise, 30-day pending | 0 links on 0 pages, [/go/raycast](https://dejaviewed.dev/go/raycast) | $0/month today: 0 links, 0 tagged entries. | [www.raycast.com/blog/affiliate-program](https://www.raycast.com/blog/affiliate-program) |
| ↳ Raycast details | *Requirements:* Anyone with a Raycast account; needs Wise for payout *Approval:* easy: anyone with a Raycast account. Duration not stated. Payout via Wise above GBP 50, 30-day pending. *Cookie:* unknown. *Confidence:* high. *Tagged entries:* 0 (-). *Priority score:* 0. *Pages by section:* -. *Notes:* Referees get 10% off; duration of the 30% commission is not stated. |  |  |  |  |  |
| **Coursera** #15 · defer until content exists | affiliate (Impact) / Impact | 15%-45% on eligible purchases; Coursera Plus pays first month only; degrees excluded | unknown (Impact default) | 0 links on 0 pages, [/go/coursera](https://dejaviewed.dev/go/coursera) | $0/month today: 0 links. 15-45%; Coursera Plus pays first month only. | [www.coursera.org/about/affiliates](https://www.coursera.org/about/affiliates) |
| ↳ Coursera details | *Requirements:* Free to join; criteria not listed *Approval:* easy: free to join. Good fit for 'learn X' guide pages. *Cookie:* 30. *Confidence:* high. *Tagged entries:* 0 (-). *Priority score:* 0. *Pages by section:* -. *Program rules:* Full network terms (PartnerStack/Impact) were not readable without an account: read them at signup before activating.. *Notes:* Natural fit for 'learn X' guide pages (quant project ideas, Avellaneda-Stoikov) if a course is genuinely relevant. |  |  |  |  |  |
| **RunPod** #18 · optional: personal referral credits | referral (PartnerStack) / PartnerStack | Referral: 3% of Pod / 5% of Serverless spend for referee's first 6 months, in credits. Affiliate tier: 10% cash after 25 paying referrals. | credits only until 25 paying referrals | 0 links on 0 pages, [/go/runpod](https://dejaviewed.dev/go/runpod) | $0 cash/month. Referral pays 3-5% of the referee's spend in credits for 6 months. | [www.runpod.io/referral-and-affiliate-program](https://www.runpod.io/referral-and-affiliate-program) |
| ↳ RunPod details | *Requirements:* Affiliate tier needs 25 paying referrals first; opting in is permanent *Approval:* easy for referral (credits); affiliate cash tier needs 25 paying referrals, and opting in is permanent. Small site starts on credits-only referral. *Cookie:* unknown. *Confidence:* high. *Tagged entries:* 0 (-). *Priority score:* 0. *Pages by section:* -. *Program rules:* Full network terms (PartnerStack/Impact) were not readable without an account: read them at signup before activating.. *Notes:* Useful only if Victor rents graphics processors (GPUs) himself (credits). |  |  |  |  |  |
| **Setapp** #21 · defer until content exists | affiliate (Impact) / Impact | $25 flat per new paid member (older page said $11.50 per trial) | $10 | 0 links on 0 pages, [/go/setapp](https://dejaviewed.dev/go/setapp) | $0/month today: 0 links. | [setapp.com/affiliate](https://setapp.com/affiliate) |
| ↳ Setapp details | *Requirements:* Free to join *Approval:* easy: free to join. $10 minimum payout. *Cookie:* 45. *Confidence:* medium. *Tagged entries:* 0 (-). *Priority score:* 0. *Pages by section:* -. *Program rules:* Full network terms (PartnerStack/Impact) were not readable without an account: read them at signup before activating.. *Notes:* $25 flat per new paid member (older page said $11.50 per trial). |  |  |  |  |  |

### Week 6 (9 programs)

| Tool · action | Program / network | Commission | Payout minimum | On site | Expected monthly now | Sign up |
|---|---|---|---|---|---|---|
| **Perplexity** #10 · recheck later | referral (other) / other (Comet browser referral) | Comet browser referral paid $2-$20 per install depending on country/date (late 2025); 2026 status unknown | unknown | 2 links on 2 pages, [/go/perplexity](https://dejaviewed.dev/go/perplexity) | $0/month. 2 links on 2 entry pages. | no signup URL on file |
| ↳ Perplexity details | *Requirements:* Personal Perplexity account; limits on referral counts *Approval:* unknown: personal-account referral; 2026 status unknown. Cash referral is for the Comet browser install. No formal affiliate. Publishers' Program is ad revenue share for news outlets, not applicable. *Cookie:* unknown. *Confidence:* low. *Tagged entries:* 2 (CA). *Priority score:* 2. *Pages by section:* e 2. *Notes:* No formal affiliate. Publishers' Program is ad revenue share for news outlets, not applicable. |  |  |  |  |  |
| **Blender** #16 · no action (Blender is free) | affiliate (direct) / Superhive marketplace (per-creator agreements) | Blender itself: none (free, open source). Superhive (formerly Blender Market) add-on marketplace has an affiliate system; rate set per creator, commonly 5-10%. | varies per creator | 90 links on 33 pages, [/go/blender](https://dejaviewed.dev/go/blender) | $0/month. Blender is free and open source; the 90 links (most on site) can never earn. | [superhivemarket.com](https://superhivemarket.com) |
| ↳ Blender details | *Requirements:* Per-creator affiliate agreements on Superhive *Approval:* n/a for Blender itself. Program is Superhive (ex-Blender Market) marketplace, not Blender itself; only link Superhive products, never point Blender pills at it. Only route to monetize Blender content is linking specific paid add-ons on Superhive; rates vary per product. *Cookie:* unknown. *Confidence:* low. *Tagged entries:* 14 (SASBBSACAACSCS). *Priority score:* 0. *Pages by section:* deeper 9, e 14, guides 9, tools 1. *Pages:* [/deeper/deeper-insight-album-as-device](https://dejaviewed.dev/deeper/deeper-insight-album-as-device), [/deeper/deeper-insight-ambient-executive-function](https://dejaviewed.dev/deeper/deeper-insight-ambient-executive-function), [/deeper/deeper-insight-claude-mastery](https://dejaviewed.dev/deeper/deeper-insight-claude-mastery), [/deeper/deeper-insight-creative-tech-stack-2026](https://dejaviewed.dev/deeper/deeper-insight-creative-tech-stack-2026), [/deeper/deeper-insight-mocap-as-reward](https://dejaviewed.dev/deeper/deeper-insight-mocap-as-reward), [/deeper/deeper-insight-natural-language-3d](https://dejaviewed.dev/deeper/deeper-insight-natural-language-3d), [/deeper/deeper-insight-one-dancer-thousand-bodies](https://dejaviewed.dev/deeper/deeper-insight-one-dancer-thousand-bodies), [/deeper/deeper-insight-plotter-loop](https://dejaviewed.dev/deeper/deeper-insight-plotter-loop), [/deeper/deeper-insight-scan-fit-print](https://dejaviewed.dev/deeper/deeper-insight-scan-fit-print), [/guides/album-as-device](https://dejaviewed.dev/guides/album-as-device), [/guides/ambient-executive-function](https://dejaviewed.dev/guides/ambient-executive-function), [/guides/claude-mastery](https://dejaviewed.dev/guides/claude-mastery), [/guides/creative-tech-stack-2026](https://dejaviewed.dev/guides/creative-tech-stack-2026), [/guides/mocap-as-reward](https://dejaviewed.dev/guides/mocap-as-reward), [/guides/natural-language-3d](https://dejaviewed.dev/guides/natural-language-3d), [/guides/one-dancer-thousand-bodies](https://dejaviewed.dev/guides/one-dancer-thousand-bodies), [/guides/plotter-loop](https://dejaviewed.dev/guides/plotter-loop), [/guides/scan-fit-print](https://dejaviewed.dev/guides/scan-fit-print), [/tools/blender](https://dejaviewed.dev/tools/blender). *Program rules:* Never point Blender links at Superhive.. *Notes:* The listed program is Superhive (ex-Blender Market), NOT Blender. Never paste a Superhive link into the Blender row; only link specific paid add-ons from a guide that genuinely uses them. / Blender's 90 links come from 14 tagged entries, 9 guides, 9 deeper pages and the indexed [/tools/blender](https://dejaviewed.dev/tools/blender) hub. |  |  |  |  |  |
| **Notion** #17 · recheck in 3 months (closed) | affiliate (PartnerStack) / PartnerStack | Up to $50 per activated signup + 20% of year-one revenue | n/a | 49 links on 17 pages, [/go/notion](https://dejaviewed.dev/go/notion) | $0/month. 49 links stay as plain measured outbound links. | [www.notion.com/affiliates](https://www.notion.com/affiliates) |
| ↳ Notion details | *Requirements:* CLOSED: not accepting new affiliates (official page) *Approval:* closed: not accepting new affiliates. Closed to new affiliates. Cannot join now. Recheck later. *Cookie:* n/a (180-day upgrade window). *Confidence:* high. *Tagged entries:* 4 (BABA). *Priority score:* 0. *Pages by section:* deeper 6, e 4, guides 6, tools 1. *Pages:* [/deeper/deeper-insight-ambient-executive-function](https://dejaviewed.dev/deeper/deeper-insight-ambient-executive-function), [/deeper/deeper-insight-autonomous-agents-wild](https://dejaviewed.dev/deeper/deeper-insight-autonomous-agents-wild), [/deeper/deeper-insight-claude-harness-pattern](https://dejaviewed.dev/deeper/deeper-insight-claude-harness-pattern), [/deeper/deeper-insight-claude-mastery](https://dejaviewed.dev/deeper/deeper-insight-claude-mastery), [/deeper/deeper-insight-earned-autonomy-router](https://dejaviewed.dev/deeper/deeper-insight-earned-autonomy-router), [/deeper/deeper-insight-prompt-architecture](https://dejaviewed.dev/deeper/deeper-insight-prompt-architecture), [/guides/ambient-executive-function](https://dejaviewed.dev/guides/ambient-executive-function), [/guides/autonomous-agents-wild](https://dejaviewed.dev/guides/autonomous-agents-wild), [/guides/claude-harness-pattern](https://dejaviewed.dev/guides/claude-harness-pattern), [/guides/claude-mastery](https://dejaviewed.dev/guides/claude-mastery), [/guides/earned-autonomy-router](https://dejaviewed.dev/guides/earned-autonomy-router), [/guides/prompt-architecture](https://dejaviewed.dev/guides/prompt-architecture), [/tools/notion](https://dejaviewed.dev/tools/notion). *Program rules:* Full network terms (PartnerStack/Impact) were not readable without an account: read them at signup before activating.. *Notes:* Closed to new affiliates per official page. Keep status pending; [/go/notion](https://dejaviewed.dev/go/notion) still measures clicks, which tells us if it is worth reapplying when it reopens. |  |  |  |  |  |
| **Vast.ai** #19 · optional | referral (direct) / direct | 3% of referee spend for life of their account; 75% cashable | unknown; cash-out via Stripe Connect/PayPal/Wise; 75% cashable | 0 links on 0 pages, [/go/vast-ai](https://dejaviewed.dev/go/vast-ai) | $0/month: 0 links. | [docs.vast.ai/guides/reference/referral-program](https://docs.vast.ai/guides/reference/referral-program) |
| ↳ Vast.ai details | *Requirements:* Use a fresh account that never rented or hosted, or cash-out is blocked *Approval:* easy, but use a fresh account that never rented or hosted, or cash-out is blocked. Cash-out via Stripe Connect, PayPal or Wise. *Cookie:* n/a. *Confidence:* high. *Tagged entries:* 0 (-). *Priority score:* 0. *Pages by section:* -. *Notes:* 3% of referee spend for life of their account. |  |  |  |  |  |
| **Warp** #20 · skip (not a commission program) | referral (direct) / direct (refer-a-friend) | Swag/gift-card tiers ($0 at 1 referral up to ~$100 at 100) | n/a (swag/gift-card tiers) | 0 links on 0 pages, [/go/warp](https://dejaviewed.dev/go/warp) | $0/month. | [docs.warp.dev/support-and-community/community/refer-a-friend/](https://docs.warp.dev/support-and-community/community/refer-a-friend/) |
| ↳ Warp details | *Requirements:* Personal account; referee must log into desktop app *Approval:* easy: personal account. Not a commission program. *Cookie:* . *Confidence:* high. *Tagged entries:* 0 (-). *Priority score:* 0. *Pages by section:* -. *Notes:* Swag tiers from 1 to 100 referrals; not cash. |  |  |  |  |  |
| **Skillshare** #22 · defer | affiliate (Impact) / Impact | 20% of first payment, capped at $34 per new customer (older page said 40%/$67) | unknown (Impact default) | 0 links on 0 pages, [/go/skillshare](https://dejaviewed.dev/go/skillshare) | $0/month: 0 links. 20% of first payment capped at $34; 30-day cookie. | [www.skillshare.com/en/affiliates](https://www.skillshare.com/en/affiliates) |
| ↳ Skillshare details | *Requirements:* At least one channel and audience aligned with brand *Approval:* medium: at least one aligned channel. Rate dropped; verify in Impact. *Cookie:* 30. *Confidence:* medium. *Tagged entries:* 0 (-). *Priority score:* 0. *Pages by section:* -. *Program rules:* Full network terms (PartnerStack/Impact) were not readable without an account: read them at signup before activating.. *Notes:* Rate dropped from 40%/$67; verify in Impact. |  |  |  |  |  |
| **Udemy** #23 · defer | affiliate (Impact) / Impact | 10% baseline; an Involve Asia listing shows 7% after July 2026 | unknown (Impact default) | 0 links on 0 pages, [/go/udemy](https://dejaviewed.dev/go/udemy) | $0/month: 0 links. 10% (7% per one listing), 7-day cookie. | [partnersupport.udemy.com/hc/en-us/articles/360049412813-What-is-the-Commission](https://partnersupport.udemy.com/hc/en-us/articles/360049412813-What-is-the-Commission) |
| ↳ Udemy details | *Requirements:* Application review *Approval:* medium: application review. Short cookie, low rate. *Cookie:* 7. *Confidence:* medium. *Tagged entries:* 0 (-). *Priority score:* 0. *Pages by section:* -. *Program rules:* Full network terms (PartnerStack/Impact) were not readable without an account: read them at signup before activating.. *Notes:* Short cookie, low rate. |  |  |  |  |  |
| **Amazon** #24 · defer | affiliate (direct) / direct (Amazon Associates) | Category rates; physical books ~4.5%, electronics ~1-3% (third-party figures) | unknown; account closes without 3 qualifying sales in 180 days (reported) | 0 links on 0 pages, [/go/amazon](https://dejaviewed.dev/go/amazon) | $0/month: 0 links. Books ~4.5%, electronics 1-3%; 1-day cookie. | [affiliate-program.amazon.com](https://affiliate-program.amazon.com) |
| ↳ Amazon details | *Requirements:* Reported: 3 qualifying sales within 180 days of signup or account closes *Approval:* easy to join, easy to lose. Rates from third-party guides; check Associates fee schedule. Low payout but universal for books/hardware. *Cookie:* 1 (90 if added to cart). *Confidence:* medium. *Tagged entries:* 0 (-). *Priority score:* 0. *Pages by section:* -. *Notes:* Only worth it if guides start linking specific books/hardware (pen plotters, Raspberry Pi, cameras). Joining early starts the 180-day 3-sale clock. |  |  |  |  |  |
| **Hostinger** #25 · skip for now | affiliate (direct) / direct | 40% base, up to 60% by volume, one-time per sale (sources conflict) | $100 PayPal; 3 approved sales reported | 0 links on 0 pages, [/go/hostinger](https://dejaviewed.dev/go/hostinger) | $0/month: 0 links, weak relevance to the catalog. | [www.hostinger.com/affiliates](https://www.hostinger.com/affiliates) |
| ↳ Hostinger details | *Requirements:* Application; $100 PayPal minimum and 3 approved sales reported *Approval:* medium: application. Official terms page not retrieved. Weak relevance to catalog. *Cookie:* 30. *Confidence:* medium. *Tagged entries:* 0 (-). *Priority score:* 0. *Pages by section:* -. *Notes:* 40-60% one-time per sale; sources conflict; official terms not retrieved. |  |  |  |  |  |

### Skipped

- **Polymarket**: Skip: wagering-adjacent, jurisdiction-restricted, US program gated via US Commodity Futures Trading Commission (CFTC) rules. RECOMMEND SKIP. Prediction-market/wagering promotion carries jurisdiction restrictions (offers 'not available in all jurisdictions'), US eligibility is gated through CFTC-filed rules, and promoting it alongside trading content creates gambling-adjacent and FTC risk for a small site.

### /go/ links on the site, by target

| Target | Links |
|---|---|
| [/go/diy](https://dejaviewed.dev/go/diy) | 1011 |
| [/go/service](https://dejaviewed.dev/go/service) | 1011 |
| [/go/blender](https://dejaviewed.dev/go/blender) | 90 |
| [/go/runway](https://dejaviewed.dev/go/runway) | 57 |
| [/go/kling](https://dejaviewed.dev/go/kling) | 49 |
| [/go/notion](https://dejaviewed.dev/go/notion) | 49 |
| [/go/higgsfield](https://dejaviewed.dev/go/higgsfield) | 46 |
| [/go/elevenlabs](https://dejaviewed.dev/go/elevenlabs) | 30 |
| [/go/vercel](https://dejaviewed.dev/go/vercel) | 27 |
| [/go/n8n](https://dejaviewed.dev/go/n8n) | 25 |
| [/go/tradingview](https://dejaviewed.dev/go/tradingview) | 5 |
| [/go/manus](https://dejaviewed.dev/go/manus) | 5 |
| [/go/perplexity](https://dejaviewed.dev/go/perplexity) | 2 |
| [/go/descript](https://dejaviewed.dev/go/descript) | 2 |

## 5. Media campaigns from the archive

14 campaign ideas built from the archive, ranked by expected value divided by effort (H/M/L value, S/M/L effort).

### #1 Kit Drip: one guide a day

- Format: carousel series · effort S · value H · score 3.0
- Premise: Ship the 63 finished, unposted kits daily on Instagram only, each with a hand-written keep/try/skip verdict line. Consistency on one platform is the first step of 'known, loved, trusted'.
- Cadence: 1 per day for 63 days
- Call to action target: Guide page (link in bio and Linktree-style [/start-here](https://dejaviewed.dev/start-here)), which internally links to tool hubs with [/go/](https://dejaviewed.dev/go/) links
- Source assets: content/&lt;slug&gt; x63 (549 slides, captions) · guide 'In short' answers
- Evidence entries: [DYR6m86oBj_](https://dejaviewed.dev/e/DYR6m86oBj_), [DXmbF8lCDOP](https://dejaviewed.dev/e/DXmbF8lCDOP), [DcT15tflt4K](https://dejaviewed.dev/e/DcT15tflt4K)
- First 3 posts:
  1. Claude Code hooks: the triggers that run themselves (claude-code-hooks-system)
  2. Boris Cherny's CLAUDE.md, the canonical template (boris-cherny-claude-md)
  3. The self-improving AI workspace (claude-second-brain; the one kit with video)

### #2 Credit Loop: 'your post anchors this guide'

- Format: carousel series + creator DMs and tags · effort S · value H · score 3.0
- Premise: Every guide is built on named creators' posts. Tag and direct message (DM) the credited creators when their kit goes live, so accounts with large audiences have a flattering reason to reshare.
- Cadence: Rides on the Kit Drip, 1 per day
- Call to action target: The guide that credits them
- Source assets: 64 guides' source entry lists · content kit captions (already carry credits)
- Evidence entries: [DbI0-guRspT](https://dejaviewed.dev/e/DbI0-guRspT), [DZ7dVg_Rqog](https://dejaviewed.dev/e/DZ7dVg_Rqog)
- First 3 posts:
  1. @chase.h.ai's 7 must-install Claude Code repos, tested (n8n-mcp-and-obsidian-skills)
  2. @jens.heitmann's Higgsfield motion-team setup, verdict (autonomous-brand-machine)
  3. @keshavsuki's primer.md pattern in practice (primer-md-pattern)

### #3 Ungated: the answer without 'comment X for the link'

- Format: carousel series · effort S · value H · score 3.0
- Premise: About 28% of the archive (roughly 236 of 846 posts) gates its payload behind 'comment KEYWORD'. Each post takes one viral gated claim and gives the full ungated answer plus a verdict from the guide. This is the brand promise made concrete, and it is polarizing in a useful way.
- Cadence: 2 per week
- Call to action target: [/best/claude-code-skills-and-plugins](https://dejaviewed.dev/best/claude-code-skills-and-plugins) or the matching guide; no comment-gate on our side
- Source assets: gated entries (e.g. [DY7r-CjT0AD](https://dejaviewed.dev/e/DY7r-CjT0AD), [DXKani5jWFi](https://dejaviewed.dev/e/DXKani5jWFi), [DWifd94uEe6](https://dejaviewed.dev/e/DWifd94uEe6)) · matching guides and [/best](https://dejaviewed.dev/best) pages
- Evidence entries: [DY7r-CjT0AD](https://dejaviewed.dev/e/DY7r-CjT0AD), [DXKani5jWFi](https://dejaviewed.dev/e/DXKani5jWFi), [DYR6m86oBj_](https://dejaviewed.dev/e/DYR6m86oBj_), [DcT15tflt4K](https://dejaviewed.dev/e/DcT15tflt4K)
- First 3 posts:
  1. 'Comment SKILL for the hook-spy skill.' Here's the whole method, free.
  2. 'Comment user-generated content (UGC) for the Seedance skill.' What it actually does and whether it's worth it.
  3. 'Comment TEAM for the Higgsfield setup.' The three steps, ungated.

### #4 Pinterest evergreen shelf

- Format: Pinterest pins (tall slides and share cards) · effort S · value M · score 2.0
- Premise: Pinterest is a search engine where 'one pin can send people to your work for years'. 549 tall slides and 846 share cards are already rendered. Write captions as searches and link every pin to its guide or entry.
- Cadence: 5 pins per week
- Call to action target: Guide or entry page
- Source assets: content/*/slides · site/og share cards · guide titles as search phrases
- Evidence entries: [DZsEdvNoFdm](https://dejaviewed.dev/e/DZsEdvNoFdm)
- First 3 posts:
  1. Claude Code hooks examples (hooks guide slide 1)
  2. Best Model Context Protocol, the plug-in standard that lets AI agents use tools (MCP) servers 2026 ([/best/mcp-servers](https://dejaviewed.dev/best/mcp-servers) card)
  3. AI video generator comparison: Kling vs Runway vs Veo ([/compare](https://dejaviewed.dev/compare) card)

### #5 Answer seeding: 'In short' on LinkedIn and Reddit

- Format: thread / text posts · effort S · value M · score 2.0
- Premise: Answer engines cite UGC platforms heavily. Post each guide's 'In short' answer keyword-first on LinkedIn, and as helpful Reddit replies where the question is asked, linking the canonical guide so AI Overviews and ChatGPT find a citable path to the site.
- Cadence: 2 LinkedIn posts + 3 Reddit answers per week
- Call to action target: Guide page
- Source assets: 64 guides' 'In short' + key-facts tables · system-prompt library
- Evidence entries: [DaEH4BJMxRX](https://dejaviewed.dev/e/DaEH4BJMxRX), [Db4DLZIh5a3](https://dejaviewed.dev/e/Db4DLZIh5a3), [DXzst1gxPeK](https://dejaviewed.dev/e/DXzst1gxPeK), [Dd6izTYiln1](https://dejaviewed.dev/e/Dd6izTYiln1)
- First 3 posts:
  1. llms.txt: what it is, and whether answer engines read it (llms-txt-standard)
  2. Claude Code vs Codex vs Gemini command-line tool (CLI) in one table ([/compare](https://dejaviewed.dev/compare))
  3. How to stop CLAUDE.md going stale: the primer.md pattern

### #6 Quiz Saves: did you actually learn what you saved?

- Format: carousel series · effort S · value M · score 2.0
- Premise: A 5-question active-recall quiz per guide, with the answers on the guide. It turns the 'you've saved this before' guilt into comments and site visits.
- Cadence: 1 per week
- Call to action target: Guide page (answers)
- Source assets: 64 guides + prompt systems
- Evidence entries: [Db3u0hAPCHV](https://dejaviewed.dev/e/Db3u0hAPCHV), [DXmbF8lCDOP](https://dejaviewed.dev/e/DXmbF8lCDOP)
- First 3 posts:
  1. 5 questions on Claude Code hooks; answers on the site
  2. Quiz: which Claude Code workflow did Boris Cherny actually recommend?
  3. Polymarket 99c limit orders: 5-question gut check

### #7 Read the fine print: sponsored AI posts vs reality

- Format: carousel series · effort S · value M · score 2.0
- Premise: The archive labels paid partnerships and income claims (e.g. Higgsfield promos, '$14k/month' sites). Frame each post around the claim, not the creator: what the ad says, what the tool does, and what our guide found. This builds trust for our own disclosed affiliate links.
- Cadence: 1 every 2 weeks
- Call to action target: [/method](https://dejaviewed.dev/method) (how we tier) and the relevant tool hub
- Source assets: sponsored/#ad-flagged entries · guides that cover the same tools · Princeton sponsored-pick study entry
- Evidence entries: [DYN0298n2H5](https://dejaviewed.dev/e/DYN0298n2H5), [DcUsVlvpYYu](https://dejaviewed.dev/e/DcUsVlvpYYu), [DdKEdJqF3QD](https://dejaviewed.dev/e/DdKEdJqF3QD), [DYR6m86oBj_](https://dejaviewed.dev/e/DYR6m86oBj_)
- First 3 posts:
  1. 18 of 23 AI assistants push the sponsored option: why we write verdicts first
  2. '$500 3D sites for local businesses': what the sponsored post leaves out
  3. How to spot a paid AI-tool reel in 3 seconds

### #8 System prompt of the week

- Format: carousel series · effort S · value M · score 2.0
- Premise: One prompt from the 64-entry system-prompt library per week, as copy-ready slides that people save.
- Cadence: 1 per week
- Call to action target: [/system-prompts](https://dejaviewed.dev/system-prompts)
- Source assets: [/system-prompts](https://dejaviewed.dev/system-prompts) library · data/compare/system-prompts.json
- Evidence entries: [DXmbF8lCDOP](https://dejaviewed.dev/e/DXmbF8lCDOP), [DcT15tflt4K](https://dejaviewed.dev/e/DcT15tflt4K), [DbJzWBfxPvD](https://dejaviewed.dev/e/DbJzWBfxPvD)
- First 3 posts:
  1. The anti-slop writing prompt we run on every caption
  2. A CLAUDE.md that updates itself after every correction
  3. The 'ask me 20 questions first' prompt

### #9 Hook Lab: 846 AI-creator hooks, decoded

- Format: carousel series + one data page · effort M · value H · score 1.5
- Premise: Extract the first 1-2 sentences of every transcript, cluster them into fill-in-the-blank templates, and publish the hook library. Hooks are what creators save and share, and the dataset is unique to us.
- Cadence: 1 per week, plus the data page once
- Call to action target: New /hooks data page, then the open-source skill repo ('built with DejaViewed')
- Source assets: transcript field of all 846 entries · creator index
- Evidence entries: [DY7r-CjT0AD](https://dejaviewed.dev/e/DY7r-CjT0AD), [DZpveoMRy0b](https://dejaviewed.dev/e/DZpveoMRy0b), [DYNMCnCEXaL](https://dejaviewed.dev/e/DYNMCnCEXaL), [DXmbF8lCDOP](https://dejaviewed.dev/e/DXmbF8lCDOP)
- First 3 posts:
  1. The 7 hook shapes AI-tool creators use most
  2. 'X just killed Y': why it works and when it's a lie
  3. Hooks that gate vs hooks that give: which ones we kept

### #10 Keep/Try/Skip tool reels

- Format: reel series (screen recording + Victor voiceover) · effort M · value H · score 1.5
- Premise: A 30-45s verdict per indexed tool hub, screen-recorded on the hub page itself, voiced by Victor. This is the monetization series because every hub carries [/go/](https://dejaviewed.dev/go/) links.
- Cadence: 2 per week
- Call to action target: [/tools](https://dejaviewed.dev/tools)/&lt;slug&gt; with [/go](https://dejaviewed.dev/go)/&lt;slug&gt;
- Source assets: 18 indexed tool hubs (higgsfield, runway, n8n, veo, cursor, codex...) · editor takes and sourced entries per hub
- Evidence entries: [DWl3Bo6jqX1](https://dejaviewed.dev/e/DWl3Bo6jqX1), [Dba75DDxiqc](https://dejaviewed.dev/e/Dba75DDxiqc), [DYR6m86oBj_](https://dejaviewed.dev/e/DYR6m86oBj_)
- First 3 posts:
  1. n8n: keep (self-hosted, Claude can build flows via n8n-mcp)
  2. Higgsfield: try (great with Claude Code, but read the sponsored-post fine print)
  3. Runway vs Kling for one-person video: our verdict

### #11 Build it live: DejaViewed for your own saves

- Format: YouTube short series + GitHub README video · effort M · value M · score 1.0
- Premise: Show the open-source skill turning a stranger's saves into a site. Frame it as Karpathy's LLM-wiki idea applied to 846 sources, with an interview-style onboarding. This drives the skill repo and is the proof-of-work for the service.
- Cadence: 4-part series, then monthly
- Call to action target: GitHub skill repo, then [/go/service](https://dejaviewed.dev/go/service)
- Source assets: skills/dejaviewed · site as demo · graph pages
- Evidence entries: [DWzPgGhiTcR](https://dejaviewed.dev/e/DWzPgGhiTcR), [Dc-Awvkhdop](https://dejaviewed.dev/e/Dc-Awvkhdop), [DWifd94uEe6](https://dejaviewed.dev/e/DWifd94uEe6), [DXMKa0vEa81](https://dejaviewed.dev/e/DXMKa0vEa81)
- First 3 posts:
  1. I turned 846 Instagram saves into a searchable site (part 1: ingest)
  2. Tiering 846 posts S to C with Claude: what got cut
  3. Your saves, as a knowledge graph

### #12 State of the Saves: monthly data report

- Format: newsletter-style report page + PR pitch + carousel · effort M · value M · score 1.0
- Premise: Monthly stats from the catalog (top tools by mentions, gated share, sponsored share, new tiers) as a citable page that reporters and newsletters can link.
- Cadence: Monthly
- Call to action target: The report page (citable), then hubs
- Source assets: catalog.json stats · tool hub counts · compare pages
- Evidence entries: [DblOuOGxU1A](https://dejaviewed.dev/e/DblOuOGxU1A), [Db4DLZIh5a3](https://dejaviewed.dev/e/Db4DLZIh5a3)
- First 3 posts:
  1. October 2026: the 10 tools AI creators mentioned most
  2. Why 28% of AI how-to posts hide the how-to
  3. Claude Code vs Codex share of voice in the archive

### #13 Done-for-you case study

- Format: carousel + 1gabe.com post + outbound · effort M · value M · score 1.0
- Premise: Turn the site into the service's portfolio piece, then source leads with a JobSpy-style search for knowledge-base and content-repurposing gigs and pitch the packaged skills plus site.
- Cadence: 1 case-study post, then weekly outbound
- Call to action target: [/go/service](https://dejaviewed.dev/go/service)
- Source assets: dejaviewed.dev itself · [/go/service](https://dejaviewed.dev/go/service) · skill repo
- Evidence entries: [DX4VJO6zMzL](https://dejaviewed.dev/e/DX4VJO6zMzL), [DXYSxNLpIAY](https://dejaviewed.dev/e/DXYSxNLpIAY)
- First 3 posts:
  1. What a searchable archive of your saves looks like (before/after)
  2. Who this is for: creators, researchers, agencies
  3. How the build works in 5 days

### #14 AI face-off reels: same prompt, four video models

- Format: reel series · effort L · value M · score 0.67
- Premise: Run one prompt through Kling, Runway, Veo and Higgsfield with camera/lens/mood specified, then post the side-by-side and verdict.
- Cadence: 1 every 2 weeks
- Call to action target: [/compare/ai-video-generators](https://dejaviewed.dev/compare/ai-video-generators) with [/go/](https://dejaviewed.dev/go/) links
- Source assets: [/compare/ai-video-generators](https://dejaviewed.dev/compare/ai-video-generators) · kling/runway/veo/higgsfield hubs
- Evidence entries: [DWBjCwCiVEe](https://dejaviewed.dev/e/DWBjCwCiVEe), [DDFdSEDtKZV](https://dejaviewed.dev/e/DDFdSEDtKZV), [DDIAME6MhzY](https://dejaviewed.dev/e/DDIAME6MhzY)
- First 3 posts:
  1. Same prompt, four AI video models: rainy interrogation, slow zoom
  2. Motion control showdown: Kling Motion Brush vs Runway
  3. Which AI video model handles product shots?

### Quick wins

- [ ] Queue the next 7 kits with the dejaviewed-content skill and post kit #1 today. All 63 kits are unposted in content/status.json. Add one hand-written verdict line per caption ([DcT15tflt4K](https://dejaviewed.dev/e/DcT15tflt4K), [DYR6m86oBj_](https://dejaviewed.dev/e/DYR6m86oBj_)).
- [ ] Tag and DM the credited creators for each of those 7 kits, so the Credit Loop starts with the first post ([DbI0-guRspT](https://dejaviewed.dev/e/DbI0-guRspT)).
- [ ] Rewrite the Instagram (IG) bio, home hero sentence and [/about](https://dejaviewed.dev/about) opener with the 4-sentence plain-English formula ([DZMw4I8oh2m](https://dejaviewed.dev/e/DZMw4I8oh2m)) and the 3-second-feeling test ([DYhEafYxHhw](https://dejaviewed.dev/e/DYhEafYxHhw)).
- [ ] Run a humanizer and StopSlop pass over the 63 kit captions before they go out, and make it a gate in content_kit.py ([DbJzWBfxPvD](https://dejaviewed.dev/e/DbJzWBfxPvD), [DcT15tflt4K](https://dejaviewed.dev/e/DcT15tflt4K)).
- [ ] Add the hook and slide constraints to scripts/content_templates: a 10-word hook cap, 12 words per tip slide, and a save/comment call to action (CTA) on the last slide ([DXmbF8lCDOP](https://dejaviewed.dev/e/DXmbF8lCDOP)).
- [ ] Write a small script that extracts the first 1-2 sentences of all 846 transcripts into hooks.json. This seeds the Hook Lab campaign and improves kit hooks, with no scraping needed ([DY7r-CjT0AD](https://dejaviewed.dev/e/DY7r-CjT0AD), [DZpveoMRy0b](https://dejaviewed.dev/e/DZpveoMRy0b)).
- [ ] Open a Pinterest business account and pin the first 5 slides with search-phrased captions linking to guides ([DZsEdvNoFdm](https://dejaviewed.dev/e/DZsEdvNoFdm)).
- [ ] Post 2 guide 'In short' answers keyword-first on LinkedIn and answer 3 matching Reddit questions with a guide link ([DaEH4BJMxRX](https://dejaviewed.dev/e/DaEH4BJMxRX), [DXzst1gxPeK](https://dejaviewed.dev/e/DXzst1gxPeK)).
- [ ] Record 3 OpenScreen walkthroughs of indexed tool hubs (n8n, higgsfield, runway), voiced by Victor, for the first Keep/Try/Skip reels ([DWl3Bo6jqX1](https://dejaviewed.dev/e/DWl3Bo6jqX1), [Dba75DDxiqc](https://dejaviewed.dev/e/Dba75DDxiqc)).
- [ ] Install n8n-mcp and add Plausible, or another goal-tracking tool, so campaign referrers and [/go/](https://dejaviewed.dev/go/) clicks get attributed before the drip scales ([DUzg0n1jRK-](https://dejaviewed.dev/e/DUzg0n1jRK-), [DY-6VBpEgLS](https://dejaviewed.dev/e/DY-6VBpEgLS)).

## 6. What the archive already knows

Source: site/catalog.json (846 entries: title, summary, takeaways, tools, caption, transcript) + guides, content kits, tool hubs, compare pages, data/monetize

Method: Keyword and domain scoring narrowed 846 entries to about 300 candidates; summaries and transcripts were read manually; only entries with a concrete, usable method were kept. Ranked within group by tier, then specificity.

### a. Content production (14)

| Entry | Tier | Creator | What it teaches | How to apply here | Effort |
|---|---|---|---|---|---|
| [You can turn Claude Code into a full motion design team on @higgsfield.a...](https://dejaviewed.dev/e/DXKFrnQEfEQ)<br>tools: Claude Code, Higgsfield, Playwright MCP, Nano Banana, Seedance 2.0 | S | @jens.heitmann | Connect Claude Code to Higgsfield 'using playwright so it can drive the tools like the marketing studio directly', generate stills/3D/avatars with Nano Banana, then install a Seedance 2.0 skill so Claude 'can architect prompts just like a professional'. | Use for B-roll and cover motion on the 63 content kits (reel_script.md has no visuals yet; only 1 kit has video). Run it from the dejaviewed-content skill as an optional 'render b-roll' step; every rendered clip doubles as a demo for the Higgsfield hub's [/go/higgsfield](https://dejaviewed.dev/go/higgsfield) link. | M |
| [Claude isn’t just for coding anymore. I’ve been using it to run full marketing...](https://dejaviewed.dev/e/DXKani5jWFi)<br>tools: Claude Code, Playwright MCP, Higgsfield, Seedance 2.0 | S | @brodyautomates | Playwright Model Context Protocol, the plug-in standard that lets AI agents use tools (MCP) gives Claude Code browser control, and a skills file teaches it to 'upload reference images, write prompts, pick Seedance 2.0 as the model, and then generate full videos with native audio all on its own'. | Same pipeline as the entry above, second confirmation. Treat the two as one build: a 'kit-to-reel' skill that turns each kit's hook slide into a 5-10s motion intro. Keep human review before posting. | M |
| [MoneyPrinterTurbo — one-topic-in, finished short video out](https://dejaviewed.dev/e/DZYoZbOMoDE)<br>tools: MoneyPrinterTurbo, Claude, Google Colab | A | @franklim.gui | MoneyPrinterTurbo takes a topic, 'writes the script, pulls HD/4K stock footage, adds narration, subtitles and music, and renders vertical or horizontal videos in batches'. Works with Claude/Gemini/DeepSeek, runs locally or in Colab, no watermark. | Feed each kit's reel_script.md in as the script (skip its own scripting) and batch-render rough vertical drafts for all 63 kits. Use them as drafts only: a talking-head or screen recording will beat stock footage for a tool-review account. | M |
| [Six monetizable AI GitHub repos — clipping, Remotion, OpenHands and more](https://dejaviewed.dev/e/Dcj_mRRv5tv)<br>tools: Remotion, AutoClip | A | @raycfu | Six repos, each mapped to a sellable service, including 'AutoClip for auto-cutting highlights from long videos' and 'Remotion for templated programmatic video'. 'Remotion turns repetitive video edits into code templates.' | Remotion fits best: build one React template that turns a kit's slide JSON into an animated 9:16 video with consistent brand motion, rendered for all 63 kits in one batch. AutoClip can cut highlights from any long-form screen recordings later. | M |
| [OpenScreen — free open-source Screen Studio alternative](https://dejaviewed.dev/e/DWl3Bo6jqX1)<br>tools: OpenScreen, Recordly | A | @marc.kaz | OpenScreen is a 'free MIT-licensed screen recorder with auto-zoom on clicks, cursor animations, webcam overlays, any aspect ratio'. The Recordly fork adds native Mac/Windows recording. | Record 30-45s 9:16 walkthroughs of the site itself (search, a tool hub, a [/compare](https://dejaviewed.dev/compare) page). These are the most honest product demos for tool-hub reels, and the openscreen-screen-recorder guide already exists to link back to. | S |
| [Humanizer skill for Claude Code — strip AI tells from your writing](https://dejaviewed.dev/e/DbJzWBfxPvD)<br>tools: Claude Code, humanizer | A | @jens.heitmann | Build a humanizer skill from blader/humanizer (based on Wikipedia's 'Signs of AI writing') plus StoryScope structural tells, and 'enforce it with CLAUDE.md rules or hooks, not just an optional skill'. | Add a de-AI pass to content_kit.py output (captions, slide text) and to guide generation. A hook gate can match the existing rebuild.sh publish gates. | S |
| [StopSlop — a Claude skill file that strips AI writing tells](https://dejaviewed.dev/e/DcT15tflt4K)<br>tools: Claude, StopSlop | A | @therobertta | StopSlop bans filler phrases, throat-clearing openers, emphasis crutches and adverbs, but 'deleting tells doesn't add opinion; take a stance yourself. Use AI for the first 80%, edit the last 20% by hand'. | Pair with the humanizer pass, and have Victor add one hand-written opinion line per caption. That line is the keep/try/skip verdict the brand needs anyway. | S |
| [AI weekly roundup — Pocket TTS, Hermes Skills Hub, Kimi K3 in pure C](https://dejaviewed.dev/e/Db0vxQexdJI)<br>tools: Pocket TTS | A | @drcintas | Kyutai Pocket text-to-speech (TTS): '100M-param local voice cloning, 6x real-time', one-command setup. | Free local fallback for voicing drafts in Victor's own cloned voice when he can't record. Disclose cloned voice, and use the real voice for flagship posts given the retention claim in [Dba75DDxiqc](https://dejaviewed.dev/e/Dba75DDxiqc). | S |
| [Claude Code content system — seven skills from research to repurposing](https://dejaviewed.dev/e/DWifd94uEe6)<br>tools: Claude Code, NotebookLM, YouTube | B | @chase.h.ai | A creator pipeline split into seven Claude Code skills: source research, a YT-pipeline skill that 'offloads analysis to NotebookLM', competitive ideation, hook/outline/title scripting and repurposing into blogs, X threads and 60-120s shorts; 'distill long videos into new short-form scripts rather than clipping'. Credited with 90 pieces in 30 days. | Map this onto the existing dejaviewed-content skill: it already has scripting and kits, so add the missing 'repurpose' stage (each guide becomes carousel + X thread + LinkedIn post + short). The guides are the long-form source to distill. | M |
| [Higgsfield Cinema Studio — directing AI video with camera and lens controls](https://dejaviewed.dev/e/DWBjCwCiVEe)<br>tools: Higgsfield Cinema Studio | B | @nateherkai | Higgsfield Cinema Studio: 'specify camera move, lens and mood explicitly in video prompts' (e.g. rainy interrogation, slow zoom). Use AI scenes for previs and ad prototypes. | Put a camera/lens/mood field in the reel b-roll prompt template so generated intros look consistent across the series. | S |
| [Ad Deconstruction with GPT-4o — reverse-engineer a winning ad, regenerate for your brand](https://dejaviewed.dev/e/DIO37tGNHiD)<br>tools: ChatGPT | B | @thesocialalpha_ | Upload a competitor ad and have ChatGPT break down 'psychology, imagery, typography, color and composition' before adapting it. 'Copy the reasoning behind an ad rather than the ad itself.' | Before freezing the kit slide template, run the breakdown on the 5 best-performing carousels from creators in the corpus (@chase.h.ai, @nateherkai). Then adapt the reasoning, not the look. | S |
| [Self-study pipeline — saved links to AI-generated study guides and quizzes](https://dejaviewed.dev/e/Db3u0hAPCHV)<br>tools: NotebookLM | B | @angus.sewell | Log every save in one table, then have an agent 'group recent saves by topic and generate study guides and quizzes', optionally via NotebookLM, for active recall. | DejaViewed already is that table. Generate a 5-question quiz carousel per guide ('Did you actually learn what you saved?'), which brings comment engagement and a reason to visit the guide. | S |
| [#ai #claude #marketing #videoediting #vibecoding](https://dejaviewed.dev/e/DXMKa0vEa81)<br>tools: Claude | B | @eddynthings | A Claude video-editing skill was given only 'create an attractive summary for our memory community repo on GitHub'. It 'went and searched the blogs, the repo for information' and produced intro, cards, animation and closing. | Point the same kind of skill at the dejaviewed GitHub repo for a launch/promo video of the open-source skill. The specific skill isn't named, so look for it before building one. | M |
| [Faceless horror channel pipeline — AI agent sourcing, human voice and edit](https://dejaviewed.dev/e/Dba75DDxiqc)<br>tools: Descript | C | @angus.sewell | Argues against fully-AI faceless channels: 'AI voiceover hurts retention, real narrators win'. Use agents for sourcing and admin, keep the creative voice human. | Victor should voice the reels himself, and keep AI for b-roll and captions. Content kits already script the words; recording 63 voiceovers is about one afternoon of batching. | S |

### b. Social growth tactics (9)

| Entry | Tier | Creator | What it teaches | How to apply here | Effort |
|---|---|---|---|---|---|
| [If you are also tryna rip a few influencer deals comment “in](https://dejaviewed.dev/e/DZpveoMRy0b)<br>tools: Claude, database | A | @angus.sewell | For user-generated content (UGC)/affiliate content: 'scrape and transcribe every single one of their posts, first three sentences and the overall concept and structure of the video, make sure you get the analytics too', put it in a database and have the agent propose concepts. The hard part is getting a good video made. | Same method on our own corpus: the database exists, so add a 'first three sentences + structure' column to the catalog build and use it when writing kit hooks. | S |
| [You can make Claude Code your Social Media Manager that studies your cha...](https://dejaviewed.dev/e/DVmw74XEbk7)<br>tools: Claude Code, Apify MCP | A | @jens.heitmann | Apify MCP plus Claude Code downloads and transcribes all your own posts, identifies 'trends, phrases, and scripts that people connect with and those that they do not', and simulates how new content will land. | Turn this on after about 20 posts are live: weekly scrape of @dejaviewed's own posts and metrics, compared against the hook templates, feeding the next-7 queue. | M |
| [Claude — 1. Prompt for viral content](https://dejaviewed.dev/e/DXmbF8lCDOP)<br>tools: Claude | A | @milamarksonofficial | Seven copy prompts, including: pain point into 'a hook of up to 10 words', a 30s reel structure ('1) Irresistible hook, 2) Short engaging story, 3) call to action (CTA) to comment or save'), carousel tips 'a maximum of 12 words' that are 'impossible not to save', and repurposing one text into 'a 7-second Reels script, a 5-slide carousel, a static post'. | Bake these constraints into scripts/content_templates: 10-word hook cap on slide 1, 12-word cap per tip slide, a save/comment CTA on the last slide, and a 7-second reel variant per kit. | S |
| [There is a free app putting artists work in front of people  — Instagram shows your work to people who already follow...](https://dejaviewed.dev/e/DZsEdvNoFdm)<br>tools: Pinterest | A | @creativeflairhq | Use Pinterest as a search engine: a business account, 'pin your work as tall, high quality images', 'write every caption like a search', 'link every pin back to where people can buy or contact you', and 'five a week beats 50 a day'. One pin can send people to your work for years. | The 549 kit slides and 846 share cards are tall, finished images. Pin 5 a week with search-phrased captions ('Claude Code hooks examples') linking to the guide or entry. This is the most evergreen, lowest-effort distribution in the corpus. | S |
| [The data is all there for you to 10x your growth](https://dejaviewed.dev/e/DY7r-CjT0AD)<br>tools: Claude, Apify (for view counts) | B | @tenfoldmarc | A 'spy' skill pulls a competitor's last 50 posts, finds outliers ('posts that have five times their average views'), transcribes the hook and on-screen text, and turns each into a fill-in-the-blank hook template with why it works. | DejaViewed already has 846 transcripts from the exact niche. Run the hook-extraction half offline now: first 1-2 sentences per transcript into hooks.json, clustered into templates. Add the outlier half once view counts are scraped (the catalog has no view data). | S |
| [it wasn’t some magic funnel, secret strategy, or cute little — it came down to 3 things:](https://dejaviewed.dev/e/DYR6m86oBj_) | B | @losilver_ | Be 'known, loved, trusted, in that order'. Known means consistency ('every single day across one platform to start'); 'master one, then move to the rest'. Loved means being polarizing ('loved or hated, never tolerated'). Trusted means being genuinely the best at the thing. | Pick Instagram only, post daily from the 63-kit backlog, and give every post an explicit keep/try/skip verdict. The neutral 'here's a tool' framing is what this warns against. Delay TikTok and YouTube until Instagram (IG) cadence holds for 30 days. | S |
| [NotebookLM channel analysis — reverse-engineer a YouTube channel's hooks](https://dejaviewed.dev/e/DYNMCnCEXaL)<br>tools: NotebookLM | B | @nateherkai | Load 10-15 videos from a channel you admire into NotebookLM and ask why they work: topics, hooks, patterns. Build the next video from one idea and 'test one idea at a time, then scale what works'. | Load the transcripts of the 3 most-saved creators in the corpus (@chase.h.ai, @nateherkai, @angus.sewell) as NotebookLM sources to pick the reel format for tool-hub reviews. | S |
| [Per the usual if you comment “content” I’ll send you the gui](https://dejaviewed.dev/e/DZc2ci4xCp6)<br>tools: Claude, Instagram | B | @angus.sewell | An autonomous carousel agent: a skill that 'scrapes and saves viral instagram posts', one that 'rewrites them as instagram carousel script', one that generates the carousel and one that posts on a schedule. The creator's own verdict: 'your best chance of this working is copying other people'. | DejaViewed has steps 1-3 already (saves, kits, slides). Add scheduling, but keep a human approval step. The differentiator is curation and verdicts, not volume, which is also the warning in this post. | M |
| [Clipper outreach agent — Roy Lee's pay-per-view clipping army, automated](https://dejaviewed.dev/e/DdZz4DfNzNW) | B | @angus.sewell | Automates the Cluely clipping tactic: an agent finds accounts your audience follows, scrapes suggested clipping accounts, pulls bio emails and pitches them with 'raw footage plus proven examples'. Clippers are paid per view. | Later-stage, once there is long-form footage (live builds). Payouts run about $1-1.50 per thousand views per [DadfHYrkmr7](https://dejaviewed.dev/e/DadfHYrkmr7), so it needs budget. Park until a YouTube long-form exists. | L |

### c. Automation pipelines (8)

| Entry | Tier | Creator | What it teaches | How to apply here | Effort |
|---|---|---|---|---|---|
| [7 must-install Claude Code repos — Obsidian Skills, n8n-MCP, Superpowers](https://dejaviewed.dev/e/DUzg0n1jRK-)<br>tools: n8n-mcp, Claude Code, n8n | S | @chase.h.ai | Seven Claude Code repos with links, including czlonkowski/n8n-mcp ('install n8n-MCP for Claude-driven n8n workflows') and nextlevelbuilder/ui-ux-pro-max-skill. | Install n8n-mcp so Claude Code can author the posting and repurposing workflows below instead of hand-building them in the n8n user interface (UI). The n8n tool hub already has [/go/n8n](https://dejaviewed.dev/go/n8n). | S |
| [Jarvis daily brief — Claude with RevenueCat, Buffer, Meta Ads and Gmail MCPs](https://dejaviewed.dev/e/DZVXehQRe3T)<br>tools: Claude, Buffer MCP, Gmail MCP, Meta Ads MCP | S | @chandlerintelligence | A Claude 'Jarvis' with MCP servers for 'RevenueCat, Buffer, Meta Ads and Gmail', custom subagents with their own skills, 'frequently asked questions (FAQs) in markdown' so Claude handles most support email, and the daily brief run as a scheduled routine. | Build a DejaViewed daily brief: Cloudflare path analytics ([/go/](https://dejaviewed.dev/go/) clicks, top pages), the next-7 post queue, and Buffer for scheduling. Add a FAQ.md for service inquiries arriving through [/go/service](https://dejaviewed.dev/go/service). | M |
| [Self-improving startup — Loom transcripts to Claude skills to scheduled tasks](https://dejaviewed.dev/e/DYxDK5ixq07)<br>tools: Loom, Claude, Obsidian | A | @angus.sewell | Do each process by hand and record it on Loom; 'the transcript becomes the skill spec'. Run skills supervised 'until they stop failing, then schedule them'. Skills log their own issues and a fixer skill improves the others. | Record Victor doing one full posting cycle (pick kit, edit caption, post, credit creator, log status) and turn it into the posting skill. Schedule it only after 5 clean supervised runs. | M |
| [n8n AI Automation — self-hosted Zapier with AI agent nodes](https://dejaviewed.dev/e/2b29777c0b5a)<br>tools: n8n, Docker, LinkedIn API | A | @6ab3 | n8n as self-hosted Zapier with AI agent nodes, covering 'AI-powered LinkedIn content pipelines, email summarizers, lead enrichment, content repurposing', with Docker setup, LinkedIn API configuration and example JSON workflows. | Use the LinkedIn pipeline as the template for cross-posting each guide's 'In short' answer to LinkedIn. That platform is one of the UGC sources answer engines cite, per [DaEH4BJMxRX](https://dejaviewed.dev/e/DaEH4BJMxRX). | M |
| [Claude Code Meta ads pipeline — Arcads API, Ads MCP and an Airtable swipe file](https://dejaviewed.dev/e/DcR6KUyPC0n)<br>tools: Claude Code, Meta Ads MCP, Arcads, Airtable | A | @mr.paidsocial | Claude Code launches Meta ads via the Arcads API and Meta Ads MCP, with 'a database of proven ads as reference, not just a brief', '~20 questions about your offer' first, and new ads cloned from an existing ad ID 'so uploads don't break targeting'. | Only for a later paid test boosting the best-performing organic carousel to the [/go/service](https://dejaviewed.dev/go/service) page. Hard budget caps are required, per [Db36X9ZypwK](https://dejaviewed.dev/e/Db36X9ZypwK). Skip until organic has a winner. | L |
| [Karpathy-style LLM knowledge base — Claude Code turns 36 videos into a linked wiki](https://dejaviewed.dev/e/DWzPgGhiTcR)<br>tools: Claude Code, Playwright | A | @nateherkai | Following Karpathy's LLM-knowledge-base post, Claude Code ingested 36 YouTube videos, extracted tools/techniques/skills per source 'so hubs emerge naturally', and kept 'source links in each node so the wiki stays verifiable'. | This describes DejaViewed at 846 sources. Use it as positioning: 'Karpathy's large language model (LLM) wiki, applied to 846 saves, open-source.' That framing makes the live-build and skill-repo posts legible to an audience that already knows the idea. | S |
| [Herk Brain AI OS — local knowledge graph wired into a personal dashboard](https://dejaviewed.dev/e/Dc-Awvkhdop)<br>tools: Claude, Codex | A | @nateherkai | A local-files 'AI OS' whose free GitHub repo 'interviews you and scaffolds the same setup'. The dashboard also surfaces 'YouTube comment trends'. 'An interview-driven setup repo is a good onboarding pattern for personal agents.' | Copy the onboarding: make the open-source dejaviewed skill open with a 5-question interview (platforms, collections, public or private, theme). That lowers the barrier for GitHub visitors and makes a clean demo reel. | M |
| [n8n + Veo 3 — Telegram-triggered AI vlog that auto-posts to YouTube](https://dejaviewed.dev/e/DLypfhGRhKw)<br>tools: n8n, Telegram, Veo 3, YouTube | B | @koen.agi | A Telegram message triggers an n8n flow that generates an eight-part story, renders each part with Veo 3, stitches it and uploads to YouTube. 'Telegram makes a convenient trigger for content pipelines.' | Use the trigger pattern: text '/kit claude-code-hooks-system' to a Telegram bot, and n8n renders the kit (slides plus reel) and drops it in a review queue. That gives one-thumb publishing from the phone. | M |

### d. Search-engine optimization (SEO) and answer-engine optimization (AEO) (6)

| Entry | Tier | Creator | What it teaches | How to apply here | Effort |
|---|---|---|---|---|---|
| [llms.txt — get ChatGPT to recommend your local business](https://dejaviewed.dev/e/DWxmSwTDFk2)<br>tools: Claude Code | A | @brycenwood.ai | A vehicle-wrap shop 'got ChatGPT to recommend' it via an llms.txt file describing business, location and value prop, 'built in 5min with Claude Code'. | llms.txt and llms-full.txt are live already. The remaining step from primer.md is registering in llms.txt directories, and logging agent user-agents against [/llms.txt](https://dejaviewed.dev/llms.txt) to check whether it is used (the llms-txt-standard guide prescribes measuring). | S |
| [Jev keyword triage — score SERP beatability before writing content](https://dejaviewed.dev/e/Dd3ZGNeSvK5)<br>tools: Claude, Jev | A | @olivermerrick___ | Pull the top 10 results per keyword and have a classifier answer literal yes/no questions per result (intent, depth, freshness, site strength). 'Three or more weak top-10 results marks a winnable keyword'. 720 results cost about 4 cents. | Run it before choosing the next tool hubs and comparisons, since 22 hubs are noindex. Promote a noindex hub to indexed only when its keyword has 3 or more weak top-10 results. Search volume needs a separate tool. | M |
| [Agent Reach — open-source skill letting agents read Reddit and X](https://dejaviewed.dev/e/Dd6izTYiln1)<br>tools: Agent Reach, Claude | A | @itstundeanthony | Agent Reach, an open-source skill, gives agents read access to 13 platforms without API costs. The demo shows Claude failing to fetch Reddit and X, then succeeding with comments. | Use it in the question-mining step: have Claude read r/ClaudeAI and related subreddits weekly for recurring questions that a guide already answers, which feeds the weekly question page and the Reddit seeding. | M |
| [Programmatic SEO in an hour a week — answer real questions with ChatGPT](https://dejaviewed.dev/e/DXzst1gxPeK)<br>tools: ChatGPT, findquestions.com | B | @heytony.agency | A weekly loop claimed at 14K visitors and 708 keywords: find a real question on findquestions.com, draft with ChatGPT, human edit, 'add images and three internal links', publish one post per week. | Make 'one question page a week' a standing job: pick a real question in a covered niche, answer it with the matching guide's 'In short' as the lead, and link 3 entries. Pages are server-rendered already, so they index cleanly. | S |
| [AI search citations — why your chatbot cites the 'unlocked web'](https://dejaviewed.dev/e/Db4DLZIh5a3) | B | @wetclaude | High-credibility sites block GPTBot and Common Crawl, so 'AI search reads only what's left', and 'one in six cited sources is AI-written'. AI cites self-ranking listicles. | Keep AI crawlers allowed (primer already says turn AI Labyrinth off). The [/best](https://dejaviewed.dev/best) and [/compare](https://dejaviewed.dev/compare) pages are listicle-shaped, which is the format AI search cites. Make them verifiably sourced (entry links) to beat the AI-written listicles they compete with. | S |
| [AI Overview SEO — seeding social posts that Google and ChatGPT cite](https://dejaviewed.dev/e/DaEH4BJMxRX)<br>tools: LinkedIn, Reddit | C | @edward.builds | A LinkedIn post was cited by Google's AI Overview the same day. 'AI answer engines lean heavily on UGC platforms for citations' (YouTube, Reddit, LinkedIn, X); 'put the target keyword at the start of the post'. | Seed each guide's 'In short' answer as a keyword-first LinkedIn post or Reddit comment linking to the guide, so answer engines find a citable UGC copy that points at the canonical page. The self-assertion gaming shown here is a reason to stay factual. | S |

### e. Newsletter, email and community (3)

| Entry | Tier | Creator | What it teaches | How to apply here | Effort |
|---|---|---|---|---|---|
| [DIY founder PR — agent-scraped journalist requests and tailored pitches](https://dejaviewed.dev/e/DblOuOGxU1A)<br>tools: Claude | B | @angus.sewell | An agent scrapes journalist request sites, pulls each journalist's last ten articles and drafts an angle close to what they already write. 'Short emails get more replies than long pitches'; 'give the model example emails so it doesn't sound like AI'; it is 'a volume game'. | Pitch the dataset angle (for example '28% of 846 AI-tool posts gate their content behind a comment') to AI newsletters and tech reporters. Backlinks from them help search-engine optimization (SEO) and answer-engine trust. | M |
| [Trojan-horse marketplace — co-marketing with adjacent vendors via AI](https://dejaviewed.dev/e/DZ7dVg_Rqog)<br>tools: Email | B | @angus.sewell | A Y Combinator (YC) growth tactic: spin up a marketplace, invite vendors selling to the same customers to be featured, offer generous affiliate splits ('10% to you, 20% to them'), and use the relationship for co-branded webinars and partnerships. 'A directory is a low-friction excuse to open partner conversations.' | The 40 tool hubs are that directory. Email tool makers (n8n, Higgsfield, Runway, Kling) that they are featured with a verdict, and ask for a reshare or an affiliate approval. This doubles as the affiliate-activation outreach for the 25 pending [/go/](https://dejaviewed.dev/go/) programs. | M |
| [DIY media brand — agent-written features and carousels instead of paid press](https://dejaviewed.dev/e/DbI0-guRspT)<br>tools: Instagram DM | C | @angus.sewell | Instead of paying for press features, an agent direct messages (DMs) influencers offering features, rewrites their top posts into articles, then turns articles into Instagram carousels and pitches collabs. 'Repurpose one strong post into article plus carousel.' | DejaViewed already features creators: 64 guides credit specific posts. DM or tag each credited creator when their guide's kit goes live ('your post anchors this guide'). Reshares from accounts like @chase.h.ai or @nateherkai are the fastest borrowed audience available. | S |

### f. Monetization (4)

| Entry | Tier | Creator | What it teaches | How to apply here | Effort |
|---|---|---|---|---|---|
| [Claude — Stop selling software. Sell the finished work.](https://dejaviewed.dev/e/DX4VJO6zMzL)<br>tools: JobSpy MCP, Claude, Gmail | A | @tpadumke | An AI-native service loop: 'JobSpy MCP pulls listings from Indeed, LinkedIn, Google Jobs', Claude scores how automatable they are and writes the proposal, then agents handle the repetitive tasks via a Gmail routine. Claimed '20 clients × $400/mo = $8k monthly recurring revenue (MRR)'. | Lead sourcing for the done-for-you service behind [/go/service](https://dejaviewed.dev/go/service): search for 'knowledge base', 'Notion cleanup', 'content repurposing' contract posts and score fit for a 'turn your saves/bookmarks into a searchable site' offer. The income figure is unverified. | M |
| [Princeton sponsored-ads study — 18 of 23 AI assistants push the paid option](https://dejaviewed.dev/e/DYN0298n2H5) | A | @forgoodcode | A Princeton study: '18 of 23 favored the sponsored pick', GPT-5.1 surfaced it 94% of the time, and a 'serve the customer only' system prompt barely moved it. The creator notes it was a hypothetical setup. | Positioning for the affiliate layer: 'verdicts written before any affiliate deal' plus the existing US Federal Trade Commission, the regulator that requires ad disclosures (FTC) label is a trust claim that AI assistants can't make. Put it on [/about](https://dejaviewed.dev/about) and [/method](https://dejaviewed.dev/method). | S |
| [Agentic OS — Claude Code as engine with Obsidian memory and skill packs](https://dejaviewed.dev/e/DXYSxNLpIAY)<br>tools: Claude Code, Obsidian | B | @chase.h.ai | An 'agentic OS' with Claude Code as engine, Obsidian as memory, skill packs and a dashboard: 'package skills plus a dashboard as a deliverable for clients'. | Define the service product package (SKU) concretely: install the dejaviewed skill on a client's saves, deliver the site plus a skill pack. The public site is the portfolio piece. | M |
| [x402 protocol — pay-per-crawl tolls for AI agents scraping your site](https://dejaviewed.dev/e/DdAT0p1xg94)<br>tools: x402 | B | @alexanderelorenzo | x402 revives HTTP 402 Payment Required so 'a site [can] charge AI agents per request using stablecoin payments', framed as a monetization layer for content consumed by agents. | The selling-to-agents guide already lays out a metered JSON endpoint of the catalog. Primer parks pay-to-crawl, which is right for now. Revisit once logs show agent traffic worth metering. | L |

### g. Design, user experience (UX) and brand (7)

| Entry | Tier | Creator | What it teaches | How to apply here | Effort |
|---|---|---|---|---|---|
| [Artist statement in four sentences — what, why, how, and the takeaway](https://dejaviewed.dev/e/DZMw4I8oh2m) | A | @creativeflairhq | A 4-sentence statement: sentence one says 'what you make in plain English', two says why this subject, three names 'only the process that changes the meaning', four says the takeaway. 'If a stranger cannot picture the work from sentence one, rewrite it.' | Rewrite the IG bio, home hero and [/about](https://dejaviewed.dev/about) with this formula. For example: 'I read 846 AI and creative-tech posts so you don't have to. Every one is tiered, summarized and linked to a guide...' | S |
| [Claude Code website build — CLAUDE.md, frontend-design skill, screenshot loop](https://dejaviewed.dev/e/DW_8FsslNJi)<br>tools: Claude Code, frontend-design skill, Playwright | A | @nateherkai | Claude Code with a CLAUDE.md of design rules, the frontend-design skill, brand assets and a reference site, where the agent screenshots its own work to self-critique. 'A reference site plus your brand assets beats a blank prompt.' | Use for the [/go/service](https://dejaviewed.dev/go/service) landing page and any campaign landing pages: one reference site from awesome-design-md plus a screenshot self-review loop via Playwright. | S |
| [Claude website design stack — Kowalski, Impeccable and taste skills plus MCP](https://dejaviewed.dev/e/DbLuwUVlE9Z)<br>tools: Impeccable, design-motion-principles, Figma MCP, Playwright | A | @nateherkai | Install the Emil Kowalski design and Impeccable skills for spacing/type/motion, add a taste skill, connect Figma MCP and Playwright 'so the agent checks its own render'. | Run the Impeccable critique and polish pass on the kit slide template before batch-posting 63 kits, so the grid looks consistent and premium from day one. | S |
| [Vibe-coded landing page toolkit — seven tools for real design taste](https://dejaviewed.dev/e/DcOs3VwRK0B)<br>tools: 21st.dev, getdesign.md, Impeccable | A | @adam_ha_yes | Landing-page toolkit: 21st.dev components, getdesign.md to borrow design systems, impeccable.style prompts. 'Feed the agent a real design system file instead of make it pretty.' | Source components for the service page and email capture block (none exists yet) from 21st.dev instead of hand-rolling them. | S |
| [Greg Isenberg — how to design stunning AI apps (not vibe-coded ugly)](https://dejaviewed.dev/e/DVbL-pREaBi)<br>tools: Ideogram, Flux, Figma, Google AI Studio | A | @gregisenberg | Six steps against 'AI slop': ugly functional prototype first, then define 'the brand's soul' with a specific prompt like 'calm and analog', a 5-10 image moodboard, a 'visual anchor' that guides every element, and a logo from Ideogram V3 with strong negative prompts. | Pick one visual anchor for the IG grid and reel intros (for example a cassette or archive-drawer motif that fits 'you've saved this before'). Keep it across all 63 kits so the account is recognizable in a feed. | M |
| [Claude — They tell it to build the website. That’s the mistake.](https://dejaviewed.dev/e/DYhEafYxHhw)<br>tools: Claude | B | @textura.us | 'The real prompt is «what should the visitor feel in the three seconds before they read anything»'; 'let a single object own the viewport'; 'delete 80% of what the next guy would leave in'. | Apply to the done-for-you service landing and the home hero: write the 3-second-feeling sentence first, then brief Claude. | S |
| [UX laws cheat sheet — 20 rules to feed Claude as design instructions](https://dejaviewed.dev/e/DcwkX6OyduT)<br>tools: Claude | B | @adam_ha_yes | Encode user experience (UX) laws in a CLAUDE.md-style file: fewer choices per screen, 'respond within 400ms; show progress', progressive disclosure, goal-gradient framing. | Apply the goal-gradient idea to start-here.html ('3 guides to get started') and the service intake form. | S |

### h. Analytics and measurement (4)

| Entry | Tier | Creator | What it teaches | How to apply here | Effort |
|---|---|---|---|---|---|
| [Vibe-coded website prompts — @angus.sewell](https://dejaviewed.dev/e/DVyek2-kbZg)<br>tools: PostHog, Claude | B | @angus.sewell | Have Claude add analytics and an A/B split of your landing page, then use the PostHog connector: 'Claude go tell me where people are leaving my website' and 'which version of my landing page is working'. | Once the service landing exists, A/B two hero variants and ask Claude the drop-off question weekly. The PostHog hub page already exists. | M |
| [Open-Source SaaS Replacements — 10 repos from yt-dlp and Ollama to n8n and Penpot](https://dejaviewed.dev/e/DY-6VBpEgLS)<br>tools: Plausible, Cal.diy, n8n, yt-dlp, Whisper | B | @stics.ai | A self-hosted replacement checklist: yt-dlp, Whisper, 'Plausible Analytics', n8n ('self-hosted removes per-task automation pricing'), Cal.com/Cal.diy. | Plausible gives cookieless pageview, referrer and goal tracking (for example outbound [/go/](https://dejaviewed.dev/go/) clicks) without a consent banner. Cal.diy can be the booking step for the done-for-you service. | S |
| [PostHog reader-drop analytics — AI feedback loop for human writers](https://dejaviewed.dev/e/Dcl1xrTIf5V)<br>tools: PostHog | C | @angus.sewell | Install PostHog on the blog and have an agent analyze 'scroll and read-through data on each article' to find 'where articles lose readers', and iterate every piece. | Guides are long. Scroll-depth per guide shows where readers bail, and tells you which section to cut or to move the [/go/](https://dejaviewed.dev/go/) CTA above. Cloudflare path analytics can't see this today. | M |
| [PostHog interest-segmented landing pages — personalize by visitor behavior](https://dejaviewed.dev/e/DdHJn-ZRpbd)<br>tools: PostHog | C | @angus.sewell | After two weeks of sessions, cluster visitors into interest groups and serve a tailored landing variant. Also: 'animated templates can hurt conversion; measure before shipping looks'. | Later. The useful part now is the warning: measure before adding motion-heavy redesigns to home or catalog, which are already at Lighthouse 93-100. | M |

### Repos and skills (22)

| Name | Repo or source entry | What it does | Use for us | Maturity |
|---|---|---|---|---|
| **MoneyPrinterTurbo** | [https://github.com/harry0703/MoneyPrinterTurbo](https://github.com/harry0703/MoneyPrinterTurbo) (URL from general knowledge; source [/e/DZYoZbOMoDE](https://dejaviewed.dev/e/DZYoZbOMoDE)) | Topic or script in, finished vertical/horizontal short out: stock footage, narration, subtitles, music, batch rendering; local or Colab. | Batch-render rough reel drafts from the 63 kits' reel_script.md. | Described as top-trending on GitHub. Stock-footage output looks generic, so use it for drafts. |
| **Remotion** | [https://github.com/remotion-dev/remotion](https://github.com/remotion-dev/remotion) (source [/e/Dcj_mRRv5tv](https://dejaviewed.dev/e/Dcj_mRRv5tv)) | Programmatic video in React; 'turns repetitive video edits into code templates'. | One branded template that animates kit slides into 9:16 video for every kit. | Mature, widely used. Check the license: companies above a size threshold need a paid license, and a solo operator likely qualifies for free use. |
| **AutoClip** | [/e/Dcj_mRRv5tv](https://dejaviewed.dev/e/Dcj_mRRv5tv) (repo URL not in entry) | Auto-cuts highlights from long videos. | Cut shorts from future live-build recordings. | Only named in the post; verify repo and license before use. |
| **blader/humanizer** | [https://github.com/blader/humanizer](https://github.com/blader/humanizer) (source [/e/DbJzWBfxPvD](https://dejaviewed.dev/e/DbJzWBfxPvD)) | Claude skill that strips AI-writing tells based on Wikipedia's 'Signs of AI writing'. | Gate captions, slide text and guides through a de-AI pass via hook. | Link given in the entry; small skill, easy to vendor. |
| **StopSlop** | [/e/DcT15tflt4K](https://dejaviewed.dev/e/DcT15tflt4K) (repo URL not in entry) | Skill file banning filler, throat-clearing openers, emphasis crutches, adverbs. | Second de-AI pass alongside humanizer. | Creator says it removes most tells but not the missing point of view. |
| **OpenScreen / Recordly** | [https://github.com/siddharthvaddem/openscreen](https://github.com/siddharthvaddem/openscreen) (source [/e/DWl3Bo6jqX1](https://dejaviewed.dev/e/DWl3Bo6jqX1)) | Free MIT Screen Studio alternative: auto-zoom on clicks, cursor animation, webcam overlay, any aspect ratio. | Record site walkthrough reels for tool hubs and comparisons. | MIT. The site already has an openscreen-screen-recorder guide. |
| **czlonkowski/n8n-mcp** | [https://github.com/czlonkowski/n8n-mcp](https://github.com/czlonkowski/n8n-mcp) (source [/e/DUzg0n1jRK](https://dejaviewed.dev/e/DUzg0n1jRK)-) | MCP server letting Claude build and edit n8n workflows. | Have Claude Code author the Telegram-to-render-to-queue and LinkedIn cross-post workflows. | Listed in an S-tier 'must-install' roundup; the site has an n8n-mcp-and-obsidian-skills guide. |
| **n8n** | [https://github.com/n8n-io/n8n](https://github.com/n8n-io/n8n) (sources [/e/2b29777c0b5a](https://dejaviewed.dev/e/2b29777c0b5a), [/e/DY-6VBpEgLS](https://dejaviewed.dev/e/DY-6VBpEgLS), [/e/DLypfhGRhKw](https://dejaviewed.dev/e/DLypfhGRhKw)) | Self-hostable workflow automation with AI agent nodes. | Scheduling, cross-posting, Telegram triggers; also an affiliate ([/go/n8n](https://dejaviewed.dev/go/n8n)). | Mature. The self-hosted license has commercial-use limits; read it before reselling it as part of the service. |
| **Seedance 2.0 / Higgsfield prompt skill** | [/e/DXKani5jWFi](https://dejaviewed.dev/e/DXKani5jWFi), [/e/DXIpm6TjE5M](https://dejaviewed.dev/e/DXIpm6TjE5M), [/e/DXKFrnQEfEQ](https://dejaviewed.dev/e/DXKFrnQEfEQ) (comment-gated GitHub skill) | Teaches Claude Code to write Seedance prompts and drive Higgsfield via Playwright MCP. | Kit-to-reel b-roll; demo content for the Higgsfield hub. | All three posts are Higgsfield promos with a discount CTA. The skill is gated, so expect to write your own. |
| **Apify MCP** | [/e/DVmw74XEbk7](https://dejaviewed.dev/e/DVmw74XEbk7) | Scrapes posts and metrics from almost any social platform for the agent. | Own-account post performance loop; adds view counts for outlier-hook analysis. | Paid usage beyond free tier. Respect platform terms. |
| **Competitor 'spy' hook skill** | [/e/DY7r-CjT0AD](https://dejaviewed.dev/e/DY7r-CjT0AD) (comment-gated) | Pulls last 50 posts, flags 5x-average outliers, transcribes hooks into templates. | The method is reproducible on the corpus's own transcripts without the skill. | Gated; reimplement. |
| **VoltAgent/awesome-design-md** | [https://github.com/VoltAgent/awesome-design-md](https://github.com/VoltAgent/awesome-design-md) (source [/e/DW-ag7St6UM](https://dejaviewed.dev/e/DW-ag7St6UM)) | DESIGN.md files breaking real brands into design systems. | Reference system for the service landing page and slide template. | Already installed locally at ~/Desktop/Projects/claude/awesome-design-md. |
| **Impeccable + design-motion-principles + UI UX Pro Max** | [https://impeccable.style](https://impeccable.style); nextlevelbuilder/ui-ux-pro-max-skill (sources [/e/DXdVUiOjKUv](https://dejaviewed.dev/e/DXdVUiOjKUv), [/e/DbLuwUVlE9Z](https://dejaviewed.dev/e/DbLuwUVlE9Z), [/e/DUzg0n1jRK](https://dejaviewed.dev/e/DUzg0n1jRK)-, [/e/DYIzu9HTz1V](https://dejaviewed.dev/e/DYIzu9HTz1V)) | Design-judgment skills for Claude: critique, polish, motion audit. | Polish the slide template and service page before campaigns start. | Impeccable and design-motion-principles are already installed as skills here. |
| **21st.dev** | [https://21st.dev](https://21st.dev) (sources [/e/18ddc4b68b6c](https://dejaviewed.dev/e/18ddc4b68b6c), [/e/DcOs3VwRK0B](https://dejaviewed.dev/e/DcOs3VwRK0B)) | shadcn/Tailwind component marketplace, usable as an MCP server. | Email-capture block and service-page components. | React components; the site is static HTML, so port the markup and don't add React. |
| **Plausible Analytics** | [https://github.com/plausible/analytics](https://github.com/plausible/analytics) (source [/e/DY-6VBpEgLS](https://dejaviewed.dev/e/DY-6VBpEgLS)) | Cookieless self-hostable web analytics. | Goals for [/go/](https://dejaviewed.dev/go/) clicks and service-page conversions; referrer attribution per campaign. | Mature, Affero General Public License, a share-alike open-source license (AGPL). Hosted plan is paid. |
| **PostHog (MCP/connector)** | [/e/DVyek2-kbZg](https://dejaviewed.dev/e/DVyek2-kbZg), [/e/Dcl1xrTIf5V](https://dejaviewed.dev/e/Dcl1xrTIf5V), [/e/DdHJn-ZRpbd](https://dejaviewed.dev/e/DdHJn-ZRpbd) | Product analytics, A/B tests, session and scroll data, queryable by Claude. | Guide scroll-depth and service-landing A/B tests. | Three of the four PostHog entries are sponsored or #ad. The tool is real, but the framing is promotional. |
| **Kyutai Pocket TTS** | [/e/Db0vxQexdJI](https://dejaviewed.dev/e/Db0vxQexdJI) | 100M-parameter local voice cloning, 6x real-time. | Free draft voiceovers in Victor's voice. | New release per a weekly roundup. Test quality first. |
| **Agent Reach** | [/e/Dd6izTYiln1](https://dejaviewed.dev/e/Dd6izTYiln1) | Skill giving agents read access to Reddit, X and 11 other platforms without paid APIs. | Weekly question mining for programmatic answer pages. | Scraping-based; may break and may conflict with platform terms. |
| **JobSpy MCP** | [/e/DX4VJO6zMzL](https://dejaviewed.dev/e/DX4VJO6zMzL) | Pulls job listings from Indeed, LinkedIn, Google Jobs into Claude. | Lead sourcing for the done-for-you service. | Named in caption only; verify the repo. |
| **Buffer MCP** | [/e/DZVXehQRe3T](https://dejaviewed.dev/e/DZVXehQRe3T) | Lets Claude schedule social posts. | Queue the next-7 kits from the daily brief. | Shown in an S-tier walkthrough; check whether Buffer supports IG carousels on your plan. |
| **Scroll World skill** | [/e/DawRY1kJ_ch](https://dejaviewed.dev/e/DawRY1kJ_ch) | One-shot scroll-animated sites from approved stills turned into video clips. | Optional hero for a campaign landing page. | Burns video credits; the fork adds budget tiers. |
| **llms.txt spec** | [https://llmstxt.org](https://llmstxt.org) (sources [/e/DWxmSwTDFk2](https://dejaviewed.dev/e/DWxmSwTDFk2), guide llms-txt-standard) | Machine-readable site summary for LLMs. | Already shipped; register in directories and measure fetches. | A proposal, not a standard; adoption by answer engines is unproven. |

## 7. Fable's queue

| Id | Item | Scope |
|---|---|---|
| 4a | **Fix the enricher's word-match tool tagger upstream** | Stop 'Cursor' matching mouse pointers, 'Runway' fashion runways, 'Llama' Spanish llamar; build_tools.FALSE_TAGS is only a stopgap list. |
| 4b | **Confirm [/method](https://dejaviewed.dev/method) policy promises with Victor** | Creator removal via contact and reuse with link-back (see victor_todo). |
| 4 | **Weekly Monday analytics report** | python3 scripts/analytics_report.py; track Search Console indexed count (13 'discovered' -&gt; indexed; sitemap now 1007), impressions for the 25 target queries, [/go/](https://dejaviewed.dev/go/) clicks per tool, AI-crawler hits on llms-full.txt (pay-to-crawl demand). |
| 5 | **Off-site discovery** | llms.txt directory registrations, GitHub README links to the site, 1gabe.com cross-link. |
| 6 | **Content build-list items 9 and 12-20** | Token-usage case study, n8n Model Context Protocol, the plug-in standard that lets AI agents use tools (MCP) explained, glossary, creator pages, OpenClaw, Polymarket-bots hub, quant ideas upgrade, MediaPipe x TouchDesigner upgrade, 'new this week' page, image-to-3D test; only after Search Console shows the first wave indexing. |
| 7 | **Gumroad/offline prompt pack** | Only if Victor wants it; set prompt_pack_url. |
| parked | **Pay-to-crawl / dataset-as-asset** | x402 or Cloudflare Pay Per Crawl on [/api/v1](https://dejaviewed.dev/api/v1) and [/dataset](https://dejaviewed.dev/dataset); build only once analytics shows crawler demand on llms-full.txt and [/api/](https://dejaviewed.dev/api/). |
| new | **Early Hints Link headers** | Add Link preload headers for shared.css and self-hosted fonts in site/_headers so the Early Hints toggle does something. |
| older | **Older queue** | Re-tier ai2/ai5/stock2 (~20% S); confirm 3 likely reposts; blind re-rate (Victor); Instagram (IG) data-export reconcile (Victor); embedding clustering; run 3 prompt systems end-to-end and feed failures into SPEC.md. |

## 8. Risks and caveats

25 items from both files; 0 near-duplicates merged.

1. Traffic is small: about 250 real visits per week and 0 Google impressions so far. Every affiliate estimate rounds to $0-15/month in total until search traffic arrives. _[status report]_
2. Indexing lag: the Search Console property is days old; a URL-inspection sample showed 6 of 20 indexed and 13 'discovered, not indexed'. Wave 2/3 pages (33 new URLs) were published late Oct 22; expect weeks before they show impressions. _[status report]_
3. Scaled-content risk: 1,007 sitemap URLs, mostly generated from the catalog. Google's scaled-content policy has no published thresholds; the tool-hub noindex thresholds (5+ entries, 2+ S/A, a curated guide) are practitioner heuristics, not guarantees. _[status report]_
4. Affiliate/catalog mismatch: the highest-commission programs (Lovable, Framer, Webflow, Raycast) have 0 links; building pages to fit them would be thin affiliation under Google's spam policy. The biggest pillar (agentic coding, Claude Code) has no affiliate program at all; its monetization is the done-for-you service and the free skill. _[status report]_
5. Affiliate terms unread: PartnerStack and Impact terms (ElevenLabs, n8n, Webflow, Lovable, Coursera, Skillshare, Setapp, Udemy, Higgsfield, Kling, Descript) were not readable without an account. Read them at signup before activating. _[status report]_
6. Unverified program data: Kling (no signup URL, commission unknown), Vercel (rates third-party only), Perplexity (2026 status unknown), Lovable (two official pages disagree). Research confidence for these is low or medium. _[status report]_
7. Payout minimums vs traffic: n8n EUR 100, Manus $100, Framer $200, Hostinger $100 minimums may take a year or more to reach at current traffic; earned money can sit unpaid. _[status report]_
8. Runway is code-based: a [/go/](https://dejaviewed.dev/go/) redirect may not carry attribution unless Runway also issues a tracked link; the code in Instagram captions is the dependable path. _[status report]_
9. Reputational risk for approvals: the l1b3rt4s jailbreak-repo guide (defensive framing) could worry affiliate reviewers; the content-gap analysis suggests considering noindex. _[status report]_
10. YMYL-adjacent pages: quant and prediction-market guides carry builder framing and no profit claims; TradingView links sit on C-tier entries. Polymarket stays skipped. _[status report]_
11. Analytics noise: bot-score fields are Enterprise-only, so humans vs bots are classified by user agent; [/go/](https://dejaviewed.dev/go/) counts are sampled estimates; Web Analytics shows 290 China (CN) page views (28d) that may be automated. _[status report]_
12. Rebuild-order trap: rebuilding tool hubs or comparison pages after the search-engine optimization (SEO) pass strips their SEO head; always run method -&gt; tools -&gt; compare -&gt; seo -&gt; monetize -&gt; links (as rebuild.sh does). _[status report]_
13. Single-source facts on comparison pages (Gemini command-line tool (CLI) free tier ending 2026-06-18, Sora discontinuation, Kling 4.0 date) were verified Oct 22 and will drift; key-facts tables carry last-verified dates and need a refresh cadence. _[status report]_
14. [/method](https://dejaviewed.dev/method) states live counts ('25 of 26 listed tools' point at official sites, '0 are live affiliate links'). The sentence is generated by scripts/build_method.py, which the brief's activation sequence did not include; the corrected sequence runs it first so the count stays true after each activation. _[status report]_
15. No newsletter or email tactics anywhere in the corpus. Nothing covers list building, lead magnets, Beehiiv/Substack or email cadence, and the site has no email capture (only feed.xml). A growth plan needs an owned channel, and this has to come from outside the archive. _[archive growth scan]_
16. No engagement data. The catalog has no view, like or save counts, so the outlier-hook method ([DY7r-CjT0AD](https://dejaviewed.dev/e/DY7r-CjT0AD)) only works after scraping metrics (Apify, [DVmw74XEbk7](https://dejaviewed.dev/e/DVmw74XEbk7)) or once our own posts have data. _[archive growth scan]_
17. Platform-algorithm claims are anecdotal. The only Instagram growth 'cheat codes' entry ([DXJ19sgjlhT](https://dejaviewed.dev/e/DXJ19sgjlhT)) has an unrelated French transcript and no content. Advice like [DYR6m86oBj_](https://dejaviewed.dev/e/DYR6m86oBj_) is one creator's experience. TikTok and YouTube algorithm mechanics are absent. _[archive growth scan]_
18. Heavy sponsor bias in the video-gen tactics. Many of the Higgsfield/Seedance entries ([DXKFrnQEfEQ](https://dejaviewed.dev/e/DXKFrnQEfEQ), [DXKani5jWFi](https://dejaviewed.dev/e/DXKani5jWFi), [DXIpm6TjE5M](https://dejaviewed.dev/e/DXIpm6TjE5M), [DcUsVlvpYYu](https://dejaviewed.dev/e/DcUsVlvpYYu), [DdKEdJqF3QD](https://dejaviewed.dev/e/DdKEdJqF3QD)) are promos with discount calls to action (CTAs). Income claims ($8k monthly recurring revenue (MRR) in [DX4VJO6zMzL](https://dejaviewed.dev/e/DX4VJO6zMzL), $40K/month in [DXzst1gxPeK](https://dejaviewed.dev/e/DXzst1gxPeK), $30k in [DcR6KUyPC0n](https://dejaviewed.dev/e/DcR6KUyPC0n)) are unverified. _[archive growth scan]_
19. About 28% of entries (roughly 236 of 846 by a caption/transcript regex) gate their payload behind 'comment KEYWORD'. Many recommended repos and skills are unnamed, so they must be found or rebuilt. _[archive growth scan]_
20. Affiliate economics are not in the corpus. All 25 [/go/](https://dejaviewed.dev/go/) programs in data/monetize/affiliates.json are 'pending', and approval terms and commission rates come from data/monetize/affiliates_research.json, not the archive. _[archive growth scan]_
21. Rights and credit. Carousels built from creators' posts need credit and should paraphrase, not re-host their video. The corpus has no guidance on repost rights or Instagram's original-content ranking. _[archive growth scan]_
22. Avoid the black- and grey-hat tactics present in the archive. Expired-domain rebuilds ([DdQD_N6Nhz2](https://dejaviewed.dev/e/DdQD_N6Nhz2)) carry manual-penalty risk, self-assertion AI-Overview gaming ([DaEH4BJMxRX](https://dejaviewed.dev/e/DaEH4BJMxRX)) can backfire, and fully synthetic AI-influencer funnels ([DdXyLUWTJ4Z](https://dejaviewed.dev/e/DdXyLUWTJ4Z), [DboDjfgkVOG](https://dejaviewed.dev/e/DboDjfgkVOG)) are ethically and legally murky. _[archive growth scan]_
23. Automation costs. Since the June 15 change, headless claude -p and Agent software development kit (SDK) runs bill per token outside Pro/Max limits ([DYXWNTERFhZ](https://dejaviewed.dev/e/DYXWNTERFhZ)), so scheduled content agents carry API cost. Video generation burns credits fast ([DawRY1kJ_ch](https://dejaviewed.dev/e/DawRY1kJ_ch), [DYiiwmzpRM7](https://dejaviewed.dev/e/DYiiwmzpRM7)). _[archive growth scan]_
24. Measurement is thin today. The site has Cloudflare path analytics only: no scroll depth, no conversion goals for [/go/service](https://dejaviewed.dev/go/service), and no per-campaign attribution. The analytics entries are mostly sponsored PostHog posts ([DdHJn-ZRpbd](https://dejaviewed.dev/e/DdHJn-ZRpbd), [Dcl1xrTIf5V](https://dejaviewed.dev/e/Dcl1xrTIf5V), [DZGC7HXtr1f](https://dejaviewed.dev/e/DZGC7HXtr1f)). _[archive growth scan]_
25. Paid distribution such as the clipping economy at about $1-1.50 per thousand views ([DadfHYrkmr7](https://dejaviewed.dev/e/DadfHYrkmr7), [DdZz4DfNzNW](https://dejaviewed.dev/e/DdZz4DfNzNW)) and Meta ads agents ([DcR6KUyPC0n](https://dejaviewed.dev/e/DcR6KUyPC0n), [Db36X9ZypwK](https://dejaviewed.dev/e/Db36X9ZypwK)) needs budget and hard spend caps. It is not a fit until organic posts identify a winner. _[archive growth scan]_

## A. Commits in the window (25)

| Hash | Date | Subject |
|---|---|---|
| `deb7844` | 2026-10-22 23:27:42 -0400 | seo: shorter system-prompts description |
| `c8f1bc7` | 2026-10-22 23:26:58 -0400 | primer + skill: SEO review loop (Phase 14d), wave 2/3 state |
| `06a92ae` | 2026-10-22 23:25:34 -0400 | Content wave: 18 indexed tool hubs (+22 noindex) with sourced editor takes and /go/ buttons, Claude Code vs Codex vs Gemini CLI and AI video generator comparisons, best Claude Code skills/plugins and MCP servers (keep/try/skip), system-prompt library (64), key-facts table on all 64 guides, hooks cookbook (18 recipes, 33 events verified), annotated CLAUDE.md examples guide + its prompt system, tools/compare/best SEO branch, noindex-aware sitemap (1007 URLs) |
| `f4c3e8c` | 2026-10-22 22:42:44 -0400 | pre-wire tools/compare/best dirs into sitemap, SEO layer, footer nav |
| `8eaa7f8` | 2026-10-22 22:40:14 -0400 | SEO wave 2: server-rendered guides (no client markdown, 1 H1, 3k crawlable links), clean root-absolute URLs site-wide (0 .html links), static footer nav, 18 collection hub pages (every page &lt;=2 clicks from home), method page + Person author, entry VideoObject/CreativeWork schema + 846 share cards, content-hash lastmod/dateModified, sitemap = indexable HTML only (980), titles &lt;=65, FAQPage removed, agent-note lint, home 49-&gt;100 / catalog 55-&gt;93 Lighthouse (slim catalog.js, prerendered cards, self-hosted fonts, _headers), thumbs &lt;=640px, llms.txt live |
| `7e70f49` | 2026-10-22 22:07:35 -0400 | SEO technical audit + content/niche gap analysis (2026-10-22) |
| `e09e639` | 2026-10-22 22:03:46 -0400 | Real 404 page (suggests nearest entry/guide), 'In short' answer block atop all 63 guides (+ Article abstract), 404 kept out of sitemap |
| `812e876` | 2026-10-22 21:27:34 -0400 | analytics: report with /go/ table (live query ok) |
| `0ef3832` | 2026-10-22 21:24:16 -0400 | primer + skill: analytics live, indexing hubs, monetize layer (Phase 14c) |
| `d669c9c` | 2026-10-22 21:22:40 -0400 | Monetize layer: /go/ measured redirects for 26 tools (all pending), FTC disclosure + tip-jar/pack slots (render only when set), DIY + done-for-you CTA footer, analytics /go/ table, rebuild phase |
| `8d298fa` | 2026-10-22 21:10:57 -0400 | Indexing pass: entry pages become linked hubs (related/appears-in/creator/prev-next, ~17 internal links each), guides+deeper link to /e/ pages, noindex for admin/rate/legacy, robots crawlable, 55 stub summaries re-enriched (3 drops) |
| `97464b6` | 2026-10-22 20:46:36 -0400 | primer: Search Console wired |
| `0e9a751` | 2026-10-22 20:46:21 -0400 | analytics: baseline now includes Search Console (sitemap submitted, 974 URLs) |
| `70eda20` | 2026-10-22 16:42:10 -0400 | analytics: first baseline report (Cloudflare live); scanner UA class |
| `bac1daa` | 2026-10-22 13:32:38 -0400 | indexnow: send User-Agent (Cloudflare 403s bare urllib); 974 URLs submitted |
| `baf01ec` | 2026-10-22 13:30:30 -0400 | Discoverability + content loop: SEO layer on all public pages, start-here, RSS, OG images, analytics instruments, IndexNow, 63 IG content kits |
| `f0d3035` | 2026-10-22 10:38:19 -0400 | Prompt systems: one full prompting system per curated dive and guide (63 packs) |
| `361c1b9` | 2026-10-22 00:40:59 -0400 | Caption integrity fix (139 cross-wired captions), re-tier of July collections, 45 curated dives, full regen |
| `ad47f56` | 2026-10-21 19:16:22 -0400 | Site search, link audit fixes, rating/reconcile instruments, dedupe, carousel slide transcripts |
| `9097a51` | 2026-10-21 18:39:51 -0400 | primer: landing redesign done |
| `a8e0b23` | 2026-10-21 18:39:46 -0400 | Landing phase in rebuild.sh + skill docs; refreshed landing_meta.js |
| `05f9bec` | 2026-10-21 18:39:17 -0400 | Merge landing-redesign: showcase index.html, catalog moved to catalog.html |
| `746d7b1` | 2026-10-21 18:36:43 -0400 | Showcase landing at index.html: hero stats, destinations, insight dives, freshest saves, pipeline + install |
| `2f6e509` | 2026-10-21 18:31:33 -0400 | Move catalog to catalog.html; nav gains Catalog/About, drops Admin; repoint catalog links |
| `42b520a` | 2026-10-21 18:27:30 -0400 | October pull: 265 new entries via collection-feed API, GPU Whisper, LLM enrichment, researcher curation pass |

---

Generated 2026-10-23 (status) / 2026-10-23 (archive scan). Source files: `data/reports/status_2026-10-23.json`, `data/reports/growth_assets_2026-10-23.json`. Regenerate with `python3 scripts/build_report.py`.

Sources the status file was built from:

- `git log --since=2026-10-21`
- `primer.md`
- `session-log.md`
- `data/analytics/SETUP.md`
- `reports/analytics_2026-10-22.md`
- `data/seo/audit_2026-10-22.json`
- `data/seo/content_gaps_2026-10-22.json`
- `data/monetize/README.md`
- `data/monetize/affiliates.json`
- `data/monetize/affiliates_research.json`
- `data/monetize/config.json`
- `content/INDEX.md`
- `content/status.json`
- `skills/dejaviewed-content/SKILL.md`
- `site/method.html`
- `grep of href="/go/<slug>" across site/**/*.html`
- `live curl checks of dejaviewed.dev on 2026-10-23`
