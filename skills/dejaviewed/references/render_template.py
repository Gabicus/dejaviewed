#!/usr/bin/env python3
"""LoreDrop catalog renderer.

Builds: index.html + ai1/ai2/ai3/ai4 collection pages + guides/<slug>.html.
Two-panel layout, multi-select category filters, color-coded taxonomy,
creator bar chart, on-page sections, quick commands. Mobile-first dark theme.
"""
import json, re
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent
DATA = ROOT / "data"
GUIDES = ROOT / "guides"
OUT = ROOT / "site"
OUT.mkdir(exist_ok=True)
(OUT / "guides").mkdir(exist_ok=True)

HANDLE = "@6ab3"
IG_URL = "https://instagram.com/6ab3"
SKILL = "dejaviewed"
TITLE = "DejaViewed"
TAGLINE = "You've saved this before."
WHY = ('You scroll, you tap save, you swear you\'ll come back. You don\'t. Your Saved tab fills up '
       'with posts you half-remember — the tool you wanted to try, the repo someone teased, the '
       '"comment LINK to get it" that you never commented on. The signal is in there. The format '
       f'just hides it. {TITLE} hands the whole pile to Claude: every save gets read, classified, '
       'tiered, and — for the ones worth the dig — turned into a real deep-dive guide with the '
       'links the creator wouldn\'t give you. The result is this site. Searchable. Findable. Yours.')

# ---------- load data ----------
posts = [json.loads(l) for l in (DATA / "catalog.jsonl").read_text().splitlines() if l.strip()]
posts = [p for p in posts if not p.get("drop")]
curation = json.loads((DATA / "curation.json").read_text())
tiers = curation.get("tiers", {})
buckets = curation.get("buckets", {})
stacks = curation.get("stacks", [])

guide_files = sorted(f.stem for f in GUIDES.glob("*.md"))
guide_titles = {}
for slug in guide_files:
    first = (GUIDES / f"{slug}.md").read_text().splitlines()[0]
    guide_titles[slug] = first.lstrip("# ").strip()

# guide confidence (based on source-quality during research phase)
GUIDE_CONFIDENCE = {
    "gemini-cli":"high","claude-code-hooks-system":"high","claude-code-parallel-worktrees":"high",
    "boris-cherny-claude-md":"high","n8n-mcp-and-obsidian-skills":"high","onyx-self-hosted-ai":"high",
    "hunyuan3d-2":"high","blender-mcp-tripo-pipeline":"high","avellaneda-stoikov-and-hawkes":"high",
    "polymarket-weather-trading":"high","polymarket-99c-limit-arbitrage":"high",
    "quant-project-ideas-list":"high","llms-txt-standard":"high","l1b3rt4s-jailbreak-repo":"high",
    "claude-code-leaked-system-prompt":"medium","primer-md-pattern":"medium",
    "openscreen-screen-recorder":"medium","world-labs-3d-generation":"medium",
}

# ---------- category derivation ----------
ART_DOMAINS = {"3d","image-gen","creative-coding","video-gen"}
DESIGN_DOMAINS = {"design"}
UIUX_KEYWORDS = ["ui","ux","interface","figma","shadcn","tailwind"]
PLATFORM_TOOLS = {"n8n","obsidian","notion","make","zapier","supabase","vercel","cloudflare","huggingface","replicate","modal","runpod","openrouter","lmstudio","ollama","openwebui"}

def categories_for(p):
    cats = set()
    t = p.get("type","")
    if t == "repo" or p.get("repos_or_projects_mentioned"):
        cats.add("repo")
    if t == "tool" or p.get("tools_mentioned"):
        cats.add("tool")
    if t == "technique" or p.get("techniques_mentioned"):
        cats.add("skill")
    if t == "tutorial" or p.get("guide_slug"):
        cats.add("guide")
    doms = set(p.get("domains") or [])
    if doms & ART_DOMAINS: cats.add("art")
    if doms & DESIGN_DOMAINS: cats.add("design")
    techs_lower = " ".join(p.get("techniques_mentioned") or []).lower()
    tools_lower = " ".join(p.get("tools_mentioned") or []).lower()
    if any(k in techs_lower or k in tools_lower for k in UIUX_KEYWORDS) or "design" in doms:
        cats.add("uiux")
    if any(pt in tools_lower for pt in PLATFORM_TOOLS):
        cats.add("platform")
    if not cats:
        cats.add("resource")
    return sorted(cats)

# attach computed fields
for p in posts:
    p["tier"] = tiers.get(p["post_url"], "C")
    dd = p.get("deep_dive_topic")
    p["guide_slug"] = dd if dd in guide_titles else None
    p["categories"] = categories_for(p)
    # title: use enriched card_title from catalog.jsonl if present; fallback only if missing
    if not p.get("card_title"):
        if p.get("repos_or_projects_mentioned"):
            p["card_title"] = p["repos_or_projects_mentioned"][0]
        elif p.get("tools_mentioned"):
            p["card_title"] = p["tools_mentioned"][0]
        elif p.get("techniques_mentioned"):
            p["card_title"] = p["techniques_mentioned"][0].title()
        else:
            s = (p.get("summary") or p.get("caption_original") or "").strip()
            p["card_title"] = (" ".join(s.split()[:7]) if s else "Untitled save")[:60]

# ---------- creator stats ----------
creator_counts = Counter(p["creator"] for p in posts if p.get("creator"))
top_creators = creator_counts.most_common(12)
total_creators = len(creator_counts)

