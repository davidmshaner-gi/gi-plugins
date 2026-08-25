# Grounded Intelligence Plugins

Public plugin marketplace for [Grounded Intelligence](https://groundedintelligence.io) client tooling.

## What's here

| Plugin | Skills | Description | Client |
|---|---|---|---|
| `lee-internal-comps` | `internal-comps`, `external-comps`, `internal-and-external-comps`, `demographic-summary`, `demographic-detail`, `business-key-facts`, `owner-lookup`, `parcel-lookup`, `tenant-search`, `owner-mailing-list`, `add-comps`, `process-mapping`, `labor-shed`, `lee-flyer-brief`, `vpd-lookup`, `nearby-businesses`, `comp-map`, `development-pipeline`, `drive-time-isochrones`, `site-infrastructure`, `lee-branding` | Internal (Dealius) and external lease & sale comps -- searchable by city, by county (either spelling; the two books store counties oppositely and the Worker normalizes), or across the RDU market -- plus a default `internal-and-external-comps` skill that returns one combined "all comps" deliverable (table + Excel + unified Source-tagged PDF) when a broker doesn't specify a source. Internal produces Excel + email drafts. External comps are reachable via typed MCP tools (`search_external_sale_comps`, `search_external_lease_comps`, `get_external_comp_detail`), backed by a weekly Excel ingest from Will. A broker-facing external-comps skill is forthcoming. Also includes demographic summaries (1/3/5-mile by default or the broker's own radii, with a GI blended growth rate per ring), multi-page Demographic and Income Profile reports, BAO-style Business Key Facts infographics, sub-second owner-of-record lookup (owner name + mailing address + assessor facts) for any property in Wake, Durham, New Hanover, or Lee NC, and tenant-search (who's in the market for space — the query surface over the shared tenant-requirements pool, fed by an automated GI-operated Triangle Pairlist ingest — searches that shared pool by asset type, size (a single target_sf matched in a ±30% band, or a min/max window), location (a city, or a county that rolls up to its cities), or recency and returns matches with the originating broker's contact to pair a listing), and owner-mailing-list (deduplicated owner + mailing-address CSV for an area + criteria request, served in seconds from the NC OneMap statewide parcel mirror via pull_owner_mailing_list — 7 NC counties, no browser extension), and add-comps (normalize a contributed comp set a broker pastes/forwards/uploads into the comps DB as a third source alongside Dealius + external, queryable across all three via `pull_unified_comps`), and labor-shed by drive-time band ("workers living within a 30-minute drive", `pull_labor_shed` geometry drive_time), and drive-time-isochrones (how far you can get from a site in 5/10/15 minutes by car, on foot, or by bike — per-band reach areas and a Lee-branded map card PDF, with isochrone GeoJSON on request for downstream programs; wraps `pull_drive_time_isochrones`), and site-infrastructure (who serves this site: the five-row utility baseline for any NC address — broadband broker-verified with an FCC map link, electric territory with overlaps surfaced, water/sewer via county GIS -> service-area maps -> curated registry, gas via registry — each row confidence-tagged + sourced, with an si-card flyer fragment + component PDF). Also includes process-mapping (a guided interview that turns any team member's repeatable process into a clean process-map document and hands it back to GI — CRE is firm context only, the user's function stays agnostic). Also includes lee-branding (apply the official Lee & Associates brand — logo, brand red, Avenir Next fonts, and logo usage rules — to any deliverable, and set up the Lee design system in Claude Design; ships the official Lee brand package on disk and confirms it against the current one through `pull_brand_package` on every run, stopping rather than rendering when that call cannot be made). | Lee & Associates |

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

