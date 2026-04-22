#!/usr/bin/env python3
"""Enrich new catalog entries with classification data extracted from captions.

Applies heuristic rules + keyword matching to fill in:
  - AI entries: tier, type, summary, domains, tools, techniques
  - Art entries: tier, type, medium, style_tags, subject_matter, summary

Usage:
  python scripts/enrich_entries.py [--dry-run]
"""
import json, re, sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "site" / "catalog.json"

TOOL_KEYWORDS = {
    # Image gen
    "midjourney": "Midjourney", "mj": "Midjourney",
    "stable diffusion": "Stable Diffusion", "sd": "Stable Diffusion", "sdxl": "Stable Diffusion",
    "comfyui": "ComfyUI", "comfy": "ComfyUI",
    "flux": "Flux", "dall-e": "DALL-E", "dalle": "DALL-E",
    "magnific": "Magnific", "ideogram": "Ideogram",
    # LLMs / agents
    "claude": "Claude", "claude code": "Claude Code",
    "chatgpt": "ChatGPT", "gpt-4": "GPT-4", "gpt4": "GPT-4", "gpt-4o": "GPT-4o", "gpt-5": "GPT-5",
    "cursor": "Cursor", "copilot": "GitHub Copilot", "codex": "Codex",
    "openai": "OpenAI", "anthropic": "Anthropic", "gemini": "Gemini",
    "llama": "Llama", "mistral": "Mistral", "ollama": "Ollama",
    "qwen": "Qwen", "deepseek": "DeepSeek", "kimi": "Kimi",
    "nemotron": "Nemotron",
    # 3D / video
    "blender": "Blender", "unreal": "Unreal Engine", "unity": "Unity",
    "touchdesigner": "TouchDesigner", "td": "TouchDesigner",
    "runway": "Runway", "pika": "Pika", "kling": "Kling", "sora": "Sora",
    "luma": "Luma", "tripo": "Tripo", "meshy": "Meshy",
    "hunyuan3d": "Hunyuan3D", "hunyuan": "Hunyuan", "world labs": "World Labs",
    "veo": "Veo", "imagen": "Imagen", "higgsfield": "Higgsfield",
    "odyssey": "Odyssey", "hypersketch": "Hypersketch",
    # Audio
    "elevenlabs": "ElevenLabs", "eleven labs": "ElevenLabs",
    "suno": "Suno", "udio": "Udio", "whisper": "Whisper",
    # Design
    "figma": "Figma", "photoshop": "Photoshop", "illustrator": "Illustrator",
    "after effects": "After Effects", "premiere": "Premiere Pro",
    "procreate": "Procreate", "canva": "Canva",
    "shadcn": "shadcn/ui", "stitch": "Stitch",
    # Dev / infra
    "n8n": "n8n", "make.com": "Make", "zapier": "Zapier",
    "notion": "Notion", "obsidian": "Obsidian",
    "react": "React", "next.js": "Next.js", "nextjs": "Next.js",
    "python": "Python", "typescript": "TypeScript",
    "supabase": "Supabase", "firebase": "Firebase",
    "vercel": "Vercel", "docker": "Docker",
    "playwright": "Playwright", "puppeteer": "Puppeteer",
    # ML infra
    "huggingface": "Hugging Face", "hugging face": "Hugging Face",
    "lora": "LoRA", "controlnet": "ControlNet",
    "mediapipe": "MediaPipe", "kinect": "Kinect",
    # Trading / data
    "polymarket": "Polymarket", "hyperliquid": "Hyperliquid",
    "duckdb": "DuckDB", "pandas": "Pandas",
    # Misc platforms
    "archive.org": "Archive.org", "internet archive": "Archive.org",
    "pretext": "Pretext", "openscreen": "OpenScreen",
    "onyx": "Onyx", "geospy": "GeoSpy",
}

