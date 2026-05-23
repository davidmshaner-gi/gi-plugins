---
name: owner-lookup
description: Look up the owner of record and owner mailing address for a US property address in the counties covered by the owner-graph bulk ingest (Wake, Durham, New Hanover, and Lee — NC). Returns the parcel's assessor record (owner name, mailing address, year built, lot size, building SF, assessed value, last sale, zoning, jurisdiction). Wraps the lee-raleigh-mcp owner_lookup tool.
---

# Owner Lookup (Lee & Associates)

Resolve a US street address to the owner of record + owner mailing address plus the parcel's assessor facts, by reading the Cloudflare D1 owner graph. Data is bulk-staged from county GIS endpoints; this skill never hits a county API at request time, so it's sub-second.

## When to use

Anything that asks "who owns X," "what's the mailing address for X," or "give me the assessor facts on X" for a property in the four covered NC counties.

Triggers:

- `/owner-lookup <address>` (slash command)
- "Who owns 100 Connemara Dr, Cary NC?"
- "Mailing address for 1500 W Main St, Durham"
- "Who's the owner of record at 201 N Front St, Wilmington?"
- "Owner + assessed value for [address]"

**Don't apply this skill to:**

- Addresses outside Wake, Durham, New Hanover, or Lee NC. Other counties land in v1.1.
- Phone or email for owners — those are NULL in v1 (contact enrichment is deferred).
- Portfolio rollups ("what else does this owner own?") — the graph supports it but a portfolio tool is a separate v1.1 skill.
- Owner history (prior deeds) — v1 returns the CURRENT owner only.
- Sale / lease comp requests (those are `internal-comps` / `external-comps`).
- Demographic profiles (those are `demographic-summary` / `demographic-detail` / `business-key-facts`).

## Process

