Mission Control for 80 Agents — Conway's law meets game UI

Once you run more than a handful of agents, the bottleneck is your attention, not tokens.
What a pro adds: An SRE or observability engineer would first define the event schema and the metric, then build the cheapest surface that could move it, and only then add the game layer.
Proof it worked: Hook-timestamped block start and end events analyzed over an ABAB crossover of ten working days.
Biggest trap: Blocks not detected: idle waits never emit a Notification. Fix: add a no-event-for-N-minutes heuristic and log it as a distinct reason.

Save this for when you build it. The carousel is the map; the guide has every prompt.

Built on posts by @evolving.ai @jarrenrocks @itsnicconley @ryanlpeterman @therobertta @shellonback
Full guide + prompts: dejaviewed.dev/guides/agent-mission-control

#ai #claudecode #aiagents #claude #bigquery #ghostty #git #slack #tmux #agentcraft #llm #uiux #agents #workflowautomation #automation #claudemdrules #promptengineering #aitools
