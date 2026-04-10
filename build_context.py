#!/usr/bin/env python3
"""Build the DejaViewed Context Layer.

Generates two files from catalog.jsonl:

1. site/catalog.json — Structured queryable index for programmatic agent access.
   Agents can fetch this file and filter by tier, domain, type, technique, tool, etc.

2. site/context.md — Agent-readable context document. Agents load this at session
   start to know what knowledge is available and surface relevant items.

The context layer turns a static catalog into a live knowledge base that any AI agent
can query in real time.

Usage:
    python3 build_context.py
"""
import json
from pathlib import Path
from collections import Counter, defaultdict
from datetime import datetime

ROOT = Path(__file__).parent
DATA = ROOT / "data"
OUT = ROOT / "site"

# Load catalog
posts = [json.loads(l) for l in (DATA / "catalog.jsonl").read_text().splitlines() if l.strip()]
live = [p for p in posts if not p.get("drop")]

# Load curation for tiers
curation = json.loads((DATA / "curation.json").read_text())
tiers = curation.get("tiers", {})
for p in live:
    if not p.get("tier") or p["tier"] == "?":
        p["tier"] = tiers.get(p["post_url"], "C")

# ──────────────────────────────────────────────
# 1. catalog.json — Queryable structured index
# ──────────────────────────────────────────────

def build_entry(p):
    """Slim a catalog record to the queryable fields agents actually need."""
    shortcode = ""
    import re
    m = re.search(r"/(p|reel)/([^/]+)", p.get("post_url", ""))
    if m:
        shortcode = m.group(2)

    return {
        "id": shortcode or p.get("post_url", ""),
        "url": p.get("post_url", ""),
        "title": p.get("card_title", ""),
        "summary": p.get("summary", ""),
        "creator": p.get("creator", ""),
        "collection": p.get("collection", ""),
        "date": p.get("date", ""),
        "type": p.get("type", ""),
        "tier": p.get("tier", "C"),
        "audience": p.get("audience", ""),
        "domains": p.get("domains", []),
        "tools": p.get("tools_mentioned", []),
        "repos": p.get("repos_or_projects_mentioned", []),
        "models": p.get("models_mentioned", []),
        "techniques": p.get("techniques_mentioned", []),
        "takeaways": p.get("key_takeaways", []),
        "links": p.get("links", []),
        "deep_dive": p.get("deep_dive_topic", ""),
        "has_guide": bool(p.get("deep_dive_topic") and (ROOT / "guides" / f"{p['deep_dive_topic']}.md").exists()),
    }

# Build indices for fast lookup
domain_index = defaultdict(list)
tool_index = defaultdict(list)
technique_index = defaultdict(list)
model_index = defaultdict(list)
type_index = defaultdict(list)
tier_index = defaultdict(list)
collection_index = defaultdict(list)

entries = []
for p in live:
    entry = build_entry(p)
    entries.append(entry)
    eid = entry["id"]

    for d in entry["domains"]:
        domain_index[d].append(eid)
    for t in entry["tools"]:
        tool_index[t.lower()].append(eid)
    for t in entry["techniques"]:
        technique_index[t.lower()].append(eid)
    for m in entry["models"]:
        model_index[m.lower()].append(eid)
    type_index[entry["type"]].append(eid)
    tier_index[entry["tier"]].append(eid)
    collection_index[entry["collection"]].append(eid)

catalog_json = {
    "version": "1.0",
    "generated": datetime.now().isoformat(),
    "description": "DejaViewed catalog — structured knowledge index. Query by tier, domain, type, tool, technique, or full-text search across titles and summaries.",
    "usage": {
        "programmatic": "Fetch this JSON, filter entries[] by any field. Indices map keywords → entry IDs for fast lookup.",
        "agent_context": "Load context.md alongside this file for AI agent reasoning about available knowledge.",
        "web": "Visit https://dejaviewed.dev for the interactive catalog.",
    },
    "stats": {
        "total_entries": len(entries),
        "collections": dict(Counter(e["collection"] for e in entries)),
        "tiers": dict(Counter(e["tier"] for e in entries)),
        "types": dict(Counter(e["type"] for e in entries)),
        "unique_tools": len(tool_index),
        "unique_techniques": len(technique_index),
        "unique_domains": len(domain_index),
        "unique_models": len(model_index),
        "guides_written": sum(1 for e in entries if e["has_guide"]),
    },
    "indices": {
        "by_domain": dict(domain_index),
        "by_tool": dict(tool_index),
        "by_technique": dict(technique_index),
        "by_model": dict(model_index),
        "by_type": dict(type_index),
        "by_tier": dict(tier_index),
        "by_collection": dict(collection_index),
    },
    "entries": entries,
}

(OUT / "catalog.json").write_text(json.dumps(catalog_json, indent=2, ensure_ascii=False))
print(f"wrote catalog.json ({len(entries)} entries, {len(json.dumps(catalog_json))//1024}KB)")


# ──────────────────────────────────────────────
# 2. context.md — Agent-readable context document
# ──────────────────────────────────────────────

