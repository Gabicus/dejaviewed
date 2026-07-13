# My DejaViewed Instance — Deployment Overlay (TEMPLATE)

Copy this file to `references/site-deployment.md` in YOUR installed copy of the skill
(e.g. `~/.claude/skills/dejaviewed/references/site-deployment.md`) and fill it in.

**How it works:** The DejaViewed skill is generic — it builds a local catalog site for
anyone. When `references/site-deployment.md` exists in your installed skill, the skill
runs in **Operator Mode**: it knows YOUR hosting, YOUR collections, and YOUR deploy
workflow, and will push updates to YOUR site when you ask it to deploy.
Without this file, the skill runs in **Public Mode**: it builds everything locally
and offers hosting options, but never assumes a deploy target.

Do NOT commit your filled-in copy to a public repo — it describes your personal
infrastructure.

---

## Hosting

- Provider: <Cloudflare Pages | GitHub Pages | Netlify | Vercel | local only>
- Deploy trigger: <e.g. push to main, deploy script, manual upload>
- Output dir: `site/`
- Custom domain: <yourdomain.tld or none>
- Repo: <your repo URL or "local only">

## Collections

<List your collection names here — the skill uses these for scoped operations>

## Current State

<Optional: entry counts, coverage stats. Update after big pipeline runs so the
skill knows what "done" looks like for your instance.>

## Deploy Workflow

1. Run pipeline steps as needed (scrape, enrich, deep dives, rebuild)
2. <your commit/push/upload steps>

## Known Gaps (expected, not bugs)

<Entries that will never have captions/transcripts/thumbnails and why —
prevents the skill from re-reporting them as problems every session.>
