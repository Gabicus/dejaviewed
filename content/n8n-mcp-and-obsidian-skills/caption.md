n8n-mcp + obsidian-skills — Two High-Leverage Claude Code Extensions

An MCP (Model Context Protocol) server that loads every n8n node's schema, documentation, and operation metadata into a searchable database and exposes it to Claude as tools.
What a pro adds: An automation engineer would not point an agent with write access at a live n8n; they would run a throwaway n8n in Docker with its own data volume…
Proof it worked: n8n's /api/v1/executions on the dev instance shows status success for every workflow counted as working, using fixture inputs.
Biggest trap: Full mode against production. Fix: dev Docker instance bound to localhost only, separate API key.

Save this for when you build it. The carousel is the map; the guide has every prompt.

Built on posts by @chase.h.ai
Full guide + prompts: dejaviewed.dev/guides/n8n-mcp-and-obsidian-skills

#ai #claudecode #aiagents #claude #czlonkowskin8nmcp #glittercowboygetshitdone #hesreallyhimawesomeclaudecode #kepanoobsidianskills #mcp #n8n #agents #automation #design #promptengineering #aitools #generativeai #llm #anthropic
