#!/usr/bin/env bash
# Print the CHANGELOG.md section body for a single released version.
#
# Usage: .tasks/changelog-extract.sh <version>   # e.g. 0.2.0  (no leading 'v')
#
# Emits the lines between the '## [<version>]' heading and the next '## ['
# heading, with surrounding blank lines trimmed. Used by the release workflow
# to build GitHub Release notes from the curated changelog.
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 <version>" >&2
  exit 2
fi

version="${1#v}"
repo_root="$(git rev-parse --show-toplevel)"
changelog="${repo_root}/CHANGELOG.md"

section="$(
  awk -v ver="$version" '
    $0 ~ "^## \\[" ver "\\]"        { inblock = 1; next }
    inblock && /^## \[/             { inblock = 0 }
    inblock && /^\[[^][]+\]:[ \t]/  { inblock = 0 }   # link-reference block
    inblock                         { print }
  ' "$changelog"
)"

# Trim leading and trailing blank lines.
section="$(printf '%s\n' "$section" | sed -e '/./,$!d' | tac | sed -e '/./,$!d' | tac)"

if [[ -z "$section" ]]; then
  echo "Error: no CHANGELOG.md section found for version ${version}." >&2
  exit 1
fi

printf '%s\n' "$section"
