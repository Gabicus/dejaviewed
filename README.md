# DejaViewed

**"You've saved this before."**

Turn your saved posts and bookmarks from **any platform** into a searchable, curated dark-mode catalog site with an auto-generated Action Plan — powered by Claude Code.

You scroll, you tap save, you swear you'll come back. You don't. DejaViewed hands the whole pile to Claude: every save gets read, classified, tiered, and — for the ones worth the dig — turned into a real deep-dive guide with the links the creator wouldn't give you. Then it tells you what to actually **do** with all of it.

**Live demo:** [dejaviewed.dev](https://dejaviewed.dev)

## Install

```bash
# Full plugin install
git clone git@github.com:Gabicus/dejaviewed.git ~/.claude/plugins/dejaviewed

# Or skill-only install
git clone git@github.com:Gabicus/dejaviewed.git /tmp/dv && cp -r /tmp/dv/skills/dejaviewed ~/.claude/skills/
```

## Use

```bash
/dejaviewed
```

Or with arguments:

```bash
/dejaviewed --urls saved_urls.json --title "My AI Bookmarks" --handle "@myhandle"
```

## Supported Sources

| Source | Auth Required | Status |
|--------|---------------|--------|
| **Instagram Saves** | Chrome profile copy | ✅ Built |
| **Chrome Bookmarks** | None (local file) | ✅ Built |
| **Firefox Bookmarks** | None (local file) | ✅ Built |
| **Edge Bookmarks** | None (local file) | ✅ Built |
| **TikTok Saves** | Chrome profile copy | 🔜 Planned |
| **Twitter/X Bookmarks** | API bearer token | 🔜 Planned |
| **Pinterest Boards** | Chrome profile / API | 🔜 Planned |
| **Reddit Saved** | OAuth token | 🔜 Planned |
| **YouTube Watch Later** | Chrome profile / API | 🔜 Planned |

## What It Does

| Phase | What happens |
|-------|-------------|
| **Ingest** | Pull saves/bookmarks from any supported source into a unified format |
| **Classify** | Claude reads each item, writes a "Subject — why I saved it" title, summary, type, tools/repos mentioned |
| **Links** | Extracts every outbound URL, GitHub repo, tool website, @mention |
| **Tier** | S/A/B/C ranking based on how actionable and substantive each item is |
| **Deep-Dive** | Markdown guides for the top-tier items — the research the creator didn't give you |
| **Thumbnails** | Downloads images locally (platform CDN URLs expire — never hotlink) |
| **Action Plan** | Auto-generates "what to DO with all this" — clone commands, install commands, guides to read, techniques to try |
| **Render** | Static HTML: masonry layout, category filters, creator bar chart, clickable links, search, action plan page |

## What You Get

A static HTML site with:

- **Masonry 3-column card layout** — cards size to content, not forced grids
- **Dark mono theme** — SF Mono / Fira Code, dark panels, gradient accents
- **Sticky sidebar** — multi-select category filters, tier pills, full-text search
- **Creator bar chart** — proportional bars colored by tier, click a segment to jump to that card
- **Clickable links on every card** — repos, tools, websites, @handles extracted from captions
- **Thumbnails** — downloaded locally, not hotlinked
- **Deep-dive guide pages** — full markdown with confidence badges
- **Per-collection pages** — if you have multiple saved folders
- **Action Plan page** — the killer feature:
  - **Clone These Repos** — S/A tier repos with `git clone` commands (click to copy)
  - **Install These Tools** — pip/npm/brew one-liners
  - **Read These Guides** — deep-dives we wrote, with confidence badges
  - **Try These Techniques** — workflows you saved but haven't tried
  - **Bookmark These Platforms** — services worth keeping
  - **Design & Art Resources** — archives, collections, inspiration
  - **Save Profile** — witty personality assessment of your hoarding habits

## Browser Bookmarks (No Auth Needed)

The easiest way to start — no cookies or API tokens required:

```bash
# Extract Chrome bookmarks
python3 adapters/chrome_bookmarks.py --out data/chrome_bookmarks.jsonl

# Extract Firefox bookmarks
python3 adapters/firefox_bookmarks.py --out data/firefox_bookmarks.jsonl

# Merge all sources (dedup by URL)
python3 adapters/merge_sources.py \
  --sources data/catalog.jsonl data/chrome_bookmarks.jsonl \
  --out data/catalog_merged.jsonl --dedup-by url
```

Cross-source dedup: if the same URL appears from Chrome AND Instagram, the merger keeps the richer record and adds `sources: ["instagram", "chrome"]`.

## Prerequisites

**For Instagram scraping:**
1. Instagram saved post URLs as JSON: `{"collection":"name","count":N,"urls":[...]}`
2. Copied Chrome profile with active IG session at `.profile-copy/Default/Cookies`
3. Python 3.10+ with `requests` and `browser_cookie3`

**For browser bookmarks only:**
1. Python 3.10+ (no additional packages needed)
2. Chrome, Firefox, or Edge installed with bookmarks

## Example Prompt

See [skills/dejaviewed/references/example-prompt.md](skills/dejaviewed/references/example-prompt.md) for a ready-to-copy template.

## Security

- Cookie values are NEVER printed, logged, or written to any output
- All card rendering via DOM createElement — no innerHTML (DOMPurify for guide markdown only)
- Platform CDN thumbnails downloaded locally, not hotlinked
- Browser bookmark adapters ONLY read bookmarks — never history, passwords, or cookies

## Credits

Built by [@6ab3](https://instagram.com/6ab3) with Claude Code.

## License

MIT
