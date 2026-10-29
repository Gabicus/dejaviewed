#!/usr/bin/env python3
"""Weekly growth scorecard: every analytics audit side by side, same metrics, same definitions.

Usage:
    python3 scripts/analytics_report.py          # 1. the raw audit -> data/analytics/<date>.json
    python3 scripts/analytics_scorecard.py       # 2. extras + scorecard (this script)
    python3 scripts/analytics_scorecard.py --no-collect   # re-render only, no network

What it does
  collect (network, read-only APIs; secrets read from file, never printed):
    - Google Search Console daily clicks/impressions/position since 2026-10-01 -> merged into
      data/analytics/gsc_daily.json (Google keeps 16 months, so the series is backfilled, not just forward)
    - Search Console impressions/clicks by site section for the 7 latest days with data
    - Cloudflare 404 paths for the audit's 7-day window (top 40; scanner probes classified)
    - site inventory at audit time (entries, guides, prompt systems, tool hubs, sitemap URLs)
    -> data/analytics/<date>.extras.json   (date = the latest raw audit's date)
  render:
    - docs/reports/analytics_scorecard.md   (tables: growth at a glance, every metric x every audit,
      weekly Google series, changes shipped, findings and actions, verification ledger)
    - docs/reports/analytics_scorecard.html (same content + charts)

Apples to apples: every metric is defined ONCE in METRICS below and computed from the raw files by
the same function for every audit. Add a metric by appending to METRICS; audits taken before the
metric existed show "n/a" (never a guessed number). Never change an existing metric's definition —
add a new key instead, so old comparisons stay valid.

Hand-maintained logs (edit these, then re-run with --no-collect):
    data/analytics/changes.json    dated things we shipped (annotate the growth chart)
    data/analytics/findings.json   what each audit taught us + action + status (open/done)
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "analytics"
SITE = ROOT / "site"
OUT_MD = ROOT / "docs" / "reports" / "analytics_scorecard.md"
OUT_HTML = ROOT / "docs" / "reports" / "analytics_scorecard.html"
GSC_DAILY = DATA / "gsc_daily.json"
CHANGES = DATA / "changes.json"
FINDINGS = DATA / "findings.json"
SERIES_START = "2026-10-01"
sys.path.insert(0, str(Path(__file__).resolve().parent))

RAW_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})\.json$")
# "Real" 404 = a path a legitimate visitor or browser would request: our site sections, our asset
# folders, browser auto-fetches. Everything else is treated as probe noise (.env hunts, CMS guesses).
REAL_RE = re.compile(r"^/(?:e|guides|deeper|tools|compare|best|collections|links|about|api|og|thumb|fonts|"
                     r"pagefind|vendor|data|cdn-cgi/l)/|^/(?:favicon\.ico|favicon\.svg|apple-touch-icon[\w.-]*\.png|"
                     r"robots\.txt|sitemap\.xml|llms(?:-full)?\.txt|feed\.xml|context\.md|\.well-known/[\w.-]+|"
                     r"catalog|prompts|search|graph|graph-cosmos|board|flow|method|start-here|system-prompts|rate)"
                     r"(?:\.html)?$|\.(?:js|css|json|jpg|png|webp|woff2)$")
SCANNER_RE = re.compile(r"\.env|\.php|wp-|wordpress|\.git|\.ya?ml$|admin|login|config|backup|\.sql|\.bak|\.swp|"
                        r"phpinfo|cgi-bin|\.aws|\.ssh|actuator|xmlrpc|sa\.json|service-account|password|"
                        r"credential|key\.json|firebase|\.docker|secret|token|\.pem$|id_rsa|register|account|portal|dashboard|settings|workspace|onboarding|@fs|"
                        r"^/(blog|news|wp|cms|site|press|old|new|test|demo|shop|home|web|main|backup|app|auth|"
                        r"api/v\d|graphql|server-status|telescope|debug|console|_next|static)(/.*)?$", re.I)


# ───────────────────────────────────────────────────────────── helpers
def jload(p: Path, default=None):
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def dig(d, *path, default=None):
    for k in path:
        if not isinstance(d, dict) or k not in d:
            return default
        d = d[k]
    return d


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()[:16]


def gsc_window_sum(series: dict, end: str | None, days: int, field: str):
    """Sum a field over the `days` dates ending at `end` (inclusive). None if the series lacks them."""
    if not end:
        return None
    e = dt.date.fromisoformat(end)
    tot, seen = 0.0, 0
    for i in range(days):
        row = series.get((e - dt.timedelta(days=i)).isoformat())
        if row is not None:
            tot += row.get(field, 0)
            seen += 1
    return tot if seen else None


# ───────────────────────────────────────────────────────────── metric registry
# (key, group, label, unit, better, fn(raw, extras, series) -> number|None, definition)
# better: "up" | "down" | "flat"  (flat = context, not judged)
def _crawler(name):
    return lambda r, x, s: dig(r, "cloudflare", "adaptive_7d", "crawlers", name)


def _ai_path(path):
    def f(r, x, s):
        cp = dig(r, "cloudflare", "adaptive_7d", "crawler_paths")
        if cp is None:
            return None
        return sum(v.get(path, 0) for k, v in cp.items() if k not in ("human/browser",))
    return f


def _status7(code):
    def f(r, x, s):
        rows = dig(r, "cloudflare", "adaptive_7d", "status_cache")
        if rows is None:
            return None
        return sum(row["requests"] for row in rows if str(row.get("status")) == code)
    return f


def _go(slug=None):
    def f(r, x, s):
        rows = dig(r, "cloudflare", "outbound_go", "rows")
        if rows is None:
            return None
        return sum(row.get("human_7d", 0) for row in rows if slug is None or row.get("slug") == slug)
    return f


def _gsc7(r, s, field):
    """7-day Google sum from the daily series. Google returns no row for a zero day, so when the series
    has nothing in the window but the audit's own 28-day total was 0, the true value is 0 (not n/a)."""
    v = gsc_window_sum(s, dig(r, "gsc", "window", "end"), 7, field)
    if v is None and dig(r, "gsc", "totals_28d", field) == 0:
        return 0
    return v


