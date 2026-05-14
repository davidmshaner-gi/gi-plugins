---
name: infographic
description: Pull a 1/3/5-mile demographic infographic for any NC address. Returns population, households, income, education, workforce mix, daytime population, and growth rates with per-metric methodology metadata. Wraps the lee-raleigh-mcp pull_infographic tool. v1.0 returns structured JSON; v1.1 will add a Lee-branded PDF link.
---

# Intellisite Demographic Infographic (Lee & Associates)

Pull a demographic profile for 1, 3, and 5-mile rings around any NC address.

## When to use

Anything that asks for a "demographic profile" or an "infographic" around a property address. The phrasing is open — what matters is the intent.

Triggers:

- `/infographic <address>` (slash command)
- "Pull infographic for 100 Walnut St, Cary"
- "Demographic profile of 200 Main St, Raleigh"
- "Site report for [address]"
- "What does the demographic look like around [address]"

**Don't apply this skill to:**

- Sale or lease comp requests (those are `internal-comps` / `external-comps`).
- Multi-address batch requests (v1 supports one address at a time).
- Custom ring sizes (v1 is hardcoded to 1/3/5 mi).

## Process

1. Parse the broker's request to extract the address as a single free-text string. Don't try to canonicalize or pre-validate — the Census Geocoder does that server-side.
2. Call the MCP tool `pull_infographic` with `{address: "<the extracted address>"}`. The tool takes ~5-7 seconds.
3. The response is structured JSON with three top-level ring keys (`1mi`, `3mi`, `5mi`) plus metadata. Render it inline conversationally — Claude already handles ring-keyed objects well; no custom formatting helper is needed.
4. If the response has `pdf_url: null` (v1.0 behavior), say so explicitly — *"PDF rendering is coming in next release; today's deliverable is the data."* If `pdf_url` is a non-null string (v1.1), surface it as a "📄 Open PDF" link with the standard 1-hour expiry note.

## Error handling

The tool returns structured errors:

- `geocode_failed` — the address didn't resolve. Echo the broker's input back and ask for clarification (city + state hint helps).
- `out_of_region` — matched address is not in NC. Tell the broker that v1 supports NC only; the team will expand coverage as demand surfaces.
- `upstream_failed` — Census or TIGER API is having a moment. Apologize and ask the broker to retry in a few minutes.
- `internal` — anything else. Apologize, surface a short message, and ask David / Bonner to check.

## What's in the response

Per-ring metrics, each carrying inline `method` / `source` / `vintage`:

- **Counts**: population, households, housing units, mean & median household income, median home value, median age
- **Mix**: bachelor's or higher %, workforce office/services/trades %
- **Baseline**: Decennial 2020 + recent ACS 5yr pop + housing, with the annualized growth rate between them
- **LEHD-derived**: employee count, resident workers, daytime population (`total_pop - resident_workers + workplace_workers`), daytime ratio

`methodology_version` is the Bonner package version this Worker port is calibrated against. `methodology_doc` points at the design spec.

## What's deliberately NOT in v1

- Tapestry segmentation, Wealth Index, Total Sales, Largest Businesses in Area — Esri-only data, not portable.
- Forward-projection growth (e.g. "Population (2025)") — deferred to a future version.
- Multi-state coverage — NC only for v1.
- PDF rendering — arrives in v1.1.

## Files

- `SKILL.md` — this file. The skill is a thin orchestrator over `pull_infographic`; no Python helpers.
