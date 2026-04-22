#!/usr/bin/env python3
"""Render per-entry summary pages from data/entries.parquet.

Writes one site/e/<id>.html per row, plus an index at site/e/index.html.
Uses a single template that embeds the shared.css card styling, so pages
look identical to the rest of the site.

Hierarchical tableau (Phase 5): five zoom levels per entry — 100k, 50k,
10k, 5k, 1k ft. At first render only the top level is populated from the
existing summary; lower tiers are stubs marked "needs deep-dive" that a
future LLM pass (or admin edit) can fill in.
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from cms import load_entries  # noqa: E402

SITE = ROOT / "site"
OUT = SITE / "e"


def esc(x) -> str:
    return html.escape(str(x or ""), quote=True)


def safe_slug(rid: str) -> str:
    """Filesystem-safe id (some post_ids include '/' or other chars)."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in rid)


def _pill(text: str, cls: str = "") -> str:
    return f'<span class="pill{" "+cls if cls else ""}">{esc(text)}</span>'


def _tier_pill(tier: str) -> str:
    t = (tier or "C").upper()
    return f'<span class="tier-pill tier-{t.lower()}">{esc(t)}-TIER</span>'


def tableau_levels(row: dict) -> list[dict]:
    """Five zoom levels, top-down. Missing fields get a placeholder so the
    UI renders consistently even before a deep-dive pass fills them in."""
    summary = (row.get("summary") or "").strip()
    takeaways = row.get("takeaways") or []
    takeaways = takeaways[: min(len(takeaways), 5)]
    caption = (row.get("caption") or "").strip()
    deep = row.get("deep_dive_slug") or ""
    tools = row.get("tools") or []
    techniques = row.get("techniques") or []
    return [
        {"label": "100k ft — What is this?",
         "body": row.get("title") or "(untitled)",
         "tags": [row.get("type"), row.get("tier") + "-tier" if row.get("tier") else ""]},
        {"label": "50k ft — Why care?",
         "body": summary or "(no summary — add via admin UI)",
         "tags": row.get("domains") or []},
        {"label": "10k ft — Key takeaways",
         "body": "\n".join(f"• {t}" for t in takeaways) or "(no takeaways yet)",
         "tags": []},
        {"label": "5k ft — Tools & techniques",
         "body": (
             (", ".join(tools) or "(no tools tagged)") + "\n\n" +
             (", ".join(techniques) or "(no techniques tagged)")
         ),
         "tags": []},
        {"label": "1k ft — Deep-dive / try it",
         "body": (caption[:800] + ("…" if len(caption) > 800 else ""))
                 if caption else "(no deep-dive content yet — add via admin UI or run skill)",
         "tags": [deep] if deep else []},
    ]


TEMPLATE = """<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<title>{title} — DejaViewed</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="../shared.css">
<script src="../shared.js"></script>
<style>
  main.entry {{ max-width: 880px; margin: 24px auto 80px; padding: 0 20px; }}
  .entry h1 {{ font: 600 28px/1.25 Inter, system-ui; margin: 8px 0 12px; color: var(--text); }}
  .entry .meta {{ color: var(--muted); font-size: 13px; margin-bottom: 16px; }}
  .entry .actions a {{ margin-right: 10px; }}
  .tableau {{ margin-top: 28px; }}
  .level {{ background: var(--panel); border: 1px solid var(--border);
           border-radius: 12px; padding: 16px 18px; margin-bottom: 12px; }}
  .level h3 {{ margin: 0 0 8px; font: 600 13px/1 Inter, system-ui;
              letter-spacing: .08em; text-transform: uppercase; color: var(--muted); }}
  .level .body {{ white-space: pre-wrap; color: var(--text); font-size: 14px; line-height: 1.55; }}
  .level .tags {{ margin-top: 10px; display: flex; flex-wrap: wrap; gap: 6px; }}
  .pill {{ display: inline-block; padding: 2px 8px; border-radius: 999px;
          background: var(--panel-2); color: var(--muted); border: 1px solid var(--border);
          font-size: 11px; }}
  .back {{ color: var(--muted); font-size: 12px; text-decoration: none; }}
  .back:hover {{ color: var(--accent); }}
</style>
</head><body>
<script>DV.mountHeader(document.body, 'entries');</script>
<main class="entry">
  <a class="back" href="index.html">← all entries</a>
  <div style="margin:10px 0">{tier_pill} {type_pill}</div>
  <h1>{title}</h1>
  <div class="meta">{meta}</div>
  <div class="actions">
    {source_link}
  </div>
  <section class="tableau">
    {levels_html}
  </section>
</main>
</body></html>
"""


