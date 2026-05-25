#!/usr/bin/env bash
set -euo pipefail

current_branch="$(git rev-parse --abbrev-ref HEAD)"
if [[ "$current_branch" == "HEAD" ]]; then
  echo "Error: Detached HEAD. Check out a branch before running cleanup."
  exit 1
fi

declare -A keep_branches=(
  ["main"]=1
  ["develop"]=1
  ["$current_branch"]=1
)

mapfile -t worktree_refs < <(git worktree list --porcelain | awk '/^branch / { print $2 }')
for ref in "${worktree_refs[@]}"; do
  if [[ "$ref" == "refs/heads/"* ]]; then
    keep_branches["${ref#refs/heads/}"]=1
  fi
done

should_keep_branch() {
  local branch="$1"
  [[ -n "${keep_branches[$branch]+x}" ]]
}

mapfile -t local_branches < <(git for-each-ref --format '%(refname:short)' refs/heads)
for branch in "${local_branches[@]}"; do
  if ! should_keep_branch "$branch"; then
    git branch -D "$branch"
    echo "Deleted local branch: $branch"
  fi
done

mapfile -t remotes < <(git remote)
if [[ ${#remotes[@]} -eq 0 ]]; then
  echo "No git remotes found. Skipping remote branch cleanup."
  exit 0
fi

for remote in "${remotes[@]}"; do
  mapfile -t remote_refs < <(git for-each-ref --format '%(refname:short)' "refs/remotes/${remote}")
  for ref in "${remote_refs[@]}"; do
    branch="${ref#${remote}/}"
    if [[ "$branch" == "HEAD" ]]; then
      continue
    fi
    if ! should_keep_branch "$branch"; then
      if git ls-remote --heads "$remote" "$branch" | grep -q .; then
        git push "$remote" --delete "$branch"
        echo "Deleted remote branch: ${remote}/${branch}"
      else
        echo "Remote branch not found: ${remote}/${branch}"
      fi
    fi
  done
  git remote prune "$remote"
done