TECHNIQUE_KEYWORDS = {
    # Image
    "img2img": "img2img", "image to image": "img2img",
    "txt2img": "txt2img", "text to image": "txt2img",
    "inpainting": "inpainting", "outpainting": "outpainting",
    "upscale": "upscaling", "upscaling": "upscaling",
    "fine-tune": "fine-tuning", "fine tune": "fine-tuning", "finetune": "fine-tuning",
    "prompt engineering": "prompt engineering", "prompting": "prompt engineering",
    # Video / motion
    "rotoscop": "rotoscoping", "motion brush": "motion brush",
    "motion capture": "motion capture", "mocap": "motion capture",
    "lip sync": "lip sync", "lipsync": "lip sync",
    "video generation": "video generation", "text to video": "video generation",
    "keyframe": "keyframing", "node canvas": "node-based editing",
    # 3D
    "3d scan": "3D scanning", "photogrammetry": "photogrammetry",
    "gaussian splat": "gaussian splatting", "3dgs": "gaussian splatting",
    "nerf": "NeRF", "image to 3d": "image-to-3D", "text to 3d": "text-to-3D",
    # Audio
    "voice clone": "voice cloning", "voice cloning": "voice cloning",
    "music generation": "music generation", "text to music": "music generation",
    "transcription": "transcription", "speech to text": "transcription",
    # Dev / agents
    "workflow": "workflow automation", "automation": "automation",
    "api": "API integration",
    "rag": "RAG", "retrieval": "RAG",
    "agent": "AI agents", "agentic": "AI agents",
    "mcp": "MCP", "model context protocol": "MCP",
    "code generation": "code generation", "coding": "code generation",
    "parallel worktree": "parallel worktrees", "worktree": "parallel worktrees",
    "hook": "hooks/automation",
    # Style / creative
    "style transfer": "style transfer",
    "generative art": "generative art", "creative coding": "creative coding",
    "projection mapping": "projection mapping",
    "steganography": "steganography",
    # Quant
    "trading": "algorithmic trading", "algo": "algorithmic trading",
    "backtesting": "backtesting",
    "mean reversion": "mean reversion", "stat arb": "statistical arbitrage",
    "kalman filter": "Kalman filter", "kalman": "Kalman filter",
    "monte carlo": "Monte Carlo", "stochastic": "stochastic modeling",
    "hurst exponent": "Hurst exponent", "regime detection": "regime detection",
    "market making": "market making", "limit order": "limit orders",
    "arbitrage": "arbitrage",
}

DOMAIN_KEYWORDS = {
    # Creative
    "design": "design", "graphic design": "design", "editorial": "design",
    "layout": "design", "branding": "design", "logo": "design",
    "typography": "design", "poster": "design", "magazine": "design",
    "ui": "UI/UX", "ux": "UI/UX", "interface": "UI/UX", "dashboard": "UI/UX",
    "art": "art", "painting": "art", "illustration": "art",
    "sculpture": "art", "kinetic": "art", "mural": "art", "installation": "art",
    "printmaking": "art", "ceramics": "art", "textile": "art",
    "photography": "photography", "photo": "photography", "darkroom": "photography",
    "architecture": "architecture",
    "fashion": "fashion",
    # Media production
    "music": "music", "audio": "audio",
    "video": "video production", "film": "video production",
    "3d": "3D", "animation": "animation",
    "motion design": "motion design", "vfx": "VFX",
    "creative coding": "creative coding", "generative": "creative coding",
    # Business
    "marketing": "marketing", "brand": "branding",
    "ecommerce": "e-commerce", "e-commerce": "e-commerce",
    "gaming": "gaming", "game dev": "gaming",
    # Dev / infra
    "coding": "software development", "programming": "software development",
    "open source": "open source", "github": "open source",
    # Finance
    "trading": "finance/trading", "quant": "finance/trading", "finance": "finance/trading",
    "crypto": "crypto", "defi": "crypto", "web3": "crypto",
    "polymarket": "prediction markets", "prediction market": "prediction markets",
    # Knowledge
    "education": "education", "tutorial": "education",
    "archive": "archives", "public domain": "archives", "vintage": "archives",
    "reference": "reference", "resource": "reference",
    # AI specific
    "llm": "LLM", "language model": "LLM",
    "agent": "agents", "agentic": "agents",
    "prompt": "prompt engineering",
    "osint": "OSINT", "geolocation": "OSINT",
    "security": "security", "jailbreak": "security",
}

