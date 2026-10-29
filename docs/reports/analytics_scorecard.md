# DejaViewed growth scorecard

Generated 2026-10-29 by `scripts/analytics_scorecard.py` from 2 audits (2026-10-22, 2026-10-29). Same metric definitions for every audit; `n/a` = not measured at that audit.
Weekly routine: `python3 scripts/analytics_report.py --inspect 40 && python3 scripts/analytics_scorecard.py`, then add what you learned to `data/analytics/findings.json` and what shipped to `data/analytics/changes.json`.

## Growth at a glance

| metric | first audit (2026-10-22) | previous (2026-10-22) | latest (2026-10-29) | since first | since previous |
|---|---|---|---|---|---|
| Real visits, 7 days | 252 | 252 | 407 | +62% ▲ | +62% ▲ |
| Google impressions, 7 days | 0 | 0 | 2,685 | new ▲ | new ▲ |
| Google clicks, 7 days | 0 | 0 | 12 | new ▲ | new ▲ |
| Indexed share of URL-inspection sample | 30% | 30% | 88% | +57 pts ▲ | +57 pts ▲ |
| OpenAI search crawler (OAI-SearchBot), 7 days | 55 | 55 | 1,661 | ×30.2 ▲ | ×30.2 ▲ |
| ClaudeBot hits, 7 days | 116 | 116 | 1,496 | ×12.9 ▲ | ×12.9 ▲ |
| ChatGPT live fetches for a user (ChatGPT-User), 7 days | 117 | 117 | 429 | ×3.7 ▲ | ×3.7 ▲ |
| Largest Contentful Paint p75 (LCP) | 2,508 | 2,508 | 992 | -60% ▲ | -60% ▲ |
| Human /go/ clicks, 7 days | 0 | 0 | 105 | new ▲ | new ▲ |

▲ = moved the good way, ▼ = moved the bad way.

## Every metric, every audit


### People

| metric | 2026-10-22 | 2026-10-29 | change since first |
|---|---|---|---|
| Real visits, 7 days | 252 | 407 | +62% ▲ |
| Real page views, 7 days | 266 | 538 | +102% ▲ |
| Real visits, 28 days | 570 | 990 | +74% ▲ |
| Edge unique visitors (sum of daily), 7 days | 3,344 | 9,113 | +173% ▲ |

### Google search

| metric | 2026-10-22 | 2026-10-29 | change since first |
|---|---|---|---|
| Google impressions, 7 days | 0 | 2,685 | new ▲ |
| Google clicks, 7 days | 0 | 12 | new ▲ |
| Google impressions, 28 days | 0 | 2,685 | new ▲ |
| Google clicks, 28 days | 0 | 12 | new ▲ |
| Average Google position, 28 days | n/a | 9.0 | +0% |
| Indexed share of URL-inspection sample | 30% | 88% | +57 pts ▲ |
| Pages with any impressions, 7 days | n/a | 277 | +0% |

### Crawlers & answer engines

