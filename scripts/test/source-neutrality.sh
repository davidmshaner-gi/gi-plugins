#!/usr/bin/env bash
# source-neutrality.sh — gi-plugins, repo-wide
#
# Company policy (David, 2026-08-14, supersedes the broker-surfaces-only scope
# of #6): the comps database replaces the reference spreadsheets brokers
# already keep. What a broker chooses to load into it is their own
# prerogative — the schema accommodates it. Accordingly, no third-party
# comps-data vendor may be named anywhere in this repo: skill prose,
# deliverable strings, comments, manifests, CHANGELOG, filenames. Say
# "external" / "the external platform" instead.
#
# Brand tokens are assembled from fragments so this guard itself complies.
# Complements (does not replace) no-costar-broker-surfaces.sh, which pins the
# specific broker-visible surfaces.
#
# Exemptions (live MCP/D1 data-contract, tracked on lee-and-associates):
# lowercase identifier forms (…_property_id, …_property_url — response-shape
# field names the skills read) and client-export test fixtures.
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT"

B1="$(printf '%s%s' Co Star)"
B2="$(printf '%s%s' Loop Net)"
B3="$(printf '%s%s' Cre xi)"

hits=$(git grep -niE "${B1}|${B2}|${B3}" -- \
  ':!*.png' ':!*.pdf' ':!*.xlsx' \
  ':!*fixtures*' \
  ':!scripts/test/source-neutrality.sh' \
  ':!scripts/test/no-costar-broker-surfaces.sh' \
  2>/dev/null \
  | grep -viE "${B1}_(property_id|property_url)|https?://[^ ]*${B1}|no-${B1}-broker-surfaces" \
  || true)

if [[ -n "$hits" ]]; then
  echo "FAIL — vendor proper noun found outside data-contract exemptions:" >&2
  echo "$hits" >&2
  exit 1
fi
echo "PASS — source-neutral: no data-vendor proper nouns outside contract exemptions"
