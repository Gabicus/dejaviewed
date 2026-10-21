# DejaViewed — Session Log

## 2026-07-13 · Fable 5 Full Review: Skill Split, Quality Audit, Digest & Recommendations

### 1. What was fixed this session

| Fix | Detail |
|---|---|
| **Public/private skill split** | Personal `site-deployment.md` (your domain, repo, collections) was committed to the PUBLIC repo. Removed, gitignored, replaced with `site-deployment.example.md` template. |
| **Two-mode architecture** | New "Public vs Operator" section in SKILL.md. One generic skill; presence of `references/site-deployment.md` switches behavior. Your local install = Operator Mode (deploys to dejaviewed.dev). Public installs = Public Mode (builds their own local site, never touches yours). |
| **Prerequisites contradiction** | Skill demanded deprecated Chrome profile-copy + Playwright MCP while Phase 0 said agent-browser replaced both. Rewritten: agent-browser primary, legacy noted. |
| **Stale Phase 1 & 6** | ingest.py "cookies from .profile-copy" removed; thumbnails section now names `ab_download_thumbs.py` as primary, `download_thumbs.py` as legacy. |
| **build_context.py breakage documented** | Reads legacy `catalog.jsonl`, predates parquet CMS. Known-issue note added to Phase 9. `site/context.md` is stale (April, 209 entries) until fixed. |
| **Title regression repaired** | July 8 re-enrichment produced 22 junk titles ("Claude", "Anthropic — for more details:") from engagement-bait captions. All 22 rewritten as "Subject — angle" from transcripts. |
| **Tier inflation corrected** | S-tier trimmed 92 → 84. ai7 was at 30% S-tier; bait posts regraded honestly. New lessons #43-44 added to skill. |

### 2. Catalog digest — what 581 entries actually say

Top domains: art (134), video production (109), **agents (108)**, **prompt engineering (83)**, design (73), open source (69). Top tools: **Claude (125) + Claude Code (62) + Anthropic (32) = 219 Claude-family entries — 38% of the catalog.**

The 21 curated dives cluster into four meta-themes:

| Meta-theme | Dives | The takeaway |
|---|---|---|
| **Claude as infrastructure** | Claude Mastery, Harness Pattern, Power User Toolkit, Self-Improving Workspace, Prompt Architecture | Context/memory/harness engineering is the durable skill; individual features churn |
| **One-person leverage** | One-Person Studio (23 entries), Creative Empire, Video Studio, Autonomous Brand Machine | Team-replacement stacks are real; the moat is pipeline assembly, not any single tool |
| **Body/code as art medium** | MediaPipe×TouchDesigner, Code as Canvas, Interactive Installations, NL→3D | Real-time body-to-art is commodity-accessible now |
| **Markets & incentives** | Physics→Alpha, 25 Agents Trading, Incentive Trap, Art Without Gatekeepers | Cross-domain model transfer (physics→markets, game theory→AI) is the recurring alpha pattern |

### 3. Recommendations — scaffolding to adopt

**R1. Close the loop: make the catalog feed Claude sessions (HIGH).**
The skill's promise — "your saves become working memory for your AI tools" — is built but unused. `site/api/*.json` + `llms.txt` exist; nothing queries them. Action: fix `build_context.py` to read parquet/catalog.json, then add a recall habit (CLAUDE.md rule or tiny skill): when starting agent/creative/trading work, grep `site/api/catalog.json` for matching tools/techniques. Your 84 S-tier entries become session priming instead of shelf inventory.

**R2. Harness findings → cognitive_scaffolding.md (HIGH).**
The Claude Harness Pattern dive (9 entries) independently converges on your existing `~/.claude/cognitive_scaffolding.md` architecture. Fold in what's new (markdown-folder harnesses, advisor-mode model routing, memory-graph patterns); discard the rest. One-time 30-min merge.

