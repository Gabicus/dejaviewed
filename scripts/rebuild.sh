#!/usr/bin/env bash
# DejaViewed end-to-end rebuild.
#
#   scripts/rebuild.sh --collections ai8=2012637673459860 creative=18530277145076636 [--skip phase,phase]
#
# Collections are given as <name>=<instagram_collection_id> (the id is the last path segment of
# https://www.instagram.com/<user>/saved/<name>/<id>/). Discover ids with:
#   npx agent-browser eval 'JSON.stringify([...document.querySelectorAll("a[href*=\"/saved/\"]")].map(a=>a.getAttribute("href")))'
#
# Prereq: agent-browser attached to a logged-in Chrome over CDP (see SKILL.md "Phase 0 (v3)").
#
# Phases, in order (skip any with --skip):
#   pull        scripts/ig_collection_api.py   collection-feed API -> data/<name>_api.json (captions, media urls)
#   media       scripts/ig_download_media.py   thumbs -> site/thumb, videos/slides -> data/media (URLs expire!)
#   ingest      scripts/ingest_api.py          upsert rows with caption/creator/date/media_type
#   transcribe  scripts/transcribe.py          Whisper (GPU if available) from data/media/<post_id>.mp4
#   sync        scripts/cms.py rebuild         parquet -> catalog.json (MUST precede enrich)
#   enrich      scripts/enrich_entries.py      heuristic tools/techniques/domains/tier/titles
#   llm         scripts/llm_enrich_batches.py  export batches; run researcher/enrichment agents; merge
#   gate        scripts/quality_gate.py        hard gates: titles, S-rate, transcripts, thumbs
#   curate      scripts/curation_export.py     digest for the researcher curation pass (Phase 5c)
#   dives       scripts/deep_dives.py          auto + curated dives
#   deeper      scripts/deeper_dives.py        narrative pages for curated dives
#   guides      scripts/build_guides.py        full guide pages + guides/index.html
#   digest      scripts/digest.py              summaries.json / recommendations.json
#   rebuild     scripts/cms.py rebuild         crosslinks + exports
#   api         scripts/build_api.py           site/api/*.json, per-entry pages, sitemap.xml
#   context     build_context.py               context.md, llms.txt, llms-full.txt, ai-plugin.json
#   render      scripts/render_template.py     collection page HTML
#   js          scripts/catalog_js.py          window.__CATALOG wrappers for file:// previews
#
# Phases that need a human/agent in the loop (llm, curate) stop with instructions instead of running.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

declare -A COLLECTIONS=()
SKIP=""
MODEL="medium"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --collections) shift; while [[ $# -gt 0 && "$1" != --* ]]; do COLLECTIONS["${1%%=*}"]="${1#*=}"; shift; done ;;
    --skip) SKIP="$2"; shift 2 ;;
    --whisper-model) MODEL="$2"; shift 2 ;;
    *) echo "unknown arg: $1"; exit 1 ;;
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

echo "=== dejaviewed rebuild === $(date -Is)"
echo "Collections: ${!COLLECTIONS[*]:-<none>}   Skip: ${SKIP:-<none>}"

if [[ ${#COLLECTIONS[@]} -gt 0 ]] && ! should_skip pull; then
  args=(); for n in "${!COLLECTIONS[@]}"; do args+=("$n" "${COLLECTIONS[$n]}"); done
  run_py pull scripts/ig_collection_api.py "${args[@]}"
  if ! should_skip media; then
    for n in "${!COLLECTIONS[@]}"; do run_py media scripts/ig_download_media.py "data/${n}_api.json"; done
  fi
  if ! should_skip ingest; then
    for n in "${!COLLECTIONS[@]}"; do run_py ingest scripts/ingest_api.py "data/${n}_api.json" --collection "$n"; done
  fi
fi

run_py transcribe scripts/transcribe.py --all --local-only --model "$MODEL"
run_py sync       scripts/cms.py rebuild
run_py enrich     scripts/enrich_entries.py --sweep

if ! should_skip llm; then
  echo "[stop] llm — export batches, run enrichment agents per data/llm_batches/SPEC.md, then:"
  echo "       python3 scripts/llm_enrich_batches.py merge 'data/llm_batches/out_*.json'"
  echo "       re-run with --skip pull,media,ingest,transcribe,sync,enrich,llm"
  exit 0
fi

run_py gate   scripts/quality_gate.py
if ! should_skip curate; then
  run_py curate scripts/curation_export.py
  echo "[stop] curate — run the researcher pass (SKILL.md Phase 5c), append survivors to data/manual_dives.json, then"
  echo "       re-run with --skip pull,media,ingest,transcribe,sync,enrich,llm,gate,curate"
  exit 0
fi

run_py dives   scripts/deep_dives.py
run_py deeper  scripts/deeper_dives.py --all-curated
run_py guides  scripts/build_guides.py
run_py digest  scripts/digest.py
run_py rebuild scripts/cms.py rebuild
run_py api     scripts/build_api.py
run_py context build_context.py
run_py render  scripts/render_template.py
run_py js      scripts/catalog_js.py
run_py gate    scripts/quality_gate.py

echo "=== done === $(date -Is)"