def _indexed_share(r, x, s):
    cs = dig(r, "gsc", "index_coverage_sample")
    if not cs or not cs.get("inspected"):
        return None
    return cs.get("coverageStates", {}).get("Submitted and indexed", 0) / cs["inspected"]


def _vital(field, div=1000):
    def f(r, x, s):
        v = dig(r, "cloudflare", "vitals_7d", field)
        return None if v is None else v / div
    return f


METRICS = [
    # ── people
    ("visits_7d", "People", "Real visits, 7 days", "", "up", lambda r, x, s: dig(r, "cloudflare", "rum_7d", "visits"),
     "Cloudflare Web Analytics (browser beacon, so bots excluded) visits in the 7 days before the audit"),
    ("pageviews_7d", "People", "Real page views, 7 days", "", "up", lambda r, x, s: dig(r, "cloudflare", "rum_7d", "pageviews"),
     "Cloudflare Web Analytics page views, 7 days"),
    ("visits_28d", "People", "Real visits, 28 days", "", "up", lambda r, x, s: dig(r, "cloudflare", "rum_28d", "visits"),
     "Cloudflare Web Analytics visits, 28 days"),
    ("uniques_7d", "People", "Edge unique visitors (sum of daily), 7 days", "", "up",
     lambda r, x, s: dig(r, "cloudflare", "rollup_7d", "uniques_sum_of_daily"), "Cloudflare zone rollup; includes bots"),
    # ── Google
    ("gsc_impr_7d", "Google search", "Google impressions, 7 days", "", "up",
     lambda r, x, s: _gsc7(r, s, "impressions"),
     "Search Console daily series, 7 days ending at the audit's Search Console window end"),
    ("gsc_clicks_7d", "Google search", "Google clicks, 7 days", "", "up",
     lambda r, x, s: _gsc7(r, s, "clicks"), "same window as above"),
    ("gsc_impr_28d", "Google search", "Google impressions, 28 days", "", "up",
     lambda r, x, s: dig(r, "gsc", "totals_28d", "impressions"), "Search Console totals, 28-day window in the raw audit"),
    ("gsc_clicks_28d", "Google search", "Google clicks, 28 days", "", "up",
     lambda r, x, s: dig(r, "gsc", "totals_28d", "clicks"), "Search Console totals, 28 days"),
    ("gsc_pos_28d", "Google search", "Average Google position, 28 days", "", "down",
     lambda r, x, s: dig(r, "gsc", "totals_28d", "position") or None, "lower is better; blank when no impressions"),
    ("indexed_share", "Google search", "Indexed share of URL-inspection sample", "%", "up", _indexed_share,
     "Submitted-and-indexed / inspected, URL Inspection API sample (sample size grows over time)"),
    ("gsc_pages_7d", "Google search", "Pages with any impressions, 7 days", "", "up",
     lambda r, x, s: dig(x, "gsc_sections", "pages_with_impressions"), "Search Console page dimension (extras)"),
    # ── answer engines and crawlers
    ("bot_google", "Crawlers & answer engines", "Googlebot hits, 7 days", "", "up", _crawler("Googlebot"), "UA class, Cloudflare sampled"),
    ("bot_bing", "Crawlers & answer engines", "Bingbot hits, 7 days", "", "up", _crawler("Bingbot"), ""),
    ("bot_oai_search", "Crawlers & answer engines", "OpenAI search crawler (OAI-SearchBot), 7 days", "", "up", _crawler("OAI-SearchBot"), ""),
    ("bot_chatgpt_user", "Crawlers & answer engines", "ChatGPT live fetches for a user (ChatGPT-User), 7 days", "", "up", _crawler("ChatGPT-User"), ""),
    ("bot_claude", "Crawlers & answer engines", "ClaudeBot hits, 7 days", "", "up", _crawler("ClaudeBot"), ""),
    ("bot_claude_user", "Crawlers & answer engines", "Claude live fetches for a user (Claude-User), 7 days", "", "up", _crawler("Claude-User"), ""),
    ("bot_perplexity", "Crawlers & answer engines", "PerplexityBot hits, 7 days", "", "up", _crawler("PerplexityBot"), ""),
    ("bot_perplexity_user", "Crawlers & answer engines", "Perplexity live fetches (Perplexity-User), 7 days", "", "up", _crawler("Perplexity-User"), ""),
    ("bot_gptbot", "Crawlers & answer engines", "GPTBot (OpenAI training crawler), 7 days", "", "flat", _crawler("GPTBot"), ""),
    ("bot_amazon", "Crawlers & answer engines", "Amazonbot hits, 7 days", "", "flat", _crawler("Amazonbot"), ""),
    ("ai_llms_full", "Crawlers & answer engines", "Bot pulls of /llms-full.txt, 7 days", "", "up", _ai_path("/llms-full.txt"),
     "all non-browser classes; the paid-data demand signal"),
    ("ai_api", "Crawlers & answer engines", "Bot pulls of /api/*, 7 days", "", "up", _ai_path("/api/"), "all non-browser classes"),
    # ── speed
    ("lcp_p75_ms", "Speed (real visitors)", "Largest Contentful Paint p75 (LCP)", "ms", "down", _vital("largestContentfulPaintP75"),
     "time until the main content shows; Google's 'good' is under 2,500 ms"),
    ("inp_p75_ms", "Speed (real visitors)", "Interaction to Next Paint p75 (INP)", "ms", "down", _vital("interactionToNextPaintP75"),
     "click responsiveness; 'good' is under 200 ms"),
    ("cls_p75", "Speed (real visitors)", "Cumulative Layout Shift p75 (CLS)", "", "down", _vital("cumulativeLayoutShiftP75", 1),
     "layout jumps; 'good' is under 0.1"),
    # ── outbound
    ("go_human_7d", "Outbound clicks", "Human /go/ clicks, 7 days", "", "up", _go(), "all /go/ slugs, browser user agents"),
    ("go_service_7d", "Outbound clicks", "Human clicks on the done-for-you service link, 7 days", "", "up", _go("service"), ""),
    ("go_diy_7d", "Outbound clicks", "Human clicks on the DIY (GitHub skill) link, 7 days", "", "up", _go("diy"), ""),
    # ── health
    ("http_404_7d", "Site health", "404 responses, 7 days (sampled)", "", "down", _status7("404"),
     "mostly scanner probes; see the 404 table for real ones"),
    ("http_404_real_7d", "Site health", "404s on non-probe paths, 7 days", "", "down",
     lambda r, x, s: dig(x, "cf_404", "real_total"), "404s on site sections, asset folders and browser auto-files (REAL_RE); probe noise excluded"),
    ("threats_7d", "Site health", "Cloudflare threats blocked, 7 days", "", "flat",
     lambda r, x, s: dig(r, "cloudflare", "rollup_7d", "threats"), ""),
    ("sitemap_errors", "Site health", "Sitemap errors in Search Console", "", "down",
     lambda r, x, s: sum(int(m.get("errors") or 0) for m in (dig(r, "gsc", "sitemaps") or [])) if dig(r, "gsc", "sitemaps") else None, ""),
    # ── what's on the site
    ("inv_entries", "Site inventory", "Entries", "", "up", lambda r, x, s: dig(x, "inventory", "entries"), "site/catalog.json"),
    ("inv_guides", "Site inventory", "Guides", "", "up", lambda r, x, s: dig(x, "inventory", "guides"), "site/guides/*.html"),
    ("inv_hubs_indexed", "Site inventory", "Indexed tool hubs", "", "up", lambda r, x, s: dig(x, "inventory", "hubs_indexed"), ""),
    ("inv_sitemap_urls", "Site inventory", "Sitemap URLs", "", "up", lambda r, x, s: dig(x, "inventory", "sitemap_urls"), ""),
]
HEADLINE = ["visits_7d", "gsc_impr_7d", "gsc_clicks_7d", "indexed_share", "bot_oai_search", "bot_claude",
            "bot_chatgpt_user", "lcp_p75_ms", "go_human_7d"]


