#!/usr/bin/env python3
"""Build the DejaViewed Context Layer.

Reads site/catalog.json (written by the parquet CMS, `cms.py rebuild`) and generates:

1. site/catalog.json is NOT written here — the CMS owns it. Agents query it directly.

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

# Load catalog (CMS output; source of truth is data/entries.parquet)
CATALOG = json.loads((OUT / "catalog.json").read_text(encoding="utf-8"))
live = [p for p in CATALOG["entries"] if not p.get("drop")]
GENERATED_DATE = datetime.now().strftime("%Y-%m-%d")

# ──────────────────────────────────────────────
# 1. catalog.json — Queryable structured index
# ──────────────────────────────────────────────

def build_entry(p):
    """Slim a site/catalog.json entry to the queryable fields agents actually need."""
    return {
        "id": p.get("id", ""),
        "url": p.get("url", ""),
        "title": p.get("title", ""),
        "summary": p.get("summary", ""),
        "creator": p.get("creator", ""),
        "collection": p.get("collection") or p.get("source_collection", ""),
        "date": p.get("date", ""),
        "type": p.get("type", ""),
        "tier": p.get("tier") or "C",
        "audience": p.get("audience", ""),
        "domains": p.get("domains") or [],
        "tools": p.get("tools") or [],
        "repos": p.get("repos") or [],
        "models": p.get("models") or [],
        "techniques": p.get("techniques") or [],
        "takeaways": p.get("takeaways") or [],
        "deep_dive": p.get("deep_dive") or p.get("deep_dive_slug", ""),
        "has_guide": bool(p.get("has_guide")),
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

print(f"loaded site/catalog.json ({len(entries)} entries, {len(collection_index)} collections)")


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
lines.append(f"*Auto-generated {GENERATED_DATE} · {len(entries)} entries across {len(collection_index)} collections*")
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

# llms.txt (llmstxt.org format) — live counts, clean URLs, every guide with its one-line answer
import sys as _sys
_sys.path.insert(0, str(ROOT / "scripts"))
from build_seo import BASE as _BASE, guide_index as _guide_index  # noqa: E402
try:
    from build_collections import collection_name as _cname, collection_slug as _cslug  # noqa: E402
except Exception:
    _cname = lambda c: c
    _cslug = lambda c: c

_gi = _guide_index()
_packs = json.loads((DATA / "prompt_systems.json").read_text(encoding="utf-8")) if (DATA / "prompt_systems.json").exists() else {}
_tiers = Counter(e["tier"] for e in entries)
_n_tr = sum(1 for p in live if (p.get("transcript") or "").strip())
_creators = len({e["creator"] for e in entries if e.get("creator")})
_L = [
    "# DejaViewed",
    "",
    f"> A curated, transcribed archive of {len(entries)} saved posts from {_creators} practitioners on AI tools, "
    f"agents, creative code, art and quant trading, tiered S to C, with {len(_gi['guides'])} guides that each ship "
    f"a runnable prompt system.",
    "",
    f"Updated: {GENERATED_DATE}. {len(entries)} entries ({_tiers.get('S', 0)} S, {_tiers.get('A', 0)} A, "
    f"{_tiers.get('B', 0)} B, {_tiers.get('C', 0)} C) in {len(collection_index)} collections; {_n_tr} speech transcripts; "
    f"{len(_gi['guides'])} guides; {len(_gi['deeper'])} deeper dives; {len(_packs)} prompt systems.",
    "",
    "Usage terms: captions, transcripts and media belong to their creators (every entry links its source post); "
    f"titles, summaries, tiers, tags, guides and prompt systems are DejaViewed's own curation. Details: {_BASE}/method#terms",
    "",
    "## Start",
    f"- [Start here]({_BASE}/start-here): what DejaViewed is, who it is for, how to cite it",
    f"- [How DejaViewed works]({_BASE}/method): pipeline, tier rubric, update cadence, affiliate policy, who runs it",
    f"- [Catalog]({_BASE}/catalog): filter every entry by tier, tool, creator and collection",
    f"- [All entries]({_BASE}/e/): one static page listing every entry",
    f"- [Guides]({_BASE}/guides/): index of all guides",
    f"- [Prompt systems]({_BASE}/prompts): one pasteable prompt system per guide",
    f"- [Flow map]({_BASE}/flow): how entries flow from sources through pillars, tools and techniques into guides and outputs, with a gap analysis",
    "",
    "## Guides",
]
for _g in _gi["guides"]:
    _L.append(f"- [{_g['title']}]({_g['url']})" + (f": {_g['answer']}" if _g["answer"] else ""))
_L += ["", "## Collections"]
if (OUT / "collections" / "index.html").exists():
    _L.append(f"- [All collections]({_BASE}/collections/)")
for _c, _ids in sorted(collection_index.items(), key=lambda kv: -len(kv[1])):
    if not _c:
        continue
    _url = f"{_BASE}/collections/{_cslug(_c)}" if (OUT / "collections" / f"{_cslug(_c)}.html").exists() else f"{_BASE}/catalog"
    _L.append(f"- [{_cname(_c)}]({_url}): {len(_ids)} entries")
_L += ["", "## Data",
       f"- [Catalog JSON]({_BASE}/api/catalog.json): every entry with title, summary, creator, tier, tools, techniques, domains, source URL",
       f"- [Prompt systems JSON]({_BASE}/api/prompts.json): one-shot prompt, step prompts with audits, gap audit, validation oracles per guide",
       f"- [Tools index]({_BASE}/api/tools.json): tools, techniques and domains to entry ids",
       f"- [Creators]({_BASE}/api/creators.json): creator handles with post counts and tier mix",
       f"- [Collections JSON]({_BASE}/api/collections.json): per-collection counts",
       f"- [Deep dives JSON]({_BASE}/api/deep_dives.json): curated insight connections behind the guides",
       f"- [Flow JSON]({_BASE}/api/flow.json): the zoned flow graph (nodes, weighted edges, ecosystem lanes, top paths, gaps)",
       "", "## Optional",
       f"- [Full text]({_BASE}/llms-full.txt): every guide answer, entry and deep dive as plain text",
       f"- [Context map]({_BASE}/context.md): domain, tool and technique map for session-start context",
       f"- [RSS feed]({_BASE}/feed.xml): new entries, guides and deeper dives",
       f"- [Sitemap]({_BASE}/sitemap.xml): every indexable page with its last-changed date",
       ]
llms_txt = "\n".join(_L) + "\n"
(OUT / "llms.txt").write_text(llms_txt, encoding="utf-8")
print(f"wrote llms.txt ({len(_gi['guides'])} guides, {len(llms_txt)} bytes)")

# Refresh the entry count in the AI plugin manifest (was hardcoded "334+")
plugin_path = OUT / ".well-known" / "ai-plugin.json"
if plugin_path.exists():
    import re
    plugin = json.loads(plugin_path.read_text(encoding="utf-8"))
    desc = plugin.get("description_for_model", "")
    new_desc = re.sub(r"catalog of [0-9,]+\+? ", f"catalog of {len(entries)} ", desc)
    if new_desc != desc:
        plugin["description_for_model"] = new_desc
        plugin_path.write_text(json.dumps(plugin, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print("updated .well-known/ai-plugin.json entry count")

print(f"\n✅ Context layer built: context.md + llms.txt (from site/catalog.json)")
