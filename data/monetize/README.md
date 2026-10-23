# Monetize layer

Files:

| file | what |
|---|---|
| `affiliates.json` | one row per tool: `tool`, `aliases`, `status` (`pending` / `active` / `skip`), `program`, `signup_url`, `affiliate_url`, `official_url`, `commission`, `notes`, `recommended_rank`, `official_check` |
| `config.json` | `service_url`, `diy_url`, `tip_jar_url`, `sponsors_url`, `prompt_pack_url`, `disclosure_footer`, `inline_label` |
| `affiliates_research.json` | the research the config was seeded from (62 tools, ranked first 10, placement bans) |
| `../../scripts/build_monetize.py` | applies all of it to `site/` (idempotent; runs as the `monetize` phase right after `seo` in `scripts/rebuild.sh`) |

## How it works

- Every non-skip tool gets a stable redirect `/go/<slug>` in `site/_redirects` (Cloudflare Pages format).
  `pending` points at `official_url`; `active` points at `affiliate_url`. The page links never change
  when a program is activated, only the redirect target does.
- Tool names in guide Tools lines and "Key tools and resources", deeper-page tool pills, and the entry
  "5k ft — Tools" line are linked to `/go/<slug>` when they match `tool` or an `aliases` entry exactly
  (case-insensitive). Pending: `rel="noopener"`, no label. Active: `rel="sponsored nofollow noopener"`
  plus a small `affiliate link` label.
- Every public page gets a footer block: DIY (free skill on GitHub) and done-for-you (contact) links,
  "Support this archive" only when `tip_jar_url` / `sponsors_url` are set, and the disclosure sentence
  only when at least one tool is `active`. Private pages (admin, rate, legacy, robots-disallowed) get none.
- `prompts.html` gets "All N prompt systems are free here and as JSON", plus a pack link only when
  `prompt_pack_url` is set. `start-here.html` gets "Want this for your own saves?" from
  `scripts/build_start_here.py`.
- Nothing with an empty URL renders and no empty redirect is written.

## Activate a program

1. Sign up at the row's `signup_url` (ranked order below). Read the terms page once you have an account:
   PartnerStack and Impact terms (ElevenLabs, Webflow, Lovable, Coursera, Skillshare, Setapp, Udemy)
   were not readable without one.
2. Paste the tracking link you are given into `affiliate_url`.
3. Set `status` to `active`.
4. Run `python3 scripts/build_monetize.py` (or the whole `scripts/rebuild.sh`), then
   `python3 scripts/build_monetize.py --check` (must say 0 files would change) and
   `python3 scripts/check_links.py --internal` (0 broken).
5. Commit and push `data/monetize/affiliates.json`, `site/_redirects` and the changed pages. Cloudflare
   Pages deploys from `main`.

The first active program automatically turns on the footer disclosure and the inline label everywhere.
To pause a program, set it back to `pending` (links stay, they go to the official site again).
`skip` removes the redirect and every link for that tool.

To add a tool: add a row with a lowercase-dash slug, `status: "pending"` and a working `official_url`.
Add aliases for every spelling the catalog uses (see `site/api/tools.json`).

Recommended order (from the research; rates change, recheck on the signup page):

| rank | tool | commission (as researched) | note |
|---|---|---|---|
| 1 | ElevenLabs | 22% recurring for 12 months | PartnerStack, open to bloggers, low payout minimum |
| 2 | Higgsfield | up to 25% recurring for 12 months | Impact; never on coupon pages, never paid ads |
| 3 | n8n | 30% of Cloud revenue for 12 months | no paid ad campaigns |
| 4 | Runway | $15 per paid subscriber | code-based, fits the Instagram content kits too |
| 5 | Lovable | up to $100 per first-time subscriber | Impact |
| 6 | Framer | 50% for 12 months, 90-day cookie | high payout minimum |
| 7 | Webflow | 50% of first subscription up to 12 months | PartnerStack |
| 8 | Raycast | 30% of Pro payments | Rewardful |
| 9 | Coursera | 15% to 45% | Impact |
| 10 | TradingView | $10 to $400 flat per new subscriber | no brand-keyword bidding |

Lovable, Framer, Webflow, Raycast and Coursera are not tagged on any catalog entry today, so they only
earn once a guide or entry names them. Polymarket is `skip` (wagering-adjacent, jurisdiction-gated).
Notion's program is closed to new affiliates and Blender's listed program is the Superhive marketplace,
not Blender itself: both stay `pending` as plain measured outbound links. Never paste a Superhive link
into the Blender row.

## Rules (FTC and program terms)

- **Disclosure.** Any page that carries an active affiliate link must disclose it clearly. This layer
  does it twice: the inline `affiliate link` label next to the link, and the footer sentence. Do not
  remove either while any tool is active. Never write copy that implies a tool is recommended because
  it pays; inclusion and ranking come from the catalog.
- **No paid ads** pointing at affiliate links (Higgsfield, Framer, n8n ban it).
- **No brand bidding**: never buy search ads on a program's brand name or typos (Higgsfield, Framer,
  TradingView).
- **No coupon or cashback framing**: no "promo code", "discount", "deal" pages built around a link
  (Higgsfield, Framer). Runway's audience discount is part of its code program, state it plainly if used.
- **No spam or unsolicited messaging** with links (Framer, TradingView).
- Links carry `rel="sponsored nofollow"` when active, as Google requires for paid links.

## Reading clicks

`scripts/analytics_report.py` adds an "Outbound (/go/) clicks (7d/28d)" table to the report: hits on
each `/go/<slug>` path from Cloudflare's edge logs, split into human (browser user agent) and bot.
Counts are sampled estimates; days outside the Cloudflare plan's retention are left out and the table
says how many days it covers. Pending tools still count, so the table shows which programs are worth
signing up for before any is active. `/go/diy` and `/go/service` measure the two CTAs.

Commands:

```
python3 scripts/build_monetize.py            # apply
python3 scripts/build_monetize.py --check    # dry run, exit 1 if anything would change
python3 scripts/build_monetize.py --report   # status counts + links per tool + CTA state
```
