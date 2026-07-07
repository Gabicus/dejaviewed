#!/usr/bin/env bash
# Cumulative URL extraction — collects URLs at each scroll position and merges
# Handles IG DOM unloading by never relying on a single snapshot
set -euo pipefail

COLLECTION="$1"
URL="$2"
OUTFILE="data/${COLLECTION}_urls.json"
TMPFILE="/tmp/ab_cumulative_${COLLECTION}.txt"
AB="npx agent-browser"

> "$TMPFILE"

echo "[extract-cumulative] $COLLECTION: collecting URLs across scroll positions"

stable_rounds=0
prev_total=0

for i in $(seq 1 40); do
  # Extract current visible URLs
  raw=$($AB eval '(() => { const s = new Set(); document.querySelectorAll("a[href*=\"/p/\"], a[href*=\"/reel/\"]").forEach(a => { const h = a.getAttribute("href"); if (h) s.add(h); }); return JSON.stringify([...s]); })()' 2>/dev/null || echo '[]')

  # Append to cumulative file
  python3 -c "
import json, sys
raw = '''$raw'''
try:
    urls = json.loads(json.loads(raw))
except:
    try:
        urls = json.loads(raw)
    except:
        urls = []
for u in urls:
    print(u)
" >> "$TMPFILE" 2>/dev/null

  total=$(sort -u "$TMPFILE" | wc -l)
  echo "[extract-cumulative] scroll $i: cumulative unique = $total"

  if [ "$total" = "$prev_total" ]; then
    stable_rounds=$((stable_rounds + 1))
  else
    stable_rounds=0
  fi

  if [ "$stable_rounds" -ge 4 ]; then
    echo "[extract-cumulative] $COLLECTION: stable after 4 rounds at $total URLs"
    break
  fi

  prev_total=$total
  $AB scroll down 800 2>/dev/null
  sleep 1.5
done

# Dedupe and write final JSON
python3 -c "
import json
seen = set()
urls = []
for line in open('$TMPFILE'):
    u = line.strip()
    if not u: continue
    full = 'https://www.instagram.com' + u.replace('https://www.instagram.com', '') if not u.startswith('http') else u
    if full not in seen:
        seen.add(full)
        urls.append(full)
with open('$OUTFILE', 'w') as f:
    json.dump(urls, f, indent=2)
print(f'{len(urls)} unique URLs saved to $OUTFILE')
"

rm -f "$TMPFILE"
