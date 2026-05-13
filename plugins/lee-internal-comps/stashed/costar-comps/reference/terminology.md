# CoStar Terminology Cache

Last verified: 2026-05-07 against CoStar production build.

This file caches CoStar's own taxonomies and label mappings so you don't have to discover them at runtime. When the broker uses a Lee-internal term, behavioral rule #3 still applies — ask, don't guess. This file is for CoStar-side mappings (which option to pick in CoStar's autocompletes), not for broker-side jargon.

## Location autocomplete: "Raleigh-Durham"

Typing "Raleigh-Durham" or "Raleigh" into the toolbar location field returns multiple options. Default mapping for Lee Raleigh comp work:

| Option in dropdown | What it actually is | Use it? |
|---|---|---|
| **Raleigh/Durham/Chapel Hill - NC (USA)** *(tagged "Hospitality Market")* | MSA-level polygon covering Wake, Durham, Orange, Chatham, Johnston, Franklin, Granville. Despite the "Hospitality Market" label, it applies as a **geographic boundary**, not a property-type-restrictive filter. | **Yes — default for industrial/office/retail/all sale and lease pulls.** |
| Raleigh, NC (USA) — *City* | City of Raleigh boundary only. Misses Durham, Cary, Garner, etc. | Only if broker explicitly says "city of Raleigh." |
| Raleigh - NC (USA) — *CoStar Market* | Office-market boundary. | Only if broker explicitly asks for office-market scope. |
| Research Triangle - Durham (USA) — *Office Submarket* | Office submarket. | Only on broker request. |
| Raleigh-Durham International Airport — *Point of Interest* | Point on the map. | Never (this is geocoding, not market scope). |
| Raleigh, IL / MS / WV (USA) | Other states. | Never. |

**Confirmation pattern:** Mention the default ("the Raleigh/Durham/Chapel Hill MSA boundary") in your resolved-query confirmation. If the broker wants a tighter scope, they will say so.

## Toolbar filter labels — Sale Comps vs Lease Activity

| Sale Comps | Lease Activity |
|---|---|
| Property Type | **Space Use** |
| Property Size | **Size Leased** |
| Sale Date | **Sign Date** |

The dropdown options inside each are also slightly different — see below.

## Property Type / Space Use option lists

**Sale Comps — Property Type checkboxes (in DOM order):**
Office · Industrial · Retail · Flex · Multifamily · Student · Land · Hospitality · Health Care · Specialty · Sports & Entertainment · *(toggle)* In a Shopping Center

**Lease Activity — Space Use checkboxes (in DOM order):**
Office · Industrial · Retail · Flex · Medical · *(toggle)* In a Shopping Center

Note: lease taxonomy has "Medical" but no Multifamily/Student/Land/Hospitality/Health Care/Specialty/Sports — those don't lease the same way.

## Date filter presets

**Sale Comps "Sold within the last":** 3 months, 6 months, 1 year, 2 years, 3 years, 4 years, 5 years, 10 years
**Lease Activity "Signed within the last":** same eight presets

When the broker says a duration that matches a preset (e.g. "last 6 months," "last year"), use the preset. Custom date ranges are slower and have date-format gotchas. Only use custom when the broker asks for an exact start/end (e.g. "Q1 2026 only").

## Size filter presets (Min/Max SF dropdown options)

Both Sale (Property Size) and Lease (Size Leased) show the same preset choices below the Min/Max SF inputs:

`No Min` · 5,000 SF · 10,000 SF · 20,000 SF · 50,000 SF · 75,000 SF · 100,000 SF · 200,000 SF · 500,000 SF

When the broker gives a non-preset range (e.g. "2K to 30K SF"), type into the Min SF and Max SF inputs directly. The presets are convenient but rarely match a broker's actual size band.

## Secondary Type list (in Filters → Building tab)

The Secondary Type dropdown is the same field on Sale Comps and Lease Activity. It's alphabetical and long (~80 entries). For industrial work, the relevant values are:

- **Warehouse** — most common; default for "warehouse only"
- Distribution
- Manufacturing
- Light Manufacturing
- Service
- Truck Terminal
- Refrigeration/Cold Storage
- R&D
- Showroom

Type the value into the search box at the top of the dropdown — typing "Warehouse" filters the list down to just Warehouse.

## Filter chip pattern

When a filter is applied, a chip appears in the toolbar and the **Filters button shows a count badge** (e.g. "Filters 5"). Use this badge as the verification signal — it should increment by 1 each time you apply a new filter. If the count doesn't change, the click didn't take and you should fall back to find().

## Record-count display

Top-right of the page, format: `N Leases / M Properties` (lease path) or `N Records / M Properties` (sale path).

After each filter is applied, the count should drop. If it doesn't drop after a filter you just applied, the filter didn't stick — verify before proceeding.