1. Parse the broker's request to extract the address as a single free-text string. Comma-separated `street, city, state` is best; the engine normalizes (uppercases, strips punctuation, expands directionals and suffixes).
2. If the broker explicitly mentions the county OR the address is ambiguous in a way only county can disambiguate, pass `county` as one of: `Wake`, `Durham`, `NEW_HANOVER`, `Lee`.
3. Call the MCP tool `owner_lookup` with `{address: "<the extracted address>", county: "<county-or-omit>"}`. The tool is sub-second (indexed D1 lookup, no external APIs on the request path).
4. The response is a JSON parcel record. Render the broker-facing essentials inline conversationally — county, parcel_id, owner_raw, owner_mail_address, assessed_value_total, year_built, lot_size_acres, building_sf, land_use, last_sale_date, last_sale_price. Format the mailing address as multi-line (it's stored with embedded `\n`).
5. If the tool returns an error, fall through to the Error Handling section below.

## Error handling

The tool returns broker-legible error messages directly; surface them as-is and apologize if needed:

- **"No parcel found for ..."** — the address didn't match. Possible reasons: outside the covered counties (Wake, Durham, NHC, Lee NC), or the address needs city / state to disambiguate. Echo the input back and ask for a more specific spelling or county hint.
- **"Multiple parcels match ... pass a county to disambiguate"** — same street address exists in more than one covered county. The error lists the candidate counties; ask the broker which one.
- Anything else (HTTP error, timeout, etc.) — apologize, surface the short message, suggest a retry. Worst case, point the broker to the county's municipal GIS (Wake iMaps, Durham GoMaps, NHC GIS Map, Lee NC GIS) for manual lookup.

## What's in the response

For a matched parcel:

- **county** — `WAKE`, `DURHAM`, `NEW_HANOVER`, or `LEE`
- **parcel_id** — the county's canonical PIN
- **address** — the assessor's situs address (the on-file street + number)
- **owner_raw** — owner name(s) exactly as recorded by the assessor
- **owner_mail_address** — owner mailing address with embedded newlines (street, then city/state/zip line)
- **year_built**, **lot_size_acres**, **building_sf**, **assessed_value_total** — assessor's structural + valuation facts
- **land_use**, **zoning_code** — assessor's land-use classification and zoning code (zoning_code may be null for some parcels)
- **last_sale_date**, **last_sale_price** — most-recent recorded sale; null when never sold or not yet refreshed
- **jurisdiction** — the assessor's jurisdiction code (e.g., `CARY`, `RA`, `WC` for Wake; varies by county)

## CRITICAL: data freshness + scope

Data is **bulk-staged quarterly-ish** from each county's GIS endpoint, NOT live. There's a lag between when a property changes hands and when our copy reflects that. If a broker is making time-sensitive decisions (offer letters, deed work), they should always confirm against the county GIS at the moment of action.

### Per-county verification portals (use these in the response)

When the response includes a "confirm against …" link, use the per-county portal below, **and include the PIN explicitly** so the broker can paste it into the portal's search bar. None of these portals support deep-linking via URL query parameter (verified 2026-05-23 via Chrome DevTools), so the format is always "open portal + paste PIN."

| County | Portal | URL | How to use |
|---|---|---|---|
| **WAKE** | Wake iMaps | https://maps.raleighnc.gov/imaps/ | Paste the 10-digit PIN into the search bar labeled "Address, owner, PIN, or REID" |
| **DURHAM** | Durham County (dconc.gov) | https://dconc.gov/ | Navigate to Tax Administration → Property Search and paste the PIN |
| **NEW_HANOVER** | NHC etax | https://etax.nhcgov.com/ | Use the Property Search form and paste the PIN |
| **LEE** | Lee County GIS | https://leecountync.gov/ | Navigate to GIS / Tax Office and paste the PIN |

**Render format** in the broker response:

> Heads-up on freshness: our owner graph is bulk-staged from {COUNTY} County GIS quarterly-ish, not live. For anything time-sensitive (offer letters, deed work), verify against **[{Portal Name}]({URL})** — search by PIN: `{PIN}`.

Substitute the four placeholders from the table above per the parcel's `county` field. **Do NOT** use a generic Wake-only link when the parcel is in Durham, NHC, or Lee.

### Known data gaps

NHC parcels have **null lat/lng** in v1 (the County's PropertyOwners layer doesn't carry usable polygon geometry on the free endpoint); this is a known limitation, not a defect.

Lee NC parcels have **null `last_sale_date`, `last_sale_price`, and `zoning_code`** in v1 — those fields live in separate Lee GIS layers and are deferred to v2.

## Examples

### Example 1 — happy path

Broker: "Who owns 100 Connemara Dr in Cary?"
Skill: calls `owner_lookup({address: "100 Connemara Dr, Cary NC"})`.
Tool: returns `{county: "WAKE", parcel_id: "0734835370", owner_raw: "PNC OF NORTH CAROLINA LLC", owner_mail_address: "7930 SKYLAND RIDGE PKWY\nRALEIGH NC 27617-6813", ...}`.
Skill renders: "Owner of 100 Connemara Dr, Cary (WAKE/0734835370): PNC OF NORTH CAROLINA LLC. Mailing address: 7930 Skyland Ridge Pkwy, Raleigh NC 27617-6813. Assessed value: $X, building SF: Y, last sale Z/$W."

### Example 2 — ambiguous address

Broker: "Who owns 100 Main St?"
Skill: calls `owner_lookup({address: "100 Main St"})`.
Tool: returns multi-match error listing the candidate counties.
Skill: "There's a 100 Main St in more than one covered county. Which one — Wake, Durham, NEW_HANOVER, or Lee?"

### Example 3 — out of scope

Broker: "Who owns 500 Oak Ave, Charlotte NC?"
Skill: calls `owner_lookup({address: "500 Oak Ave, Charlotte NC"})`.
Tool: returns "No parcel found ... outside the covered counties (Wake, Durham, New Hanover, Lee NC)."
Skill: "I don't have Charlotte (Mecklenburg County) yet — coverage is currently Wake, Durham, New Hanover, and Lee in NC. For Charlotte, try Mecklenburg County's POLARIS GIS at https://polaris3g.mecklenburgcountync.gov/."

## What's deliberately NOT in v1

- **Owner phone / email** — contact enrichment layer is deferred (no free public source).
- **Portfolio rollups** ("everything owner X owns") — the owner graph supports this but a `portfolio-lookup` skill is a v1.1 deliverable.
- **Owner history / prior deeds** — current owner only.
- **More counties** — Johnston, Brunswick, Pender are next. Mecklenburg / Buncombe / Guilford are larger projects.
- **LLC resolution** (NC Secretary of State entity lookup) — v1.1.

## Files

- `SKILL.md` — this file. The skill is a thin orchestrator over the `owner_lookup` MCP tool on `lee-raleigh-mcp`. No Python helpers, no local assets, no PDFs. Everything happens server-side in the Worker.
