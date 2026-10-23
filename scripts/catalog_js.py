#!/usr/bin/env python3
"""Emit site/catalog.js, site/catalog.slim.js and site/summaries.js, and prerender the catalog page.

Wraps the JSON blobs in `window.__CATALOG` / `window.__SUMMARIES` /
`window.__RECOMMENDATIONS` so pages work when opened directly from disk
(fetch() is blocked on file:// in most browsers). Pages check window.__X
first, fall back to fetch().

catalog.slim.js (`window.__CATALOG_SLIM`) is the card-only subset the catalog page
needs: no caption / transcript / takeaways / media_url, summary clipped to 160 chars.
The full catalog.js stays for pages that read the heavy fields (graph, board, admin...).

Also prerenders, between idempotent markers in site/catalog.html:
    <!-- catalog:cats:start/end -->   category buttons with live counts
    <!-- catalog:colls:start/end -->  collection pills (computed from data, never hardcoded)
    <!-- catalog:stats:start/end -->  sidebar stat tiles
    <!-- catalog:cards:start/end -->  the first FIRST_CARDS cards of the default view
The page's JS hydrates those cards in place (reuses the nodes by data-id) instead of
wiping and re-inserting them. Finally re-runs the landing prerender (build_landing_meta)
so the home page counts match the final catalog.json.
"""
from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
THUMBS = SITE / "thumb"
FIRST_CARDS = 24
SUMMARY_MAX = 160

PAIRS = [
    (SITE / "catalog.json",         SITE / "catalog.js",         "__CATALOG"),
    (SITE / "summaries.json",       SITE / "summaries.js",       "__SUMMARIES"),
    (SITE / "recommendations.json", SITE / "recommendations.js", "__RECOMMENDATIONS"),
]


def write_if_changed(dst: Path, text: str) -> bool:
    if dst.exists() and dst.read_text(encoding="utf-8") == text:
        return False
    dst.write_text(text, encoding="utf-8")
    return True


def wrap(src: Path, dst: Path, var: str) -> None:
    if not src.exists():
        print(f"[catalog_js] skip {src.name} (missing)")
        return
    data = json.loads(src.read_text(encoding="utf-8"))
    body = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    banner = f"// Auto-generated from {src.name} for file:// previews. Do not edit by hand.\n"
    write_if_changed(dst, banner + f"window.{var} = {body};\n")
    print(f"[catalog_js] wrote {dst.relative_to(ROOT)} ({dst.stat().st_size:,} bytes)")


# ── slim catalog ─────────────────────────────────────────────────────────────

def clean(s) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]*>", "", str(s or ""))).strip()


def clip(s: str, n: int = SUMMARY_MAX) -> str:
    s = clean(s)
    if len(s) <= n:
        return s
    cut = s[: n - 1]
    sp = cut.rfind(" ")
    cut = cut[:sp] if sp > n * 0.6 else cut
    return re.sub(r"[\s,;:—–-]+$", "", cut) + "…"


def shortcode(url: str) -> str:
    m = re.search(r"/(?:p|reel)/([^/?#]+)", url or "")
    return m.group(1) if m else ""


_thumb_dims: dict[str, tuple[int, int] | None] = {}


def thumb_rel(e: dict) -> str | None:
    """thumb/<name>.jpg if the file exists (thumbs are saved with '/' -> '_')."""
    for cand in (e.get("post_id"), shortcode(e.get("url", "")), e.get("id")):
        if not cand:
            continue
        name = str(cand).replace("/", "_") + ".jpg"
        if (THUMBS / name).is_file():
            return "thumb/" + name
    return None


def thumb_dims(rel: str) -> tuple[int, int] | None:
    if rel not in _thumb_dims:
        try:
            from PIL import Image
            with Image.open(SITE / rel) as im:
                _thumb_dims[rel] = im.size
        except Exception:
            _thumb_dims[rel] = None
    return _thumb_dims[rel]


def slim_entry(e: dict) -> dict:
    out = {
        "id": e.get("id") or "",
        "title": e.get("title") or "",
        "summary": clip(e.get("summary") or e.get("caption") or ""),
        "creator": e.get("creator") or "",
        "tier": e.get("tier") or "C",
        "type": e.get("type") or "resource",
        "collection": e.get("collection") or e.get("source_collection") or "",
        "collections": e.get("collections") or [],
        "tools": e.get("tools") or [],
        "techniques": e.get("techniques") or [],
        "repos": e.get("repos") or [],
        "url": e.get("url") or "",
        "date": e.get("date") or "",
    }
    t = thumb_rel(e)
    if t:
        out["thumb"] = t
    if e.get("has_guide") and e.get("deep_dive_slug"):
        out["guide"] = e["deep_dive_slug"]
    if e.get("is_new"):
        out["is_new"] = True
    return out


