#!/usr/bin/env bash
# Deploy site/ contents to gh-pages branch for GitHub Pages.
# SAFE: works in a temp clone so .git in the main worktree is never touched.
#
# Usage: scripts/deploy-gh-pages.sh

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SITE_DIR="$PROJECT_DIR/site"
REMOTE=$(git -C "$PROJECT_DIR" remote get-url origin)
TMPDIR=$(mktemp -d)

trap 'rm -rf "$TMPDIR"' EXIT

echo "=== Deploy to gh-pages ==="
echo "Source: $SITE_DIR"
echo "Remote: $REMOTE"
echo "Temp:   $TMPDIR"
echo

# Clone just the gh-pages branch (or init fresh if it doesn't exist)
if git ls-remote --heads "$REMOTE" gh-pages | grep -q gh-pages; then
  git clone --branch gh-pages --single-branch --depth 1 "$REMOTE" "$TMPDIR/repo"
else
  mkdir "$TMPDIR/repo"
  cd "$TMPDIR/repo"
  git init
  git remote add origin "$REMOTE"
  git checkout --orphan gh-pages
fi

cd "$TMPDIR/repo"

# Clear old content (preserving .git)
find . -maxdepth 1 ! -name '.git' ! -name '.' -exec rm -rf {} +

# Copy site contents to repo root
cp -a "$SITE_DIR/." .

# .nojekyll skips Jekyll processing
touch .nojekyll

# Commit and push
git add -A
if git diff --cached --quiet; then
  echo "No changes to deploy."
else
  git commit -m "Deploy site to GitHub Pages — $(date -u '+%Y-%m-%d %H:%M UTC')"
  git push origin gh-pages
  echo
  echo "=== Deployed to gh-pages ==="
fi
