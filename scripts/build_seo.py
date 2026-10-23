#!/usr/bin/env python3
"""SEO / answer-engine layer for the static site. Idempotent post-processor.

Run AFTER every page generator (guides, deeper, entries, start-here, og, feed).
For each public HTML page it injects (or replaces) one block in <head>:

    <!-- seo:start --> canonical, description, Open Graph, Twitter card,
                       RSS alternate, one JSON-LD @graph <!-- seo:end -->

and removes duplicate description / og: / twitter: / canonical / ld+json tags
that live outside the block. Pages listed in data/seo/queries.json get their
<title> rewritten when it lacks the query's key noun (log: data/seo/title_changes.json).

Run twice -> byte-identical output (files are only written when they change).

Usage:
  python3 scripts/build_seo.py           # process + coverage table
  python3 scripts/build_seo.py --check   # dry run: report what would change, exit 1 if anything would
"""
from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
DATA = ROOT / "data"
BASE = "https://dejaviewed.dev"
SITE_NAME = "DejaViewed"
REPO_URL = "https://github.com/Gabicus/dejaviewed"
AUTHOR_URL = "https://instagram.com/6ab3"
FEED_TITLE = "DejaViewed: new entries, guides and deeper dives"

START, END = "<!-- seo:start -->", "<!-- seo:end -->"
BLOCK_RE = re.compile(r"<!-- seo:start -->.*?<!-- seo:end -->\n?", re.S)

# top-level pages processed (everything else at site root is skipped:
# admin, rate, board, graph*, legacy/, pagefind/, about/, links/, ai_presentation/)
TOP_PAGES = ["index.html", "catalog.html", "prompts.html", "search.html", "start-here.html"]
SUB_DIRS = ["guides", "deeper", "e"]

# private / superseded pages: get a seo block holding only robots noindex,follow
# (plus every page Disallowed in site/robots.txt). Never part of the public set.
NOINDEX_PAGES = ["admin.html", "rate.html", "404.html"]
NOINDEX_DIRS = ["legacy"]

OG_W, OG_H = 1200, 630


# ─────────────────────────── shared helpers (imported by sibling scripts) ──
def strip_block(text: str) -> str:
    return BLOCK_RE.sub("", text)


def write_if_changed(path: Path, text: str, ignore_seo_block: bool = False) -> bool:
    """Write only when content differs. With ignore_seo_block, an existing file
    that equals `text` once its seo block is removed counts as unchanged."""
    if path.exists():
        old = path.read_text(encoding="utf-8", errors="replace")
        if old == text:
            return False
        if ignore_seo_block and strip_block(old) == strip_block(text):
            return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def parse_date(s) -> date | None:
    s = (s or "").strip()
    if not s:
        return None
    try:
        return date.fromisoformat(s[:10])
    except ValueError:
        pass
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def safe_slug(rid: str) -> str:
    """Must match render_entries.safe_slug (entry page filename)."""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in rid)


def canonical_url(rel: str) -> str:
    """site-relative path -> clean absolute URL (Cloudflare Pages clean URLs)."""
    rel = rel.replace("\\", "/")
    if rel == "index.html":
        return BASE + "/"
    if rel.endswith("/index.html"):
        return BASE + "/" + quote(rel[: -len("index.html")])
    if rel.endswith(".html"):
        rel = rel[:-5]
    return BASE + "/" + quote(rel)


_GIT_CACHE: dict | None = None


def git_dates() -> dict[str, tuple[date, date]]:
    """{'site/guides/x.html': (first_commit_date, last_commit_date)} — one git call."""
    global _GIT_CACHE
    if _GIT_CACHE is not None:
        return _GIT_CACHE
    out: dict[str, list[date]] = {}
    try:
        log = subprocess.run(
            ["git", "-C", str(ROOT), "log", "--format=%x00%cs", "--name-only", "--", "site/"],
            capture_output=True, text=True, check=True).stdout
    except Exception:
        _GIT_CACHE = {}
        return _GIT_CACHE
    cur = None
    for line in log.splitlines():
        if line.startswith("\x00"):
            cur = parse_date(line[1:])
            continue
        line = line.strip()
        if not line or cur is None:
            continue
        d = out.setdefault(line, [cur, cur])  # newest first in log order
        d[0] = cur                            # keeps moving back -> first add
    _GIT_CACHE = {k: (v[0], v[1]) for k, v in out.items()}
    return _GIT_CACHE


