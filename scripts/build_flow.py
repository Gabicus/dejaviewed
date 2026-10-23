#!/usr/bin/env python3
"""Build the /flow data: a zoned, Sankey-style node network of the whole archive + a gap analysis.

Usage:
    python3 scripts/build_flow.py            # writes site/flow_data.json, site/api/flow.json, site/flow_gaps.json,
                                             # patches the crawler summary in site/flow.html
    python3 scripts/build_flow.py --check    # dry run; exit 1 if any output would change

Zones, left -> right in data-flow order (the same six-band idea as the Unicron Atlas, unicron/atlas/app.js):
    0 Sources   18 collections + creators with >= 4 entries (the rest folded into "other creators")
    1 Pillars   the 8 pillars of data/seo/content_gaps_2026-10-22.json + "Music & art" + "Other"
    2 Tools     tools >= 3 entries (canonical names from build_tools.hub_names), models >= 3, repos >= 2
    3 Techniques  >= 4 entries
    4 Guides    curated dives with a page in site/guides/ (+ deeper page when it exists)
    5 Outputs   prompt systems, content kits, tool hubs, comparisons, best-of, system prompts, collection pages

Edges join adjacent zones (plus the pillar->guide and tool->guide bridges the page shows when a zone is
collapsed). Weight = shared entry count. Edges below MIN_W are dropped except guide->output edges.
If the edge budget is exceeded, the per-kind minimum weight is raised for the densest kinds first.

Read-only on data/*, content/*, site/catalog.json. Deterministic: two runs produce byte-identical files.
Pillar membership is a tag/text rule set (below); entries can sit in several pillars, like the content-gaps
file. The rules are re-derived here because that file's scratch script is not in the repo.
"""
from __future__ import annotations

import argparse
import html
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DATA = ROOT / "data"
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_collections import collection_name, collection_url, safe_slug  # noqa: E402
from build_tools import hub_names, slug_for  # noqa: E402

OUT = SITE / "flow_data.json"
OUT_API = SITE / "api" / "flow.json"
OUT_GAPS = SITE / "flow_gaps.json"
PAGE = SITE / "flow.html"

ZONES = ["Sources", "Pillars", "Tools · models · repos", "Techniques", "Guides & deeper", "Outputs"]
MIN_CREATOR, MIN_TOOL, MIN_MODEL, MIN_REPO, MIN_TECH = 4, 3, 3, 2, 4
MIN_W = 2
MAX_NODES, MAX_EDGES = 400, 1500
ENTRY_CAP = 200
TIERS = "SABC"
TIER_RANK = {t: i for i, t in enumerate(TIERS)}
QUANT_COLLS = {"quant", "stock2", "stock3", "game-theory"}
ART_COLLS = {"music", "art-i-like", "art-inspiration"}

# ── pillars: key -> (label, regex over tools/models/repos/tags/techniques/domains/title/summary) ──
PILLARS = [
    ("agentic_coding", "Agentic coding",
     r"claude code|codex|cursor|gemini cli|windsurf|vibe[- ]?cod|coding agent|cline\b|aider|copilot|antigravity|"
     r"claude\.md|replit|lovable|bolt\.new|kiro|opencode|terminal agent|ai coding|agentic coding|subagent"),
    ("agents_automation", "Agents, MCP & automation",
     r"\bmcp\b|model context protocol|n8n|zapier|make\.com|headless|scheduled (?:agent|task)|ai agents?\b|"
     r"autonomous agent|multi-agent|agent sdk|openclaw|clawdbot|browser use|computer use|agent workflow|"
     r"workflow automation|automate (?:your|the|every)"),
    ("prompt_context_eng", "Prompt & context engineering",
     r"prompt|system prompt|context engineering|context window|claude\.md|skills?\.md|meta-prompt|jailbreak"),
    ("quant_trading_prediction", "Quant trading & prediction markets",
     r"polymarket|kalshi|prediction market|trading|tradingview|backtest|quant|stock|options|hedge fund|"
     r"market maker|order ?book|crypto|bitcoin|portfolio|investing|game theory"),
    ("ai_video_image_gen", "AI video & image generation",
     r"higgsfield|runway|\bveo\b|seedance|kling|\bsora\b|midjourney|video generation|image generation|"
     r"text-to-video|image-to-video|nano banana|flux\b|hailuo|pika\b|luma|ai video|ai image|ai film|"
     r"stable diffusion|ideogram|krea"),
    ("threeD_creative_coding", "3D & creative coding",
     r"blender|touchdesigner|mediapipe|gaussian splat|splat|plotter|three\.js|threejs|unreal|creative coding|"
     r"p5\.js|shader|generative art|houdini|webgl|projection mapping|interactive installation|"
     r"3d (?:model|scan|print|scene|mesh|render|animation)|image-to-3d|text-to-3d"),
    ("local_open_ai", "Local & open-weight AI",
     r"ollama|qwen|deepseek|kimi|llama|local llm|local ai|open[- ]weight|open[- ]source model|hugging ?face|"
     r"lm studio|comfyui|gguf|mistral|gemma|self-host|offline ai|on-device|mlx\b|vllm"),
    ("security_osint", "Security, OSINT & red-teaming",
     r"security|osint|jailbreak|prompt injection|red[- ]team|privacy|hacking|hacker|pentest|vulnerab|"
     r"surveillance|exploit|malware|phishing|scam"),
]
PILLAR_RE = {k: re.compile(rx, re.I) for k, _, rx in PILLARS}
PILLAR_LABEL = {k: lbl for k, lbl, _ in PILLARS}
PILLAR_LABEL.update({"music_art": "Music & art", "other": "Other"})
PILLAR_ORDER = [k for k, _, _ in PILLARS] + ["music_art", "other"]

