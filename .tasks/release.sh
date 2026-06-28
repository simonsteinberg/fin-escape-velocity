#!/usr/bin/env bash
# Cut a release: bump the version, roll the changelog, commit, tag, and push.
#
# Usage: mise run release -- {patch|minor|major}
#
# The pushed tag (vX.Y.Z) is what triggers .github/workflows/release.yml, which
# verifies the tagged commit and creates the GitHub Release. This script keeps
# pyproject.toml and the git tag in lockstep so the two never drift.
#
# The initial v0.1.0 release is published by tagging directly (see
# docs/VERSIONING.md); this script is for every release after the baseline.
set -euo pipefail

part="${1:-}"
case "$part" in
  patch | minor | major) ;;
  *)
    echo "Usage: mise run release -- {patch|minor|major}" >&2
    exit 2
    ;;
esac

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

# ── Guards ─────────────────────────────────────────────────────────
branch="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$branch" != "main" ]]; then
  echo "Error: releases must be cut from 'main' (currently on '${branch}')." >&2
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Error: working tree is not clean. Commit or stash changes first." >&2
  exit 1
fi

git fetch --quiet origin main
if [[ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]]; then
  echo "Error: local 'main' is not in sync with 'origin/main'." >&2
  exit 1
fi

# Require curated release notes and a green tree before touching the version.
.tasks/changelog-check.sh
mise run check

# ── Bump ───────────────────────────────────────────────────────────
# `mise` forces color (CLICOLOR_FORCE), so uv emits ANSI escape codes even when
# its output is captured. Strip them, or the codes leak into the tag name (which
# git then rejects) and the changelog headers.
strip_ansi() { sed -E $'s/\x1b\\[[0-9;]*m//g'; }
prev="$(uv version --short | strip_ansi)"
uv version --bump "$part"
new="$(uv version --short | strip_ansi)"
date="$(date +%F)"
echo "Bumping v${prev} -> v${new}"

# ── Roll the changelog ─────────────────────────────────────────────
# Promote [Unreleased] entries to a dated [new] section, open a fresh empty
# [Unreleased], and update the link references at the bottom of the file.
awk -v new="$new" -v prev="$prev" -v date="$date" '
  !did_head && /^## \[Unreleased\]/ {
    print
    print ""
    print "## [" new "] - " date
    did_head = 1
    next
  }
  /^\[Unreleased\]:/ {
    url = $0
    sub(/^\[Unreleased\]: /, "", url)
    base = url
    sub(/\/compare\/.*$/, "", base)
    print "[Unreleased]: " base "/compare/v" new "...HEAD"
    print "[" new "]: " base "/compare/v" prev "...v" new
    next
  }
  { print }
' CHANGELOG.md > CHANGELOG.md.tmp && mv CHANGELOG.md.tmp CHANGELOG.md

# ── Commit, tag, push ──────────────────────────────────────────────
git add pyproject.toml uv.lock CHANGELOG.md
git commit -m "chore(release): v${new}"
git tag -a "v${new}" -m "v${new}"
git push --follow-tags

echo "Released v${new}. The release workflow will publish the GitHub Release."
