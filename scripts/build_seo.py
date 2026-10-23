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
OWNER_NAME = "Victor"
OWNER_URL = "https://www.1gabe.com/"
OWNER_GITHUB = "https://github.com/Gabicus"
CONTACT_URL = "https://www.1gabe.com/contact/"
FEED_TITLE = "DejaViewed: new entries, guides and deeper dives"

START, END = "<!-- seo:start -->", "<!-- seo:end -->"
BLOCK_RE = re.compile(r"<!-- seo:start -->.*?<!-- seo:end -->\n?", re.S)

# top-level pages processed (everything else at site root is skipped:
# admin, rate, board, graph*, legacy/, pagefind/, about/, links/, ai_presentation/)
TOP_PAGES = ["index.html", "catalog.html", "prompts.html", "start-here.html", "method.html", "system-prompts.html",
             "flow.html"]
SUB_DIRS = ["guides", "deeper", "e", "tools", "compare", "best"]  # collections/ writes its own seo block (build_collections.py)

# private / superseded pages: get a seo block holding only robots noindex,follow
# (plus every page Disallowed in site/robots.txt). Never part of the public set.
NOINDEX_PAGES = ["admin.html", "rate.html", "404.html", "search.html"]  # search: empty without a query
NOINDEX_DIRS = ["legacy"]

OG_W, OG_H = 1200, 630
TITLE_MAX = 65                      # <title> budget (Google cuts at ~580-600 px)
TITLE_SUFFIX = " · " + SITE_NAME
HASHES_PATH = DATA / "seo" / "content_hashes.json"


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
    s = re.sub(r"\s+", " ", s).strip()
    return re.sub(r"\s+([,.;:!?])", r"\1", s)      # "in parallel , each" -> "in parallel, each"


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


# ─────────────────────────────────────── content freshness (SEO-07) ──
# Sitemap <lastmod> and Article dateModified come from data/seo/content_hashes.json:
#   {canonical url: {hash, first_seen, last_changed}}
# hash = the page's main content: entry pages -> their catalog record (ENTRY_FIELDS); guides -> the
# markdown source; other pages -> visible text with generated chrome removed (seo / monetize /
# sitenav blocks, all of <head>, <script>/<style>/<nav>/<footer>, date stamps, markup).
# A rebuild that only re-stamps dates, rewrites hrefs or restyles templates leaves the hash alone.
# New urls are seeded from git history (entries: site/catalog.json history; pages: the file's own):
# first_seen = first commit containing it, last_changed = oldest committed version with today's hash.
GEN_BLOCK_RE = re.compile(r"<!-- (seo|monetize|monetize-prompts|sitenav|answer-meta):start -->.*?<!-- \1:end -->", re.S)
DATE_RE = re.compile(r"\b20\d\d-\d\d-\d\d(?:[T ][0-9:.]+(?:Z|[+-]\d\d:?\d\d)?)?\b|"
                     r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2}, 20\d\d\b")


def content_text(page: str) -> str:
    # <title> is left out on purpose: build_seo trims it, generators re-emit the long form, and
    # that round trip must not count as a content change
    s = GEN_BLOCK_RE.sub(" ", page)
    bi = s.lower().find("<body")
    s = s[bi:] if bi >= 0 else s
    s = re.sub(r"<(script|style|nav|footer|template|noscript)\b.*?</\1\s*>", " ", s, flags=re.S | re.I)
    s = re.sub(r"<!--.*?-->", " ", s, flags=re.S)
    s = re.sub(r"<[^>]+>", " ", s)
    s = html.unescape(s)
    s = DATE_RE.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


def content_hash(page: str) -> str:
    import hashlib
    return hashlib.sha1(content_text(page).encode("utf-8")).hexdigest()[:16]


HASH_V = 3   # bump when the hash definition changes: records are re-hashed without moving last_changed
ENTRY_FIELDS = ("title", "summary", "transcript", "caption", "tags", "tools", "techniques", "domains",
                "takeaways", "tier", "type")
MD_RE = re.compile(r'<script[^>]*id="md"[^>]*>(.*?)</script>', re.S)


def entry_hash(e: dict) -> str:
    """An entry page's main content is its catalog record (template/link churn does not count)."""
    import hashlib
    payload = json.dumps([e.get(k) or "" for k in ENTRY_FIELDS], ensure_ascii=False, sort_keys=True)
    return hashlib.sha1(DATE_RE.sub(" ", payload).encode("utf-8")).hexdigest()[:16]


def page_key_hash(rel: str, page: str) -> str:
    """Guides: the markdown source (the visible body is rendered from it); everything else: visible text."""
    if rel.startswith("guides/") and not rel.endswith("index.html"):
        m = MD_RE.search(page)
        if m:
            import hashlib
            md = DATE_RE.sub(" ", html.unescape(m.group(1)))
            return hashlib.sha1(re.sub(r"\s+", " ", md).strip().encode("utf-8")).hexdigest()[:16]
    return content_hash(page)


