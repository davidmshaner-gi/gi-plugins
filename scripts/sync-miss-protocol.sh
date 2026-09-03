#!/usr/bin/env bash
# sync-miss-protocol.sh
#
# Propagates the canonical miss-protocol block
# (plugins/lee-internal-comps/shared/miss-protocol.md, between the
# BEGIN/END markers) into every lee-raleigh-riding SKILL.md — replacing
# an existing marked block in place, or appending one at the end of the
# file. Idempotent. Companion to scripts/test/miss-protocol-guidance.test.sh,
# which fails on any drift. (gi-plugins#164)
#
# The covered-skill set is "every skill except NO_CONNECTOR_SKILLS" and
# must match the test's list.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN="$ROOT/plugins/lee-internal-comps"
CANON="$PLUGIN/shared/miss-protocol.md"
BEGIN='<!-- BEGIN MISS-PROTOCOL BLOCK (canonical: shared/miss-protocol.md -- edit there, then scripts/sync-miss-protocol.sh) -->'
END='<!-- END MISS-PROTOCOL BLOCK -->'

NO_CONNECTOR_SKILLS=("process-mapping")

BLOCK="$(awk -v b="$BEGIN" -v e="$END" '
  $0 == b {found=1}
  found   {print}
  $0 == e {exit}
' "$CANON")"
if [[ -z "$BLOCK" ]]; then
  echo "ERROR: no canonical block found in $CANON" >&2
  exit 1
fi

for dir in "$PLUGIN"/skills/*/; do
  skill="$(basename "$dir")"
  for x in "${NO_CONNECTOR_SKILLS[@]}"; do
    [[ "$skill" == "$x" ]] && continue 2
  done
  md="$dir/SKILL.md"
  [[ -f "$md" ]] || { echo "WARN: $skill has no SKILL.md, skipping" >&2; continue; }

  tmp="$(mktemp)"
  if grep -qF -- "$BEGIN" "$md"; then
    # Replace the existing marked block in place. The block is multiline, so it
    # must travel via ENVIRON — `awk -v` cannot carry raw newlines.
    BLOCK="$BLOCK" awk -v b="$BEGIN" -v e="$END" '
      $0 == b {printf "%s\n", ENVIRON["BLOCK"]; inblock=1; next}
      inblock && $0 == e {inblock=0; next}
      inblock {next}
      {print}
    ' "$md" > "$tmp"
    action="updated"
  else
    # Append: blank line + block at end of file
    cat "$md" > "$tmp"
    [[ -n "$(tail -c 1 "$md")" ]] && printf '\n' >> "$tmp"   # ensure trailing newline
    printf '\n%s\n' "$BLOCK" >> "$tmp"
    action="appended"
  fi
  # Write through the existing file (not mv) so the target keeps its mode —
  # mktemp files are 0600 and a mv would clobber SKILL.md down from 0644.
  cat "$tmp" > "$md"
  rm -f "$tmp"
  echo "$action  $skill"
done