def file_dates(path: Path) -> tuple[date, date]:
    """(published, modified) for a site file: git first/last commit, else file mtime."""
    rel = str(path.relative_to(ROOT))
    g = git_dates().get(rel)
    if g:
        return g
    m = date.fromtimestamp(path.stat().st_mtime) if path.exists() else date.today()
    return m, m


def clean_text(s: str) -> str:
    s = html.unescape(s or "")
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)    # md links
    s = re.sub(r"[*_`#>]+", "", s)
    return re.sub(r"\s+", " ", s).strip()


def clip(s: str, n: int = 160) -> str:
    s = clean_text(s)
    if len(s) <= n:
        return s
    cut = s[: n - 1]
    if " " in cut:
        cut = cut[: cut.rfind(" ")]
    return cut.rstrip(" ,;:—–-·.") + "…"


def load_json(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return default


def og_image_rel(name: str) -> str | None:
    for ext in (".png", ".jpg"):
        if (SITE / "og" / f"{name}{ext}").is_file():
            return f"og/{name}{ext}"
    return None


def thumb_rel(e: dict) -> str:
    pid = e.get("post_id") or e.get("id") or ""
    if not pid:
        return ""
    rel = f"thumb/{pid.replace('/', '_')}.jpg"
    return rel if (SITE / rel).is_file() else ""


def strip_title_suffix(t: str) -> str:
    t = re.sub(r"\s*[·—|-]\s*DejaViewed\s*$", "", t.strip())
    return t.strip() or SITE_NAME


# ─────────────────────────────────────────────────────────── site context ──
class Ctx:
    def __init__(self):
        cat = load_json(SITE / "catalog.json", {}) or {}
        self.catalog = cat
        self.entries = cat.get("entries", [])
        self.by_slug = {safe_slug(e["id"]): e for e in self.entries if e.get("id")}
        self.manual = {d["id"].replace("dd-insight-", ""): d
                       for d in (load_json(DATA / "manual_dives.json", {}) or {}).get("manual_dives", [])}
        self.deep = {d["id"]: d for d in (load_json(DATA / "deep_dives.json", {}) or {}).get("deep_dives", [])}
        self.deeper = {d["slug"]: d for d in (load_json(DATA / "deeper_dives.json", {}) or {}).get("deeper_dives", [])}
        self.packs = load_json(DATA / "prompt_systems.json", {}) or {}
        self.weak_entries: list[str] = []
        self.queries = (load_json(DATA / "seo" / "queries.json", {}) or {}).get("queries", [])
        self.n_entries = len(self.entries)
        self.n_colls = len({e.get("collection") for e in self.entries} - {None, ""})
        self.n_creators = len({e.get("creator") for e in self.entries} - {None, ""})
        self.n_transcripts = sum(1 for e in self.entries if (e.get("transcript") or "").strip())
        self.guides = sorted(p.stem for p in (SITE / "guides").glob("*.html") if p.name != "index.html")
        self.deepers = sorted(p.stem for p in (SITE / "deeper").glob("*.html"))
        self.n_packs = len(self.packs)
        self.n_steps = sum(len(p.get("steps", [])) for p in self.packs.values())
        self.generated = parse_date(cat.get("generated")) or date.today()
        tools = Counter(t for e in self.entries for t in (e.get("tools") or []))
        self.top_tools = [t for t, _ in tools.most_common(15)]
        ds = sorted(d for d in (parse_date(e.get("date")) for e in self.entries) if d)
        self.date_span = (ds[0], ds[-1]) if ds else (None, None)

    def guide_entries(self, slug: str) -> list[dict]:
        ids = set((self.manual.get(slug) or {}).get("entry_ids") or [])
        out = [e for e in self.entries
               if e.get("id") in ids or e.get("deep_dive_slug") == slug or e.get("deep_dive") == slug]
        return out

    def guide_tools(self, slug: str, k: int = 10) -> list[str]:
        c = Counter(t for e in self.guide_entries(slug) for t in (e.get("tools") or []))
        return [t for t, _ in c.most_common(k)]


ORG = {"@type": "Organization", "@id": BASE + "/#org", "name": SITE_NAME, "url": BASE + "/",
       "sameAs": [REPO_URL, AUTHOR_URL]}
WEBSITE_REF = {"@id": BASE + "/#website"}


def top_descriptions(c: Ctx) -> dict[str, str]:
    return {
        "index.html": (f"A curated archive of {c.n_entries} saved posts on AI tools, agents, creative code and quant, "
                       f"transcribed and tiered, with {len(c.guides)} guides and {c.n_packs} prompt systems."),
        "catalog.html": (f"Filter {c.n_entries} curated posts by tier, tool, technique, creator and collection. "
                         f"{c.n_transcripts} have transcripts; JSON at /api/catalog.json."),
        "prompts.html": (f"{c.n_packs} pasteable prompt systems, one per DejaViewed guide: a one-shot prompt, "
                         f"{c.n_steps} step prompts with audits, gap audits and validation oracles."),
        "search.html": (f"Full-text search across {c.n_entries} DejaViewed entries, transcript excerpts, "
                        f"{len(c.guides)} guides and {len(c.deepers)} deeper dives. Static, runs in your browser."),
        "start-here.html": (f"What DejaViewed is, who it is for, how humans and agents use it, how to cite it, "
                            f"and what is inside its {c.n_entries} entries and {c.n_colls} collections."),
        "guides/index.html": (f"{len(c.guides)} DejaViewed guides that connect saved posts into one build plan, "
                              f"each with sources, a thesis and a step-by-step prompt system."),
        "e/index.html": (f"Every DejaViewed entry on one page: {c.n_entries} saved posts with creator, tier, "
                         f"collection and a summary, each linking to its own detail page."),
    }


def sr_first_paragraph(text: str) -> str:
    """First paragraph after the first <h2> in the hidden pagefind block (hand-written guides)."""
    m = re.search(r'class="sr-index".*?</div>', text, re.S)
    blob = m.group(0) if m else text
    h = blob.find("<h2")
    if h < 0:
        return ""
    for p in re.findall(r"<p>(.*?)</p>", blob[h:], re.S):
        t = clean_text(p)
        if len(t) >= 60 and not re.match(r"^(GitHub|Creator|Insight class|Stars|Source)\b", t):
            return t
    return ""


WORD = re.compile(r"[a-z0-9][a-z0-9.\-]{3,}")
STOP = set("that this with from your have does what when which into than then they them were will would "
           "should could about after before every each more most just only also over under while there "
           "their still being doing done make made used using real".split())


def _words(s: str) -> set[str]:
    return {w for w in WORD.findall(s.lower()) if w not in STOP}


FAQ_MIN_SCORE = 5.5


def faq_pairs(pack: dict, k: int = 6) -> list[tuple[str, str]]:
    """Pair each self-question with the best-matching validation oracle, failure mode or step
    (IDF-weighted word overlap, each answer used once). Below FAQ_MIN_SCORE the
    question is dropped (FAQ answers must actually answer)."""
    import math
    qs = [q for q in (pack.get("self_questions") or []) if isinstance(q, str)][:k]
    oracles = [clean_text(o) for o in (pack.get("validation_oracles") or []) if isinstance(o, str)]
    cands: list[tuple[str, str]] = [(o, o) for o in oracles]          # (match text, answer text)
    cands += [(clean_text(f), clean_text(f)) for f in (pack.get("failure_modes") or []) if isinstance(f, str)]
    for st in pack.get("steps") or []:
        ans = f"Step {st.get('n')}, {st.get('title', '')}: {st.get('goal', '')} Expect: {st.get('expect', '')}"
        cands.append((clean_text(" ".join(str(st.get(x, "")) for x in ("title", "goal", "expect", "audit"))),
                      clip(ans, 400)))
    cw = [_words(m) for m, _ in cands]
    df = Counter(w for ws in cw for w in ws)
    idf = {w: math.log((1 + len(cands)) / (1 + n)) + 1 for w, n in df.items()}
    used: set[int] = set()
    out = []
    for i, q in enumerate(qs):
        qw = _words(q)
        best, score = None, 0.0
        for j, ws in enumerate(cw):
            if j in used:
                continue
            sc = sum(idf[w] for w in qw & ws)
            if sc > score:
                best, score = j, sc
        if best is None or score < FAQ_MIN_SCORE:
            continue   # no candidate answers this question: leave it out rather than mis-pair
        used.add(best)
        out.append((clean_text(q), cands[best][1]))
    return out


def breadcrumbs(items: list[tuple[str, str | None]]) -> dict:
    el = []
    for i, (name, url) in enumerate(items, 1):
        li = {"@type": "ListItem", "position": i, "name": name}
        if url:
            li["item"] = url
        el.append(li)
    return {"@type": "BreadcrumbList", "itemListElement": el}


def dataset_node(c: Ctx) -> dict:
    a, b = c.date_span
    node = {
        "@type": "Dataset", "@id": BASE + "/#dataset",
        "name": "DejaViewed catalog",
        "description": (f"{c.n_entries} saved social-media posts about AI tools, agents, creative coding, art "
                        f"reference and quant trading, collected in {c.n_colls} collections from {c.n_creators} "
                        f"creators. Each entry has a title, summary, creator, tier (S/A/B/C), tools, techniques "
                        f"and domains; {c.n_transcripts} include a speech transcript. Original posts remain "
                        f"the property of their creators; entries link to the source."),
        "url": BASE + "/catalog",
        "creator": {"@id": ORG["@id"]},
        "publisher": {"@id": ORG["@id"]},
        "license": "https://opensource.org/licenses/MIT",
        "isAccessibleForFree": True,
        "dateModified": c.generated.isoformat(),
        "keywords": c.top_tools,
        "distribution": [
            {"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": BASE + "/api/catalog.json",
             "name": "Catalog (all entries)"},
            {"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": BASE + "/api/prompts.json",
             "name": "Prompt systems"},
            {"@type": "DataDownload", "encodingFormat": "text/plain", "contentUrl": BASE + "/llms-full.txt",
             "name": "Full plain-text dump for LLMs"},
        ],
    }
    if a and b:
        node["temporalCoverage"] = f"{a.isoformat()}/{b.isoformat()}"
    return node


def item_list(urls_names: list[tuple[str, str]]) -> dict:
    return {"@type": "ItemList", "numberOfItems": len(urls_names),
            "itemListElement": [{"@type": "ListItem", "position": i, "url": u, "name": n}
                                for i, (u, n) in enumerate(urls_names, 1)]}


# ─────────────────────────────────────────────────────────── per page ──
def page_meta(rel: str, text: str, c: Ctx, title: str) -> dict:
    """-> {desc, og_type, image_rel, image_is_og, graph:[...]}"""
    url = canonical_url(rel)
    ttl = strip_title_suffix(title)
    tops = top_descriptions(c)
    graph: list[dict] = [ORG]
    og_type = "website"
    image = og_image_rel("default")
    desc = ""
    parts = rel.split("/")

    if rel in tops:
        desc = tops[rel]
        name = {"index.html": "default", "catalog.html": "catalog", "prompts.html": "prompts",
                "start-here.html": "start-here"}.get(rel)
        image = (og_image_rel(name) if name else None) or image
        if rel == "index.html":
            graph.append({"@type": "WebSite", "@id": WEBSITE_REF["@id"], "url": BASE + "/", "name": SITE_NAME,
                          "description": desc, "publisher": {"@id": ORG["@id"]},
                          "potentialAction": {"@type": "SearchAction",
                                              "target": {"@type": "EntryPoint",
                                                         "urlTemplate": BASE + "/search?q={search_term_string}"},
                                              "query-input": "required name=search_term_string"}})
            graph.append(dataset_node(c))
        elif rel == "catalog.html":
            graph.append({"@type": "CollectionPage", "@id": url + "#page", "url": url, "name": ttl,
                          "description": desc, "isPartOf": WEBSITE_REF, "mainEntity": {"@id": BASE + "/#dataset"}})
            graph.append(dataset_node(c))
        elif rel == "prompts.html":
            lst = [(canonical_url(f"guides/{g}.html") + "#prompt-system", g) for g in c.guides if g in c.packs]
            graph.append({"@type": "CollectionPage", "@id": url + "#page", "url": url, "name": ttl,
                          "description": desc, "isPartOf": WEBSITE_REF, "mainEntity": item_list(lst)})
        elif rel == "guides/index.html":
            lst = []
            for g in c.guides:
                gt = re.search(r"<title>(.*?)</title>", (SITE / "guides" / f"{g}.html").read_text(errors="replace"), re.S)
                lst.append((canonical_url(f"guides/{g}.html"), strip_title_suffix(html.unescape(gt.group(1))) if gt else g))
            graph.append({"@type": "CollectionPage", "@id": url + "#page", "url": url, "name": ttl,
                          "description": desc, "isPartOf": WEBSITE_REF, "mainEntity": item_list(lst)})
            graph.append(breadcrumbs([("Home", BASE + "/"), ("Guides", None)]))
        elif rel == "e/index.html":
            graph.append({"@type": "CollectionPage", "@id": url + "#page", "url": url, "name": ttl,
                          "description": desc, "isPartOf": WEBSITE_REF,
                          "mainEntity": {"@type": "ItemList", "numberOfItems": c.n_entries}})
            graph.append(breadcrumbs([("Home", BASE + "/"), ("All entries", None)]))
        else:  # search, start-here
            graph.append({"@type": "WebPage", "@id": url + "#page", "url": url, "name": ttl,
                          "description": desc, "isPartOf": WEBSITE_REF})

    elif parts[0] == "guides":
        slug = Path(rel).stem
        og_type = "article"
        md = c.manual.get(slug) or {}
        pack = c.packs.get(slug) or {}
        desc = md.get("thesis") or sr_first_paragraph(text) or pack.get("mission", "")
        desc = clip(desc)
        if desc and len(desc) < 110 and pack.get("steps"):
            desc = clip(f"{desc} Includes a {len(pack['steps'])}-step prompt system.")
        image = og_image_rel(slug) or image
        pub, mod = file_dates(SITE / rel)
        upd = parse_date(pack.get("updated_at"))
        if upd and upd > mod:
            mod = upd
        art = {"@type": "Article", "@id": url + "#article", "headline": ttl[:110], "description": desc,
               "url": url, "mainEntityOfPage": url, "datePublished": pub.isoformat(),
               "dateModified": max(pub, mod).isoformat(),
               "author": {"@type": "Organization", "name": SITE_NAME, "url": BASE + "/"},
               "publisher": {"@id": ORG["@id"]}, "isPartOf": WEBSITE_REF,
               "image": BASE + "/" + (image or "og/default.png"),
               "about": [{"@type": "Thing", "name": t} for t in c.guide_tools(slug)]}
        ans = re.search(r"(?m)^> \*\*In short:\*\* (.+)$", text)
        if ans:   # the "In two sentences" answer block build_guides.py puts at the top of every guide
            art["abstract"] = html.unescape(ans.group(1)).strip()
        graph.append(art)
        faqs = faq_pairs(pack)
        if faqs:
            graph.append({"@type": "FAQPage", "@id": url + "#faq",
                          "mainEntity": [{"@type": "Question", "name": q,
                                          "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faqs]})
        graph.append(breadcrumbs([("Home", BASE + "/"), ("Guides", BASE + "/guides/"), (ttl, None)]))

    elif parts[0] == "deeper":
        stem = Path(rel).stem
        slug = stem.replace("deeper-insight-", "", 1)
        og_type = "article"
        dd = c.deeper.get(stem) or {}
        desc = clip(dd.get("thesis") or (c.manual.get(slug) or {}).get("thesis") or "")
        image = og_image_rel(stem) or image
        pub, mod = file_dates(SITE / rel)
        gen = parse_date(dd.get("generated_at"))
        if gen and gen > mod:
            mod = gen
        tools = (dd.get("tools") or [])[:10]
        graph.append({"@type": "Article", "@id": url + "#article", "headline": ttl[:110], "description": desc,
                      "url": url, "mainEntityOfPage": url, "datePublished": pub.isoformat(),
                      "dateModified": max(pub, mod).isoformat(),
                      "author": {"@type": "Organization", "name": SITE_NAME, "url": BASE + "/"},
                      "publisher": {"@id": ORG["@id"]}, "isPartOf": WEBSITE_REF,
                      "image": BASE + "/" + (image or "og/default.png"),
                      "about": [{"@type": "Thing", "name": t} for t in tools]})
        crumbs = [("Home", BASE + "/"), ("Guides", BASE + "/guides/")]
        if (SITE / "guides" / f"{slug}.html").exists():
            gt = re.search(r"<title>(.*?)</title>", (SITE / "guides" / f"{slug}.html").read_text(errors="replace"), re.S)
            crumbs.append((strip_title_suffix(html.unescape(gt.group(1))) if gt else slug,
                           canonical_url(f"guides/{slug}.html")))
        crumbs.append(("Deeper dive", None))
        graph.append(breadcrumbs(crumbs))

    elif parts[0] == "e":
        og_type = "article"
        e = c.by_slug.get(Path(rel).stem) or {}
        desc = clip(e.get("summary") or "")
        if e and len(desc) < 70:   # stub summary ("title — @creator"): pad with transcript/caption
            c.weak_entries.append(rel)
            extra = ""
            for src in (e.get("transcript"), e.get("caption")):
                t = clean_text(src or "")
                if not t.startswith("(") and len(re.findall(r"[A-Za-z]{3,}", t)) >= 8:
                    extra = t
                    break
            if not extra:   # nothing usable: state the catalog facts instead
                bits = [f"{e.get('type') or 'saved'} post in the {e.get('collection')} collection, tier {e.get('tier')}"]
                tools = (e.get("tools") or [])[:3]
                if tools:
                    bits.append("tools: " + ", ".join(tools))
                extra = "Saved " + "; ".join(bits) + "."
            base = desc or clean_text(e.get("title") or "")
            desc = clip(f"{base.rstrip('. ')}. {extra}")
        th = thumb_rel(e) if e else ""
        image = th or image
        # mirrors the visible breadcrumb render_entries writes (Home › Catalog › <collection> › title);
        # the collection has no URL of its own, so it is left out of the structured list
        graph.append(breadcrumbs([("Home", BASE + "/"), ("Catalog", canonical_url("catalog.html")), (ttl, None)]))

    return {"desc": desc, "og_type": og_type, "image": image or "og/default.png",
            "image_is_og": bool(image and image.startswith("og/")), "graph": graph, "url": url, "og_title": ttl}


def build_block(m: dict) -> str:
    a = lambda s: html.escape(s or "", quote=True)
    img = BASE + "/" + m["image"]
    lines = [START,
             f'<link rel="canonical" href="{a(m["url"])}">',
             f'<meta name="description" content="{a(m["desc"])}">',
             f'<meta property="og:site_name" content="{SITE_NAME}">',
             f'<meta property="og:type" content="{m["og_type"]}">',
             f'<meta property="og:title" content="{a(m["og_title"])}">',
             f'<meta property="og:description" content="{a(m["desc"])}">',
             f'<meta property="og:url" content="{a(m["url"])}">',
             f'<meta property="og:image" content="{a(img)}">']
    if m["image_is_og"]:
        lines += [f'<meta property="og:image:width" content="{OG_W}">',
                  f'<meta property="og:image:height" content="{OG_H}">']
    lines += ['<meta name="twitter:card" content="summary_large_image">',
              f'<meta name="twitter:title" content="{a(m["og_title"])}">',
              f'<meta name="twitter:description" content="{a(m["desc"])}">',
              f'<meta name="twitter:image" content="{a(img)}">',
              f'<link rel="alternate" type="application/rss+xml" title="{a(FEED_TITLE)}" href="{BASE}/feed.xml">']
    ld = json.dumps({"@context": "https://schema.org", "@graph": m["graph"]}, ensure_ascii=False,
                    separators=(",", ":")).replace("</", "<\\/")
    lines.append(f'<script type="application/ld+json">{ld}</script>')
    lines.append(END)
    return "\n".join(lines) + "\n"


STRAY = [
    r"<meta\b[^>]*\bname=[\"']description[\"'][^>]*>",
    r"<meta\b[^>]*\bproperty=[\"']og:[^\"']*[\"'][^>]*>",
    r"<meta\b[^>]*\bname=[\"']twitter:[^\"']*[\"'][^>]*>",
    r"<link\b[^>]*\brel=[\"']canonical[\"'][^>]*>",
    r"<link\b[^>]*\btype=[\"']application/rss\+xml[\"'][^>]*>",
    r"<script\b[^>]*\btype=[\"']application/ld\+json[\"'][^>]*>.*?</script>",
]


def remove_strays(head: str) -> str:
    for pat in STRAY:
        head = re.sub(r"(?m)^[ \t]*" + pat + r"[ \t]*\n", "", head, flags=re.S | re.I)
        head = re.sub(pat, "", head, flags=re.S | re.I)
    return head


def norm(s: str) -> str:
    return re.sub(r"[\s\-_]+", " ", html.unescape(s).lower()).strip()


def process(rel: str, c: Ctx, qmap: dict, title_log: dict) -> tuple[str, str, dict]:
    path = SITE / rel
    orig = path.read_text(encoding="utf-8", errors="replace")
    text = strip_block(orig)
    hi = text.lower().find("</head>")
    if hi < 0:
        return orig, orig, {}
    head, rest = text[:hi], text[hi:]
    head = remove_strays(head)

    tm = re.search(r"<title>(.*?)</title>", head, re.S | re.I)
    title = html.unescape(tm.group(1).strip()) if tm else SITE_NAME
    q = qmap.get(rel)
    if q and tm and norm(q["key_noun"]) not in norm(title):
        new_title = q["title"].strip() + " · " + SITE_NAME
        title_log[rel] = {"query": q["query"], "key_noun": q["key_noun"], "old": title, "new": new_title}
        head = head[: tm.start()] + f"<title>{html.escape(new_title, quote=False)}</title>" + head[tm.end():]
        title = new_title
        tm = re.search(r"<title>(.*?)</title>", head, re.S | re.I)

    meta = page_meta(rel, text, c, title)
    block = build_block(meta)
    if tm:
        pos = tm.end()
        if head[pos:pos + 1] == "\n":
            pos += 1
    else:  # after <meta charset> or at head start
        mc = re.search(r"<head[^>]*>\n?", head, re.I)
        pos = mc.end() if mc else 0
    head = head[:pos] + block + head[pos:]
    return orig, head + rest, meta


def noindex_pages() -> list[str]:
    rels = {p for p in NOINDEX_PAGES if (SITE / p).is_file()}
    for d in NOINDEX_DIRS:
        rels |= {str(p.relative_to(SITE)) for p in (SITE / d).glob("*.html")}
    robots = SITE / "robots.txt"
    if robots.exists():
        for line in robots.read_text(encoding="utf-8").splitlines():
            m = re.match(r"\s*Disallow:\s*/(\S+)", line, re.I)
            if not m:
                continue
            path = m.group(1).rstrip("$")
            for cand in (path, path + ".html", path.rstrip("/") + "/index.html"):
                if cand and (SITE / cand).is_file() and cand.endswith(".html"):
                    rels.add(cand)
                    break
    return sorted(rels)


def process_noindex(rel: str) -> tuple[str, str]:
    """Block = robots noindex,follow only; drop robots metas outside the block."""
    path = SITE / rel
    orig = path.read_bytes().decode("utf-8", errors="replace")   # keep CRLF files CRLF
    nl = "\r\n" if "\r\n" in orig else "\n"
    text = re.sub(r"<!-- seo:start -->.*?<!-- seo:end -->(\r?\n)?", "", orig, flags=re.S)
    hi = text.lower().find("</head>")
    if hi < 0:
        return orig, orig
    head, rest = re.sub(r"[ \t]*<meta\b[^>]*\bname=[\"']robots[\"'][^>]*>[ \t]*(\r?\n)?", "", text[:hi], flags=re.I), text[hi:]
    block = START + nl + '<meta name="robots" content="noindex,follow">' + nl + END + nl
    tm = re.search(r"<title>.*?</title>(\r?\n)?", head, re.S | re.I) or re.search(r"<head[^>]*>(\r?\n)?", head, re.I)
    pos = tm.end() if tm else 0
    return orig, head[:pos] + block + head[pos:] + rest


def collect_pages() -> list[str]:
    rels = [p for p in TOP_PAGES if (SITE / p).is_file()]
    for d in SUB_DIRS:
        rels += sorted(str(p.relative_to(SITE)) for p in (SITE / d).glob("*.html"))
    return rels


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="dry run; exit 1 if any page would change")
    args = ap.parse_args()

    c = Ctx()
    qmap = {q["page"]: q for q in c.queries}
    log_path = DATA / "seo" / "title_changes.json"
    title_log: dict = {}
    stats = defaultdict(lambda: Counter())
    missing, would_change = [], []
    for rel in collect_pages():
        orig, new, meta = process(rel, c, qmap, title_log)
        d = rel.split("/")[0] if "/" in rel else "(root)"
        stats[d]["pages"] += 1
        if not meta:
            stats[d]["no-head"] += 1
            continue
        if meta["desc"]:
            stats[d]["described"] += 1
        else:
            missing.append(rel)
        if meta["image_is_og"]:
            stats[d]["og-image"] += 1
        elif meta["image"].startswith("thumb/"):
            stats[d]["thumb-image"] += 1
        else:
            stats[d]["default-image"] += 1
        if new != orig:
            stats[d]["changed"] += 1
            would_change.append(rel)
            if not args.check:
                path = SITE / rel
                path.write_text(new, encoding="utf-8")

    private = noindex_pages()
    public = set(collect_pages())
    for rel in private:
        if rel in public:
            print(f"warning: {rel} is both public and noindex; leaving it public", file=sys.stderr)
            continue
        orig, new = process_noindex(rel)
        stats["(noindex)"]["pages"] += 1
        if new != orig:
            stats["(noindex)"]["changed"] += 1
            would_change.append(rel)
            if not args.check:
                (SITE / rel).write_bytes(new.encode("utf-8"))

    if title_log and not args.check:
        prev = load_json(log_path, {}) or {}
        prev.update(title_log)
        write_if_changed(log_path, json.dumps(prev, ensure_ascii=False, indent=2, sort_keys=True) + "\n")

    cols = ["pages", "changed", "described", "og-image", "thumb-image", "default-image"]
    print(f"{'dir':10} " + " ".join(f"{h:>13}" for h in cols))
    tot = Counter()
    for d in sorted(stats):
        tot.update(stats[d])
        print(f"{d:10} " + " ".join(f"{stats[d][h]:>13}" for h in cols))
    print(f"{'TOTAL':10} " + " ".join(f"{tot[h]:>13}" for h in cols))
    print(f"missing description: {len(missing)}" + (f" -> {missing[:20]}" if missing else ""))
    print(f"entries with a stub summary (description padded from transcript/caption): {len(c.weak_entries)}"
          + (f" -> {[Path(r).stem for r in c.weak_entries]}" if c.weak_entries else ""))
    if title_log:
        print(f"titles rewritten this run: {len(title_log)}")
        for rel, t in sorted(title_log.items()):
            print(f"  {rel}: {t['old']!r} -> {t['new']!r}")
    if args.check:
        print(f"[check] {len(would_change)} page(s) would change")
        return 1 if would_change else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