class Freshness:
    """first_seen / last_changed per canonical url, persisted in HASHES_PATH."""

    def __init__(self, today: date | None = None):
        self.today = (today or date.today()).isoformat()
        self.data: dict = load_json(HASHES_PATH, {}) or {}
        self.dirty = False
        self.seen: set[str] = set()          # urls observed this run
        self._hist: dict | None = None
        self._entries: dict | None = None    # slug -> current record hash
        self._cat_hist: list | None = None   # [(date, {slug: record hash})] newest first

    def _history(self) -> dict[str, list[tuple[str, str]]]:
        """{'site/x.html': [(commit, YYYY-MM-DD author date), ... newest first]} — one git call."""
        if self._hist is not None:
            return self._hist
        out: dict[str, list[tuple[str, str]]] = {}
        try:
            log = subprocess.run(["git", "-C", str(ROOT), "log", "--format=%x00%H %as", "--name-only",
                                  "--diff-filter=AMR", "--", "site/"],
                                 capture_output=True, text=True, check=True).stdout
        except Exception:
            log = ""
        cur = None
        for line in log.splitlines():
            if line.startswith("\x00"):
                cur = tuple(line[1:].split(" ", 1))
                continue
            line = line.strip()
            if line.endswith(".html") and cur:
                out.setdefault(line, []).append(cur)
        self._hist = out
        return out

    def _git_blobs(self, specs: list[str]) -> list[str | None]:
        """Contents of '<commit>:<path>' specs via one `git cat-file --batch` call."""
        proc = subprocess.run(["git", "-C", str(ROOT), "cat-file", "--batch"],
                              input="".join(s + "\n" for s in specs).encode(), capture_output=True, check=True)
        blobs, buf = [], proc.stdout
        while buf:
            nl = buf.index(b"\n")
            hdr = buf[:nl].split()
            if len(hdr) < 3 or hdr[1] != b"blob":
                blobs.append(None)
                buf = buf[nl + 1:]
                continue
            n = int(hdr[2])
            blobs.append(buf[nl + 1: nl + 1 + n].decode("utf-8", "replace"))
            buf = buf[nl + 1 + n + 1:]
        return blobs

    def entries(self) -> dict[str, str]:
        if self._entries is None:
            cat = load_json(SITE / "catalog.json", {}) or {}
            self._entries = {safe_slug(e["id"]): entry_hash(e) for e in cat.get("entries", []) if e.get("id")}
        return self._entries

    def key_hash(self, rel: str, page: str) -> str:
        if rel.startswith("e/") and not rel.endswith("index.html"):
            h = self.entries().get(Path(rel).stem)
            if h:
                return h
        return page_key_hash(rel, page)

    def _catalog_history(self) -> list:
        if self._cat_hist is not None:
            return self._cat_hist
        self._cat_hist = []
        try:
            log = subprocess.run(["git", "-C", str(ROOT), "log", "--format=%H %as", "--", "site/catalog.json"],
                                 capture_output=True, text=True, check=True).stdout.split("\n")
            commits = [tuple(x.split(" ", 1)) for x in log if x.strip()]
            for (c, d), blob in zip(commits, self._git_blobs([f"{c}:site/catalog.json" for c, _ in commits])):
                try:
                    es = json.loads(blob or "{}").get("entries", [])
                except Exception:
                    es = []
                self._cat_hist.append((d, {safe_slug(e["id"]): entry_hash(e) for e in es if e.get("id")}))
        except Exception:
            pass
        return self._cat_hist

    def _seed_entry(self, rel: str, h: str) -> dict:
        slug = Path(rel).stem
        hist = self._catalog_history()
        seen_in = [d for d, m in hist if slug in m]
        first = min(seen_in) if seen_in else self.today
        last = None
        for d, m in hist:                    # newest first
            if m.get(slug) != h:
                break
            last = d
        return {"hash": h, "first_seen": first, "last_changed": last or self.today, "v": HASH_V}

    def _seed(self, rel: str, h: str) -> dict:
        if rel.startswith("e/") and not rel.endswith("index.html") and Path(rel).stem in self.entries():
            return self._seed_entry(rel, h)
        path = "site/" + rel
        hist = self._history().get(path) or []
        if not hist:
            return {"hash": h, "first_seen": self.today, "last_changed": self.today, "v": HASH_V}
        first = hist[-1][1]
        last = None
        try:
            for (c, d), b in zip(hist, self._git_blobs([f"{c}:{path}" for c, _ in hist])):   # newest first
                if b is None or page_key_hash(rel, b) != h:
                    break
                last = d                             # oldest committed version with today's content
        except Exception:
            pass
        return {"hash": h, "first_seen": first, "last_changed": last or self.today, "v": HASH_V}

    def observe(self, rel: str, page: str) -> dict:
        url = canonical_url(rel)
        h = self.key_hash(rel, page)
        self.seen.add(url)
        rec = self.data.get(url)
        if rec is None:
            rec = self._seed(rel, h)
            self.data[url] = rec
            self.dirty = True
        elif rec.get("v") != HASH_V:          # hash definition changed: re-key, keep the dates
            rec.update(hash=h, v=HASH_V)
            self.dirty = True
        elif rec.get("hash") != h:
            rec.update(hash=h, last_changed=self.today)
            self.dirty = True
        return rec

    def observe_key(self, key: str, payload: str) -> dict:
        """Freshness for a non-page resource (e.g. the dataset): hash of the raw payload."""
        import hashlib
        h = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]
        rec = self.data.get(key)
        if rec is None:
            rec = {"hash": h, "first_seen": self.today, "last_changed": self.today}
            self.data[key] = rec
            self.dirty = True
        elif rec.get("hash") != h:
            rec.update(hash=h, last_changed=self.today)
            self.dirty = True
        return rec

    def dates(self, rel: str) -> tuple[date, date]:
        rec = self.data.get(canonical_url(rel)) or {}
        a = parse_date(rec.get("first_seen")) or date.today()
        b = parse_date(rec.get("last_changed")) or a
        return a, max(a, b)

    def save(self) -> bool:
        if not self.dirty:
            return False
        return write_if_changed(HASHES_PATH, json.dumps(self.data, ensure_ascii=False, indent=1, sort_keys=True) + "\n")


