# Analytics evaluation, Oct 22 baseline → Oct 29 (first full week after the SEO, monetize and flow work)

Sources: `reports/analytics_2026-10-29.md` + `data/analytics/2026-10-29.json` (run: `python3 scripts/analytics_report.py --inspect 40`, 2026-10-29), baseline `reports/analytics_2026-10-22.md`. Daily Search Console rows pulled 2026-10-29 with `searchanalytics.query` on `sc-domain:dejaviewed.dev`, dimensions `date` / `page`, 2026-10-15..2026-10-28 (Google data ends 2026-10-27).

## Headline numbers (7-day windows)

| metric | Oct 22 | Oct 29 | change |
|---|---|---|---|
| Real visitor page views (Cloudflare Web Analytics) | 266 | 538 | +102% |
| Real visits | 252 | 407 | +62% |
| Google impressions (28d) | 0 | 2,685 | new |
| Google clicks (28d) | 0 | 12 | new |
| Average Google position | n/a | 9.0 | |
| Indexed, URL Inspection sample | 6 of 20 | 35 of 40 | 30% → 88% |
| Googlebot hits | 178 | 5,070 | ×28 |
| OpenAI search crawler (OAI-SearchBot) | 55 | 1,661 | ×30 |
| ClaudeBot | 116 | 1,496 | ×13 |
| ChatGPT-User (live fetches for a user's question) | 117 | 429 | ×3.7 |
| Largest Contentful Paint p75 (LCP) | 2.5 s | 0.99 s | faster |
| Cumulative Layout Shift p75 (CLS) | 0.096 | 0.012 | better |
| Interaction to Next Paint p75 (INP) | 312 ms | 216 ms | better |
| /go/ outbound clicks, human, 7d | 0 | 105 (diy 21, service 19, notion 10, vercel 8 …) | new |

## Google, by day

| date | clicks | impressions | avg position |
|---|---|---|---|
| 10-22 | 0 | 46 | 12.7 |
| 10-23 | 0 | 950 | 6.3 |
| 10-24 | 4 | 880 | 8.5 |
| 10-25 | 2 | 394 | 12.7 |
| 10-26 | 6 | 415 | 12.2 |
| 10-27 | 4 | 360 | 11.7 |

Impressions by section (Oct 15–28): /catalog 1,861 (2 clicks) · /e/ entry pages 565 (9 clicks) · /guides/ 495 (3) · /deeper/ 106 · /best/ 26 · /compare/ 6 · /flow 3. 277 distinct pages earned impressions.

## Reading

- Indexing worked: the sitemap is read daily with 0 errors and the sample went from 30% to 88% indexed. The Oct 23 spike is Google's first full pass after the SEO waves; it settled at ~400 impressions/day.
- Clicks are tiny but now daily (2–6/day). Entry pages convert best (9 clicks on 565 impressions); /catalog gets most impressions but almost no clicks, because it matches thousands of one-off long-tail queries (many are automated agent searches with operators) at mid positions.
- Answer engines are reading the site hard: OpenAI's search crawler and ClaudeBot each ~1,500 hits/week; ChatGPT fetched pages live 429 times. Nobody pulls /llms-full.txt in volume yet (≤9 hits), so the pay-to-crawl demand signal is still absent.
- Human traffic doubled but is still small (~60 visits/day). /doetug/ (the Department of Energy Tableau User Group deck) took 110 views.
- /go/ clicks exist now even with no affiliate program active — the done-for-you CTA ("service", 19) and DIY link (21) lead.
- Noise: 181 /wp-admin/install.php probes and 255 /favicon.ico 404s per week; the favicon is open item 3 in the primer.

## Next measurements
Re-run Mondays. Watch: catalog CTR (title/description rewrite candidate), entry-page clicks, indexed share on a 100-URL sample, llms-full.txt and /api/ pulls by AI crawlers.