# ---------- CSS ----------
CSS = r"""
:root{
  --bg:#0a0a0f;--bg-2:#0f0f1a;--surface:#12121a;
  --panel:rgba(255,255,255,0.03);--panel-2:rgba(255,255,255,0.05);
  --border:rgba(255,255,255,0.08);--border-hi:rgba(255,255,255,0.15);
  --text:#e8e8f0;--text-dim:#a0a0b8;--text-mute:#6a6a80;
  --accent:#a78bfa;--accent-2:#f472b6;
  --c-repo:#4cda8c;--c-tool:#f0a050;--c-skill:#e060a0;--c-guide:#a78bfa;
  --c-platform:#e0d040;--c-resource:#40d0e0;--c-art:#f05060;--c-design:#fb7185;--c-uiux:#60a5fa;
  --s:#fbbf24;--a:#a78bfa;--b:#60a5fa;--c:#6a6a80;
  --radius:14px;--radius-sm:8px;
}
*{box-sizing:border-box}html,body{margin:0;padding:0}
body{font-family:'SF Mono','Fira Code','JetBrains Mono',Menlo,monospace;background:var(--bg);color:var(--text);line-height:1.6;-webkit-font-smoothing:antialiased;min-height:100vh;
  background-image:radial-gradient(ellipse 80% 50% at 50% -20%,rgba(167,139,250,0.18),transparent),radial-gradient(ellipse 60% 40% at 80% 10%,rgba(244,114,182,0.10),transparent),radial-gradient(ellipse 60% 40% at 20% 10%,rgba(96,165,250,0.10),transparent);
  background-attachment:fixed}
a{color:var(--accent);text-decoration:none}a:hover{color:var(--accent-2)}
.wrap{max-width:1500px;margin:0 auto;padding:0 22px}
header.site{border-bottom:1px solid var(--border);padding:22px 0;backdrop-filter:blur(20px);background:rgba(10,10,15,0.7);position:sticky;top:0;z-index:100}
.head-row{display:flex;flex-wrap:wrap;gap:16px;align-items:center;justify-content:space-between}
.brand h1{margin:0;font-size:32px;font-weight:900;letter-spacing:-0.03em;background:linear-gradient(135deg,#fff 0%,#a78bfa 45%,#f472b6 100%);-webkit-background-clip:text;background-clip:text;color:transparent}
.brand .tagline{color:var(--text-dim);font-size:13px;font-weight:500;margin-top:2px}
.brand .tagline a{color:var(--accent-2);font-weight:700}
.nav{display:flex;gap:6px;flex-wrap:wrap}
.nav a{padding:8px 14px;border-radius:999px;font-size:12px;font-weight:700;background:var(--panel);border:1px solid var(--border);color:var(--text-dim);transition:all .15s;text-transform:uppercase;letter-spacing:.05em}
.nav a:hover{background:var(--panel-2);color:var(--text);border-color:var(--border-hi)}
.nav a.active{background:linear-gradient(135deg,rgba(167,139,250,.25),rgba(244,114,182,.25));border-color:rgba(167,139,250,.5);color:#fff}
.src-group{display:inline-flex;align-items:center;gap:2px;padding:3px 4px 3px 0;border-radius:999px;background:var(--panel);border:1px solid var(--border)}
.src-group.active-group{border-color:rgba(167,139,250,.4)}
.src-label{padding:6px 10px;font-size:11px;font-weight:700;color:var(--text-mute);text-transform:uppercase;letter-spacing:.06em;white-space:nowrap}
.sub-links{display:inline-flex;gap:2px}
.sub-links a.sub{padding:6px 10px;border-radius:999px;font-size:11px;font-weight:700;color:var(--text-dim);background:transparent;border:1px solid transparent;transition:all .15s;text-transform:uppercase;letter-spacing:.04em}
.sub-links a.sub:hover{background:var(--panel-2);color:var(--text);border-color:var(--border-hi)}
.sub-links a.sub.active{background:linear-gradient(135deg,rgba(167,139,250,.25),rgba(244,114,182,.25));border-color:rgba(167,139,250,.5);color:#fff}

.skill-callout{margin:22px 0 0;padding:20px 22px;background:linear-gradient(135deg,rgba(167,139,250,.08),rgba(244,114,182,.05));border:1px solid rgba(167,139,250,.25);border-radius:var(--radius);font-size:14px}
.skill-callout strong{color:#fff}
.skill-callout code{background:rgba(0,0,0,.45);border:1px solid var(--border);padding:2px 8px;border-radius:6px;font-size:12.5px;font-family:'JetBrains Mono',Menlo,monospace;color:var(--accent)}
.skill-callout details{margin-top:12px}
.skill-callout summary{cursor:pointer;color:var(--accent);font-weight:700;padding:6px 0}
.skill-callout pre{margin:10px 0 0;padding:14px;background:rgba(0,0,0,.55);border:1px solid var(--border);border-radius:var(--radius-sm);overflow-x:auto;font-size:12px;line-height:1.55;font-family:'JetBrains Mono',Menlo,monospace;color:var(--text-dim);white-space:pre-wrap}

.hero{padding:30px 0 8px}
.hero-grid{display:grid;grid-template-columns:1fr 1fr;gap:24px;align-items:stretch}
.hero-left{display:flex;flex-direction:column}
.hero h2{font-size:clamp(30px,4.5vw,48px);margin:0 0 12px;font-weight:900;letter-spacing:-0.035em;line-height:1.05;background:linear-gradient(135deg,#fff 0%,#fff 50%,#a78bfa 100%);-webkit-background-clip:text;background-clip:text;color:transparent}
.hero p.why{font-size:15px;color:var(--text-dim);margin:0 0 18px}
@media(max-width:900px){.hero-grid{grid-template-columns:1fr}.grid{column-count:1}}

/* BANS strip */
.bans{display:grid;gap:10px;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));margin:auto 0 0}
.ban{padding:14px 16px;background:var(--panel);border:1px solid var(--border);border-radius:var(--radius)}
.ban .v{font-size:24px;font-weight:900;color:#fff;line-height:1}
.ban .l{font-size:10.5px;text-transform:uppercase;letter-spacing:.09em;color:var(--text-mute);margin-top:6px;font-weight:700}

/* Two-panel layout */
.layout{display:grid;grid-template-columns:280px 1fr;gap:28px;margin-top:30px;align-items:flex-start}
.sidebar{position:sticky;top:96px;background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);padding:20px;max-height:calc(100vh - 120px);overflow-y:auto}
.sidebar h4{font-size:11px;text-transform:uppercase;letter-spacing:.1em;color:var(--text-mute);margin:0 0 10px;font-weight:800}
.sidebar h4:not(:first-child){margin-top:18px}
.search{width:100%;background:rgba(0,0,0,.35);border:1px solid var(--border);border-radius:10px;padding:11px 14px;color:var(--text);font-size:13.5px;font-family:inherit;transition:all .15s}
.search:focus{outline:none;border-color:var(--accent)}
.btn-group{display:flex;flex-direction:column;gap:5px}
.cat-btn{display:flex;align-items:center;justify-content:space-between;gap:8px;padding:8px 12px;border-radius:8px;font-size:12.5px;font-weight:700;background:transparent;border:1px solid var(--border);color:var(--text-dim);cursor:pointer;text-align:left;font-family:inherit;transition:all .12s}
.cat-btn .dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.cat-btn .n{color:var(--text-mute);font-size:11px;font-weight:600}
.cat-btn:hover{background:var(--panel-2);color:var(--text)}
.cat-btn.on{background:var(--panel-2);color:#fff;border-color:var(--border-hi)}
.cat-btn.on .n{color:var(--text)}
.cat-btn[data-cat="all"].on{background:linear-gradient(135deg,rgba(167,139,250,.25),rgba(244,114,182,.25));border-color:rgba(167,139,250,.5)}
.cat-btn[data-cat="repo"] .dot{background:var(--c-repo)} .cat-btn[data-cat="repo"].on{border-color:var(--c-repo);box-shadow:inset 3px 0 0 var(--c-repo)}
.cat-btn[data-cat="tool"] .dot{background:var(--c-tool)} .cat-btn[data-cat="tool"].on{border-color:var(--c-tool);box-shadow:inset 3px 0 0 var(--c-tool)}
.cat-btn[data-cat="skill"] .dot{background:var(--c-skill)} .cat-btn[data-cat="skill"].on{border-color:var(--c-skill);box-shadow:inset 3px 0 0 var(--c-skill)}
.cat-btn[data-cat="guide"] .dot{background:var(--c-guide)} .cat-btn[data-cat="guide"].on{border-color:var(--c-guide);box-shadow:inset 3px 0 0 var(--c-guide)}
.cat-btn[data-cat="platform"] .dot{background:var(--c-platform)} .cat-btn[data-cat="platform"].on{border-color:var(--c-platform);box-shadow:inset 3px 0 0 var(--c-platform)}
.cat-btn[data-cat="resource"] .dot{background:var(--c-resource)} .cat-btn[data-cat="resource"].on{border-color:var(--c-resource);box-shadow:inset 3px 0 0 var(--c-resource)}
.cat-btn[data-cat="art"] .dot{background:var(--c-art)} .cat-btn[data-cat="art"].on{border-color:var(--c-art);box-shadow:inset 3px 0 0 var(--c-art)}
.cat-btn[data-cat="design"] .dot{background:var(--c-design)} .cat-btn[data-cat="design"].on{border-color:var(--c-design);box-shadow:inset 3px 0 0 var(--c-design)}
.cat-btn[data-cat="uiux"] .dot{background:var(--c-uiux)} .cat-btn[data-cat="uiux"].on{border-color:var(--c-uiux);box-shadow:inset 3px 0 0 var(--c-uiux)}

.tier-row{display:flex;gap:5px;flex-wrap:wrap}
.tier-pill{padding:6px 11px;border-radius:999px;font-size:11px;font-weight:900;background:transparent;border:1px solid var(--border);color:var(--text-dim);cursor:pointer;font-family:inherit;letter-spacing:.05em}
.tier-pill[data-t="S"].on{background:rgba(251,191,36,.15);color:var(--s);border-color:var(--s)}
.tier-pill[data-t="A"].on{background:rgba(167,139,250,.15);color:var(--a);border-color:var(--a)}
.tier-pill[data-t="B"].on{background:rgba(96,165,250,.15);color:var(--b);border-color:var(--b)}
.tier-pill[data-t="C"].on{background:rgba(106,106,128,.15);color:var(--c);border-color:#888}

.coll-row{display:flex;gap:4px;flex-wrap:wrap}
.coll-pill{padding:5px 10px;border-radius:6px;font-size:10.5px;font-weight:800;background:transparent;border:1px solid var(--border);color:var(--text-dim);cursor:pointer;font-family:inherit;text-transform:uppercase;letter-spacing:.06em}
.coll-pill.on{background:var(--panel-2);color:#fff;border-color:var(--border-hi)}

.sort-select{width:100%;background:rgba(0,0,0,.35);border:1px solid var(--border);border-radius:8px;padding:9px 11px;color:var(--text);font-size:12.5px;font-family:inherit;cursor:pointer}

/* Main panel */
.main{min-width:0}
.section-head{display:flex;align-items:baseline;justify-content:space-between;gap:10px;margin:32px 0 14px}
.section-head:first-child{margin-top:0}
.section-head h3{margin:0;font-size:22px;font-weight:900;letter-spacing:-0.015em;display:flex;align-items:center;gap:10px}
.section-head h3 .icon{width:28px;height:28px;border-radius:7px;display:inline-flex;align-items:center;justify-content:center;font-size:13px;font-weight:900;color:#0a0a0f}
.section-head .count{color:var(--text-mute);font-size:13px;font-weight:600}
.section-sub{color:var(--text-dim);font-size:13.5px;margin:-8px 0 14px}

/* Creators panel */
.creators{background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);padding:18px 18px 14px;display:flex;flex-direction:column;min-height:0}
.creators h3{margin:0 0 2px;font-size:15px;font-weight:900;letter-spacing:-0.01em;display:flex;align-items:center;gap:8px}
.creators .sub{color:var(--text-dim);font-size:11.5px;margin-bottom:12px;line-height:1.45}
.bar-scroll{flex:1;overflow-y:auto;padding-right:6px;max-height:170px}
.bar-scroll::-webkit-scrollbar{width:6px}
.bar-scroll::-webkit-scrollbar-track{background:transparent}
.bar-scroll::-webkit-scrollbar-thumb{background:rgba(255,255,255,.1);border-radius:3px}
.bar-list{display:flex;flex-direction:column;gap:5px}
.bar-row{display:grid;grid-template-columns:100px 1fr 24px;gap:8px;align-items:center;font-size:11.5px}
.bar-row a.handle{font-weight:700;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:11px}
.bar-row a.handle:hover{color:var(--accent)}
.bar-track{display:flex;height:7px;background:rgba(255,255,255,.04);border-radius:3px;border:1px solid var(--border);gap:1px;padding:0;overflow:hidden}
.seg{flex:0 0 auto;height:100%;cursor:pointer;transition:transform .1s,filter .1s}
.seg:hover{transform:scaleY(1.15);filter:brightness(1.4)}
.seg.tS{background:var(--s)}
.seg.tA{background:var(--a)}
.seg.tB{background:var(--b)}
.seg.tC{background:var(--c)}
.bar-row .n{color:var(--text-mute);font-weight:700;text-align:right;font-size:11px}
.creators .legend{display:flex;gap:10px;font-size:10px;color:var(--text-mute);margin-top:10px;padding-top:10px;border-top:1px solid var(--border)}
.creators .legend span{display:flex;align-items:center;gap:4px}
.creators .legend i{width:8px;height:8px;border-radius:2px;display:inline-block}

/* Quick commands */
.commands{background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);padding:20px}
.commands h3{font-size:13px;text-transform:uppercase;letter-spacing:.1em;color:var(--accent);margin:0 0 12px;font-weight:800}
.cmd-row{display:flex;align-items:center;gap:12px;padding:6px 0;font-size:12.5px}
.cmd-row code{background:rgba(0,0,0,.5);border:1px solid var(--border);padding:5px 11px;border-radius:5px;color:var(--c-repo);font-family:'JetBrains Mono',Menlo,monospace;font-size:12px;flex-shrink:0;white-space:nowrap}
.cmd-row span{color:var(--text-dim)}

/* Cards grid */
.grid{column-count:3;column-gap:15px;margin-bottom:18px}
@media(max-width:1200px){.grid{column-count:2}}
.grid > .card{break-inside:avoid;display:inline-block;width:100%;margin-bottom:15px}
.grid > h3{column-span:all}
.links{margin-top:12px;padding-top:10px;border-top:1px dashed var(--border);display:flex;flex-wrap:wrap;gap:6px}
.links a{font-size:11px;padding:3px 8px;background:rgba(255,255,255,.04);border:1px solid var(--border);border-radius:6px;color:var(--text-dim);text-decoration:none;transition:all .15s;max-width:100%;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.links a:hover{background:rgba(167,139,250,.12);border-color:var(--c-skill);color:#fff}
.card{background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);padding:18px;display:flex;flex-direction:column;transition:all .18s;position:relative;overflow:hidden;border-left-width:3px}
.thumb{display:block;margin:14px -18px -18px -18px;aspect-ratio:5/2;overflow:hidden;background:#0a0a12;border-top:1px solid var(--border)}
.thumb img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .3s}
.card:hover .thumb img{transform:scale(1.04)}
.card.cat-repo{border-left-color:var(--c-repo)}
.card.cat-tool{border-left-color:var(--c-tool)}
.card.cat-skill{border-left-color:var(--c-skill)}
.card.cat-guide{border-left-color:var(--c-guide)}
.card.cat-platform{border-left-color:var(--c-platform)}
.card.cat-resource{border-left-color:var(--c-resource)}
.card.cat-art{border-left-color:var(--c-art)}
.card.cat-design{border-left-color:var(--c-design)}
.card.cat-uiux{border-left-color:var(--c-uiux)}
.card:hover{background:var(--panel-2);border-color:var(--border-hi);transform:translateY(-2px)}
.card .ctitle{font-size:13px;font-weight:800;color:#fff;margin:0 0 6px;letter-spacing:0;line-height:1.35}
.card .top{display:flex;align-items:flex-start;justify-content:space-between;gap:10px;margin-bottom:10px}
.card .meta{font-size:11px;color:var(--text-mute)}
.card .meta a{color:var(--accent);font-weight:600}
.tier{font-size:9.5px;font-weight:900;padding:3px 8px;border-radius:5px;text-transform:uppercase;letter-spacing:.08em;border:1px solid;flex-shrink:0}
.tier.S{color:var(--s);border-color:rgba(251,191,36,.4);background:rgba(251,191,36,.08)}
.tier.A{color:var(--a);border-color:rgba(167,139,250,.4);background:rgba(167,139,250,.08)}
.tier.B{color:var(--b);border-color:rgba(96,165,250,.4);background:rgba(96,165,250,.08)}
.tier.C{color:var(--c);border-color:rgba(106,106,128,.4);background:rgba(106,106,128,.08)}
.card .sum-wrap{flex:1;display:flex;flex-direction:column}
.card .summary{font-size:12px;color:var(--text-dim);line-height:1.6;margin:0;letter-spacing:0.01em}
.cat-chips{display:flex;flex-wrap:wrap;gap:4px;margin-top:10px;padding-top:10px;border-top:1px solid var(--border)}
.chip{font-size:9px;padding:2px 6px;border-radius:4px;font-weight:600;background:rgba(255,255,255,.03);border:1px solid var(--border);color:var(--text-mute);text-transform:uppercase;letter-spacing:.04em;line-height:1.4}
.chip.repo{color:var(--c-repo);border-color:rgba(76,218,140,.28)}
.chip.tool{color:var(--c-tool);border-color:rgba(240,160,80,.28)}
.chip.skill{color:var(--c-skill);border-color:rgba(224,96,160,.28)}
.chip.guide{color:var(--c-guide);border-color:rgba(167,139,250,.28)}
.chip.platform{color:var(--c-platform);border-color:rgba(224,208,64,.28)}
.chip.resource{color:var(--c-resource);border-color:rgba(64,208,224,.28)}
.chip.art{color:var(--c-art);border-color:rgba(240,80,96,.28)}
.chip.design{color:var(--c-design);border-color:rgba(251,113,133,.28)}
.chip.uiux{color:var(--c-uiux);border-color:rgba(96,165,250,.28)}
.card .actions{display:flex;gap:8px;margin-top:14px;padding-top:14px;border-top:1px solid var(--border)}
.btn{flex:1;text-align:center;padding:8px 12px;border-radius:8px;font-size:12px;font-weight:700;border:1px solid var(--border);background:var(--panel);color:var(--text);transition:all .15s}
.btn:hover{background:var(--panel-2);border-color:var(--border-hi);color:#fff}
.btn.primary{background:linear-gradient(135deg,rgba(167,139,250,.2),rgba(244,114,182,.2));border-color:rgba(167,139,250,.4);color:#fff}
.btn.primary:hover{background:linear-gradient(135deg,rgba(167,139,250,.3),rgba(244,114,182,.3))}
.btn.browse{background:rgba(76,218,140,.15);border-color:rgba(76,218,140,.4);color:var(--c-repo)}
.btn.browse:hover{background:rgba(76,218,140,.25)}

footer.site{margin:60px 0 40px;padding-top:30px;border-top:1px solid var(--border);color:var(--text-mute);font-size:12.5px;text-align:center}
footer.site a{color:var(--text-dim)}
footer.site code{background:rgba(0,0,0,.5);border:1px solid var(--border);padding:2px 7px;border-radius:5px;color:var(--accent);font-family:'JetBrains Mono',Menlo,monospace;font-size:11.5px}

@media(max-width:900px){
  .layout{grid-template-columns:1fr}
  .sidebar{position:relative;top:0;max-height:none}
}
@media(max-width:640px){
  .brand h1{font-size:24px}
  .hero h2{font-size:30px}
  header.site{position:static}
  .grid{grid-template-columns:1fr}
  .bar-row{grid-template-columns:110px 1fr 30px}
}

/* Guide page */
.guide{max-width:780px;margin:30px auto;padding:0 22px;font-size:16px;line-height:1.75}
.guide h1,.guide h2,.guide h3{color:#fff;letter-spacing:-0.01em;margin-top:1.7em}
.guide h1{font-size:34px;font-weight:900;margin-top:0;background:linear-gradient(135deg,#fff 0%,#a78bfa 60%,#f472b6 100%);-webkit-background-clip:text;background-clip:text;color:transparent}
.guide h2{font-size:24px;border-bottom:1px solid var(--border);padding-bottom:6px}
.guide h3{font-size:18px}.guide p{color:var(--text)}
.guide code{background:rgba(255,255,255,.07);padding:2px 6px;border-radius:4px;font-family:'JetBrains Mono',Menlo,monospace;font-size:.9em;color:var(--accent)}
.guide pre{background:rgba(0,0,0,.55);border:1px solid var(--border);padding:16px;border-radius:var(--radius-sm);overflow-x:auto}
.guide pre code{background:none;padding:0;color:var(--text)}
.guide blockquote{border-left:3px solid var(--accent);padding-left:16px;color:var(--text-dim);margin:16px 0}
.guide a{color:var(--accent);text-decoration:underline;text-decoration-color:rgba(167,139,250,.3)}
.guide a:hover{text-decoration-color:var(--accent)}
.guide hr{border:none;border-top:1px solid var(--border);margin:30px 0}
.guide ul,.guide ol{padding-left:24px}
.confidence-badge{display:inline-block;padding:4px 10px;border-radius:6px;font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:.06em;margin-bottom:18px}
.confidence-badge.high{background:rgba(76,218,140,.12);color:var(--c-repo);border:1px solid rgba(76,218,140,.4)}
.confidence-badge.medium{background:rgba(240,160,80,.12);color:var(--c-tool);border:1px solid rgba(240,160,80,.4)}
"""

