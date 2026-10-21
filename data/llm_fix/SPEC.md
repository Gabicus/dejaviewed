# LLM Enrichment Spec — DejaViewed catalog

You are enriching Instagram saves for a curated technical catalog (dejaviewed.dev). Input: `batch_NN.json`
(array of entries with caption, Whisper transcript, OCR of carousel slides, and the current heuristic
fields). Output: `out_NN.json` — array, one object per input entry, same order, schema below.

Read the WHOLE caption + transcript + ocr before judging. The transcript is usually where the real
content is; captions are often engagement bait ("comment GUIDE for the link").

## Output object (all keys required)
```json
{"id": "<copy input id>",
 "title": "Subject — angle",
 "summary": "1-3 sentences naming concrete things",
 "tier": "S|A|B|C",
 "type": "technique|tool|repo|guide|platform|resource|art|design|skill|demo|news|inspiration",
 "tags": ["3-8 short lowercase tags"],
 "domains": ["1-3 from the domain vocab"],
 "tools": ["canonical product names actually used/shown, e.g. Claude Code, ComfyUI, Blender, n8n"],
 "techniques": ["named methods, e.g. MCP server, LoRA fine-tuning, RAG, vibe coding"],
 "models": ["model names mentioned, e.g. Claude Fable 5, GPT-5.6, Flux, Sora"],
 "repos": ["github.com/... URLs or owner/repo mentioned"],
 "takeaways": ["2-4 bullets: the actionable 'so what'"],
 "links": ["URLs found in caption/transcript/ocr, resolved as far as text allows"],
 "drop": false, "drop_reason": ""}
```

## Title rules (the owner WILL complain if wrong)
- Format `Subject — angle` with a spaced em-dash. Subject = the actual tool/technique/concept. Angle =
  why it matters / what it enables. 40-90 chars.
- NEVER a bare name ("Claude Code"), never `@creator:` prefix, never the hook sentence, never clickbait.
- GOOD: `Claude Code — real-time terminal agent for any codebase`; `Heston Model — closed-form vol surface from 5 parameters`
- Bait caption + rich transcript → title from the transcript.
- Music / art posts: `Artist or piece — what makes it worth studying` (medium, technique, mood).

## Summary rules
1-3 sentences. Name the concrete tools/repos/techniques. No "In this video the creator…". What it is,
what it does, why you'd care. Second person is fine, mildly conspiratorial voice OK, no hype.

## Tier rubric (target mix per batch roughly S ≤15%, A ~30%, B ~40%, C rest)
- S: exceptional — deep, specific, linkable (a real repo/tool/paper), you'd build on it this week.
- A: solid, actionable, names real things, worth a guide.
- B: useful reference, one idea, or a good example without depth.
- C: thin, hype-only, promo, no subject, or sponsored content dressed as news.

## Type vocab
technique, tool, repo, guide, platform, resource, art, design, skill (merged with tutorial), demo,
news, inspiration. Use `art` for visual/music works, `inspiration` for mood/reference only.

## Domain vocab (pick 1-3)
agents, LLM, prompt engineering, software development, open source, video production, 3D, animation,
design, UI/UX, art, music, audio, finance/trading, quant, crypto, data science, security, OSINT,
marketing, education, creative coding, architecture, branding, hardware, robotics, productivity, news.

## Drop rules
Set `drop: true` ONLY for: no subject at all, pure self-promo with zero content, or exact duplicate of a
richer entry in the same batch. Target ≤10% drops. Sponsored "news" (e.g. the Vertus/Neurotopology ad)
is NOT a drop — keep it, tier C, say so in summary.

## Process
1. `python3 -c` to load the batch; work through every entry; write `out_NN.json` with `json.dump`
   (ensure_ascii=False, indent=1).
2. Validate: `python3 -c "import json;o=json.load(open('out_NN.json'));b=json.load(open('batch_NN.json'));assert [x['id'] for x in o]==[x['id'] for x in b];print(len(o))"`
3. Self-audit before finishing: no title < 14 chars, no title == post_id, no title containing
   "NEEDS ENRICHMENT", every entry has ≥1 tag and ≥1 domain, S-rate ≤ 20% in your batch.
Do not touch any other files. Do not run git. Report: per batch, count, tier mix, and the 3 best
entries (title only).
