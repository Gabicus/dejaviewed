#!/usr/bin/env python3
"""Prompt systems: one pasteable prompting system per curated deep dive and standalone guide.

    python3 scripts/prompt_systems.py export [--size 8]
        -> data/prompt_systems/batch_NN.json   (targets: curated dives + hand-written guides)
    python3 scripts/prompt_systems.py merge 'data/prompt_systems/out_*.json'
        -> data/prompt_systems.json            (slug -> pack)
    python3 scripts/prompt_systems.py render
        -> injects/refreshes the "Prompt system" section in site/guides/<slug>.html (hand-written pages),
           writes site/api/prompts.json and site/prompts.html.
           Generated guide pages get the section from build_guides.py (which imports section_markdown),
           deeper pages from deeper_dives.py (section_html).

Spec for the writing agents: data/prompt_systems/SPEC.md
"""
import argparse
import glob
import html as htmlmod
import json
import re
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
BATCH_DIR = ROOT / "data" / "prompt_systems"
PACKS = ROOT / "data" / "prompt_systems.json"
MARK_START = "<!-- prompt-system:start -->"
MARK_END = "<!-- prompt-system:end -->"
MD_RE = re.compile(r'(<script id="md" type="text/markdown">)(.*?)(</script>)', re.S)


def _load(p):
    return json.load(open(p))


def _l(v):
    try:
        return [str(x) for x in list(v)] if v is not None else []
    except TypeError:
        return []


def load_packs() -> dict:
    return _load(PACKS) if PACKS.exists() else {}


# --------------------------------------------------------------------------- targets
def guide_markdown(path: Path) -> str:
    m = MD_RE.search(path.read_text())
    if not m:
        return ""
    md = m.group(2)
    if MARK_START in md:
        md = md.split(MARK_START)[0]
    return md.strip()


def targets():
    dd = _load(ROOT / "data" / "deep_dives.json")["deep_dives"]
    manual = {m["id"]: m for m in _load(ROOT / "data" / "manual_dives.json")["manual_dives"]}
    cat = _load(SITE / "catalog.json")
    entries = cat["entries"] if isinstance(cat, dict) else cat
    by_id = {}
    for e in entries:
        for k in (e.get("id"), e.get("post_id")):
            if k:
                by_id.setdefault(k, e)

    def brief(e):
        return {
            "title": e.get("title"), "summary": e.get("summary"), "creator": e.get("creator"),
            "tier": e.get("tier"), "type": e.get("type"), "url": e.get("url"),
            "tools": _l(e.get("tools")), "techniques": _l(e.get("techniques")),
            "takeaways": _l(e.get("takeaways"))[:6],
            "caption": (e.get("caption") or "")[:700],
            "transcript": (e.get("transcript") or "")[:1800],
        }

    out = []
    seen = set()
    for d in dd:
        if not (d.get("suggested_by") == "curated" or d.get("pinned")):
            continue
        m = manual.get(d["id"], {})
        slug = d["id"].replace("dd-insight-", "")
        seen.add(slug)
        ents = [by_id[i] for i in d.get("entry_ids", []) if i in by_id]
        out.append({
            "slug": slug, "kind": "dive", "dive_id": d["id"], "title": d.get("title"),
            "class": d.get("class") or d.get("dive_class"),
            "thesis": d.get("thesis") or m.get("thesis"),
            "why_it_matters": d.get("why_it_matters") or m.get("why_it_matters"),
            "action_sketch": d.get("action_sketch") or m.get("action_sketch"),
            "prerequisites": d.get("prerequisites") or m.get("prerequisites"),
            "connection_map": d.get("connection_map") or m.get("connection_map"),
            "tools": sorted({t for e in ents for t in _l(e.get("tools"))}),
            "techniques": sorted({t for e in ents for t in _l(e.get("techniques"))}),
            "domains": sorted({t for e in ents for t in _l(e.get("domains"))}),
            "entries": [brief(e) for e in ents],
        })
    for p in sorted((SITE / "guides").glob("*.html")):
        slug = p.stem
        if slug == "index" or slug in seen:
            continue
        md = guide_markdown(p)
        if not md:
            continue
        title = re.search(r"^#\s+(.+)$", md, re.M)
        out.append({
            "slug": slug, "kind": "guide", "title": title.group(1).strip() if title else slug,
            "guide_markdown": md[:9000], "entries": [],
        })
    return out


