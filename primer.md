# DejaViewed · primer

Updated: 2026-10-22 (pm)

## Current status

846 entries · 18 collections · 324K crosslinks · 219 deep dives (45 curated) · 63 guide pages · 45 deeper pages · **63 prompt systems** (one per curated dive + hand-written guide) · site search · 0 broken links. Site live at dejaviewed.dev (Cloudflare Pages, auto-deploy from main). Quality gate passes. Everything from the Oct 21 pull is captioned, Whisper-transcribed (medium, GPU), thumbed, LLM-enriched and indexed (api/, sitemap 957 URLs, llms.txt, context.md all live-computed).

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

### Oct 22 (pm) — prompt systems
- **Phase 5d built:** every curated dive (45) and hand-written guide (18) now carries a full prompting system: deeper-not-bigger block (pro would / rawest material / methods+tools / external proof / rewritten prompt), one-shot prompt (500-1000 w), 5-9 step prompts each with expect+audit, gap-audit prompt, self-questions, validation oracles, failure modes, agent direction. Written by 10 Opus agents to `data/prompt_systems/SPEC.md`; validator in `scripts/prompt_systems.py`.
- **Rendered:** bottom of every guide page (marked + copy buttons, anchor `#prompt-system`), every deeper page, `site/prompts.html` index, `site/api/prompts.json`, Prompts nav item, landing tile, llms.txt + sitemap entries.
- **Pipeline:** `rebuild.sh` has a `prompts` phase that stops when any target lacks a pack; `build_guides.py --force` and `deeper_dives.py` embed packs; hand-written guides are patched in place between `<!-- prompt-system:start|end -->` markers (lesson #52).
- Security-adjacent packs (jailbreak repo, leaked system prompt, injection-CI, headless, OSINT) are defensive-only; money packs carry paper arms + caps + "no real money" gate.

## Next up

1. ~~Landing redesign~~ DONE Oct 21. ~~Parked dives, carousel videos, re-tier, search, dedupe, link check~~ DONE Oct 22.
2. ai2/ai5/stock2 still ~20% S (small collections, July tiers) — re-tier with `data/llm_retier/SPEC.md` if it bothers you.
3. 3 likely reposts (dedupe report "possible", same creator+title+thumb) — download the missing mp4 to confirm, then merge.
4. Blind re-rate: open /rate.html, rate 30, download JSON → `scripts/apply_ratings.py`.
5. IG data export → `scripts/reconcile_ig_export.py` for the authoritative save list.
6. Embedding-based clustering (replace keyword dives/crosslinks) — only remaining "deeper version" item.
7. Prompt systems: run 3 packs end-to-end for real (e.g. claude-second-brain, plotter-loop, polymarket-99c paper arm) and feed what breaks back into SPEC.md. New curated dives need a pack before publish (rebuild.sh enforces).

## Next run — Victor setup items (Oct 21 aside: analytics, money, reach)

**Victor does (needs dashboard/login):**
1. Cloudflare → Web Analytics → add `dejaviewed.dev` with automatic injection for Pages. Site has NO analytics beacon today → zero page-view data.
2. Create API token (Account Analytics: Read + Zone Analytics: Read) → save as `CLOUDFLARE_API_TOKEN=...` in `~/.config/cloudflare/dejaviewed.env` (chmod 600), never in chat. Then Fable pulls GraphQL reports: human vs bot share, which crawlers hit /api/ + llms.txt, top pages, Web Vitals.
3. `! npx wrangler login` (token expired Oct 21) so wrangler deploy fallback works.
4. Apply for Cloudflare **Pay Per Crawl** (private beta; HTTP 402 for Web-Bot-Auth crawlers). Pocket change at this scale, free to enable.
5. Google Search Console + Bing Webmaster: submit sitemap.xml (957 URLs).

**Fable does (queued):**
6. OG/meta description tags on every guide/entry page (unfurls on X/LinkedIn/Discord).
7. Social: 45 curated dives → one thread each via dejaviewed.social pipeline.
8. Register llms.txt on llmstxt directories (llmstxt.site, directory.llmstxt.cloud).
9. `/accessibility-audit` on index/catalog/guides — contrast on dim mono labels likely fails.
10. RSS/Atom feed for new entries + dives.
11. Optional: x402 Worker on /api/* (402 + stablecoin price for agents, free for humans). Demand unproven — build only as an experiment.

## Don't forget

- `cms.py rebuild` BEFORE `enrich_entries.py --sweep` (enrich reads catalog.json, clobbers parquet-only edits) — lesson #50
- Don't write parquet while transcribe.py runs — lesson #48
- pkill/pgrep -f patterns match your own tool shell → use helper scripts (exit 144 ×5 this session)
- Media-info API throttles after ~75 calls; per-post page nav gives stale pk unless you verify returned `code`
- agent-browser bundled Chromium can't decrypt Chrome ≥136 cookies → CDP attach (Phase 0 v3)
- Signed CDN URLs expire in hours → download media right after the pull
- NEVER commit `references/site-deployment.md`; `data/media/` and `data/*.bak*` are gitignored
- Chrome window driven over CDP keeps playing whatever post was last opened — park it on about:blank
