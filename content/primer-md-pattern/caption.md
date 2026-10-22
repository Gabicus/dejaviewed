primer.md — The Living Handoff Document Pattern

The core mechanic: at the end of every Claude Code session, Claude rewrites primer.md with a snapshot of where the project currently stands and what the next session should do first.
What a pro adds: Verify hook semantics against the current Claude Code docs before copying the guide's config: the guide wires the rewrite to the Stop hook…
Proof it worked: claude --debug logs across exit, /compact, and multi-turn sessions: exactly one rewrite per exit and per compaction, zero per turn, zero recursive.
Biggest trap: Rewrite on every turn. Fix: move to SessionEnd and PreCompact.

Save this for when you build it. The carousel is the map; the guide has every prompt.

Built on posts by @keshavsuki
Full guide + prompts: dejaviewed.dev/guides/primer-md-pattern

#ai #claudecode #aiagents #claude #agents #promptengineering #aitools #generativeai #llm #anthropic #automation #agenticai #aiworkflow #buildinpublic #learnai