# ---------- helpers ----------
def esc(s): return (s or "").replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"',"&quot;")

def handle_to_url(handle):
    if not handle: return None
    h = handle.lstrip("@").strip()
    return f"https://instagram.com/{h}" if h else None

def header_html(active, prefix=""):
    # Source groups: label → [(key, sublabel), ...]
    sources = [
        ("instagram", "Instagram", [("ai1","AI1"),("ai2","AI2"),("ai3","AI3"),("ai4","AI4")]),
        # Future sources get added here:
        # ("chrome", "Chrome", [("chrome","Bookmarks")]),
        # ("tiktok", "TikTok", []),
        # ("twitter", "Twitter / X", []),
        # ("youtube", "YouTube", []),
    ]
    # Build nav: Playbook first, then All, then source groups
    nav = []
    # Playbook
    cls = "actions-nav active" if active == "actions" else "actions-nav"
    nav.append(f'<a class="{cls}" href="{prefix}">DEJAVIEWED</a>')
    # All
    cls = "active" if active == "index" else ""
    nav.append(f'<a class="{cls.strip()}" href="{prefix}catalog.html">ALL</a>')
    # Source groups
    for src_id, src_label, subs in sources:
        # Source label (non-clickable or clicks to first sub)
        first_href = f"{prefix}{subs[0][0]}.html" if subs else "#"
        is_active = active in [s[0] for s in subs]
        group_cls = "src-group"
        if is_active: group_cls += " active-group"
        sub_links = []
        for key, sublabel in subs:
            scls = "sub active" if active == key else "sub"
            sub_links.append(f'<a class="{scls}" href="{prefix}{key}.html">{sublabel}</a>')
        subs_html = f'<span class="sub-links">{"".join(sub_links)}</span>' if sub_links else ""
        nav.append(f'<span class="{group_cls}"><span class="src-label">{src_label}</span>{subs_html}</span>')
    return f"""<header class="site"><div class="wrap head-row">
  <div class="brand">
    <h1>{TITLE}</h1>
    <div class="tagline">{TAGLINE} · Curated by <a href="{IG_URL}">{HANDLE}</a></div>
  </div>
  <nav class="nav">{''.join(nav)}</nav>
</div></header>"""

