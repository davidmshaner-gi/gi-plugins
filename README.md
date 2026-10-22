# Grounded Intelligence Plugins

Claude plugins for [Grounded Intelligence](https://groundedintelligence.io) clients.

Grounded Intelligence coaches a company's leaders, one on one, until they build their own AI
co-workers, then stays on as the company's Chief AI Officer. Most of what our clients build lives
in their own Claude accounts. This marketplace holds the shared skills we maintain for a client
when a team needs the same tool across many desks.

## What's here

| Plugin | What it does |
|---|---|
| `lee-internal-comps` | A brokerage team's research toolkit: lease and sale comps, demographics, owner and parcel lookups, traffic counts, drive times, site infrastructure, tenants in the market, and branded output. Each skill documents itself in its own `SKILL.md`. |

## Install

In Claude Cowork: **Customize → Plugins → Add marketplace** and paste:

```
davidmshaner-gi/gi-plugins
```

Then click **Install** on the plugin you've been authorized for.

## Authorization

Plugins in this marketplace require client-specific authorization. If you haven't been set up for one, contact `david@groundedintelligence.io`.

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