# ───────────────────────────────────────────────────────────── collect
def collect(audit_date: str, raw: dict) -> None:
    import analytics_report as A
    extras: dict = {"date": audit_date, "collected_at": dt.datetime.now().isoformat(timespec="seconds"), "errors": {}}

    # Google
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build
        cred = service_account.Credentials.from_service_account_file(
            str(A.GSC_JSON), scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
        svc = build("searchconsole", "v1", credentials=cred, cache_discovery=False)
        prop = raw.get("gsc", {}).get("property") or A.GSC_PROPERTIES[0]
        today = dt.date.today().isoformat()
        rows = svc.searchanalytics().query(siteUrl=prop, body={
            "startDate": SERIES_START, "endDate": today, "dimensions": ["date"], "rowLimit": 500}).execute().get("rows", [])
        series = jload(GSC_DAILY, {}) or {}
        for row in rows:
            series[row["keys"][0]] = {"clicks": row["clicks"], "impressions": row["impressions"],
                                      "position": round(row["position"], 2)}
        GSC_DAILY.write_text(json.dumps(dict(sorted(series.items())), indent=1) + "\n", encoding="utf-8")
        last = max(series) if series else today
        start = (dt.date.fromisoformat(last) - dt.timedelta(days=6)).isoformat()
        prow = svc.searchanalytics().query(siteUrl=prop, body={
            "startDate": start, "endDate": last, "dimensions": ["page"], "rowLimit": 5000}).execute().get("rows", [])
        sec: dict = defaultdict(lambda: {"clicks": 0, "impressions": 0, "pages": 0})
        for row in prow:
            path = re.sub(r"^https?://[^/]+", "", row["keys"][0]) or "/"
            parts = path.strip("/").split("/")
            key = "/" if path == "/" else ("/" + parts[0] + ("/" if len(parts) > 1 else ""))
            sec[key]["clicks"] += row["clicks"]
            sec[key]["impressions"] += row["impressions"]
            sec[key]["pages"] += 1
        extras["gsc_sections"] = {"start": start, "end": last, "pages_with_impressions": len(prow),
                                  "by_section": dict(sorted(sec.items(), key=lambda kv: -kv[1]["impressions"]))}
    except Exception as e:  # pragma: no cover - network
        extras["errors"]["gsc"] = f"{type(e).__name__}: {str(e)[:200]}"

    # Cloudflare 404 paths in the audit's 7-day window
    try:
        env = A.load_env_file(A.CF_ENV)
        tok = env["CLOUDFLARE_API_TOKEN"]
        zone = env.get("CLOUDFLARE_ZONE_ID") or A._cf_request(tok, f"{A.CF_API}/zones?name={A.DOMAIN}")["result"][0]["id"]
        q = ("query($zone:String!,$start:Time!,$end:Time!){viewer{zones(filter:{zoneTag:$zone}){"
             "p:httpRequestsAdaptiveGroups(limit:400,filter:{datetime_geq:$start,datetime_lt:$end,edgeResponseStatus:404},"
             "orderBy:[count_DESC]){count dimensions{clientRequestPath}}}}}")
        c: Counter = Counter()
        for s, e in A._day_windows(7):
            for row in A.cf_gql(tok, q, {"zone": zone, "start": s, "end": e})["viewer"]["zones"][0]["p"]:
                c[row["dimensions"]["clientRequestPath"]] += row["count"]
        real = [(p, n) for p, n in c.most_common() if REAL_RE.search(p) and not SCANNER_RE.search(p)]
        extras["cf_404"] = {"total_sampled": sum(c.values()), "real_total": sum(n for _, n in real),
                            "top_real": [{"path": p, "hits": n} for p, n in real[:25]],
                            "top_all": [{"path": p, "hits": n} for p, n in c.most_common(15)]}
    except Exception as e:  # pragma: no cover - network
        extras["errors"]["cf_404"] = f"{type(e).__name__}: {str(e)[:200]}"

    # inventory
    cat = jload(SITE / "catalog.json", {}) or {}
    tools = list((SITE / "tools").glob("*.html"))
    noindex = re.compile(r'<meta\s+name="robots"\s+content="[^"]*noindex', re.I)
    sm = (SITE / "sitemap.xml").read_text(encoding="utf-8") if (SITE / "sitemap.xml").is_file() else ""
    extras["inventory"] = {
        "entries": len(cat.get("entries", [])),
        "guides": sum(1 for p in (SITE / "guides").glob("*.html") if p.stem != "index"),
        "prompt_systems": len(jload(ROOT / "data" / "prompt_systems.json", {}) or {}),
        "hubs_total": sum(1 for p in tools if p.stem != "index"),
        "hubs_indexed": sum(1 for p in tools if p.stem != "index" and not noindex.search(p.read_text(encoding="utf-8", errors="replace")[:6000])),
        "sitemap_urls": sm.count("<loc>"),
    }
    (DATA / f"{audit_date}.extras.json").write_text(json.dumps(extras, indent=1) + "\n", encoding="utf-8")
    print(f"collected extras -> data/analytics/{audit_date}.extras.json"
          + (f" (errors: {', '.join(extras['errors'])})" if extras["errors"] else ""))


# ───────────────────────────────────────────────────────────── compute
def audits() -> list[tuple[str, dict, dict, Path]]:
    out = []
    for p in sorted(DATA.glob("*.json")):
        m = RAW_RE.match(p.name)
        if m:
            out.append((m.group(1), jload(p, {}), jload(DATA / f"{m.group(1)}.extras.json", {}) or {}, p))
    return out


def fmt(v, unit=""):
    if v is None:
        return "n/a"
    if unit == "%":
        return f"{v * 100:.0f}%"
    if isinstance(v, float) and not v.is_integer():
        return f"{v:,.3f}" if abs(v) < 1 else f"{v:,.1f}"
    return f"{int(v):,}"


def change(a, b, better, unit=""):
    if a is None or b is None:
        return "", ""
    if unit == "%":
        txt = f"{(b - a) * 100:+.0f} pts"
    elif a == 0:
        txt = "new" if b else "="
    else:
        pct = (b - a) / abs(a) * 100
        txt = f"×{b / a:.1f}" if pct >= 200 else f"{pct:+.0f}%"
    good = "" if better == "flat" or b == a else ("good" if (b > a) == (better == "up") else "bad")
    return txt, good


def compute():
    A_ = audits()
    series = jload(GSC_DAILY, {}) or {}
    table = {m[0]: [m[5](r, x, series) for _, r, x, _ in A_] for m in METRICS}
    return A_, series, table


# ───────────────────────────────────────────────────────────── render
def weekly_series(series: dict) -> list[tuple[str, int, float, float]]:
    """ISO weeks (Mon start): (week_start, days_with_data, clicks, impressions)."""
    wk: dict = defaultdict(lambda: [0, 0.0, 0.0])
    for d, row in series.items():
        day = dt.date.fromisoformat(d)
        ws = (day - dt.timedelta(days=day.weekday())).isoformat()
        wk[ws][0] += 1
        wk[ws][1] += row.get("clicks", 0)
        wk[ws][2] += row.get("impressions", 0)
    return [(w, *wk[w]) for w in sorted(wk)]


def render_md(A_, series, table, changes, findings) -> str:
    dates = [a[0] for a in A_]
    first, last = 0, len(dates) - 1
    prev = max(0, last - 1)
    L = ["# DejaViewed growth scorecard", "",
         f"Generated {dt.date.today().isoformat()} by `scripts/analytics_scorecard.py` from {len(dates)} audits "
         f"({', '.join(dates)}). Same metric definitions for every audit; `n/a` = not measured at that audit.",
         "Weekly routine: `python3 scripts/analytics_report.py --inspect 40 && python3 scripts/analytics_scorecard.py`, "
         "then add what you learned to `data/analytics/findings.json` and what shipped to `data/analytics/changes.json`.", "",
         "## Growth at a glance", "",
         f"| metric | first audit ({dates[first]}) | previous ({dates[prev]}) | latest ({dates[last]}) | since first | since previous |",
         "|---|---|---|---|---|---|"]
    meta = {m[0]: m for m in METRICS}
    for k in HEADLINE:
        _, _, label, unit, better, _, _ = meta[k]
        v = table[k]
        c1, g1 = change(v[first], v[last], better, unit)
        c2, g2 = change(v[prev], v[last], better, unit)
        mark = lambda c, g: (c + (" ▲" if g == "good" else " ▼" if g == "bad" else "")) if c else ""
        L.append(f"| {label} | {fmt(v[first], unit)} | {fmt(v[prev], unit)} | {fmt(v[last], unit)} | {mark(c1, g1)} | {mark(c2, g2)} |")
    L += ["", "▲ = moved the good way, ▼ = moved the bad way.", "", "## Every metric, every audit", ""]
    group = None
    for key, grp, label, unit, better, _, defn in METRICS:
        if grp != group:
            group = grp
            L += ["", f"### {grp}", "", "| metric | " + " | ".join(dates) + " | change since first |",
                  "|---|" + "---|" * len(dates) + "---|"]
        v = table[key]
        firstv = next((x for x in v if x is not None), None)
        c, g = change(firstv, v[-1], better, unit)
        L.append(f"| {label} | " + " | ".join(fmt(x, unit) for x in v) + f" | {c}{' ▲' if g == 'good' else ' ▼' if g == 'bad' else ''} |")
    L += ["", "## Google search by week (daily series, backfilled from Search Console)", "",
          "| week starting | days with data | clicks | impressions | clicks per 1,000 impressions |", "|---|---|---|---|---|"]
    for w, n, c, i in weekly_series(series):
        L.append(f"| {w} | {n} | {int(c):,} | {int(i):,} | {(c / i * 1000 if i else 0):.1f} |")
    xl = A_[-1][2] if A_ else {}
    sec = dig(xl, "gsc_sections", "by_section") or {}
    if sec:
        L += ["", f"### Where Google shows us ({dig(xl, 'gsc_sections', 'start')} to {dig(xl, 'gsc_sections', 'end')})", "",
              "| section | pages | impressions | clicks |", "|---|---|---|---|"]
        for s, v in list(sec.items())[:14]:
            L.append(f"| {s} | {v['pages']} | {int(v['impressions']):,} | {int(v['clicks'])} |")
    f404 = dig(xl, "cf_404", "top_real") or []
    if f404:
        L += ["", "### 404s on real-looking paths (latest audit week)", "", "| path | hits |", "|---|---|"]
        L += [f"| `{r['path']}` | {r['hits']} |" for r in f404[:12]]
    L += ["", "## What we shipped (changes log)", "", "| date | change |", "|---|---|"]
    L += [f"| {c['date']} | {c['what']} |" for c in sorted(changes, key=lambda c: c["date"])]
    L += ["", "## Findings and actions", "", "| found | finding | action | status |", "|---|---|---|---|"]
    for f in sorted(findings, key=lambda f: (f.get("status") != "open", f["found"])):
        L.append(f"| {f['found']} | {f['finding']} | {f['action']} | {f['status']}{' (' + f['done'] + ')' if f.get('done') else ''} |")
    L += ["", "## Metric definitions", "", "| key | metric | better | definition |", "|---|---|---|---|"]
    L += [f"| `{k}` | {lbl} | {b} | {d} |" for k, _, lbl, _, b, _, d in METRICS]
    L += ["", "## Verification ledger", "",
          "Every number above is recomputed from these files by `python3 scripts/analytics_scorecard.py --no-collect`.", "",
          "| audit | raw file | sha256 (first 16) | extras file | sha256 (first 16) |", "|---|---|---|---|---|"]
    for d, _, _, p in A_:
        xp = DATA / f"{d}.extras.json"
        L.append(f"| {d} | `{p.relative_to(ROOT)}` | `{sha256(p)}` | " +
                 (f"`{xp.relative_to(ROOT)}` | `{sha256(xp)}` |" if xp.is_file() else "none | |"))
    if GSC_DAILY.is_file():
        L.append(f"\nDaily Google series: `{GSC_DAILY.relative_to(ROOT)}` ({len(series)} days, sha256 `{sha256(GSC_DAILY)}`).")
    return "\n".join(L) + "\n"


def svg_line(points: list[tuple[str, float]], marks: list[tuple[str, str]], w=760, h=200, color="#a78bfa", label="") -> str:
    if not points:
        return ""
    xs = [dt.date.fromisoformat(d).toordinal() for d, _ in points]
    x0, x1 = min(xs), max(xs) or 1
    ymax = max(v for _, v in points) or 1
    px = lambda d: 40 + (dt.date.fromisoformat(d).toordinal() - x0) / max(1, x1 - x0) * (w - 60)
    py = lambda v: h - 24 - v / ymax * (h - 44)
    path = " ".join(("M" if i == 0 else "L") + f"{px(d):.1f},{py(v):.1f}" for i, (d, v) in enumerate(points))
    out = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{html.escape(label)}" class="chart">',
           f'<line x1="40" y1="{h - 24}" x2="{w - 20}" y2="{h - 24}" class="axis"/>',
           f'<text x="36" y="{py(ymax) + 4:.0f}" class="tick" text-anchor="end">{ymax:,.0f}</text>',
           f'<text x="36" y="{h - 20}" class="tick" text-anchor="end">0</text>']
    for d, what in marks:
        if x0 <= dt.date.fromisoformat(d).toordinal() <= x1:
            x = px(d)
            out.append(f'<line x1="{x:.1f}" y1="14" x2="{x:.1f}" y2="{h - 24}" class="mark"><title>{html.escape(d + ": " + what)}</title></line>')
    out.append(f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2.2"/>')
    for d, v in points:
        out.append(f'<circle cx="{px(d):.1f}" cy="{py(v):.1f}" r="2.6" fill="{color}"><title>{d}: {v:,.0f}</title></circle>')
    out.append(f'<text x="40" y="{h - 6}" class="tick">{points[0][0]}</text>'
               f'<text x="{w - 20}" y="{h - 6}" class="tick" text-anchor="end">{points[-1][0]}</text></svg>')
    return "".join(out)


def md_to_html_tables(md: str) -> str:
    """Tiny renderer for the subset of markdown this script emits (headings, paragraphs, tables, code)."""
    out, rows = [], []

    def inline(t):
        t = html.escape(t)
        t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
        t = t.replace("▲", '<span class="good">▲</span>').replace("▼", '<span class="bad">▼</span>')
        return t

    def flush():
        if rows:
            head, body = rows[0], rows[2:]
            out.append("<div class=\"tw\"><table><thead><tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) +
                       "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>" for r in body) +
                       "</tbody></table></div>")
            rows.clear()
    for line in md.splitlines():
        if line.startswith("|"):
            rows.append([c.strip() for c in line.strip().strip("|").split("|")])
            continue
        flush()
        if line.startswith("### "):
            out.append(f"<h3>{inline(line[4:])}</h3>")
        elif line.startswith("## "):
            out.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("# "):
            continue
        elif line.strip():
            out.append(f"<p>{inline(line)}</p>")
    flush()
    return "\n".join(out)