EXAMPLE_PROMPT = """Hi Claude. I have these Instagram saved collections — please run the dejaviewed workflow on them:

https://www.instagram.com/<user>/saved/<collection>/<id>/
https://www.instagram.com/<user>/saved/<collection-2>/<id2>/

Full pipeline:
 1. Scrape every post (cookies+requests primary, MCP Playwright fallback). Cookie-safe.
 2. Classify every post (summary, type, domains, tools, repos, audience, deep-dive flag).
 3. Write a deep-dive guide for every high-signal topic in guides/<slug>.md and clone the repo.
 4. Curate S/A/B/C tiers, thematic buckets, project stacks, and a 'start here' list.
 5. Render a mobile-first dark HTML catalog: one page per collection + combined index.
 6. Header callout crediting my IG handle and explaining how to install/invoke dejaviewed.

My IG handle is @myhandle."""

def skill_callout_html():
    return f"""<div class="wrap"><div class="skill-callout">
  <strong>✨ Built with the <code>{SKILL}</code> skill for Claude Code.</strong> {TAGLINE}
  <div style="margin-top:10px;color:var(--text-dim)">
    <strong>Install:</strong> <code>/plugin install {SKILL}</code> &nbsp;·&nbsp;
    <strong>Invoke:</strong> <code>/{SKILL} &lt;instagram-saved-url&gt;</code> &nbsp;·&nbsp;
    or just ask Claude: <em>"dejaviewed these IG saves"</em>
  </div>
  <details><summary>📋 Copy the example prompt that built this catalog</summary>
<pre>{esc(EXAMPLE_PROMPT)}</pre></details>
  <div style="margin-top:10px;color:var(--text-mute);font-size:12px">Cookie-safe scraping: cookie values are never logged, printed, or written to disk — only existence checks.</div>
</div></div>"""

