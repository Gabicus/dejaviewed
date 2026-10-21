#!/usr/bin/env python3
"""Dead-link audit for the DejaViewed site.

Two scopes:
  A) INTERNAL — crawl site/ HTML (+ sitemap.xml <loc>s) and verify every
     relative/root-relative href/src resolves to a file on disk. Cloudflare
     Pages clean URLs are honoured: `foo`, `foo.html`, `dir/` -> dir/index.html.
  B) EXTERNAL — HEAD/GET every external URL from S/A-tier entries
     (takeaways "link: ..." + repos) and from guide/deeper page hrefs.
     2xx/3xx = alive, 401/403/405/429/999 = unknown (bot-blocked),
     404/410/5xx-after-retry/connection errors = dead. Instagram skipped.

Output: data/link_report.json + a printed summary.

Usage:
  python3 scripts/check_links.py               # both scopes
  python3 scripts/check_links.py --internal    # internal only (fast, offline)
  python3 scripts/check_links.py --external
  python3 scripts/check_links.py --e-sample 0  # check ALL e/*.html (default 50)
"""
from __future__ import annotations

import argparse
import ast
import json
import random
import re
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
REPORT = ROOT / "data" / "link_report.json"
SITE_HOST = "dejaviewed.dev"

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/126.0 Safari/537.36")
SKIP_SCHEMES = ("mailto:", "tel:", "javascript:", "data:", "blob:", "about:", "sms:")
LINK_ATTRS = {"href", "src", "poster", "data-src"}


# ---------------------------------------------------------------- HTML parse
class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[int, str, str]] = []  # (line, tag, url)

    def handle_starttag(self, tag, attrs):
        line = self.getpos()[0]
        for k, v in attrs:
            if not v:
                continue
            if k in LINK_ATTRS:
                self.links.append((line, tag, v.strip()))
            elif k == "srcset":
                for part in v.split(","):
                    u = part.strip().split(" ")[0]
                    if u:
                        self.links.append((line, tag, u))

    handle_startendtag = handle_starttag