def render_html(md: str, A_, series, table, changes) -> str:
    marks = [(c["date"], c["what"]) for c in changes]
    imp = [(d, r["impressions"]) for d, r in sorted(series.items())]
    clk = [(d, r["clicks"]) for d, r in sorted(series.items())]
    vis = [(a[0], v) for a, v in zip(A_, table["visits_7d"]) if v is not None]
    oai = [(a[0], (v or 0) + (w or 0) + (z or 0)) for a, v, w, z in zip(A_, table["bot_oai_search"], table["bot_claude"], table["bot_chatgpt_user"])]
    charts = (
        "<section class=\"charts\">"
        f"<figure><figcaption>Google impressions per day (vertical lines = changes shipped; hover for what)</figcaption>{svg_line(imp, marks, label='Google impressions per day')}</figure>"
        f"<figure><figcaption>Google clicks per day</figcaption>{svg_line(clk, marks, color='#4cda8c', label='Google clicks per day')}</figure>"
        f"<figure><figcaption>Real visits per 7 days, by audit</figcaption>{svg_line(vis, marks, color='#f472b6', label='Real visits per week')}</figure>"
        f"<figure><figcaption>Answer-engine hits per 7 days (OpenAI search + ClaudeBot + ChatGPT live), by audit</figcaption>{svg_line(oai, marks, color='#fbbf24', label='Answer engine hits per week')}</figure>"
        "</section>")
    body = md_to_html_tables(md)
    first_h2 = body.find("<h2>")
    intro, rest = body[:first_h2], body[first_h2:]
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>DejaViewed Growth Scorecard</title>
<style>
:root{{--bg:#0a0a0f;--panel:#12121a;--text:#e8e8f0;--dim:#a0a0b8;--mute:#6a6a80;--border:rgba(255,255,255,.1);--accent:#a78bfa;--good:#4cda8c;--bad:#f87171}}
@media (prefers-color-scheme: light){{:root:not([data-theme="dark"]){{--bg:#fafafb;--panel:#fff;--text:#16161d;--dim:#4a4a5a;--mute:#7a7a8a;--border:rgba(0,0,0,.12);--accent:#6d4ed8;--good:#118a4a;--bad:#c62828}}}}
body{{margin:0;background:var(--bg);color:var(--text);font:15px/1.55 Inter,system-ui,sans-serif}}
main{{max-width:1100px;margin:0 auto;padding:28px 16px 60px}}
h1{{font-size:28px;margin:0 0 6px;letter-spacing:-.02em}}h2{{margin:34px 0 10px;font-size:19px}}h3{{margin:22px 0 8px;font-size:15px;color:var(--dim)}}
p{{color:var(--dim);margin:6px 0}}code{{font:12px 'JetBrains Mono',ui-monospace,monospace;color:var(--text)}}
.tw{{overflow-x:auto;border:1px solid var(--border);border-radius:10px;background:var(--panel);margin:8px 0}}
table{{border-collapse:collapse;width:100%;font-size:13px}}th,td{{padding:7px 10px;border-bottom:1px solid var(--border);text-align:left;white-space:nowrap}}
th{{font-size:11px;text-transform:uppercase;letter-spacing:.05em;color:var(--mute)}}td:first-child{{white-space:normal;min-width:220px}}
.good{{color:var(--good)}}.bad{{color:var(--bad)}}
.charts{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,500px),1fr));gap:14px;margin:18px 0}}
figure{{margin:0;padding:12px;border:1px solid var(--border);border-radius:10px;background:var(--panel)}}figcaption{{font-size:12px;color:var(--mute);margin-bottom:6px}}
.chart{{width:100%;height:auto}}.axis{{stroke:var(--border)}}.mark{{stroke:var(--accent);stroke-opacity:.35;stroke-dasharray:3 3}}.tick{{fill:var(--mute);font-size:10px}}
</style></head><body><main>
<h1>DejaViewed growth scorecard</h1>
{intro}{charts}{rest}
</main></body></html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-collect", action="store_true", help="render only; no network")
    args = ap.parse_args()
    A_ = audits()
    if not A_:
        print("no audits in data/analytics/ — run scripts/analytics_report.py first")
        return 1
    if not args.no_collect:
        collect(A_[-1][0], A_[-1][1])
    A_, series, table = compute()
    changes = jload(CHANGES, []) or []
    findings = jload(FINDINGS, []) or []
    md = render_md(A_, series, table, changes, findings)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(md, encoding="utf-8")
    OUT_HTML.write_text(render_html(md, A_, series, table, changes), encoding="utf-8")
    print(f"scorecard: {len(A_)} audits, {len(METRICS)} metrics, {len(series)} Google days -> "
          f"{OUT_MD.relative_to(ROOT)}, {OUT_HTML.relative_to(ROOT)}")
    meta = {m[0]: m for m in METRICS}
    for k in HEADLINE:
        v = table[k]
        print(f"  {meta[k][2]:<52} " + "  ".join(f"{a[0]}={fmt(x, meta[k][3])}" for a, x in zip(A_, v)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
