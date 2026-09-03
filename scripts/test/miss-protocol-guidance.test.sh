#!/usr/bin/env bash
# miss-protocol-guidance.test.sh
#
# Guard for gi-plugins#164 (program lee#530): every lee-internal-comps skill
# that rides the lee-raleigh connector must carry the canonical miss-protocol
# block -- a miss is never final; follow the server's next[] (max 3 hops);
# show nearest[] as choices; ask the broker only on ask_broker; coverage wins;
# say what was tried -- and must NOT keep the retired per-tool prose that
# coached the model to punt ("ask for a city + state hint").
#
# Canonical source: plugins/lee-internal-comps/shared/miss-protocol.md
# (the text between the BEGIN/END markers). Each covered SKILL.md must
# contain that block VERBATIM between the same markers -- edit the shared
# file, then run scripts/sync-miss-protocol.sh to propagate. Same mechanism
# and same covered-skill set as connector-auth-guidance.test.sh; the two
# NO_CONNECTOR_SKILLS lists must match (either direction of drift fails).
#
# Exit 0 = clean. Exit 1 = drift / missing block / retired copy present.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PLUGIN="$ROOT/plugins/lee-internal-comps"
CANON="$PLUGIN/shared/miss-protocol.md"
BEGIN='<!-- BEGIN MISS-PROTOCOL BLOCK (canonical: shared/miss-protocol.md -- edit there, then scripts/sync-miss-protocol.sh) -->'
END='<!-- END MISS-PROTOCOL BLOCK -->'

# Skills that make NO lee-raleigh connector calls (verified at gi-plugins#117
# pickup, 2026-07-20): lee-branding shipped brand assets bundled on disk;
# process-mapping is a guided interview with no MCP tools.
#
# lee-branding LEFT this list on 2026-08-25 (lee#507). It now calls
# pull_brand_package before it renders anything, so it rides the connector
# like every other skill and needs the canonical auth block. Its assets are
# still bundled on disk -- the sandbox has no network for file reads -- but
# the brand VALUES are confirmed per-run over the connector.
# NB: scripts/sync-miss-protocol.sh carries the same list. Drift between the
# two lists in EITHER direction fails this test (sync skips a skill this test
# covers → "block missing"; this test excludes a skill sync stamps → "listed
# as no-connector but carries the block"), so the duplication is self-checking.
NO_CONNECTOR_SKILLS=("process-mapping")

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
      report "$skill — listed as no-connector but carries the miss-protocol block"
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
    report "$skill — $nblocks miss-protocol blocks (must be exactly one)"
    continue
  fi
  SKILL_BLOCK="$(extract_block "$md")"
  if [[ -z "$SKILL_BLOCK" ]]; then
    report "$skill — miss-protocol block missing (run scripts/sync-miss-protocol.sh)"
  elif [[ "$SKILL_BLOCK" != "$CANON_BLOCK" ]]; then
    report "$skill — miss-protocol block DRIFTED from canonical (run scripts/sync-miss-protocol.sh)"
  else
    ok "$skill"
  fi
done

# 2. The retired punt prose must be gone. These phrasings coached the model to
#    hand a miss back to the broker on the first zero (the class the lee#530
#    program exists to end). They may not appear anywhere OUTSIDE the canonical
#    block (which names none of them).
RETIRED=(
  "city + state hint"
  "city + NC hint"
  "ask for a cleaner address"
  "more specific spelling"
  "ask for clarification (city"
)
for md in "$PLUGIN"/skills/*/SKILL.md; do
  skill="$(basename "$(dirname "$md")")"
  outside="$(awk -v b="$BEGIN" -v e="$END" '
    $0 == b {inblock=1; next}
    inblock && $0 == e {inblock=0; next}
    !inblock {print}
  ' "$md")"
  for phrase in "${RETIRED[@]}"; do
    if grep -qF -- "$phrase" <<<"$outside"; then
      report "$skill -- retired punt prose present: \"$phrase\" (delete it; the miss-protocol block owns miss handling)"
    fi
  done
done

if [[ "$fail" -ne 0 ]]; then
  echo "miss-protocol-guidance: FAIL" >&2
  exit 1
fi
echo "miss-protocol-guidance: PASS"
