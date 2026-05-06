#!/usr/bin/env bash
# Extract all post URLs from an Instagram saved collection page using agent-browser
# Usage: ./ab_extract_urls.sh <collection_name> <collection_url>
set -euo pipefail

COLLECTION="$1"
URL="$2"
OUTFILE="data/${COLLECTION}_urls.json"
AB="npx agent-browser"

echo "[extract] Opening $COLLECTION: $URL"
$AB open "$URL" 2>/dev/null

sleep 3

prev_count=0
stable_rounds=0

while true; do
  count=$($AB eval '(() => { const s = new Set(); document.querySelectorAll("a[href*=\"/p/\"], a[href*=\"/reel/\"]").forEach(a => { const h = a.getAttribute("href"); if (h) s.add(h); }); return s.size; })()' 2>/dev/null)

  echo "[extract] $COLLECTION: $count posts found"

  if [ "$count" = "$prev_count" ]; then
    stable_rounds=$((stable_rounds + 1))
  else
    stable_rounds=0
  fi

  if [ "$stable_rounds" -ge 3 ]; then
    echo "[extract] $COLLECTION: no new posts after 3 scroll rounds, done"
    break
  fi

  prev_count=$count
  $AB scroll down 1500 2>/dev/null
  sleep 2
done

# Final extraction
$AB eval '(() => { const s = new Set(); document.querySelectorAll("a[href*=\"/p/\"], a[href*=\"/reel/\"]").forEach(a => { const h = a.getAttribute("href"); if (h) s.add("https://www.instagram.com" + h.replace(/^https:\/\/www\.instagram\.com/, "")); }); return JSON.stringify([...s]); })()' 2>/dev/null > "${OUTFILE}.raw"

python3 -c "
import json
raw = open('${OUTFILE}.raw').read().strip()
# agent-browser double-encodes: JSON string wrapping a JSON array
try:
    urls = json.loads(json.loads(raw))
except:
    urls = json.loads(raw)
with open('${OUTFILE}', 'w') as f:
    json.dump(urls, f, indent=2)
print(len(urls))
" > /tmp/ab_count.txt
rm -f "${OUTFILE}.raw"

final_count=$(cat /tmp/ab_count.txt)
echo "[extract] $COLLECTION: saved $final_count URLs to $OUTFILE"
