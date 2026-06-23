---
name: site-infrastructure
description: Who serves this site? For any NC property address, pull the documented utility baseline a buyer or tenant asks about first - broadband (broker-verified row with FCC map link), electric utility (retail service territory, overlapping territories surfaced), water and sewer operators (county GIS + service-area maps + curated registry), and natural gas provider. Every row carries a confidence tag and source. Returns a flyer-ready si-card PDF plus structured JSON. Answers "who serves this site", "what utilities serve [address]", "site infrastructure for [address]", "is there water/sewer/gas at [site]" for industrial and land listings, BOVs, and OMs. Wraps the lee-raleigh-mcp pull_site_infrastructure tool.
---

# Site Infrastructure (Lee & Associates)

Answer one broker question: **"who serves this site, and what's documented?"** For any NC address, the five-row utility baseline - broadband, electric, water, sewer, gas - each row carrying the provider (or the right place to look), a confidence tag, and the source, plus a ready-to-place flyer card.

## When to use

Anything that asks which utilities or providers serve a property - especially industrial and land subjects where an OM, BOV, or buyer call needs the documented baseline.

Triggers:

- `/site-infrastructure <address>` (slash command)
- "Who serves 9725 Stone Quarry Rd, Sanford?"
- "What utilities serve [address]?"
- "Is there water and sewer at [site]?"
- "Who's the electric provider at [address]?"
- "Site infrastructure for [listing]"

**Don't apply this skill to:**

- Capacity questions - megawatts available, water gpm, sewer allocation, gas pressure. Those need a utility conversation; the card's footer says so. Quote the footer, don't guess.
- Demographics / population (use `demographic-summary` or `demographic-detail`).
- Traffic counts (use `vpd-lookup`).
- Nearby businesses / retail context (use `business-key-facts` or `nearby-businesses`).
- Parcel ownership / assessor records (use `parcel-lookup` or `owner-lookup`).
- Non-NC addresses (v1 is NC only).
- Multi-address batch requests (one address at a time).

## Process

1. Parse the broker's request to extract the address as a single free-text string. Don't canonicalize or pre-validate; the geocoder does that server-side.
2. Call the MCP tool `pull_site_infrastructure` with `{address: "<the extracted address>"}`.
3. The response is structured JSON:
   - `subject` - geocoded address, lat/lng, `county_fips` + `county_name`.
   - `layers` - one entry each for `broadband`, `electric`, `water`, `sewer`, `gas`. Each carries `provider` (null when the answer is a link), `confidence_label` (e.g. `parcel-verified`, `service area (2004 NC OneMap)`, `territory (HIFLD 2022)`, `county-level`, `broker-verified`, `see source`), `note`, `link` + `link_label`, and `sources` with vintages.
   - `fragment_html` - the composable si-card fragment (lee-listing-flyer composition path).
   - `pdf_url` - signed link to the rendered flyer card, or `null`.
4. If `pdf_url` is a non-null string, surface it as a "📄 Open PDF" link with an expiry note: *"Link expires soon - download or share it now."* That is the Lee-branded card a broker drops into a flyer / OM / BOV. If `pdf_url` is `null`, deliver the five rows inline and note the card couldn't render this time (suggest a re-run).

## How to present it

Lead with the five-row summary, one line per service, ALWAYS carrying the confidence tag - these are documented baselines, not capacity claims:

> **Electric:** Duke Energy Progress (investor-owned); Central Electric Membership Corp. (cooperative) - *territory (HIFLD 2022)*. Overlapping territories: confirm the serving utility.
> **Water:** TriRiver Water - *county-level* (mains mapped within 500 m, Lee County GIS).
> ...

Presentation rules:

- **Broadband is the broker's row to verify.** It always renders as *broker-verified* with the FCC National Broadband Map link as the starting point - no free source names the provider at parcel level. Say that plainly; never imply a broadband provider was looked up.
- **Overlapping electric territories are normal** (an investor-owned utility and a co-op often both map a point). Name every territory returned and tell the broker to confirm which one serves the parcel.
- **Vintages matter.** A `service area (2004 NC OneMap)` answer means boundaries have grown since - say so when it's the deciding row.
- **Never quote capacity.** The card's footer disclaimer ("Capacity figures ... require utility confirmation") is part of the deliverable.

## Error handling

Same envelope as sibling skills:

- `geocode_failed` - the address didn't resolve. Echo the broker's input back and ask for a city + state hint (rural and raw-land addresses sometimes need the nearest numbered address).
- `out_of_region` - matched address is not in NC. Tell the broker v1 supports NC only.
- `upstream_failed` - geocoder or data lookup hiccup. Apologize and ask the broker to retry.
- `rate_limited` (HTTP 429) - the daily cap (100 pulls/broker/day) is reached; it resets at midnight UTC.
- `internal` - anything else. Apologize, surface a short message, ask David / Bonner to check.

A degraded row (provider null, "see county GIS" / "see NCUC" link) is NOT an error - deliver it as the row's answer with its link. The card always has five rows.

## What's deliberately NOT in v1

- Capacity figures (MW, gpm, sewer allocation, gas pressure) - utility-conversation territory by design.
- Broadband provider names - the row is broker-verified with the FCC map as the aid.
- Non-NC coverage; multi-address batch.

## Files

- `SKILL.md` - this file. The skill is a thin orchestrator over `pull_site_infrastructure`; no Python helpers, no local assets.
- Numeric/copy parity reference: the `site-infrastructure` Python engine at `40_delivery/site-infrastructure/` (Wake Stone Deep River + cold Wilmington samples) in the parent GI repo.
