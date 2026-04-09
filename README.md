# DejaViewed

**"You've saved this before."**

Turn your Instagram saved posts into a searchable, curated dark-mode catalog site — powered by Claude Code.

You scroll, you tap save, you swear you'll come back. You don't. DejaViewed hands the whole pile to Claude: every save gets read, classified, tiered, and — for the ones worth the dig — turned into a real deep-dive guide with the links the creator wouldn't give you.

## Install

```bash
claude plugin add github:Gabicus/dejaviewed
```

## Use

```bash
/dejaviewed
```

Or with arguments:

```bash
/dejaviewed --urls saved_urls.json --title "My AI Bookmarks" --handle "@myhandle"
```

## What It Does

| Phase | What happens |
|-------|-------------|
| **Scrape** | Cookie-authenticated requests pull full captions, metadata, thumbnails from every IG saved post |
| **Classify** | Claude reads each caption, writes a "Subject — why I saved it" title, summary, type, tools/repos mentioned |
| **Links** | Extracts every outbound URL, GitHub repo, tool website, @mention from captions |
| **Tier** | S/A/B/C ranking based on how actionable and substantive each post is |
| **Deep-Dive** | Markdown guides for the top-tier posts — the research the creator didn't give you |
| **Thumbnails** | Downloads og:image locally (IG CDN URLs expire — never hotlink) |
| **Render** | Static HTML: masonry layout, category filters, creator bar chart, clickable links, search |

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

## Prerequisites

1. **Instagram saved post URLs** as JSON: `{"collection":"name","count":N,"urls":[...]}`
2. **Copied Chrome profile** with active IG session at `.profile-copy/Default/Cookies`
3. **Python 3.10+** with `requests` and `browser_cookie3`

## Example Prompt

See [skills/dejaviewed/references/example-prompt.md](skills/dejaviewed/references/example-prompt.md) for a ready-to-copy template.

## Security

- Cookie values are NEVER printed, logged, or written to any output
- All card rendering via DOM createElement — no innerHTML (DOMPurify for guide markdown only)
- IG CDN thumbnails downloaded locally, not hotlinked

## Credits

Built by [@6ab3](https://instagram.com/6ab3) with Claude Code.

## License

MIT
