# Lease Activity — DOM Map

Last verified: 2026-05-07.

URL: `https://product.costar.com/suiteapps/lease-activity?new_search=true`

**Important:** CoStar does not have a "Lease Comps" page. Lease comp data lives at "Lease Activity" — same data, different label. The URL `/search/lease-comps/` exists but is a different (For Lease listings) page; do NOT use it. Always navigate directly to `/suiteapps/lease-activity?new_search=true` (the `?new_search=true` parameter clears any prior session state).

## Page layout (top to bottom)

```
[Top blue header bar — News | Properties | Leasing (active) | Sales | Owners | Tenants | ...]
[Subnav row — For Lease | Lease Activity (active) | UK Registered Leases | Lease Analysis]
[Toolbar: filter chips (different labels from Sale Comps), action buttons, view toggles]
[Main area: MAP (default) or LIST view]
```

## Toolbar — filter chips (left to right)

Same y-coordinate (~89). Filter labels differ from Sale Comps — see terminology.md for the mapping.

| # | Element | X-coord | DOM signal |
|---|---|---|---|
| 1 | Address or Location input | ~85 | placeholder text "Address or Location" — same widget as Sale Comps |
| 2 | **Space Use** dropdown | ~203 | label "Space Use" (NOT "Property Type") |
| 3 | **Size Leased** | ~296 | label "Size Leased" (NOT "Property Size") |
| 4 | **Sign Date** | ~405 | label format "After M/D/YY" |
| 5 | Star rating | ~492 | (rarely used) |

## Toolbar — action buttons (right side)

| Element | X-coord | Notes |
|---|---|---|
| Clear | ~1145 | |
| Filters | ~1196 | opens the advanced Filters panel (different tabs from Sale Comps — see below) |
| Sort | ~1259 | |
| Save | ~1305 | |
| Reports | ~1361 | **PDFs only** — see anti-patterns AP-1 |
| **More** | ~1413 | **only contains "Removed Comps"** — no Export option exists |
| MAP icon | ~1469 | |
| LIST icon | ~1492 | |
| ANALYTICS icon | ~1525 | |

## Filters panel (advanced)

Click "Filters" at (1196, 90). The panel opens on the right side with tabs: **Search** (default) and **Location**.

The **Search tab** has three sub-tabs: **Lease**, **Building**, **Contacts**.

### Lease sub-tab — relevant fields

Space Use, Size Leased, Sign Date, Lease Term In Years, Lease Type (Direct / Assignment / Sublet / Coworking checkboxes), Deal Type (New Lease / Renewal toggle), Rental Rate, Rent Type (Starting / Effective / Asking), Services, Expiration, Termination Option, Review Date, Build-Out Status, Floors, Tenant.

### Building sub-tab — relevant fields

CoStar Rating, Property Type, Property Size, **Secondary Type** (Warehouse, Distribution, Manufacturing, etc. — type to filter, see terminology.md), Year Built, Land Area, Amenities, Stories, Building FAR, Clear Height, Loading Docks, Drive-Ins, Tenancy, Owner Occupied, Building Class.

The Secondary Type dropdown is at approximately (1369, 324). Type "Warehouse" into it (it filters live), then click the matching option that appears below.

### Location tab — what's NOT there

Submarket, Market, Postcode, City, Country, Country Divisions are exposed. **County is NOT exposed.** See anti-patterns AP-3 — apply Wake/Durham filtering at the rank step instead.

To dismiss the Filters panel, click "Done" at approximately (1539, 730).

## Filter application sequence (happy path)

1. **Location:** click (85, 89), type market name, wait 2s, click the matching autocomplete option.
2. **Space Use:** click (203, 89), check Industrial (or other), click outside to close.
3. **Sign Date:** click (405, 89). For preset matches (3 mo, 6 mo, 1 yr, 2 yr, 3 yr, 4 yr, 5 yr, 10 yr), click the preset on the left side of the panel — it's much faster than custom dates. Custom range fields are on the right if needed.
4. **Size Leased:** click (296, 89). Min SF / Max SF inputs at approximately (302, 119) and (411, 119).
5. **Subtype (optional):** if broker said "warehouse only," click Filters at (1196, 89), click Building tab at (1248, 149), click Secondary Type at (1369, 324), type "Warehouse," click the matching option at approximately (1241, 346), then click Done at (1539, 730).

## Filter verification

- Filters button badge increments per filter applied.
- Record-count display (top right): `N Leases / M Properties`.

## Export — does NOT exist on this page

See anti-patterns AP-1. The More menu only has "Removed Comps." Reports outputs PDFs only. **Don't waste round-trips trying.**

## Side-panel scrape (what to use instead)

Switch to MAP view (click MAP icon at (1469, 89)) so the side panel of property cards is visible on the right. Each card contains:

```
[image] [N/total]
{SF} SF • {rent details}
{Lease Type} (Direct/Sublet/etc.) • Signed {Mon Year}
{tenant name (if disclosed)} • Floor {N}
{street address}
{City, ST ZIP}
{star rating}
```

To extract the data, call `get_page_text` on the page after MAP view loads. The visible text includes all 20 cards on page 1 in order. Parse the text using a regex pattern like:

```
(\d{1,3}(,\d{3})?)\s*SF\s*(•\s*\$([\d.]+)/SF\s*([A-Z]+)\s*(Asking|Starting)\s*Rent)?
.*?Industrial\s*(Direct|Sublet)\s*•\s*Signed\s*(\w+\s+\d{4}).*?
([\d\w\s]+)\s*(Floor\s+\d+)?\s*([\w\s,&]+(?:Rd|St|Ln|Ave|Dr|Blvd|Ct|Way|Pkwy|Hwy)\b[^|]*)
([\w\s\-]+),\s*NC\s*(\d{5})
```

A more reliable approach: use a JavaScript scrape via `javascript_tool` to walk the DOM cards directly. Look for `<li>` elements containing both "SF" and "Signed" markers in their innerText. (See `flows/lease-comp-pull.md` for the working scrape script.)

If the broker's filter set returns more than 20 results, the side panel paginates; navigate to page 2 by scrolling the side panel (NOT the map) and re-scrape.

## City → County mapping (Triangle area)

Used at the rank step to apply "Wake/Durham only" filter post-pull:

| City | County |
|---|---|
| Raleigh, Cary, Apex, Garner, Fuquay-Varina, Morrisville, Wake Forest, Holly Springs, Knightdale, Wendell, Zebulon, Rolesville | Wake |
| Durham | Durham |
| Hillsborough, Chapel Hill, Efland, Mebane (NC side) | Orange (DROP) |
| Pittsboro | Chatham (DROP) |
| Smithfield, Selma, Clayton, Princeton, Benson | Johnston (DROP) |
| Franklinton, Louisburg | Franklin (DROP) |

Morrisville straddles the Wake/Durham line — most ZIP 27560 addresses are Wake. Default to Wake unless the address is east of NC 540.