# Build knowledge summary by domain
domain_summaries = {}
for domain, ids in sorted(domain_index.items(), key=lambda x: -len(x[1])):
    items = [e for e in entries if e["id"] in ids]
    s_count = sum(1 for e in items if e["tier"] == "S")
    a_count = sum(1 for e in items if e["tier"] == "A")
    top_items = [e for e in items if e["tier"] in ("S", "A")]
    top_titles = [e["title"] for e in sorted(top_items, key=lambda x: {"S": 0, "A": 1}.get(x["tier"], 2))[:5]]
    domain_summaries[domain] = {
        "count": len(items),
        "s": s_count,
        "a": a_count,
        "top": top_titles,
    }

# Build tool directory
tool_entries = {}
for tool_lower, ids in sorted(tool_index.items(), key=lambda x: -len(x[1])):
    items = [e for e in entries if e["id"] in ids]
    best_tier = min(({"S": 0, "A": 1, "B": 2, "C": 3}.get(e["tier"], 4) for e in items), default=4)
    tier_label = {0: "S", 1: "A", 2: "B", 3: "C"}.get(best_tier, "C")
    tool_entries[tool_lower] = {
        "mentions": len(ids),
        "best_tier": tier_label,
        "in_domains": list(set(d for e in items for d in e["domains"]))[:5],
    }

# Build technique directory
technique_entries = {}
for tech_lower, ids in sorted(technique_index.items(), key=lambda x: -len(x[1])):
    items = [e for e in entries if e["id"] in ids]
    best_tier = min(({"S": 0, "A": 1, "B": 2, "C": 3}.get(e["tier"], 4) for e in items), default=4)
    tier_label = {0: "S", 1: "A", 2: "B", 3: "C"}.get(best_tier, "C")
    technique_entries[tech_lower] = {
        "mentions": len(ids),
        "best_tier": tier_label,
    }

# Generate the context document
lines = []
lines.append("# DejaViewed Knowledge Context")
lines.append("")
lines.append(f"*Auto-generated {datetime.now().strftime('%Y-%m-%d')} · {len(entries)} entries across {len(collection_index)} collections*")
lines.append("")
lines.append("This document maps everything saved in the DejaViewed catalog. Use it to surface")
lines.append("relevant tools, techniques, repos, and guides when the user's task matches a domain below.")
lines.append("")
lines.append("**Queryable index:** `catalog.json` (same directory) has full structured data with indices.")
lines.append("")

# Stats block
lines.append("## Quick Stats")
lines.append("")
lines.append(f"- **{len(entries)}** curated entries from **{len(set(e['creator'] for e in entries if e.get('creator')))}** creators")
lines.append(f"- **{sum(1 for e in entries if e['tier'] == 'S')}** S-tier · **{sum(1 for e in entries if e['tier'] == 'A')}** A-tier · **{sum(1 for e in entries if e['tier'] == 'B')}** B-tier")
lines.append(f"- **{len(tool_index)}** unique tools · **{len(technique_index)}** techniques · **{len(model_index)}** models")
lines.append(f"- **{sum(1 for e in entries if e['has_guide'])}** deep-dive guides written")
lines.append(f"- Collections: {', '.join(f'{k} ({v})' for k, v in sorted(Counter(e['collection'] for e in entries).items(), key=lambda x: -x[1]))}")
lines.append("")

# Domain map
lines.append("## Domain Map")
lines.append("")
lines.append("When the user works in one of these domains, surface the matching entries:")
lines.append("")
for domain, info in sorted(domain_summaries.items(), key=lambda x: -x[1]["count"]):
    tier_badge = ""
    if info["s"]:
        tier_badge += f" ({info['s']}S"
        if info["a"]:
            tier_badge += f"/{info['a']}A"
        tier_badge += ")"
    elif info["a"]:
        tier_badge += f" ({info['a']}A)"
    top_str = ""
    if info["top"]:
        top_str = " — " + "; ".join(info["top"][:3])
    lines.append(f"- **{domain}** [{info['count']} items]{tier_badge}{top_str}")
lines.append("")

# S-tier items — always surface these
s_items = [e for e in entries if e["tier"] == "S"]
if s_items:
    lines.append("## S-Tier (Highest Signal)")
    lines.append("")
    lines.append("These are the most actionable, well-documented items. Surface first when relevant:")
    lines.append("")
    for e in s_items:
        guide_flag = " 📘" if e["has_guide"] else ""
        domains_str = ", ".join(e["domains"][:3]) if e["domains"] else ""
        lines.append(f"- **{e['title']}**{guide_flag} [{domains_str}]")
        if e["takeaways"]:
            for t in e["takeaways"][:2]:
                lines.append(f"  - {t}")
    lines.append("")

# A-tier items
a_items = [e for e in entries if e["tier"] == "A"]
if a_items:
    lines.append("## A-Tier (High Value)")
    lines.append("")
    for e in a_items:
        guide_flag = " 📘" if e["has_guide"] else ""
        lines.append(f"- **{e['title']}**{guide_flag} [{', '.join(e['domains'][:3])}]")
    lines.append("")