# ─────────────────────────────────────────────── title policy (SEO-10) ──
_TITLE_TAIL_STOP = {"and", "or", "with", "the", "a", "an", "for", "of", "to", "in", "on", "at", "by", "vs", "from", "&", "+"}


def fit_title(t: str, limit: int = TITLE_MAX) -> str:
    """<title> <= limit chars: subject first; ' · DejaViewed' only when it fits; long titles cut at a
    separator (' — ', ': ', ' | ') when that keeps >= 40 chars, else at a word boundary."""
    base = re.sub(r"\s+", " ", strip_title_suffix(t)).strip()
    if base == SITE_NAME:
        return base
    if len(base) + len(TITLE_SUFFIX) <= limit:
        return base + TITLE_SUFFIX
    if len(base) <= limit:
        return base
    cut = ""
    for sep in (" — ", " – ", ": ", " | ", " · ", " - "):
        i = base.rfind(sep, 0, limit + 1)
        while i >= 40:
            cand = base[:i].rstrip(" ,;:—–-·|")
            if len(cand) <= limit:
                cut = cand
                break
            i = base.rfind(sep, 0, i)
        if cut:
            break
    if not cut:
        words = base[: limit + 1].split(" ")
        if len(words) > 1:
            words = words[:-1]
        else:
            words = [base[:limit]]
        while len(words) > 3 and words[-1].lower().strip(",;:—–-·|(") in _TITLE_TAIL_STOP:
            words.pop()
        cut = " ".join(words).rstrip(" ,;:—–-·|(")
    cut = re.sub(r"\s*[(\[][^)\]]*$", "", cut).strip() or cut   # no dangling "(..."
    return cut + TITLE_SUFFIX if len(cut) + len(TITLE_SUFFIX) <= limit else cut


def clip_sentence(s: str, n: int = 155) -> str:
    """Whole sentences up to n chars; falls back to clip() when the first sentence is longer."""
    s = clean_text(s)
    if len(s) <= n:
        return s
    out = ""
    for m in re.finditer(r".+?[.!?](?=\s+[A-Z0-9\"“(]|\s*$)", s):
        cand = s[: m.end()].strip()
        if len(cand) > n:
            break
        out = cand
    return out if len(out) >= 60 else clip(s, n)


# ───────────────────────────────────────────── guide index (llms.txt) ──
ANSWER_RE = re.compile(r"(?m)^> \*\*In short:\*\* (.+)$")


def page_heading(text: str) -> str:
    """Full (untruncated) page heading: md '# ' line, else first <h1>, else <title>."""
    m = re.search(r'<script[^>]*id="md"[^>]*>(.*?)</script>', text, re.S)
    if m:
        h = re.search(r"(?m)^# (.+)$", m.group(1))
        if h:
            return clean_text(h.group(1))
    h = re.search(r"<h1\b[^>]*>(.*?)</h1>", text, re.S | re.I)
    if h and clean_text(h.group(1)):
        return clean_text(h.group(1))
    tm = re.search(r"<title>(.*?)</title>", text, re.S | re.I)
    return strip_title_suffix(html.unescape(tm.group(1))) if tm else ""


def guide_index() -> dict[str, list[dict]]:
    """{'guides': [{slug, title, url, answer}], 'deeper': [{slug, title, url}]} from the pages on disk."""
    out: dict[str, list[dict]] = {"guides": [], "deeper": []}
    for p in sorted((SITE / "guides").glob("*.html")):
        if p.name == "index.html":
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        a = ANSWER_RE.search(text)
        out["guides"].append({"slug": p.stem, "title": page_heading(text) or p.stem,
                              "url": canonical_url(f"guides/{p.name}"),
                              "answer": clean_text(html.unescape(a.group(1))) if a else ""})
    for p in sorted((SITE / "deeper").glob("*.html")):
        if p.name == "index.html":
            continue
        text = p.read_text(encoding="utf-8", errors="replace")
        out["deeper"].append({"slug": p.stem, "title": page_heading(text) or p.stem,
                              "url": canonical_url(f"deeper/{p.name}")})
    return out


