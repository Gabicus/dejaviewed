#!/usr/bin/env python3
"""Per-tool hub pages: site/tools/<slug>.html + site/tools/index.html.

A hub is the archive's answer to "what do creators actually do with <tool>?": a computed summary,
an editor's take written by hand (data/tools/<slug>.json), the curated guides that draw on the
tool, every tagged post (best first), co-occurring tools, alternatives, prompt systems that use it,
and one outbound "Official site" link.

Qualification is computed from site/catalog.json, never hand-picked:
  INDEXED   >= 5 entries tag the tool, >= 2 of them S/A tier, >= 1 curated guide draws >= 2
            of them, AND data/tools/<slug>.json holds an editor's take of >= 150 words.
  NOINDEX   >= 3 entries but some indexed test fails -> page with <meta name="robots" content="noindex,follow">
            (still useful, still linked from /tools/; build_api's sitemap must skip these).
  SKIPPED   < 3 entries, or a generic/company/non-software tag (EXCLUDE).
Tool tags are merged through ALIASES; "Claude" (company/model tag) counts toward the Claude Code
hub only when the entry's text mentions "Claude Code".

Editor's take format (data/tools/<slug>.json "take"): plain text, paragraphs split by a blank line,
inline citations as [label](/e/<id>) or [label](/guides/<slug>). Every /e/ citation must be an entry
of that hub; every paragraph needs >= 1 citation. Violations are build errors.

Outbound link: /go/<slug> when data/monetize/affiliates.json has the slug with a live redirect
(status pending|active); else the verified official URL in TOOL_META. The button class is
"go-btn", NOT "go": build_monetize strips every <a class="go" ...> it does not re-create, and it only
re-creates them on guides/deeper/e pages. This script applies the same rel policy itself
(active -> rel="sponsored nofollow noopener" + "affiliate link" label + disclosure line).

build_seo.py adds the seo block (tools/ is in its SUB_DIRS); this page emits only <title>,
<meta name="description"> and, for noindex hubs, the robots meta.

Usage:  python3 scripts/build_tools.py            # write pages (scaffolds missing data/tools/*.json)
        python3 scripts/build_tools.py --check    # dry run; exit 1 if any page would change or a take is invalid
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
OUT = SITE / "tools"
DATA_TOOLS = ROOT / "data" / "tools"
CATALOG = SITE / "catalog.json"
DIVES = ROOT / "data" / "deep_dives.json"
PACKS = ROOT / "data" / "prompt_systems.json"
AFF = ROOT / "data" / "monetize" / "affiliates.json"
AFF_CFG = ROOT / "data" / "monetize" / "config.json"

sys.path.insert(0, str(ROOT / "scripts"))
from build_collections import (as_list, clip, collection_name, collection_slug, collection_url,  # noqa: E402
                               esc, fmt_date, handle, safe_slug, sort_key, tier_badge)

MIN_PAGE, MIN_INDEX, MIN_SA, MIN_GUIDE_DRAW, MIN_TAKE_WORDS = 3, 5, 2, 2, 150
TODAY_FALLBACK = "2026-10-22"

# tag spelling -> canonical hub name
ALIASES = {
    "Gemini CLI": "Gemini", "Runway Gen-3": "Runway", "GPT-5": "ChatGPT", "GPT-4": "ChatGPT",
    "GPT-4o": "ChatGPT", "Veo 3": "Veo", "Higgsfield Cinema Studio": "Higgsfield", "Blender MCP": "Blender",
    "Figma MCP": "Figma", "czlonkowski/n8n-mcp": "n8n", "three.js": "Three.js",
    "react-three-fiber": "Three.js", "React Three Fiber": "Three.js",
}
# generic / company / language / platform tags, and non-software tags (Banjo = the instrument)
EXCLUDE = {"Claude", "Anthropic", "OpenAI", "Google", "Python", "React", "YouTube", "Slack", "Docker",
           "Internet Archive", "MCP", "LinkedIn", "GitHub", "Meta", "Banjo"}
# (tool, entry id) tags the enricher got wrong: the word appears, the product does not (checked by hand 2026-10-22)
FALSE_TAGS = {
    ("Cursor", "DWl3Bo6jqX1"),   # "cursor animations" in a screen recorder
    ("Cursor", "DXFaQvyExqx"),   # mouse-cursor physics text effect
    ("Cursor", "DYijhcetmBP"),   # "cursor interaction" in an animation prompt
    ("Llama", "DXcWjL0jLsd"),    # Spanish "se llama" ("is called")
    ("Runway", "CuhWvfkoO29"),   # song lyric "take off the runway"
    ("Runway", "DW1O6ZBEfDa"),   # "runway assassin" film-role joke
    ("Runway", "DW5syk6Cjh-"),   # "no runway lighting" in a portrait prompt
    ("Runway", "C-Ad0PoApy1"),   # "gorilla walking down the runway" prompt example
}

PILLARS = [
    ("agentic_coding", "Agentic coding", "Terminal and IDE coding agents, and the design-to-code tools around them."),
    ("prompt_context_eng", "Prompt and context engineering", "General assistants and research notebooks people prompt directly."),
    ("agents_automation", "Agents, MCP and automation", "Browser automation, workflow builders, second brains and agent platforms."),
    ("quant_trading_prediction", "Quant trading and prediction markets", "Markets and charting tools that show up in builder posts."),
    ("ai_video_image_gen", "AI video and image generation", "Video and image models creators use for shots, ads and short films."),
    ("threeD_creative_coding", "3D, creative coding and installations", "3D suites, real-time engines and computer-vision kits."),
    ("local_open_ai", "Local and open-weight AI", "Open-weight model families, model hubs and local runtimes."),
    ("security_osint", "Security and OSINT", "Reconnaissance and red-team tools."),
]

# canonical name -> slug (affiliates.json slug wins when present), pillar, one-line descriptor, official URL
# (official URLs verified 2026-10-22 by GET; 403 = bot-blocked but live). Affiliate tools use /go/<slug>.
TOOL_META = {
    "Claude Code": ("claude-code", "agentic_coding", "Anthropic's terminal coding agent", "https://claude.com/product/claude-code"),
    "Codex": ("codex", "agentic_coding", "OpenAI's coding agent (CLI, IDE and cloud)", "https://openai.com/codex"),
    "Cursor": ("cursor", "agentic_coding", "AI-first code editor", "https://cursor.com"),
    "Gemini": ("gemini", "agentic_coding", "Google's model family, incl. the Gemini CLI agent", "https://gemini.google.com"),
    "Figma": ("figma", "agentic_coding", "Design tool, now wired to agents via MCP", "https://www.figma.com"),
    "Stitch": ("stitch", "agentic_coding", "Google's AI UI-design generator", "https://stitch.withgoogle.com"),
    "Impeccable": ("impeccable", "agentic_coding", "Design-taste skill pack for coding agents", "https://impeccable.style"),
    "Vercel": ("vercel", "agentic_coding", "Frontend hosting and deploys", ""),
    "ChatGPT": ("chatgpt", "prompt_context_eng", "OpenAI's assistant and GPT models", "https://chatgpt.com"),
    "NotebookLM": ("notebooklm", "prompt_context_eng", "Google's source-grounded research notebook", "https://notebooklm.google.com"),
    "Playwright": ("playwright", "agents_automation", "Browser automation, used by agents via MCP", "https://playwright.dev"),
    "n8n": ("n8n", "agents_automation", "Visual workflow automation", ""),
    "Obsidian": ("obsidian", "agents_automation", "Markdown vault used as an agent's second brain", "https://obsidian.md"),
    "Notion": ("notion", "agents_automation", "Docs and databases workspace", ""),
    "Manus": ("manus", "agents_automation", "General-purpose autonomous agent", ""),
    "PostHog": ("posthog", "agents_automation", "Product analytics platform", "https://posthog.com"),
    "Polymarket": ("polymarket", "quant_trading_prediction", "Crypto prediction market", "https://polymarket.com"),
    "TradingView": ("tradingview", "quant_trading_prediction", "Charting and Pine Script platform", ""),
    "Higgsfield": ("higgsfield", "ai_video_image_gen", "AI video and image studio for creators", ""),
    "Runway": ("runway", "ai_video_image_gen", "AI video generation and editing", ""),
    "Veo": ("veo", "ai_video_image_gen", "Google DeepMind's video model", "https://deepmind.google/models/veo/"),
    "Sora": ("sora", "ai_video_image_gen", "OpenAI's video model", "https://openai.com/sora"),
    "Kling": ("kling", "ai_video_image_gen", "Kuaishou's video model", ""),
    "Midjourney": ("midjourney", "ai_video_image_gen", "Image generation model", "https://www.midjourney.com"),
    "Blender": ("blender", "threeD_creative_coding", "Open-source 3D suite", ""),
    "TouchDesigner": ("touchdesigner", "threeD_creative_coding", "Node-based real-time visuals", "https://derivative.ca"),
    "MediaPipe": ("mediapipe", "threeD_creative_coding", "Google's on-device vision and tracking kit",
                  "https://developers.google.com/edge/mediapipe/solutions/guide"),
    "Three.js": ("three-js", "threeD_creative_coding", "WebGL 3D library for the browser", "https://threejs.org"),
    "Unreal Engine": ("unreal-engine", "threeD_creative_coding", "Epic's real-time 3D engine", "https://www.unrealengine.com"),
    "Unity": ("unity", "threeD_creative_coding", "Real-time 3D game engine", "https://unity.com"),
    "After Effects": ("after-effects", "threeD_creative_coding", "Adobe's motion-graphics app",
                      "https://www.adobe.com/products/aftereffects.html"),
    "DeepSeek": ("deepseek", "local_open_ai", "Open-weight Chinese model family", "https://www.deepseek.com"),
    "Qwen": ("qwen", "local_open_ai", "Alibaba's open-weight model family", "https://qwen.ai"),
    "Kimi": ("kimi", "local_open_ai", "Moonshot AI's model and assistant", "https://www.kimi.com"),
    "Llama": ("llama", "local_open_ai", "Meta's open-weight model family", "https://www.llama.com"),
    "Hugging Face": ("hugging-face", "local_open_ai", "Model and dataset hub", "https://huggingface.co"),
    "Ollama": ("ollama", "local_open_ai", "Run open models locally", "https://ollama.com"),
    "OpenRouter": ("openrouter", "local_open_ai", "One API across many model providers", "https://openrouter.ai"),
    "Raspberry Pi": ("raspberry-pi", "local_open_ai", "Single-board computer for offline builds", "https://www.raspberrypi.com"),
    "Sherlock": ("sherlock", "security_osint", "Username search across social sites",
                 "https://github.com/sherlock-project/sherlock"),
}

HEAD = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<title>{title}</title>
<meta name="description" content="{desc}">
{robots}<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="../shared.css">
<script src="../shared.js"></script>
<style>
  main.tool {{ max-width: 960px; margin: 24px auto 40px; padding: 0 20px; }}
  .tool h1 {{ font: 700 30px/1.2 Inter, system-ui; margin: 8px 0 12px; color: var(--text); }}
  .tool .lead, .tool .take p {{ color: var(--text-dim); font-size: 15px; line-height: 1.65; margin: 0 0 12px; max-width: 760px; }}
  .tool .take p {{ color: var(--text); }}
  .tool a {{ color: var(--accent); text-decoration: none; }}
  .tool a:hover {{ text-decoration: underline; }}
  nav.crumbs {{ font-size: 12px; color: var(--text-mute); margin-bottom: 6px; }}
  nav.crumbs a {{ color: var(--text-mute); }}
  nav.crumbs .sep {{ margin: 0 6px; opacity: .6; }}
  .tool .upd {{ color: var(--text-mute); font: 400 11px/1.6 'JetBrains Mono', ui-monospace, monospace; margin: 0 0 14px; }}
  .tool .cta {{ display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin: 4px 0 18px; }}
  .tool a.go-btn {{ display: inline-block; background: var(--accent); color: var(--bg, #0b0b10); font: 600 14px/1 Inter, system-ui;
                   padding: 10px 16px; border-radius: 999px; text-decoration: none; }}
  .tool a.go-btn:hover {{ filter: brightness(1.1); text-decoration: none; }}
  .tool .cta .aff, .tool .cta .disc {{ color: var(--text-mute); font-size: 12px; }}
  .tool h2 {{ margin: 28px 0 10px; font: 600 12px/1 'JetBrains Mono', ui-monospace, monospace; letter-spacing: .08em;
             text-transform: uppercase; color: var(--text-mute); }}
  .tool .take {{ background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 16px 18px 6px; }}
  ul.glist {{ list-style: none; margin: 0; padding: 0; }}
  ul.glist li {{ background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 10px 14px; margin-bottom: 8px; }}
  ul.glist .t {{ font-weight: 600; font-size: 14px; }}
  ul.glist .n {{ color: var(--text-mute); font-size: 11px; margin-left: 6px; }}
  ul.glist .s {{ display: block; color: var(--text-dim); font-size: 13px; line-height: 1.45; margin-top: 3px; }}
  ul.chips {{ list-style: none; margin: 0; padding: 0; display: flex; flex-wrap: wrap; gap: 8px; }}
  ul.chips li {{ background: var(--panel); border: 1px solid var(--border); border-radius: 999px; padding: 5px 12px; font-size: 13px; color: var(--text); }}
  ul.chips .n {{ color: var(--text-mute); font-size: 11px; margin-left: 6px; }}
  ol.entries {{ list-style: none; margin: 0; padding: 0; }}
  ol.entries li {{ background: var(--panel); border: 1px solid var(--border); border-radius: 10px; padding: 10px 14px; margin-bottom: 8px; }}
  ol.entries a.t {{ color: var(--text); font-weight: 600; font-size: 14px; }}
  ol.entries a.t:hover {{ color: var(--accent); }}
  ol.entries .m {{ display: block; color: var(--text-mute); font: 400 11px/1.6 'JetBrains Mono', ui-monospace, monospace; margin-top: 3px; }}
  .tb {{ display: inline-block; min-width: 18px; text-align: center; padding: 0 5px; margin-right: 8px; border-radius: 999px;
        font: 800 10px/16px Inter, system-ui; border: 1px solid var(--border); color: var(--text-mute); vertical-align: 1px; }}
  .tb.t-s {{ color: var(--c-entry-s); border-color: rgba(251,191,36,.45); background: rgba(251,191,36,.12); }}
  .tb.t-a {{ color: var(--c-entry-a); border-color: rgba(167,139,250,.45); background: rgba(167,139,250,.12); }}
  .tb.t-b {{ color: var(--c-entry-b); border-color: rgba(96,165,250,.45); background: rgba(96,165,250,.12); }}
  .tgrid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 12px; margin: 0; padding: 0; list-style: none; }}
  .tgrid li a {{ display: block; background: var(--panel); border: 1px solid var(--border); border-radius: 12px; padding: 12px 14px;
                color: var(--text); height: 100%; box-sizing: border-box; }}
  .tgrid li a:hover {{ border-color: var(--accent); text-decoration: none; }}
  .tgrid h3 {{ margin: 0 0 4px; font: 600 16px/1.3 Inter, system-ui; }}
  .tgrid .m {{ color: var(--text-mute); font: 400 11px/1.6 'JetBrains Mono', ui-monospace, monospace; }}
  .tgrid p {{ color: var(--text-dim); font-size: 13px; line-height: 1.45; margin: 6px 0 0; }}
  .pdesc {{ color: var(--text-dim); font-size: 13px; margin: -4px 0 10px; }}
  .note {{ color: var(--text-mute); font-size: 12px; margin: 8px 0 0; }}
  .more {{ margin-top: 22px; font-size: 13px; color: var(--text-mute); }}
  .more a {{ color: var(--text-dim); margin-right: 14px; }}
  @media (max-width: 560px) {{ .tool h1 {{ font-size: 24px; }} }}
</style>
</head><body>
<script>DV.mountHeader(document.body, 'tools');</script>
"""


