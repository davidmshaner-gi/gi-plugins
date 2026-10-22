# Grounded Intelligence Plugins

Public plugin marketplace for [Grounded Intelligence](https://groundedintelligence.io) client tooling.

## What's here

| Plugin | Skills | Description |
|---|---|---|
| `lee-internal-comps` | `internal-comps`, `external-comps`, `internal-and-external-comps`, `demographic-summary`, `demographic-detail`, `business-key-facts`, `owner-lookup`, `parcel-lookup`, `tenant-search`, `owner-mailing-list`, `add-comps`, `process-mapping`, `labor-shed`, `lee-flyer-brief`, `vpd-lookup`, `nearby-businesses`, `comp-map`, `development-pipeline`, `drive-time-isochrones`, `site-infrastructure`, `lee-branding`, `map-my-inbox` | Skills a client's brokers and analysts run in Claude: lease and sale comps from their own records and an external platform, demographic and business reports, parcel and owner lookups, tenant search, site and drive-time reports, branded deliverables, and guided process mapping. |

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

