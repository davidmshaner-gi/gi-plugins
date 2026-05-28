---
name: labor-shed
description: Show the labor force around a commercial site sliced by industry, for any NC address. Returns the resident labor pool a tenant can recruit (LEHD LODES residence data) and the existing employer mix already in the area (LODES workplace data) for 1/3/5-mile rings, with the industrial-family workforce (manufacturing, wholesale, transportation & warehousing, construction) called out. Wraps the lee-raleigh-mcp pull_labor_shed tool.
---

# Labor Shed (Lee & Associates)

Show the workforce around a site, sliced by industry, for 1/3/5-mile rings around any NC address. Answers "who can a tenant recruit here" (resident labor pool) and "who is already here" (existing employer mix).

## When to use

Anything that asks about the labor force, workforce, or labor pool around a site, especially for an industrial / flex BOV or OM.

Triggers:

- `/labor-shed <address>` (slash command)
- "Labor shed for 7144 Deep River Rd, Sanford"
- "What's the labor pool around [address]?"
- "Is there an industrial workforce near [address]?"
- "Who can a tenant recruit at [address]?"
- "Workforce by industry for [address]"

**Don't apply this skill to:**

- General population / income handouts (use `demographic-summary`).
- Multi-page OM demographic reports (use `demographic-detail`).
- Business Key Facts infographics (use `business-key-facts`).
- Sale or lease comp requests (those are `internal-comps` / `external-comps`).
- Counts of *businesses* / *establishments* by industry. This tool reports the
  *workforce* (jobs and where workers live), not establishment counts.
- Multi-address batch requests (v1 supports one address at a time).
- Custom ring sizes or drive-time bands (v1 is 1/3/5 mi rings only).
- Non-NC addresses (v1 supports NC only).

## Process

1. Parse the broker's request to extract the address as a single free-text string. Don't canonicalize or pre-validate; the Census Geocoder does that server-side.
2. Call the MCP tool `pull_labor_shed` with `{address: "<the extracted address>"}`.
3. The response is structured JSON with three ring keys (`1mi`, `3mi`, `5mi`), each carrying a resident labor pool (`rac`) and existing employer mix (`wac`), sliced by NAICS sector, plus an industrial subtotal + share. Render inline conversationally, leading with the headline (5-mile) numbers: labor pool, industrial-eligible workforce + share, existing jobs, existing industrial jobs.
4. If `pdf_url` is a non-null string, surface it as a "📄 Open PDF" link with a 1-hour expiry note: *"Link expires in ~1 hour, download or share it now."* If `pdf_url` is `null`, deliver the structured data and suggest the broker re-run.

## How to present it

Lead with the broker question, not the table:

> Within 5 miles of [site], the resident labor pool is **X** workers, **Y (Z%)** of them already in industrial-family jobs (manufacturing, wholesale, transportation & warehousing, construction). There are **W** jobs already located in that radius, **V%** of them industrial, so the site sits inside an existing industrial cluster rather than a green-field labor market.

Then offer the per-ring or per-sector breakdown if they want it.

"Industrial" here means construction (NAICS 23), manufacturing (31-33), wholesale trade (42), and transportation & warehousing (48-49). Say so if a broker asks what counts.

## Error handling

Same envelope as sibling skills:

- `geocode_failed` — the address didn't resolve. Echo the broker's input back and ask for a city + state hint.
- `out_of_region` — matched address is not in NC. Tell the broker v1 supports NC only.
- `upstream_failed` — Census or D1 lookup hiccup. Apologize and ask the broker to retry.
- `internal` — anything else. Apologize, surface a short message, ask David / Bonner to check.

## What's deliberately NOT in v1

- Drive-time-band geometry (the local engine supports it; the Worker is rings-only until the isochrone overlay lands across all the demographic tools, roadmap #57). v1 is 1/3/5 mi rings.
- Establishment counts by NAICS (the BAO "businesses" stat) — needs County Business Patterns / QCEW, separate tracked work.
- Multi-state coverage — NC only for v1.
- Multi-address batch.

## Files

- `SKILL.md` — this file. The skill is a thin orchestrator over `pull_labor_shed`; no Python helpers, no local assets.
- Numeric parity reference: the `labor_shed` Python engine at `40_delivery/labor-shed/`. Worker port spec: `40_delivery/labor-shed/WORKER_PORT_SPEC.md`.
