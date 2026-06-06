#!/usr/bin/env bash
# Fail if CHANGELOG.md has no entries recorded under the [Unreleased] heading.
#
# A release must carry human-written notes, so this guards against tagging a
# version whose [Unreleased] section is empty. Run by `mise run changelog-check`
# and as a precondition inside `.tasks/release.sh`.
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
changelog="${repo_root}/CHANGELOG.md"

if [[ ! -f "$changelog" ]]; then
  echo "Error: CHANGELOG.md not found at ${changelog}" >&2
  exit 1
fi

# Extract the body between '## [Unreleased]' and the next '## [' heading, then
# check whether it contains at least one bullet entry ('- ...').
entries="$(
  awk '
    /^## \[Unreleased\]/ { inblock = 1; next }
    inblock && /^## \[/   { inblock = 0 }
    inblock && /^[[:space:]]*-[[:space:]]+/ { print }
  ' "$changelog"
)"

if [[ -z "$entries" ]]; then
  echo "Error: the [Unreleased] section of CHANGELOG.md has no entries." >&2
  echo "Add at least one '- ...' bullet under a category before releasing." >&2
  exit 1
fi

echo "CHANGELOG [Unreleased] section has entries."