MEDIUM_KEYWORDS = {
    "oil": "oil", "acrylic": "acrylic", "watercolor": "watercolor",
    "sculpture": "sculpture", "ceramic": "ceramic", "clay": "ceramic",
    "collage": "collage", "mixed media": "mixed",
    "3d render": "3d", "cgi": "3d", "blender": "3d",
    "photograph": "photo", "shot on": "photo", "35mm": "photo", "analog": "photo",
    "digital art": "digital", "digital painting": "digital",
    "typography": "typography", "lettering": "typography", "type design": "typography",
    "motion": "motion", "animation": "motion",
    "mural": "mural", "fresco": "mural",
    "print": "print", "screenprint": "print", "risograph": "print",
    "embroidery": "textile", "textile": "textile", "fabric": "textile",
    "pencil": "drawing", "sketch": "drawing", "charcoal": "drawing", "ink": "drawing",
}


DOMAIN_CANONICAL = {
    "3d": "3D", "llm": "LLM", "prompt-eng": "prompt engineering",
    "video": "video production", "trading": "finance/trading",
    "data": "data science", "rag": "RAG", "nocode": "no-code",
    "image-gen": "image generation", "creative-coding": "creative coding",
    "signal-processing": "signal processing",
}


def canonicalize_domains(domains: list[str]) -> list[str]:
    out = set()
    for d in domains:
        out.add(DOMAIN_CANONICAL.get(d, d))
    return sorted(out)


def extract_keywords(text: str, keyword_map: dict) -> list[str]:
    if not text:
        return []
    lower = text.lower()
    found = set()
    for kw, canonical in keyword_map.items():
        if re.search(r'\b' + re.escape(kw) + r'\b', lower):
            found.add(canonical)
    return sorted(found)


def classify_type_from_caption(caption: str, collection: str, title: str = "") -> str:
    lower = ((caption or "") + " " + (title or "")).lower()
    if collection.startswith("art"):
        if any(w in lower for w in ["tutorial", "how to", "step by step", "workflow"]):
            return "resource"
        if any(w in lower for w in ["ui ", "ux ", "interface", "dashboard", "app design"]):
            return "design"
        if any(w in lower for w in ["poster", "branding", "logo", "layout", "book cover",
                                     "magazine", "editorial", "typography", "graphic design"]):
            return "design"
        if any(w in lower for w in ["inspire", "mood", "aesthetic", "reference", "vibe"]):
            return "inspiration"
        return "art"
    # Design detection across all collections
    if any(w in lower for w in ["design tool", "design system", "design skill", "ui component",
                                 "graphic design", "design engineer", "mockup", "prototype",
                                 "layout", "design reference", "designers", "design uplevel"]):
        return "design"
    if any(w in lower for w in ["archive", "public domain", "vintage", "magazine scan",
                                 "editorial layout", "design reference scan"]):
        return "design"
    if any(w in lower for w in ["tutorial", "how to", "step by step", "guide", "learn",
                                 "walkthrough", "masterclass"]):
        return "tutorial"
    if any(w in lower for w in ["demo", "simulation", "visualization", "visualize",
                                 "interactive", "playground"]):
        return "demo"
    if any(w in lower for w in ["tool", "app ", "platform", "launch", "release",
                                 "free ", "alternative", "open-source"]):
        return "tool"
    if any(w in lower for w in ["news", "update", "announce", "breaking", "leaked"]):
        return "news"
    if any(w in lower for w in ["repo", "github", "open source", "library", "npm",
                                 "pip install"]):
        return "repo"
    if any(w in lower for w in ["technique", "method", "approach", "framework",
                                 "pattern", "model", "algorithm"]):
        return "technique"
    if any(w in lower for w in ["inspiration", "aesthetic", "curated", "collection of"]):
        return "inspiration"
    return "resource"