# ─────────────────────────────────────────────────────────── site context ──
DATASET_KEY = "dataset:catalog"
VOLATILE = {"is_new", "transcript_at", "user_notes", "favorited", "thumb_path", "media_url"}


class Ctx:
    def __init__(self, fresh: "Freshness | None" = None):
        cat = load_json(SITE / "catalog.json", {}) or {}
        self.catalog = cat
        self.fresh = fresh
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

    def entry_title_overrides(self) -> dict[str, str]:
        """slug -> disambiguated <title> for entries whose fitted titles collide (same caption twice)."""
        if hasattr(self, "_eto"):
            return self._eto
        groups: dict[str, list[dict]] = defaultdict(list)
        for e in self.entries:
            if e.get("id"):
                groups[fit_title(e.get("title") or "").lower()].append(e)
        out: dict[str, str] = {}
        for _, es in groups.items():
            if len(es) < 2:
                continue
            for e in es:
                base = strip_title_suffix(fit_title(e.get("title") or ""))
                d = parse_date(e.get("date"))
                for tag in (f"@{e.get('creator')}" if e.get("creator") else "",
                            f"@{e.get('creator')}, {d:%b %Y}" if e.get("creator") and d else "",
                            e.get("post_id") or e.get("id")):
                    if not tag:
                        continue
                    words = base.split(" ")
                    while words and len(" ".join(words)) + len(tag) + 3 > TITLE_MAX:
                        words.pop()
                    cand = " ".join(words).rstrip(" ,;:—–-·|") + f" · {tag}"
                    if sum(1 for x in es if x is not e and out.get(safe_slug(x["id"])) == cand) == 0 and \
                            not any(out.get(safe_slug(x["id"])) == cand for x in es):
                        out[safe_slug(e["id"])] = cand
                        break
        # still colliding (same creator + month): fall back to the id tag
        seen: dict[str, str] = {}
        for slug, cand in sorted(out.items()):
            if cand in seen.values():
                e = self.by_slug.get(slug) or {}
                tag = e.get("post_id") or slug
                base = cand.rsplit(" · ", 1)[0]
                out[slug] = base[: TITLE_MAX - len(tag) - 3].rstrip() + f" · {tag}"
            seen[slug] = out[slug]
        self._eto = out
        return out

    def dataset_modified(self) -> date:
        if not self.fresh:
            return self.generated
        payload = json.dumps([{k: v for k, v in e.items() if k not in VOLATILE} for e in self.entries],
                             sort_keys=True, ensure_ascii=False)
        rec = self.fresh.observe_key(DATASET_KEY, payload)
        return parse_date(rec.get("last_changed")) or self.generated

    def guide_entries(self, slug: str) -> list[dict]:
        ids = set((self.manual.get(slug) or {}).get("entry_ids") or [])
        out = [e for e in self.entries
               if e.get("id") in ids or e.get("deep_dive_slug") == slug or e.get("deep_dive") == slug]
        return out

    def guide_tools(self, slug: str, k: int = 10) -> list[str]:
        c = Counter(t for e in self.guide_entries(slug) for t in (e.get("tools") or []))
        return [t for t, _ in c.most_common(k)]


PERSON = {"@type": "Person", "@id": BASE + "/#victor", "name": OWNER_NAME, "url": OWNER_URL,
          "sameAs": [OWNER_GITHUB, AUTHOR_URL], "contactPoint": {"@type": "ContactPoint", "url": CONTACT_URL,
                                                               "contactType": "general"}}
ORG = {"@type": "Organization", "@id": BASE + "/#org", "name": SITE_NAME, "url": BASE + "/",
       "logo": BASE + "/og/default.png", "sameAs": [REPO_URL, AUTHOR_URL],
       "founder": {"@id": PERSON["@id"]}, "publishingPrinciples": BASE + "/method"}
AUTHOR_REF = {"@id": PERSON["@id"]}
WEBSITE_REF = {"@id": BASE + "/#website"}


def load_official_urls() -> dict[str, str]:
    """lowercased tool name/alias -> official site (data/monetize/affiliates.json official_url)."""
    out: dict[str, str] = {}
    aff = load_json(DATA / "monetize" / "affiliates.json", {}) or {}
    for rec in (aff.values() if isinstance(aff, dict) else aff):
        if not isinstance(rec, dict):
            continue
        u = (rec.get("official_url") or "").strip()
        if not u:
            continue
        for name in [rec.get("tool")] + list(rec.get("aliases") or []):
            if name:
                out.setdefault(str(name).lower(), u)
    return out


OFFICIAL = load_official_urls()


