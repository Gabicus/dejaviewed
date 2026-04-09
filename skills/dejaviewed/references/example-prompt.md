# Example Prompt to Invoke DejaViewed

Copy and customize this prompt. Replace the bracketed values with your own.

---

```
/dejaviewed

I have [NUMBER] Instagram saved posts across [NUMBER] collections that I want
turned into a searchable catalog site. Here's my setup:

## My Info
- IG handle: @[YOUR_HANDLE]
- Site title: [YOUR_TITLE] (or suggest one)
- Tagline: [YOUR_TAGLINE] (or suggest one)

## Collections
- [name1]: data/[name1]_urls.json ([N] posts — [topic description])
- [name2]: data/[name2]_urls.json ([N] posts — [topic description])

## URL Files
I've exported my saved post URLs into JSON files in `data/`. Each file looks like:
{"collection":"name","count":N,"urls":["https://www.instagram.com/p/XXX/", ...]}

## Chrome Profile
I've copied my Chrome profile to `.profile-copy/` (while Chrome was closed).
The Cookies DB is at `.profile-copy/Default/Cookies`.

## What I Want
1. Scrape every post for full captions, metadata, and thumbnails
2. Classify each post: what is it, what tools/repos/techniques does it mention
3. Give every card a title that answers "what is this and why did I save it"
   - Format: "Subject — value/angle" (e.g., "GeoSpy.ai — geolocate any photo from buildings/shadows")
   - NO bare names like "Claude Code" — always include the angle
4. Extract and display ALL links mentioned: github repos, tool websites, @handles, domains
5. Tier everything S/A/B/C based on how actionable and substantive it is
6. Write deep-dive guides for the S and A tier posts that have enough substance
7. Drop posts that are genuinely empty (pure hashtags, off-topic) but be generous — 10-20% max
8. Render a dark-mode static HTML site with:
   - Masonry 3-column card layout
   - Monospace font (SF Mono / Fira Code stack)
   - Sticky sidebar with multi-select category filters, tier pills, search
   - Creator bar chart (proportional width, colored by tier, click to scroll)
   - Thumbnails on each card (downloaded locally, NOT hotlinked)
   - Clickable link pills on every card for repos/tools/sites mentioned
   - Section grouping by category when viewing all
   - Deep-dive guide pages with confidence badges

## Additional Content (optional)
I also have curated resources beyond IG saves that should be merged in:
- [Describe any repos, tools, archive collections, guides you want included]
- These get "Browse" buttons instead of "Open post" buttons

## Hosting (optional)
I plan to host this at [URL] via [platform]. Static HTML is fine.
```

---

## What This Prompt Triggers

The skill will execute 10 phases automatically:

1. **Setup** — Create project structure, set brand constants
2. **Scrape** — Cookie-authenticated requests to each IG URL, extract full captions + metadata
3. **Classify** — LLM reads every caption, writes title + summary + type + tools + drop flag
4. **Curate** — Assign S/A/B/C tiers, group into thematic stacks
5. **Deep-Dive** — Write markdown guides for top-tier candidates
6. **Thumbnails** — Download og:image for every post to local directory
7. **Render** — Build static HTML site with all the design spec
8. **Browser Bookmarks** — Auto-detect Chrome/Firefox/Edge bookmarks, merge with dedup
9. **DejaViewed Page** — Build the summary/actions page with install sidebar + section jump pills + action cards
10. **Verify** — Run output checklist (titles, links, layout, security)

## Tips for Better Results

- **More collections = richer site.** Don't dump everything in one file. Theme your collections.
- **Describe your collections** in the prompt so the LLM knows the domain context when classifying.
- **If you have non-IG content** (repo lists, archive collections, tool bookmarks), include them. They add depth.
- **Review the drops.** Ask to see what was dropped and resurrect anything with a named subject.
- **Review the titles.** If any title is just a brand name without an angle, push back immediately. They should all answer "what + why."
