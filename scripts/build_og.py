#!/usr/bin/env python3
"""Render 1200x630 Open Graph images into site/og/ with headless Chromium.

Targets: every guide (og/<slug>.png), every deeper dive (og/deeper-insight-<slug>.png),
the top pages (default, catalog, prompts, start-here, method) and every entry page
(og/e/<slug>.jpg: title, creator, tier, collection, thumbnail on the right).

An image is (re)rendered only when it is missing or its inputs changed: a content hash of
(template version, kind, title, sub, stats, thumbnail size+mtime) per image is kept in
data/seo/og_hashes.json. --force re-renders everything. A guide/top PNG over 150 KB is
re-shot as JPEG quality 85 (.jpg) and the PNG removed; entry cards are always JPEG.

Usage:
  python3 scripts/build_og.py            # render missing / changed
  python3 scripts/build_og.py --force    # re-render all
  python3 scripts/build_og.py --only plotter-loop default e/DXYSxNLpIAY
  python3 scripts/build_og.py --no-entries   # skip the entry cards
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import html
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_seo import (DATA, Ctx, SITE, clip, load_json, og_image_rel, safe_slug, sr_first_paragraph,  # noqa: E402
                       strip_title_suffix, thumb_rel, write_if_changed)

try:
    from build_collections import collection_name  # display names ("AI Saves, Vol. 1")
except Exception:  # pragma: no cover - optional sibling
    def collection_name(c: str) -> str:
        return re.sub(r"[-_]+", " ", c or "").title()

OUT = SITE / "og"
MAX_BYTES = 150 * 1024
HASHES = DATA / "seo" / "og_hashes.json"
TEMPLATE_VERSION = "3"   # bump to force a full re-render after a template change
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
.th{{position:absolute;top:64px;right:64px;width:330px;height:440px;border-radius:18px;overflow:hidden;
  border:1px solid rgba(255,255,255,.12);box-shadow:0 20px 60px rgba(0,0,0,.5);background:#15151f}}
.th img{{width:100%;height:100%;object-fit:cover;display:block}}
body.has-th .wrap{{padding-right:440px}}
body.has-th .foot{{margin-right:-376px}}
</style></head><body class="{bodycls}"><div class="glow"></div><div class="bar"></div>{thumb}
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
    t.append(dict(name="method", kind="how it works", title="How DejaViewed is made",
                  sub="Saves, transcripts, enrichment, tiers S to C, curated guides and prompt systems.",
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


def entry_targets(c: Ctx) -> list[dict]:
    t = []
    for e in c.entries:
        if not e.get("id") or not (SITE / "e" / f"{safe_slug(e['id'])}.html").is_file():
            continue
        coll = collection_name(e.get("collection") or "")
        bits = [f"@{e['creator']}" if e.get("creator") else "", e.get("type") or "",
                ", ".join((e.get("tools") or [])[:2])]
        th = thumb_rel(e)
        t.append(dict(name=f"e/{safe_slug(e['id'])}", kind=f"tier {e.get('tier') or 'C'} · {coll}".strip(" ·"),
                      title=re.sub(r"\s+", " ", e.get("title") or "Untitled").strip(),
                      sub=clip(e.get("summary") or "", 140), stats=" · ".join(b for b in bits if b),
                      thumb=th, jpeg=True))
    return t


def target_hash(t: dict) -> str:
    th = t.get("thumb") or ""
    st = ""
    if th:
        s = (SITE / th).stat()
        st = f"{s.st_size}:{int(s.st_mtime)}"
    key = json.dumps([TEMPLATE_VERSION, t["kind"], t["title"], t["sub"], t["stats"], th, st], ensure_ascii=False)
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def thumb_data_uri(rel: str) -> str:
    """Thumbnail as a downscaled JPEG data URI (pages are set via set_content, so file:// is unreliable)."""
    from io import BytesIO
    from PIL import Image
    with Image.open(SITE / rel) as im:
        im = im.convert("RGB")
        im.thumbnail((660, 880))
        buf = BytesIO()
        im.save(buf, "JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def nowrap_hyphens(s: str) -> str:
    """Keep hyphenated tokens ("GPT-5") on one line."""
    return re.sub(r"(\S+-\S+)", r'<span style="white-space:nowrap">\1</span>', s)


def font_size(title: str, narrow: bool = False) -> int:
    n = len(title)
    if narrow:
        return 60 if n <= 30 else 50 if n <= 60 else 42 if n <= 90 else 36
    return 76 if n <= 40 else 64 if n <= 70 else 54 if n <= 100 else 46


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--only", nargs="*", default=None, help="image names to (re)render")
    ap.add_argument("--no-entries", action="store_true", help="skip the per-entry cards")
    args = ap.parse_args()

    c = Ctx()
    alltargets = targets(c) + ([] if args.no_entries else entry_targets(c))
    hashes: dict = load_json(HASHES, {}) or {}
    for t in alltargets:
        t["hash"] = target_hash(t)
    todo = alltargets
    if args.only:
        todo = [t for t in todo if t["name"] in set(args.only)]
    if not args.force and not args.only:
        todo = [t for t in todo if not og_image_rel(t["name"]) or hashes.get(t["name"]) != t["hash"]]
    OUT.mkdir(exist_ok=True)
    (OUT / "e").mkdir(exist_ok=True)
    if not todo:
        print(f"og: nothing to render ({len(alltargets)} images up to date; use --force)")
        return 0

    from playwright.sync_api import sync_playwright
    made, jpg, t0 = 0, 0, time.time()
    try:
        with sync_playwright() as p:
            def fresh_browser():
                # software rendering: the GPU process crashes after a few hundred screenshots
                br = p.chromium.launch(args=["--disable-gpu", "--disable-dev-shm-usage"])
                return br, br.new_page(viewport={"width": 1200, "height": 630}, device_scale_factor=1)
            b, pg = fresh_browser()
            for i, t in enumerate(todo):
                if i and i % 200 == 0:   # recycle the browser to keep memory flat
                    b.close()
                    b, pg = fresh_browser()
                sub = f'<div class="sub">{esc(t["sub"])}</div>' if t["sub"] else ""
                thumb = ""
                if t.get("thumb"):
                    try:
                        thumb = f'<div class="th"><img src="{thumb_data_uri(t["thumb"])}" alt=""></div>'
                    except Exception:
                        thumb = ""
                doc = TEMPLATE.format(fs=font_size(t["title"], bool(thumb)), kind=esc(t["kind"]),
                                      title=nowrap_hyphens(esc(t["title"])), sub=sub, stats=esc(t["stats"]),
                                      thumb=thumb, bodycls="has-th" if thumb else "")
                pg.set_content(doc, wait_until="networkidle" if i % 200 == 0 else "load")
                pg.evaluate("document.fonts.ready")
                for ext in (".png", ".jpg"):
                    (OUT / f"{t['name']}{ext}").unlink(missing_ok=True)
                if t.get("jpeg"):
                    pg.screenshot(path=str(OUT / f"{t['name']}.jpg"), type="jpeg", quality=80)
                    jpg += 1
                else:
                    png = OUT / f"{t['name']}.png"
                    pg.screenshot(path=str(png), type="png")
                    if png.stat().st_size > MAX_BYTES:
                        png.unlink()
                        pg.screenshot(path=str(OUT / f"{t['name']}.jpg"), type="jpeg", quality=85)
                        jpg += 1
                hashes[t["name"]] = t["hash"]
                made += 1
                if made % 100 == 0:
                    print(f"  og: {made}/{len(todo)} ({time.time() - t0:.0f}s)", flush=True)
                    write_if_changed(HASHES, json.dumps(hashes, indent=1, sort_keys=True) + "\n")
            b.close()
    finally:
        write_if_changed(HASHES, json.dumps(hashes, indent=1, sort_keys=True) + "\n")
    files = [f for f in OUT.rglob("*") if f.suffix in (".png", ".jpg")]
    sizes = sorted(f.stat().st_size for f in files)
    over = sum(1 for f in files if f.parent == OUT and f.stat().st_size > MAX_BYTES)
    print(f"og: rendered {made} ({jpg} as jpeg) in {time.time() - t0:.0f}s · {len(sizes)} images in site/og "
          f"({sum(sizes) // (1024 * 1024)} MB) · max {max(sizes) // 1024} KB · guide/top images over 150 KB: {over}")
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main())
