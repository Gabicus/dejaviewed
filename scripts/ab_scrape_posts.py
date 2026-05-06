#!/usr/bin/env python3
"""Scrape post metadata from Instagram using agent-browser.
Uses 'get text' command to grab page text, then parses creator/caption."""
import json
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from cms import load_entries, write_entries, compute_crosslinks, write_crosslinks, _write_catalog_exports


def ab_cmd(cmd: str, timeout: int = 15) -> str:
    result = subprocess.run(
        f"npx agent-browser {cmd}",
        shell=True, capture_output=True, text=True, timeout=timeout,
        cwd=str(ROOT)
    )
    return (result.stdout + result.stderr).strip()


def parse_post_text(text: str) -> dict:
    """Parse creator, caption, date from agent-browser 'get text' output."""
    data = {}
    lines = text.split('\n')

    # Pattern: creator line, then "Original audio" or "Follow", then creator again, blank, time, caption
    # Or: creator, time, caption
    for i, line in enumerate(lines):
        stripped = line.strip()
        # Find the time marker (e.g., "3w", "2d", "1h", "April 4")
        if re.match(r'^\d+[wdhms]$', stripped) or re.match(r'^\w+ \d+$', stripped):
            # Creator is usually 1-2 lines above (after blank line)
            for j in range(i-1, max(i-4, -1), -1):
                candidate = lines[j].strip()
                if candidate and not candidate.startswith(('Follow', 'Original', 'Verified', ' ')):
                    if re.match(r'^[a-zA-Z0-9_.]+$', candidate):
                        data['creator'] = '@' + candidate
                        break

            # Caption starts right after the time line
            caption_lines = []
            for k in range(i+1, len(lines)):
                cl = lines[k].strip()
                # Stop at comments section indicators
                if re.match(r'^\d[\d,]* likes?$', cl):
                    break
                if cl == 'Reply':
                    break
                if re.match(r'^View all \d+ repl', cl):
                    break
                # Stop if we hit another username + time pattern (comment)
                if k+1 < len(lines) and re.match(r'^\d+[wdhms]$', lines[k+1].strip()):
                    is_user = re.match(r'^[a-zA-Z0-9_.]+$', cl)
                    if is_user:
                        break
                caption_lines.append(lines[k])

            if caption_lines:
                data['caption'] = '\n'.join(caption_lines).strip()[:3000]
            break

    # Media type via eval (fast, no DOM walk)
    try:
        mt = ab_cmd("eval 'document.querySelector(\"main video\") ? \"video\" : \"image\"'", timeout=5)
        data['media_type'] = mt.strip('"') if mt else 'image'
    except:
        data['media_type'] = 'image'

    # Date
    try:
        d = ab_cmd("eval 'document.querySelector(\"time[datetime]\") ? document.querySelector(\"time[datetime]\").getAttribute(\"datetime\") : \"\"'", timeout=5)
        d = d.strip('"')
        if d:
            data['date'] = d
    except:
        pass

    return data


def scrape_post(url: str) -> dict:
    """Navigate to post and extract metadata."""
    ab_cmd(f'open "{url}"', timeout=20)
    time.sleep(2)
    text = ab_cmd('get text "main"', timeout=10)
    if not text or 'Unknown command' in text:
        return {}
    return parse_post_text(text)


def main():
    entries = load_entries()
    placeholders = [
        e for e in entries
        if '[NEEDS ENRICHMENT]' in e.get('title', '')
        and e.get('url', '').startswith('https://www.instagram.com/')
    ]
    print(f"Found {len(placeholders)} placeholder entries to scrape")

    scraped_count = 0
    failed_count = 0
    for i, entry in enumerate(placeholders):
        url = entry['url']
        post_id = entry.get('post_id', '')
        print(f"[{i+1}/{len(placeholders)}] {post_id}", end=" ", flush=True)

        try:
            data = scrape_post(url)
            if data.get('caption'):
                entry['caption'] = data['caption']
                scraped_count += 1
                print(f"✓ {len(data['caption'])}ch", end="")
            else:
                print("✗ no caption", end="")
                failed_count += 1
            if data.get('creator'):
                entry['creator'] = data['creator']
                print(f" {data['creator']}", end="")
            if data.get('media_type'):
                entry['media_type'] = data['media_type']
            if data.get('date'):
                entry['date'] = data['date']
            print()
        except Exception as ex:
            print(f"✗ {ex}")
            failed_count += 1

        # Save progress every 20 posts
        if (i + 1) % 20 == 0:
            write_entries(entries)
            print(f"  [checkpoint] saved {scraped_count} captions so far")

        time.sleep(1)

    # Final save
    write_entries(entries)
    crosslinks = compute_crosslinks(entries)
    write_crosslinks(crosslinks)
    _write_catalog_exports(entries)
    print(f"\nDone: {scraped_count} captions, {failed_count} failed out of {len(placeholders)}")


if __name__ == "__main__":
    main()
