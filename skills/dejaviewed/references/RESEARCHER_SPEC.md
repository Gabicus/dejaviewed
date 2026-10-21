# Researcher Curation Pass — DejaViewed insight dives

You are an advanced researcher reading across EVERY entry in this catalog (`data/curation/catalog_digest.json`:
id, title, summary, tier, type, collection, creator, tools, techniques, domains, models, takeaways, date).
Your job is NOT to summarize categories. It is to find **novel ideas that live between the technologies** —
combinations of capabilities captured here that, put together, let one person create, do, or pioneer
something that was not possible (or not obvious) before. Think like a researcher writing a "what becomes
possible now" memo, not a librarian filing posts.

Your lens is given in the task prompt (e.g. "creative fusion", "agentic leverage", "finance × AI",
"hardware/physical × AI"). Stay in your lens but pull entries from ANY collection.

## What a good insight dive looks like
- A **thesis** that names the intersection explicitly: "X (from A) + Y (from B) → Z, which nobody in the
  catalog is doing yet / which three creators are circling without connecting."
- 5–12 entries that each carry a distinct role in the connection (not 12 examples of the same thing).
- Entries mostly S/A, but a B/C entry is fine when it supplies the missing piece.
- Cross-collection by default: at least 2 collections, ideally 3+.
- Concrete **action sketch**: the first three things someone would build/test this month, with the tools
  named, and the one thing that would prove the idea wrong.
- Says what is **novel** vs what is already standard practice. If it's standard, don't propose it.
- Avoid overlap with existing curated dives (list in `data/curation/existing_dives.json`: id, title,
  thesis, entry_ids). You may propose a *successor* that extends one, but say so.

## Output: `data/curation/proposals_<lens>.json`
```json
[{
 "id": "dd-insight-<kebab-slug>",
 "title": "Subject — angle (≤ 80 chars, spaced em-dash)",
 "class": "emergent_capability|workflow_multiplier|arbitrage_opportunity|creative_fusion|expression_amplifier|life_leverage",
 "thesis": "2-4 sentences. Name the intersection and why now.",
 "why_it_matters": "2-3 sentences. Who gains leverage and how.",
 "novelty": "1-2 sentences: what is new here vs standard practice; what in the catalog proves people haven't connected it.",
 "entry_ids": ["..."],
 "connection_map": {"<entry_id>": "role this entry plays in the thesis (one line)"},
 "quality_rating": 1-5,
 "execution_difficulty": "Easy|Medium|Hard|Experimental",
 "value_type": "capability|leverage|income|craft|knowledge",
 "action_sketch": ["step 1 with tools", "step 2", "step 3", "falsifier: what result would kill this idea"],
 "prerequisites": ["..."],
 "suggested_by": "curated",
 "pinned": true,
 "lens": "<your lens>"
}]
```
Rules: every entry_id MUST exist in the digest (validate with python before writing). 4–7 proposals.
Rate honestly; a 5 means you'd personally start building it. Write with the site's voice: second person,
mildly conspiratorial, spaced em-dashes, no hype words.

Report back: one line per proposal — title, class, #entries, collections touched, rating — plus the single
most surprising connection you found and the one idea you considered and rejected (and why).
