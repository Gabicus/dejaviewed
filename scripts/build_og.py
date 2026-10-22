#!/usr/bin/env python3
"""Render 1200x630 Open Graph images into site/og/ with headless Chromium.

Targets: every guide (og/<slug>.png), every deeper dive (og/deeper-insight-<slug>.png),
and the top pages (default, catalog, prompts, start-here). Entry pages are NOT
rendered; build_seo.py points them at their thumbnail.

Existing images are skipped unless --force. A PNG over 150 KB is re-shot as
JPEG quality 85 (.jpg) and the PNG removed.

Usage:
  python3 scripts/build_og.py            # render missing
  python3 scripts/build_og.py --force    # re-render all
  python3 scripts/build_og.py --only plotter-loop default
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_seo import Ctx, SITE, clip, og_image_rel, sr_first_paragraph, strip_title_suffix  # noqa: E402

OUT = SITE / "og"
MAX_BYTES = 150 * 1024
esc = lambda s: html.escape(str(s), quote=True)

TEMPLATE = """<!doctype html><html><head><meta charset="utf-8">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@500;700;800;900&family=JetBrains+Mono:wght@500;700&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:1200px;height:630px;background:#0a0a0f;overflow:hidden}}
body{{font-family:'Inter',system-ui,sans-serif;color:#e8e8f0;position:relative}}
.glow{{position:absolute;inset:0;background:
  radial-gradient(600px 380px at 92% 8%,rgba(167,139,250,.22),transparent 70%),
  radial-gradient(520px 340px at 4% 100%,rgba(244,114,182,.16),transparent 70%)}}
.bar{{position:absolute;left:0;right:0;top:0;height:6px;background:linear-gradient(90deg,#a78bfa,#f472b6,#60a5fa)}}
.wrap{{position:absolute;inset:0;padding:64px 72px 56px;display:flex;flex-direction:column}}
.kind{{font:700 20px/1 'JetBrains Mono',monospace;letter-spacing:.16em;text-transform:uppercase;color:#a78bfa}}
h1{{margin-top:28px;font-weight:900;letter-spacing:-.03em;line-height:1.06;font-size:{fs}px;
  background:linear-gradient(135deg,#fff 0%,#a78bfa 55%,#f472b6 100%);-webkit-background-clip:text;background-clip:text;color:transparent;
  display:-webkit-box;-webkit-line-clamp:4;-webkit-box-orient:vertical;overflow:hidden;padding-bottom:6px}}
.sub{{margin-top:18px;font:500 24px/1.4 'Inter',sans-serif;color:#a0a0b8;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
.foot{{margin-top:auto;display:flex;align-items:flex-end;justify-content:space-between;gap:24px}}
.stats{{font:500 21px/1.4 'JetBrains Mono',monospace;color:#c8c8d8}}
.mark{{font:800 22px/1 'Inter',sans-serif;color:#fff;letter-spacing:-.01em;white-space:nowrap;display:flex;align-items:center;gap:10px}}
.mark i{{width:14px;height:14px;border-radius:50%;background:#a78bfa;display:inline-block}}
</style></head><body><div class="glow"></div><div class="bar"></div>
<div class="wrap"><div class="kind">{kind}</div><h1>{title}</h1>{sub}
<div class="foot"><div class="stats">{stats}</div><div class="mark"><i></i>dejaviewed.dev</div></div></div>
</body></html>"""


def page_title(path: Path) -> str:
    m = re.search(r"<title>(.*?)</title>", path.read_text(errors="replace"), re.S)
    t = strip_title_suffix(html.unescape(m.group(1))) if m else path.stem
    return re.sub(r"\s*—\s*Deeper Dive$", "", t)


def targets(c: Ctx) -> list[dict]:
    t = []
    top_stats = f"{c.n_entries} posts · {c.n_colls} collections · {len(c.guides)} guides · {c.n_packs} prompt systems"
    t.append(dict(name="default", kind="dejaviewed", title="You've saved this before.",
                  sub="A curated, transcribed archive of practitioner posts on AI, creative code and quant.",
                  stats=top_stats))
    t.append(dict(name="catalog", kind="catalog", title=f"{c.n_entries} curated posts, tiered S to C",
                  sub="Filter by tool, technique, creator and collection.",
                  stats=f"{c.n_creators} creators · {c.n_transcripts} transcripts · {c.n_colls} collections"))
    t.append(dict(name="prompts", kind="prompt systems", title="A runnable prompt system for every guide",
                  sub="One-shot prompt, step prompts with audits, gap audit, validation oracles.",
                  stats=f"{c.n_packs} systems · {c.n_steps} step prompts"))
    t.append(dict(name="start-here", kind="start here", title="What DejaViewed is and how to use it",
                  sub="For people starting with agents, builders, researchers, and agents themselves.",
                  stats=top_stats))
    for g in c.guides:
        pack = c.packs.get(g) or {}
        n_e = len(c.guide_entries(g))
        tools = ", ".join(c.guide_tools(g, 3))
        bits = []
        if n_e:
            bits.append(f"{n_e} source post{'s' if n_e != 1 else ''}")
        if pack.get("steps"):
            bits.append(f"{len(pack['steps'])}-step prompt system")
        if tools:
            bits.append(tools)
        gp = SITE / "guides" / f"{g}.html"
        thesis = (c.manual.get(g) or {}).get("thesis") or sr_first_paragraph(gp.read_text(errors="replace"))
        t.append(dict(name=g, kind="guide", title=page_title(gp), sub=clip(thesis, 150),
                      stats=" · ".join(bits)))
    for stem in c.deepers:
        dd = c.deeper.get(stem) or {}
        n_e = dd.get("entry_count") or len(dd.get("entries") or [])
        tools = ", ".join((dd.get("tools") or [])[:3])
        bits = [f"{n_e} connected posts"] if n_e else []
        if tools:
            bits.append(tools)
        t.append(dict(name=stem, kind="deeper dive", title=page_title(SITE / "deeper" / f"{stem}.html"),
                      sub=clip(dd.get("thesis") or "", 150),
                      stats=" · ".join(bits)))
    return t


def font_size(title: str) -> int:
    n = len(title)
    return 76 if n <= 40 else 64 if n <= 70 else 54 if n <= 100 else 46


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", nargs="*", default=None, help="image names to (re)render")
    args = ap.parse_args()

    c = Ctx()
    todo = targets(c)
    if args.only:
        todo = [t for t in todo if t["name"] in set(args.only)]
    if not args.force and not args.only:
        todo = [t for t in todo if not og_image_rel(t["name"])]
    OUT.mkdir(exist_ok=True)
    if not todo:
        print("og: nothing to render (all present; use --force)")
        return 0

    from playwright.sync_api import sync_playwright
    made, jpg = 0, 0
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1200, "height": 630}, device_scale_factor=1)
        for i, t in enumerate(todo):
            sub = f'<div class="sub">{esc(t["sub"])}</div>' if t["sub"] else ""
            doc = TEMPLATE.format(fs=font_size(t["title"]), kind=esc(t["kind"]), title=esc(t["title"]),
                                  sub=sub, stats=esc(t["stats"]))
            pg.set_content(doc, wait_until="networkidle" if i == 0 else "load")
            pg.evaluate("document.fonts.ready")
            for ext in (".png", ".jpg"):
                (OUT / f"{t['name']}{ext}").unlink(missing_ok=True)
            png = OUT / f"{t['name']}.png"
            pg.screenshot(path=str(png), type="png")
            if png.stat().st_size > MAX_BYTES:
                png.unlink()
                pg.screenshot(path=str(OUT / f"{t['name']}.jpg"), type="jpeg", quality=85)
                jpg += 1
            made += 1
        b.close()
    sizes = sorted(f.stat().st_size for f in OUT.iterdir() if f.suffix in (".png", ".jpg"))
    over = sum(1 for s in sizes if s > MAX_BYTES)
    print(f"og: rendered {made} ({jpg} as jpeg) · {len(sizes)} images in site/og · "
          f"max {max(sizes) // 1024} KB · over 150 KB: {over}")
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())
