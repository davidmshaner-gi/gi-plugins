#!/usr/bin/env bash
# sync-connector-auth.sh
#
# Propagates the canonical connector-auth block
# (plugins/lee-internal-comps/shared/connector-auth.md, between the
# BEGIN/END markers) into every lee-raleigh-riding SKILL.md — replacing
# an existing marked block in place, or appending one at the end of the
# file. Idempotent. Companion to scripts/test/connector-auth-guidance.test.sh,
# which fails on any drift. (gi-plugins#117)
#
# The covered-skill set is "every skill except NO_CONNECTOR_SKILLS" and
# must match the test's list.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PLUGIN="$ROOT/plugins/lee-internal-comps"
CANON="$PLUGIN/shared/connector-auth.md"
BEGIN='<!-- BEGIN CONNECTOR-AUTH BLOCK (canonical: shared/connector-auth.md — edit there, then scripts/sync-connector-auth.sh) -->'
END='<!-- END CONNECTOR-AUTH BLOCK -->'

NO_CONNECTOR_SKILLS=("lee-branding" "process-mapping")

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
  mv "$tmp" "$md"
  echo "$action  $skill"
done