def cmd_export(a):
    BATCH_DIR.mkdir(exist_ok=True)
    for f in list(BATCH_DIR.glob("batch_*.json")) + list(BATCH_DIR.glob("out_*.json")):
        f.unlink()
    t = targets()
    n = 0
    for n, i in enumerate(range(0, len(t), a.size), 1):
        json.dump(t[i:i + a.size], open(BATCH_DIR / f"batch_{n:02d}.json", "w"), indent=1, ensure_ascii=False)
    print(f"[export] {len(t)} targets ({sum(x['kind']=='dive' for x in t)} dives, "
          f"{sum(x['kind']=='guide' for x in t)} guides) -> {n} batches in {BATCH_DIR}")


REQUIRED = ["mission", "deeper_not_bigger", "one_shot", "steps", "gap_audit_prompt",
            "self_questions", "validation_oracles", "failure_modes", "agent_direction"]
DNB = ["professional_would", "rawest_material", "methods_tools", "external_proof", "rewritten_prompt"]


def validate(p: dict) -> list[str]:
    errs = [f"missing {k}" for k in REQUIRED if not p.get(k)]
    for k in DNB:
        if not (p.get("deeper_not_bigger") or {}).get(k):
            errs.append(f"missing deeper_not_bigger.{k}")
    steps = p.get("steps") or []
    if not 5 <= len(steps) <= 9:
        errs.append(f"steps={len(steps)} (want 5-9)")
    for s in steps:
        for k in ("title", "goal", "prompt", "expect", "audit"):
            if not s.get(k):
                errs.append(f"step {s.get('n')} missing {k}")
    if len(p.get("one_shot") or "") < 1500:
        errs.append("one_shot too short")
    return errs


def cmd_merge(a):
    packs = load_packs()
    n_ok = n_bad = 0
    for path in a.files:
        for p in _load(path):
            errs = validate(p)
            if errs:
                n_bad += 1
                print(f"[reject] {path}: {p.get('slug')}: {'; '.join(errs)}")
                continue
            p["updated_at"] = date.today().isoformat()
            packs[p["slug"]] = p
            n_ok += 1
    json.dump(packs, open(PACKS, "w"), indent=1, ensure_ascii=False)
    print(f"[merge] ok={n_ok} rejected={n_bad} total packs={len(packs)} -> {PACKS}")


# --------------------------------------------------------------------------- rendering
def _fence(s: str) -> str:
    s = (s or "").strip().replace("```", "'''")
    return f"```text\n{s}\n```"


def section_markdown(pack: dict) -> str:
    """Markdown for the guide pages (rendered client-side by marked)."""
    d = pack["deeper_not_bigger"]
    o = ["", "---", "", "## Prompt system — run this yourself", "",
         "Everything below is pasteable into Claude Code, Claude, or any agent. Use the one-shot when you want "
         "the whole result in one run; use the step prompts when you want to steer. Every step carries its own "
         "audit, and the gap audit at the end makes the agent find and fill what it missed.", "",
         "**Mission.** " + pack["mission"].strip(), "",
         "### 1 · Deeper, not bigger", "",
         "Before running anything, make the task deeper rather than larger. Ask: what would a top professional do "
         "here that I am not asking for; what is the rawest material; which methods and tools; what, other than the "
         "model or me, proves it right. Then ask for exactly that.", "",
         f"- **What a top professional would do (that you didn't ask for):** {d['professional_would'].strip()}",
         f"- **Rawest material to start from:** {d['rawest_material'].strip()}",
         f"- **Methods and tools:** {d['methods_tools'].strip()}",
         f"- **What proves it right (other than you or the model):** {d['external_proof'].strip()}", "",
         "**Rewritten prompt — ask for exactly that:**", "", _fence(d["rewritten_prompt"]), "",
         "### 2 · One-shot prompt", "", _fence(pack["one_shot"]), "",
         "### 3 · Step-by-step prompts", ""]
    for s in pack["steps"]:
        o += [f"#### Step {s['n']} — {s['title'].strip()}", "", f"*Goal:* {s['goal'].strip()}", "",
              _fence(s["prompt"]), "",
              f"**Expect:** {s['expect'].strip()}", "",
              f"**Audit before moving on:** {s['audit'].strip()}", ""]
    o += ["### 4 · Gap analysis and audit", "",
          "Run this after the build. It makes the agent enumerate its own claims, mark what is verified, "
          "rank the gaps and fix the top ones.", "", _fence(pack["gap_audit_prompt"]), "",
          "**Questions the agent must ask itself before it says done:**", ""]
    o += [f"- {q.strip()}" for q in pack["self_questions"]]
    o += ["", "### 5 · What proves it right", ""]
    o += [f"- {q.strip()}" for q in pack["validation_oracles"]]
    o += ["", "### 6 · Failure modes", ""]
    o += [f"- {q.strip()}" for q in pack["failure_modes"]]
    o += ["", "### 7 · Agent direction (unattended runs)", "", pack["agent_direction"].strip(), "",
          f"*Prompt system updated {pack.get('updated_at', '')} · [all prompt systems](../prompts.html) · "
          f"[JSON](../api/prompts.json)*", ""]
    return "\n".join(o)