def hero_html(coll, ps):
    if coll == "all":
        h2 = TITLE
        sub = WHY
    else:
        meta = COLL_META[coll]
        h2 = meta[0]
        sub = meta[1]
    bans = bans_inner_html(ps)
    creators = creators_html(ps)
    return f'''<section class="hero"><div class="wrap">
  <div class="hero-grid">
    <div class="hero-left">
      <h2>{h2}</h2>
      <p class="why">{sub}</p>
      {bans}
    </div>
    <div>{creators}</div>
  </div>
</div></section>'''

COLL_META = {
    "ai1":("AI1 — Foundations & Agents","Claude Code craft, agent patterns, prompt engineering, jailbreaks, and the LLM underpinnings that anchor the rest of the catalog."),
    "ai2":("AI2 — Open Source & Tools","Self-hosted models, open terminals, developer tools, and the weekend-build surface area for a solo engineer."),
    "ai3":("AI3 — Research & Resources","The original hand-curated catalog: trading agents, creative coding, worldbuilding, design systems."),
    "ai4":("AI4 — Frontier & Experiments","The newest saves: 3D generation, Polymarket plays, quant ideas, the frontier edge."),
}

# ---------- BANS ----------
def bans_inner_html(ps):
    tc = Counter(p["tier"] for p in ps)
    n_creators = len({p["creator"] for p in ps if p.get("creator")})
    n_repos = sum(1 for p in ps if "repo" in p["categories"])
    n_guides = sum(1 for p in ps if p.get("guide_slug"))
    return f'''<div class="bans">
  <div class="ban"><div class="v">{len(ps)}</div><div class="l">Posts</div></div>
  <div class="ban"><div class="v">{n_creators}</div><div class="l">Creators</div></div>
  <div class="ban"><div class="v">{tc.get("S",0)}</div><div class="l">S-tier</div></div>
  <div class="ban"><div class="v">{tc.get("A",0)}</div><div class="l">A-tier</div></div>
  <div class="ban"><div class="v">{n_repos}</div><div class="l">Repos</div></div>
  <div class="ban"><div class="v">{n_guides}</div><div class="l">Deep dives</div></div>
  <div class="ban"><div class="v">{len(stacks)}</div><div class="l">Stacks</div></div>
</div>'''

# ---------- Sidebar ----------
CAT_LABELS = [("all","All"),("repo","Repos"),("guide","Guides"),("skill","Skills"),("tool","Tools"),("platform","Platforms"),("resource","Resources"),("art","Art"),("design","Design"),("uiux","UI / UX")]

def sidebar_html(ps, fixed_collection):
    cat_counts = Counter()
    for p in ps:
        for c in p["categories"]: cat_counts[c] += 1
    cat_counts["all"] = len(ps)
    btns = []
    for k,label in CAT_LABELS:
        n = cat_counts.get(k,0)
        on = " on" if k == "all" else ""
        btns.append(f'<button class="cat-btn{on}" data-cat="{k}"><span><span class="dot"></span> {label}</span><span class="n">{n}</span></button>')
    coll_pills = ""
    if not fixed_collection:
        coll_pills = '<h4>Collection</h4><div class="coll-row">' + "".join(
            f'<button class="coll-pill" data-coll="{c}">{c.upper()}</button>' for c in ["ai1","ai2","ai3","ai4"]
        ) + '</div>'
    return f"""<aside class="sidebar">
  <h4>Search</h4>
  <input id="search" class="search" placeholder="captions, tools, repos…">
  <h4>Category</h4>
  <div class="btn-group">{''.join(btns)}</div>
  <h4>Tier</h4>
  <div class="tier-row">
    <button class="tier-pill" data-t="S">S</button>
    <button class="tier-pill" data-t="A">A</button>
    <button class="tier-pill" data-t="B">B</button>
    <button class="tier-pill" data-t="C">C</button>
  </div>
  {coll_pills}
  <h4>Sort</h4>
  <select id="sort" class="sort-select">
    <option value="tier">Tier (S→C)</option>
    <option value="date">Date (newest)</option>
    <option value="creator">Creator (A→Z)</option>
  </select>
</aside>"""

# ---------- Creators panel ----------
def post_anchor(p):
    # short anchor from post URL slug
    m = re.search(r"/p/([^/]+)/?", p["post_url"])
    return "post-" + (m.group(1) if m else str(abs(hash(p["post_url"])))[:10])

def creators_html(ps):
    by_creator = {}
    for p in ps:
        h = p.get("creator")
        if not h: continue
        if h.lower() in ("@6ab3", "6ab3"): continue  # curator, not a creator
        by_creator.setdefault(h, []).append(p)
    if not by_creator: return ""
    # sort by count desc, then S/A first
    def rank(items):
        return (-len(items), -sum(1 for x in items if x["tier"] in ("S","A")))
    sorted_creators = sorted(by_creator.items(), key=lambda kv: rank(kv[1]))
    max_count = max(len(items) for _, items in sorted_creators) or 1
    seg_pct = 100.0 / max_count
    rows = []
    for handle, items in sorted_creators:
        url = handle_to_url(handle)
        # sort segments by tier so S first
        items_sorted = sorted(items, key=lambda x: {"S":0,"A":1,"B":2,"C":3}.get(x["tier"],4))
        segs = "".join(
            f'<a class="seg t{x["tier"]}" style="width:{seg_pct:.3f}%" href="#{post_anchor(x)}" title="{esc(x["card_title"])} — {x["tier"]}-tier"></a>'
            for x in items_sorted
        )
        rows.append(
            f'<div class="bar-row"><a class="handle" href="{url}" target="_blank" rel="noopener">{esc(handle)}</a>'
            f'<div class="bar-track">{segs}</div><div class="n">{len(items)}</div></div>'
        )
    legend = ('<div class="legend">'
              '<span><i style="background:var(--s)"></i>S</span>'
              '<span><i style="background:var(--a)"></i>A</span>'
              '<span><i style="background:var(--b)"></i>B</span>'
              '<span><i style="background:var(--c)"></i>C</span>'
              '<span style="margin-left:auto">click bar → jump to post</span></div>')
    return f"""<div class="creators">
  <h3>👥 {len(by_creator)} creators cited</h3>
  <div class="sub">Each bar = one creator. Each segment = one saved post, colored by tier. Click a segment to jump to its card.</div>
  <div class="bar-scroll"><div class="bar-list">{''.join(rows)}</div></div>
  {legend}
</div>"""

