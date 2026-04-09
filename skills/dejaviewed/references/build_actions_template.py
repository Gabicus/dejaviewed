#!/usr/bin/env python3
"""Build data/actions.json — structured action plan from the DejaViewed catalog."""

import json, os, re
from collections import Counter
from datetime import date
from pathlib import Path

ROOT = Path(__file__).parent
CATALOG = ROOT / "data" / "catalog.jsonl"
CURATION = ROOT / "data" / "curation.json"
GUIDES_DIR = ROOT / "guides"
OUT = ROOT / "data" / "actions.json"


def load_catalog():
    records = []
    with open(CATALOG) as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def load_curation():
    with open(CURATION) as f:
        return json.load(f)


def get_tier(record, curation_tiers):
    """Resolve tier: explicit field > curation.json lookup > 'B' default."""
    t = record.get("tier")
    if t and t != "none":
        return t
    url = record.get("post_url", "")
    if url in curation_tiers:
        return curation_tiers[url]
    return "B"  # untiered defaults to B


def post_id(record):
    """Extract short post ID from URL."""
    m = re.search(r"/p/([^/]+)", record.get("post_url", ""))
    return m.group(1) if m else record.get("post_url", "unknown")


def is_github_url(url):
    return "github.com/" in url and "/issues" not in url and "/pull/" not in url


def extract_git_clone_url(record):
    """Try to find a cloneable git URL from links or repos_mentioned."""
    for link in record.get("links", []):
        url = link.get("url", "")
        if is_github_url(url) and url.count("/") >= 4:
            # Looks like github.com/owner/repo
            clean = url.rstrip("/")
            # Remove trailing fragments
            clean = clean.split("#")[0].split("?")[0]
            return clean
    # Try to construct from repos_or_projects_mentioned
    for repo in record.get("repos_or_projects_mentioned", []):
        if "/" in repo and not repo.startswith("http"):
            return f"https://github.com/{repo}"
    return None


def make_item(record, tier, **extra):
    """Build a standard action item."""
    item = {
        "title": record.get("card_title", "Untitled"),
        "why": (record.get("summary", "") or "")[:200],
        "tier": tier,
        "source_cards": [post_id(record)],
        "links": record.get("links", []),
    }
    item.update(extra)
    return item


def build_clone_repos(live, tiers):
    """Section 1: Clone-worthy repos. S/A tier only."""
    items = []
    seen_urls = set()
    candidates = []
    for r in live:
        tier = get_tier(r, tiers)
        if tier not in ("S", "A"):
            continue
        has_repo = (
            r.get("type") == "repo"
            or len(r.get("repos_or_projects_mentioned", [])) > 0
        )
        if not has_repo:
            continue
        git_url = extract_git_clone_url(r)
        if git_url and git_url not in seen_urls:
            seen_urls.add(git_url)
            candidates.append((r, tier, git_url))

    # Sort: S first, then A
    tier_order = {"S": 0, "A": 1}
    candidates.sort(key=lambda x: tier_order.get(x[1], 2))

    for r, tier, git_url in candidates:
        items.append(make_item(r, tier, command=f"git clone {git_url}"))
    return items


def build_install_tools(live, tiers):
    """Section 2: Installable tools. S/A tier only."""
    items = []
    seen = set()
    for r in live:
        tier = get_tier(r, tiers)
        if tier not in ("S", "A"):
            continue
        is_tool = r.get("type") == "tool" or any(
            kw in t.lower()
            for t in r.get("tools_mentioned", [])
            for kw in ["cli", "sdk", "api"]
        )
        if not is_tool and r.get("type") != "tool":
            continue
        title = r.get("card_title", "")
        if title in seen:
            continue
        seen.add(title)

        # Try to derive install command
        cmd = None
        git_url = extract_git_clone_url(r)
        if git_url:
            cmd = f"git clone {git_url}"
        for link in r.get("links", []):
            url = link.get("url", "")
            if "npmjs.com" in url:
                pkg = url.rstrip("/").split("/")[-1]
                cmd = f"npm install {pkg}"
            elif "pypi.org" in url:
                pkg = url.rstrip("/").split("/")[-1]
                cmd = f"pip install {pkg}"

        extra = {}
        if cmd:
            extra["command"] = cmd
        tier_order = {"S": 0, "A": 1}
        items.append((tier_order.get(tier, 2), make_item(r, tier, **extra)))

    items.sort(key=lambda x: x[0])
    return [it for _, it in items]


