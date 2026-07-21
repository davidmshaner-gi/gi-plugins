#!/usr/bin/env bash
# connector-auth-guidance.test.sh
#
# Guard for gi-plugins#117: every lee-internal-comps skill that rides the
# lee-raleigh connector must carry the canonical connector-auth block —
# (1) attempt the tool call BEFORE any claim about authorization (the
# Bonner 2026-07-15 false-refusal incident), and (2) broker-legible
# reconnect copy on a genuine tool-level auth error (the James Bailey
# 2026-07-08 grant-drop incident).
#
# Canonical source: plugins/lee-internal-comps/shared/connector-auth.md
# (the text between the BEGIN/END markers). Each covered SKILL.md must
# contain that block VERBATIM between the same markers — edit the shared
# file, then run scripts/sync-connector-auth.sh to propagate. This test
# fails on any drift, any missing block, and on the retired misleading
# copy ("try again in a few minutes" as an auth-failure response).
#
# Coverage: every skill under plugins/lee-internal-comps/skills/ EXCEPT
# the explicit no-connector list below. A NEW skill is covered by
# default — if it genuinely doesn't touch the lee-raleigh connector, add
# it to NO_CONNECTOR_SKILLS with a comment saying why.
#
# Exit 0 = clean. Exit 1 = drift / missing block / retired copy present.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PLUGIN="$ROOT/plugins/lee-internal-comps"
CANON="$PLUGIN/shared/connector-auth.md"
BEGIN='<!-- BEGIN CONNECTOR-AUTH BLOCK (canonical: shared/connector-auth.md — edit there, then scripts/sync-connector-auth.sh) -->'
END='<!-- END CONNECTOR-AUTH BLOCK -->'

# Skills that make NO lee-raleigh connector calls (verified at gi-plugins#117
# pickup, 2026-07-20): lee-branding ships brand assets bundled on disk;
# process-mapping is a guided interview with no MCP tools.
NO_CONNECTOR_SKILLS=("lee-branding" "process-mapping")

fail=0
report() { printf 'FAIL  %s\n' "$1" >&2; fail=1; }
ok()     { printf 'ok    %s\n' "$1"; }

extract_block() { # extract_block <file> — prints the marked block, inclusive
  awk -v b="$BEGIN" -v e="$END" '
    $0 == b {found=1}
    found   {print}
    $0 == e {exit}
  ' "$1"
}

# 0. Canonical file exists and has a well-formed block
if [[ ! -f "$CANON" ]]; then
  report "canonical file missing: $CANON"
  exit 1
fi
CANON_BLOCK="$(extract_block "$CANON")"
if [[ -z "$CANON_BLOCK" ]] || ! grep -qF -- "$END" <<<"$CANON_BLOCK"; then
  report "canonical file has no complete BEGIN/END block: $CANON"
  exit 1
fi
ok "canonical block ($CANON)"

# 1. Every covered SKILL.md carries the canonical block verbatim
for dir in "$PLUGIN"/skills/*/; do
  skill="$(basename "$dir")"
  skip=""
  for x in "${NO_CONNECTOR_SKILLS[@]}"; do
    [[ "$skill" == "$x" ]] && skip=1
  done
  md="$dir/SKILL.md"
  if [[ -n "$skip" ]]; then
    # No-connector skills must NOT carry the block (it would be noise/drift bait)
    if grep -qF -- "$BEGIN" "$md" 2>/dev/null; then
      report "$skill — listed as no-connector but carries the connector-auth block"
    else
      ok "$skill (no-connector, block absent as expected)"
    fi
    continue
  fi
  if [[ ! -f "$md" ]]; then
    report "$skill — no SKILL.md"
    continue
  fi
  SKILL_BLOCK="$(extract_block "$md")"
  if [[ -z "$SKILL_BLOCK" ]]; then
    report "$skill — connector-auth block missing (run scripts/sync-connector-auth.sh)"
  elif [[ "$SKILL_BLOCK" != "$CANON_BLOCK" ]]; then
    report "$skill — connector-auth block DRIFTED from canonical (run scripts/sync-connector-auth.sh)"
  else
    ok "$skill"
  fi
done

# 2. The retired misleading copy must be gone: "try again in a few minutes"
#    was the owner-mailing-list "Connector unavailable" response, which strands
#    a broker whose real problem is a dropped auth grant (James Bailey case).
#    A transient-outage retry line is only acceptable when the same table row
#    explicitly scopes itself to NON-auth failures.
while IFS= read -r hit; do
  file="${hit%%:*}"
  if ! grep -qF -- "$BEGIN" "$file"; then
    report "retired copy: 'try again in a few minutes' in ${file#"$ROOT"/} without the connector-auth block"
  elif ! grep -q "not an auth" "$file"; then
    report "'try again in a few minutes' in ${file#"$ROOT"/} is not scoped to non-auth failures"
  else
    ok "transient-retry line in ${file#"$ROOT"/} is auth-scoped"
  fi
done < <(grep -rlF "try again in a few minutes" "$PLUGIN"/skills/*/SKILL.md 2>/dev/null | sed 's/$/:/')

if [[ "$fail" -ne 0 ]]; then
  echo "connector-auth-guidance: FAIL" >&2
  exit 1
fi
echo "connector-auth-guidance: PASS"