# ───────────────────────────────────────────────────────────── data
def text_of(e: dict) -> str:
    return " ".join(str(e.get(k) or "") for k in ("title", "summary", "caption", "transcript"))


def hub_names(e: dict) -> set[str]:
    out = set()
    for t in as_list(e.get("tools")):
        t = ALIASES.get(t, t)
        if t == "Claude":
            if "claude code" in text_of(e).lower():
                out.add("Claude Code")
            continue
        if t not in EXCLUDE and (t, e.get("id")) not in FALSE_TAGS:
            out.add(t)
    return out


def slug_for(name: str) -> str:
    if name in TOOL_META:
        return TOOL_META[name][0]
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def load_guides() -> list[dict]:
    try:
        from build_guides import is_curated, slug_of
    except Exception:  # pragma: no cover
        def is_curated(d): return d.get("suggested_by") == "curated" or bool(d.get("pinned"))
        def slug_of(i): return i[len("dd-"):] if i.startswith("dd-") else i
    out = []
    for d in json.loads(DIVES.read_text(encoding="utf-8")).get("deep_dives", []):
        if not is_curated(d):
            continue
        slug = slug_of(d["id"])
        p = SITE / "guides" / f"{slug}.html"
        if not p.is_file():
            continue
        m = re.search(r"(?m)^> \*\*In short:\*\* (.+)$", p.read_text(encoding="utf-8", errors="replace"))
        out.append({"slug": slug, "title": d.get("title") or slug, "ids": set(d.get("entry_ids") or []),
                    "short": m.group(1).strip() if m else ""})
    return out