def build_read_guides(live, tiers):
    """Section 3: Items with matching deep-dive guide files."""
    guide_slugs = {f.stem for f in GUIDES_DIR.glob("*.md")} if GUIDES_DIR.exists() else set()
    items = []
    for r in live:
        slug = r.get("deep_dive_topic")
        if not slug or slug not in guide_slugs:
            continue
        tier = get_tier(r, tiers)
        items.append(
            make_item(
                r,
                tier,
                guide_url=f"guides/{slug}.html",
                guide_slug=slug,
            )
        )
    # Sort by tier
    tier_order = {"S": 0, "A": 1, "B": 2, "C": 3}
    items.sort(key=lambda x: tier_order.get(x["tier"], 4))
    return items


def build_try_techniques(live, tiers):
    """Section 4: Techniques worth trying."""
    items = []
    seen = set()
    for r in live:
        techs = r.get("techniques_mentioned", [])
        if not techs:
            continue
        tier = get_tier(r, tiers)
        title = r.get("card_title", "")
        if title in seen:
            continue
        seen.add(title)
        items.append(
            make_item(
                r,
                tier,
                techniques=techs,
            )
        )
    tier_order = {"S": 0, "A": 1, "B": 2, "C": 3}
    items.sort(key=lambda x: tier_order.get(x["tier"], 4))
    return items


def build_bookmark_platforms(live, tiers):
    """Section 5: Platforms to bookmark."""
    items = []
    seen = set()
    for r in live:
        is_plat = r.get("type") == "platform" or "platform" in " ".join(
            r.get("domains", [])
        )
        if not is_plat:
            continue
        title = r.get("card_title", "")
        if title in seen:
            continue
        seen.add(title)
        tier = get_tier(r, tiers)
        # Find the primary URL
        primary_url = None
        for link in r.get("links", []):
            url = link.get("url", "")
            if url and "instagram.com" not in url:
                primary_url = url
                break
        extra = {}
        if primary_url:
            extra["url"] = primary_url
        items.append(make_item(r, tier, **extra))
    tier_order = {"S": 0, "A": 1, "B": 2, "C": 3}
    items.sort(key=lambda x: tier_order.get(x["tier"], 4))
    return items


def build_design_resources(live, tiers):
    """Section 6: Design, art, UI/UX resources."""
    design_domains = {"design", "art", "uiux", "creative-coding", "image-gen", "3d"}
    items = []
    seen = set()
    for r in live:
        domains = set(r.get("domains", []))
        if not domains & design_domains:
            continue
        title = r.get("card_title", "")
        if title in seen:
            continue
        seen.add(title)
        tier = get_tier(r, tiers)
        items.append(make_item(r, tier))
    tier_order = {"S": 0, "A": 1, "B": 2, "C": 3}
    items.sort(key=lambda x: tier_order.get(x["tier"], 4))
    return items


def build_watch_out(live, tiers):
    """Section 7: C-tier, DM-bait, gated content."""
    items = []
    seen = set()
    for r in live:
        tier = get_tier(r, tiers)
        summary = r.get("summary", "").lower()
        is_suspect = (
            tier == "C"
            or r.get("drop", False)
            or re.search(r"\bDM\b", r.get("summary", ""))
            or "comment " in summary
            or "link in bio" in summary
            or "gated" in summary
        )
        if not is_suspect:
            continue
        title = r.get("card_title", "")
        if title in seen:
            continue
        seen.add(title)

        # Write an honest note
        note = ""
        if re.search(r"\bDM\b", r.get("summary", "")):
            note = "Content gated behind DM — actual value unverifiable."
        elif "link in bio" in summary:
            note = "Points to newsletter/bio link — real content may be thin."
        elif "comment" in summary and ("drop" in summary or tier == "C"):
            note = "Engagement bait — asks for comments to unlock content."
        elif tier == "C":
            note = "Low signal-to-noise. Covered better elsewhere in catalog."

        items.append(make_item(r, tier, note=note))
    return items