def _e(s):
    return htmlmod.escape((s or "").strip())


def _pre(s):
    return f'<div class="ps-pre"><button class="ps-copy" type="button">Copy</button><pre>{_e(s)}</pre></div>'


def section_html(pack: dict, api_rel: str = "../api/prompts.json", index_rel: str = "../prompts.html") -> str:
    """HTML for the deeper pages and prompts.html (server-side rendered, styled by PS_CSS)."""
    d = pack["deeper_not_bigger"]
    h = [f'<section class="ps" id="prompt-system"><h2>Prompt system — run this yourself</h2>',
         '<p class="ps-lead">Pasteable into Claude Code, Claude, or any agent. One-shot for the whole result, '
         'step prompts when you want to steer. Every step carries its own audit; the gap audit makes the agent '
         'find and fill what it missed.</p>',
         f'<p><strong>Mission.</strong> {_e(pack["mission"])}</p>',
         '<h3>1 · Deeper, not bigger</h3><ul>',
         f'<li><strong>What a top professional would do (that you didn\'t ask for):</strong> {_e(d["professional_would"])}</li>',
         f'<li><strong>Rawest material to start from:</strong> {_e(d["rawest_material"])}</li>',
         f'<li><strong>Methods and tools:</strong> {_e(d["methods_tools"])}</li>',
         f'<li><strong>What proves it right:</strong> {_e(d["external_proof"])}</li></ul>',
         '<p><strong>Rewritten prompt — ask for exactly that:</strong></p>', _pre(d["rewritten_prompt"]),
         '<h3>2 · One-shot prompt</h3>', _pre(pack["one_shot"]),
         '<h3>3 · Step-by-step prompts</h3>']
    for s in pack["steps"]:
        h += [f'<h4>Step {s["n"]} — {_e(s["title"])}</h4><p><em>Goal:</em> {_e(s["goal"])}</p>', _pre(s["prompt"]),
              f'<p><strong>Expect:</strong> {_e(s["expect"])}</p>',
              f'<p><strong>Audit before moving on:</strong> {_e(s["audit"])}</p>']
    h += ['<h3>4 · Gap analysis and audit</h3>', _pre(pack["gap_audit_prompt"]),
          '<p><strong>Questions the agent must ask itself before it says done:</strong></p><ul>']
    h += [f"<li>{_e(q)}</li>" for q in pack["self_questions"]]
    h += ['</ul><h3>5 · What proves it right</h3><ul>']
    h += [f"<li>{_e(q)}</li>" for q in pack["validation_oracles"]]
    h += ['</ul><h3>6 · Failure modes</h3><ul>']
    h += [f"<li>{_e(q)}</li>" for q in pack["failure_modes"]]
    h += ['</ul><h3>7 · Agent direction (unattended runs)</h3>', f'<p>{_e(pack["agent_direction"])}</p>',
          f'<p class="ps-foot">Prompt system updated {_e(pack.get("updated_at", ""))} · '
          f'<a href="{index_rel}">all prompt systems</a> · <a href="{api_rel}">JSON</a></p></section>']
    return "\n".join(h)