def load_packs() -> dict[str, str]:
    """slug -> searchable pack text (only packs whose guide page exists)."""
    if not PACKS.exists():
        return {}
    raw = json.loads(PACKS.read_text(encoding="utf-8"))
    items = raw.items() if isinstance(raw, dict) else ((p.get("slug"), p) for p in raw)
    return {s: json.dumps(p, ensure_ascii=False) for s, p in items
            if s and (SITE / "guides" / f"{s}.html").is_file()}


def name_re(name: str, aliases: list[str]) -> re.Pattern:
    alts = sorted({name, *aliases}, key=len, reverse=True)
    return re.compile(r"(?<![\w.-])(?:" + "|".join(re.escape(a) for a in alts) + r")(?![\w])")


def load_aff() -> tuple[dict, dict]:
    aff = json.loads(AFF.read_text(encoding="utf-8")) if AFF.exists() else {}
    cfg = json.loads(AFF_CFG.read_text(encoding="utf-8")) if AFF_CFG.exists() else {}
    return aff, cfg


def load_take(slug: str) -> dict | None:
    p = DATA_TOOLS / f"{slug}.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


LINK_MD = re.compile(r"\[([^\]]+)\]\((/(?:e|guides)/[^)\s]+)\)")


def take_words(take: str) -> int:
    return len(re.findall(r"[A-Za-z0-9][\w'’.-]*", LINK_MD.sub(r"\1", take or "")))


