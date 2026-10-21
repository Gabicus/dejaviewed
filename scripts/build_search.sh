#!/usr/bin/env bash
# Static site search: mark indexable regions, then build the Pagefind index into site/pagefind/.
# Indexed: site/e/*.html (entries), site/guides/*.html, site/deeper/*.html — only pages carrying a
# data-pagefind-body region (render_entries.py + search_prep.py add them), so e/index.html and
# guides/index.html are skipped. Everything else (admin, board, graph*, legacy/) is outside the glob.
# site/pagefind/ is committed — the site is static-hosted.
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"
PAGEFIND_VERSION="1.3.0"   # pinned
python3 scripts/search_prep.py
rm -rf site/pagefind        # stale fragments would otherwise accumulate (only the generated index dir)
npx --yes "pagefind@${PAGEFIND_VERSION}" --site site --output-subdir pagefind \
  --glob "{e,guides,deeper}/*.html"
echo "[search] index: $(find site/pagefind -type f | wc -l) files, $(du -sh site/pagefind | cut -f1)"
