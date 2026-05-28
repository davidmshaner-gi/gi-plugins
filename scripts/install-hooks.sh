#!/usr/bin/env bash
# install-hooks.sh — wire scripts/git-hooks/ to git via core.hooksPath.
#
# Idempotent: safe to re-run. Run once after cloning gi-plugins.
set -uo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="scripts/git-hooks"

if [[ ! -d "$REPO_ROOT/$HOOKS_DIR" ]]; then
  echo "ERROR: $REPO_ROOT/$HOOKS_DIR not found" >&2
  exit 1
fi

current=$(git -C "$REPO_ROOT" config --local --get core.hooksPath || true)
if [[ "$current" == "$HOOKS_DIR" ]]; then
  echo "core.hooksPath already set to $HOOKS_DIR — nothing to do."
  exit 0
fi

git -C "$REPO_ROOT" config --local core.hooksPath "$HOOKS_DIR"
echo "Set core.hooksPath = $HOOKS_DIR for this clone."

# Sanity-check: ensure each hook in the dir is executable.
for f in "$REPO_ROOT/$HOOKS_DIR"/*; do
  [[ -f "$f" ]] || continue
  if [[ ! -x "$f" ]]; then
    chmod +x "$f"
    echo "  chmod +x $(basename "$f")"
  fi
done

echo "Done. Pre-commit hook is active for this clone."
