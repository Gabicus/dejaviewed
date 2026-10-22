#!/usr/bin/env python3
"""Generate site/feed.xml — RSS 2.0 with Atom self-link and dc:/content: fields.

Items: the 50 newest entries (by post date) plus the 25 newest guides and deeper
dives. Guide/deeper dates come from the file's first git commit (falls back to
file mtime), not raw mtime: generators rewrite every page on each rebuild, so
mtime would re-date every item daily and make readers re-show old items.

Idempotent: lastBuildDate is the catalog's generated date, and the file is only
written when it changes.

Usage: python3 scripts/build_feed.py
"""
from __future__ import annotations

import html
import re
import sys
from datetime import date, datetime, time, timezone
from email.utils import format_datetime
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_seo import (BASE, FEED_TITLE, SITE, Ctx, canonical_url, clip, file_dates,  # noqa: E402
                       parse_date, safe_slug, sr_first_paragraph, strip_title_suffix, write_if_changed)

OUT = SITE / "feed.xml"
N_ENTRIES, N_GUIDES = 50, 25


def rfc822(d: date) -> str:
    return format_datetime(datetime.combine(d, time(12, 0), tzinfo=timezone.utc))


def page_title(p: Path) -> str:
    m = re.search(r"<title>(.*?)</title>", p.read_text(errors="replace"), re.S)
    return strip_title_suffix(html.unescape(m.group(1))) if m else p.stem


def main() -> int:
    c = Ctx()
    items = []
    dated = []
    for e in c.entries:
        dt = parse_date(e.get("date"))
        if dt and e.get("id") and (SITE / "e" / f"{safe_slug(e['id'])}.html").exists():
            dated.append((dt, e))
    dated.sort(key=lambda x: (x[0], x[1]["id"]), reverse=True)
    for dt, e in dated[:N_ENTRIES]:
        url = canonical_url(f"e/{safe_slug(e['id'])}.html")
        items.append(dict(date=dt, title=e.get("title") or e["id"], url=url,
                          desc=clip(e.get("summary") or "", 400),
                          cats=[e.get("collection") or "", e.get("type") or "", f"tier {e.get('tier', '')}"],
                          creator=e.get("creator") or ""))

    pages = []
    for g in c.guides:
        p = SITE / "guides" / f"{g}.html"
        pub, _ = file_dates(p)
        desc = (c.manual.get(g) or {}).get("thesis") or sr_first_paragraph(p.read_text(errors="replace"))
        pages.append(dict(date=pub, title=page_title(p), url=canonical_url(f"guides/{g}.html"),
                          desc=clip(desc, 400), cats=["guide"], creator="DejaViewed"))
    for stem in c.deepers:
        p = SITE / "deeper" / f"{stem}.html"
        pub, _ = file_dates(p)
        pages.append(dict(date=pub, title=page_title(p), url=canonical_url(f"deeper/{stem}.html"),
                          desc=clip((c.deeper.get(stem) or {}).get("thesis") or "", 400),
                          cats=["deeper dive"], creator="DejaViewed"))
    pages.sort(key=lambda x: (x["date"], x["url"]), reverse=True)
    items += pages[:N_GUIDES]
    items.sort(key=lambda x: (x["date"], x["url"]), reverse=True)

    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:dc="http://purl.org/dc/elements/1.1/">',
           '<channel>',
           f'<title>{escape(FEED_TITLE)}</title>',
           f'<link>{BASE}/</link>',
           f'<atom:link href="{BASE}/feed.xml" rel="self" type="application/rss+xml"/>',
           f'<description>{escape(f"Newest saved posts, guides and deeper dives from DejaViewed ({c.n_entries} entries in total).")}</description>',
           '<language>en</language>',
           f'<lastBuildDate>{rfc822(c.generated)}</lastBuildDate>',
           f'<image><url>{BASE}/og/{"default.jpg" if (SITE / "og" / "default.jpg").exists() else "default.png"}</url>'
           f'<title>{escape(FEED_TITLE)}</title><link>{BASE}/</link></image>']
    for it in items:
        out.append('<item>')
        out.append(f'<title>{escape(it["title"])}</title>')
        out.append(f'<link>{escape(it["url"])}</link>')
        out.append(f'<guid isPermaLink="true">{escape(it["url"])}</guid>')
        out.append(f'<pubDate>{rfc822(it["date"])}</pubDate>')
        if it["creator"]:
            out.append(f'<dc:creator>{escape(it["creator"])}</dc:creator>')
        for cat in it["cats"]:
            if cat.strip():
                out.append(f'<category>{escape(cat)}</category>')
        out.append(f'<description>{escape(it["desc"])}</description>')
        out.append('</item>')
    out += ['</channel>', '</rss>', '']
    changed = write_if_changed(OUT, "\n".join(out))
    print(f"feed: {'written' if changed else 'unchanged'} · {len(items)} items "
          f"({min(N_ENTRIES, len(dated))} entries + {min(N_GUIDES, len(pages))} guides/deeper)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