def extract_links(path: Path) -> list[tuple[int, str, str]]:
    p = LinkParser()
    try:
        p.feed(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as ex:  # malformed HTML shouldn't kill the audit
        print(f"  warn: parse failed {path}: {ex}", file=sys.stderr)
    return p.links


# ---------------------------------------------------------------- internal
def is_templated(u: str) -> bool:
    return "${" in u or "{{" in u or "' +" in u or '" +' in u


def resolve_internal(src: Path, url: str) -> tuple[bool, str]:
    """Return (ok, resolved_site_relative_path)."""
    parts = urlsplit(url)
    path = unquote(parts.path)
    if not path:  # pure "#frag" or "?q"
        return True, ""
    if path.startswith("/"):
        target = SITE / path.lstrip("/")
    else:
        target = (src.parent / path)
    try:
        target = target.resolve()
        rel = target.relative_to(SITE.resolve())
    except ValueError:
        return False, str(target)  # escapes site/
    cands = [target]
    if path.endswith("/") or target.is_dir():
        cands.append(target / "index.html")
    else:
        cands.append(target.with_name(target.name + ".html"))
    ok = any(c.is_file() for c in cands)
    return ok, str(rel) + ("/" if path.endswith("/") else "")


def internal_pages(e_sample: int) -> list[Path]:
    pages: list[Path] = []
    pages += sorted(SITE.glob("*.html"))  # index, catalog, search, board, graph*, admin, ...
    pages += sorted((SITE / "guides").glob("*.html"))
    pages += sorted((SITE / "deeper").glob("*.html"))
    for sub in ("about/index.html", "links/index.html"):
        if (SITE / sub).is_file():
            pages.append(SITE / sub)
    eps = sorted((SITE / "e").glob("*.html"))
    if e_sample and len(eps) > e_sample:
        rnd = random.Random(42)
        # always include the weird-id pages (sanitized slugs) + a seeded sample
        weird = [p for p in eps if "_" in p.stem]
        eps = sorted(set(rnd.sample(eps, e_sample)) | set(weird[:10]))
    pages += eps
    return pages


def check_internal(e_sample: int) -> dict:
    broken: dict[str, list[dict]] = defaultdict(list)
    n_links = 0
    pages = internal_pages(e_sample)
    for page in pages:
        for line, tag, url in extract_links(page):
            low = url.lower()
            if low.startswith(SKIP_SCHEMES) or low.startswith("#") or is_templated(url):
                continue
            sp = urlsplit(url)
            if sp.scheme in ("http", "https") or url.startswith("//"):
                if sp.netloc.lower().removeprefix("www.") != SITE_HOST:
                    continue  # external — scope B
                url = sp.path or "/"
            n_links += 1
            ok, resolved = resolve_internal(page, url)
            if not ok:
                broken[str(page.relative_to(SITE))].append(
                    {"line": line, "tag": tag, "url": url, "resolved": resolved})
    # sitemap <loc>s
    sm = SITE / "sitemap.xml"
    if sm.is_file():
        for i, line in enumerate(sm.read_text(encoding="utf-8").splitlines(), 1):
            for loc in re.findall(r"<loc>([^<]+)</loc>", line):
                path = urlsplit(loc.replace("&amp;", "&")).path or "/"
                n_links += 1
                ok, resolved = resolve_internal(SITE / "index.html", path)
                if not ok:
                    broken["sitemap.xml"].append(
                        {"line": i, "tag": "loc", "url": loc, "resolved": resolved})
    # JS-rendered thumbs (index.html / catalog.html build thumb/<id '/'->'_'>.jpg at
    # runtime and hide the <img> on error) — informational, not counted as broken.
    missing_thumbs = []
    try:
        cat = json.loads((SITE / "catalog.json").read_text(encoding="utf-8"))
        for e in cat["entries"]:
            pid = (e.get("post_id") or e.get("id") or "").replace("/", "_")
            if pid and not (SITE / "thumb" / f"{pid}.jpg").is_file():
                missing_thumbs.append(e.get("id"))
    except Exception:
        pass
    return {"pages_scanned": len(pages) + (1 if sm.is_file() else 0),
            "missing_thumbs_info": missing_thumbs,
            "links_checked": n_links,
            "broken_count": sum(len(v) for v in broken.values()),
            "broken": dict(broken)}


# ---------------------------------------------------------------- external
def _as_list(v) -> list:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    s = str(v).strip()
    if s.startswith("["):
        try:
            return list(ast.literal_eval(s))
        except Exception:
            return []
    return [s] if s else []


URL_RE = re.compile(r"https?://[^\s\"'<>)\]`|\\]+")
PLACEHOLDER_RE = re.compile(r"(^|\.)(example\.(com|org|net)|yourdomain\.com)$|^localhost|^127\.0\.0\.1|^host\.docker\.internal")
# page-asset hosts (fonts/CDNs/XML namespaces) — not content links
ASSET_HOSTS = {"fonts.googleapis.com", "fonts.gstatic.com", "cdn.jsdelivr.net",
               "cdnjs.cloudflare.com", "unpkg.com", "www.w3.org", "w3.org",
               "cdn.tailwindcss.com", "code.jquery.com"}
DOMAIN_RE = re.compile(r"^[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}(/\S*)?$")
GH_RE = re.compile(r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")


def repo_to_url(r: str) -> str | None:
    r = r.strip().rstrip(".,")
    if r.startswith(("http://", "https://")):
        return r
    if r.lower().startswith("github.com/"):
        return "https://" + r
    if GH_RE.match(r):
        if "." in r.split("/")[0]:  # "foo.com/bar" style
            return "https://" + r
        return "https://github.com/" + r
    if DOMAIN_RE.match(r):
        return "https://" + r
    return None  # free text like "vectorbt" — not resolvable


def collect_external() -> tuple[dict[str, set[str]], list[str]]:
    where: dict[str, set[str]] = defaultdict(set)
    unresolvable: list[str] = []
    cat = json.loads((SITE / "catalog.json").read_text(encoding="utf-8"))
    for e in cat["entries"]:
        if e.get("tier") not in ("S", "A"):
            continue
        eid = e.get("id", "?")
        for t in _as_list(e.get("takeaways")):
            t = str(t)
            if t.lower().lstrip().startswith("link:"):
                for u in URL_RE.findall(t) or [t.split(":", 1)[1].strip()]:
                    u = u.rstrip(".,;")
                    if not u.startswith("http"):
                        u = repo_to_url(u) or ""
                    if u:
                        where[u].add(f"entry:{eid}:takeaways")
        for r in _as_list(e.get("repos")):
            u = repo_to_url(str(r))
            if u:
                where[u].add(f"entry:{eid}:repos")
            else:
                unresolvable.append(f"{eid}: {r}")
    # Guide pages carry most links as Markdown inside <script id="md"> (rendered
    # client-side), so scan raw text for URLs rather than only parsed <a href>.
    for sub in ("guides", "deeper"):
        for page in sorted((SITE / sub).glob("*.html")):
            for ln, text in enumerate(page.read_text(encoding="utf-8", errors="replace")
                                      .splitlines(), 1):
                for url in URL_RE.findall(text):
                    url = url.rstrip(".,;:*`'")
                    host = urlsplit(url).netloc.lower().removeprefix("www.")
                    if (not host or host == SITE_HOST or host in ASSET_HOSTS
                            or PLACEHOLDER_RE.search(host)):  # code-sample placeholders
                        continue
                    where[url].add(f"{sub}/{page.name}:{ln}")
    # drop instagram (login wall)
    skipped = [u for u in where if "instagram.com" in urlsplit(u).netloc.lower()]
    for u in skipped:
        where.pop(u)
    return where, unresolvable + [f"(instagram skipped) {len(skipped)} urls"]


def probe(url: str) -> tuple[str, int | None, str]:
    import requests
    hdrs = {"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9"}

    def once() -> tuple[int | None, str]:
        try:
            r = requests.head(url, headers=hdrs, timeout=10, allow_redirects=True)
            if r.status_code in (403, 404, 405, 400, 429, 501) or r.status_code >= 500:
                r = requests.get(url, headers=hdrs, timeout=10, allow_redirects=True, stream=True)
                r.close()
            return r.status_code, ""
        except requests.RequestException as ex:
            return None, type(ex).__name__

    def classify(code, err) -> str:
        if code is None:
            return "dead"
        if 200 <= code < 400:
            return "alive"
        if code in (401, 403, 405, 429, 999, 451):
            return "unknown"
        if code in (404, 410):
            return "dead"
        if code >= 500:
            return "dead"
        return "unknown"

    code, err = once()
    status = classify(code, err)
    if status == "dead":
        time.sleep(1.5)
        code, err = once()
        status = classify(code, err)
    return status, code, err


def check_external() -> dict:
    where, unresolvable = collect_external()
    urls = sorted(where)
    with ThreadPoolExecutor(max_workers=8) as ex:
        results = list(ex.map(probe, urls))
    rows = []
    for u, (status, code, err) in zip(urls, results):
        rows.append({"url": u, "status": status, "code": code, "error": err,
                     "appears_in": sorted(where[u])})
    counts = {k: sum(1 for r in rows if r["status"] == k) for k in ("alive", "unknown", "dead")}
    return {"total": len(rows), "counts": counts, "unresolved_refs": unresolvable,
            "dead": [r for r in rows if r["status"] == "dead"],
            "unknown": [r for r in rows if r["status"] == "unknown"],
            "alive": [r["url"] for r in rows if r["status"] == "alive"]}


# ---------------------------------------------------------------- main
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--internal", action="store_true")
    ap.add_argument("--external", action="store_true")
    ap.add_argument("--e-sample", type=int, default=50, help="0 = all e/*.html")
    a = ap.parse_args()
    do_int = a.internal or not a.external
    do_ext = a.external or not a.internal

    t0 = time.time()
    report: dict = {"generated": time.strftime("%Y-%m-%dT%H:%M:%S")}
    if REPORT.exists():  # keep the other scope's last result when running one
        try:
            report.update({k: v for k, v in json.loads(REPORT.read_text()).items()
                           if k in ("internal", "external")})
        except Exception:
            pass
    if do_int:
        report["internal"] = check_internal(a.e_sample)
        i = report["internal"]
        print(f"INTERNAL: {i['pages_scanned']} pages, {i['links_checked']} links, "
              f"{i['broken_count']} broken  (info: {len(i['missing_thumbs_info'])} entries "
              f"without a thumb file; JS hides those)")
        for src, lst in sorted(i["broken"].items()):
            print(f"  {src}  ({len(lst)})")
            for b in lst[:8]:
                print(f"    L{b['line']:<5} <{b['tag']}> {b['url']}")
            if len(lst) > 8:
                print(f"    ... +{len(lst) - 8} more")
    if do_ext:
        report["external"] = check_external()
        x = report["external"]
        c = x["counts"]
        print(f"\nEXTERNAL: {x['total']} urls | alive {c['alive']} | unknown {c['unknown']} "
              f"| dead {c['dead']}")
        for r in x["dead"]:
            print(f"  DEAD {r['code'] or r['error']:<22} {r['url']}")
            print(f"       in: {', '.join(r['appears_in'][:4])}")
    report["runtime_s"] = round(time.time() - t0, 1)
    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nruntime {report['runtime_s']}s -> {REPORT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
