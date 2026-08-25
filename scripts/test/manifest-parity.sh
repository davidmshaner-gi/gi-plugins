#!/usr/bin/env bash
# manifest-parity.sh (lee#496) -- the marketplace card and the plugin manifest
# must agree.
#
# `.claude-plugin/marketplace.json` is what a broker READS when browsing or
# syncing in Cowork; `plugins/<name>/.claude-plugin/plugin.json` is what the
# plugin ships. They carried byte-identical descriptions by convention only, so
# a capability added to one silently missed the other -- exactly what happened
# when county support landed in plugin.json alone. Convention is not a guard;
# this is.
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
FAIL=0

report() { echo "FAIL  $*"; FAIL=1; }
ok()     { echo "ok    $*"; }

MARKET="$ROOT/.claude-plugin/marketplace.json"

while IFS= read -r name; do
  manifest="$ROOT/plugins/$name/.claude-plugin/plugin.json"
  if [[ ! -f "$manifest" ]]; then
    report "$name — listed in marketplace.json but has no plugin.json"
    continue
  fi
  for field in version description; do
    a=$(jq -r --arg n "$name" '.plugins[] | select(.name==$n) | .'"$field" "$MARKET")
    b=$(jq -r ".$field" "$manifest")
    if [[ "$a" != "$b" ]]; then
      report "$name — $field differs between marketplace.json and plugin.json"
      echo "        marketplace: $a"
      echo "        plugin.json: $b"
    else
      ok "$name $field"
    fi
  done
done < <(jq -r '.plugins[].name' "$MARKET")

if [[ $FAIL -eq 0 ]]; then
  echo "manifest-parity: PASS"
else
  echo "manifest-parity: FAIL"
fi
exit $FAIL
