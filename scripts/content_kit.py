#!/usr/bin/env python3
"""Content kits: turn every curated deep dive / hand-written guide into standalone Instagram content.

    python3 scripts/content_kit.py --all                 # every target: slides.json, PNGs, caption, reel script
    python3 scripts/content_kit.py --slug claude-second-brain --video
    python3 scripts/content_kit.py --all --force         # re-render even if nothing changed

Per slug -> content/<slug>/
    slides.json      7-9 slides (type, kicker, heading, text, alt) built ONLY from the prompt-system pack + dive data
    slide_NN.png     1080x1350 carousel renders (gitignored)
    caption.md       IG caption <= 2,000 chars: hook, summary, save line, credits, link, 15-20 hashtags
    reel_script.md   30-45 s voiceover script (90-120 words), on-screen text per beat, b-roll note
    reel/reel_NN.png + reel.mp4   with --video: 1080x1920 frames, 3.2 s/slide, slow zoom, 0.3 s crossfades (gitignored)
content/INDEX.md     table of kits + "Next 7 to post" (status from content/status.json)

Targets are the same list as scripts/prompt_systems.py targets(). Text is compressed from data, never invented:
whole sentences first, otherwise cut at a clause boundary and marked with an ellipsis. Each slide is fit-checked in
the browser (no text past the content box, nothing touching the edges); if it overflows, the word budget shrinks
and it is rebuilt. One Playwright browser per run. Idempotent: unchanged kits are skipped unless --force.
"""
import argparse
import hashlib
import html
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import prompt_systems as ps  # noqa: E402

ROOT = ps.ROOT
OUT = ROOT / "content"
TPL = Path(__file__).resolve().parent / "content_templates"
STATUS = OUT / "status.json"
SITE_HOST = "dejaviewed.dev"
SLIDE_SECONDS = 3.2
XFADE = 0.3
VERSION = "1"  # bump to force a rebuild of every kit when the builders change