**R3. Enrichment title-quality gate (MEDIUM — codified as lesson #43).**
Add to any future bulk enrichment: post-run audit that `title.len < 14` count is 0 and per-collection S-rate < 15%. Bait-caption entries must title from transcript. Could be a 5-line assert in `enrich_entries.py --sweep`.

**R4. Scheduled ingestion flywheel (MEDIUM).**
Pipeline is now proven end-to-end (166 captions, 146 transcripts in one sitting). Monthly cadence: new-collection pull → captions → whisper → enrich → audit gate (R3) → dive regen → push. Semi-automatable via /schedule; agent-browser login remains the manual step.

**R5. Dive-to-skill converter (IDEA).**
Quality-5 curated dives are already structured (thesis, prerequisites, action sketch, entry evidence) — that's a SKILL.md skeleton. E.g. MediaPipe×TouchDesigner dive → `/body-to-art` skill. Would turn the catalog from reference into executable capability.

**R6. Don't build:** RSS feed, keyword-engine integration (low value vs. R1-R4); per-entry pages redesign (parked in legacy, fine there).

### 4. State after this session

- 581 entries · captions 546 · transcripts 510 · thumbs 570 · crosslinks ~146K
- Tiers: S 84 · A 179 · B 264 · C 54 (post-audit, honest)
- Skill: v2 with mode split, 44 lessons, synced local ↔ repo
- Public repo no longer leaks personal deployment info

---

## 2026-10-21 — October pull: 265 new entries, API pipeline, researcher curation pass

### What Victor asked
Pull everything new from ai8 / quant / stock2 / stock3 / creative (+ creative4, music found on IG), fully process every post (caption, Whisper-listened transcript, thumbnail, keywords, "all the AI juice"), rerun all analyses, index the best, make the deep dives researcher-grade (novel ideas *between* technologies), add it all to the site + sitemap, update the public skill so others can rebuild the same suite, then publish. Also: say what a top professional would do that wasn't asked for, name the rawest material and methods/tools, and who else would prove results right.

### Coverage after the run

| collection | n | captions | videos | transcripts | thumbs | S/A/B/C |
|---|---|---|---|---|---|---|
| ai8 (new) | 111 | 111 | 109 | 109 | 111 | 6/34/45/26 |
| creative (+83) | 149 | 149 | 148 | 147 | 148 | 10/42/76/21 |
| music (+41) | 69 | 69 | 69 | 69 | 69 | 1/9/44/15 |
| creative4 (new) | 11 | 11 | 11 | 11 | 11 | 0/3/5/3 |
| stock3 (new) | 14 | 14 | 14 | 14 | 14 | 1/3/3/7 |
| stock2 (+8) | 14 | 14 | 14 | 14 | 14 | 2/5/6/1 |
| quant (+5) | 30 | 30 | 29 | 29 | 30 | 8/12/8/2 |
| **total** | **846** | 811 | 782 | 778 | 813 | 98/251/374/123 |

Gaps are all logged (30 non-IG URLs, 5 deleted posts, 1 no-audio video, 20 music-only reels). Quality gate: ALL PASS (warnings only on July-era S-rates in ai2/ai4/ai7/quant).

### What a top professional would do that wasn't asked (delivered where cheap, scoped where not)
| Item | Status |
|---|---|
| Pull from the API (rawest structured source) instead of scroll-scraping DOM | **Done** — found 2.5× more posts in small collections |
| Get the media itself, not og:image; read carousel slides | **Done** (6 carousels vision-read) |
| True creators/dates from the API, not from DOM text | **Done**; exposed 48 "Edited" creator bugs + 7 cross-wired captions from the July scrape |
| Hard quality gates as code | **Done** — `quality_gate.py` |
| Researcher-grade curation with explicit novelty + falsifier | **Done** — 4 lenses, 26 proposals, 17 shipped |
| Instagram data-export reconciliation (authoritative save list) | Not done — needs Victor to request export from IG |
| pHash dedupe, embedding clustering / semantic site search (Pagefind), lychee dead-link check, blind kappa re-rate, Opus blind title judge | Not done — scoped in primer "Next up" |

**Who proves it right besides us:** the IG export count (external ground truth), lychee (0 dead S-tier links), a blind re-rate by Victor on 30 entries (Cohen's kappa), a second-model blind title judge, Cloudflare Web Analytics on what visitors actually open.

### Researcher pass — the 17 new curated dives
Red-Team Your Own Agent · Skills That Earn Their Lines · Earned Autonomy router · Every App Is Headless Now · Dox Yourself First · Anything With Geometry (pen-plotter loop) · Capture the Room Twice · Escaping the AI House Style · Melody Genealogy · Own the Thermometer · Strategy Autoresearch (the judge is the product) · Forecast the Weather, Not the Price · Buying Dead Apps · Scan, Fit, Print · Ambient Executive Function · Benchmark Your Brain · Offline AI Appliances.
Best cross-lens connections: Ising herding model as a choreography score; an agent loop's own trial count makes deflated-Sharpe exact; agent supervision and ADHD scaffolding are the same interface problem.

### Incidents / lessons (now in SKILL.md #45–50 + memory)
- agent-browser's Chromium can't decrypt Chrome ≥136 cookies → CDP attach to real Chrome.
- Scroll-scrape lossy; API complete.
- `pkill -f` from a tool shell kills the shell (5×).
- Enrich reads catalog.json → rebuild before sweep.
- Per-post page nav returns stale pk → verify returned shortcode.
- Media-info API throttles ~75 calls.

### Rewritten prompt (what to ask next time)
> Pull every post from IG saved collections X via the collection-feed API; download media immediately; ingest with API captions/creators/dates; Whisper every video from local files on GPU; vision-read every carousel; LLM-enrich from caption+transcript+OCR with the SPEC; run the quality gate; run the researcher curation pass with 4 lenses and review; regenerate dives/deeper/guides/digest/api/context/sitemap; verify every new page serves 200 and appears in index, guides index, api and sitemap; update skill + overlay + primer; commit by explicit paths; push.
