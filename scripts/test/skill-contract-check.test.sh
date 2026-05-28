#!/usr/bin/env bash
# Test harness for scripts/skill-contract-check.sh.
# Runs the check against fixtures; asserts pass/fail.
#
# Each case prints PASS or FAIL plus a one-line reason. The script exits 1
# if any case fails. Intended as the fast inner loop: ~15s per check (one
# claude CLI call per fixture), no network beyond the claude subscription.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
CHECK_SCRIPT="$REPO_ROOT/scripts/skill-contract-check.sh"
FIXTURE_ROOT="$REPO_ROOT/scripts/test/fixtures"

FAILURES=0

run_case() {
  local name="$1"
  local fixture="$2"
  local expected_exit="$3"  # 0 = expected pass, 1 = expected fail (blocker reported)
  local actual_exit

  echo "--- $name (fixture: $fixture, expected exit=$expected_exit)"
  bash "$CHECK_SCRIPT" "$FIXTURE_ROOT/$fixture" > /tmp/sc-out.$$ 2>&1
  actual_exit=$?

  if [[ "$actual_exit" -eq "$expected_exit" ]]; then
    echo "PASS — exit code $actual_exit matched expected"
  else
    echo "FAIL — expected exit $expected_exit, got $actual_exit"
    echo "Output was:"
    sed 's/^/  /' /tmp/sc-out.$$
    FAILURES=$((FAILURES+1))
  fi
  rm -f /tmp/sc-out.$$
}

run_case "passing-skill should pass (description matches helpers)" \
  "passing-skill" 0

run_case "missing-capability-skill should fail (description omits sale)" \
  "missing-capability-skill" 1

run_case "no-helpers-skill should pass (no helpers.py = skip cleanly)" \
  "no-helpers-skill" 0

if [[ "$FAILURES" -eq 0 ]]; then
  echo ""
  echo "All cases passed."
  exit 0
else
  echo ""
  echo "$FAILURES case(s) failed."
  exit 1
fi