# ── agent lanes (ecosystems) from tools/models/repos text ──
LANES = {
    "anthropic": r"claude|anthropic|\bmcp\b|model context protocol|agent sdk",
    "openai": r"chatgpt|\bgpt[- ]?\w*|codex|\bsora\b|openai|\bo[134]\b|dall-?e",
    "google": r"gemini|\bveo\b|notebooklm|\bstitch\b|antigravity|google ai|nano banana|imagen",
    "open-weight": r"llama|qwen|deepseek|kimi|ollama|hugging ?face|comfyui|mistral|gemma|stable diffusion|flux\b",
    "creative": r"blender|touchdesigner|runway|higgsfield|kling|mediapipe|unreal|three\.js|threejs|figma",
    "automation": r"n8n|playwright|docker|vercel|zapier|make\.com",
    "quant": r"polymarket|tradingview|kalshi|quantconnect|backtrader",
}
LANE_RE = {k: re.compile(v, re.I) for k, v in LANES.items()}
LANE_ORDER = list(LANES)

SUMMARY_START, SUMMARY_END = "<!-- flow:summary:start -->", "<!-- flow:summary:end -->"


# ───────────────────────────────────────────────────────────── helpers
def jload(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def as_list(v) -> list:
    if isinstance(v, list):
        return [x for x in v if x]
    return [v] if v else []


def kebab(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-") or "x"


def tier_of(e: dict) -> str:
    t = (e.get("tier") or "C").upper()
    return t if t in TIER_RANK else "C"


def entry_text(e: dict) -> str:
    parts = []
    for k in ("tools", "models", "repos", "tags", "techniques", "domains"):
        parts += [str(x) for x in as_list(e.get(k))]
    parts += [str(e.get("title") or ""), str(e.get("summary") or "")]
    return " | ".join(parts)


def lane_text(e: dict) -> str:
    return " | ".join(str(x) for k in ("tools", "models", "repos") for x in as_list(e.get(k)))


def is_noindex(p: Path) -> bool:
    return bool(re.search(r'<meta\s+name="robots"\s+content="[^"]*noindex', p.read_text(encoding="utf-8", errors="replace")[:6000], re.I))


def title_of(p: Path) -> str:
    m = re.search(r"<title>(.*?)</title>", p.read_text(encoding="utf-8", errors="replace"), re.S)
    t = html.unescape(m.group(1)).strip() if m else p.stem
    return re.sub(r"\s*[·|—-]\s*DejaViewed\s*$", "", t)


# ───────────────────────────────────────────────────────────── build
class Graph:
    def __init__(self, entries: dict[str, dict]):
        self.E = entries
        self.nodes: dict[str, dict] = {}
        self.members: dict[str, set[str]] = {}

    def add(self, nid: str, zone: int, label: str, kind: str, ids: set[str], url: str | None = None, **extra):
        ids = {i for i in ids if i in self.E}
        self.members[nid] = ids
        self.nodes[nid] = {"id": nid, "zone": zone, "label": label, "kind": kind, "url": url, **extra}

    def finish_node(self, nid: str, lane_of: dict[str, set[str]]) -> dict:
        n, ids = self.nodes[nid], self.members[nid]
        mix = Counter(tier_of(self.E[i]) for i in ids)
        lanes = Counter(l for i in ids for l in lane_of[i])
        ordered = sorted(ids, key=lambda i: (TIER_RANK[tier_of(self.E[i])], _neg(self.E[i].get("date") or ""), i))
        n["count"] = n.get("count", len(ids))
        n["tier_mix"] = {t: mix.get(t, 0) for t in TIERS}
        n["lanes"] = {l: lanes[l] for l in LANE_ORDER if lanes.get(l)}
        n["entries"] = ordered[:ENTRY_CAP]
        for k in ("hub", "indexed", "affiliate"):
            n.setdefault(k, False)
        return n


def _neg(date: str) -> str:
    """Sort key that orders ISO dates newest-first inside an ascending sort."""
    return "".join(chr(0x10FFFF - ord(c)) if c else c for c in date)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    cat = jload(SITE / "catalog.json")
    entries = {e["id"]: e for e in cat["entries"] if e.get("id")}
    E = entries

    # per-entry facets
    pillars_of: dict[str, set[str]] = {}
    lane_of: dict[str, set[str]] = {}
    tools_of: dict[str, set[str]] = {}
    for i, e in E.items():
        txt = entry_text(e)
        ps = {k for k, rx in PILLAR_RE.items() if rx.search(txt)}
        colls = set(as_list(e.get("collections"))) | {e.get("source_collection") or ""}
        if colls & QUANT_COLLS:
            ps.add("quant_trading_prediction")
        if colls & ART_COLLS or (not ps and re.search(r"\bmusic\b|\bart\b|illustrat|painting|photograph", txt, re.I)):
            ps.add("music_art")
        if not ps:
            ps.add("other")
        pillars_of[i] = ps
        lt = lane_text(e)
        ls = {k for k, rx in LANE_RE.items() if rx.search(lt)}
        if colls & QUANT_COLLS:
            ls.add("quant")
        lane_of[i] = ls
        tools_of[i] = hub_names(e)

    G = Graph(E)

    # ── zone 0: sources ──
    by_coll: dict[str, set[str]] = defaultdict(set)
    by_creator: dict[str, set[str]] = defaultdict(set)
    for i, e in E.items():
        c = e.get("source_collection") or (as_list(e.get("collections")) or [""])[0]
        if c:
            by_coll[c].add(i)
        cr = (e.get("creator") or "").strip().lstrip("@")
        if cr:
            by_creator[cr].add(i)
    for c in sorted(by_coll, key=lambda c: (-len(by_coll[c]), c)):
        G.add(f"coll:{c}", 0, collection_name(c), "collection", by_coll[c], collection_url(c))
    other_ids: set[str] = set()
    n_other = 0
    for cr in sorted(by_creator, key=lambda c: (-len(by_creator[c]), c)):
        if len(by_creator[cr]) >= MIN_CREATOR:
            G.add(f"creator:{cr}", 0, "@" + cr, "creator", by_creator[cr], f"https://www.instagram.com/{cr}/")
        else:
            other_ids |= by_creator[cr]
            n_other += 1
    G.add("creator:_other", 0, f"Other creators ({n_other})", "creator-group", other_ids, None, folded=n_other)

    # ── zone 4 first (guides), pillars/hub links need them ──
    dives = jload(DATA / "deep_dives.json", {}).get("deep_dives", [])
    packs = jload(DATA / "prompt_systems.json", {}) or {}
    kits = jload(ROOT / "content" / "status.json", {}) or {}
    guides: dict[str, dict] = {}
    for d in dives:
        if not (d.get("suggested_by") == "curated" or d.get("pinned")):
            continue
        slug = d["id"][len("dd-insight-"):] if d["id"].startswith("dd-insight-") else d["id"]
        if not (SITE / "guides" / f"{slug}.html").is_file():
            continue
        ids = set(as_list(d.get("entry_ids"))) | {i for i, e in E.items() if e.get("deep_dive_slug") == slug}
        guides[slug] = {"title": d.get("title") or slug, "ids": {i for i in ids if i in E}}
    # hand-written guide pages without a curated dive record still count as guides
    for p in sorted((SITE / "guides").glob("*.html")):
        if p.stem != "index" and p.stem not in guides:
            ids = {i for i, e in E.items() if e.get("deep_dive_slug") == p.stem}
            ids |= set(re.findall(r'href="/e/([A-Za-z0-9_-]+)"', p.read_text(encoding="utf-8", errors="replace"))) & set(E)
            guides[p.stem] = {"title": title_of(p), "ids": ids}
    in_guide: dict[str, set[str]] = defaultdict(set)
    for g, gd in guides.items():
        for i in gd["ids"]:
            in_guide[i].add(g)

    # ── zone 1: pillars ──
    pill_ids: dict[str, set[str]] = defaultdict(set)
    for i, ps in pillars_of.items():
        for p in ps:
            pill_ids[p].add(i)
    gap_file = jload(DATA / "seo" / "content_gaps_2026-10-22.json", {}) or {}
    gap_stats = {p["key"]: p.get("stats", {}) for p in gap_file.get("pillars", [])}
    pillar_guides: dict[str, list[tuple[str, int]]] = {}
    for p in PILLAR_ORDER:
        ids = pill_ids.get(p, set())
        # a guide "covers" a pillar when >= 2 of its entries and >= 30% of them sit in the pillar
        cov = sorted(((g, len(gd["ids"] & ids)) for g, gd in guides.items()
                      if len(gd["ids"] & ids) >= 2 and len(gd["ids"] & ids) >= 0.3 * max(1, len(gd["ids"]))),
                     key=lambda x: (-x[1], x[0]))
        pillar_guides[p] = cov
        url = f"/guides/{cov[0][0]}" if cov else ("/collections/music" if p == "music_art" else "/catalog")
        G.add(f"pillar:{p}", 1, PILLAR_LABEL[p], "pillar", ids, url,
              guides=len(cov), source_entries=gap_stats.get(p, {}).get("entries"))

    # ── zone 2: tools / models / repos ──
    aff = jload(DATA / "monetize" / "affiliates.json", {}) or {}
    aff_names = {}
    for slug, a in aff.items():
        for nm in [a.get("tool") or slug, *as_list(a.get("aliases"))]:
            aff_names[nm.lower()] = slug
    by_tool: dict[str, set[str]] = defaultdict(set)
    for i, ts in tools_of.items():
        for t in ts:
            by_tool[t].add(i)
    tool_nodes = {}
    for t in sorted(by_tool, key=lambda t: (-len(by_tool[t]), t)):
        if len(by_tool[t]) < MIN_TOOL:
            continue
        s = slug_for(t)
        hp = SITE / "tools" / f"{s}.html"
        hub = hp.is_file()
        a_slug = aff.get(s) and s or aff_names.get(t.lower())
        nid = f"tool:{s}"
        if nid in G.nodes:
            G.members[nid] |= by_tool[t]
            continue
        G.add(nid, 2, t, "tool", by_tool[t], f"/tools/{s}" if hub else None,
              hub=hub, indexed=hub and not is_noindex(hp), affiliate=bool(a_slug),
              affiliate_slug=a_slug or None, affiliate_status=(aff.get(a_slug) or {}).get("status") if a_slug else None)
        tool_nodes[t.lower()] = nid
    for field, kind, mn in (("models", "model", MIN_MODEL), ("repos", "repo", MIN_REPO)):
        by: dict[str, set[str]] = defaultdict(set)
        disp: dict[str, str] = {}
        for i, e in E.items():
            for m in as_list(e.get(field)):
                k = str(m).strip()
                if not k:
                    continue
                by[k.lower()].add(i)
                disp.setdefault(k.lower(), k)
        for k in sorted(by, key=lambda k: (-len(by[k]), k)):
            if len(by[k]) < mn or k in tool_nodes:
                continue
            url = f"https://github.com/{disp[k]}" if kind == "repo" and re.fullmatch(r"[\w.-]+/[\w.-]+", disp[k]) else None
            G.add(f"{kind}:{kebab(k)}", 2, disp[k], kind, by[k], url)

    # ── zone 3: techniques ──
    by_tech: dict[str, set[str]] = defaultdict(set)
    tdisp: dict[str, str] = {}
    for i, e in E.items():
        for t in as_list(e.get("techniques")):
            k = str(t).strip().lower()
            by_tech[k].add(i)
            tdisp.setdefault(k, str(t).strip())
    for k in sorted(by_tech, key=lambda k: (-len(by_tech[k]), k)):
        if len(by_tech[k]) >= MIN_TECH:
            G.add(f"tech:{kebab(k)}", 3, tdisp[k], "technique", by_tech[k], None)

    # ── zone 4: guides (+ deeper) ──
    for g in sorted(guides):
        deeper = SITE / "deeper" / f"deeper-insight-{g}.html"
        G.add(f"guide:{g}", 4, guides[g]["title"], "guide", guides[g]["ids"], f"/guides/{g}",
              deeper=f"/deeper/deeper-insight-{g}" if deeper.is_file() else None,
              prompt_system=g in packs, kit=kits.get(g))

    # ── zone 5: outputs ──
    for g in sorted(guides):
        if g in packs:
            G.add(f"ps:{g}", 5, f"Prompt system · {guides[g]['title']}", "prompt-system", guides[g]["ids"],
                  f"/guides/{g}#prompt-system", guide=g)
    for k in sorted(kits):
        ids = guides.get(k, {}).get("ids", set())
        G.add(f"kit:{k}", 5, f"Content kit · {guides[k]['title'] if k in guides else k}", "kit", ids,
              f"/guides/{k}" if k in guides else None, status=kits[k], guide=k if k in guides else None)
    hub_ids: dict[str, set[str]] = defaultdict(set)
    for i, ts in tools_of.items():
        for t in ts:
            hub_ids[slug_for(t)].add(i)
    for p in sorted((SITE / "tools").glob("*.html")):
        if p.stem == "index":
            continue
        ni = is_noindex(p)
        G.add(f"hub:{p.stem}", 5, f"Tool hub · {title_of(p).split(':')[0].split('—')[0].strip()}", "hub",
              hub_ids.get(p.stem, set()), f"/tools/{p.stem}", hub=True, indexed=not ni)
    page_links: dict[str, set[str]] = {}
    for spec in sorted((DATA / "compare").glob("*.json")):
        d = jload(spec, {})
        kind = d.get("kind") or "compare"
        sub = d.get("dir") or kind
        rel = f"{d['slug']}.html" if sub == "root" else f"{sub}/{d['slug']}.html"
        p = SITE / rel
        if not p.is_file():
            continue
        url = "/" + rel[:-5]
        nid = f"{'sp' if sub == 'root' else kind}:{d['slug']}"
        lbl = {"compare": "Compare", "best": "Best of"}.get(kind, "Page")
        ids = set(as_list(d.get("entries_cited")))
        G.add(nid, 5, f"{lbl} · {d.get('crumb') or d.get('h1') or d['slug']}" if sub != "root" else "System prompts",
              "system-prompts" if sub == "root" else kind, ids, url)
        page_links[nid] = set(re.findall(r'href="/guides/([a-z0-9-]+)', p.read_text(encoding="utf-8", errors="replace")))
    coll_pages = sorted(p.stem for p in (SITE / "collections").glob("*.html") if p.stem != "index")
    G.add("pages:collections", 5, "Collection pages", "collection-pages",
          set().union(*(by_coll.get(c, set()) for c in by_coll)), "/collections/", pages=len(coll_pages))

    # ───────────────────────────── edges
    def zone_nodes(z, kinds=None):
        return [n for n in G.nodes if G.nodes[n]["zone"] == z and (kinds is None or G.nodes[n]["kind"] in kinds)]

    # inverted index: entry -> nodes per zone (fast pair weights)
    node_of_entry: dict[int, dict[str, set[str]]] = {z: defaultdict(set) for z in range(6)}
    for nid, ids in G.members.items():
        z = G.nodes[nid]["zone"]
        for i in ids:
            node_of_entry[z][i].add(nid)

    def pair_weights(za, zb, kinds_a=None, kinds_b=None) -> dict[tuple[str, str], set[str]]:
        out: dict[tuple[str, str], set[str]] = defaultdict(set)
        for i in E:
            As = [a for a in node_of_entry[za].get(i, ()) if kinds_a is None or G.nodes[a]["kind"] in kinds_a]
            if not As:
                continue
            Bs = [b for b in node_of_entry[zb].get(i, ()) if kinds_b is None or G.nodes[b]["kind"] in kinds_b]
            for a in As:
                for b in Bs:
                    out[(a, b)].add(i)
        return out

    GUIDE_K = {"guide"}
    raw: dict[str, dict[tuple[str, str], set[str]]] = {
        "collection-pillar": pair_weights(0, 1, {"collection"}),
        "creator-pillar": pair_weights(0, 1, {"creator", "creator-group"}),
        "pillar-tool": pair_weights(1, 2),
        "tool-technique": pair_weights(2, 3),
        "technique-guide": pair_weights(3, 4),
        "pillar-guide": pair_weights(1, 4),
        "tool-guide": pair_weights(2, 4),
    }
    out_edges: dict[tuple[str, str], tuple[set[str], int]] = {}
    for g in guides:
        gid = f"guide:{g}"
        gids = G.members[gid]
        if f"ps:{g}" in G.nodes:
            out_edges[(gid, f"ps:{g}")] = (gids, max(1, len(gids)))
        if f"kit:{g}" in G.nodes:
            out_edges[(gid, f"kit:{g}")] = (gids, max(1, len(gids)))
        for hn in zone_nodes(5, {"hub"}):
            ov = gids & G.members[hn]
            if len(ov) >= 1:
                out_edges[(gid, hn)] = (ov, len(ov))
        for pn, linked in page_links.items():
            ov = gids & G.members[pn]
            if ov or g in linked:
                out_edges[(gid, pn)] = (ov, max(1, len(ov)))

    min_w = {k: MIN_W for k in raw}

    def kept() -> list[tuple[str, str, str, set[str]]]:
        rows = []
        for kind, pairs in raw.items():
            for (a, b), ids in pairs.items():
                if len(ids) >= min_w[kind]:
                    rows.append((kind, a, b, ids))
        return rows

    # node budget: drop the thinnest zone-2/3 nodes first if over the cap (tools keep priority over models/repos)
    if len(G.nodes) > MAX_NODES:
        drop = sorted((n for n in G.nodes if G.nodes[n]["zone"] in (2, 3)),
                      key=lambda n: (len(G.members[n]), G.nodes[n]["kind"] == "tool", n))[: len(G.nodes) - MAX_NODES]
        for n in drop:
            del G.nodes[n]
            del G.members[n]
        for kind in raw:
            raw[kind] = {k: v for k, v in raw[kind].items() if k[0] in G.nodes and k[1] in G.nodes}

    # edge budget: raise the min weight of the densest droppable kind until under MAX_EDGES
    while len(kept()) + len(out_edges) > MAX_EDGES:
        counts = Counter(k for k, *_ in kept())
        kind = max((k for k in counts if not k.startswith("collection")), key=lambda k: (counts[k], k))
        min_w[kind] += 1

    edges = []
    for kind, a, b, ids in kept():
        edges.append((a, b, len(ids), kind, ids))
    for (a, b), (ids, w) in out_edges.items():
        bk = G.nodes[b]["kind"]
        edges.append((a, b, w, "guide-" + {"prompt-system": "prompt", "system-prompts": "prompt",
                                             "collection-pages": "page"}.get(bk, bk), ids))
    edges.sort(key=lambda r: (G.nodes[r[0]]["zone"], r[0], r[1]))

    # finalize nodes
    nodes_out = [G.finish_node(n, lane_of) for n in G.nodes]
    edges_out = []
    for a, b, w, kind, ids in edges:
        mix = Counter(tier_of(E[i]) for i in ids)
        lanes = Counter(l for i in ids for l in lane_of[i])
        edges_out.append({"source": a, "target": b, "weight": w, "kind": kind,
                          "tiers": [mix.get(t, 0) for t in TIERS],
                          "lanes": [lanes.get(l, 0) for l in LANE_ORDER]})

    # compact entry lookup for every id the page can show
    used = set()
    for n in nodes_out:
        used.update(n["entries"])
    e_dir = SITE / "e"
    elook = {}
    for i in sorted(used):
        e = E[i]
        s = safe_slug(i)
        elook[i] = {"t": e.get("title") or i, "tier": tier_of(e), "c": e.get("creator") or "",
                    "u": f"/e/{s}" if (e_dir / f"{s}.html").is_file() else f"/catalog#post-{i}"}

    # ───────────────────────────── top paths: creator -> pillar -> tool -> guide -> prompt system
    # Score = entries that travel the WHOLE route (one creator, in the pillar, tagged the tool, inside the guide).
    path_ct: Counter = Counter()
    for g in sorted(guides):
        if f"ps:{g}" not in G.nodes:
            continue
        for i in sorted(G.members.get(f"guide:{g}", ())):
            cr = (E[i].get("creator") or "").lstrip("@")
            cid = f"creator:{cr}"
            if cid not in G.nodes:
                continue
            for p in sorted(pillars_of[i]):
                for t in sorted(tools_of[i]):
                    tid = f"tool:{slug_for(t)}"
                    if tid in G.nodes:
                        path_ct[(cid, f"pillar:{p}", tid, f"guide:{g}", f"ps:{g}")] += 1
    rw: dict[tuple[str, str], int] = {}
    for pairs in raw.values():
        for k, ids in pairs.items():
            rw[k] = max(rw.get(k, 0), len(ids))
    for k, (ids, w) in out_edges.items():
        rw[k] = w
    scored = []
    for route, n in path_ct.items():
        wprod = 1
        for a, b in zip(route, route[1:]):
            wprod *= rw.get((a, b), 1)
        scored.append((wprod, n, route))
    scored.sort(key=lambda r: (-r[0], -r[1], r[2]))
    paths, seen_g = [], set()
    per_creator: Counter = Counter()
    per_tool: Counter = Counter()
    # coherent routes (>= 2 entries travel end to end) first, then fill with single-entry routes
    for wprod, n, route in [r for r in scored if r[1] >= 2] + [r for r in scored if r[1] < 2]:
        if len(paths) == 10:
            break
        if route[3] in seen_g or per_creator[route[0]] >= 2 or per_tool[route[2]] >= 3:
            continue
        seen_g.add(route[3])
        per_creator[route[0]] += 1
        per_tool[route[2]] += 1
        ids = sorted(G.members[route[0]] & pill_ids[route[1][7:]] & G.members[route[2]] & G.members[route[3]])
        paths.append({"rank": len(paths) + 1, "nodes": list(route), "entries": ids, "through": n,
                      "weights": [rw.get((a, b), 1) for a, b in zip(route, route[1:])], "weight_product": wprod,
                      "labels": [G.nodes[x]["label"] for x in route]})

    # ───────────────────────────── gaps
    gaps = []

    def gap(kind, label, metric, suggestion, links, score, node=None):
        gaps.append({"kind": kind, "label": label, "metric": metric, "suggestion": suggestion,
                     "links": links, "score": score, "node": node})

    for p in PILLAR_ORDER:
        if p == "other":
            continue
        n_e, n_g = len(pill_ids.get(p, ())), len(pillar_guides[p])
        ratio = n_e / max(1, n_g)
        if n_e >= 40 and ratio >= 15:
            gap("pillar-thin", PILLAR_LABEL[p], f"{n_e} entries / {n_g} guides = {ratio:.0f} per guide",
                "Write a guide that owns this pillar; pull from its S/A entries.",
                [{"label": "pillar top guide", "url": G.nodes[f'pillar:{p}']["url"]}], round(ratio, 1), f"pillar:{p}")
    for t in sorted(by_tool, key=lambda t: (-len(by_tool[t]), t)):
        n = len(by_tool[t])
        nid = f"tool:{slug_for(t)}"
        if n >= 5 and not (G.nodes.get(nid) or {}).get("indexed"):
            hub = (G.nodes.get(nid) or {}).get("hub")
            gap("tool-no-hub", t, f"{n} entries, " + ("hub is noindex" if hub else "no /tools/ hub"),
                "Raise the hub to indexable (editor take >= 150 words, a guide drawing >= 2)." if hub
                else "Add a data/tools/<slug>.json take and build the hub.",
                [{"label": "hub", "url": f"/tools/{slug_for(t)}"}] if hub else [], n, nid if nid in G.nodes else None)
    for cr in sorted(by_creator, key=lambda c: (-len(by_creator[c]), c)):
        ids = by_creator[cr]
        if len(ids) >= 6 and not any(in_guide.get(i) for i in ids):
            sa = sum(1 for i in ids if tier_of(E[i]) in "SA")
            gap("creator-unguided", "@" + cr, f"{len(ids)} entries ({sa} S/A), 0 in any guide",
                "Check whether this creator's saves form a guide-worthy thread.",
                [{"label": "instagram", "url": f"https://www.instagram.com/{cr}/"}], len(ids), f"creator:{cr}")
    for k in sorted(by_tech, key=lambda k: (-len(by_tech[k]), k)):
        ids = by_tech[k]
        if len(ids) < 6:
            continue
        best = max((len(gd["ids"] & ids) for gd in guides.values()), default=0)
        if best < 2:
            gap("technique-unguided", tdisp[k], f"{len(ids)} entries, no guide uses >= 2 of them",
                "Candidate for a technique guide or a section in an existing one.", [], len(ids),
                f"tech:{kebab(k)}")
    for g in sorted(guides):
        miss = [x for x, ok in (("prompt system", g in packs), ("content kit", g in kits)) if not ok]
        if miss:
            gap("guide-incomplete", guides[g]["title"], "missing " + " and ".join(miss),
                "Run scripts/prompt_systems.py export / content_kit.py for this slug.",
                [{"label": "guide", "url": f"/guides/{g}"}], 5 * len(miss), f"guide:{g}")
    s_out = sorted((i for i, e in E.items() if tier_of(e) == "S" and not in_guide.get(i)),
                   key=lambda i: (_neg(E[i].get("date") or ""), i))
    if s_out:
        gap("s-tier-unguided", "S-tier entries outside every guide", f"{len(s_out)} of "
            f"{sum(1 for e in E.values() if tier_of(e) == 'S')} S-tier entries",
            "Fold the strongest into existing guides or seed a new one. Top 10 linked.",
            [{"label": E[i].get("title") or i, "url": elook.get(i, {}).get("u") or f"/e/{safe_slug(i)}"} for i in s_out[:10]],
            len(s_out) * 2, None)
    for c in sorted(by_coll, key=lambda c: (-len(by_coll[c]), c)):
        ids = by_coll[c]
        cov = sum(1 for i in ids if in_guide.get(i)) / max(1, len(ids))
        if cov < 0.25:
            gap("collection-uncovered", collection_name(c), f"{cov:.0%} of {len(ids)} entries are in a guide",
                "Curate a guide from this collection's S/A entries.",
                [{"label": "collection", "url": collection_url(c)}], round(len(ids) * (0.25 - cov), 1), f"coll:{c}")
    for slug, a in sorted(aff.items()):
        name = a.get("tool") or slug
        n = len(hub_ids.get(slug, set()) | by_tool.get(name, set()))
        if n < 3:
            gap("affiliate-thin", name, f"{n} entries, affiliate status {a.get('status') or '?'}",
                "Too little archive evidence to recommend; keep /go/ links off until saves exist.",
                [{"label": "go link", "url": f"/go/{slug}"}] if a.get("affiliate_url") else [], 3 - n, None)
    kind_rank = {k: i for i, k in enumerate(["s-tier-unguided", "pillar-thin", "tool-no-hub", "creator-unguided",
                                             "technique-unguided", "collection-uncovered", "guide-incomplete",
                                             "affiliate-thin"])}
    gaps.sort(key=lambda g: (-g["score"], kind_rank[g["kind"]], g["label"]))

    # ───────────────────────────── outputs
    zone_counts = []
    for z, name in enumerate(ZONES):
        zn = [n for n in nodes_out if n["zone"] == z]
        zone_counts.append({"zone": z, "name": name, "nodes": len(zn),
                            "edges_out": sum(1 for e in edges_out if G.nodes[e["source"]]["zone"] == z),
                            "kinds": dict(sorted(Counter(n["kind"] for n in zn).items()))})
    data = {
        "version": 1,
        "generated_from": "scripts/build_flow.py",
        "as_of": (cat.get("generated") or "")[:10],
        "zones": ZONES,
        "zone_counts": zone_counts,
        "lanes": LANE_ORDER,
        "lane_patterns": LANES,
        "pillars": [{"key": p, "label": PILLAR_LABEL[p], "url": G.nodes[f"pillar:{p}"]["url"],
                     "entries": len(pill_ids.get(p, ())), "guides": len(pillar_guides[p])} for p in PILLAR_ORDER],
        "totals": {"entries": len(E), "nodes": len(nodes_out), "edges": len(edges_out), "guides": len(guides),
                   "prompt_systems": sum(1 for g in guides if g in packs), "kits": len(kits),
                   "kits_posted": sum(1 for v in kits.values() if v == "posted"),
                   "hubs": sum(1 for n in nodes_out if n["kind"] == "hub"),
                   "hubs_indexed": sum(1 for n in nodes_out if n["kind"] == "hub" and n["indexed"])},
        "thresholds": {"creator": MIN_CREATOR, "tool": MIN_TOOL, "model": MIN_MODEL, "repo": MIN_REPO,
                       "technique": MIN_TECH, "edge_min_weight": min_w},
        "nodes": nodes_out,
        "edges": edges_out,
        "entries": elook,
        "paths": paths,
        "gaps": gaps,
    }
    gaps_doc = {"as_of": data["as_of"], "generated_from": "scripts/build_flow.py", "count": len(gaps),
                "by_kind": dict(sorted(Counter(g["kind"] for g in gaps).items())), "gaps": gaps,
                "s_tier_unguided": s_out, "paths": paths}

    blob = json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=False) + "\n"
    gblob = json.dumps(gaps_doc, ensure_ascii=False, indent=1) + "\n"
    writes = {OUT: blob, OUT_API: blob, OUT_GAPS: gblob}
    if PAGE.is_file():
        writes[PAGE] = patch_summary(PAGE.read_text(encoding="utf-8"), data)

    changed = [p for p, s in writes.items() if not p.is_file() or p.read_text(encoding="utf-8") != s]
    if args.check:
        for p in changed:
            print(f"would change {p.relative_to(ROOT)}")
        return 1 if changed else 0
    for p in changed:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(writes[p], encoding="utf-8")

    # ───────────────────────────── report
    print(f"flow: {len(nodes_out)} nodes, {len(edges_out)} edges, {len(blob)//1024} KB "
          f"({len(changed)} file(s) changed)")
    for zc in zone_counts:
        print(f"  zone {zc['zone']} {zc['name']:<24} nodes {zc['nodes']:>4}  edges out {zc['edges_out']:>4}  {zc['kinds']}")
    print("  edge kinds:", dict(sorted(Counter(e["kind"] for e in edges_out).items())), "min weights:", min_w)
    print(f"gaps: {len(gaps)}  by kind {gaps_doc['by_kind']}")
    for g in gaps[:10]:
        print(f"  [{g['kind']}] {g['label']}: {g['metric']}")
    print("top paths:")
    for p in paths[:5]:
        print(f"  {p['rank']}. " + " -> ".join(p["labels"]) + f"  (weights {p['weights']}, {p['through']} entries end to end)")
    return 0


def patch_summary(text: str, d: dict) -> str:
    """Crawler-visible static summary (zone counts + pillar links) between the flow:summary markers."""
    if SUMMARY_START not in text:
        return text
    esc = html.escape
    t = d["totals"]
    zl = "".join(f"<li><strong>{esc(z['name'])}</strong>: {z['nodes']} nodes</li>" for z in d["zone_counts"])
    pl = "".join(f'<li><a href="{esc(p["url"])}">{esc(p["label"])}</a> · {p["entries"]} entries, '
                 f'{p["guides"]} guides</li>' for p in d["pillars"] if p["key"] not in ("music_art", "other"))
    body = (f'\n<section class="flow-static" aria-label="Archive flow summary">'
            f'<p>{t["entries"]} saved posts flow through {t["nodes"]} nodes and {t["edges"]} links: '
            f'sources, pillars, tools, techniques, {t["guides"]} guides and {t["prompt_systems"]} prompt systems, '
            f'{t["kits"]} content kits ({t["kits_posted"]} posted) and {t["hubs"]} tool hubs '
            f'({t["hubs_indexed"]} indexed). Data: <a href="/api/flow.json">/api/flow.json</a>.</p>'
            f'<h2>Zones</h2><ul>{zl}</ul><h2>Pillars</h2><ul>{pl}</ul></section>\n')
    a = text.index(SUMMARY_START) + len(SUMMARY_START)
    b = text.index(SUMMARY_END)
    return text[:a] + body + text[b:]


if __name__ == "__main__":
    sys.exit(main())
