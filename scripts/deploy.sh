#!/usr/bin/env bash
# Deploy site/ to Cloudflare Pages (manual fallback — auto-deploy handles most pushes).
#
# Usage: scripts/deploy.sh

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SITE_DIR="$PROJECT_DIR/site"

echo "=== Deploy to Cloudflare Pages ==="
echo "Source: $SITE_DIR"
echo

wrangler pages deploy "$SITE_DIR" --project-name dejaviewed --branch main