# Tool directory
lines.append("## Tool Directory")
lines.append("")
lines.append("When the user mentions or needs one of these tools, surface the relevant entries:")
lines.append("")
for tool, info in sorted(tool_entries.items(), key=lambda x: (-x[1]["mentions"], x[0])):
    if info["mentions"] >= 2 or info["best_tier"] in ("S", "A"):
        lines.append(f"- **{tool}** ({info['mentions']}x, best: {info['best_tier']}-tier) — domains: {', '.join(info['in_domains'][:3])}")
lines.append("")

# Technique directory (top ones)
lines.append("## Technique Directory")
lines.append("")
lines.append("Techniques referenced across the catalog:")
lines.append("")
for tech, info in sorted(technique_entries.items(), key=lambda x: (-x[1]["mentions"], x[0])):
    if info["mentions"] >= 2 or info["best_tier"] in ("S", "A"):
        lines.append(f"- **{tech}** ({info['mentions']}x, best: {info['best_tier']}-tier)")
lines.append("")

# How to use section
lines.append("## How Agents Use This")
lines.append("")
lines.append("### Pattern: Domain-triggered surfacing")
lines.append("```")
lines.append("User says: 'I want to build a market making bot'")
lines.append("Agent thinks: domain=market-making,quant,hft → check context.md domain map")
lines.append("Agent finds: Avellaneda-Stoikov (S-tier), Ornstein-Uhlenbeck (A-tier), etc.")
lines.append("Agent surfaces: 'Your DejaViewed catalog has S-tier coverage of market making —")
lines.append("  the Avellaneda-Stoikov guide covers optimal spread calculation. Want me to pull it up?'")
lines.append("```")
lines.append("")
lines.append("### Pattern: Tool lookup")
lines.append("```")
lines.append("User says: 'How do I use VectorBT?'")
lines.append("Agent thinks: tool=vectorbt → check catalog.json by_tool index")
lines.append("Agent finds: entry with summary + links")
lines.append("Agent surfaces: 'You saved a VectorBT explainer — here's the summary and links.'")
lines.append("```")
lines.append("")
lines.append("### Pattern: Gap detection")
lines.append("```")
lines.append("User says: 'I need a good options pricing model'")
lines.append("Agent thinks: domain=options,derivatives → check entries")
lines.append("Agent finds: Heston Model (S-tier), Vol Surface (S-tier), Black-Scholes mentioned")
lines.append("Agent surfaces: 'You have two S-tier entries on options pricing. The Heston Model")
lines.append("  guide covers stochastic vol. Want the deep dive?'")
lines.append("```")
lines.append("")
lines.append("### Programmatic access")
lines.append("```python")
lines.append("import json")
lines.append("catalog = json.load(open('catalog.json'))")
lines.append("")
lines.append("# Find all S-tier entries")
lines.append("s_ids = catalog['indices']['by_tier']['S']")
lines.append("s_entries = [e for e in catalog['entries'] if e['id'] in s_ids]")
lines.append("")
lines.append("# Find entries about a specific domain")
lines.append("quant_ids = catalog['indices']['by_domain'].get('quant', [])")
lines.append("")
lines.append("# Find entries mentioning a tool")
lines.append("python_ids = catalog['indices']['by_tool'].get('python', [])")
lines.append("")
lines.append("# Full-text search across titles and summaries")
lines.append("matches = [e for e in catalog['entries']")
lines.append("           if 'volatility' in (e['title'] + ' ' + e['summary']).lower()]")
lines.append("```")
lines.append("")

context_md = "\n".join(lines)
(OUT / "context.md").write_text(context_md)
print(f"wrote context.md ({len(lines)} lines, {len(context_md)//1024}KB)")

# Also write a llms.txt for LLM-native discovery
llms_txt = f"""# DejaViewed
> A curated knowledge catalog of {len(entries)} saved posts, tools, techniques, and repos.

## Docs
- [Interactive Catalog](https://dejaviewed.dev/catalog.html): Browse all entries with filters
- [Context Layer](https://dejaviewed.dev/context.md): Agent-readable knowledge map
- [Queryable Index](https://dejaviewed.dev/catalog.json): Structured JSON with indices

## Stats
- {len(entries)} entries across {len(collection_index)} collections
- {sum(1 for e in entries if e['tier'] == 'S')} S-tier, {sum(1 for e in entries if e['tier'] == 'A')} A-tier items
- {len(tool_index)} tools, {len(technique_index)} techniques, {len(model_index)} models indexed
- {sum(1 for e in entries if e['has_guide'])} deep-dive guides

## Usage
Agents can fetch catalog.json and filter by tier, domain, type, tool, or technique.
Load context.md at session start for domain-triggered knowledge surfacing.
"""
(OUT / "llms.txt").write_text(llms_txt)
print(f"wrote llms.txt")

print(f"\n✅ Context layer built: catalog.json + context.md + llms.txt")
