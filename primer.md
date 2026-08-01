# DejaViewed · primer

Updated: 2026-07-13

## Current status

581 entries across 15 collections. ~146K crosslinks. 150 deep dives (21 curated, 1 featured). 31 guide pages. 21 deeper dive pages. CMS parquet is source of truth. Site live at dejaviewed.dev via Cloudflare Pages (auto-deploy from main).

### Coverage (post July 8-13 enrichment push)
- Captions: 546/581 (5 IG failures, 30 non-IG URLs — expected gaps)
- Transcripts: 510/581 (13 video failures, 58 images with no audio — expected)
- Thumbnails: 570/581 (4 no og:image, 7 other)
- Tiers (post-audit, honest): S 84 · A 179 · B 264 · C 54

### Collections (15)
ai1, ai2, ai3, ai4, ai5, ai6, ai7, quant, stock2, music, creative, prompts, game-theory, art-inspiration, art-i-like

### Repos
- `~/Desktop/Projects/dejaviewed-plugin/` — main project (github.com/Gabicus/dejaviewed, PUBLIC)
- `~/.claude/` — private config repo (github.com/Gabicus/claude-config, PRIVATE) — holds Operator skill install
- `~/Desktop/Projects/dejaviewed.social/` — PRIVATE social pipeline
- graph-node / graph-cosmos — separate generic graph engine repos

## Skill architecture (v2, July 13) — IMPORTANT

ONE generic SKILL.md, TWO modes, keyed off `references/site-deployment.md` presence:
- **Operator Mode** (Victor's install at `~/.claude/skills/dejaviewed/`): private overlay file holds hosting, domain, collections, coverage, deploy workflow. Deploys to dejaviewed.dev.
- **Public Mode** (GitHub installs): no overlay → builds user's OWN local site, offers hosting options, NEVER touches dejaviewed.dev. Ships `site-deployment.example.md` template.
- Overlay is gitignored in the public repo. It leaked once (fixed in 6edbc40) — never commit it.
- After editing local skill: `cp ~/.claude/skills/dejaviewed/SKILL.md skills/dejaviewed/SKILL.md`, commit both repos.
- 44 numbered lessons in SKILL.md. Key new ones: #43 bait-caption title poisoning, #44 instance facts stay in overlay.

## What changed (July 8-13)

- **July 8:** 161 captions scraped (`ab_scrape_posts.py --missing-captions` — new flag), 146 Whisper transcripts (`transcribe.py --all --model small`), full re-enrich, 150 dives regenerated, crosslinks 131K→146K. Deployed.
- **July 13 (Fable 5 review):** Public/Operator skill split; personal overlay removed from public repo + gitignored; fixed skill contradictions (deprecated profile-copy/Playwright prereqs, stale ingest/thumb sections); repaired 22 junk titles from bait captions; regraded S-tier 92→84; wrote session-log.md with digest + recommendations R1-R6.

## Next up

### High priority
- **R1 — Catalog→Claude recall loop:** Fix `build_context.py` (reads legacy `catalog.jsonl`, predates parquet CMS — currently broken, context.md stale from April). Then wire `site/api/catalog.json` querying into session starts so 84 S-tier entries prime related work.
- **R2 — Harness merge:** Fold Claude Harness Pattern dive findings (9 entries) into `~/.claude/cognitive_scaffolding.md`. ~30 min.
- **Skill on site:** Ensure dejaviewed.dev advertises the skill + install instructions.

### Medium
- **R3 — Enrichment quality gate:** Add assert to `enrich_entries.py --sweep`: titles <14 chars must be 0, S-rate <15%/collection. Bait captions title from TRANSCRIPT.
- **R4 — Monthly ingestion flywheel:** proven pipeline: pull → captions → whisper → enrich → audit gate → dives → push. agent-browser login is the one manual step.
- **Claude Mastery guide maintenance:** living doc — update with new models/features.

### Ideas
- **R5 — Dive-to-skill converter:** quality-5 dives (thesis/prereqs/action sketch) → SKILL.md scaffolds.
- R6 (rejected): RSS, keyword-engine integration, per-entry page redesign — low value.

## Scraping workflow (agent-browser)

```bash
npx agent-browser close
npx agent-browser --profile Default --headed open "<collection_url>"   # Chrome must be CLOSED
bash scripts/ab_extract_urls.sh <name> "<url>"                          # or ab_extract_cumulative.py
python3 scripts/ingest.py --urls-file data/<name>_urls.json --collection <name> --non-interactive
python3 scripts/ab_scrape_posts.py --missing-captions                   # captions BEFORE whisper
python3 scripts/transcribe.py --all --model small                       # Chrome closed (cookies)
python3 scripts/enrich_entries.py --sweep                               # then audit titles/tiers
python3 scripts/deep_dives.py && python3 scripts/deeper_dives.py --all-curated
python3 scripts/cms.py rebuild
git add -A && git commit && git push                                    # push = deploy
```

## Don't forget

- Run captions BEFORE Whisper — caption scrape corrects media_type; otherwise videos tagged "image" get skipped
- After bulk enrichment: audit `title.len<14`==0 and S-rate <15%/collection (bait captions poison titles)
- NEVER commit `references/site-deployment.md` to the public repo (gitignored, stay vigilant)
- NEVER change shared.css breakpoints for single-page issues
- ALWAYS push before destructive operations
- DESIGN.md is UI authority; agent-browser needs Chrome closed
- Collection pills dynamic — no HTML changes for new collections
- "tutorial" merged into "skill" — don't re-add
- Verify entry IDs before writing manual_dives.json
- Guide/deeper pages call `DV.mountHeader()`; guide↔deeper cross-links via inline div
- [NEEDS ENRICHMENT] bug: 3-layer defense in cms.py
- Enrichment deletes parquet before internal migrate to avoid stale title merge
- `~/.claude/CLAUDE.md` + `settings.json` have uncommitted changes predating July 13 — left alone deliberately
