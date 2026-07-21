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
# NB: scripts/sync-connector-auth.sh carries the same list. Drift between the
# two lists in EITHER direction fails this test (sync skips a skill this test
# covers → "block missing"; this test excludes a skill sync stamps → "listed
# as no-connector but carries the block"), so the duplication is self-checking.
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
  nblocks="$(grep -cF -- "$BEGIN" "$md" || true)"
  if [[ "$nblocks" -gt 1 ]]; then
    report "$skill — $nblocks connector-auth blocks (must be exactly one)"
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
#    a broker whose real problem is a dropped auth grant (the 2026-07-08
#    grant-drop incident). OUTSIDE the canonical block (which mentions the
#    phrase only to scope it), any line carrying the phrase must scope itself
#    to NON-auth failures on that same line ("not an auth ...").
for md in "$PLUGIN"/skills/*/SKILL.md; do
  skill="$(basename "$(dirname "$md")")"
  # Strip the canonical block region, then look for the phrase in what's left.
  hits="$(awk -v b="$BEGIN" -v e="$END" '
    $0 == b {inblock=1; next}
    inblock && $0 == e {inblock=0; next}
    !inblock {print}
  ' "$md" | grep -F "try again in a few minutes" || true)"
  [[ -z "$hits" ]] && continue
  while IFS= read -r line; do
    if ! grep -qF "not an auth" <<<"$line"; then
      report "$skill — 'try again in a few minutes' outside the block, not scoped to non-auth failures on its line: ${line:0:80}"
    else
      ok "$skill — transient-retry line outside the block is auth-scoped"
    fi
  done <<<"$hits"
done

if [[ "$fail" -ne 0 ]]; then
  echo "connector-auth-guidance: FAIL" >&2
  exit 1
fi
echo "connector-auth-guidance: PASS"
