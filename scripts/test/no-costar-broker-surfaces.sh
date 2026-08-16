#!/usr/bin/env bash
# no-costar-broker-surfaces.sh
#
# Compliance guard (GitHub issue #6, per Bonner): the "CoStar" brand string
# must NOT appear on any broker-facing surface of the lee-internal-comps
# plugin — descriptions/frontmatter, READMEs, or the strings written into
# broker deliverables (Excel Methodology sheet, email body).
#
# Scope decision (David, 2026-06-02): generic-ize CoStar -> "external",
# keep "Dealius". Originally the data-contract identifiers were exempt; the
# 2026-08-14 policy extended scope repo-wide and lee#442 (2026-08-15) renamed
# the live contract itself (external_property_id/_url, ASSET_TYPE_TO_EXTERNAL_*),
# so nothing carries the string anymore. This guard stays as the broker-surface
# pin; scripts/test/source-neutrality.sh covers the whole repo.
#
# This guard therefore checks the *advertising + deliverable* surfaces only,
# not a blanket repo grep.
#
# Exit 0 = clean. Exit 1 = a broker-facing surface still carries "CoStar".
set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PLUGIN="$ROOT/plugins/lee-internal-comps"
fail=0

report() { printf 'FAIL  %s\n' "$1" >&2; fail=1; }
ok()     { printf 'ok    %s\n' "$1"; }

# 1. Plugin manifest description (surfaced in plugin listings)
if jq -er '.description' "$PLUGIN/.claude-plugin/plugin.json" | grep -qi costar; then
  report "plugins/lee-internal-comps/.claude-plugin/plugin.json — description mentions CoStar"
else
  ok "plugin.json description"
fi

# 2. Marketplace descriptions (surfaced in the marketplace)
if jq -er '.description, (.plugins[].description)' "$ROOT/.claude-plugin/marketplace.json" | grep -qi costar; then
  report ".claude-plugin/marketplace.json — a description mentions CoStar"
else
  ok "marketplace.json descriptions"
fi

# 3. Repo README (the lee-internal-comps capabilities row) — all prose
if grep -qi costar "$ROOT/README.md"; then
  report "README.md — mentions CoStar"
else
  ok "README.md"
fi

# 4. Plugin README — all prose, broker/installer facing
if grep -qi costar "$PLUGIN/README.md"; then
  report "plugins/lee-internal-comps/README.md — mentions CoStar"
else
  ok "plugin README.md"
fi

# 5. SKILL.md frontmatter `description:` lines (the broker-visible skill blurb).
#    Bodies may keep CoStar in data-contract/terminology sections (out of scope);
#    the frontmatter description is the advertising line and must be clean.
for skill in internal-comps external-comps; do
  desc=$(awk '/^description:/{print; exit}' "$PLUGIN/skills/$skill/SKILL.md")
  if printf '%s' "$desc" | grep -qi costar; then
    report "skills/$skill/SKILL.md — frontmatter description mentions CoStar"
  else
    ok "skills/$skill/SKILL.md description"
  fi
done

# 6. internal-comps SKILL.md body — its only CoStar use is broker-facing prose
#    ("Don't apply this skill to..."), so the whole file should be clean.
if grep -qi costar "$PLUGIN/skills/internal-comps/SKILL.md"; then
  report "skills/internal-comps/SKILL.md — body mentions CoStar (prose, in scope)"
else
  ok "internal-comps SKILL.md body"
fi

# 7. Deliverable strings emitted to the broker by helpers.py (Excel Methodology
#    "Source"/"Caveat" rows and the email body). These two phrases cover all
#    three display strings; the column-map identifiers are intentionally exempt.
HELPERS="$PLUGIN/skills/external-comps/helpers.py"
if grep -qi "costar weekly snapshot" "$HELPERS"; then
  report "external-comps/helpers.py — broker deliverable string says 'CoStar weekly snapshot'"
else
  ok "helpers.py deliverable 'Source'/email string"
fi
if grep -qi "external costar data" "$HELPERS"; then
  report "external-comps/helpers.py — broker Caveat string says 'External CoStar data'"
else
  ok "helpers.py deliverable 'Caveat' string"
fi

# 8. Verbatim broker reply templates in SKILL.md (markdown blockquote lines,
#    flagged "reply verbatim" / shown to the broker). Bodies may keep CoStar in
#    data-contract sections, but anything the broker is told verbatim must not.
for skill in internal-comps external-comps; do
  if grep -nE '^[[:space:]]*>' "$PLUGIN/skills/$skill/SKILL.md" | grep -qi costar; then
    report "skills/$skill/SKILL.md — a verbatim broker reply (blockquote) mentions CoStar"
  else
    ok "skills/$skill/SKILL.md broker reply blockquotes"
  fi
done

if [[ $fail -eq 0 ]]; then
  echo "PASS — no CoStar brand on broker-facing surfaces"
fi
exit $fail