def build_slim(cat: dict) -> dict:
    return {"generated": cat.get("generated"), "stats": cat.get("stats", {}),
            "entries": [slim_entry(e) for e in cat.get("entries", [])]}


def write_slim(slim: dict) -> None:
    dst = SITE / "catalog.slim.js"
    body = json.dumps(slim, ensure_ascii=False, separators=(",", ":"))
    write_if_changed(dst, "// Auto-generated by scripts/catalog_js.py from catalog.json (card fields only). "
                     "Do not edit by hand.\n" f"window.__CATALOG_SLIM = {body};\n")
    print(f"[catalog_js] wrote {dst.relative_to(ROOT)} ({dst.stat().st_size:,} bytes, "
          f"{len(slim['entries'])} entries)")


# ── catalog.html prerender ───────────────────────────────────────────────────

SECTION_ORDER = [  # mirrors SECTION_ORDER in catalog.html's script
    ("technique", "🔬 Techniques", "var(--c-technique, #a78bfa)"),
    ("inspiration", "✨ Inspiration", "var(--c-inspiration, #f472b6)"),
    ("tool", "🛠 Tools", "var(--c-tool)"),
    ("skill", "⚡ Skills", "var(--c-skill)"),
    ("news", "📰 News", "var(--c-news, #fbbf24)"),
    ("resource", "📚 Resources", "var(--c-resource)"),
    ("demo", "🎬 Demos", "var(--c-demo, #4cdc8c)"),
    ("repo", "🧰 Repos", "var(--c-repo)"),
    ("platform", "🌐 Platforms", "var(--c-platform)"),
    ("guide", "📘 Guides", "var(--c-guide)"),
    ("art", "🎨 Art", "var(--c-art, #f05060)"),
    ("design", "✏️ Design", "var(--c-design, #fb7185)"),
]
CAT_BUTTONS = [  # (data-cat, label) — order of the sidebar category buttons
    ("art", "Art"), ("design", "Design"), ("inspiration", "Inspiration"), ("technique", "Techniques"),
    ("tool", "Tools"), ("news", "News"), ("resource", "Resources"), ("demo", "Demos"), ("repo", "Repos"),
    ("platform", "Platforms"), ("guide", "Guides"), ("skill", "Skills"),
]
COLL_LABELS = {"ai1": "AI1", "ai2": "AI2", "ai3": "AI3", "ai4": "AI4", "ai5": "AI5", "ai6": "AI6",
               "quant": "QUANT", "stock2": "STOCK2", "music": "MUSIC", "creative": "CREATIVE",
               "prompts": "PROMPTS", "game-theory": "GAME-TH",
               "art-inspiration": "ART-INSP", "art-i-like": "ART-LIKE"}  # mirrors buildCollPills()
TIER_RANK = {"S": 0, "A": 1, "B": 2, "C": 3}

esc = lambda s: html.escape(str(s), quote=True)  # noqa: E731


def patch(text: str, name: str, inner: str, prefix: str) -> str:
    start, end = f"<!-- {prefix}:{name}:start -->", f"<!-- {prefix}:{name}:end -->"
    pat = re.compile(re.escape(start) + r".*?" + re.escape(end), re.S)
    if not pat.search(text):
        raise SystemExit(f"[{prefix}] marker {start} missing")
    return pat.sub(lambda _m: start + inner + end, text, count=1)


def card_html(p: dict) -> str:
    primary = p["type"] or "resource"
    sc = shortcode(p["url"])
    creator = p["creator"]
    ig = "https://instagram.com/" + creator.lstrip("@") if creator else "#"
    meta_tail = " · " + p["collection"] + (" · " + p["date"] if p["date"] else "")
    top = (f'<div class="top"><div class="meta"><a href="{esc(ig)}" target="_blank" rel="noopener">'
           f'{esc(creator or "unknown")}</a>{esc(meta_tail)}</div>'
           f'<span class="tier {esc(p["tier"])}">{esc(p["tier"])}</span>'
           + ('<span class="badge-new">NEW</span>' if p.get("is_new") else "") + "</div>")
    acts = ""
    if p["url"]:
        label = "Open post ↗" if "instagram.com" in p["url"] else "View source ↗"
        acts += f'<a class="btn" href="{esc(p["url"])}" target="_blank" rel="noopener">{label}</a>'
    if p.get("guide"):
        acts += f'<a class="btn primary" href="/guides/{esc(quote(p["guide"]))}">Deep dive →</a>'
    thumb = ""
    if p.get("thumb"):
        dims = thumb_dims(p["thumb"])
        wh = f' width="{dims[0]}" height="{dims[1]}"' if dims else ""
        thumb = (f'<a class="thumb" href="{esc(p["url"])}" target="_blank" rel="noopener">'
                 f'<img loading="lazy" decoding="async" alt="{esc(p["title"])}" src="{esc(p["thumb"])}"{wh}></a>')
    return (f'<article class="card cat-{esc(primary)}" data-tier="{esc(p["tier"])}" id="post-{esc(sc)}" '
            f'data-id="{esc(p["id"])}"><h4 class="ctitle">{esc(p["title"])}</h4>{top}'
            f'<div class="sum-wrap"><p class="summary">{esc(p["summary"])}</p></div>'
            f'<div class="actions">{acts}</div>{thumb}</article>')