def validate_take(slug: str, take: str, hub_ids: set[str], all_ids: set[str], guide_slugs: set[str]) -> list[str]:
    errs = []
    for para in [p for p in re.split(r"\n\s*\n", take or "") if p.strip()]:
        links = LINK_MD.findall(para)
        if not links:
            errs.append(f"{slug}: paragraph without a citation: {clip(para, 60)!r}")
        for _, href in links:
            if href.startswith("/e/"):
                rid = href[3:]
                if rid not in hub_ids:
                    errs.append(f"{slug}: cites /e/{rid} which is " + ("not tagged with this tool" if rid in all_ids else "not an entry"))
            elif href[len("/guides/"):].split("#")[0] not in guide_slugs:
                errs.append(f"{slug}: cites missing guide {href}")
    stray = re.sub(LINK_MD, "", take or "")
    if re.search(r"\]\(|https?://", stray):
        errs.append(f"{slug}: take contains a malformed link or an external URL")
    return errs


def render_take(take: str, id_to_slug: dict[str, str]) -> str:
    out = []
    for para in [p.strip() for p in re.split(r"\n\s*\n", take or "") if p.strip()]:
        pos, buf = 0, []
        for m in LINK_MD.finditer(para):
            buf.append(esc(para[pos:m.start()]))
            href = m.group(2)
            if href.startswith("/e/"):
                href = "/e/" + id_to_slug.get(href[3:], safe_slug(href[3:]))
            buf.append(f'<a href="{esc(href)}">{esc(m.group(1))}</a>')
            pos = m.end()
        buf.append(esc(para[pos:]))
        out.append("<p>" + "".join(buf).replace("\n", " ") + "</p>")
    return "\n".join(out)


