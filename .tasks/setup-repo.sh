#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: .tasks/setup-repo.sh <new-project-name>"
  echo "Example: .tasks/setup-repo.sh myproject"
  exit 1
fi

NEW_NAME="$1"

# Validate the new name (alphanumeric and underscore only)
if ! [[ "$NEW_NAME" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]]; then
  echo "Error: Project name must start with a letter or underscore, and contain only alphanumeric characters and underscores."
  exit 1
fi

PROJECT_NAME=""
if [[ -f "pyproject.toml" ]]; then
  PROJECT_NAME="$(awk -F' = ' '
    $0 ~ /^\[project\]$/ { in_project = 1; next }
    in_project && $1 == "name" {
      gsub(/"/, "", $2);
      print $2;
      exit
    }
    in_project && $0 ~ /^\[/ { in_project = 0 }
  ' pyproject.toml)"
fi

SRC_NAME=""
if [[ -d "src" ]]; then
  SRC_NAME="$(find src -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort | head -n 1)"
fi

if [[ -z "$SRC_NAME" && -z "$PROJECT_NAME" ]]; then
  echo "Error: Cannot infer current project name from src/ or pyproject.toml."
  exit 1
fi

CURRENT_NAME="${SRC_NAME:-$PROJECT_NAME}"

echo "Renaming project from '$CURRENT_NAME' to '$NEW_NAME'..."

# Rename directory if it exists
if [[ -n "$SRC_NAME" && "$SRC_NAME" != "$NEW_NAME" && -d "src/${SRC_NAME}" ]]; then
  mv "src/${SRC_NAME}" "src/${NEW_NAME}"
  echo "✓ Renamed src/${SRC_NAME} → src/${NEW_NAME}"
fi

# Build legacy name variants (case variations + double-letter typos)
declare -A LEGACY_NAMES=()
add_legacy_name() {
  local name="$1"
  if [[ -n "$name" ]]; then
    LEGACY_NAMES["$name"]=1
  fi
}

add_variants() {
  local base="$1"
  add_legacy_name "$base"
  add_legacy_name "${base,,}"
  add_legacy_name "${base^^}"
  add_legacy_name "${base^}"

  for ((i=0; i<${#base}; i++)); do
    ch="${base:$i:1}"
    variant="${base:0:$((i+1))}${ch}${base:$((i+1))}"
    add_legacy_name "$variant"
  done
}

if [[ -n "$SRC_NAME" ]]; then
  add_variants "$SRC_NAME"
fi

if [[ -n "$PROJECT_NAME" && "$PROJECT_NAME" != "$SRC_NAME" ]]; then
  add_variants "$PROJECT_NAME"
fi

existing_variants=("${!LEGACY_NAMES[@]}")
for variant in "${existing_variants[@]}"; do
  add_legacy_name "${variant,,}"
  add_legacy_name "${variant^^}"
  add_legacy_name "${variant^}"
done

legacy_list=($(printf '%s\n' "${!LEGACY_NAMES[@]}" | sort))
perl_args=()
for legacy in "${legacy_list[@]}"; do
  if [[ "$legacy" != "$NEW_NAME" ]]; then
    perl_args+=("-e" "s/\\Q${legacy}\\E/${NEW_NAME}/g;")
  fi
done

# Find and replace in files (excluding git, venv, cache directories, and binary files)
if [[ ${#perl_args[@]} -gt 0 ]]; then
  find . \
    -not -path './.git/*' \
    -not -path './.venv/*' \
    -not -path '*/__pycache__/*' \
    -not -path '*/.pytest_cache/*' \
    -not -path '*/node_modules/*' \
    -not -path '*/htmlcov/*' \
    -type f \
    ! -name '*.pyc' \
    ! -name '*.so' \
    ! -name '*.o' \
    -exec perl -pi "${perl_args[@]}" {} +
fi

echo "✓ Replaced all occurrences of legacy names with '$NEW_NAME'"
echo "Setup complete!"
