# Grounded Intelligence Plugins

Public plugin marketplace for [Grounded Intelligence](https://groundedintelligence.io) client tooling.

## What's here

| Plugin | Skills | Description | Client |
|---|---|---|---|
| `lee-internal-comps` | `internal-comps`, `external-comps`, `internal-and-external-comps`, `demographic-summary`, `demographic-detail`, `business-key-facts`, `owner-lookup`, `daily-debrief`, `tenants-in-market`, `owner-mailing-list`, `add-comps`, `process-mapping`, `labor-shed`, `lee-flyer-brief`, `vpd-lookup`, `nearby-businesses`, `comp-map` | Internal (Dealius) and external lease & sale comps, plus a default `internal-and-external-comps` skill that returns one combined "all comps" deliverable (table + Excel + unified Source-tagged PDF) when a broker doesn't specify a source. Internal produces Excel + email drafts. External comps are reachable via typed MCP tools (`search_external_sale_comps`, `search_external_lease_comps`, `get_external_comp_detail`), backed by a weekly Excel ingest from Will. A broker-facing external-comps skill is forthcoming. Also includes single-page demographic summaries, multi-page Demographic and Income Profile reports, BAO-style Business Key Facts infographics, sub-second owner-of-record lookup (owner name + mailing address + assessor facts) for any property in Wake, Durham, New Hanover, or Lee NC, and daily-debrief (Will-only interview-style classification of yesterday's plugin sessions; feeds Friday usage rollup in #all-groundedintelligence), and tenants-in-market (scheduled ingest of Triangle Pairlist tenant-requirement emails into a shared, queryable store), and owner-mailing-list (deduplicated owner + mailing-address CSV for an area + criteria request, via Claude-for-Chrome against county ArcGIS parcel data — 19 NC counties), and add-comps (normalize a contributed comp set a broker pastes/forwards/uploads into the comps DB as a third source alongside Dealius + CoStar, queryable across all three via `pull_unified_comps`). Also includes process-mapping (a guided interview that turns any team member's repeatable process into a clean process-map document and hands it back to GI — CRE is firm context only, the user's function stays agnostic). | Lee & Associates |

## Install

In Claude Cowork: **Customize → Plugins → Add marketplace** and paste:

```
davidmshaner-gi/gi-plugins
```

Then click **Install** on the plugin you've been authorized for.

## Authorization

Plugins in this marketplace require client-specific authorization. If you haven't been pre-provisioned in the relevant client's broker registry, contact `david@groundedintelligence.io`.

## Pre-commit Hook

This repo ships a pre-commit hook that uses the `claude` CLI to verify
each skill's `SKILL.md` frontmatter `description:` field advertises every
capability the sibling `helpers.py` actually implements. It catches the
class of bug where the implementation supports a code path the
discoverability description omits — invisible at runtime until a user
asks for the missing capability.

**Install once after cloning:**

```bash
bash scripts/install-hooks.sh
```

This sets `core.hooksPath` to `scripts/git-hooks/` for this clone. Idempotent.

**How it works:** On commit, the hook collects every `plugins/*/skills/*/`
that has staged changes to `SKILL.md` or `helpers.py`. For each, it pipes
both files into `claude -p` with the reviewer system prompt at
`scripts/prompts/skill-contract-reviewer.md`. The prompt encodes a
growing list of numbered checks (one per past bug class). If the model
reports any `blocker`-severity issue, the commit is blocked.

**Bypass when intentional** (e.g. WIP branch): `git commit --no-verify`.

**Adding a new check** when a new bug class is discovered:

1. Append a numbered check to `scripts/prompts/skill-contract-reviewer.md`
   under "Numbered checks" — see the "How to grow this prompt over time"
   section of that file for the format.
2. Add a fixture to `scripts/test/fixtures/` exercising the new check.
3. Add a case to `scripts/test/skill-contract-check.test.sh`.
4. Run `bash scripts/test/skill-contract-check.test.sh` and confirm
   the new case passes alongside the existing ones.
5. Commit the new check + fixture + test case together.

**Cost:** zero per-call (uses the project's Pro Max subscription via
the `claude` CLI, never the Anthropic API key). Adds ~5–15s to commits
that touch plugin skills; no overhead on other commits.