# --------------------------------------------------------------------------- text helpers
_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_SENT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(@`])")
_CLAUSE = re.compile(r"(?:;|:|,| - | — | – )\s*")
PRIVATE = re.compile(r"\bVictor\b")


def clean(s) -> str:
    s = str(s or "")
    s = _MD_LINK.sub(r"\1", s)
    s = s.replace("**", "").replace("`", "").replace("__", "")
    s = re.sub(r"(?<![\w*])\*([^*\n]+)\*(?![\w*])", r"\1", s)
    s = re.sub(r"^\s*[-*]\s+", "", s, flags=re.M)
    s = re.sub(r"\s+", " ", s).strip()
    return s


SUPERLATIVE = re.compile(r"\b(best|greatest|ever|by far|most (?!of\b)[a-z]+|highest[- ][a-z]+|insane|game[- ]changer|revolutionary|"
                         r"unbelievable|mind[- ]blowing)\b", re.I)


def sentences(s: str) -> list[str]:
    out = [x.strip() for x in _SENT.split(clean(s)) if x.strip()]
    out = [x for x in out if not PRIVATE.search(x)]  # private overlay never leaves the laptop
    plain = [x for x in out if not SUPERLATIVE.search(x)]  # no hype claims on the slides
    return plain or out


def words(s: str) -> int:
    return len(s.split())


TAIL_STOP = {"the", "a", "an", "and", "or", "of", "to", "with", "for", "in", "on", "at", "by", "from", "as", "is",
             "are", "that", "which", "what", "its", "your", "their", "his", "her", "this", "these", "into", "per", "vs"}


def _cut(sent: str, n: int) -> str:
    """Cut one over-long sentence to <= n words at the last clause boundary (or hard cut), ending in an ellipsis."""
    w = sent.split()
    if len(w) <= n:
        return sent
    head = " ".join(w[:n])
    best = None
    for m in _CLAUSE.finditer(head):
        if words(head[:m.start()]) >= max(4, int(n * 0.45)):
            best = m.start()
    if best is not None:
        head = head[:best]
    if head.count("(") > head.count(")"):  # never leave a parenthesis open
        head = head[:head.rfind("(")]
    head = head.rstrip(" ,;:-—–(")
    ws = head.split()
    while len(ws) > 3 and ws[-1].lower().strip(",;:") in TAIL_STOP:  # never end on "the…" / "and…"
        ws.pop()
    return " ".join(ws).rstrip(" ,;:-—–(") + "…"


_PAREN = re.compile(r"\s*\(([^()]*)\)")


def drop_parens(s: str) -> str:
    """Remove parenthetical asides, but keep ones that are just a URL/repo path (the source's name)."""
    return _PAREN.sub(lambda m: m.group(0) if re.fullmatch(r"\S*[./]\S*", m.group(1).strip()) else "", s)


def compress(s, n: int, max_sent: int = 9) -> str:
    """Whole sentences while they fit in n words; if the first does not fit, cut it at a clause boundary."""
    n = max(4, int(n))
    out, used = [], 0
    for sent in sentences(s)[:max_sent]:
        k = words(sent)
        if used + k <= n:
            out.append(sent)
            used += k
        elif not out:
            return _cut(sent, n)
        else:
            break
    return " ".join(out)


def first_clause(s: str, n: int) -> str:
    """A short name: text up to the first ':' / ' - ' / ' — ' if that is a real phrase, else the first n words."""
    s = clean(s)
    m = re.match(r"^(.{8,}?)(?::\s| - | — | – |\. )", s)
    head = m.group(1) if m and words(m.group(1)) >= 3 else s
    return _cut(head.rstrip("."), n)


def split_top(s: str) -> list[str]:
    """Split on commas / ', and ' that sit outside parentheses (for one-sentence lists of sources)."""
    out, depth, cur = [], 0, ""
    for ch in s:
        depth += (ch == "(") - (ch == ")")
        if ch == "," and depth == 0:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    out = [re.sub(r"^\s*and\s+", "", x).strip().rstrip(".") for x in out]
    return [x for x in out if x]


def endp(s: str) -> str:
    """End a fragment with exactly one terminal mark."""
    s = s.rstrip()
    return s if s.endswith(("…", ".", "!", "?")) else s + "."


def esc(s: str) -> str:
    return html.escape(s, quote=False)


# --------------------------------------------------------------------------- data access
def _l(v):
    return ps._l(v)


def catalog_entries():
    cat = json.load(open(ps.SITE / "catalog.json"))
    return cat["entries"] if isinstance(cat, dict) else cat


HANDLE = re.compile(r"^[A-Za-z0-9._]{2,30}$")
TIER_RANK = {"S": 0, "A": 1, "B": 2, "C": 3}


def creators_of(entries) -> list[str]:
    seen, out = set(), []
    for e in sorted(entries, key=lambda e: TIER_RANK.get(str(e.get("tier")), 9)):
        c = str(e.get("creator") or "").lstrip("@").strip()
        if c and HANDLE.match(c) and not c.isdigit() and c.lower() not in seen:
            seen.add(c.lower())
            out.append(c)
    return out


def ranked(entries, field) -> list[str]:
    """Values of a list field ordered by how many entries carry them (ties: S/A-tier first, then name)."""
    cnt, best = {}, {}
    for e in entries:
        for x in dict.fromkeys(_l(e.get(field))):
            cnt[x] = cnt.get(x, 0) + 1
            best[x] = min(best.get(x, 9), TIER_RANK.get(str(e.get("tier")), 9))
    return sorted(cnt, key=lambda x: (-cnt[x], best[x], x.lower()))


def guide_thesis(md: str) -> str:
    """First real prose paragraph of a hand-written guide (skips title, metadata lines, rules, lists, code)."""
    body = re.sub(r"```.*?```", "", md, flags=re.S)
    m = re.search(r"^##\s+What (?:it|this) is\s*$(.*?)(?=^##\s|\Z)", body, re.M | re.S | re.I)
    paras = re.split(r"\n\s*\n", m.group(1)) if m else []
    lead = [x for x in re.split(r"\n\s*\n", body) if x.strip() and x.strip()[0] not in "#-*|>!"
            and not x.strip().startswith("**")][:4]
    for para in (paras or lead):  # a "What it is" section wins; otherwise the opening paragraphs
        p = para.strip()
        if not p or p[0] in "#-*|>!" or p.startswith("**") or re.match(r"(Both|It|This|They|These)\b", p) or p.startswith("---") or re.match(r"\d+[.)]\s", p):
            continue
        first = (_SENT.split(clean(p)) or [""])[0]
        if (words(clean(p)) >= 15 and not SUPERLATIVE.search(first) and not first.rstrip().endswith(":")
                and not PRIVATE.search(first)):
            return clean(p)
    return ""


def load_ratings() -> dict:
    r = {}
    for d in json.load(open(ROOT / "data" / "deep_dives.json"))["deep_dives"]:
        r[d["id"]] = d.get("quality_rating")
    for m in json.load(open(ROOT / "data" / "manual_dives.json"))["manual_dives"]:
        if r.get(m["id"]) is None:
            r[m["id"]] = m.get("quality_rating")
    return r


# --------------------------------------------------------------------------- kit model
class Kit:
    def __init__(self, t: dict, pack: dict, cat_by_slug: dict):
        self.t, self.p, self.slug = t, pack, t["slug"]
        self.url = f"{SITE_HOST}/guides/{self.slug}"
        self.title = clean(t.get("title") or self.slug)
        if t["kind"] == "dive":
            self.entries = t.get("entries") or []
            self.thesis_src = t.get("thesis") or ""
            self.tools = ranked(self.entries, "tools") or (t.get("tools") or [])
            self.domains = ranked(self.entries, "domains") or (t.get("domains") or [])
            self.cmap = t.get("connection_map") or {}
            self.entry_ids = list(self.cmap)
        else:
            self.entries = cat_by_slug.get(self.slug, [])
            self.thesis_src = guide_thesis(t.get("guide_markdown") or "")
            self.tools = ranked(self.entries, "tools")
            self.domains = ranked(self.entries, "domains")
            self.cmap = {}
        if not self.thesis_src:
            self.thesis_src = pack.get("mission", "")
        self.creators = creators_of(self.entries)
        dnb = pack.get("deeper_not_bigger") or {}
        self.pro = dnb.get("professional_would", "")
        self.raw = dnb.get("rawest_material", "")
        m = re.search(r"Done means:?\s*(.*)", pack.get("mission", ""), re.S)
        self.done = m.group(1) if m else ""

    # ---- pieces -------------------------------------------------------------
    def hook_title(self) -> str:
        t = self.title
        if words(t) <= 12:
            return t
        parts = [p.strip() for p in re.split(r":\s| — | – | - ", t) if p.strip()]
        fits = [p for p in parts if words(p) <= 12]
        return max(fits, key=words) if fits else _cut(t, 12)

    def raw_sources(self, k=3) -> list[str]:
        r = str(self.raw)
        if re.search(r"(^|\s)\(?1\)\s", r):
            items = re.split(r"(?:^|\s)\(?\d{1,2}\)\s", r)
        elif re.search(r"^\s*-\s", r, re.M):
            items = re.split(r"^\s*-\s", r, flags=re.M)
        elif ";" in r:
            items = r.split(";")
        else:
            items = sentences(r)
        items = [i for i in items if i.strip()]
        if len(items) < 3:
            items = [x for i in items for x in split_top(i)]
        items = [clean(re.sub(r"^Start from the source, not summaries:?", "", i)) for i in items]
        items = [_PAREN.sub(lambda m: "" if SUPERLATIVE.search(m.group(1)) else m.group(0), i) for i in items]
        items = [i for i in items if words(i) >= 2 and not PRIVATE.search(i)]
        return items[:k]

    def key_steps(self) -> list[dict]:
        st = self.p.get("steps") or []
        if len(st) <= 3:
            return st
        idx = sorted({0, len(st) // 2, len(st) - 1})  # ground truth, the core build, the final proof
        return [st[i] for i in idx]

    def failure(self):
        fm = (self.p.get("failure_modes") or [""])[0]
        fm = clean(fm)
        m = re.match(r"^(.*?)[.:]\s+Tell:\s*(.*?)\s*Fix:\s*(.*)$", fm)
        if m:
            return m.group(1), m.group(2), m.group(3)
        ss = sentences(fm)
        return (ss[0] if ss else fm), " ".join(ss[1:2]), " ".join(ss[2:3])

    def quote(self):
        """Creator claim this guide tests: the dive's connection_map line for the top-tier creator's post."""
        if not self.cmap:
            return None
        by_id = {}
        for e in self.entries:
            m = re.search(r"/(?:p|reel|reels|tv)/([^/?#]+)", str(e.get("url") or ""))
            if m:
                by_id[m.group(1)] = e
        for e in sorted(self.entries, key=lambda e: TIER_RANK.get(str(e.get("tier")), 9)):
            c = str(e.get("creator") or "").lstrip("@")
            if not HANDLE.match(c):
                continue
            for pid, line in self.cmap.items():
                if by_id.get(pid) is e and line and not PRIVATE.search(line):
                    return clean(line), c
        return None

    # ---- slides (f = word-budget factor, shrunk when a slide overflows) --------
    def slide_builders(self):
        b = []
        b.append(lambda f: {"type": "hook", "kicker": "Build this", "heading": self.hook_title(),
                            "text": compress(self.done, 24 * f) if self.done else compress(self.p.get("mission"), 22 * f),
                            "label": "Done means" if self.done else "The goal"})
        cred = self.creators[:3]

        def thesis(f):
            return {"type": "point", "kicker": "The idea", "heading": "What it is",
                    "paras": [["", compress(self.thesis_src, (34 if cred else 40) * f)]],
                    "credit": ("From " + " · ".join("@" + c for c in cred)) if cred else ""}
        b.append(thesis)
        q = self.quote()
        if q:
            b.append(lambda f: {"type": "quote", "kicker": "The claim being tested",
                                "text": compress(q[0], 26 * f), "who": "@" + q[1]})
        b.append(lambda f: {"type": "point", "kicker": "Deeper, not bigger",
                            "heading": "What a pro would do that you didn't ask for",
                            "paras": [["", compress(self.pro, 40 * f)]]})
        b.append(lambda f: {"type": "list", "kicker": "Rawest material", "heading": "Start from the source",
                            "items": [_cut(first_clause(drop_parens(i) if words(i) > 14 * f else i, 14), int(14 * f))
                                      for i in self.raw_sources()]})
        b.append(lambda f: {"type": "steps", "kicker": "The system", "heading": "3 steps that matter most",
                            "steps": [[_cut(clean(s.get("title")), 10),
                                       compress(s.get("goal"), 18 * f)] for s in self.key_steps()]})
        b.append(lambda f: {"type": "list", "kicker": "Proof", "heading": "How you know it worked",
                            "items": [compress(o, 24 * f) for o in (self.p.get("validation_oracles") or [])[:2]]})

        def fail(f):
            name, tell, fix = self.failure()
            paras = []
            if tell:
                paras.append(["Tell", compress(tell, 17 * f)])
            if fix:
                paras.append(["Fix", compress(fix, 19 * f)])
            return {"type": "point", "kicker": "Biggest failure mode", "heading": _cut(name, max(4, int(9 * f))),
                    "paras": paras}
        b.append(fail)
        b.append(lambda f: {"type": "cta", "kicker": "Get the full system", "heading": "Build it yourself",
                            "text": "Full prompt system + one-shot prompt at", "url": self.url,
                            "bio": "Link in bio. Save this for your build."})
        return b


# --------------------------------------------------------------------------- HTML rendering
def body_html(s: dict) -> str:
    k = f'<div class="kicker">{esc(s.get("kicker", ""))}</div>'
    t = s["type"]
    if t == "hook":
        return (k + f'<h1><span class="grad">{esc(s["heading"])}</span></h1>'
                + f'<p class="promise"><span class="lbl">{esc(s["label"])}</span>{esc(s["text"])}</p>')
    if t == "point":
        ps_ = "".join(f'<p>{(f"<span class=lbl>{esc(lbl)}</span>" if lbl else "")}{esc(txt)}</p>'
                      for lbl, txt in s["paras"] if txt)
        cr = f'<p class="credit">{esc(s["credit"])}</p>' if s.get("credit") else ""
        return k + f'<h2>{esc(s["heading"])}</h2>' + ps_ + cr
    if t == "list":
        return k + f'<h2>{esc(s["heading"])}</h2><ul>' + "".join(f"<li>{esc(i)}</li>" for i in s["items"]) + "</ul>"
    if t == "quote":
        return k + f'<blockquote>{esc(s["text"])}</blockquote><p class="who">via {esc(s["who"])}</p>'
    if t == "steps":
        return (k + f'<h2>{esc(s["heading"])}</h2><ol>'
                + "".join(f'<li><div class="n">{i}</div><div><p><b>{esc(a)}</b><span>{esc(g)}</span></p></div></li>'
                          for i, (a, g) in enumerate(s["steps"], 1)) + "</ol>")
    if t == "cta":
        return (k + f'<h2>{esc(s["heading"])}</h2><p>{esc(s["text"])}</p>'
                + f'<p class="url">{esc(s["url"])}</p><p class="bio">{esc(s["bio"])}</p>')
    raise ValueError(t)


def slide_text(s: dict) -> str:
    """All visible text of a slide, in reading order (used for alt text)."""
    t = s["type"]
    bits = [s.get("kicker", "")]
    if t == "hook":
        bits += [s["heading"], f'{s["label"]}: {s["text"]}']
    elif t == "point":
        bits += [s["heading"]] + [(f"{l}: {x}" if l else x) for l, x in s["paras"] if x] + [s.get("credit", "")]
    elif t == "list":
        bits += [s["heading"]] + s["items"]
    elif t == "quote":
        bits += [s["text"], "via " + s["who"]]
    elif t == "steps":
        bits += [s["heading"]] + [f"{i}. {a}: {g}" for i, (a, g) in enumerate(s["steps"], 1)]
    elif t == "cta":
        bits += [s["heading"], s["text"] + " " + s["url"], s["bio"]]
    bits = [x.strip() for x in bits if x and x.strip()]
    return " ".join(x if x[-1] in ".…!?" else x + "." for x in bits)


class Renderer:
    FIT_JS = """() => {
      const sl = document.querySelector('.slide'), m = document.querySelector('.main');
      const R = sl.getBoundingClientRect(), cs = getComputedStyle(sl);
      const padX = parseFloat(cs.paddingLeft) - 1, mr = m.getBoundingClientRect();
      const bad = [];
      if (m.scrollHeight > m.clientHeight + 1) bad.push('main overflow ' + m.scrollHeight + '>' + m.clientHeight);
      for (const el of sl.querySelectorAll('.main *, .foot *, .top *')) {
        const r = el.getBoundingClientRect();
        if (!r.width) continue;
        if (r.left < R.left + padX || r.right > R.right - padX) bad.push('x-edge ' + el.tagName);
        if (el.closest('.main') && (r.bottom > mr.bottom + 1 || r.top < mr.top - 1)) bad.push('y ' + el.tagName);
        if (el.scrollWidth > el.clientWidth + 1 && getComputedStyle(el).display !== 'inline') bad.push('wide ' + el.tagName);
      }
      return bad;
    }"""

    def __init__(self):
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch()
        self.pages = {}
        car = (TPL / "carousel.html").read_text()
        base_css = re.search(r"<style>(.*?)</style>", car, re.S).group(1).replace("{{EXTRA_CSS}}", "")
        self.tpl = {"carousel": car.replace("{{EXTRA_CSS}}", ""),
                    "reel": (TPL / "reel.html").read_text().replace("{{BASE_CSS}}", base_css)}
        self.size = {"carousel": (1080, 1350), "reel": (1080, 1920)}

    def page(self, kind):
        if kind not in self.pages:
            w, h = self.size[kind]
            self.pages[kind] = self.browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
        return self.pages[kind]

    def load(self, kind, s, n, total, url):
        h = (self.tpl[kind].replace("{{TYPE}}", s["type"]).replace("{{PILL}}", f"{n:02d} / {total:02d}")
             .replace("{{FOOTER}}", esc(url)).replace("{{BODY}}", body_html(s)))
        pg = self.page(kind)
        pg.set_content(h, wait_until="load")
        pg.evaluate("document.fonts.ready")
        return pg

    def problems(self, kind, s, n, total, url):
        return self.load(kind, s, n, total, url).evaluate(self.FIT_JS)

    def shot(self, kind, s, n, total, url, path):
        pg = self.load(kind, s, n, total, url)
        pg.locator(".slide").screenshot(path=str(path))

    def close(self):
        self.browser.close()
        self._pw.stop()


FACTORS = [1.0, 0.85, 0.72, 0.6, 0.5, 0.4, 0.3]


def fit_slides(kit: Kit, r: Renderer) -> list[dict]:
    builders = kit.slide_builders()
    total = len(builders)
    out = []
    for n, build in enumerate(builders, 1):
        for f in FACTORS:
            s = build(f)
            bad = r.problems("carousel", s, n, total, kit.url)
            if not bad:
                bad = r.problems("reel", s, n, total, kit.url)
            if not bad:
                break
        else:
            raise RuntimeError(f"{kit.slug} slide {n} does not fit even at f={FACTORS[-1]}: {bad[:3]}")
        s["fit_factor"] = f
        s["alt"] = f"DejaViewed carousel, slide {n} of {total}. " + slide_text(s)
        out.append(s)
    return out


# --------------------------------------------------------------------------- caption / reel script
BROAD = ["ai", "claudecode", "aiagents", "claude", "promptengineering", "aitools", "generativeai", "llm",
         "anthropic", "automation", "agenticai", "aiworkflow", "buildinpublic", "learnai"]
STOP = {"the", "and", "for", "with", "that", "your", "from", "into", "when", "what", "this", "how", "why",
        "deep", "dive", "every", "code", "pattern", "system", "standard", "anything", "about", "their", "own", "now", "again", "first", "real"}


def tag(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(s).lower())


def hashtags(kit: Kit) -> list[str]:
    out = []

    def add(x):
        t = tag(x)
        if 2 <= len(t) <= 30 and not t.isdigit() and t not in out:
            out.append(t)
    for x in BROAD[:3]:
        add(x)
    for x in kit.tools[:8]:
        add(x)
    dc = {}
    for e in kit.entries:
        for x in dict.fromkeys(_l(e.get("domains"))):
            dc[x] = dc.get(x, 0) + 1
    common = [x for x in kit.domains if dc.get(x, 0) >= 2] if len(kit.entries) > 2 else kit.domains
    for x in (common or kit.domains)[:3]:
        add(x)
    for x in ranked(kit.entries, "techniques"):
        if len(out) >= 16:
            break
        if len(tag(x)) <= 20:
            add(x)
    for x in BROAD[3:]:
        if len(out) >= 18:
            break
        add(x)
    return out[:20]


def caption(kit: Kit, slides: list[dict], f: float = 1.0) -> str:
    hook = slides[0]
    name, tell, fix = kit.failure()
    oracle = (kit.p.get("validation_oracles") or [""])[0]
    lines = [f'{hook["heading"]}', "",
             compress(kit.thesis_src, 34 * f),
             "What a pro adds: " + compress(kit.pro, 30 * f),
             "Proof it worked: " + compress(oracle, 24 * f),
             "Biggest trap: " + endp(_cut(name, 10)) + (f" Fix: {compress(fix, 18 * f)}" if fix else ""),
             "",
             "Save this for when you build it. The carousel is the map; the guide has every prompt.",
             ""]
    if kit.creators:
        lines.append("Built on posts by " + " ".join("@" + c for c in kit.creators[:6]))
    lines += [f"Full guide + prompts: {kit.url}", "", " ".join("#" + h for h in hashtags(kit))]
    return "\n".join(lines).replace("..", ".").strip() + "\n"


def build_caption(kit, slides):
    for f in FACTORS:
        c = caption(kit, slides, f)
        if len(c) <= 2000:
            return c
    raise RuntimeError(f"{kit.slug}: caption over 2000 chars")


def reel_script(kit: Kit, slides: list[dict]) -> str:
    name, tell, fix = kit.failure()
    oracle = (kit.p.get("validation_oracles") or [""])[0]
    hook = slides[0]["heading"]
    cta = f"The full prompt system and a one-shot prompt are free at dejaviewed dot dev. Link in bio. Save this."

    def beats(f, extra):
        b = [("Hook", hook.rstrip(".") + ".", hook),
             ("Beat 1", compress(kit.thesis_src, 30 * f), "The idea"),
             ("Beat 2", "A pro would go further. " + compress(kit.pro, 26 * f), "What a pro adds"),
             ("Beat 3", "You know it worked when: " + compress(oracle, 20 * f)
              + (" Watch for " + endp(_cut(name, 9)) if extra else ""), "Proof it worked")]
        b.append(("CTA", cta, kit.url))
        return b
    best = None
    for extra in (False, True):
        for f in [1.4, 1.25, 1.1, 1.0, 0.9, 0.8, 0.7, 0.6, 0.5]:
            b = beats(f, extra)
            n = sum(words(x[1]) for x in b)
            if 90 <= n <= 120:
                best = (b, n)
                break
            if best is None or abs(n - 105) < abs(best[1] - 105):
                best = (b, n)
        if 90 <= best[1] <= 120:
            break
    b, n = best
    rows, t = [], 0.0
    for i, (lbl, vo, ost) in enumerate(b):
        d = 3.0 if lbl == "Hook" else max(3.0, words(vo) / 2.7)
        rows.append(f"| {lbl} | {t:.0f}-{t + d:.0f} s | {vo} | {ost} |")
        t += d
    tools = ", ".join(kit.tools[:4]) if kit.tools else "the tools named on the slides"
    out = [f"# Reel script: {kit.title}", "",
           f"Length: {n} words of voiceover, about {t:.0f} s at a natural pace. Guide: {kit.url}", "",
           "| Beat | Time | Voiceover | On-screen text |", "|---|---|---|---|", *rows, "",
           f"**B-roll:** screen capture of {tools} in use, cut against the carousel slides "
           f"(reel.mp4 if rendered). Keep on-screen text inside the middle of the frame; Instagram's UI covers "
           f"the top and bottom.", "",
           ("**Credits on screen:** " + " ".join("@" + c for c in kit.creators[:4])) if kit.creators else "",
           ""]
    return "\n".join(out).rstrip() + "\n", n


# --------------------------------------------------------------------------- video
def ffmpeg_bin() -> str:
    cands = []
    if shutil.which("ffmpeg"):
        cands.append(shutil.which("ffmpeg"))
    try:
        import imageio_ffmpeg
        cands.append(imageio_ffmpeg.get_ffmpeg_exe())
    except Exception:
        pass
    for c in cands:
        enc = subprocess.run([c, "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
        if re.search(r"\blibx264\b", enc):
            return c
    raise RuntimeError("no ffmpeg with libx264 (system ffmpeg or imageio-ffmpeg)")


def make_video(frames: list[Path], out: Path):
    n = len(frames)
    args = [ffmpeg_bin(), "-y", "-hide_banner", "-loglevel", "error"]
    for i, fr in enumerate(frames):
        d = SLIDE_SECONDS + (XFADE if i < n - 1 else 0)
        args += ["-loop", "1", "-framerate", "30", "-t", f"{d:.2f}", "-i", str(fr)]
    fl = []
    for i in range(n):
        # 2x upscale before zoompan keeps the slow push-in smooth; zoom 1.00 -> ~1.05 over the clip
        fl.append(f"[{i}:v]scale=2160:3840,zoompan=z='min(1+0.00045*on,1.06)':x='iw/2-(iw/zoom/2)':"
                  f"y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30,setsar=1,format=yuv420p[v{i}]")
    prev = "v0"
    for i in range(1, n):
        o = f"x{i}"
        fl.append(f"[{prev}][v{i}]xfade=transition=fade:duration={XFADE}:offset={i * SLIDE_SECONDS:.2f}[{o}]")
        prev = o
    args += ["-filter_complex", ";".join(fl), "-map", f"[{prev}]", "-an", "-c:v", "libx264", "-preset", "medium",
             "-crf", "22", "-pix_fmt", "yuv420p", "-r", "30", "-movflags", "+faststart", str(out)]
    subprocess.run(args, check=True)


# --------------------------------------------------------------------------- driver
def write_if_changed(p: Path, s: str) -> bool:
    if p.exists() and p.read_text() == s:
        return False
    p.write_text(s)
    return True


def src_hash(t, pack, cat_entries) -> str:
    h = hashlib.sha256()
    for part in (VERSION, json.dumps(t, sort_keys=True, default=str), json.dumps(pack, sort_keys=True),
                 json.dumps(cat_entries, sort_keys=True, default=str),
                 (TPL / "carousel.html").read_text(), (TPL / "reel.html").read_text(), Path(__file__).read_text()):
        h.update(part.encode())
    return h.hexdigest()[:16]


def pngs_fresh(paths, ref: Path) -> bool:
    return all(p.exists() and p.stat().st_mtime >= ref.stat().st_mtime for p in paths)


def build_kit(t, pack, cat_by_slug, r_get, video, force) -> dict:
    slug = t["slug"]
    d = OUT / slug
    d.mkdir(parents=True, exist_ok=True)
    kit = Kit(t, pack, cat_by_slug)
    sj = d / "slides.json"
    h = src_hash({k: v for k, v in t.items() if k != "guide_markdown"} | {"gm": t.get("guide_markdown")},
                 pack, cat_by_slug.get(slug, []))
    old = json.load(open(sj)) if sj.exists() else None
    if old and old.get("source_hash") == h and not force:
        slides = old["slides"]
    else:
        slides = fit_slides(kit, r_get())
    doc = {"slug": slug, "title": kit.title, "guide_url": "https://" + kit.url, "kind": t["kind"],
           "creators": kit.creators, "source_hash": h, "slides": slides}
    changed = write_if_changed(sj, json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    cap = build_caption(kit, slides)
    write_if_changed(d / "caption.md", cap)
    script, nwords = reel_script(kit, slides)
    write_if_changed(d / "reel_script.md", script)
    total = len(slides)
    pngs = [d / f"slide_{i:02d}.png" for i in range(1, total + 1)]
    for old_png in d.glob("slide_*.png"):
        if old_png not in pngs:
            old_png.unlink()
    rendered = 0
    if force or changed or not pngs_fresh(pngs, sj):
        r = r_get()
        for i, s in enumerate(slides, 1):
            r.shot("carousel", s, i, total, kit.url, pngs[i - 1])
        rendered = total
    mp4 = d / "reel.mp4"
    if video and (force or changed or not mp4.exists() or mp4.stat().st_mtime < sj.stat().st_mtime):
        rd = d / "reel"
        rd.mkdir(exist_ok=True)
        for old_png in rd.glob("reel_*.png"):
            old_png.unlink()
        frames = []
        r = r_get()
        for i, s in enumerate(slides, 1):
            fr = rd / f"reel_{i:02d}.png"
            r.shot("reel", s, i, total, kit.url, fr)
            frames.append(fr)
        make_video(frames, mp4)
    return {"slug": slug, "title": kit.title, "slides": total, "caption_chars": len(cap), "script_words": nwords,
            "video": mp4.exists(), "rendered": rendered, "kind": t["kind"], "dive_id": t.get("dive_id")}


def write_index(rows, status, ratings):
    rows = sorted(rows, key=lambda r: r["slug"])
    L = ["# Content kits", "",
         "Instagram kits generated by `scripts/content_kit.py` from the prompt-system packs and deep dives. "
         "Mark a kit posted in `content/status.json` as `\"posted:YYYY-MM-DD\"`.", "",
         f"{len(rows)} kits · {sum(r['slides'] for r in rows)} slides · "
         f"{sum(1 for r in rows if r['video'])} with video", "",
         "| Slug | Title | Slides | Caption chars | Video | Status | Guide |", "|---|---|---|---|---|---|---|"]
    for r in rows:
        u = f"https://{SITE_HOST}/guides/{r['slug']}"
        L.append(f"| [{r['slug']}]({r['slug']}/) | {r['title'].replace('|', '/')} | {r['slides']} | "
                 f"{r['caption_chars']} | {'yes' if r['video'] else 'no'} | {status.get(r['slug'], 'unposted')} | {u} |")
    order = sorted([r for r in rows if status.get(r["slug"], "unposted") == "unposted"],
                   key=lambda r: (-(ratings.get(r["dive_id"]) or 0), r["kind"] != "dive", r["slug"]))
    L += ["", "## Next 7 to post", "", "Unposted kits, highest dive quality rating first.", ""]
    for i, r in enumerate(order[:7], 1):
        q = ratings.get(r["dive_id"])
        L.append(f"{i}. **{r['title']}** (`{r['slug']}`, quality {q if q is not None else 'n/a'}/5): "
                 f"`content/{r['slug']}/`")
    write_if_changed(OUT / "INDEX.md", "\n".join(L) + "\n")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--slug", nargs="+")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--video", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    targets = ps.targets()
    packs = ps.load_packs()
    by_slug = {t["slug"]: t for t in targets}
    if a.slug:
        missing = [s for s in a.slug if s not in by_slug]
        if missing:
            sys.exit(f"unknown slug(s): {missing}")
        todo = [by_slug[s] for s in a.slug]
    else:
        todo = targets
    todo = [t for t in todo if t["slug"] in packs] or sys.exit("no targets with prompt-system packs")

    cat_by_slug = {}
    for e in catalog_entries():
        if e.get("deep_dive_slug"):
            cat_by_slug.setdefault(e["deep_dive_slug"], []).append(
                {k: e.get(k) for k in ("creator", "tier", "tools", "domains", "url", "title")})

    OUT.mkdir(exist_ok=True)
    status = json.load(open(STATUS)) if STATUS.exists() else {}
    for t in targets:
        status.setdefault(t["slug"], "unposted")
    write_if_changed(STATUS, json.dumps(dict(sorted(status.items())), indent=1) + "\n")

    holder = {}

    def r_get():
        if "r" not in holder:
            holder["r"] = Renderer()
        return holder["r"]

    try:
        for t in todo:
            res = build_kit(t, packs[t["slug"]], cat_by_slug, r_get, a.video, a.force)
            print(f"[kit] {res['slug']}: {res['slides']} slides, caption {res['caption_chars']} chars, "
                  f"script {res['script_words']} words, rendered {res['rendered']}, video {res['video']}")
    finally:
        if "r" in holder:
            holder["r"].close()

    rows = []
    for t in targets:
        sj = OUT / t["slug"] / "slides.json"
        if not sj.exists():
            continue
        doc = json.load(open(sj))
        rows.append({"slug": t["slug"], "title": doc["title"], "slides": len(doc["slides"]),
                     "caption_chars": len((OUT / t["slug"] / "caption.md").read_text()),
                     "video": (OUT / t["slug"] / "reel.mp4").exists(), "kind": t["kind"], "dive_id": t.get("dive_id")})
    write_index(rows, status, load_ratings())
    print(f"[index] {len(rows)} kits -> {OUT / 'INDEX.md'}")


if __name__ == "__main__":
    main()
