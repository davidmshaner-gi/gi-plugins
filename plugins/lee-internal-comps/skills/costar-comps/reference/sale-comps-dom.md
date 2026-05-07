# Sale Comps — DOM Map

Last verified: 2026-05-07.

URL: `https://product.costar.com/search/sale-comps/`

## Page layout (top to bottom)

```
[Top blue header bar — News | Properties | Leasing | Sales | Owners | Tenants | ...]
[Subnav row — Sale Comps (active) | For Sale | Auctions]
[Toolbar: filter chips on the left, action buttons on the right, view toggles far right]
[Main area: MAP (default) or LIST view]
```

## Toolbar — filter chips (left to right)

Y-coordinate is approximately **89-90** in the default 1568x744 viewport. X-coordinates below assume that viewport.

| # | Element | X-coord | DOM signal | Click behavior |
|---|---|---|---|---|
| 1 | Address or Location input | ~89 | placeholder text "Address or Location" | Click → type to search → autocomplete dropdown appears |
| 2 | Property Type dropdown | ~222 | label "Property Type" | Click → checkbox list opens (see terminology.md for option order) |
| 3 | Sale Date | ~325 | label format "After M/D/YY" | Click → presets + date-range fields panel opens |
| 4 | Property Size | ~428 | label "Property Size" | Click → Min SF / Max SF inputs + presets list |
| 5 | Sale Price | ~513 | label "Sale Price" | (rarely used in standard pulls) |
| 6 | Cap Rate | ~600 | label "Cap Rate" | (rarely used) |
| 7 | Star rating | ~673 | five-star icons | (rarely used) |

## Toolbar — action buttons (right side)

| Element | X-coord | Notes |
|---|---|---|
| Clear | ~1140 | clears all filters |
| Filters | ~1190 | opens the advanced Filters panel (Lease/Building/Contacts tabs) |
| Sort | ~1245 | |
| Save | ~1283 | |
| Reports | ~1328 | opens PDF report templates dialog |
| **More** | ~1378 | dropdown: Add Records, **Export**, Added/Removed |
| MAP icon | ~1478 | view toggle |
| LIST icon | ~1502 | view toggle |
| ANALYTICS icon | ~1538 | view toggle |

## Filter application sequence (happy path)

1. **Location:** click input at (89, 90), type market name, wait 2s, click the autocomplete option (use `find('Raleigh/Durham/Chapel Hill option in dropdown')` if the y-coordinate is uncertain — option items appear stacked starting around y=112).
2. **Property Type:** click at (222, 90), then click the checkbox row for "Industrial" at approximately y=156 (3rd row in dropdown list, ordered Office, Industrial, Retail, ...). Click outside (e.g. (800, 400)) to close.
3. **Sale Date:** click at (325, 90). The dropdown has presets on the left ("Sold within the last") at y=140-300, and a custom Date Range with start/end fields at y=178. For preset matches use the preset; otherwise triple-click the start field, type MM/DD/YYYY, Tab, type end MM/DD/YYYY, Tab.
4. **Property Size:** click at (428, 90). Click Min SF input at approximately (425, 117), type Min, Tab, type Max, Tab. Click outside to close.

## Filter verification

- After each filter, **the Filters button shows a count badge** (e.g. "Filters 4"). Verify the badge increments.
- The record-count display (top right, e.g. "20 Records / 17 Properties") should drop after each filter.

## LIST view export (the only path that works)

1. Click LIST icon at (1502, 90). Wait 3s for grid to render.
2. **Select all rows** — click the column-header checkbox at approximately (24, 138). This is at the top of the leftmost icon column, above the data rows. Verify the toolbar shows a "(N)" selection count > 0.
3. Click **More** at (1378, 90). Wait 1s.
4. Click **Export** in the dropdown at approximately (1380, 135).
5. The "Export Data" dialog opens. Defaults are correct:
   - Selected Field Layout: "Default (List View)"
   - File type: "Microsoft Excel File"
6. Click **Export** button at approximately (968, 689).
7. Wait 6s for download. CoStar saves `CostarExport.xlsx` (or `CostarExport (N).xlsx` if a previous run exists — see anti-patterns AP-5).

## Reading the export file

Sandbox path: `/sessions/.../mnt/Downloads/CostarExport.xlsx` (or `(N).xlsx`).

Use `ls -lat /sessions/.../mnt/Downloads/CostarExport*.xlsx | head -1` to grab the most recent.

The export has ~66 columns including all standard sale comp fields:
- Property Address, Property City, Property State, Property Type
- Building SF, Sale Price, Price Per SF, Sale Date, Sale Status, Sale Type
- Year Built, Secondary Type, Building Class, Submarket Name, Property County
- Buyer (True) Company, Seller (True) Company, Listing Broker Company
- Cap Rate (Actual + Pro Forma), Asking Price, Hold Period
- + ~50 more

## Modify Table (Sale Comps)

If you ever need to reshape the columns, click "Modify Table" at the bottom-right (approximately (1520, 727)). Sale Comps' Available Fields list does include City, County, Submarket Name. (Lease Activity's does NOT — see anti-patterns AP-2.)
