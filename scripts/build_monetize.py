#!/usr/bin/env python3
"""Monetization layer for the static site. Idempotent post-processor, run AFTER build_seo.

Inputs (hand-maintained):
  data/monetize/affiliates.json   {slug: {tool, aliases, status pending|active|skip, affiliate_url, official_url, ...}}
  data/monetize/config.json       service/diy/tip-jar/sponsors/prompt-pack URLs, disclosure text, inline label

Outputs:
  site/_redirects                 Cloudflare Pages rules `/go/<slug> <url> 302` inside a marker section
                                  (active -> affiliate_url, pending -> official_url, skip -> no rule;
                                  plus /go/diy, /go/service, /go/tip, /go/sponsors, /go/prompt-pack when set).
  tool links                      guide markdown (Tools lines + "Key tools and resources" list),
                                  deeper hero tool pills, entry "5k ft — Tools" line -> <a class="go" href="/go/<slug>">.
                                  active: rel="sponsored nofollow noopener" + <sup class="aff">affiliate link</sup>;
                                  pending: rel="noopener" (plain outbound, still measured via /go/).
  <!-- monetize:start --> footer   before </body> on every public page (not NOINDEX pages): DIY / done-for-you CTAs,
                                  optional tip jar / sponsors, disclosure only when an affiliate is active.
  <!-- monetize-prompts:start -->  "free here and as JSON" note on prompts.html (+ pack link when set).

Every run strips its own markup first, then re-applies, so a second run is byte-identical.
Never touches <pre>, <code>, <style>, non-markdown <script>, headings, or prompt-system blocks.

Usage:
  python3 scripts/build_monetize.py            # apply
  python3 scripts/build_monetize.py --check    # dry run; exit 1 if anything would change
  python3 scripts/build_monetize.py --report   # apply (or with --check: don't) + per-tool link counts
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_seo import DATA, SITE, collect_pages, noindex_pages  # noqa: E402

AFF = DATA / "monetize" / "affiliates.json"
CFG = DATA / "monetize" / "config.json"
REDIRECTS = SITE / "_redirects"

R_START, R_END = "# monetize:start", "# monetize:end"
F_START, F_END = "<!-- monetize:start -->", "<!-- monetize:end -->"
P_START, P_END = "<!-- monetize-prompts:start -->", "<!-- monetize-prompts:end -->"
PS_START, PS_END = "<!-- prompt-system:start -->", "<!-- prompt-system:end -->"

FOOTER_RE = re.compile(r"<!-- monetize:start -->.*?<!-- monetize:end -->\n?", re.S)
PROMPTS_RE = re.compile(r"<!-- monetize-prompts:start -->.*?<!-- monetize-prompts:end -->\n?", re.S)
LINK_RE = re.compile(r'<a class="go" href="/go/[^"]*" rel="[^"]*">(.*?)</a>(?:<sup class="aff">[^<]*</sup>)?', re.S)
SECTION_RE = re.compile(r"\n?# monetize:start\n.*?# monetize:end\n?", re.S)

# fixed CTA slugs -> config key
CTA_SLUGS = {"diy": "diy_url", "service": "service_url", "tip": "tip_jar_url",
             "sponsors": "sponsors_url", "prompt-pack": "prompt_pack_url"}


# ─────────────────────────────────────────────────────────── config
def load() -> tuple[dict, dict]:
    aff = json.loads(AFF.read_text(encoding="utf-8"))
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    for slug, a in aff.items():
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
            raise SystemExit(f"affiliates.json: bad slug {slug!r} (lowercase letters, digits, dashes)")
        if slug in CTA_SLUGS:
            raise SystemExit(f"affiliates.json: slug {slug!r} collides with a CTA slug")
        st = a.get("status")
        if st not in ("pending", "active", "skip"):
            raise SystemExit(f"affiliates.json: {slug} has status {st!r} (pending|active|skip)")
        if st == "active" and not (a.get("affiliate_url") or "").strip():
            print(f"warning: {slug} is active but affiliate_url is empty -> treated as pending", file=sys.stderr)
            a["status"] = "pending"
        if st != "skip" and not (a.get("official_url") or "").strip():
            print(f"warning: {slug} has no official_url -> skipped", file=sys.stderr)
            a["status"] = "skip"
    return aff, cfg


def target(a: dict) -> str:
    return (a["affiliate_url"] if a["status"] == "active" else a["official_url"]).strip()


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(s)).strip().lower()


def name_map(aff: dict) -> dict[str, str]:
    m: dict[str, str] = {}
    for slug, a in aff.items():
        if a["status"] == "skip":
            continue
        for n in [a["tool"], *(a.get("aliases") or [])]:
            k = norm(n)
            if k in m and m[k] != slug:
                print(f"warning: name {n!r} maps to both {m[k]} and {slug}; keeping {m[k]}", file=sys.stderr)
                continue
            m[k] = slug
    return m


def cta(cfg: dict, slug: str) -> bool:
    return bool((cfg.get(CTA_SLUGS[slug]) or "").strip())


# ─────────────────────────────────────────────────────────── _redirects
def build_redirects(old: str, aff: dict, cfg: dict) -> str:
    lines = [R_START,
             "# Generated by scripts/build_monetize.py from data/monetize/{affiliates,config}.json. Edit those, not this block.",
             "# /go/<slug> is stable: pending tools 302 to the official site, active ones to the affiliate URL,",
             "# so outbound clicks show in Cloudflare path analytics from day one (analytics_report.py /go/ table).",
             "# Cloudflare Pages limit: 2,000 static + 100 dynamic redirect rules per _redirects file."]
    for slug in sorted(CTA_SLUGS):
        if cta(cfg, slug):
            lines.append(f"/go/{slug} {cfg[CTA_SLUGS[slug]].strip()} 302")
    for slug in sorted(aff):
        a = aff[slug]
        if a["status"] != "skip":
            lines.append(f"/go/{slug} {target(a)} 302")
    lines.append(R_END)
    block = "\n".join(lines) + "\n"
    rest = SECTION_RE.sub("\n", old).strip("\n") if old else ""
    n_rules = sum(1 for l in (rest + "\n" + block).splitlines() if l.strip() and not l.lstrip().startswith("#"))
    if n_rules > 2000:
        raise SystemExit(f"_redirects would hold {n_rules} rules (> 2,000 Cloudflare Pages limit)")
    return (rest + "\n\n" if rest else "") + block


# ─────────────────────────────────────────────────────────── link markup
def link(name_html: str, slug: str, aff: dict, cfg: dict) -> str:
    active = aff[slug]["status"] == "active"
    rel = "sponsored nofollow noopener" if active else "noopener"
    out = f'<a class="go" href="/go/{slug}" rel="{rel}">{name_html}</a>'
    if active:
        out += f'<sup class="aff">{html.escape(cfg.get("inline_label") or "affiliate link")}</sup>'
    return out


def strip_links(text: str) -> str:
    return LINK_RE.sub(r"\1", text)


def link_list(items: str, sep: str, names: dict, aff: dict, cfg: dict, hits: Counter) -> str:
    """Comma-separated tool names -> each exact match linked; everything else untouched."""
    parts = items.split(sep)
    for i, p in enumerate(parts):
        core = p.strip()
        slug = names.get(norm(core))
        if slug and core:
            lead = p[: len(p) - len(p.lstrip())]
            trail = p[len(p.rstrip()):]
            parts[i] = lead + link(core, slug, aff, cfg) + trail
            hits[slug] += 1
    return sep.join(parts)


def protected_spans(text: str) -> list[tuple[int, int]]:
    spans = []
    for m in re.finditer(re.escape(PS_START) + r".*?" + re.escape(PS_END), text, re.S):
        spans.append(m.span())
    return spans


def outside(pos: int, spans: list[tuple[int, int]]) -> bool:
    return not any(a <= pos < b for a, b in spans)


def link_guide_md(text: str, names, aff, cfg, hits) -> str:
    """Guides render <script id="md" type="text/markdown"> client-side (marked + DOMPurify keeps a[href,rel,class], sup).
    Only the '**Tools:** a, b' lines and the '## Key tools and resources' bullet list are touched, and only
    before the '## Prompt system' heading."""
    m = re.search(r'(<script id="md" type="text/markdown">)(.*?)(</script>)', text, re.S)
    if not m:
        return text
    md = m.group(2)
    ps = re.search(r"(?m)^## Prompt system", md)
    head, tail = (md[: ps.start()], md[ps.start():]) if ps else (md, "")
    out, in_tools = [], False
    for line in head.split("\n"):
        if line.startswith("## "):
            in_tools = line.strip() == "## Key tools and resources"
        elif line.startswith("#"):
            in_tools = False
        if in_tools:
            bm = re.fullmatch(r"(- \*\*)(.+?)(\*\*)", line)
            if bm:
                line = bm.group(1) + link_list(bm.group(2), "\x00", names, aff, cfg, hits) + bm.group(3)
        else:
            tm = re.search(r"\*\*Tools:\*\* (.+)$", line)
            if tm:
                line = line[: tm.start(1)] + link_list(tm.group(1), ", ", names, aff, cfg, hits)
        out.append(line)
    new_md = "\n".join(out) + tail
    return text[: m.start(2)] + new_md + text[m.end(2):]


def link_deeper(text: str, names, aff, cfg, hits) -> str:
    spans = protected_spans(text)

    def tools_div(m):
        if not outside(m.start(), spans):
            return m.group(0)
        inner = re.sub(r"(<span class='tool-pill'>)([^<]*)(</span>)",
                       lambda p: p.group(1) + link_list(p.group(2), "\x00", names, aff, cfg, hits) + p.group(3),
                       m.group(2))
        return m.group(1) + inner + m.group(3)
    return re.sub(r'(<div class="tools">)(.*?)(</div>)', tools_div, text, count=1, flags=re.S)


def link_entry(text: str, names, aff, cfg, hits) -> str:
    """Entry tableau: first line of the 5k ft level body is the comma-separated tool list."""
    return re.sub(r'(<h3>5k ft — Tools &amp; techniques</h3><div class="body">)([^\n<]*)',
                  lambda m: m.group(1) + link_list(m.group(2), ", ", names, aff, cfg, hits),
                  text, count=1)


# ─────────────────────────────────────────────────────────── footer / prompts note
def footer_html(aff: dict, cfg: dict) -> str:
    esc = html.escape
    rows = []
    cta_bits = []
    if cta(cfg, "diy"):
        cta_bits.append('DIY: <a href="/go/diy" rel="noopener">free skill on GitHub</a>')
    if cta(cfg, "service"):
        cta_bits.append('Done for you: <a href="/go/service" rel="noopener">get in touch</a>')
    if cta_bits:
        rows.append('<p class="mon-cta">' + " · ".join(cta_bits) + "</p>")
    sup = []
    if cta(cfg, "tip"):
        sup.append('<a href="/go/tip" rel="noopener">tip jar</a>')
    if cta(cfg, "sponsors"):
        sup.append('<a href="/go/sponsors" rel="noopener">sponsor</a>')
    if sup:
        rows.append('<p class="mon-sup">Support this archive: ' + " · ".join(sup) + "</p>")
    if any(a["status"] == "active" for a in aff.values()) and (cfg.get("disclosure_footer") or "").strip():
        rows.append(f'<p class="mon-disc">{esc(cfg["disclosure_footer"].strip())}</p>')
    if not rows:
        return ""
    return (F_START + '<footer class="mon" data-pagefind-ignore><div class="mon-in">'
            + "".join(rows) + "</div></footer>" + F_END + "\n")


def add_footer(text: str, block: str) -> str:
    if not block:
        return text
    i = text.lower().rfind("</body>")
    if i < 0:
        return text
    return text[:i] + block + text[i:]


def prompts_note(cfg: dict) -> str:
    try:
        n = json.loads((SITE / "api" / "prompts.json").read_text(encoding="utf-8")).get("count")
    except Exception:
        n = None
    if not n:
        return ""
    pack = ' <a href="/go/prompt-pack" rel="noopener">Get the pack (offline bundle)</a>' if cta(cfg, "prompt-pack") else ""
    return (P_START + f'<p class="mon-note">All {n} prompt systems are free here and as JSON '
            f'(<a href="api/prompts.json">api/prompts.json</a>).{pack}</p>' + P_END + "\n")


def add_prompts_note(text: str, block: str) -> str:
    if not block:
        return text
    m = re.search(r'<p class="lead">.*?</p>\n', text, re.S)
    if not m:
        return text
    return text[: m.end()] + block + text[m.end():]


# ─────────────────────────────────────────────────────────── main
def process(rel: str, public: bool, names, aff, cfg, footer, pnote, hits) -> tuple[str, str]:
    path = SITE / rel
    orig = path.read_text(encoding="utf-8", errors="replace")
    text = PROMPTS_RE.sub("", FOOTER_RE.sub("", orig))
    text = strip_links(text)
    if public:
        top = rel.split("/")[0]
        if top == "guides" and rel != "guides/index.html":
            text = link_guide_md(text, names, aff, cfg, hits)
        elif top == "deeper":
            text = link_deeper(text, names, aff, cfg, hits)
        elif top == "e":
            text = link_entry(text, names, aff, cfg, hits)
        if rel == "prompts.html":
            text = add_prompts_note(text, pnote)
        text = add_footer(text, footer)
    return orig, text


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="dry run; exit 1 if anything would change")
    ap.add_argument("--report", action="store_true", help="print tool status counts and per-tool link counts")
    args = ap.parse_args()

    aff, cfg = load()
    names = name_map(aff)
    footer = footer_html(aff, cfg)
    pnote = prompts_note(cfg)
    hits: Counter = Counter()
    pages_hit: Counter = Counter()
    would_change: list[str] = []

    old_r = REDIRECTS.read_text(encoding="utf-8") if REDIRECTS.exists() else ""
    new_r = build_redirects(old_r, aff, cfg)
    if new_r != old_r:
        would_change.append("_redirects")
        if not args.check:
            REDIRECTS.write_text(new_r, encoding="utf-8")

    public = collect_pages()
    private = [p for p in noindex_pages() if p not in set(public)]
    footers = 0
    for rel, is_public in [(p, True) for p in public] + [(p, False) for p in private]:
        before = sum(hits.values())
        orig, new = process(rel, is_public, names, aff, cfg, footer, pnote, hits)
        if sum(hits.values()) > before:
            pages_hit[rel.split("/")[0] if "/" in rel else "(root)"] += 1
        footers += F_START in new
        if new != orig:
            would_change.append(rel)
            if not args.check:
                (SITE / rel).write_text(new, encoding="utf-8")

    st = Counter(a["status"] for a in aff.values())
    print(f"monetize: tools {len(aff)} (active {st['active']}, pending {st['pending']}, skip {st['skip']}); "
          f"public pages {len(public)}, footer blocks {footers}, private pages cleaned {len(private)}; "
          f"tool links {sum(hits.values())} on {sum(pages_hit.values())} pages; "
          f"{'would change' if args.check else 'changed'} {len(would_change)} file(s)")
    if args.report:
        print(f"{'slug':14} {'status':8} {'links':>6}  target")
        for slug in sorted(aff, key=lambda s: (-hits[s], s)):
            a = aff[slug]
            tgt = "-" if a["status"] == "skip" else target(a)
            print(f"{slug:14} {a['status']:8} {hits[slug]:>6}  {tgt}")
        print("pages with tool links: " + ", ".join(f"{k} {v}" for k, v in sorted(pages_hit.items())))
        print("CTAs: " + ", ".join(f"/go/{s} {'on' if cta(cfg, s) else 'off (empty URL)'}" for s in sorted(CTA_SLUGS)))
    if args.check:
        print(f"[check] {len(would_change)} file(s) would change" + (f": {would_change[:10]}" if would_change else ""))
        return 1 if would_change else 0
    # Guide bodies are server-rendered from the <script id="md"> source we just rewrote:
    # re-render so the HTML body never lags the markdown (build_guides.rerender_all is idempotent).
    if any(rel.startswith("guides/") for rel in would_change):
        try:
            from build_guides import rerender_all
            n_changed, n_total = rerender_all()
            print(f"monetize: re-rendered guide bodies ({n_changed}/{n_total} changed)")
        except Exception as e:  # never fail the monetize pass over a render hiccup; report it
            print(f"monetize: WARNING guide re-render skipped: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
