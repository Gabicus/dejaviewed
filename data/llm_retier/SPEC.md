# Tier re-rate — old collections (ai2, ai4, ai7, quant)

These entries were tiered by hand in July 2026 with a looser bar; 20-29% are S. Re-rate ONLY the tier,
blind to current_tier (read it last, and only to flag big jumps). Do not rewrite titles or summaries.

Rubric (target across a batch: S ≤ 12%, A ~30%, B ~40%, C rest):
- S: exceptional — deep, specific, linkable (real repo/tool/paper), you'd build on it this week; the
  transcript/caption actually delivers the content (not "comment X for the guide").
- A: solid, actionable, names real things, worth a guide.
- B: useful reference / one idea / good example without depth.
- C: thin, hype, promo, bait with no delivered content, sponsored.
Bait captions with a rich transcript: judge the transcript. Rich caption + empty transcript: judge the caption.
A famous tool name alone is not S; what the post teaches about it is what counts.

Output `out_NN.json`: [{"id": ..., "tier": "S|A|B|C", "reason": "≤ 20 words"}] same order as input.
Validate ids/order with python. Report: per batch the S/A/B/C counts, how many changed vs current_tier,
and the 5 biggest demotions (title, old→new, reason).
