#!/usr/bin/env bash
# skill-contract-check.sh <skill-dir>
#
# Verifies that the SKILL.md frontmatter description in <skill-dir>
# advertises every capability that the sibling helpers.py implements.
#
# Mechanism: pipes both files into `claude -p` with a system prompt that
# encodes the contract. Parses the JSON response. Exits non-zero if any
# blocker-severity issue is reported.
#
# Pre-reqs:
#   - `claude` on PATH (Pro Max subscription; we never use the Anthropic
#     API key per project policy).
#   - `jq` on PATH.
#
# Exit codes:
#   0 — pass (description matches helpers, or no helpers.py to check)
#   1 — blocker issue reported (drift detected)
#   2 — internal error (missing files, bad JSON, etc.)
set -uo pipefail

SKILL_DIR="${1:-}"
if [[ -z "$SKILL_DIR" ]]; then
  echo "Usage: $0 <skill-dir>" >&2
  exit 2
fi
if [[ ! -d "$SKILL_DIR" ]]; then
  echo "ERROR: skill dir not found: $SKILL_DIR" >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROMPT_FILE="$SCRIPT_DIR/prompts/skill-contract-reviewer.md"
if [[ ! -f "$PROMPT_FILE" ]]; then
  echo "ERROR: reviewer prompt not found: $PROMPT_FILE" >&2
  exit 2
fi

SKILL_MD="$SKILL_DIR/SKILL.md"
HELPERS_PY="$SKILL_DIR/helpers.py"

if [[ ! -f "$SKILL_MD" ]]; then
  echo "ERROR: no SKILL.md in $SKILL_DIR" >&2
  exit 2
fi

# No helpers.py — out of scope for this check. The reviewer prompt also
# encodes this fallback, but we short-circuit here to avoid the API call.
if [[ ! -f "$HELPERS_PY" ]]; then
  echo "SKIP $SKILL_DIR — no helpers.py"
  exit 0
fi

USER_MSG=$(cat <<EOF
<skill_md path="$SKILL_MD">
$(cat "$SKILL_MD")
</skill_md>

<helpers_py path="$HELPERS_PY">
$(cat "$HELPERS_PY")
</helpers_py>
EOF
)

# Pipe via stdin per project convention; system prompt via flag.
RESPONSE=$(printf '%s' "$USER_MSG" | claude -p \
  --dangerously-skip-permissions \
  --output-format json \
  --model claude-sonnet-4-6 \
  --system-prompt "$(cat "$PROMPT_FILE")" 2>&1) || {
    echo "ERROR: claude CLI invocation failed" >&2
    echo "$RESPONSE" >&2
    exit 2
  }

# The claude CLI wraps the model output in its own envelope when
# --output-format json. Extract the .result field, which is the raw
# string the model returned — our schema'd JSON object.
INNER=$(printf '%s' "$RESPONSE" | jq -r '.result // empty')
if [[ -z "$INNER" ]]; then
  echo "ERROR: claude returned no result. Full envelope:" >&2
  printf '%s\n' "$RESPONSE" >&2
  exit 2
fi

# Defensive: strip any markdown code fences the model may add.
INNER=$(printf '%s' "$INNER" | sed -E 's/^```(json)?$//; s/```$//')

# Use has("pass") + tostring — naive `.pass // empty` treats `false` as
# null-like and would coerce a legit failing verdict to "missing field".
PASS=$(printf '%s' "$INNER" | jq -r 'if has("pass") then (.pass | tostring) else "" end')
if [[ -z "$PASS" ]]; then
  echo "ERROR: model returned non-conforming JSON (no .pass field):" >&2
  printf '%s\n' "$INNER" >&2
  exit 2
fi

if [[ "$PASS" == "true" ]]; then
  echo "PASS $SKILL_DIR"
  exit 0
fi

# Blocker(s) reported. Print them and exit 1.
echo "FAIL $SKILL_DIR — drift detected:"
printf '%s' "$INNER" | jq -r '.issues[] | "  [\(.severity)] \(.check_id): \(.evidence)\n    fix: \(.fix_hint)"'
exit 1
