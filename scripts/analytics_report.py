#!/usr/bin/env python3
"""dejaviewed.dev analytics report: Cloudflare (GraphQL) + Google Search Console.

Runs the moment credentials exist; until then, prints precise
"missing: <what> -- do: <step>" lines and exits 0.

SECURITY: secret values are read from file at call time, used only in an
HTTP header / credentials object, and NEVER printed, logged, or written.
Only existence and file-mode checks are ever reported.

Credentials:
  ~/.config/cloudflare/dejaviewed.env   (mode 600)  KEY=VALUE lines:
      CLOUDFLARE_API_TOKEN=...            (required)
      CLOUDFLARE_ZONE_ID=...              (optional, looked up by name)
      CLOUDFLARE_ACCOUNT_ID=...           (optional, taken from the zone)
  ~/.config/google/dejaviewed-gsc.json  (mode 600)  service-account key

Outputs:
  data/analytics/<YYYY-MM-DD>.json   raw aggregated numbers
  reports/analytics_<YYYY-MM-DD>.md  tables + deltas vs previous JSON

Usage:
  python3 scripts/analytics_report.py            # live run
  python3 scripts/analytics_report.py --dry-run  # show queries, no network
  python3 scripts/analytics_report.py --only cf|gsc
  python3 scripts/analytics_report.py --inspect 20   # GSC URL-inspection sample size

Setup steps: data/analytics/SETUP.md
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import stat
import sys
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "analytics"
REPORT_DIR = ROOT / "reports"
SITEMAP = ROOT / "site" / "sitemap.xml"
SETUP = "data/analytics/SETUP.md"

DOMAIN = "dejaviewed.dev"
CF_ENV = Path.home() / ".config" / "cloudflare" / "dejaviewed.env"
GSC_JSON = Path.home() / ".config" / "google" / "dejaviewed-gsc.json"
GSC_PROPERTIES = ["sc-domain:dejaviewed.dev", "https://dejaviewed.dev/"]
CF_API = "https://api.cloudflare.com/client/v4"
CF_GQL = CF_API + "/graphql"

# Order matters: first match wins (Claude-Web before ClaudeBot etc. are distinct tokens anyway).
AI_CRAWLERS = [
    ("GPTBot", r"gptbot"),
    ("ChatGPT-User", r"chatgpt-user"),
    ("OAI-SearchBot", r"oai-searchbot"),
    ("ClaudeBot", r"claudebot"),
    ("Claude-Web", r"claude-web"),
    ("Claude-User", r"claude-user"),
    ("Claude-SearchBot", r"claude-searchbot"),
    ("anthropic-ai", r"anthropic-ai"),
    ("PerplexityBot", r"perplexitybot"),
    ("Perplexity-User", r"perplexity-user"),
    ("Google-Extended", r"google-extended"),
    ("Googlebot", r"googlebot|google-inspectiontool|storebot-google"),
    ("Bingbot", r"bingbot|bingpreview"),
    ("CCBot", r"ccbot"),
    ("Bytespider", r"bytespider"),
    ("Amazonbot", r"amazonbot"),
    ("Applebot", r"applebot"),
    ("meta-externalagent", r"meta-externalagent|meta-externalfetcher|facebookexternalhit"),
    ("YandexBot", r"yandex"),
    ("DuckDuckBot", r"duckduckbot|duckassistbot"),
    ("cohere-ai", r"cohere-ai|cohere-training"),
    ("Diffbot", r"diffbot"),
    ("scanner", r"scanner|scan/|l9scan|leakix|nuclei|zgrab|masscan|nmap|censys|shodan|^https?://|wp-admin|wp-login|install\.php"),
    ("other-bot", r"bot|crawler|spider|scrape|curl/|wget/|python-requests|python-urllib|httpx|go-http-client|axios|node-fetch|headless|^mozilla/5\.0 \(windows nt 10\.0; win64; x64\) applewebkit/537\.36$"),
]
_AI_RE = [(n, re.compile(p, re.I)) for n, p in AI_CRAWLERS]

# Paths whose crawler hits we track explicitly.
PATH_BUCKETS = [
    ("/api/", lambda p: p.startswith("/api/")),
    ("/llms.txt", lambda p: p == "/llms.txt"),
    ("/llms-full.txt", lambda p: p == "/llms-full.txt"),
    ("/prompts", lambda p: p.startswith("/prompts")),
    ("/guides/*", lambda p: p.startswith("/guides/")),
    ("/robots.txt", lambda p: p == "/robots.txt"),
    ("/sitemap.xml", lambda p: p == "/sitemap.xml"),
]

MISSING: list[str] = []


def missing(what: str, do: str) -> None:
    line = f"missing: {what} -- do: {do}"
    MISSING.append(line)
    print(line)


def classify_ua(ua: str) -> str:
    ua = ua or ""
    for name, rx in _AI_RE:
        if rx.search(ua):
            return name
    return "human/browser" if ua else "empty-UA"


# ---------------------------------------------------------------- secrets
def mode_ok(path: Path) -> bool:
    return stat.S_IMODE(path.stat().st_mode) == 0o600


def load_env_file(path: Path) -> dict[str, str]:
    """Parse KEY=VALUE lines. Values are returned to the caller only; never printed."""
    out: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[7:]
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


# ---------------------------------------------------------------- cloudflare
class CFError(Exception):
    pass


def _cf_request(token: str, url: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if body is not None else "GET")
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        # Body is Cloudflare's JSON error; it never echoes the token.
        try:
            detail = json.loads(e.read().decode())
            msgs = [x.get("message", "") for x in detail.get("errors", [])] or [str(detail)[:300]]
        except Exception:
            msgs = [f"HTTP {e.code}"]
        raise CFError(f"HTTP {e.code}: " + "; ".join(msgs)) from None
    except urllib.error.URLError as e:
        raise CFError(f"network: {e.reason}") from None


def cf_gql(token: str, query: str, variables: dict) -> dict:
    res = _cf_request(token, CF_GQL, {"query": query, "variables": variables})
    if res.get("errors"):
        raise CFError("; ".join(e.get("message", str(e)) for e in res["errors"])[:600])
    return res.get("data") or {}


Q_ZONE_1D = """
query($zone: String!, $since: Date!, $until: Date!) {
  viewer { zones(filter: {zoneTag: $zone}) {
    httpRequests1dGroups(limit: 100, filter: {date_geq: $since, date_leq: $until}, orderBy: [date_ASC]) {
      dimensions { date }
      sum {
        requests bytes cachedRequests cachedBytes pageViews threats
        responseStatusMap { edgeResponseStatus requests }
        countryMap { clientCountryName requests threats }
      }
      uniq { uniques }
    }
  } }
}"""

# Adaptive (sampled) dataset. One query per UTC day because free/pro plans cap
# the per-query time range (commonly 1 day) and the lookback window.
Q_ZONE_ADAPTIVE_DAY = """
query($zone: String!, $start: Time!, $end: Time!) {
  viewer { zones(filter: {zoneTag: $zone}) {
    total: httpRequestsAdaptiveGroups(limit: 1, filter: {datetime_geq: $start, datetime_lt: $end}) {
      count sum { edgeResponseBytes visits }
    }
    byPath: httpRequestsAdaptiveGroups(limit: 200, filter: {datetime_geq: $start, datetime_lt: $end}, orderBy: [count_DESC]) {
      count dimensions { clientRequestHTTPHost clientRequestPath }
    }
    byUA: httpRequestsAdaptiveGroups(limit: 500, filter: {datetime_geq: $start, datetime_lt: $end}, orderBy: [count_DESC]) {
      count dimensions { userAgent }
    }
    byUAPath: httpRequestsAdaptiveGroups(limit: 5000, filter: {datetime_geq: $start, datetime_lt: $end}, orderBy: [count_DESC]) {
      count dimensions { userAgent clientRequestPath }
    }
    byStatus: httpRequestsAdaptiveGroups(limit: 50, filter: {datetime_geq: $start, datetime_lt: $end}, orderBy: [count_DESC]) {
      count dimensions { edgeResponseStatus cacheStatus }
    }
  } }
}"""

# Bot-management fields: usually Enterprise / Bot Management only. Isolated so
# a schema/permission error here does not kill the rest.  [UNVERIFIED FIELDS]
Q_ZONE_BOTS_DAY = """
query($zone: String!, $start: Time!, $end: Time!) {
  viewer { zones(filter: {zoneTag: $zone}) {
    httpRequestsAdaptiveGroups(limit: 200, filter: {datetime_geq: $start, datetime_lt: $end}, orderBy: [count_DESC]) {
      count dimensions { botScoreSrcName verifiedBotCategory }
    }
  } }
}"""

# Web Analytics (RUM). Account-scoped.  [UNVERIFIED: dimension names requestHost/requestPath/countryName]
Q_RUM = """
query($acct: String!, $since: Date!, $until: Date!) {
  viewer { accounts(filter: {accountTag: $acct}) {
    total: rumPageloadEventsAdaptiveGroups(limit: 100, filter: {date_geq: $since, date_leq: $until}) {
      count sum { visits } dimensions { requestHost }
    }
    pages: rumPageloadEventsAdaptiveGroups(limit: 500, filter: {date_geq: $since, date_leq: $until}, orderBy: [count_DESC]) {
      count sum { visits } dimensions { requestHost requestPath }
    }
    countries: rumPageloadEventsAdaptiveGroups(limit: 300, filter: {date_geq: $since, date_leq: $until}, orderBy: [count_DESC]) {
      count dimensions { requestHost countryName }
    }
  } }
}"""

# [UNVERIFIED: dataset rumWebVitalsEventsAdaptiveGroups and quantile field names]
Q_RUM_VITALS = """
query($acct: String!, $since: Date!, $until: Date!) {
  viewer { accounts(filter: {accountTag: $acct}) {
    rumWebVitalsEventsAdaptiveGroups(limit: 200, filter: {date_geq: $since, date_leq: $until}) {
      count dimensions { requestHost }
      quantiles {
        largestContentfulPaintP50 largestContentfulPaintP75
        cumulativeLayoutShiftP50 cumulativeLayoutShiftP75
        interactionToNextPaintP75 firstContentfulPaintP75
      }
    }
  } }
}"""


def _day_windows(days: int) -> list[tuple[str, str]]:
    today = dt.datetime.now(dt.timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    out = []
    for i in range(days, 0, -1):
        s = today - dt.timedelta(days=i)
        e = s + dt.timedelta(days=1)
        out.append((s.strftime("%Y-%m-%dT%H:%M:%SZ"), e.strftime("%Y-%m-%dT%H:%M:%SZ")))
    return out


def _date_range(days: int) -> tuple[str, str]:
    today = dt.datetime.now(dt.timezone.utc).date()
    return str(today - dt.timedelta(days=days)), str(today - dt.timedelta(days=1))


def cf_collect(dry: bool) -> dict | None:
    if not CF_ENV.exists():
        missing(f"Cloudflare credential file {CF_ENV}",
                f"create an API token (Account Analytics:Read, Zone Analytics:Read, Zone:Read), "
                f"save 'CLOUDFLARE_API_TOKEN=<token>' in that file, then 'chmod 600 {CF_ENV}' -- see {SETUP} steps 2-3")
        return None
    if not mode_ok(CF_ENV):
        missing(f"safe permissions on {CF_ENV} (is {oct(stat.S_IMODE(CF_ENV.stat().st_mode))})",
                f"chmod 600 {CF_ENV}   (refusing to read it until then)")
        return {"refused": True}
    env = load_env_file(CF_ENV)
    token = env.get("CLOUDFLARE_API_TOKEN", "")
    if not token:
        missing(f"CLOUDFLARE_API_TOKEN line in {CF_ENV}",
                f"add a line 'CLOUDFLARE_API_TOKEN=<token>' -- see {SETUP} step 2")
        return None
    zone = env.get("CLOUDFLARE_ZONE_ID", "")
    acct = env.get("CLOUDFLARE_ACCOUNT_ID", "")
    print(f"cloudflare: token present (value hidden); zone id {'set' if zone else 'not set -> lookup'}; "
          f"account id {'set' if acct else 'not set -> from zone'}")

    if dry:
        print(f"  [dry-run] GET {CF_API}/zones?name={DOMAIN}  (only if zone id not set)")
        print("  [dry-run] GraphQL httpRequests1dGroups: last 7d and 28d (requests, bytes, cache, status, countries, uniques)")
        print("  [dry-run] GraphQL httpRequestsAdaptiveGroups per UTC day x7: totals, top paths, top UAs, UA x path, status x cache")
        print("  [dry-run] GraphQL httpRequestsAdaptiveGroups bot fields (botScoreSrcName, verifiedBotCategory) x7")
        print("  [dry-run] GraphQL rumPageloadEventsAdaptiveGroups + rumWebVitalsEventsAdaptiveGroups: 7d and 28d")
        return None

    out: dict = {"errors": {}}
    try:
        if not zone or not acct:
            res = _cf_request(token, f"{CF_API}/zones?name={DOMAIN}")
            zs = res.get("result") or []
            if not zs:
                raise CFError(f"zone {DOMAIN} not visible to this token (needs Zone:Read on it)")
            zone = zone or zs[0]["id"]
            acct = acct or (zs[0].get("account") or {}).get("id", "")
    except CFError as e:
        out["errors"]["zone_lookup"] = str(e)
        missing(f"a working Cloudflare token with Zone:Read on {DOMAIN} (API said: {e})",
                f"re-create the token with the three read permissions and replace the CLOUDFLARE_API_TOKEN line "
                f"in {CF_ENV} -- see {SETUP} step 2")
        out["failed"] = True
        return out
    out["zone_id_found"] = bool(zone)
    out["account_id_found"] = bool(acct)

    # ---- 1d rollups (non-sampled; long range OK on all plans)
    for days in (7, 28):
        since, until = _date_range(days)
        try:
            d = cf_gql(token, Q_ZONE_1D, {"zone": zone, "since": since, "until": until})
            rows = d["viewer"]["zones"][0]["httpRequests1dGroups"]
            agg = Counter()
            status, country = Counter(), Counter()
            uniques = 0
            for r in rows:
                s = r["sum"]
                for k in ("requests", "bytes", "cachedRequests", "cachedBytes", "pageViews", "threats"):
                    agg[k] += s.get(k) or 0
                for m in s.get("responseStatusMap") or []:
                    status[str(m["edgeResponseStatus"])] += m["requests"]
                for m in s.get("countryMap") or []:
                    country[m["clientCountryName"]] += m["requests"]
                uniques += (r.get("uniq") or {}).get("uniques") or 0
            out[f"rollup_{days}d"] = {
                "since": since, "until": until, "days_returned": len(rows),
                **agg, "uniques_sum_of_daily": uniques,
                "cache_ratio": round(agg["cachedRequests"] / agg["requests"], 4) if agg["requests"] else None,
                "status": dict(status.most_common()), "countries": dict(country.most_common(30)),
                "daily": [{"date": r["dimensions"]["date"], "requests": r["sum"]["requests"],
                           "pageViews": r["sum"]["pageViews"]} for r in rows],
            }
        except (CFError, KeyError, IndexError, TypeError) as e:
            out["errors"][f"rollup_{days}d"] = str(e)
            print(f"  cloudflare rollup {days}d failed: {e}")

    # ---- adaptive per-day (sampled; counts are estimates)
    tot = Counter()
    paths, uas, status_cache = Counter(), Counter(), Counter()
    ua_path = Counter()
    days_ok, day_errs = [], []
    for start, end in _day_windows(7):
        try:
            d = cf_gql(token, Q_ZONE_ADAPTIVE_DAY, {"zone": zone, "start": start, "end": end})
            z = d["viewer"]["zones"][0]
            for r in z["total"]:
                tot["requests"] += r["count"]
                tot["bytes"] += r["sum"]["edgeResponseBytes"] or 0
                tot["visits"] += r["sum"]["visits"] or 0
            for r in z["byPath"]:
                paths[(r["dimensions"]["clientRequestHTTPHost"], r["dimensions"]["clientRequestPath"])] += r["count"]
            for r in z["byUA"]:
                uas[r["dimensions"]["userAgent"]] += r["count"]
            for r in z["byUAPath"]:
                ua_path[(r["dimensions"]["userAgent"], r["dimensions"]["clientRequestPath"])] += r["count"]
            for r in z["byStatus"]:
                status_cache[(str(r["dimensions"]["edgeResponseStatus"]), r["dimensions"]["cacheStatus"])] += r["count"]
            days_ok.append(start[:10])
        except (CFError, KeyError, IndexError, TypeError) as e:
            day_errs.append(f"{start[:10]}: {e}")
    if day_errs:
        out["errors"]["adaptive_days"] = day_errs
        print(f"  cloudflare adaptive: {len(day_errs)} day(s) failed (first: {day_errs[0][:200]})")
    if days_ok:
        crawler_hits = Counter()
        crawler_paths: dict[str, Counter] = defaultdict(Counter)
        for ua, n in uas.items():
            crawler_hits[classify_ua(ua)] += n
        for (ua, p), n in ua_path.items():
            c = classify_ua(ua)
            for bucket, fn in PATH_BUCKETS:
                if fn(p or ""):
                    crawler_paths[c][bucket] += n
        human = crawler_hits.get("human/browser", 0)
        total_ua = sum(crawler_hits.values())
        out["adaptive_7d"] = {
            "days": days_ok, "sampled": True, **tot,
            "top_paths": [{"host": h, "path": p, "requests": n} for (h, p), n in paths.most_common(30)],
            "top_user_agents": [{"ua": u[:200], "class": classify_ua(u), "requests": n} for u, n in uas.most_common(30)],
            "crawlers": dict(crawler_hits.most_common()),
            "crawler_paths": {c: dict(v) for c, v in crawler_paths.items()},
            "human_share_by_ua": round(human / total_ua, 4) if total_ua else None,
            "status_cache": [{"status": s, "cache": c, "requests": n} for (s, c), n in status_cache.most_common(40)],
            "note": "top-N per day merged; UA/path tables cover the top 500 UAs / 5000 UA-path pairs per day",
        }

    # ---- bot-management fields (optional)
    bots = Counter()
    bot_err = None
    for start, end in _day_windows(7):
        try:
            d = cf_gql(token, Q_ZONE_BOTS_DAY, {"zone": zone, "start": start, "end": end})
            for r in d["viewer"]["zones"][0]["httpRequestsAdaptiveGroups"]:
                dm = r["dimensions"]
                bots[f"{dm.get('botScoreSrcName') or '-'} | {dm.get('verifiedBotCategory') or '-'}"] += r["count"]
        except (CFError, KeyError, IndexError, TypeError) as e:
            bot_err = str(e)
            break
    if bot_err:
        out["errors"]["bot_fields"] = bot_err + " (bot-management fields are often Enterprise-only; UA classification used instead)"
    else:
        out["bot_fields_7d"] = dict(bots.most_common())

    # ---- Web Analytics (RUM)
    if not acct:
        out["errors"]["rum"] = "account id unknown (set CLOUDFLARE_ACCOUNT_ID or give token Zone:Read)"
    else:
        for days in (7, 28):
            since, until = _date_range(days)
            try:
                d = cf_gql(token, Q_RUM, {"acct": acct, "since": since, "until": until})
                a = d["viewer"]["accounts"][0]
                mine = lambda r: (r["dimensions"].get("requestHost") or "").endswith(DOMAIN)
                total = [r for r in a["total"] if mine(r)]
                rum = {
                    "pageviews": sum(r["count"] for r in total),
                    "visits": sum(r["sum"]["visits"] for r in total),
                    "top_pages": [{"path": r["dimensions"]["requestPath"], "pageviews": r["count"],
                                   "visits": r["sum"]["visits"]} for r in a["pages"] if mine(r)][:30],
                }
                cc = Counter()
                for r in a["countries"]:
                    if mine(r):
                        cc[r["dimensions"]["countryName"]] += r["count"]
                rum["countries"] = dict(cc.most_common(20))
                rum["has_data"] = rum["pageviews"] > 0
                out[f"rum_{days}d"] = rum
            except (CFError, KeyError, IndexError, TypeError) as e:
                out["errors"][f"rum_{days}d"] = str(e)
            try:
                d = cf_gql(token, Q_RUM_VITALS, {"acct": acct, "since": since, "until": until})
                rows = [r for r in d["viewer"]["accounts"][0]["rumWebVitalsEventsAdaptiveGroups"]
                        if (r["dimensions"].get("requestHost") or "").endswith(DOMAIN)]
                if rows:
                    r = max(rows, key=lambda x: x["count"])
                    out[f"vitals_{days}d"] = {"samples": r["count"], **r["quantiles"]}
            except (CFError, KeyError, IndexError, TypeError) as e:
                out["errors"][f"vitals_{days}d"] = str(e)
        if not (out.get("rum_7d") or {}).get("has_data"):
            out["rum_hint"] = ("no Web Analytics page-loads -- enable Cloudflare Web Analytics for the Pages "
                               f"project with automatic injection ({SETUP} step 1)")
    for k, v in out["errors"].items():
        if k != "adaptive_days":
            print(f"  cloudflare {k}: {str(v)[:240]}")
    return out


# ---------------------------------------------------------------- search console
def gsc_collect(dry: bool, inspect_n: int) -> dict | None:
    if not GSC_JSON.exists():
        missing(f"Google Search Console service-account key {GSC_JSON}",
                f"verify the domain property in Search Console, create a service account with the Search Console API "
                f"enabled, download its JSON key to that path, 'chmod 600 {GSC_JSON}', add the service-account email "
                f"as a Full user on the property -- see {SETUP} steps 4-8")
        return None
    if not mode_ok(GSC_JSON):
        missing(f"safe permissions on {GSC_JSON} (is {oct(stat.S_IMODE(GSC_JSON.stat().st_mode))})",
                f"chmod 600 {GSC_JSON}   (refusing to read it until then)")
        return {"refused": True}
    try:
        from google.oauth2 import service_account  # noqa
        from googleapiclient.discovery import build  # noqa
    except ImportError:
        missing("python packages google-api-python-client + google-auth",
                "pip install --user google-api-python-client google-auth")
        return None
    print("search console: key file present (contents hidden), libraries present")
    if dry:
        print(f"  [dry-run] searchanalytics.query on {GSC_PROPERTIES[0]} (fallback {GSC_PROPERTIES[1]}): "
              "28d totals, top 50 queries, top 50 pages")
        print(f"  [dry-run] sitemaps.list; urlInspection.index.inspect on {inspect_n} sitemap URLs")
        return None

    from google.oauth2 import service_account
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError

    out: dict = {"errors": {}}
    creds = service_account.Credentials.from_service_account_file(
        str(GSC_JSON), scopes=["https://www.googleapis.com/auth/webmasters.readonly"])
    svc = build("searchconsole", "v1", credentials=creds, cache_discovery=False)

    today = dt.date.today()
    end = today - dt.timedelta(days=3)  # GSC data lags ~2-3 days
    start = end - dt.timedelta(days=27)
    prop = None
    for p in GSC_PROPERTIES:
        try:
            body = {"startDate": str(start), "endDate": str(end), "rowLimit": 1}
            tot = svc.searchanalytics().query(siteUrl=p, body=body).execute()
            prop = p
            break
        except HttpError as e:
            out["errors"][f"property {p}"] = f"HTTP {e.resp.status}: {e._get_reason()[:200]}"
    if not prop:
        missing("Search Console access for the service account",
                f"in Search Console > Settings > Users and permissions, add the service-account email as Full user "
                f"on {GSC_PROPERTIES[0]} -- see {SETUP} step 8")
        out["failed"] = True
        return out
    out["property"] = prop
    out["window"] = {"start": str(start), "end": str(end)}
    try:
        t = svc.searchanalytics().query(siteUrl=prop, body={"startDate": str(start), "endDate": str(end)}).execute()
        row = (t.get("rows") or [{}])[0]
        out["totals_28d"] = {k: row.get(k, 0) for k in ("clicks", "impressions", "ctr", "position")}
        for dim in ("query", "page"):
            r = svc.searchanalytics().query(siteUrl=prop, body={
                "startDate": str(start), "endDate": str(end), "dimensions": [dim], "rowLimit": 50}).execute()
            out[f"top_{dim}s"] = [{dim: x["keys"][0], "clicks": x["clicks"], "impressions": x["impressions"],
                                   "ctr": round(x["ctr"], 4), "position": round(x["position"], 1)}
                                  for x in r.get("rows", [])]
    except HttpError as e:
        out["errors"]["searchanalytics"] = f"HTTP {e.resp.status}: {e._get_reason()[:200]}"
    try:
        sm = svc.sitemaps().list(siteUrl=prop).execute()
        out["sitemaps"] = [{"path": s.get("path"), "lastSubmitted": s.get("lastSubmitted"),
                            "lastDownloaded": s.get("lastDownloaded"), "isPending": s.get("isPending"),
                            "errors": s.get("errors"), "warnings": s.get("warnings"),
                            "contents": s.get("contents")} for s in sm.get("sitemap", [])]
        if not out["sitemaps"]:
            out["sitemaps_hint"] = f"no sitemap submitted -- Search Console > Sitemaps > add 'sitemap.xml' ({SETUP} step 9)"
    except HttpError as e:
        out["errors"]["sitemaps"] = f"HTTP {e.resp.status}: {e._get_reason()[:200]}"

    # Index coverage: the Coverage/Pages report has no API. URL Inspection
    # (2000/day quota) gives per-URL verdicts; we sample the first N sitemap URLs.
    if inspect_n > 0 and SITEMAP.exists():
        urls = re.findall(r"<loc>([^<]+)</loc>", SITEMAP.read_text())[:inspect_n]
        verdicts, states, samples = Counter(), Counter(), []
        for u in urls:
            try:
                r = svc.urlInspection().index().inspect(body={"inspectionUrl": u, "siteUrl": prop}).execute()
                ir = r.get("inspectionResult", {}).get("indexStatusResult", {})
                verdicts[ir.get("verdict", "?")] += 1
                states[ir.get("coverageState", "?")] += 1
                samples.append({"url": u, "verdict": ir.get("verdict"), "coverageState": ir.get("coverageState"),
                                "lastCrawlTime": ir.get("lastCrawlTime")})
            except HttpError as e:
                out["errors"]["urlInspection"] = f"HTTP {e.resp.status}: {e._get_reason()[:200]}"
                break
        out["index_coverage_sample"] = {"inspected": len(samples), "verdicts": dict(verdicts),
                                        "coverageStates": dict(states), "urls": samples}
    for k, v in out["errors"].items():
        print(f"  search console {k}: {v}")
    return out


# ---------------------------------------------------------------- report
def _fmt(n) -> str:
    if n is None:
        return "-"
    if isinstance(n, float):
        return f"{n:,.4f}" if abs(n) < 1 else f"{n:,.1f}"
    return f"{n:,}" if isinstance(n, int) else str(n)


def _table(headers: list[str], rows: list[list]) -> str:
    if not rows:
        return "_no rows_\n"
    s = "| " + " | ".join(headers) + " |\n|" + "---|" * len(headers) + "\n"
    for r in rows:
        s += "| " + " | ".join(_fmt(c).replace("|", "\\|") for c in r) + " |\n"
    return s


def _delta_metrics(d: dict) -> dict[str, float]:
    m = {}
    cf = d.get("cloudflare") or {}
    for k in ("rollup_7d", "rollup_28d"):
        for f in ("requests", "pageViews", "bytes", "cache_ratio", "uniques_sum_of_daily"):
            v = (cf.get(k) or {}).get(f)
            if v is not None:
                m[f"cf.{k}.{f}"] = v
    for c, n in ((cf.get("adaptive_7d") or {}).get("crawlers") or {}).items():
        m[f"cf.crawler7d.{c}"] = n
    for k in ("rum_7d", "rum_28d"):
        for f in ("pageviews", "visits"):
            v = (cf.get(k) or {}).get(f)
            if v is not None:
                m[f"cf.{k}.{f}"] = v
    g = (d.get("gsc") or {}).get("totals_28d") or {}
    for f, v in g.items():
        m[f"gsc.28d.{f}"] = v
    return m


def render_md(d: dict, prev: tuple[str, dict] | None) -> str:
    L = [f"# dejaviewed.dev analytics -- {d['date']}\n",
         f"Generated {d['generated_at']} by `scripts/analytics_report.py`. Raw numbers: `data/analytics/{d['date']}.json`.\n"]
    if d.get("missing"):
        L.append("## Missing setup\n")
        L += [f"- {m}" for m in d["missing"]]
        L.append("")
    cf = d.get("cloudflare") or {}
    if cf:
        L.append("## Traffic (Cloudflare, edge)\n")
        rows = []
        for k in ("rollup_7d", "rollup_28d"):
            r = cf.get(k)
            if r:
                rows.append([k.split("_")[1], r["requests"], r["pageViews"], r["uniques_sum_of_daily"],
                             round(r["bytes"] / 1e6, 1), r["cache_ratio"], r["threats"]])
        L.append(_table(["window", "requests", "page views (edge)", "uniques (sum of daily)", "MB served",
                         "cache ratio", "threats"], rows))
        r28 = cf.get("rollup_28d") or cf.get("rollup_7d")
        if r28:
            L.append("### Status codes ({}d)\n".format(28 if cf.get("rollup_28d") else 7))
            L.append(_table(["status", "requests"], [[k, v] for k, v in r28["status"].items()]))
            L.append("### Countries (edge requests, top 15)\n")
            L.append(_table(["country", "requests"], list(r28["countries"].items())[:15]))
        a = cf.get("adaptive_7d")
        if a:
            L.append(f"### Top pages (7d, sampled; days: {len(a['days'])})\n")
            L.append(_table(["host", "path", "requests"], [[x["host"], x["path"], x["requests"]] for x in a["top_paths"]]))
            L.append(f"### Human vs bot (7d, by user-agent class)\n\nHuman/browser share of requests: "
                     f"**{_fmt(a['human_share_by_ua'])}**\n")
            if cf.get("bot_fields_7d"):
                L.append("Cloudflare bot fields (botScoreSrcName | verifiedBotCategory):\n")
                L.append(_table(["source | category", "requests"], list(cf["bot_fields_7d"].items())))
            L.append("## AI crawlers (7d)\n")
            buckets = [b for b, _ in PATH_BUCKETS]
            rows = []
            for c, n in a["crawlers"].items():
                cp = a["crawler_paths"].get(c, {})
                rows.append([c, n] + [cp.get(b, 0) for b in buckets])
            L.append(_table(["crawler", "all hits"] + buckets, rows))
            L.append("### Top user agents (7d)\n")
            L.append(_table(["class", "requests", "user agent"],
                            [[x["class"], x["requests"], x["ua"][:110]] for x in a["top_user_agents"]]))
            L.append("### Status x cache (7d, sampled)\n")
            L.append(_table(["status", "cache", "requests"],
                            [[x["status"], x["cache"], x["requests"]] for x in a["status_cache"][:20]]))
        L.append("## Web Analytics (real visitors)\n")
        rum_any = False
        for k in ("rum_7d", "rum_28d"):
            r = cf.get(k)
            if r and r.get("has_data"):
                rum_any = True
                L.append(f"**{k.split('_')[1]}:** {_fmt(r['pageviews'])} page views, {_fmt(r['visits'])} visits\n")
        if rum_any:
            r = cf.get("rum_28d") or cf.get("rum_7d")
            L.append(_table(["path", "page views", "visits"], [[x["path"], x["pageviews"], x["visits"]] for x in r["top_pages"]]))
            L.append(_table(["country", "page views"], list(r["countries"].items())))
        else:
            L.append(f"_{cf.get('rum_hint', 'no Web Analytics data')}_\n")
        L.append("### Web Vitals\n")
        vrows = []
        for k in ("vitals_7d", "vitals_28d"):
            v = cf.get(k)
            if v:
                vrows.append([k.split("_")[1], v["samples"], v.get("largestContentfulPaintP75"),
                              v.get("cumulativeLayoutShiftP75"), v.get("interactionToNextPaintP75")])
        L.append(_table(["window", "samples", "LCP p75", "CLS p75", "INP p75"], vrows))
        if cf.get("errors"):
            L.append("### Cloudflare query errors\n")
            for k, v in cf["errors"].items():
                L.append(f"- `{k}`: {v if isinstance(v, str) else '; '.join(v)[:500]}")
            L.append("")
    g = d.get("gsc") or {}
    if g and g.get("property"):
        L.append(f"## Google Search ({g['property']}, {g['window']['start']} to {g['window']['end']})\n")
        t = g.get("totals_28d") or {}
        L.append(_table(["clicks", "impressions", "CTR", "avg position"],
                        [[t.get("clicks"), t.get("impressions"), t.get("ctr"), t.get("position")]]))
        L.append("### Top queries\n")
        L.append(_table(["query", "clicks", "impr.", "CTR", "pos."],
                        [[x["query"], x["clicks"], x["impressions"], x["ctr"], x["position"]] for x in g.get("top_querys", [])]))
        L.append("### Top pages\n")
        L.append(_table(["page", "clicks", "impr.", "CTR", "pos."],
                        [[x["page"], x["clicks"], x["impressions"], x["ctr"], x["position"]] for x in g.get("top_pages", [])]))
        L.append("### Sitemaps\n")
        L.append(_table(["path", "last submitted", "last downloaded", "pending", "errors", "warnings"],
                        [[s["path"], s["lastSubmitted"], s["lastDownloaded"], s["isPending"], s["errors"], s["warnings"]]
                         for s in g.get("sitemaps", [])]))
        cov = g.get("index_coverage_sample")
        if cov:
            L.append(f"### Index coverage (URL Inspection sample of {cov['inspected']})\n")
            L.append(_table(["coverage state", "URLs"], list(cov["coverageStates"].items())))
        if g.get("errors"):
            L.append("### Search Console errors\n")
            L += [f"- `{k}`: {v}" for k, v in g["errors"].items()]
            L.append("")
    L.append("## Deltas vs previous report\n")
    if not prev:
        L.append("_first report -- no prior JSON in data/analytics/_\n")
    else:
        pm, cm = _delta_metrics(prev[1]), _delta_metrics(d)
        rows = []
        for k in sorted(set(pm) | set(cm)):
            a, b = pm.get(k), cm.get(k)
            ch = None
            if isinstance(a, (int, float)) and isinstance(b, (int, float)):
                ch = f"{(b - a) / a * 100:+.1f}%" if a else ("new" if b else "0")
            rows.append([k, a, b, ch])
        L.append(f"Previous: `{prev[0]}`\n")
        L.append(_table(["metric", "previous", "now", "change"], rows))
    return "\n".join(L) + "\n"


def previous_report(today: str) -> tuple[str, dict] | None:
    cands = sorted(p for p in DATA_DIR.glob("????-??-??.json") if p.stem < today)
    if not cands:
        return None
    p = cands[-1]
    try:
        return p.name, json.loads(p.read_text())
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="print what would be queried; no network, no files")
    ap.add_argument("--only", choices=["cf", "gsc"], help="run one source only")
    ap.add_argument("--inspect", type=int, default=20, help="GSC URL-inspection sample size (0 = skip)")
    args = ap.parse_args()

    today = dt.date.today().isoformat()
    print(f"dejaviewed analytics {today}{' (dry-run)' if args.dry_run else ''}")
    cf = cf_collect(args.dry_run) if args.only in (None, "cf") else None
    gsc = gsc_collect(args.dry_run, args.inspect) if args.only in (None, "gsc") else None
    refused = any(isinstance(x, dict) and x.get("refused") for x in (cf, gsc))

    if args.dry_run:
        print(f"[dry-run] would write data/analytics/{today}.json and reports/analytics_{today}.md")
        return 2 if refused else 0
    has_data = any(isinstance(x, dict) and not x.get("refused") and
                   any(k for k in x if k not in ("errors", "zone_id_found", "account_id_found", "failed")) for x in (cf, gsc))
    failed = any(isinstance(x, dict) and x.get("failed") for x in (cf, gsc))
    if not has_data:
        print(f"no data collected -- nothing written. Follow {SETUP}, then re-run: python3 scripts/analytics_report.py")
        return 2 if refused else (1 if failed else 0)

    d = {"date": today, "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
         "domain": DOMAIN, "missing": MISSING,
         "cloudflare": cf if isinstance(cf, dict) and not cf.get("refused") else None,
         "gsc": gsc if isinstance(gsc, dict) and not gsc.get("refused") else None}
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    jp = DATA_DIR / f"{today}.json"
    jp.write_text(json.dumps(d, indent=1, default=str))
    mp = REPORT_DIR / f"analytics_{today}.md"
    mp.write_text(render_md(d, previous_report(today)))
    print(f"wrote {jp.relative_to(ROOT)} and {mp.relative_to(ROOT)}")
    return 2 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