def guess_tier(caption: str, tools: list, techniques: list, is_art: bool) -> str:
    if not caption:
        return "C"
    lower = caption.lower()
    signals = 0
    if len(caption) > 200:
        signals += 1
    if len(tools) >= 2:
        signals += 1
    if len(techniques) >= 1:
        signals += 1
    if any(w in lower for w in ["deep dive", "breakdown", "masterclass", "comprehensive"]):
        signals += 2
    if any(w in lower for w in ["step by step", "tutorial", "how to", "guide"]):
        signals += 1
    if any(w in lower for w in ["tip", "trick", "hack"]):
        signals += 0
    if is_art:
        if any(w in lower for w in ["process", "technique", "behind the scenes"]):
            signals += 1
    if signals >= 3:
        return "S"
    elif signals >= 2:
        return "A"
    elif signals >= 1:
        return "B"
    return "C"


def build_summary(entry: dict, tools: list, techniques: list) -> str:
    creator = entry.get("creator", "")
    caption = entry.get("caption", "")
    if not caption:
        return f"Post by @{creator}" if creator else ""

    first_line = caption.split("\n")[0].strip()
    if len(first_line) > 120:
        first_line = first_line[:117] + "..."

    parts = []
    if creator:
        parts.append(f"@{creator}")
    if tools:
        parts.append(f"uses {', '.join(tools[:3])}")
    if techniques:
        parts.append(f"demonstrates {', '.join(techniques[:2])}")

    if parts:
        return f"{first_line} — {'; '.join(parts)}."
    return first_line


def enrich_entry(entry: dict) -> dict:
    caption = entry.get("caption", "")
    collection = entry.get("source_collection", "")
    is_art = collection.startswith("art") or entry.get("type") == "art"

    tools = extract_keywords(caption, TOOL_KEYWORDS)
    techniques = extract_keywords(caption, TECHNIQUE_KEYWORDS)
    domains = extract_keywords(caption, DOMAIN_KEYWORDS)

    entry["tools"] = tools
    entry["techniques"] = techniques
    if is_art and "art" not in domains:
        domains.append("art")
    entry["domains"] = canonicalize_domains(domains)
    entry["type"] = classify_type_from_caption(caption, collection, entry.get("title", ""))
    creator = entry.get("creator", "")
    if creator.startswith("@"):
        entry["creator"] = creator.lstrip("@")
    entry["tier"] = guess_tier(caption, tools, techniques, is_art)
    entry["summary"] = build_summary(entry, tools, techniques)

    if is_art:
        medium = extract_keywords(caption, MEDIUM_KEYWORDS)
        entry["medium"] = medium[0] if medium else "unknown"
        entry["style_tags"] = []
        entry["subject_matter"] = ""
        entry["reference_for"] = []

    return entry


