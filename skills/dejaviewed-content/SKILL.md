---
name: dejaviewed-content
description: Turn DejaViewed guides and deeper dives into standalone Instagram content — carousel slides, captions with credits and hashtags, reel scripts and optional reel videos — and run the posting loop (next-7 queue, posted/unposted status). Triggers: "content kit", "make posts from the guides", "carousel for <guide>", "reel script", "what should I post next", "dejaviewed content".
---

# /dejaviewed-content — the posting loop

The catalog is the source; every guide and deeper dive becomes its own post. One generator, one queue,
one status file. Runs after a `/dejaviewed` rebuild (needs `data/prompt_systems.json` and `data/deep_dives.json`).

## Commands

```bash
python3 scripts/content_kit.py --all                 # every curated dive + hand-written guide → content/<slug>/
python3 scripts/content_kit.py --slug <slug> --force  # regenerate one
python3 scripts/content_kit.py --slug <slug> --video  # + reel.mp4 (1080×1920, ~3.2 s/slide, no audio)
```

Output per slug: `slides.json` (7–9 slides + alt text), `slide_NN.png` (1080×1350), `caption.md`
(≤2,000 chars, hook, summary, "save this", @creator credits, link line, 15–20 hashtags), `reel_script.md`
(30–45 s, hook/3 beats/CTA, on-screen text), optional `reel.mp4`. Queue: `content/INDEX.md` ("Next 7 to
post" = unposted, highest quality first). Status: `content/status.json` `{slug: "unposted" | "posted:<date>"}`.

PNG/MP4 are gitignored (regenerable); json/md/templates are committed.

## Laws

1. **Text only from data.** Every slide line comes from the prompt pack / dive / catalog. No invented
   numbers or claims. Creators credited by @handle on the content they made.
2. **No superlatives** ("best ever", "ultimate"). Hook = the promise, stated plainly.
3. **Readable on a phone:** ≥44 px body, ≥72 px titles, text never touches the edges — open 3 PNGs with the
   Read tool after any template change.
4. **One Playwright browser per run**; `--force` to regenerate; idempotent otherwise.
5. **Posting is manual** (Instagram API posting for personal accounts is not worth the approval friction).
   The loop: open `content/INDEX.md` → take the top of "Next 7" → post slides + caption → set
   `status.json[slug] = "posted:YYYY-MM-DD"` → regenerate INDEX. One post a day keeps 63 kits going two months;
   every new curated dive adds a kit automatically.
6. **Measure:** when Cloudflare Web Analytics is on, compare `/guides/<slug>` traffic the week after a post
   with the week before (`scripts/analytics_report.py`). Keep the formats that move the needle.

## Templates

`scripts/content_templates/carousel.html` (1080×1350) and `reel.html` (1080×1920): dark DejaViewed brand
(shared.css tokens, Inter + JetBrains Mono, violet→pink accent), slide types hook / point / list / quote /
steps / cta, footer `dejaviewed.dev/guides/<slug>` on every slide. Change the look here, then `--all --force`.

## Ideas queue (not built)

- Voiceover for reels: TTS from `reel_script.md` + ffmpeg mux (ElevenLabs or local Piper).
- Threads/X: 5-post thread per dive from the same slides.json.
- Weekly digest post: "7 things I saved this week" from `data/entries.parquet` newest rows.
