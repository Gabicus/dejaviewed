# DejaViewed · primer

Updated: 2026-10-21

## Current status

846 entries · 18 collections · 310K crosslinks · 203 deep dives (38 curated) · 57 guide pages · 38 deeper pages. Site live at dejaviewed.dev (Cloudflare Pages, auto-deploy from main). Quality gate passes. Everything from the Oct 21 pull is captioned, Whisper-transcribed (medium, GPU), thumbed, LLM-enriched and indexed (api/, sitemap 957 URLs, llms.txt, context.md all live-computed).

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

## PAUSED mid-run (Oct 21 evening) — resume here first

Caption refresh was stopped at a checkpoint (152/549 pre-October entries verified; `data/caption_refresh.json`). To resume, in order:
1. Start CDP Chrome + attach: `bash <scratchpad>/start_cdp.sh` equivalent — see SKILL.md Phase 0 v3 (Chrome must be closed first; log into Instagram in regular Chrome if the saved page shows "Log In").
2. `python3 scripts/ig_refresh_captions.py --codes-file <old codes>` (old codes = IG entries not in data/new_items_2026-10-21.json). Resumes from the cache. ~6 s/post.
3. `python3 scripts/ig_refresh_captions.py --apply` → data/caption_refresh_changed.json lists entries whose caption/creator changed.
4. Export those ids with `scripts/llm_enrich_batches.py export --ids <file>` → Opus enrichment agents (data/llm_batches/SPEC.md) → merge.
5. Finish tier re-rate: data/llm_retier/out_01-03.json exist (merge tier-only for entries whose caption did NOT change); batches 04-06 still need an agent (first agent was stopped by a safety classifier mid-write; grade on caption where transcript mismatches).
6. Also fix in parquet: entry DehlIB2PT4h takeaway link maths.tcd.ie (dead → Wikipedia Broom Bridge), entry repo github.com/open-multi-agent/scaffold (deleted → note).
7. Regen chain: cms rebuild → deep_dives → deeper_dives --all-curated → build_guides → build_landing_meta → digest → cms rebuild → build_api → build_context → catalog_js → build_search.sh → quality_gate → commit → push → live check.
Already live after the Oct 21 evening push: site search, link fixes, rate.html + instruments, dedupe/link-check scripts, carousel slide transcripts, lesson 51. NOT yet regenerated on site: the 7 promoted dives (manual_dives.json has 45; site shows 38) — step 7 picks them up.

## Next up

1. ~~Landing redesign~~ DONE Oct 21 (merged 05f9bec): index.html = showcase, catalog.html = full catalog, nav Catalog·Guides·Graphs·Board·About, Admin out of nav. `build_landing_meta.py` runs after guides/deeper regen.
2. Parked q3 proposals: revisit after Victor reads the 17 new dives.
3. Carousel slide videos (few) untranscribed — add to transcribe.py targets if wanted.
4. Old collections ai2/ai4/ai7/quant S-rate 20–29% (July manual regrade) — gate warns; decide whether to re-tier with the LLM rubric.
5. Deeper-version items not yet built: pHash dedupe, embeddings-based clustering/search (Pagefind), lychee link check, blind kappa re-rate, IG data-export reconciliation.

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