def render_one(row: dict) -> str:
    title = row.get("title") or row.get("id") or "(untitled)"
    meta_bits = []
    if row.get("creator"): meta_bits.append(esc(row["creator"]))
    if row.get("date"): meta_bits.append(esc(row["date"]))
    cols = row.get("collections") or []
    if cols: meta_bits.append("in " + ", ".join(esc(c) for c in cols))
    meta = " · ".join(meta_bits)
    source_link = (
        f'<a class="primary" href="{esc(row["url"])}" target="_blank" rel="noopener">Open post ↗</a>'
        if row.get("url") else ""
    )
    levels = tableau_levels(row)
    levels_html = "\n".join(
        f'<div class="level"><h3>{esc(L["label"])}</h3>'
        f'<div class="body">{esc(L["body"])}</div>'
        + (
            '<div class="tags">' + "".join(_pill(t) for t in L["tags"] if t) + "</div>"
            if L["tags"] else ""
        )
        + "</div>"
        for L in levels
    )
    return TEMPLATE.format(
        title=esc(title),
        tier_pill=_tier_pill(row.get("tier") or "C"),
        type_pill=_pill(row.get("type") or "resource"),
        meta=meta,
        source_link=source_link,
        levels_html=levels_html,
    )


def render_index(rows: list[dict]) -> str:
    rows = sorted(rows, key=lambda r: (r.get("tier") or "Z", r.get("title") or ""))
    cards = []
    for r in rows:
        rid = r.get("id")
        if not rid: continue
        cards.append(
            f'<a class="entry-card" href="{esc(safe_slug(rid))}.html">'
            f'  <div class="row">{_tier_pill(r.get("tier") or "C")} {_pill(r.get("type") or "resource")}</div>'
            f'  <h3>{esc((r.get("title") or "(untitled)")[:90])}</h3>'
            f'  <div class="meta">{esc(r.get("creator") or "")}'
            + (f' · {esc(", ".join(r.get("collections") or []))}' if r.get("collections") else "")
            + "</div>"
            f'  <p>{esc((r.get("summary") or "")[:180])}{"…" if (r.get("summary") or "") and len(r["summary"])>180 else ""}</p>'
            "</a>"
        )
    body = "\n".join(cards)
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><title>All Entries — DejaViewed</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap">
<link rel="stylesheet" href="../shared.css">
<script src="../shared.js"></script>
<style>
  main.entries {{ max-width: 1200px; margin: 24px auto 80px; padding: 0 20px;
                  display: grid; grid-template-columns: repeat(auto-fill,minmax(320px,1fr)); gap: 14px; }}
  .entry-card {{ display:block; background:var(--panel); border:1px solid var(--border);
                 border-radius:12px; padding:14px 16px; color:var(--text); text-decoration:none;
                 transition:border-color .15s, transform .15s; }}
  .entry-card:hover {{ border-color: var(--accent); transform: translateY(-2px); }}
  .entry-card h3 {{ font: 600 15px/1.35 Inter, system-ui; margin:8px 0 6px; color: var(--text); }}
  .entry-card .row {{ display:flex; gap:6px; font-size:11px; }}
  .entry-card .meta {{ color: var(--muted); font-size: 12px; margin-bottom: 8px; }}
  .entry-card p {{ color: var(--muted); font-size: 13px; line-height: 1.5; margin: 0; }}
  .pill {{ display:inline-block; padding:2px 8px; border-radius:999px; background:var(--panel-2);
          color:var(--muted); border:1px solid var(--border); font-size:11px; }}
</style>
</head><body>
<script>DV.mountHeader(document.body, 'entries');</script>
<main class="entries">
{body}
</main>
</body></html>
"""


def main():
    rows = load_entries()
    if not rows:
        print("[render_entries] no entries — run `python scripts/cms.py migrate` first", file=sys.stderr)
        return 1
    OUT.mkdir(exist_ok=True)
    for r in rows:
        rid = r.get("id")
        if not rid: continue
        (OUT / f"{safe_slug(rid)}.html").write_text(render_one(r), encoding="utf-8")
    (OUT / "index.html").write_text(render_index(rows), encoding="utf-8")
    print(f"[render_entries] wrote {len(rows)} entry pages + index.html to {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