def build_save_profile(live, tiers):
    """Generate the witty save profile string."""
    type_counts = Counter(r.get("type", "unknown") for r in live)
    total = len(live)

    # Category groups
    code_types = sum(type_counts.get(t, 0) for t in ["repo", "tool", "tutorial"])
    inspo_types = sum(type_counts.get(t, 0) for t in ["inspiration", "demo", "news"])
    guide_types = type_counts.get("guide", 0)
    technique_types = type_counts.get("technique", 0)

    code_pct = round(100 * code_types / total)
    inspo_pct = round(100 * inspo_types / total)
    guide_pct = round(100 * guide_types / total)

    tier_counts = Counter(get_tier(r, tiers) for r in live)
    c_pct = round(100 * tier_counts.get("C", 0) / total)

    profile = (
        f"You save mostly repos, tools, and tutorials ({code_pct}%) with "
        f"{inspo_pct}% pure inspiration. Only {guide_pct}% are guides — "
        f"you hoard more than you study. "
        f"{c_pct}% of your saves are C-tier filler. "
        f"Your strongest signal is in agents and trading; your weakest is "
        f"finishing what you bookmark."
    )
    return profile


def build_stats(live, tiers):
    type_counts = Counter(r.get("type", "unknown") for r in live)
    tier_counts = Counter(get_tier(r, tiers) for r in live)
    domain_counts = Counter()
    for r in live:
        for d in r.get("domains", []):
            domain_counts[d] += 1

    return {
        "total_saves": len(live),
        "sources": ["instagram", "catalog"],
        "top_types": type_counts.most_common(),
        "top_domains": domain_counts.most_common(10),
        "tier_distribution": dict(tier_counts.most_common()),
        "save_profile": build_save_profile(live, tiers),
    }


def main():
    records = load_catalog()
    curation = load_curation()
    curation_tiers = curation.get("tiers", {})

    live = [r for r in records if not r.get("drop", False)]

    sections = [
        {
            "id": "clone-repos",
            "icon": "\U0001f9f0",
            "title": "Clone These Repos",
            "subtitle": "Highest-value repos across your saves. S and A tier only.",
            "items": build_clone_repos(live, curation_tiers),
        },
        {
            "id": "install-tools",
            "icon": "\u26a1",
            "title": "Install These Tools",
            "subtitle": "Tools worth setting up right now.",
            "items": build_install_tools(live, curation_tiers),
        },
        {
            "id": "read-guides",
            "icon": "\U0001f4d8",
            "title": "Read These Deep-Dives",
            "subtitle": "We wrote guides for the posts worth digging into.",
            "items": build_read_guides(live, curation_tiers),
        },
        {
            "id": "try-techniques",
            "icon": "\U0001f527",
            "title": "Try These Techniques",
            "subtitle": "Techniques and workflows you saved but probably haven't tried.",
            "items": build_try_techniques(live, curation_tiers),
        },
        {
            "id": "bookmark-platforms",
            "icon": "\U0001f310",
            "title": "Bookmark These Platforms",
            "subtitle": "Services and platforms worth keeping in your toolkit.",
            "items": build_bookmark_platforms(live, curation_tiers),
        },
        {
            "id": "design-resources",
            "icon": "\U0001f3a8",
            "title": "Design & Art Resources",
            "subtitle": "Archives, collections, and inspiration.",
            "items": build_design_resources(live, curation_tiers),
        },
        {
            "id": "watch-out",
            "icon": "\u26a0\ufe0f",
            "title": "Teasers & DM-Bait",
            "subtitle": "Things that sounded good but the content is gated or thin.",
            "items": build_watch_out(live, curation_tiers),
        },
    ]

    output = {
        "generated": str(date.today()),
        "stats": build_stats(live, curation_tiers),
        "sections": sections,
    }

    with open(OUT, "w") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Report
    total_items = sum(len(s["items"]) for s in sections)
    print(f"Generated {OUT}")
    print(f"Total action items: {total_items}")
    print(f"Sections:")
    for s in sections:
        print(f"  {s['icon']} {s['title']}: {len(s['items'])} items")


if __name__ == "__main__":
    main()
