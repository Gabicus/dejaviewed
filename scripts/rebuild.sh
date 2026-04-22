#!/usr/bin/env bash
# dejaviewed rebuild — one-call pipeline runner.
#
# Usage:
#   scripts/rebuild.sh \
#     --collections ai1=<url> ai2=<url> ai3=<url> ai4=<url> ai5=<url> \
#                   quant=<url> art-inspiration=<url> art-i-like=<url>
#
# Skip phases with --skip <phase>[,<phase>...]:
#   scrape,extract,catalog,context,digest,render,js
#
# Each phase is a separate Python module. Missing modules are skipped with a
# warning so this script can evolve as the pipeline fills in (digest.py and
# render_template.py aren't built yet at time of writing).

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

SKIP=""
declare -A COLLECTIONS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --skip) SKIP="$2"; shift 2 ;;
    --collections) shift
      while [[ $# -gt 0 && "$1" != --* ]]; do
        IFS='=' read -r name url <<< "$1"
        if [[ -n "$name" && -n "$url" ]]; then COLLECTIONS["$name"]="$url"; fi
        shift
      done
      ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

should_skip() { [[ ",$SKIP," == *",$1,"* ]]; }

run_py() {
  local phase="$1"; shift
  local script="$1"; shift
  if should_skip "$phase"; then echo "[skip] $phase"; return 0; fi
  if [[ ! -f "$script" ]]; then echo "[skip] $phase — $script not found"; return 0; fi
  echo "[run ] $phase — $script $*"
  python3 "$script" "$@"
}

echo "=== dejaviewed rebuild ==="
echo "Project: $PROJECT_DIR"
echo "Collections: ${!COLLECTIONS[*]}"
echo "Skip: ${SKIP:-<none>}"
echo

# Phase 1: scrape each collection
if ! should_skip scrape; then
  for name in "${!COLLECTIONS[@]}"; do
    url="${COLLECTIONS[$name]}"
    echo "[run ] scrape $name"
    if [[ -f scripts/scrape.py ]]; then
      python3 scripts/scrape.py --collection "$name" --url "$url"
    else
      echo "       (scripts/scrape.py not built yet — existing playwright workflow stands in)"
    fi
  done
fi

# Phase 2-7: the rest of the pipeline
run_py extract  scripts/extract.py
run_py catalog  scripts/build_catalog.py
run_py context  build_context.py
run_py digest   scripts/digest.py
run_py render   scripts/render_template.py
run_py js       scripts/catalog_js.py

echo
echo "=== done ==="