def tool_nodes(tools: list[str]) -> list[dict]:
    out = []
    for name in tools:
        u = OFFICIAL.get(name.lower())
        out.append({"@type": "SoftwareApplication", "name": name, "url": u, "sameAs": u} if u
                   else {"@type": "Thing", "name": name})
    return out


_DIM_CACHE: dict[str, tuple[int, int] | None] = {}


def image_dims(rel: str) -> tuple[int, int] | None:
    if rel.startswith("og/"):
        return OG_W, OG_H
    if rel not in _DIM_CACHE:
        try:
            from PIL import Image
            with Image.open(SITE / rel) as im:
                _DIM_CACHE[rel] = im.size
        except Exception:
            _DIM_CACHE[rel] = None
    return _DIM_CACHE[rel]


def creator_person(e: dict) -> dict | None:
    h = (e.get("creator") or "").strip().lstrip("@")
    if not h:
        return None
    u = e.get("url") or ""
    node = {"@type": "Person", "name": "@" + h, "alternateName": h}
    if "instagram.com" in u:
        node["url"] = f"https://www.instagram.com/{h}/"
    elif "github.com" in u:
        node["url"] = f"https://github.com/{h}"
    elif "tiktok.com" in u:
        node["url"] = f"https://www.tiktok.com/@{h}"
    elif "x.com" in u or "twitter.com" in u:
        node["url"] = f"https://x.com/{h}"
    return node


def entry_node(e: dict, url: str, desc: str, image: str, title: str) -> dict:
    """Primary entity of an /e/ page: VideoObject when it is a video with a transcript, else CreativeWork."""
    is_video = (e.get("media_type") == "video") and bool((e.get("transcript") or "").strip())
    kw = []
    for k in list(e.get("tags") or []) + list(e.get("tools") or []):
        if k and k.lower() not in {x.lower() for x in kw}:
            kw.append(k)
    node = {"@type": "VideoObject" if is_video else "CreativeWork", "@id": url + "#entry",
            "name": title, "description": desc or title, "url": url, "mainEntityOfPage": url,
            "isPartOf": {"@id": BASE + "/#dataset"}}
    au = creator_person(e)
    if au:
        node["author"] = au
        node["creator"] = au
    d = parse_date(e.get("date"))
    if d:
        node["uploadDate" if is_video else "datePublished"] = d.isoformat()
        if is_video:
            node["datePublished"] = d.isoformat()
    if kw:
        node["keywords"] = ", ".join(kw[:20])
    if e.get("url"):
        node["isBasedOn"] = e["url"]
        node["sameAs"] = e["url"]
    th = thumb_rel(e)
    if is_video:
        node["thumbnailUrl"] = BASE + "/" + (th or image)
        node["transcript"] = clip(e.get("transcript") or "", 500)
    if image:
        node["image"] = BASE + "/" + image
    if e.get("tools"):
        node["about"] = tool_nodes((e.get("tools") or [])[:6])
    return node


def flow_description(c: Ctx) -> str:
    """Live counts from site/flow_data.json (scripts/build_flow.py); <= 155 chars."""
    try:
        t = json.loads((SITE / "flow_data.json").read_text(encoding="utf-8"))["totals"]
    except (OSError, ValueError, KeyError):
        return f"How {c.n_entries} saved posts flow from creators and collections through tools into guides and prompt systems."
    return (f"Map of how {t['entries']} saved posts flow from creators through tools and techniques into "
            f"{t['guides']} guides and {t['prompt_systems']} prompt systems, with a gap analysis.")


def top_descriptions(c: Ctx) -> dict[str, str]:
    return {
        "flow.html": flow_description(c),
        "index.html": (f"A curated archive of {c.n_entries} saved posts on AI tools, agents, creative code and quant, "
                       f"transcribed and tiered, with {len(c.guides)} guides and {c.n_packs} prompt systems."),
        "catalog.html": (f"Filter {c.n_entries} curated posts by tier, tool, technique, creator and collection. "
                         f"{c.n_transcripts} have transcripts; JSON at /api/catalog.json."),
        "prompts.html": (f"{c.n_packs} pasteable prompt systems, one per DejaViewed guide: a one-shot prompt, "
                         f"{c.n_steps} step prompts with audits, gap audits and validation oracles."),
        "method.html": (f"How DejaViewed works: saved posts are captioned, transcribed, enriched and tiered S to C, "
                        f"then curated into {len(c.guides)} guides. Who runs it, update cadence, affiliate policy."),
        "system-prompts.html": (f"{c.n_packs} system prompt examples lifted from DejaViewed prompt systems, grouped by "
                                f"pillar: role, stance, constraints, each copyable and linked to its guide."),
        "start-here.html": (f"What DejaViewed is, who it is for, how humans and agents use it, how to cite it, "
                            f"and what is inside its {c.n_entries} entries and {c.n_colls} collections."),
        "guides/index.html": (f"{len(c.guides)} DejaViewed guides that connect saved posts into one build plan, "
                              f"each with sources, a thesis and a step-by-step prompt system."),
        "e/index.html": (f"Every DejaViewed entry on one page: {c.n_entries} saved posts with creator, tier, "
                         f"collection and a summary, each linking to its own detail page."),
    }