| metric | 2026-10-22 | 2026-10-29 | change since first |
|---|---|---|---|
| Googlebot hits, 7 days | 178 | 5,070 | ×28.5 ▲ |
| Bingbot hits, 7 days | 80 | 111 | +39% ▲ |
| OpenAI search crawler (OAI-SearchBot), 7 days | 55 | 1,661 | ×30.2 ▲ |
| ChatGPT live fetches for a user (ChatGPT-User), 7 days | 117 | 429 | ×3.7 ▲ |
| ClaudeBot hits, 7 days | 116 | 1,496 | ×12.9 ▲ |
| Claude live fetches for a user (Claude-User), 7 days | 2 | 17 | ×8.5 ▲ |
| PerplexityBot hits, 7 days | 81 | 201 | +148% ▲ |
| Perplexity live fetches (Perplexity-User), 7 days | 25 | 17 | -32% ▼ |
| GPTBot (OpenAI training crawler), 7 days | 58 | 49 | -16% |
| Amazonbot hits, 7 days | 88 | 2,769 | ×31.5 |
| Bot pulls of /llms-full.txt, 7 days | 2 | 14 | ×7.0 ▲ |
| Bot pulls of /api/*, 7 days | 363 | 164 | -55% ▼ |

### Speed (real visitors)

| metric | 2026-10-22 | 2026-10-29 | change since first |
|---|---|---|---|
| Largest Contentful Paint p75 (LCP) | 2,508 | 992 | -60% ▲ |
| Interaction to Next Paint p75 (INP) | 312 | 216 | -31% ▲ |
| Cumulative Layout Shift p75 (CLS) | 0.096 | 0.012 | -88% ▲ |

### Outbound clicks

| metric | 2026-10-22 | 2026-10-29 | change since first |
|---|---|---|---|
| Human /go/ clicks, 7 days | 0 | 105 | new ▲ |
| Human clicks on the done-for-you service link, 7 days | 0 | 19 | new ▲ |
| Human clicks on the DIY (GitHub skill) link, 7 days | 0 | 21 | new ▲ |

### Site health

| metric | 2026-10-22 | 2026-10-29 | change since first |
|---|---|---|---|
| 404 responses, 7 days (sampled) | 73 | 3,222 | ×44.1 ▼ |
| 404s on non-probe paths, 7 days | n/a | 465 | +0% |
| Cloudflare threats blocked, 7 days | 133 | 127 | -5% |
| Sitemap errors in Search Console | 0 | 0 | = |

### Site inventory

| metric | 2026-10-22 | 2026-10-29 | change since first |
|---|---|---|---|
| Entries | n/a | 846 | +0% |
| Guides | n/a | 64 | +0% |
| Indexed tool hubs | n/a | 18 | +0% |
| Sitemap URLs | n/a | 1,008 | +0% |

## Google search by week (daily series, backfilled from Search Console)

| week starting | days with data | clicks | impressions | clicks per 1,000 impressions |
|---|---|---|---|---|
| 2026-10-19 | 4 | 6 | 2,270 | 2.6 |
| 2026-10-26 | 2 | 10 | 775 | 12.9 |

### Where Google shows us (2026-10-21 to 2026-10-27)

| section | pages | impressions | clicks |
|---|---|---|---|
| /catalog | 1 | 1,861 | 2 |
| /e/ | 180 | 565 | 9 |
| /guides/ | 50 | 495 | 3 |
| /deeper/ | 22 | 106 | 0 |
| /best/ | 2 | 26 | 0 |
| / | 1 | 19 | 1 |
| /collections/ | 8 | 12 | 0 |
| /prompts | 1 | 9 | 1 |
| /compare/ | 1 | 6 | 0 |
| /start-here | 1 | 4 | 0 |
| /flow | 1 | 3 | 0 |
| /method | 1 | 3 | 0 |
| /tools/ | 2 | 3 | 0 |
| /go/ | 1 | 2 | 0 |

### 404s on real-looking paths (latest audit week)

| path | hits |
|---|---|
| `/favicon.ico` | 216 |
| `/.well-known/traffic-advice` | 36 |
| `/cdn-cgi/l/email-protection` | 25 |
| `/data/deeper_dives.json` | 10 |
| `/og/default.png` | 8 |
| `/thumb/DX70-hPsI1q.jpg` | 4 |
| `/.well-known/security.txt` | 4 |
| `/meta.json` | 4 |
| `/build/manifest.json` | 3 |
| `/ngsw.json` | 3 |
| `/nx.json` | 3 |
| `/.vscode/launch.json` | 3 |

## What we shipped (changes log)

| date | change |
|---|---|
| 2026-10-21 | Oct 21 pull: 265 new entries via collection API, Whisper transcripts, LLM enrichment, 17 new curated dives |
| 2026-10-22 | Caption integrity fix (139 entries), re-tier, site search (Pagefind), link checker, 7 parked dives promoted |
| 2026-10-22 | SEO layer on every page (canonical, descriptions, Open Graph cards, JSON-LD), start-here, RSS, IndexNow; 64 prompt systems on guides |
| 2026-10-22 | Analytics live; entry pages turned into linked hubs (2 -> ~17 internal links); /go/ redirects + footer call-to-action; sitemap submitted to Google and Bing |
| 2026-10-23 | SEO waves 2-3: server-rendered guides, clean URLs, collection hubs, /method, speed work (home Lighthouse 49 -> 100), tool hubs, /compare, /best, /system-prompts, In-short answer blocks |
| 2026-10-23 | /flow page (zoned Sankey of the archive + gap analysis); footer nav mobile overflow fixed on all pages |
| 2026-10-29 | Small fixes: favicon set, Organization logo (og/logo.png, was a broken URL in JSON-LD on every page), Chrome traffic-advice file, links-page email opted out of Cloudflare obfuscation, catalog title + description rewritten for searchers; board deeper-dive picker fixed (api/deeper_dives.json); security.txt; weekly growth scorecard started |

## Findings and actions

| found | finding | action | status |
|---|---|---|---|
| 2026-10-29 | Indexing worked: sample 35/40 indexed (88%), sitemap read daily with 0 errors; impressions spiked to 950 on Oct 23 and settled ~400/day | Keep weekly; grow the inspection sample to 100 URLs once a month | open |
| 2026-10-29 | /catalog takes ~1,800 impressions/week but ~2 clicks: it ranks for thousands of one-off long-tail queries (many automated agent searches) at mid positions | Title + description rewritten (2026-10-29); next: watch catalog CTR, consider letting entry pages win those queries (they convert ~1.6%) | open |
| 2026-10-29 | Entry pages convert best: 9 clicks on 565 impressions | Strengthen entry pages (summary quality, titles); they are the long-tail landing pages | open |
| 2026-10-29 | Answer engines read heavily: OAI-SearchBot ×30, ClaudeBot ×13, ChatGPT live fetches ×3.7 in a week | Keep llms.txt/API fresh; track live-fetch counts (ChatGPT-User, Claude-User, Perplexity-User) as the 'cited by AI' proxy | open |
| 2026-10-29 | Nobody pulls /llms-full.txt in volume (<=9/week): no demand signal yet for paid data access | Leave pay-to-crawl parked; re-check monthly | open |
| 2026-10-29 | 105 human /go/ clicks/week with zero affiliate programs active; done-for-you 'service' 19 and DIY 21 lead | None until Victor decides on affiliates (stance: not the point yet) | open |
| 2026-10-29 | Cloudflare dashboard features add noise: Email Obfuscation script, bot-challenge scripts on every page | Victor: turn Email Obfuscation off in the Cloudflare dashboard (Scrape Shield) | open |
| 2026-10-29 | Bot pulls of /api/* fell 363 -> 164 in a week while page crawling rose (crawlers shifted to HTML pages) | Watch next audit; if it keeps falling, add /api/ to llms.txt prominence or an /api/ index page (Week-0 growth-plan item) | open |
| 2026-10-22 | Google had 0 impressions; URL-inspection sample 6/20 indexed, 13 'discovered, not indexed'; 847 entry pages were orphans | Indexing pass: linked entry hubs, collection hubs, sitemap + IndexNow | done (2026-10-23) |
| 2026-10-22 | Home Lighthouse mobile 49, catalog 55; LCP p75 2.5 s | Speed wave (slim catalog, prerender, self-hosted fonts, caching headers) | done (2026-10-23) |
| 2026-10-29 | favicon.ico 404 ~216/week; Organization logo og/default.png 404 (broken in JSON-LD on every page); /.well-known/traffic-advice 404 36/week; Cloudflare email-protection link 404 25/week | Fixed: favicon set + apple-touch-icon, og/logo.png, traffic-advice file, email_off on links page | done (2026-10-29) |
| 2026-10-29 | Most remaining 404s are hacker probes for .env, wp-admin, .git (correctly 404, nothing exposed) | None; tracked as 'real 404s' metric which excludes probes | done (2026-10-29) |
| 2026-10-29 | Board page fetched ../data/deeper_dives.json, which is never deployed (404, deeper-dive picker silently empty) | build_api.py now publishes slim site/api/deeper_dives.json; board fetches it | done (2026-10-29) |

## Metric definitions

| key | metric | better | definition |
|---|---|---|---|
| `visits_7d` | Real visits, 7 days | up | Cloudflare Web Analytics (browser beacon, so bots excluded) visits in the 7 days before the audit |
| `pageviews_7d` | Real page views, 7 days | up | Cloudflare Web Analytics page views, 7 days |
| `visits_28d` | Real visits, 28 days | up | Cloudflare Web Analytics visits, 28 days |
| `uniques_7d` | Edge unique visitors (sum of daily), 7 days | up | Cloudflare zone rollup; includes bots |
| `gsc_impr_7d` | Google impressions, 7 days | up | Search Console daily series, 7 days ending at the audit's Search Console window end |
| `gsc_clicks_7d` | Google clicks, 7 days | up | same window as above |
| `gsc_impr_28d` | Google impressions, 28 days | up | Search Console totals, 28-day window in the raw audit |
| `gsc_clicks_28d` | Google clicks, 28 days | up | Search Console totals, 28 days |
| `gsc_pos_28d` | Average Google position, 28 days | down | lower is better; blank when no impressions |
| `indexed_share` | Indexed share of URL-inspection sample | up | Submitted-and-indexed / inspected, URL Inspection API sample (sample size grows over time) |
| `gsc_pages_7d` | Pages with any impressions, 7 days | up | Search Console page dimension (extras) |
| `bot_google` | Googlebot hits, 7 days | up | UA class, Cloudflare sampled |
| `bot_bing` | Bingbot hits, 7 days | up |  |
| `bot_oai_search` | OpenAI search crawler (OAI-SearchBot), 7 days | up |  |
| `bot_chatgpt_user` | ChatGPT live fetches for a user (ChatGPT-User), 7 days | up |  |
| `bot_claude` | ClaudeBot hits, 7 days | up |  |
| `bot_claude_user` | Claude live fetches for a user (Claude-User), 7 days | up |  |
| `bot_perplexity` | PerplexityBot hits, 7 days | up |  |
| `bot_perplexity_user` | Perplexity live fetches (Perplexity-User), 7 days | up |  |
| `bot_gptbot` | GPTBot (OpenAI training crawler), 7 days | flat |  |
| `bot_amazon` | Amazonbot hits, 7 days | flat |  |
| `ai_llms_full` | Bot pulls of /llms-full.txt, 7 days | up | all non-browser classes; the paid-data demand signal |
| `ai_api` | Bot pulls of /api/*, 7 days | up | all non-browser classes |
| `lcp_p75_ms` | Largest Contentful Paint p75 (LCP) | down | time until the main content shows; Google's 'good' is under 2,500 ms |
| `inp_p75_ms` | Interaction to Next Paint p75 (INP) | down | click responsiveness; 'good' is under 200 ms |
| `cls_p75` | Cumulative Layout Shift p75 (CLS) | down | layout jumps; 'good' is under 0.1 |
| `go_human_7d` | Human /go/ clicks, 7 days | up | all /go/ slugs, browser user agents |
| `go_service_7d` | Human clicks on the done-for-you service link, 7 days | up |  |
| `go_diy_7d` | Human clicks on the DIY (GitHub skill) link, 7 days | up |  |
| `http_404_7d` | 404 responses, 7 days (sampled) | down | mostly scanner probes; see the 404 table for real ones |
| `http_404_real_7d` | 404s on non-probe paths, 7 days | down | 404s on site sections, asset folders and browser auto-files (REAL_RE); probe noise excluded |
| `threats_7d` | Cloudflare threats blocked, 7 days | flat |  |
| `sitemap_errors` | Sitemap errors in Search Console | down |  |
| `inv_entries` | Entries | up | site/catalog.json |
| `inv_guides` | Guides | up | site/guides/*.html |
| `inv_hubs_indexed` | Indexed tool hubs | up |  |
| `inv_sitemap_urls` | Sitemap URLs | up |  |

## Verification ledger

Every number above is recomputed from these files by `python3 scripts/analytics_scorecard.py --no-collect`.

| audit | raw file | sha256 (first 16) | extras file | sha256 (first 16) |
|---|---|---|---|---|
| 2026-10-22 | `data/analytics/2026-10-22.json` | `00a3a854e174d432` | none | |
| 2026-10-29 | `data/analytics/2026-10-29.json` | `72e2ca804daa7f29` | `data/analytics/2026-10-29.extras.json` | `d404fe952b9148bb` |

Daily Google series: `data/analytics/gsc_daily.json` (6 days, sha256 `d0c72679e2bbfa86`).