# ───────────────────────────────────────────────────────────── model
class Hub:
    def __init__(self, name: str, items: list[dict]):
        self.name, self.items = name, items
        self.slug = slug_for(name)
        self.ids = {e["id"] for e in items}
        self.sa = sum(1 for e in items if (e.get("tier") or "").upper() in ("S", "A"))
        self.data: dict | None = None
        self.status, self.reasons = "", []
        self.guides: list[dict] = []
        self.pairs: list[tuple[str, int]] = []
        self.packs: list[tuple[str, int]] = []


def qualify(hubs: dict[str, Hub], guides: list[dict]) -> None:
    for h in hubs.values():
        h.guides = sorted(({**g, "n": len(g["ids"] & h.ids)} for g in guides if len(g["ids"] & h.ids) >= MIN_GUIDE_DRAW),
                          key=lambda g: (-g["n"], g["title"]))
        h.data = load_take(h.slug)
        if len(h.items) < MIN_PAGE:
            h.status, h.reasons = "skip", [f"{len(h.items)} entries < {MIN_PAGE}"]
            continue
        r = []
        if len(h.items) < MIN_INDEX:
            r.append(f"{len(h.items)} entries < {MIN_INDEX}")
        if h.sa < MIN_SA:
            r.append(f"{h.sa} S/A < {MIN_SA}")
        if not h.guides:
            r.append(f"no curated guide draws >= {MIN_GUIDE_DRAW}")
        if take_words((h.data or {}).get("take", "")) < MIN_TAKE_WORDS:
            r.append(f"editor take < {MIN_TAKE_WORDS} words")
        h.status, h.reasons = ("noindex", r) if r else ("index", [])


def describe(h: Hub, tiers: Counter, creators: Counter) -> str:
    s = (f"What creators do with {h.name}: {len(h.items)} saved posts ranked S to C "
         f"({tiers.get('S', 0)} S-tier, {tiers.get('A', 0)} A-tier)")
    if h.guides:
        s += f", {len(h.guides)} curated guide{'s' if len(h.guides) != 1 else ''}"
    s += "."
    top = [p for p, _ in h.pairs[:3]]
    if top and len(s) + 20 < 158:
        s2 = s + " Often paired with " + ", ".join(top) + "."
        s = s2 if len(s2) <= 158 else s
    return clip(s, 158)


