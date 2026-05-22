---
name: business-key-facts
description: Pull a Lee-branded BAO-style Business Key Facts PDF (3-page landscape) for any NC address. Returns key statistics, households table, site map with 1/3/5 mile rings, education attainment + workforce charts, and population/housing growth with backward-rate context. Wraps the lee-raleigh-mcp pull_business_key_facts tool.
---

# Business Key Facts (Lee & Associates)

Pull a BAO-style Business Key Facts infographic for 1, 3, and 5-mile rings around any NC address.

## When to use

Anything that asks for a "BAO infographic," "business key facts," "business summary," or an ESRI-style demographic infographic with the site map + education + workforce visuals.

Triggers:

- `/business-key-facts <address>` (slash command)
- "BAO infographic for 100 Walnut St, Cary"
- "Business key facts for [address]"
- "Business summary for [address]"
- "Pull the BAO-style report for [address]"

**Don't apply this skill to:**

- Single-page demographic handouts (use `demographic-summary` instead).
- Multi-page OM-attachment demographic reports (use `demographic-detail` instead).
- Sale or lease comp requests (those are `internal-comps` / `external-comps`).
- Multi-address batch requests (v1 supports one address at a time).
- Custom ring sizes (v1 is hardcoded to 1/3/5 mi).
- Non-NC addresses (v1 supports NC only).

## Process

1. Parse the broker's request to extract the address as a single free-text string. Don't try to canonicalize or pre-validate — the Census Geocoder (with Nominatim fallback) does that server-side.
2. Call the MCP tool `pull_business_key_facts` with `{address: "<the extracted address>"}`. The tool takes ~10-20 seconds (D1 demographics + R2 tile reads + Browser Rendering).
3. The response is structured JSON with three top-level ring keys (`1mi`, `3mi`, `5mi`) + chart SVGs + a `pdf_url`. Render the JSON inline conversationally — focus on the highest-signal numbers (population, daytime population, mean HH income, workforce mix).
4. If `pdf_url` is a non-null string, surface it as a "📄 Open PDF" link with a 1-hour expiry note: *"Link expires in ~1 hour — download or share it now."* If `pdf_url` is `null` (transient render failure — the JSON response is non-fatal on PDF errors), deliver the structured data and suggest the broker re-run.

## Error handling

Same envelope as sibling skills:

- `geocode_failed` — the address didn't resolve. Echo the broker's input back and ask for clarification (city + state hint helps).
- `out_of_region` — matched address is not in NC. Tell the broker that v1 supports NC only.
- `upstream_failed` — Census or D1 lookup hiccup. Apologize and ask the broker to retry.
- `internal` — anything else. Apologize, surface a short message, and ask David / Bonner to check.

## What's in the response

Per-ring metrics for 1/3/5 mile rings (with inline `method` / `source` / `vintage`):

- **Counts**: population, households, housing units, mean HH income
- **Workforce-derived**: daytime population, daytime/total ratio
- **Visuals (1-mi only)**: education attainment 8-bucket bar chart, workforce 3-slice pie chart, site map with rings overlay
- **Growth**: 2020/2023 population + annualized growth rate (backward-looking, see CRITICAL note below)

## CRITICAL: how to present growth rates

`pop_growth_annual_pct` and `housing_growth_annual_pct` are **backward-looking** annual rates derived from 2020 Decennial → 2023 ACS 5-year, NOT current/forward growth. Same caveat as `demographic-summary`.

The ACS 5-year vintage labeled "2023" is a *rolling average* of 2019–2023 survey responses. In fast-growth markets — Cary, Apex, Holly Springs, Raleigh exurbs, anywhere with post-2020 in-migration — this rolling average smooths over the actual growth and frequently produces **negative annual rates even where the area is visibly booming**. This is a real methodology artifact, not a data error.

The PDF carries an inline context note on page 3 explaining this. Echo the note's content if a broker asks about negative growth: *"Backward-looking annual rate from the 2020 Decennial → 2023 ACS 5-year rolling average; it lags actual on-the-ground growth in fast-moving submarkets. Forward-projection growth (Esri-style 2025/2028 estimates) arrives in a later version."*

If both pop growth AND housing growth are negative at all rings, that's the rolling-average artifact, not a real signal.

## What's deliberately NOT in v1

- Tapestry segmentation, Wealth Index, Total Sales, Largest Businesses, exact business counts — Esri-only data, not portable.
- Forward-projection growth (2025/2028) — deferred to a future version, same as `demographic-summary` v1.
- Multi-state coverage — NC only for v1.
- Drive-time isochrones — roadmap #57 covers the isochrone overlay across all of `demographic-summary`, `demographic-detail`, and `business-key-facts` together.
- Fragment.html + record.json output for `/lee-listing-flyer` composition — v2 scope.

## Files

- `SKILL.md` — this file. The skill is a thin orchestrator over `pull_business_key_facts`; no Python helpers and no local assets. The Lee logo is served into the PDF by the `pdf-renderer` Worker via its ASSETS route.