# ---------- Quick commands (index only) ----------
def commands_html():
    install_rows = [
        ("git clone git@github.com:Gabicus/dejaviewed.git ~/.claude/plugins/dejaviewed", "Plugin install (full — adds /dejaviewed command)"),
        ("git clone git@github.com:Gabicus/dejaviewed.git /tmp/dv && cp -r /tmp/dv/skills/dejaviewed ~/.claude/skills/", "Skill-only install (lighter)"),
        (f"/{SKILL}", f"Invoke the skill once installed"),
    ]
    prereq_rows = [
        ("pip install browser-cookie3 requests", "Python deps for cookie-safe IG scraping"),
        ("cp -r ~/.config/google-chrome/Default /path/to/project/.profile-copy/Default", "Copy Chrome profile (while Chrome is closed)"),
    ]
    quick_rows = [
        ("git clone https://github.com/google-gemini/gemini-cli", "Free Claude Code alternative — 1000 reqs/day"),
        ("git clone https://github.com/onyx-dot-app/onyx", "Self-hosted ChatGPT/Claude replacement"),
        ("git clone https://github.com/Tencent-Hunyuan/Hunyuan3D-2", "Open image-to-3D mesh generator"),
        ("npx @smithery/cli install n8n-mcp", "n8n workflow MCP server for Claude Code"),
    ]
    def row_html(rows):
        return "".join(f'<div class="cmd-row"><code>{esc(c)}</code> <span>{esc(d)}</span></div>' for c,d in rows)
    return f"""<div class="commands">
  <h3>📦 Install DejaViewed</h3>
  <p style="font-size:11px;color:var(--text-dim);margin:0 0 10px;line-height:1.5">
    Clone the <a href="https://github.com/Gabicus/dejaviewed" target="_blank" rel="noopener" style="color:var(--accent)">Gabicus/dejaviewed</a> repo.
    Works with Claude Code — adds the <code>/{SKILL}</code> slash command.
  </p>
  {row_html(install_rows)}
  <h3 style="margin-top:18px">⚙️ Prerequisites</h3>
  <p style="font-size:11px;color:var(--text-dim);margin:0 0 10px;line-height:1.5">
    You need a copied Chrome profile with an active Instagram session and two Python packages.
    See <a href="https://github.com/Gabicus/dejaviewed#prerequisites" target="_blank" rel="noopener" style="color:var(--accent)">full setup guide</a>.
  </p>
  {row_html(prereq_rows)}
  <h3 style="margin-top:18px">⚡ Quick commands</h3>
  {row_html(quick_rows)}
</div>"""

# ---------- App JS ----------
APP_JS = r"""
const state = { coll: FIXED_COLL, cats: new Set(['all']), tiers: new Set(), search: '', sort: 'tier' };
function $(s,r=document){return r.querySelector(s)}
function $$(s,r=document){return Array.from(r.querySelectorAll(s))}
function tr(t){return {S:0,A:1,B:2,C:3}[t]??4}
function matches(p){
  if(state.coll && p.collection!==state.coll)return false;
  if(state.tiers.size && !state.tiers.has(p.tier))return false;
  if(!state.cats.has('all')){
    let any=false;
    for(const c of p.categories){ if(state.cats.has(c)){any=true;break} }
    if(!any)return false;
  }
  if(state.search){
    const q=state.search.toLowerCase();
    const h=[p.summary,p.caption_original,p.creator,p.card_title,...(p.tools_mentioned||[]),...(p.repos_or_projects_mentioned||[]),...(p.techniques_mentioned||[])].join(' ').toLowerCase();
    if(!h.includes(q))return false;
  }
  return true;
}
function sf(a,b){
  if(state.sort==='tier')return tr(a.tier)-tr(b.tier)||(b.date||'').localeCompare(a.date||'');
  if(state.sort==='date')return (b.date||'').localeCompare(a.date||'');
  if(state.sort==='creator')return (a.creator||'').localeCompare(b.creator||'');
  return 0;
}
function el(tag, attrs={}, kids=[]){
  const e=document.createElement(tag);
  for(const k in attrs){
    if(k==='class')e.className=attrs[k];
    else if(k==='text')e.textContent=attrs[k];
    else e.setAttribute(k,attrs[k]);
  }
  for(const c of (Array.isArray(kids)?kids:[kids])){
    if(c==null)continue;
    e.appendChild(typeof c==='string'?document.createTextNode(c):c);
  }
  return e;
}
function ighandleUrl(h){ if(!h)return '#'; return 'https://instagram.com/'+h.replace(/^@/,''); }
function postId(p){ const m=p.post_url.match(/\/(p|reel)\/([^/]+)/); return 'post-'+(m?m[2]:''); }
function shortcode(p){ const m=p.post_url.match(/\/(p|reel)\/([^/]+)/); return m?m[2]:''; }
function card(p){
  const primary = p.categories[0] || 'resource';
  const c=el('article',{class:'card cat-'+primary,'data-tier':p.tier,'id':postId(p)});
  c.appendChild(el('h4',{class:'ctitle',text:p.card_title}));
  const top=el('div',{class:'top'});
  const meta=el('div',{class:'meta'});
  const a=el('a',{href:ighandleUrl(p.creator),target:'_blank',rel:'noopener',text:p.creator||'unknown'});
  meta.appendChild(a);
  meta.appendChild(document.createTextNode(' · '+(p.collection||'')+(p.date?(' · '+p.date):'')));
  top.appendChild(meta);
  top.appendChild(el('span',{class:'tier '+p.tier,text:p.tier}));
  c.appendChild(top);
  const sumWrap=el('div',{class:'sum-wrap'});
  sumWrap.appendChild(el('p',{class:'summary',text:p.summary||p.caption_original||''}));
  c.appendChild(sumWrap);
  const act=el('div',{class:'actions'});
  const isIG=p.post_url && p.post_url.includes('instagram.com');
  if(isIG){
    act.appendChild(el('a',{class:'btn',href:p.post_url,target:'_blank',rel:'noopener',text:'Open post ↗'}));
  } else if(p.post_url){
    act.appendChild(el('a',{class:'btn browse',href:p.post_url,target:'_blank',rel:'noopener',text:'Browse ↗'}));
  }
  if(p.guide_slug)act.appendChild(el('a',{class:'btn primary',href:'guides/'+p.guide_slug+'.html',text:'Deep dive →'}));
  c.appendChild(act);
  if(p.links && p.links.length){
    const lnks=el('div',{class:'links'});
    for(const l of p.links){
      lnks.appendChild(el('a',{href:l.url,target:'_blank',rel:'noopener',text:l.label,title:l.url}));
    }
    c.appendChild(lnks);
  }
  const sc=shortcode(p);
  if(sc){
    const thumb=el('a',{class:'thumb',href:p.post_url,target:'_blank',rel:'noopener'});
    const img=el('img',{loading:'lazy',alt:p.card_title||'',src:'thumb/'+sc+'.jpg'});
    img.onerror=function(){ thumb.parentNode && thumb.parentNode.removeChild(thumb); };
    thumb.appendChild(img);
    c.appendChild(thumb);
  }
  return c;
}
const SECTION_ORDER = [
  ['guide','📘 Guides','var(--c-guide)'],
  ['repo','🧰 Repos','var(--c-repo)'],
  ['skill','⚡ Skills','var(--c-skill)'],
  ['tool','🛠 Tools','var(--c-tool)'],
  ['platform','🌐 Platforms','var(--c-platform)'],
  ['art','🎨 Art','var(--c-art)'],
  ['design','✏️ Design','var(--c-design)'],
  ['uiux','📐 UI / UX','var(--c-uiux)'],
  ['resource','📚 Resources','var(--c-resource)']
];
function render(){
  const main=$('#main-content'); main.textContent='';
  const filtered=POSTS.filter(matches).sort(sf);
  $('#count').textContent=filtered.length+' post'+(filtered.length===1?'':'s');
  if(!filtered.length){
    main.appendChild(el('div',{class:'section-sub',text:'No posts match these filters.'}));
    return;
  }
  // Group sections only when no specific category selected (i.e. 'all')
  const grouped = state.cats.has('all') && state.cats.size===1;
  if(grouped){
    const buckets = {};
    for(const p of filtered){
      const primary = p.categories[0] || 'resource';
      (buckets[primary] = buckets[primary] || []).push(p);
    }
    for(const [key,label,color] of SECTION_ORDER){
      const arr = buckets[key];
      if(!arr || !arr.length) continue;
      const head = el('div',{class:'section-head'});
      const h3 = el('h3');
      const icon = el('span',{class:'icon'}); icon.style.background=color; icon.textContent=label.split(' ')[0];
      h3.appendChild(icon);
      h3.appendChild(document.createTextNode(' '+label.split(' ').slice(1).join(' ')));
      head.appendChild(h3);
      head.appendChild(el('span',{class:'count',text:arr.length+' items'}));
      main.appendChild(head);
      const grid = el('div',{class:'grid'});
      arr.forEach(p=>grid.appendChild(card(p)));
      main.appendChild(grid);
    }
  } else {
    const head = el('div',{class:'section-head'});
    head.appendChild(el('h3',{text:'📇 Filtered posts'}));
    head.appendChild(el('span',{class:'count',text:filtered.length+' items'}));
    main.appendChild(head);
    const grid = el('div',{class:'grid'});
    filtered.forEach(p=>grid.appendChild(card(p)));
    main.appendChild(grid);
  }
}
function init(){
  $('#search').addEventListener('input',e=>{state.search=e.target.value;render()});
  $('#sort').addEventListener('change',e=>{state.sort=e.target.value;render()});
  $$('.cat-btn').forEach(b=>b.addEventListener('click',()=>{
    const k=b.getAttribute('data-cat');
    if(k==='all'){
      state.cats.clear(); state.cats.add('all');
      $$('.cat-btn').forEach(x=>x.classList.toggle('on',x.getAttribute('data-cat')==='all'));
    } else {
      state.cats.delete('all');
      $('.cat-btn[data-cat="all"]').classList.remove('on');
      if(state.cats.has(k)){state.cats.delete(k);b.classList.remove('on')}
      else{state.cats.add(k);b.classList.add('on')}
      if(!state.cats.size){state.cats.add('all');$('.cat-btn[data-cat="all"]').classList.add('on')}
    }
    render();
  }));
  $$('.tier-pill').forEach(b=>b.addEventListener('click',()=>{
    const t=b.getAttribute('data-t');
    if(state.tiers.has(t)){state.tiers.delete(t);b.classList.remove('on')}
    else{state.tiers.add(t);b.classList.add('on')}
    render();
  }));
  $$('.coll-pill').forEach(b=>b.addEventListener('click',()=>{
    const c=b.getAttribute('data-coll');
    if(state.coll===c){state.coll='';b.classList.remove('on')}
    else{
      state.coll=c;
      $$('.coll-pill').forEach(x=>x.classList.remove('on'));
      b.classList.add('on');
    }
    render();
  }));
}
document.addEventListener('DOMContentLoaded',()=>{init();render();
  // Segment-bar click → reset filters so the target card is visible, then scroll
  document.body.addEventListener('click',e=>{
    const seg=e.target.closest('.seg'); if(!seg)return;
    e.preventDefault();
    state.cats.clear(); state.cats.add('all'); state.tiers.clear(); state.search='';
    $$('.cat-btn').forEach(x=>x.classList.toggle('on',x.getAttribute('data-cat')==='all'));
    $$('.tier-pill').forEach(x=>x.classList.remove('on'));
    $('#search').value='';
    render();
    const id=seg.getAttribute('href').slice(1);
    setTimeout(()=>{const t=document.getElementById(id);if(t){t.scrollIntoView({behavior:'smooth',block:'center'});t.style.outline='2px solid var(--accent)';setTimeout(()=>t.style.outline='',1800)}},50);
  });
});
"""