def prerender_catalog(slim: dict) -> None:
    page = SITE / "catalog.html"
    text = page.read_text(encoding="utf-8")
    posts = slim["entries"]

    # Category buttons
    n_by_type: dict[str, int] = {}
    for p in posts:
        n_by_type[p["type"]] = n_by_type.get(p["type"], 0) + 1
    btn = lambda k, label, n, on="": (  # noqa: E731
        f'<button class="cat-btn{on}" data-cat="{k}"><span><span class="dot"></span> {label}</span>'
        f'<span class="n">{n}</span></button>')
    cats = btn("all", "All", len(posts), " on") + "".join(
        btn(k, label, n_by_type.get(k, 0)) for k, label in CAT_BUTTONS)
    text = patch(text, "cats", cats, "catalog")

    # Collection pills — computed from the data
    coll_counts: dict[str, int] = {}
    for p in posts:
        if p["collection"]:
            coll_counts[p["collection"]] = coll_counts.get(p["collection"], 0) + 1
    colls = "".join(f'<button class="coll-pill" data-coll="{esc(c)}">{esc(COLL_LABELS.get(c, c.upper()))} '
                    f'{coll_counts[c]}</button>' for c in sorted(coll_counts))
    text = patch(text, "colls", colls, "catalog")

    # Stats tiles
    creators = {p["creator"] for p in posts}
    stats = [("stat-posts", len(posts), "Posts"), ("stat-creators", len(creators), "Creators"),
             ("stat-stier", sum(p["tier"] == "S" for p in posts), "S-tier"),
             ("stat-repos", sum(p["type"] == "repo" for p in posts), "Repos")]
    text = patch(text, "stats", "".join(
        f'<div class="ban"><div class="v" id="{i}">{v}</div><div class="l">{label}</div></div>'
        for i, v, label in stats), "catalog")
    n_colls = len({p["collection"] for p in posts})
    text = patch(text, "about", esc(f"{len(posts)} curated entries · {n_colls} collections · "
                                    f"{len(creators)} creators"), "catalog")
    text = patch(text, "creators", esc(f"👥 {len(creators)} creators cited"), "catalog")

    # First cards of the default view: tier S→C, then newest first; grouped by primary type
    # same order as the JS comparator (tier rank, then date string desc; stable for ties)
    ordered = sorted(posts, key=lambda p: p["date"] or "", reverse=True)
    ordered = sorted(ordered, key=lambda p: TIER_RANK.get(p["tier"], 4))
    buckets: dict[str, list[dict]] = {}
    for p in ordered:
        buckets.setdefault(p["type"] or "resource", []).append(p)
    out, left = [], FIRST_CARDS
    for key, label, color in SECTION_ORDER:
        arr = buckets.get(key) or []
        if not arr or left <= 0:
            continue
        icon, rest = label.split(" ")[0], " ".join(label.split(" ")[1:])
        out.append(f'<div class="section-head"><h3><span class="icon" style="background:{color}">{icon}</span> '
                   f'{esc(rest)}</h3><span class="count">{len(arr)} items</span></div>')
        out.append('<div class="grid">' + "".join(card_html(p) for p in arr[:left]) + "</div>")
        left -= len(arr[:left])
    text = patch(text, "cards", "".join(out), "catalog")

    if write_if_changed(page, text):
        print(f"[catalog_js] prerendered catalog.html ({FIRST_CARDS} cards, {len(coll_counts)} collections)")
    else:
        print("[catalog_js] catalog.html prerender unchanged")


def main() -> int:
    for src, dst, var in PAIRS:
        wrap(src, dst, var)
    cat_path = SITE / "catalog.json"
    if cat_path.exists():
        slim = build_slim(json.loads(cat_path.read_text(encoding="utf-8")))
        write_slim(slim)
        prerender_catalog(slim)
    # Home page prerender uses the final catalog.json — runs here because rebuild.sh calls
    # build_landing_meta before cms.py rebuild regenerates catalog.json.
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import build_landing_meta
    build_landing_meta.prerender_index()
    return 0


if __name__ == "__main__":
    sys.exit(main())