def enrich_sweep(entry: dict, force_reclassify: bool = False) -> dict:
    """Fill gaps + optionally reclassify types using expanded dictionaries."""
    caption = entry.get("caption", "")
    transcript = entry.get("transcript", "")
    title = entry.get("title", "")
    text = f"{title} {caption} {transcript}".strip()
    collection = entry.get("source_collection", "") or entry.get("collection", "")
    is_art = collection.startswith("art") or entry.get("type") == "art"

    # Always re-extract with latest dictionaries (merge, don't replace)
    new_tools = extract_keywords(text, TOOL_KEYWORDS)
    old_tools = entry.get("tools") or []
    entry["tools"] = sorted(set(old_tools + new_tools))

    new_tech = extract_keywords(text, TECHNIQUE_KEYWORDS)
    old_tech = entry.get("techniques") or []
    entry["techniques"] = sorted(set(old_tech + new_tech))

    new_dom = extract_keywords(text, DOMAIN_KEYWORDS)
    old_dom = entry.get("domains") or []
    merged_dom = list(set(old_dom + new_dom))
    if is_art and "art" not in merged_dom:
        merged_dom.append("art")
    entry["domains"] = canonicalize_domains(merged_dom)

    # Fix creator @ prefix
    creator = entry.get("creator", "")
    if creator.startswith("@"):
        entry["creator"] = creator.lstrip("@")

    if not entry.get("summary") or entry["summary"].startswith("Post by"):
        entry["summary"] = build_summary(entry, entry.get("tools", []), entry.get("techniques", []))

    if is_art and not entry.get("medium"):
        medium = extract_keywords(text, MEDIUM_KEYWORDS)
        entry["medium"] = medium[0] if medium else "unknown"

    # Reclassify type if forced or if current type is generic
    if force_reclassify or entry.get("type") in ("resource", ""):
        new_type = classify_type_from_caption(caption, collection, title)
        if new_type != "resource" or not entry.get("type"):
            entry["type"] = new_type

    # Only upgrade tier, never downgrade
    if entry.get("tier", "C") in ("C", ""):
        new_tier = guess_tier(text, entry.get("tools", []), entry.get("techniques", []), is_art)
        if new_tier != "C":
            entry["tier"] = new_tier
    return entry


def main():
    import argparse
    p = argparse.ArgumentParser(description="Enrich catalog entries with classification data")
    p.add_argument("--dry-run", action="store_true", help="Preview changes without saving")
    p.add_argument("--sweep", action="store_true", help="Re-enrich all entries (not just is_new)")
    p.add_argument("--reclassify", action="store_true", help="Force re-evaluate type for resource posts")
    args = p.parse_args()
    dry_run = args.dry_run
    sweep = args.sweep
    reclassify = args.reclassify

    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    entries = data["entries"]

    enriched = 0
    for e in entries:
        if not sweep and not e.get("is_new"):
            continue
        if sweep:
            enrich_sweep(e, force_reclassify=reclassify)
        else:
            enrich_entry(e)
        enriched += 1

    print(f"Enriched {enriched} entries")

    tier_dist = {}
    type_dist = {}
    for e in entries:
        if e.get("is_new"):
            t = e.get("tier", "C")
            tier_dist[t] = tier_dist.get(t, 0) + 1
            tp = e.get("type", "?")
            type_dist[tp] = type_dist.get(tp, 0) + 1

    print(f"Tier distribution: {tier_dist}")
    print(f"Type distribution: {type_dist}")

    if dry_run:
        print("Dry run — not saving")
        return

    from process_raw import build_stats, CATALOG as CAT_PATH, CATALOG_JS
    extra = build_stats(entries)
    wrapper = {
        "entries": entries,
        "stats": extra["stats"],
        "indices": extra["indices"],
        "generated_at": datetime.now().isoformat(),
    }
    CAT_PATH.write_text(json.dumps(wrapper, indent=2, ensure_ascii=False), encoding="utf-8")
    js = "window.__CATALOG = " + json.dumps(wrapper, ensure_ascii=False) + ";\n"
    CATALOG_JS.write_text(js, encoding="utf-8")
    print(f"Saved {len(entries)} entries to catalog.json + catalog.js")

    # Sync enriched data back to parquet CMS
    import subprocess
    print("[enrich] Syncing enriched data to parquet CMS...")
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "cms.py"), "migrate"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"[enrich] WARNING: cms.py migrate failed:\n{result.stderr}", file=sys.stderr)
    else:
        print("[enrich] Parquet sync complete")


if __name__ == "__main__":
    main()