def page_shell(page_title, active, ps, fixed_collection, show_commands=False):
    posts_json = json.dumps(ps, ensure_ascii=False)
    app_js = APP_JS.replace("FIXED_COLL", json.dumps(fixed_collection))
    coll_for_hero = "all" if not fixed_collection else fixed_collection
    cmds = commands_html() if show_commands else ""
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(page_title)} · {TITLE}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
{header_html(active)}
{skill_callout_html()}
{hero_html(coll_for_hero, ps)}
<div class="wrap">
  {f'<div style="margin-top:24px">{cmds}</div>' if show_commands else ''}
  <div class="layout">
    {sidebar_html(ps, fixed_collection)}
    <main class="main" id="main-content"></main>
  </div>
</div>
<footer class="site"><div class="wrap">
  Curated by <a href="{IG_URL}">{HANDLE}</a> · Built with the <code>{SKILL}</code> skill for Claude Code<br>
  <span style="font-size:11px">All content sourced from public Instagram posts. Cookie-safe scraping. <span id="count"></span></span>
</div></footer>
<script>const POSTS={posts_json};{app_js}</script>
</body></html>"""

# ---------- Render pages ----------
for coll in ["ai1","ai2","ai3","ai4"]:
    ps = [p for p in posts if p["collection"] == coll]
    title = COLL_META[coll][0]
    (OUT / f"{coll}.html").write_text(page_shell(title, coll, ps, coll, show_commands=False))
    print(f"wrote {coll}.html ({len(ps)} posts)")

(OUT / "catalog.html").write_text(page_shell(f"{TITLE} — AI Edition", "index", posts, "", show_commands=True))
print(f"wrote catalog.html ({len(posts)} posts)")

# ---------- Actions page ----------
actions_path = DATA / "actions.json"
if actions_path.exists():
    actions = json.loads(actions_path.read_text())
    stats = actions.get("stats", {})
    sections = actions.get("sections", [])

    # Build stats banner
    stats_html = f"""<div class="bans">
        <div class="ban"><div class="v">{stats.get('total_saves',0)}</div><div class="l">Saves</div></div>
        <div class="ban"><div class="v">{sum(len(s.get('items',[])) for s in sections)}</div><div class="l">Actions</div></div>
        <div class="ban"><div class="v">{stats.get('sources_count', len(stats.get('sources',[])))}</div><div class="l">Sources</div></div>
        <div class="ban"><div class="v">{len(sections)}</div><div class="l">Categories</div></div>
      </div>"""

    # Build section HTML
    sections_html = ""
    for sec in sections:
        items_html = ""
        for item in sec.get("items", []):
            cmd_html = ""
            if item.get("command"):
                cmd_html = f'<div class="action-cmd"><code>{esc(item["command"])}</code></div>'
            links_html = ""
            if item.get("links"):
                pills = "".join(f'<a href="{esc(l["url"])}" target="_blank" rel="noopener">{esc(l["label"])}</a>' for l in item["links"][:6])
                links_html = f'<div class="action-links">{pills}</div>'
            source_html = ""
            if item.get("source_cards"):
                refs = " ".join(f'<a href="catalog.html#{esc(sc)}">→</a>' for sc in item["source_cards"][:3])
                source_html = f'<span class="source-refs">{refs}</span>'
            tier = item.get("tier", "C")
            items_html += f"""<div class="action-item tier-{tier}">
              <div class="action-head">
                <span class="tier {tier}">{tier}</span>
                <h4>{esc(item.get('title',''))}</h4>
                {source_html}
              </div>
              <p class="action-why">{esc(item.get('why',''))}</p>
              {cmd_html}{links_html}
            </div>"""

        sections_html += f"""<section class="action-section" id="{esc(sec.get('id',''))}">
          <h2>{sec.get('icon','')} {esc(sec.get('title',''))}</h2>
          <p class="section-sub">{esc(sec.get('subtitle',''))}</p>
          <div class="action-grid">{items_html}</div>
        </section>"""

    # Actions-specific CSS additions
    actions_css = r"""