def summary(h: Hub, tiers: Counter, creators: Counter, hubs: dict[str, Hub]) -> str:
    dates = sorted(fmt_date(e.get("date")) for e in h.items if e.get("date"))
    tier_mix = ", ".join(f"{tiers[t]} {t}-tier" for t in "SABC" if tiers.get(t))
    span = ""
    if dates:
        span = (f", posted between {dates[0][:7]} and {dates[-1][:7]}" if dates[0][:7] != dates[-1][:7]
                else f", posted in {dates[0][:7]}")
    s = (f"{len(h.items)} saved post{'s' if len(h.items) != 1 else ''} in this archive tag {esc(h.name)}, "
         f"from {len(creators)} creator{'s' if len(creators) != 1 else ''}{span} ({tier_mix}).")
    colls = Counter(c for e in h.items if (c := e.get("collection") or e.get("source_collection")))
    if colls:
        cl = ", ".join(f'<a href="{collection_url(c)}">{esc(collection_name(c))}</a> ({n})'
                       for c, n in colls.most_common(3)
                       if (SITE / "collections" / f"{collection_slug(c)}.html").is_file())
        if cl:
            s += f" Most sit in {cl}."
    top_cr = [(c, n) for c, n in creators.most_common(3) if n > 1]
    if top_cr:
        s += " Most-saved creators: " + ", ".join(f"@{esc(c)} ({n})" for c, n in top_cr) + "."
    if h.pairs:
        s += " It most often appears alongside " + ", ".join(f"{esc(p)} ({n})" for p, n in h.pairs[:3]) + "."
    return s


def cta(h: Hub, aff: dict, cfg: dict) -> str:
    a = aff.get(h.slug)
    if a and a.get("status") in ("pending", "active") and a.get("official_url"):
        active = a["status"] == "active"
        rel = "sponsored nofollow noopener" if active else "noopener"
        out = f'<a class="go-btn" href="/go/{esc(h.slug)}" rel="{rel}">Official site ↗</a>'
        if active:
            out += f'<span class="aff">{esc(cfg.get("inline_label") or "affiliate link")}</span>'
            out += f'<span class="disc">{esc(cfg.get("disclosure_footer") or "")}</span>'
        return out
    url = (a or {}).get("official_url") if a else ""
    url = url or (TOOL_META.get(h.name, ("", "", "", ""))[3])
    if not url:
        return ""
    return f'<a class="go-btn" href="{esc(url)}" rel="noopener">Official site ↗</a>'


def render_hub(h: Hub, hubs: dict[str, Hub], id_to_slug: dict[str, str], aff: dict, cfg: dict) -> str:
    tiers = Counter((e.get("tier") or "C").upper() for e in h.items)
    creators = Counter(c for e in h.items if (c := handle(e)))
    data = h.data or {}
    updated = str(data.get("updated") or TODAY_FALLBACK)
    title = f"{h.name}: what creators actually do with it ({len(h.items)} posts) · DejaViewed"
    robots = '<meta name="robots" content="noindex,follow">\n' if h.status == "noindex" else ""
    parts = [f"""<main class="tool">
  <nav class="crumbs" aria-label="Breadcrumb"><a href="/">Home</a><span class="sep">›</span><a href="/tools/">Tools</a><span class="sep">›</span><span aria-current="page">{esc(h.name)}</span></nav>
  <h1>{esc(h.name)} — what creators actually do with it</h1>
  <p class="upd">Updated <time datetime="{esc(updated)}">{esc(updated)}</time> · {len(h.items)} posts · {h.sa} S/A-tier</p>
  <p class="lead">{summary(h, tiers, creators, hubs)}</p>"""]
    c = cta(h, aff, cfg)
    if c:
        parts.append(f'  <div class="cta">{c}</div>')
    if data.get("take"):
        parts.append(f'  <h2>Editor\'s take</h2>\n  <div class="take">\n{render_take(data["take"], id_to_slug)}\n  </div>')
    if h.guides:
        li = "".join(f'<li><a class="t" href="/guides/{esc(g["slug"])}">{esc(g["title"])}</a>'
                     f'<span class="n">{g["n"]} of its posts</span>'
                     + (f'<span class="s">{esc(clip(g["short"], 240))}</span>' if g["short"] else "") + "</li>"
                     for g in h.guides)
        parts.append(f'  <h2>Guides using it</h2>\n  <ul class="glist">{li}</ul>')
    rows = []
    for e in sorted(h.items, key=sort_key):
        meta = " · ".join(x for x in ((f"@{handle(e)}" if handle(e) else ""), fmt_date(e.get("date")), e.get("type") or "") if x)
        rows.append(f'<li>{tier_badge(e.get("tier"))}<a class="t" href="/e/{esc(safe_slug(e["id"]))}">'
                    f'{esc(clip(e.get("title") or e["id"], 110))}</a>'
                    + (f'<span class="m">{esc(meta)}</span>' if meta else "") + "</li>")
    parts.append(f'  <h2>All {len(h.items)} posts · best first</h2>\n  <ol class="entries">\n' + "\n".join(rows) + "\n  </ol>")
    if h.pairs:
        def chip(p, n):
            o = hubs.get(p)
            label = f'<a href="/tools/{esc(o.slug)}">{esc(p)}</a>' if o and o.status in ("index", "noindex") else esc(p)
            return f'<li>{label}<span class="n">{n}</span></li>'
        parts.append('  <h2>Pairs with</h2>\n  <ul class="chips">' + "".join(chip(p, n) for p, n in h.pairs) + "</ul>"
                     + '\n  <p class="note">Count = posts that tag both tools.</p>')
    alts = []
    for s in data.get("alternatives") or []:
        o = next((x for x in hubs.values() if x.slug == s and x.status in ("index", "noindex")), None)
        if o and o is not h:
            alts.append(f'<li><a href="/tools/{esc(o.slug)}">{esc(o.name)}</a><span class="n">{len(o.items)} posts</span></li>')
    if alts:
        parts.append('  <h2>Alternatives in this archive</h2>\n  <ul class="chips">' + "".join(alts) + "</ul>")
    if h.packs:
        li = "".join(f'<li><a href="/guides/{esc(s)}#prompt-system">{esc(s.replace("-", " "))}</a>'
                     f'<span class="n">{n} mention{"s" if n != 1 else ""}</span></li>' for s, n in h.packs)
        parts.append(f'  <h2>Prompt systems that use it</h2>\n  <ul class="chips">{li}</ul>')
    if data.get("faq"):
        qa = "".join(f'<li><span class="t">{esc(f["q"])}</span><span class="s">{render_take(f["a"], id_to_slug)[3:-4]}</span></li>'
                     for f in data["faq"] if f.get("q") and f.get("a"))
        parts.append(f'  <h2>Questions</h2>\n  <ul class="glist">{qa}</ul>')
    parts.append('  <p class="more"><a href="/tools/">All tool hubs</a><a href="/catalog">Filter in the catalog</a>'
                 '<a href="/guides/">All guides</a></p>\n</main>\n</body></html>\n')
    return HEAD.format(title=esc(title), desc=esc(describe(h, tiers, creators)), robots=robots) + "\n".join(parts)


