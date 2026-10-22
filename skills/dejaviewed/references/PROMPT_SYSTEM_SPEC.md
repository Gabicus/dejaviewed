# Prompt-system spec — one prompting system per guide / deep dive

You are writing the **prompt system** for DejaViewed deep dives and guides: everything a person (or an
agent harness) needs to actually *execute* the dive — not read about it. One pack per target. Verbose,
robust, comprehensive. The reader pastes these into Claude Code / Claude / any agent and gets the real
thing built, with the gaps found and filled along the way.

Input: `data/prompt_systems/batch_NN.json` — a list of targets. Each has `slug`, `kind` (`dive` = curated
deep dive with connected posts; `guide` = standalone hand-written guide whose markdown is included),
`title`, `thesis`, `why_it_matters`, `action_sketch`, `prerequisites`, `tools`, `techniques`, `domains`,
`entries[]` (title, summary, creator, tier, takeaways, tools, caption, transcript excerpt) and, for guides,
`guide_markdown`.

Output: `data/prompt_systems/out_NN.json` — a list, **same order, same slugs**, one object each:

```json
{
  "slug": "<copy from input>",
  "mission": "2-4 sentences: what running this prompt system produces, for whom, and the bar for done.",
  "deeper_not_bigger": {
    "professional_would": "What a top professional in THIS field would do here that the reader is NOT asking for. Specific. 3-6 sentences.",
    "rawest_material": "The rawest primary material they would start from instead of the digested posts: papers, source repos, docs, datasets, filings, logs, the creator's own code. Name them. 3-6 sentences or a list.",
    "methods_tools": "The specific methods and tools they would use (named libraries, commands, techniques, evaluation methods). Concrete, not 'use best practices'.",
    "external_proof": "What, other than the model or the reader, would show the result is right: tests, benchmarks, reproductions, third-party data, a paying user, a backtest with a control, a reviewer. Name the oracle.",
    "rewritten_prompt": "The reader's naive ask, rewritten to ask for EXACTLY the above. A complete, pasteable prompt, 150-350 words."
  },
  "one_shot": "A single pasteable prompt, 500-1000 words, that does the whole dive in one run. Must contain: role + stance; context the agent needs (name the tools/repos/posts); hard constraints; ordered deliverables; a built-in gap analysis (the agent lists what it could not verify / what is missing and fills what it can); self-questions it must answer before finishing; stop conditions; the exact return format.",
  "steps": [
    {
      "n": 1,
      "title": "short step name",
      "goal": "one sentence",
      "prompt": "The full pasteable prompt for this step, 120-400 words. Standalone — assumes only the prior steps' outputs.",
      "expect": "What a correct output looks like (artifact, shape, size).",
      "audit": "The check the agent runs on its own step output before moving on: what to re-verify, what counts as fail, what to do on fail."
    }
  ],
  "gap_audit_prompt": "A pasteable prompt (150-400 words) run AFTER the build: enumerate claims, mark each verified/unverified/false with evidence, list missing pieces, rank by impact, fix the top ones now, and report what it could not fix and why.",
  "self_questions": ["8-15 questions the agent must ask itself for things it is missing — specific to this dive, not generic ('did I handle errors')."],
  "validation_oracles": ["3-6 external things that prove the result right — each one names WHO/WHAT and HOW (e.g. 'reproduce the paper's Table 2 within 5%', 'the Blender scene opens and renders without errors in 4.2 headless')."],
  "failure_modes": ["4-8 ways this goes wrong in practice, each with the tell-tale sign and the fix."],
  "agent_direction": "Notes for an agent harness running this unattended: which tools to reach for first, what to cache, when to spawn a sub-agent, when to stop and ask, what to return and in what file(s). 120-300 words."
}
```

## Laws

1. **Specific to the dive.** Every prompt names the actual tools, repos, models, creators' techniques and
   data from the input. A prompt that could be pasted under a different dive unchanged is a failure.
2. **Steps are 5-9**, each a complete standalone prompt. Together they must reach the same end as
   `one_shot`. Step 1 is always "establish ground truth / rawest material"; the last step is always
   "validate against the oracles + write the gap report".
3. **Gap analysis and audit are built in**, not appended: every step has an `audit`, the one-shot has an
   internal gap list, and `gap_audit_prompt` is the independent post-build pass. The agent must find and
   fill its own gaps and ask itself what it is missing.
4. **No fluff, no hedging, no marketing.** Imperative voice. Numbers, names, paths, flags.
5. **Use the raw material in the input** (transcripts, captions, takeaways, guide markdown). Quote the
   concrete claims the creators made so the prompts test them rather than repeat them.
6. **Money / markets / trading dives** (Polymarket, quant, stocks, capital): prompts must include a paper
   or backtest arm with a control, position-size and loss caps, and an explicit "no real money until the
   oracle passes" gate. Never promise returns.
7. **Security-adjacent targets** (jailbreak repo, leaked system prompts, injection in CI): write the pack
   for the *defensive* use — understanding the attack classes, building detectors/evals, hardening your
   own agents. No operational attack prompts against third parties.
8. **Length.** Each pack is 1,800-3,500 words total. Verbose is correct here; padding is not.
9. Output must be valid JSON (escape newlines inside strings as `\n`). Write the file with the Write tool.
   Do not touch any other file.