PS_CSS = """
.ps{margin:40px 0;padding-top:24px;border-top:1px solid var(--border)}
.ps h2{font-size:20px;font-weight:900;color:#fff;margin:0 0 10px}
.ps h3{font-size:16px;font-weight:800;color:#fff;margin:26px 0 8px}
.ps h4{font-size:13.5px;font-weight:800;color:var(--accent);margin:18px 0 6px}
.ps p,.ps li{font-size:13.5px;line-height:1.65;color:var(--text-dim)}
.ps ul{padding-left:22px}
.ps-lead{color:var(--text-mute)}
.ps-pre{position:relative;margin:10px 0 14px}
.ps-pre pre{background:rgba(0,0,0,.55);border:1px solid var(--border);padding:14px 16px;border-radius:8px;
  overflow-x:auto;white-space:pre-wrap;word-break:break-word;font-size:12.5px;line-height:1.55;color:var(--text);margin:0}
.ps-copy{position:absolute;top:8px;right:8px;font:700 11px/1 'JetBrains Mono',monospace;padding:5px 9px;border-radius:6px;
  border:1px solid var(--border);background:var(--panel);color:var(--text-dim);cursor:pointer}
.ps-copy:hover{color:#fff;border-color:var(--border-hi)}
.ps-foot{font-size:11.5px;color:var(--text-mute);margin-top:18px}
"""

COPY_JS = """<script>
document.addEventListener('click',e=>{const b=e.target.closest('.ps-copy,.md-copy');if(!b)return;
const pre=b.parentElement.querySelector('pre');navigator.clipboard.writeText(pre.innerText).then(()=>{b.textContent='Copied';setTimeout(()=>b.textContent='Copy',1200)});});
</script>"""

# For marked-rendered guide pages: wrap every <pre> after render with a copy button.
GUIDE_COPY_JS = """<script>
document.querySelectorAll('#guide-body h2').forEach(h=>{if(/^Prompt system/.test(h.textContent))h.id='prompt-system';});
document.querySelectorAll('#guide-body pre').forEach(p=>{const w=document.createElement('div');w.className='ps-pre';
p.parentNode.insertBefore(w,p);const b=document.createElement('button');b.type='button';b.className='md-copy ps-copy';b.textContent='Copy';w.appendChild(b);w.appendChild(p);});
</script>""" + COPY_JS


def inject_guide(path: Path, pack: dict) -> bool:
    """Insert/refresh the prompt-system block inside a hand-written guide's markdown script."""
    txt = path.read_text()
    m = MD_RE.search(txt)
    if not m:
        return False
    md = m.group(2)
    if MARK_START in md and MARK_END in md:
        md = md[:md.index(MARK_START)] + md[md.index(MARK_END) + len(MARK_END):]
    block = f"\n\n{MARK_START}\n{section_markdown(pack)}\n{MARK_END}\n"
    block = re.sub(r"</(script)", r"&lt;/\1", block, flags=re.I)
    md = md.rstrip() + block
    txt = txt[:m.start(2)] + md + txt[m.end(2):]
    txt = re.sub(r"<!-- ps-tail -->.*?<!-- /ps-tail -->", "", txt, flags=re.S)
    txt = txt.replace("</body></html>", f"<!-- ps-tail --><style>{PS_CSS}</style>{GUIDE_COPY_JS}<!-- /ps-tail --></body></html>", 1)
    path.write_text(txt)
    return True