def sr_first_paragraph(text: str) -> str:
    """First real paragraph of the server-rendered guide body (<!-- body:start --> … <!-- body:end -->),
    preferring the text after the first <h2>; falls back to the legacy sr-index prerender."""
    m = re.search(r"<!-- body:start -->(.*?)<!-- body:end -->", text, re.S) \
        or re.search(r'class="sr-index".*?</div>', text, re.S)
    if not m:
        return ""
    blob = m.group(1) if m.lastindex else m.group(0)
    h = blob.find("<h2")
    paras = re.findall(r"<p\b[^>]*>(.*?)</p>", blob[h:] if h >= 0 else blob, re.S)
    if h >= 0 and not paras:
        paras = re.findall(r"<p\b[^>]*>(.*?)</p>", blob, re.S)
    for p in paras:
        t = clean_text(p)
        if len(t) >= 60 and not re.match(r"^(GitHub|Creator|Insight class|Stars|Source)\b", t):
            return t
    return ""


def as_list(v) -> list:
    """deeper_dives.json stores some lists as their Python repr string."""
    if isinstance(v, list):
        return v
    if isinstance(v, str) and v.strip().startswith("["):
        import ast
        try:
            r = ast.literal_eval(v)
            return r if isinstance(r, list) else []
        except Exception:
            return []
    return []


