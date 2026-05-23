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

echo "Renaming project from 'barista' to '$NEW_NAME'..."

# Rename directory if it exists
if [[ -d "src/barista" ]]; then
  mv "src/barista" "src/${NEW_NAME}"
  echo "✓ Renamed src/barista → src/${NEW_NAME}"
fi

# Find and replace in files (excluding git, venv, cache directories, and binary files)
find . \
  -not -path './.git/*' \
  -not -path './.venv/*' \
  -not -path '*/.*' \
  -not -path '*/__pycache__/*' \
  -not -path '*/.pytest_cache/*' \
  -not -path '*/node_modules/*' \
  -not -path '*/htmlcov/*' \
  -type f \
  ! -name '*.pyc' \
  ! -name '*.so' \
  ! -name '*.o' \
  -exec sed -i "s/barista/${NEW_NAME}/g" {} +

echo "✓ Replaced all occurrences of 'barista' with '$NEW_NAME'"
echo "Setup complete!"
