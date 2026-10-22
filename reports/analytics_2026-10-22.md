# dejaviewed.dev analytics -- 2026-10-22

Generated 2026-10-22T16:41:51 by `scripts/analytics_report.py`. Raw numbers: `data/analytics/2026-10-22.json`.

## Missing setup

- missing: Google Search Console service-account key /home/victor/.config/google/dejaviewed-gsc.json -- do: verify the domain property in Search Console, create a service account with the Search Console API enabled, download its JSON key to that path, 'chmod 600 /home/victor/.config/google/dejaviewed-gsc.json', add the service-account email as a Full user on the property -- see data/analytics/SETUP.md steps 4-8

## Traffic (Cloudflare, edge)

| window | requests | page views (edge) | uniques (sum of daily) | MB served | cache ratio | threats |
|---|---|---|---|---|---|---|
| 7d | 18,415 | 11,303 | 2,014 | 477.6 | 0.0001 | 133 |
| 28d | 53,329 | 23,856 | 6,885 | 1,227.1 | 0.0001 | 305 |

### Status codes (28d)

| status | requests |
|---|---|
| 200 | 34,947 |
| 403 | 9,930 |
| 301 | 4,531 |
| 308 | 1,439 |
| 204 | 1,229 |
| 405 | 627 |
| 404 | 210 |
| 304 | 174 |
| 499 | 128 |
| 206 | 113 |
| 500 | 1 |

### Countries (edge requests, top 15)

| country | requests |
|---|---|
| US | 12,766 |
| CN | 5,766 |
| NL | 4,395 |
| FR | 3,600 |
| SG | 3,118 |
| PL | 3,107 |
| DE | 3,106 |
| TW | 1,879 |
| IN | 1,595 |
| GB | 1,515 |
| AU | 1,446 |
| BR | 1,399 |
| JP | 1,138 |
| CA | 1,022 |
| KR | 1,021 |

### Top pages (7d, sampled; days: 7)

| host | path | requests |
|---|---|---|
| dejaviewed.dev | / | 941 |
| dejaviewed.dev | /cdn-cgi/rum | 479 |
| dejaviewed.dev | /shared.js | 292 |
| dejaviewed.dev | /robots.txt | 228 |
| dejaviewed.dev | /cdn-cgi/challenge-platform/scripts/jsd/main.js | 213 |
| dejaviewed.dev | /shared.css | 211 |
| dejaviewed.dev | /favicon.ico | 181 |
| dejaviewed.dev | /wp-admin/install.php | 175 |
| dejaviewed.dev | /cdn-cgi/challenge-platform/h/b/scripts/jsd/d2d3316b729e/main.js | 156 |
| dejaviewed.dev | /catalog.js | 146 |
| dejaviewed.dev | /cdn-cgi/content | 128 |
| dejaviewed.dev | /cdn-cgi/scripts/5c5dd728/cloudflare-static/email-decode.min.js | 121 |
| dejaviewed.dev | /deep_dives.js | 117 |
| dejaviewed.dev:443 | / | 66 |
| dejaviewed.dev | /.env | 62 |
| dejaviewed.dev | /.git/config | 61 |
| dejaviewed.dev | /guides/ai-trading-agents.html | 52 |
| dejaviewed.dev | /wp-login.php | 49 |
| dejaviewed.dev | /e/CzWiXY2PCrr.html | 48 |
| dejaviewed.dev | /e/DIQ4GdHI4ZH.html | 48 |
| dejaviewed.dev | /guides/avellaneda-stoikov-and-hawkes.html | 48 |
| dejaviewed.dev | /e/DYQObkHRzmE.html | 48 |
| dejaviewed.dev | /e/685f44ff3d7b | 48 |
| dejaviewed.dev | /e/CvSEQAft0zm.html | 48 |
| dejaviewed.dev | /e/DIO37tGNHiD.html | 48 |
| dejaviewed.dev | /.env.local | 41 |
| dejaviewed.dev | /.env.development | 40 |
| dejaviewed.dev | /guides/n8n-mcp-and-obsidian-skills.html | 38 |
| dejaviewed.dev | /e/DYShNwIDzTK | 36 |
| dejaviewed.dev | /config.js | 36 |