def render_index(hubs: dict[str, Hub]) -> str:
    live = [h for h in hubs.values() if h.status in ("index", "noindex")]
    n_posts = len({i for h in live for i in h.ids})
    sections = []
    for key, label, blurb in PILLARS:
        hs = sorted((h for h in live if TOOL_META.get(h.name, ("", "other"))[1] == key),
                    key=lambda h: (h.status != "index", -len(h.items), h.name))
        if not hs:
            continue
        cards = "".join(f'<li><a href="/tools/{esc(h.slug)}"><h3>{esc(h.name)}</h3>'
                        f'<span class="m">{len(h.items)} posts · {h.sa} S/A'
                        + (f' · {len(h.guides)} guide{"s" if len(h.guides) != 1 else ""}' if h.guides else "")
                        + f'</span><p>{esc(TOOL_META.get(h.name, ("", "", ""))[2])}</p></a></li>' for h in hs)
        sections.append(f'  <h2>{esc(label)}</h2>\n  <p class="pdesc">{esc(blurb)}</p>\n  <ul class="tgrid">{cards}</ul>')
    other = sorted((h for h in live if h.name not in TOOL_META), key=lambda h: -len(h.items))
    if other:
        sections.append('  <h2>Other tools</h2>\n  <ul class="tgrid">' + "".join(
            f'<li><a href="/tools/{esc(h.slug)}"><h3>{esc(h.name)}</h3><span class="m">{len(h.items)} posts</span></a></li>'
            for h in other) + "</ul>")
    lead = (f"{len(live)} tools that at least three saved posts in this archive cover, {n_posts} posts in all. "
            f"Each hub collects what creators actually built with the tool, the guides that use it, "
            f"the tools it pairs with, and a link to the official site.")
    title = f"AI tool hubs: {len(live)} tools, what creators do with them · DejaViewed"
    body = f"""<main class="tool">
  <nav class="crumbs" aria-label="Breadcrumb"><a href="/">Home</a><span class="sep">›</span><span aria-current="page">Tools</span></nav>
  <h1>Tools</h1>
  <p class="lead">{esc(lead)}</p>
{chr(10).join(sections)}
  <p class="more"><a href="/catalog">Filter in the catalog</a><a href="/collections/">Collections</a><a href="/guides/">All guides</a></p>
</main>
</body></html>
"""
    return HEAD.format(title=esc(title), desc=esc(clip(lead, 158)), robots="") + body


