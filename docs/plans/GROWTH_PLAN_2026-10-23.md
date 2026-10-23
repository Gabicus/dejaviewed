# DejaViewed Growth Plan — leave nothing on the table

Written 2026-10-23 by Fable (PM) from: the technical SEO audit, the content/niche gap analysis, the archive growth-asset scan (55 entries, 22 repos, 14 campaigns), the affiliate research (62 programs), the analytics baseline, and the 48-hour status report. Every tactic below traces to one of those files; entry ids are `/e/<id>` on dejaviewed.dev.

Sources: `data/seo/audit_2026-10-22.json`, `data/seo/content_gaps_2026-10-22.json`, `data/reports/growth_assets_2026-10-23.json`, `data/monetize/affiliates_research.json`, `reports/analytics_2026-10-22.md`, `docs/reports/dejaviewed_status_2026-10-23.html`.

---

## 0. The thesis in one paragraph

DejaViewed owns something nobody else has: 846 creator posts, 784 of them transcribed, tiered, cross-linked, with 64 full prompting systems and 18 tool hubs built on top. Competitors (Futurepedia, There's An AI For That, newsletters, awesome-lists) have tool lists; we have **what creators actually did, in their words, with a verdict**. The flywheel: the archive produces content → content earns saves and shares → shares earn creator reshares and answer-engine citations → citations earn search traffic → traffic reaches tool hubs with measured outbound links → clicks fund the loop and prove demand for the data itself. Residual income comes last and only from usefulness: affiliates on hubs, the done-for-you service, a monthly "run it for me" refresh, a prompt pack, a sponsorship slot in a citable monthly report, and eventually the dataset behind a 402.

Honest baseline: ~250 human visits/week, 0 outbound clicks recorded, 0 posts published, Google has indexed ~30% of the sitemap. Everything below is designed to compound from that, not to pretend otherwise.

---

## 1. Operating rules (apply to every workstream)

1. **One platform first.** Instagram daily until it is boring (DYR6m86oBj_: consistency on one platform before "known, loved, trusted"). Pinterest and LinkedIn are low-effort mirrors, not second homes.
2. **Credit, don't re-host.** Carousels paraphrase and credit; never repost a creator's video. Credit is also the distribution mechanic (Credit Loop).
3. **Ungated is the brand promise.** 28% of the archive hides its payload behind "comment KEYWORD". We give the answer. Every post, every page.
4. **Verdict on everything.** Keep / Try / Skip. Tier S–C. A page without a judgment is a list, and lists don't get shared.
5. **No slop.** Humanizer + StopSlop pass on every caption and slide (DbJzWBfxPvD, DcT15tflt4K). 10-word hooks, 12 words per slide (DXmbF8lCDOP).
6. **Measure before scaling.** Nothing moves from "experiment" to "cadence" without a number: saves/post, /go/ clicks, GSC impressions, referrer.
7. **Cost caps.** Headless Claude runs bill per token (DYXWNTERFhZ). Every automation has a monthly ceiling. Video credits burn fast. No paid distribution until an organic winner exists.
8. **Avoid the grey hat in the archive.** No expired-domain games (DdQD_N6Nhz2), no self-asserting AI-Overview gaming (DaEH4BJMxRX), no synthetic influencer funnels (DdXyLUWTJ4Z).

---

## 2. Workstreams

### W1. Content engine — the daily drip (Victor posts, Fable produces)

**What:** ship the 63 finished kits, one per day, on Instagram. Each caption gets one hand-written verdict line from Victor. Kits come from `content/<slug>/`; queue in `content/INDEX.md`; mark in `content/status.json`.

**Series that ride the same drip (rotate, 7-day cycle):**
- Mon **Kit Drip** — a guide as a carousel.
- Tue **Ungated** — one gated viral claim, the full answer, our verdict (links /best/ or the guide).
- Wed **Keep/Try/Skip reel** — 30–45s screen recording of a tool hub, Victor voiceover (the monetization series; every hub has /go/ links). Record with OpenScreen (DWl3Bo6jqX1).
- Thu **System prompt of the week** — copy-ready slides from /system-prompts.
- Fri **Read the fine print** — a sponsored-post claim vs what the tool does vs what our guide found; frame the claim, not the creator. Links /method.
- Sat **Quiz Saves** — 5 active-recall questions per guide, answers on the guide page.
- Sun **Hook Lab** — one decoded hook template from the 846-transcript hook library (see W6).

**Fable builds (this week):** `hooks.json` extractor (first 1–2 sentences of every transcript), humanizer/StopSlop gate + word caps in `content_kit.py`, kit templates for Ungated / Quiz / Fine-print / System-prompt / Hook formats, a `content/queue.md` daily brief ("post this, tag these 3 creators, use this hook"). Optional: Remotion template that animates slides into 9:16 reels; MoneyPrinterTurbo for rough drafts.

**Victor does:** 10 minutes a day: paste caption, add verdict line, post, tag, reply to comments for 30 minutes after (DYR6m86oBj_: first-hour engagement).

**KPI:** saves per post (target: beat the account's median within 3 weeks), profile → link clicks, posts/week = 7.

### W2. Credit Loop — creators as distribution

**What:** every guide names its creators. When a kit goes live, tag them in the post and DM: "your post anchors this guide, here's the page". Large accounts have a flattering, zero-cost reason to reshare (DbI0-guRspT, DZ7dVg_Rqog).

**Fable builds:** `data/creators/outreach.json` (creator → guides → kit date → DM template → status), creator pages at `/creators/<handle>` for handles with ≥4 entries (content gap item; also a page each creator wants to share), a "Featured in DejaViewed" badge image creators can post.

**Victor does:** 3 DMs/day from the queue. Reply to every creator who responds.

**KPI:** reshares, creator follows, referral visits from instagram.com.

### W3. Answer-engine and search (the compounding channel)

Already shipped this week: server-rendered guides, "In short" answer blocks, key-facts tables, clean URLs, collections, tool hubs, comparisons, method page, 1,007-URL sitemap, IndexNow. Now:

- **Indexing watch:** weekly `analytics_report.py`; target the 13-of-20 "discovered, not indexed" sample → indexed within 30 days. If a page type stalls, cut it (noindex) rather than dilute.
- **Answer seeding:** post each guide's "In short" keyword-first on LinkedIn; answer matching Reddit questions with the canonical guide link (answer engines cite UGC platforms: DaEH4BJMxRX, DXzst1gxPeK). 2 LinkedIn + 3 Reddit per week. Never spam; only where the question is actually asked.
- **Question mining:** Agent Reach-style weekly sweep of Reddit/HN/X questions in our 8 pillars → add a Q&A block to the matching guide or write a new one (content gap items 9–20).
- **Directories:** register llms.txt (llmstxt.site, directory.llmstxt.cloud), submit the skill to awesome-claude-code lists, Product Hunt + Show HN for the open-source skill (W5).
- **Citable artifacts:** "State of the Saves" monthly data page (W6) is the thing journalists and newsletters link.
- **Cross-links:** 1gabe.com → dejaviewed.dev (author site), GitHub README → site, every creator page → their Instagram.

**KPI:** GSC indexed count, impressions on the 25 target queries (`data/seo/queries.json`), ChatGPT-User/Perplexity-User fetches per week (already 119/25 in the baseline).

### W4. Owned channel — email (the gap the archive doesn't cover)

The corpus has zero email tactics and the site has no capture. Build it anyway; it is the only channel platforms can't throttle.

- Newsletter: **"7 saves you forgot"** — weekly, 7 entries (S/A) with one-line verdicts + the week's new guide + one system prompt. Entirely generated from the catalog; Victor edits 5 minutes.
- Capture: one block on /start-here, guide footers and the 404 page ("get the weekly 7"). Provider: Buttondown or Beehiiv (free tiers). Lead magnet: the prompt pack (W7) or the hook library.
- Fable builds the generator (`scripts/build_newsletter.py` → markdown + HTML issue from catalog deltas), the capture block, and the provider webhook.

**KPI:** subscribers, open rate, clicks to hubs.

### W5. The skill as a product — DejaViewed for everyone

The open-source skill (github.com/Gabicus/dejaviewed) is the proof-of-work and the top of the service funnel.

- **Build it live** series: a stranger's saves → a site, as YouTube Shorts/Reels; frame as Karpathy's LLM-wiki idea applied to 846 sources.
- **Launches:** Product Hunt, Show HN, r/ClaudeAI, r/SideProject, awesome-list PRs. One launch per month, not all at once.
- **README:** demo video, "run it on your saves in 20 minutes", badges, link to the method page.
- **Saved-tab roast (UGC hook):** people DM a screenshot of their Saved tab; we reply with 3 guides they should have read and an invite to the service. Cheap, personal, shareable.
- **Bookmarklet / share-sheet:** "You've saved this before?" → checks the catalog for the URL and returns our verdict. Small JS; a reason to install something.

**KPI:** stars, forks, skill installs (README clone counts), service inquiries.

### W6. Data products — the moat made visible

- **Hook Lab:** `/hooks` page from the 846-transcript hook library, clustered into fill-in-the-blank templates. Unique dataset; creators save it. Also a weekly post format (W1).
- **State of the Saves:** monthly report page: top tools by mentions, gated share (28%), sponsored share, tier distribution, new entries, what rose and fell. Citable, PR-pitchable, sponsorable (W7).
- **Open API:** already live (`/api/*.json`). Add a `/api/` index page, a changelog, and a "cite us" line. Free sample tier stays free forever.
- **Dataset release (bridge to pay-to-crawl):** publish a free sample on Hugging Face (titles, tiers, tools, links; no creator captions/transcripts) with a dataset card that points to the full versioned release behind a 402 (x402/USDC) when demand shows. Measure: who fetches `llms-full.txt` and `/api/` (baseline: nobody yet).

### W7. Monetization ladder (in order of effort → income)

1. **Affiliates (weeks 1–6)**: apply in the order of links on site × payout × ease: Runway (57 links), Higgsfield (46), ElevenLabs (30), then n8n, Kling, TradingView; later Vercel, Descript, Manus. Activate by pasting the tracking URL into `data/monetize/affiliates.json`, status active, rebuild. Expected: $0–15/month at current traffic. Honest. The point is the instrument, not the income.
2. **Done-for-you service** (`/go/service` → 1gabe.com/contact): "send me your saves, get your own site". Price $150–300 one-off. Case study = dejaviewed.dev itself. Lead sourcing: JobSpy-style search for knowledge-base/content-repurposing gigs.
3. **Run-it-for-me subscription**: monthly re-pull + re-enrich + new guides for a customer's saves. $9–19/month. This is the actual residual product; the pipeline already exists (`rebuild.sh`).
4. **Prompt pack** (Gumroad, $19): the 64 systems as an offline bundle with updates + the hook library. Free on site; paid for convenience and support.
5. **Sponsorship slot** in State of the Saves + the newsletter once >1,000 subscribers.
6. **Dataset / API licence** behind x402 (parked; build when `llms-full.txt` fetches appear).
7. **Tip jar / GitHub Sponsors**: trivially on; signal, not income.

### W8. Measurement and attribution

- Weekly `analytics_report.py` (Mondays): traffic, bots, AI crawlers, /go/ clicks per slug, GSC indexing + impressions, deltas.
- Add Plausible (or PostHog) with goals: /go/ click, service click, newsletter signup, scroll depth on guides; UTM tags on every campaign link (`?utm_source=ig&utm_campaign=kitdrip`).
- Own-post performance loop: Apify or manual export of post metrics into `content/status.json` → outlier hooks feed Hook Lab and kit hooks.
- Decision rules: a series that is below the account median on saves after 6 posts gets cut or reformatted; a hub whose /go/ clicks are 0 after 60 days loses its button placement to a better-performing hub.

### W9. Automation (with ceilings)

- n8n (self-hosted) + n8n-mcp: Telegram "post this" trigger → kit render → Buffer queue; LinkedIn cross-post of "In short" answers; weekly question-mining sweep. Monthly API cap $20.
- Weekly Fable routines: analytics report, new saves pull + full processing, newsletter draft, queue brief, State of the Saves on the 1st.
- Never automate the human parts: verdict lines, DMs, replies.

### W10. Brand, UX, trust

- Plain-English rewrite of IG bio, home hero and start-here opener (4-sentence formula DZMw4I8oh2m; 3-second-feeling test DYhEafYxHhw).
- Service landing block on /start-here with a real case study and price.
- Accessibility pass on dim mono labels (audit flagged contrast).
- /method already states tiers, affiliate policy, author, removal and reuse terms; confirm the two policy sentences with Victor.

### W11. Partnerships and PR

- Pitch State of the Saves to 5 AI newsletters monthly (Ben's Bites, The Rundown, TLDR AI, Superhuman, The Neuron) with one chart.
- Offer credited creators a co-post ("we read your post so you don't have to") — the Credit Loop at scale.
- Guest post on 1gabe.com and one dev blog about the pipeline (Whisper + enrichment + prompting systems).

### W12. Paid amplification — gated

Only after an organic post clears 2× the median saves: boost that post ($20 cap) or test the clipping economy ($1–1.50/1k views, DadfHYrkmr7) with a hard cap. Not before.

---

## 3. Timeline

**Week 0 (this week)**
- Victor: post kit #1 today; apply Runway, Higgsfield, ElevenLabs; Cloudflare email obfuscation off; confirm /method sentences; pick newsletter provider.
- Fable: hooks.json; humanizer + caps in content_kit; 5 new kit formats + 7-day rotation queue; creator outreach file; UTM on all campaign links; `/api/` index page; Plausible snippet (if Victor creates the account) or Cloudflare-only goals.

**Weeks 1–2**
- Daily drip running (7/week). Credit Loop DMs (3/day). Answer seeding (2 LinkedIn, 3 Reddit/week).
- Fable: creator pages (≥4 entries), `/hooks` page, newsletter generator + capture block, first "7 saves you forgot" issue, weekly report #2.
- Affiliates week 2: n8n, Kling, TradingView.

**Weeks 3–4**
- First Keep/Try/Skip reels recorded (3 hubs). Pinterest shelf starts (5 pins/week).
- Fable: State of the Saves #1 (Nov 1), PR pitch list, llms.txt directory registrations, Product Hunt page draft for the skill.
- Affiliates week 3: Vercel, Descript, Manus. First activation rebuilds as approvals land.

**Month 2**
- Skill launch #1 (Show HN or Product Hunt). Build-it-live short #1. Saved-tab roast opens.
- Service page with case study + price; first outreach batch (JobSpy list).
- Content gap builds 9–20 as Search Console confirms the first wave indexes (token-usage case study, glossary, n8n MCP explained, "new this week").
- Hugging Face sample dataset + card.

**Month 3**
- Run-it-for-me subscription offered to service customers. Prompt pack on Gumroad. Sponsorship slot drafted.
- Decision review: cut series below median; double the ones above; decide pay-to-crawl build from `llms-full.txt` fetch data.

---

## 4. KPIs and kill/scale rules

| metric | baseline (Oct 22) | 30 days | 90 days |
|---|---|---|---|
| human visits / week | ~250 | 500 | 1,500 |
| GSC indexed pages | ~30% of sitemap | 60% | 85% |
| posts published | 0 | 28 | 84 |
| saves per post (median) | n/a | account median | 2× |
| /go/ clicks / week | 0 | 20 | 100 |
| AI-crawler guide fetches / week | ~150 | 300 | 600 |
| newsletter subscribers | 0 | 100 | 500 |
| service inquiries | 0 | 2 | 6 |
| affiliate programs active | 0 | 4 | 8 |

Scale what beats target; cut what misses two reviews in a row. Numbers are targets, not predictions.

---

## 5. Who does what

**Victor (needs a human, a face, or a login):** daily post + verdict line + 30 minutes of replies; 3 creator DMs/day; affiliate applications on schedule; Cloudflare toggles; newsletter provider account; record reels (voice); approve prices and policy sentences; launches (PH/HN need a human account).

**Fable (everything else):** all generators, pages, kits, queues, reports, outreach files, newsletter drafts, data pages, launch copy, measurement, weekly review, and the specs for Opus subagents that write content at scale (with the no-slop gate and the cite-every-claim law).

---

## 6. What could make this actually spread (the clever bits, ranked by my confidence)

1. **Ungated as identity.** "We read the gated post so you don't have to comment 'GUIDE'." It names a universal irritation, it is repeatable daily, and it makes creators who gate look worse by comparison without attacking them.
2. **Credit Loop.** Free distribution from accounts 100× our size, triggered by flattery that is also true.
3. **Hook Lab dataset.** The one asset no one else can produce; creators will save and share hook templates mined from 846 real posts.
4. **State of the Saves.** Monthly numbers reporters can cite; a sponsorship slot falls out of it.
5. **Saved-tab roast.** Personal, cheap, screenshot-native, funnels straight to the service.
6. **The skill itself.** Open source turns the whole operation into a story other people can tell: "I ran DejaViewed on my saves."
7. **Keep/Try/Skip reels on hubs.** The only series that earns money on day one, and it is honest.

---

## 7. First actions, in order (today)

1. Victor posts kit #1 with a verdict line; tags its creators.
2. Victor applies to Runway, Higgsfield, ElevenLabs (links and rules in the status report).
3. Fable ships hooks.json, the no-slop gate, the 7-day rotation queue, the outreach file, UTM tags, and the `/api/` index page, then re-runs the weekly report Monday.