def deeper_description(dd: dict, text: str) -> str:
    """A deeper page's own snippet (not the guide's thesis): how many posts, from whom, which tools,
    and the first action step. Keeps guide/deeper twins from sharing one description (SEO-11)."""
    n = dd.get("entry_count") or len(as_list(dd.get("entries")))
    try:
        n = int(n)
    except (TypeError, ValueError):
        n = 0
    if not n:
        n = len(re.findall(r'class="dd-entry"', text))
    creators = ["@" + str(x).lstrip("@") for x in as_list(dd.get("creators"))][:3]
    tools = [str(x) for x in as_list(dd.get("tools"))][:3]
    if not n:
        return ""
    s = f"The evidence behind this idea: {n} connected saved post{'s' if n != 1 else ''}"
    if creators:
        s += " from " + (", ".join(creators[:-1]) + " and " + creators[-1] if len(creators) > 1 else creators[0])
    if tools:
        s += ", covering " + ", ".join(tools)
    s += "."
    act = clean_text(str(dd.get("action_sketch") or ""))
    act = re.sub(r"^\s*1[.)]\s*", "", act)
    first = re.split(r"(?:\s+\d[.)]\s+|\s*→\s*|(?<=[.!?])\s+)", act)[0].strip(" .") if act else ""
    if first and len(s) + len(first) + 20 <= 158:
        s += f" First step: {first}."
    return clip(s, 158)


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
        "creator": AUTHOR_REF,
        "publisher": {"@id": ORG["@id"]},
        # curation fields are ours; captions/transcripts stay with their creators (see /method#terms)
        "license": BASE + "/method#terms",
        "usageInfo": BASE + "/method#terms",
        "isAccessibleForFree": True,
        "dateModified": c.dataset_modified().isoformat(),
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
    graph: list[dict] = [ORG, PERSON]
    og_type = "website"
    image = og_image_rel("default")
    desc = ""
    parts = rel.split("/")

    if rel in tops:
        desc = tops[rel]
        name = {"index.html": "default", "catalog.html": "catalog", "prompts.html": "prompts",
                "start-here.html": "start-here", "method.html": "method"}.get(rel)
        image = (og_image_rel(name) if name else None) or image
        if rel == "index.html":
            graph.append({"@type": "WebSite", "@id": WEBSITE_REF["@id"], "url": BASE + "/", "name": SITE_NAME,
                          "description": desc, "publisher": {"@id": ORG["@id"]}, "author": AUTHOR_REF,
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
        elif rel == "method.html":
            pub, mod = c.fresh.dates(rel) if c.fresh else file_dates(SITE / rel)
            graph.append({"@type": "AboutPage", "@id": url + "#page", "url": url, "name": ttl,
                          "description": desc, "isPartOf": WEBSITE_REF, "author": AUTHOR_REF,
                          "publisher": {"@id": ORG["@id"]}, "about": {"@id": ORG["@id"]},
                          "datePublished": pub.isoformat(), "dateModified": mod.isoformat()})
            graph.append(breadcrumbs([("Home", BASE + "/"), ("How it works", None)]))
        else:  # start-here
            graph.append({"@type": "WebPage", "@id": url + "#page", "url": url, "name": ttl,
                          "description": desc, "isPartOf": WEBSITE_REF})

    elif parts[0] == "guides":
        slug = Path(rel).stem
        og_type = "article"
        md = c.manual.get(slug) or {}
        pack = c.packs.get(slug) or {}
        desc = md.get("thesis") or sr_first_paragraph(text) or pack.get("mission", "")
        desc = clip_sentence(desc)
        if desc and len(desc) < 110 and pack.get("steps"):
            desc = clip_sentence(f"{desc.rstrip('.…')}. Includes a {len(pack['steps'])}-step prompt system.")
        image = og_image_rel(slug) or image
        pub, mod = c.fresh.dates(rel) if c.fresh else file_dates(SITE / rel)
        tools = c.guide_tools(slug)
        art = {"@type": "Article", "@id": url + "#article", "headline": ttl[:110], "description": desc,
               "url": url, "mainEntityOfPage": url, "datePublished": pub.isoformat(),
               "dateModified": mod.isoformat(), "author": AUTHOR_REF,
               "publisher": {"@id": ORG["@id"]}, "isPartOf": WEBSITE_REF,
               "image": BASE + "/" + (image or "og/default.png")}
        if tools:
            art["about"] = tool_nodes(tools[:3])
            if tools[3:]:
                art["mentions"] = tool_nodes(tools[3:])
        ans = re.search(r"(?m)^> \*\*In short:\*\* (.+)$", text)
        if ans:   # the "In two sentences" answer block build_guides.py puts at the top of every guide
            art["abstract"] = html.unescape(ans.group(1)).strip()
        # no FAQPage: Google shows FAQ rich results only for gov/health sites since 2023, and the
        # self_questions are already visible in the prompt system (SEO-13)
        graph.append(art)
        graph.append(breadcrumbs([("Home", BASE + "/"), ("Guides", BASE + "/guides/"), (ttl, None)]))

    elif parts[0] == "deeper":
        stem = Path(rel).stem
        slug = stem.replace("deeper-insight-", "", 1)
        og_type = "article"
        dd = c.deeper.get(stem) or {}
        desc = deeper_description(dd, text) or clip_sentence(dd.get("thesis") or (c.manual.get(slug) or {}).get("thesis") or "")
        image = og_image_rel(stem) or image
        pub, mod = c.fresh.dates(rel) if c.fresh else file_dates(SITE / rel)
        tools = as_list(dd.get("tools"))[:10]
        art = {"@type": "Article", "@id": url + "#article", "headline": ttl[:110], "description": desc,
               "url": url, "mainEntityOfPage": url, "datePublished": pub.isoformat(),
               "dateModified": mod.isoformat(), "author": AUTHOR_REF,
               "publisher": {"@id": ORG["@id"]}, "isPartOf": WEBSITE_REF,
               "image": BASE + "/" + (image or "og/default.png")}
        if tools:
            art["about"] = tool_nodes(tools[:3])
            if tools[3:]:
                art["mentions"] = tool_nodes(tools[3:])
        graph.append(art)
        crumbs = [("Home", BASE + "/"), ("Guides", BASE + "/guides/")]
        if (SITE / "guides" / f"{slug}.html").exists():
            gt = re.search(r"<title>(.*?)</title>", (SITE / "guides" / f"{slug}.html").read_text(errors="replace"), re.S)
            crumbs.append((strip_title_suffix(html.unescape(gt.group(1))) if gt else slug,
                           canonical_url(f"guides/{slug}.html")))
        crumbs.append(("Deeper dive", None))
        graph.append(breadcrumbs(crumbs))

    elif parts[0] in ("tools", "compare", "best") and len(parts) == 2:
        # Hub / comparison / best-of pages (build_tools.py, build_compare.py) carry their own
        # <meta name="description"> and <h1>; reuse them, add Article + breadcrumb.
        section = {"tools": "Tools", "compare": "Compare", "best": "Best of"}[parts[0]]
        og_type = "article"
        md = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', text, re.I)
        desc = clip_sentence(html.unescape(md.group(1))) if md and md.group(1).strip() else ""
        if not desc:
            lead = re.search(r'<p[^>]*class="[^"]*lead[^"]*"[^>]*>(.*?)</p>', text, re.S | re.I) \
                or re.search(r'<main[^>]*>.*?<p[^>]*>(.*?)</p>', text, re.S | re.I)
            desc = clip_sentence(clean_text(lead.group(1))) if lead else ttl
        image = og_image_rel(f"{parts[0]}-{Path(rel).stem}") or og_image_rel(parts[0]) or image
        pub, mod = c.fresh.dates(rel) if c.fresh else file_dates(SITE / rel)
        art = {"@type": "Article", "@id": url + "#article", "headline": ttl[:110], "description": desc,
               "url": url, "mainEntityOfPage": url, "datePublished": pub.isoformat(),
               "dateModified": mod.isoformat(), "author": AUTHOR_REF,
               "publisher": {"@id": ORG["@id"]}, "isPartOf": WEBSITE_REF,
               "image": BASE + "/" + (image or "og/default.png")}
        graph.append(art)
        crumbs = [("Home", BASE + "/")]
        if parts[1] != "index.html":
            crumbs += [(section, canonical_url(f"{parts[0]}/index.html")), (ttl, None)]
        else:
            crumbs.append((section, None))
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
        image = og_image_rel("e/" + Path(rel).stem) or th or image
        if e:
            graph.append(entry_node(e, url, desc, image, ttl))
        # mirrors the visible breadcrumb render_entries writes: Home › Catalog › <collection> › title
        crumbs = [("Home", BASE + "/"), ("Catalog", canonical_url("catalog.html"))]
        coll = (e.get("collection") or e.get("source_collection") or "") if e else ""
        if coll:
            try:
                from build_collections import collection_name, collection_url
                if (SITE / (collection_url(coll).lstrip("/") + ".html")).is_file():
                    crumbs.append((collection_name(coll), BASE + collection_url(coll)))
            except Exception:
                pass
        crumbs.append((ttl, None))
        graph.append(breadcrumbs(crumbs))

    image = image or "og/default.png"
    return {"desc": desc, "og_type": og_type, "image": image, "image_dims": image_dims(image),
            "image_is_og": image.startswith("og/"), "graph": graph, "url": url, "og_title": ttl}


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
    if m.get("image_dims"):
        w, h = m["image_dims"]
        lines += [f'<meta property="og:image:width" content="{w}">',
                  f'<meta property="og:image:height" content="{h}">']
    lines.append(f'<meta property="og:image:alt" content="{a(m["og_title"])}">')
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
    in_head = title
    if rel.startswith("e/") and Path(rel).stem in c.entry_title_overrides():
        title = c.entry_title_overrides()[Path(rel).stem]
    if rel.startswith("deeper/"):   # keep the twin distinct from its guide: the marker goes first
        base = re.sub(r"\s*[—–-]\s*Deeper Dive\s*$", "", strip_title_suffix(title), flags=re.I)
        if not base.lower().startswith("deeper dive"):
            base = "Deeper dive: " + base
        title = base
    fitted = fit_title(title)
    if tm and fitted != in_head:    # title policy: <= TITLE_MAX chars, suffix only when it fits
        head = head[: tm.start()] + f"<title>{html.escape(fitted, quote=False)}</title>" + head[tm.end():]
        title = fitted
        tm = re.search(r"<title>(.*?)</title>", head, re.S | re.I)
    if c.fresh:
        c.fresh.observe(rel, head + rest)

    if rel.split("/")[0] in ("tools", "compare", "best") and START in orig \
            and not re.search(r'<meta\s+name="description"', text, re.I):
        # generator-owned description lived outside the block on first run and inside it after;
        # on a standalone re-run the outside tag is gone (STRAY-stripped), so carry it over from the previous block.
        prev = re.search(r'<meta\s+name="description"\s+content="([^"]*)"', orig[orig.find(START):], re.I)
        if prev and prev.group(1).strip():
            text = text.replace("<head>", f'<head><meta name="description" content="{prev.group(1)}">', 1)
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

    fresh = Freshness()
    c = Ctx(fresh)
    qmap = {q["page"]: q for q in c.queries}
    titles: dict[str, str] = {}
    descs: dict[str, str] = {}
    faq_nodes = 0
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
        tm = re.search(r"<title>(.*?)</title>", new, re.S | re.I)
        titles[rel] = html.unescape(tm.group(1)) if tm else ""
        descs[rel] = meta["desc"]
        faq_nodes += sum(1 for n in meta["graph"] if n.get("@type") == "FAQPage")
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

    # freshness store + sitemap (lastmod = last real content change, not build date)
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from build_api import sitemap_xml
    sm_new = sitemap_xml(fresh)
    sm_path = SITE / "sitemap.xml"
    sm_old = sm_path.read_text(encoding="utf-8") if sm_path.exists() else ""
    if sm_new != sm_old:
        would_change.append("sitemap.xml")
    if not args.check:
        fresh.save()
        write_if_changed(sm_path, sm_new)
    elif fresh.dirty:
        would_change.append(str(HASHES_PATH.relative_to(ROOT)))

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
    lens = sorted(len(x) for x in titles.values())
    dup_t = sum(n for n in Counter(titles.values()).values() if n > 1)
    dup_d = Counter(v for v in descs.values() if v)
    print(f"titles: {len(lens)} · max {lens[-1] if lens else 0} chars · > {TITLE_MAX}: "
          f"{sum(1 for x in lens if x > TITLE_MAX)} · pages sharing a title: {dup_t}")
    print(f"descriptions used on more than one page: {sum(1 for v in dup_d.values() if v > 1)} values "
          f"({sum(v for v in dup_d.values() if v > 1)} pages) · FAQPage nodes: {faq_nodes}")
    print(f"sitemap: {sm_new.count('<url>')} urls · freshness: {sum(1 for k in fresh.data if k.startswith('http'))} pages tracked, "
          f"{sum(1 for r in fresh.data.values() if r.get('last_changed') == fresh.today)} changed today")
    if args.check:
        print(f"[check] {len(would_change)} page(s) would change" + (f": {would_change[:10]}" if would_change else ""))
        return 1 if would_change else 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