def build_index(packs: dict, meta: dict) -> str:
    cards = []
    for slug, p in sorted(packs.items(), key=lambda kv: kv[1].get("title", kv[0]).lower()):
        t = meta.get(slug, {})
        kind = t.get("kind", "guide")
        deeper = f'<a href="deeper/deeper-insight-{slug}.html#prompt-system">deeper</a> · ' if kind == "dive" else ""
        cards.append(
            f'<div class="card"><div class="ps-kind">{kind} · {len(p["steps"])} steps</div>'
            f'<h3><a href="guides/{slug}.html#prompt-system">{_e(p.get("title") or slug)}</a></h3>'
            f'<p>{_e(p["mission"])[:260]}</p>'
            f'<div class="ps-links">{deeper}<a href="guides/{slug}.html">guide</a></div></div>')
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Prompt systems · DejaViewed</title>
<meta name="description" content="{len(packs)} pasteable prompting systems — one-shot prompts, step-by-step prompts with built-in audits, gap analysis and validation oracles — one for every DejaViewed deep dive and guide.">
<link rel="stylesheet" href="shared.css"><script src="shared.js"></script>
<style>
.wrap{{max-width:1100px;margin:30px auto 80px;padding:0 20px}}
h1{{font-size:32px;font-weight:900;letter-spacing:-.02em;background:linear-gradient(135deg,#fff 0%,#a78bfa 50%,#f472b6 100%);-webkit-background-clip:text;background-clip:text;color:transparent;margin:0 0 10px}}
.lead{{color:var(--text-dim);font-size:15px;line-height:1.65;max-width:760px}}
.lead code{{background:rgba(255,255,255,.07);padding:2px 6px;border-radius:4px;font-family:'JetBrains Mono',monospace;font-size:.9em;color:var(--accent)}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:14px;margin-top:28px}}
.card{{background:var(--panel);border:1px solid var(--border);border-radius:12px;padding:16px 18px}}
.card h3{{font-size:15px;margin:6px 0 8px;line-height:1.35}}.card h3 a{{color:#fff;text-decoration:none}}.card h3 a:hover{{color:var(--accent)}}
.card p{{font-size:12.5px;color:var(--text-dim);line-height:1.55;margin:0 0 10px}}
.ps-kind{{font:700 10.5px/1 'JetBrains Mono',monospace;text-transform:uppercase;letter-spacing:.08em;color:var(--text-mute)}}
.ps-links{{font-size:12px}}.ps-links a{{color:var(--accent);text-decoration:none;font-weight:700}}
.meta{{display:flex;gap:18px;flex-wrap:wrap;margin:18px 0 0;font:600 12px/1 'JetBrains Mono',monospace;color:var(--text-mute)}}
</style></head><body>
<script>DV.mountHeader(document.body,'prompts');</script>
<main class="wrap">
<h1>Prompt systems</h1>
<p class="lead">One prompting system per deep dive and guide: a <em>deeper-not-bigger</em> rewrite of the ask, a verbose one-shot prompt, 5–9 step prompts that each carry their own audit, a post-build gap analysis, the questions the agent must ask itself, and the external oracles that prove the result right. Paste into Claude Code or any agent. Machine-readable at <code>api/prompts.json</code>.</p>
<div class="meta"><span>{len(packs)} systems</span><span>{sum(len(p['steps']) for p in packs.values())} step prompts</span><span>updated {date.today().isoformat()}</span></div>
<div class="grid">{''.join(cards)}</div>
</main>
<footer class="site" style="margin:60px 0 40px;padding-top:30px;border-top:1px solid var(--border);color:var(--text-mute);font-size:12.5px;text-align:center"><a href="index.html" style="color:var(--text-dim)">← Back to DejaViewed</a></footer>
</body></html>"""


def cmd_render(a):
    packs = load_packs()
    if not packs:
        print("[render] no packs; run merge first", file=sys.stderr)
        return 1
    meta = {t["slug"]: t for t in targets()}
    n_inj = 0
    for slug, p in packs.items():
        t = meta.get(slug)
        if t and t["kind"] == "guide":
            if inject_guide(SITE / "guides" / f"{slug}.html", p):
                n_inj += 1
    (SITE / "api").mkdir(exist_ok=True)
    api = {"generated_at": datetime.now().replace(microsecond=0).isoformat(), "count": len(packs),
           "spec": "data/prompt_systems/SPEC.md",
           "prompt_systems": [{"slug": s, "kind": meta.get(s, {}).get("kind", "guide"),
                               "guide": f"https://dejaviewed.dev/guides/{s}",
                               **{k: v for k, v in p.items() if k != "slug"}}
                              for s, p in sorted(packs.items())]}
    json.dump(api, open(SITE / "api" / "prompts.json", "w"), indent=1, ensure_ascii=False)
    (SITE / "prompts.html").write_text(build_index(packs, meta))
    print(f"[render] packs={len(packs)} hand-written guides injected={n_inj} -> site/api/prompts.json, site/prompts.html")
    print("         generated guides/deeper pages: re-run build_guides.py --force and deeper_dives.py --all-curated")
    return 0


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("export"); e.add_argument("--size", type=int, default=8)
    m = sub.add_parser("merge"); m.add_argument("files", nargs="+")
    sub.add_parser("render")
    a = p.parse_args()
    if a.cmd == "export":
        cmd_export(a)
    elif a.cmd == "merge":
        a.files = [f for pat in a.files for f in sorted(glob.glob(pat))]
        cmd_merge(a)
    else:
        sys.exit(cmd_render(a))


if __name__ == "__main__":
    main()