### Human vs bot (7d, by user-agent class)

Human/browser share of requests: **0.5783**

## AI crawlers (7d)

| crawler | all hits | /api/ | /llms.txt | /llms-full.txt | /prompts | /guides/* | /robots.txt | /sitemap.xml |
|---|---|---|---|---|---|---|---|---|
| human/browser | 11,010 | 140 | 24 | 0 | 0 | 564 | 52 | 4 |
| other-bot | 3,997 | 149 | 1 | 0 | 0 | 178 | 61 | 5 |
| scanner | 2,375 | 109 | 0 | 0 | 0 | 0 | 0 | 0 |
| empty-UA | 528 | 6 | 0 | 0 | 0 | 0 | 1 | 1 |
| Googlebot | 191 | 2 | 0 | 0 | 0 | 18 | 34 | 0 |
| ChatGPT-User | 119 | 6 | 0 | 0 | 0 | 15 | 0 | 0 |
| ClaudeBot | 116 | 4 | 0 | 0 | 0 | 1 | 1 | 0 |
| DuckDuckBot | 90 | 4 | 0 | 0 | 0 | 1 | 1 | 0 |
| Amazonbot | 79 | 1 | 1 | 0 | 0 | 57 | 0 | 0 |
| PerplexityBot | 79 | 8 | 0 | 0 | 0 | 13 | 19 | 0 |
| Bingbot | 75 | 2 | 0 | 0 | 0 | 16 | 5 | 1 |
| Bytespider | 57 | 3 | 0 | 0 | 0 | 2 | 16 | 0 |
| GPTBot | 57 | 0 | 0 | 0 | 0 | 0 | 2 | 0 |
| OAI-SearchBot | 56 | 0 | 0 | 0 | 0 | 3 | 21 | 0 |
| meta-externalagent | 53 | 1 | 0 | 0 | 0 | 0 | 7 | 0 |
| Applebot | 45 | 0 | 0 | 0 | 0 | 0 | 8 | 0 |
| CCBot | 45 | 2 | 0 | 0 | 0 | 0 | 0 | 1 |
| Perplexity-User | 25 | 1 | 0 | 0 | 0 | 0 | 0 | 0 |
| cohere-ai | 22 | 2 | 0 | 0 | 0 | 0 | 0 | 0 |
| YandexBot | 17 | 1 | 0 | 0 | 0 | 1 | 0 | 0 |
| Claude-User | 2 | 0 | 0 | 0 | 0 | 2 | 0 | 0 |

### Top user agents (7d)

| class | requests | user agent |
|---|---|---|
| other-bot | 2,327 | curl/8.7.1 |
| human/browser | 2,090 | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/151.0.0.0 Safari/537.3 |
| scanner | 1,926 | TLM-Audit-Scanner/2.0 |
| human/browser | 1,451 | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Safari/537.3 |
| human/browser | 1,161 | Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari |
| human/browser | 1,015 | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.3 |
| human/browser | 765 | Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko, Yokohama Institute of I |
| empty-UA | 528 |  |
| human/browser | 448 | Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/155.0.0.0 Safari/537.36 |
| other-bot | 364 | Mozilla/5.0 (compatible; AhrefsBot/7.0; +http://ahrefs.com/robot/) |
| human/browser | 358 | Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 |
| other-bot | 316 | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 |
| human/browser | 294 | Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 |
| human/browser | 243 | Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari |
| human/browser | 184 | Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/153.0.0.0 Safari |
| human/browser | 181 | Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari |
| scanner | 175 | http://dejaviewed.dev/wp-admin/install.php?step=1 |
| human/browser | 172 | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.3 |
| other-bot | 163 | Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; HubSpot Crawler; +https://www.hubspot.com) Chro |
| human/browser | 130 | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.3 |
| human/browser | 121 | Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0 |
| Googlebot | 105 | Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html) |
| ChatGPT-User | 101 | Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko); compatible; ChatGPT-User/1.0; +https://openai.com/bot |
| human/browser | 99 | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.3 |
| scanner | 93 | Mozilla/5.0 (l9scan/2.0.9333e2030323e27363e2237313; +https://leakix.net) |
| scanner | 92 | Mozilla/5.0 (l9scan/2.0.130313e22383e21323e2430313; +https://leakix.net) |
| other-bot | 89 | Mozilla/5.0 AppleWebKit/537.36 (KHTML, like Gecko; compatible; Reflectionbot/1.0; +https://reflection.ai/bot)  |
| human/browser | 80 | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.3 |
| human/browser | 80 | Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.3 |
| other-bot | 80 | Go-http-client/1.1 |

### Status x cache (7d, sampled)

| status | cache | requests |
|---|---|---|
| 200 | dynamic | 10,384 |
| 200 | miss | 2,013 |
| 301 | dynamic | 1,636 |
| 200 | revalidated | 1,027 |
| 308 | dynamic | 914 |
| 403 | none | 814 |
| 200 | none | 573 |
| 204 | none | 479 |
| 200 | expired | 395 |
| 302 | none | 213 |
| 405 | dynamic | 129 |
| 301 | miss | 129 |
| 304 | revalidated | 75 |
| 404 | none | 74 |
| 304 | miss | 59 |
| 499 | none | 50 |
| 206 | miss | 19 |
| 206 | revalidated | 18 |
| 301 | expired | 9 |
| 404 | bypass | 9 |

## Web Analytics (real visitors)

**7d:** 290 page views, 280 visits

**28d:** 710 page views, 520 visits

| path | page views | visits |
|---|---|---|
| / | 220 | 210 |
| /doetug/ | 110 | 0 |
| /guides/onyx-self-hosted-ai | 40 | 40 |
| /guides/llms-txt-standard | 30 | 30 |
| /guides/gemini-cli | 30 | 30 |
| /guides/quant-project-ideas-list | 20 | 20 |
| /links/ | 20 | 20 |
| /graph-cosmos | 20 | 0 |
| /guides/hunyuan3d-2 | 20 | 20 |
| /graph | 20 | 10 |
| /guides/creative-tech-stack-2026 | 20 | 0 |
| /guides/claude-code-parallel-worktrees | 20 | 20 |
| /guides/blender-mcp-tripo-pipeline | 10 | 10 |
| /guides/l1b3rt4s-jailbreak-repo | 10 | 10 |
| /guides/mediapipe-touchdesigner-pipeline | 10 | 10 |
| /guides/boris-cherny-claude-md | 10 | 10 |
| /guides/claude-code-leaked-system-prompt | 10 | 10 |
| /about/ | 10 | 10 |
| /guides/polymarket-weather-trading | 10 | 10 |
| /art-ai | 10 | 10 |
| /guides/claude-mastery | 10 | 10 |
| /board | 10 | 10 |
| /guides/ | 10 | 0 |
| /ai_art | 10 | 10 |
| /deeper/deeper-insight-mediapipe-touchdesigner-pipeline | 10 | 0 |
| /guides/n8n-mcp-and-obsidian-skills | 10 | 10 |

| country | page views |
|---|---|
| US | 270 |
| CN | 270 |
| HK | 60 |
| DE | 30 |
| GB | 30 |
| IN | 20 |
| RO | 10 |
| IE | 10 |
| BR | 10 |

### Web Vitals

| window | samples | LCP p75 | CLS p75 | INP p75 |
|---|---|---|---|---|
| 7d | 198 | 2,556,000 | 0.0960 | 344,000 |
| 28d | 520 | 2,948,000 | 0.0200 | 296,000 |

### Cloudflare query errors

- `bot_fields`: zone '372eab20bd0cb270a64c9a4d346a6f15' does not have access to the field 'botscoresrcname' from the path (bot-management fields are often Enterprise-only; UA classification used instead)

## Deltas vs previous report

_first report -- no prior JSON in data/analytics/_

