---
name: demographics-report
description: Pull a 14-page Lee-branded Demographic and Income Profile for any NC address. Returns 1/3/5-mile rings with population/households/income/age/race breakdowns, four Esri-analog indices (Diversity, Median Net Worth, Wealth, Housing Affordability), 2020/2025/2030 projections, trend comparisons against State + US, four Chart.js charts per ring, plus a Lee-branded PDF (1-hour signed URL). Wraps the lee-raleigh-mcp pull_demographics_report tool.
---

# Demographics Report (Lee & Associates)

Pull a 14-page demographic and income profile for 1, 3, and 5-mile rings around any NC address. This is the OM-quality companion to the 3-page Infographic skill. Use this for investment package attachments; use the Infographic for quick broker handouts or email blasts.

## When to use

Anything that asks for a "demographic report," "demographic and income profile," or a deep demographic deliverable around a property address.

Triggers:

- `/demographics-report <address>` (slash command)
- "Pull a demographic report for 100 Walnut St, Cary"
- "I need the deep demographic for the OM at [address]"
- "Demographic and income profile of [address]"
- "Full demographic report for this site"

**Don't apply this skill to:**

- Quick broker handouts or email-blast deliverables -- use the `infographic` skill instead.
- Sale or lease comp requests (those are `internal-comps` / `external-comps`).
- Multi-address batch requests (v1 supports one address at a time).
- Custom ring sizes (v1 is hardcoded to 1/3/5 mi).
- Non-NC addresses (v1 supports NC only; v2 expands the coverage).

## Process

1. Parse the broker's request to extract the address as a single free-text string. Don't try to canonicalize or pre-validate -- the Census Geocoder does that server-side.
2. Call the MCP tool `pull_demographics_report` with `{address: "<the extracted address>"}`. The tool takes ~7-12 seconds (longer than the infographic -- the wider data pull plus 12 Chart.js renders in the headless browser).
3. The response is structured JSON with three top-level ring keys (`1mi`, `3mi`, `5mi`), demographic atoms grouped by concept (`age_buckets`, `income_brackets`, `race_hispanic`, `indices`, `trend_rows`, projections), plus `state` metadata (FIPS code + name).
4. Render the JSON inline conversationally -- focus on the highest-signal numbers (projected 2025 population, trend rates vs state/national, the four indices). Claude already handles ring-keyed objects well; no custom formatter needed.
5. If `pdf_url` is a non-null string, surface it as a "Open Report" link with a 1-hour expiry note: *"Link expires in ~1 hour -- download or share it now."* If `pdf_url` is `null` (transient render failure), deliver the JSON and tell the broker to re-run.

## Error handling

The tool returns structured errors:

- `geocode_failed` -- the address didn't resolve. Echo the input back, ask for clarification (city + state hint helps).
- `out_of_region` -- matched address is not in NC. Tell the broker v1 supports NC only; the team is expanding coverage as demand surfaces.
- `upstream_error` -- transient Census API or D1 issue. Re-run.

## Relationship to the Infographic skill

This skill and `infographic` share the same underlying data pipeline. They differ in the output artifact:

- **This skill (`demographics-report`)** produces a 14-page deep report with Chart.js charts, race/income breakdowns, 2020/2025/2030 projections, and the four Esri-analog indices. Use for investment OMs, board packets, and deep due-diligence work.
- **`infographic`** produces a 3-page tile-grid PDF with the core scalars only. Use for quick broker handouts, email blasts, or initial site scoping.

A broker can run both for the same address and pick the right artifact for the audience. No deprecation of the Infographic is planned -- field feedback (target window: late May 2026) will determine whether both stick around long-term.

## Files

- `SKILL.md` -- this file. The skill is a thin orchestrator over `pull_demographics_report`; no Python helpers.