# ───────────────────────────────────────────────────────────── main
def build() -> tuple[dict[str, Hub], dict[str, str], list[str]]:
    entries = [e for e in json.loads(CATALOG.read_text(encoding="utf-8")).get("entries") or [] if e.get("id")]
    groups: dict[str, list[dict]] = defaultdict(list)
    tagsets = {}
    for e in entries:
        ts = hub_names(e)
        tagsets[e["id"]] = ts
        for t in ts:
            groups[t].append(e)
    hubs = {n: Hub(n, items) for n, items in groups.items()}
    guides = load_guides()
    qualify(hubs, guides)
    packs = load_packs()
    for h in hubs.values():
        if h.status == "skip":
            continue
        co = Counter(t for e in h.items for t in tagsets[e["id"]] if t != h.name)
        h.pairs = sorted(((t, n) for t, n in co.items() if n >= 2), key=lambda x: (-x[1], x[0].lower()))[:12]
        rx = name_re(h.name, [a for a in ((h.data or {}).get("aliases") or []) if len(a) > 2])
        h.packs = sorted(((s, len(rx.findall(txt))) for s, txt in packs.items() if rx.search(txt)),
                         key=lambda x: (-x[1], x[0]))[:10]
    all_ids = {e["id"] for e in entries}
    errs = []
    gslugs = {g["slug"] for g in guides} | {p.stem for p in (SITE / "guides").glob("*.html")}
    for h in hubs.values():
        if h.data and h.data.get("take"):
            errs += validate_take(h.slug, h.data["take"], h.ids, all_ids, gslugs)
            for f in h.data.get("faq") or []:
                errs += validate_take(h.slug + " faq", f.get("a", ""), h.ids, all_ids, gslugs)
    id_to_slug = {e["id"]: safe_slug(e["id"]) for e in entries}
    aff, cfg = load_aff()
    pages = {}
    for h in hubs.values():
        if h.status in ("index", "noindex"):
            pages[f"{h.slug}.html"] = render_hub(h, hubs, id_to_slug, aff, cfg)
    pages["index.html"] = render_index(hubs)
    return hubs, pages, errs


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="dry run; exit 1 if anything would change or a take is invalid")
    args = ap.parse_args()
    if not CATALOG.exists():
        print(f"[tools] {CATALOG} missing — run cms.py rebuild first", file=sys.stderr)
        return 1
    hubs, pages, errs = build()
    for e in errs:
        print(f"[tools] ERROR {e}", file=sys.stderr)
    changed = [n for n, t in pages.items() if not (OUT / n).is_file() or (OUT / n).read_text(encoding="utf-8") != t]
    stale = [p.name for p in OUT.glob("*.html") if p.name not in pages] if OUT.is_dir() else []
    if not args.check:
        if errs:
            print("[tools] refusing to write: fix the take errors above", file=sys.stderr)
            return 1
        OUT.mkdir(exist_ok=True)
        DATA_TOOLS.mkdir(parents=True, exist_ok=True)
        for n in stale:
            (OUT / n).unlink()
        for n in changed:
            (OUT / n).write_text(pages[n], encoding="utf-8")
        for h in hubs.values():   # scaffold an editable data file for every hub with a page
            p = DATA_TOOLS / f"{h.slug}.json"
            if h.status in ("index", "noindex") and not p.exists():
                p.write_text(json.dumps({"slug": h.slug, "tool": h.name, "aliases": [], "take": "", "alternatives": [],
                                         "faq": [], "updated": TODAY_FALLBACK}, indent=2, ensure_ascii=False) + "\n",
                             encoding="utf-8")
    idx = sorted((h for h in hubs.values() if h.status == "index"), key=lambda h: -len(h.items))
    nox = sorted((h for h in hubs.values() if h.status == "noindex"), key=lambda h: -len(h.items))
    skp = [h for h in hubs.values() if h.status == "skip"]
    print(f"[tools] indexed {len(idx)}: " + ", ".join(f"{h.name} ({len(h.items)})" for h in idx))
    print(f"[tools] noindex {len(nox)}: " + "; ".join(f"{h.name} ({len(h.items)}: {', '.join(h.reasons)})" for h in nox))
    print(f"[tools] skipped {len(skp)} tools with < {MIN_PAGE} entries; excluded as generic/non-software: "
          + ", ".join(sorted(EXCLUDE)))
    words = sorted(take_words((h.data or {}).get("take", "")) for h in idx)
    if words:
        print(f"[tools] editor take words (indexed): min {words[0]}, median {words[len(words) // 2]}, max {words[-1]}")
    verb = "would change" if args.check else "wrote"
    print(f"[tools] {verb} {len(changed)} page(s), {'would remove' if args.check else 'removed'} {len(stale)} stale")
    if args.check:
        return 1 if (changed or stale or errs) else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