.dv-sidebar{display:flex;flex-direction:column;gap:12px}
.dv-sidebar .about-card{background:var(--panel);border:1px solid var(--border);border-radius:var(--radius-sm);padding:14px 16px;overflow:hidden}
.dv-sidebar .about-card h3{margin:0 0 8px;font-size:13px;font-weight:800;color:#fff}
.dv-sidebar .cmd-row{margin-bottom:6px}
.dv-sidebar .cmd-row code{display:block;background:rgba(0,0,0,.45);border:1px solid var(--border);padding:5px 10px;border-radius:6px;font-size:10.5px;color:var(--c-repo);white-space:nowrap;overflow-x:auto;cursor:pointer}
.dv-sidebar .cmd-row code:hover{background:rgba(0,0,0,.6);border-color:var(--c-repo)}
.dv-sidebar .cmd-row span{font-size:10px;color:var(--text-mute);margin-top:2px;display:block}
.dv-sidebar .src-list{margin:0 0 4px;font-size:11.5px;color:var(--text-dim);line-height:1.6}
.dv-sidebar .save-profile{font-size:12px;color:var(--text-dim);line-height:1.6;font-style:italic;padding:12px 16px;background:var(--panel);border:1px solid var(--border);border-radius:var(--radius-sm);margin:0}
.action-section{margin-bottom:36px}
.action-section h2{font-size:20px;font-weight:900;letter-spacing:-0.02em;margin:0 0 4px;color:#fff;column-span:all}
.section-sub{font-size:12px;color:var(--text-mute);margin:0 0 16px;line-height:1.5;column-span:all}
.action-grid{column-count:3;column-gap:14px}
@media(max-width:1200px){.action-grid{column-count:2}}
@media(max-width:700px){.action-grid{column-count:1}}
.action-item{background:var(--panel);border:1px solid var(--border);border-radius:var(--radius-sm);padding:14px 16px;margin-bottom:14px;border-left-width:3px;transition:all .15s;break-inside:avoid;display:inline-block;width:100%}
.action-item:hover{border-color:var(--border-hi);background:var(--panel-2)}
.action-item.tier-S{border-left-color:var(--s)}.action-item.tier-A{border-left-color:var(--a)}
.action-item.tier-B{border-left-color:var(--b)}.action-item.tier-C{border-left-color:var(--c)}
.action-head{display:flex;align-items:center;gap:10px;margin-bottom:6px;flex-wrap:wrap}
.action-head h4{margin:0;font-size:13px;font-weight:700;color:#fff;flex:1}
.action-why{font-size:12px;color:var(--text-dim);margin:0 0 8px;line-height:1.5}
.action-cmd{margin:8px 0}
.action-cmd code{display:block;background:rgba(0,0,0,.45);border:1px solid var(--border);padding:8px 12px;border-radius:6px;font-size:11.5px;color:var(--c-repo);white-space:pre-wrap;word-break:break-all;cursor:pointer}
.action-cmd code:hover{background:rgba(0,0,0,.6);border-color:var(--c-repo)}
.action-links{display:flex;flex-wrap:wrap;gap:5px;margin-top:8px}
.action-links a{font-size:10.5px;padding:3px 8px;background:rgba(255,255,255,.04);border:1px solid var(--border);border-radius:6px;color:var(--text-dim);transition:all .15s;white-space:nowrap}
.action-links a:hover{background:rgba(167,139,250,.12);border-color:var(--accent);color:#fff}
.source-refs{display:flex;gap:4px}
.source-refs a{font-size:10px;color:var(--text-mute);background:var(--panel-2);padding:2px 6px;border-radius:4px;border:1px solid var(--border)}
.source-refs a:hover{color:var(--accent)}
.actions-nav{background:linear-gradient(135deg,rgba(251,191,36,.15),rgba(244,114,182,.15))!important;border-color:rgba(251,191,36,.3)!important;color:var(--s)!important}
.sec-pills{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 28px;justify-content:center}
.sec-pill{display:inline-flex;align-items:center;gap:6px;padding:8px 16px;border-radius:999px;font-size:12px;font-weight:700;background:var(--panel);border:1px solid var(--border);color:var(--text-dim);transition:all .15s;text-transform:uppercase;letter-spacing:.04em}
.sec-pill:hover{background:var(--panel-2);color:#fff;border-color:var(--border-hi)}
.sec-pill .n{font-size:10px;background:rgba(255,255,255,.08);padding:2px 6px;border-radius:999px;color:var(--text-mute)}
@media(max-width:900px){.dv-sidebar{margin-top:16px}}
"""

    # Build section jump-link pills
    section_pills = []
    for sec in sections:
        sid = sec.get('id', '')
        icon = sec.get('icon', '')
        label = sec.get('title', '').replace('These ', '')
        n = len(sec.get('items', []))
        section_pills.append(f'<a class="sec-pill" href="#{esc(sid)}">{icon} {esc(label)} <span class="n">{n}</span></a>')
    pills_html = '<div class="sec-pills">' + ''.join(section_pills) + '</div>'

    actions_page = f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{TITLE}</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{CSS}{actions_css}</style></head><body>
{header_html("actions")}
<section class="hero"><div class="wrap">
  <div class="hero-grid">
    <div class="hero-left">
      <h2>{TITLE}</h2>
      <p class="why">{WHY}</p>
      {stats_html}
    </div>
    <div class="dv-sidebar">
      <div class="about-card">
        <h3>📦 Install</h3>
        <div class="cmd-row"><code>git clone git@github.com:Gabicus/dejaviewed.git ~/.claude/plugins/dejaviewed</code><span>Full plugin</span></div>
        <div class="cmd-row"><code>/{SKILL}</code><span>Run the pipeline</span></div>
      </div>
      <div class="about-card">
        <h3>🔌 Sources</h3>
        <p class="src-list"><strong style="color:#fff">Built:</strong> Instagram · Chrome · Firefox · Edge</p>
        <p class="src-list"><strong style="color:var(--text-mute)">Planned:</strong> TikTok · Twitter/X · Reddit · YouTube</p>
      </div>
      <p class="save-profile">{esc(stats.get('save_profile',''))}</p>
    </div>
  </div>
</div></section>
<div class="wrap">
  {pills_html}
  {sections_html}
</div>
<footer class="site"><div class="wrap">
  <a href="catalog.html">Browse all {len(posts)} saves →</a> ·
  Curated by <a href="{IG_URL}">{HANDLE}</a> · Built with <code>{SKILL}</code> ·
  <a href="https://github.com/Gabicus/dejaviewed" target="_blank" rel="noopener">GitHub</a>
</div></footer>
<script>
document.querySelectorAll('.action-cmd code').forEach(el=>{{
  el.title='Click to copy';
  el.addEventListener('click',()=>{{navigator.clipboard.writeText(el.textContent).then(()=>{{el.style.borderColor='var(--c-repo)';setTimeout(()=>el.style.borderColor='',800)}});}});
}});
</script>
</body></html>"""

    (OUT / "index.html").write_text(actions_page)
    print(f"wrote index.html ({sum(len(s.get('items',[])) for s in sections)} action items)")
else:
    print("skipping index.html (no data/actions.json — run build_actions.py first)")

# ---------- Guide pages ----------
for slug in guide_files:
    md = (GUIDES / f"{slug}.md").read_text()
    title = guide_titles[slug]
    confidence = GUIDE_CONFIDENCE.get(slug, "medium")
    md_escaped = md.replace("</script>","<\\/script>")
    badge = f'<div class="confidence-badge {confidence}">Source confidence: {confidence}</div>'
    page = f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · {TITLE}</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
{header_html("index", prefix="../")}
<article class="guide">
  {badge}
  <div id="guide-body"></div>
</article>
<footer class="site"><div class="wrap"><a href="../catalog.html">← Back to {TITLE}</a> · curated by <a href="{IG_URL}">{HANDLE}</a> · <code>{SKILL}</code></div></footer>
<script id="md" type="text/markdown">{md_escaped}</script>
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<script src="https://cdn.jsdelivr.net/npm/dompurify@3/dist/purify.min.js"></script>
<script>
const raw=document.getElementById('md').textContent;
const html=DOMPurify.sanitize(marked.parse(raw));
document.getElementById('guide-body').innerHTML=html;
</script></body></html>"""
    (OUT / "guides" / f"{slug}.html").write_text(page)
print(f"wrote {len(guide_files)} guide pages")
print(f"\n✅ {TITLE} site built at {OUT}")
