# Flow: Sale Comp Pull

Last verified: 2026-05-07. Estimated tool-call count for happy path: **~12-15** (vs. ~25-30 for an uncached run).

## Pre-flight

You should have already:
- Confirmed the resolved query with the broker (rule #4).
- Read `reference/terminology.md`, `reference/anti-patterns.md`, `reference/sale-comps-dom.md`.

Required inputs from the broker (resolved):
- `comp_type = sale`
- `property_type` (e.g. Industrial)
- `location` (e.g. Raleigh-Durham → maps to "Raleigh/Durham/Chapel Hill - NC (USA)" — see terminology.md)
- `date_range` (e.g. "last 4 months" → custom Date Range, or preset if matches 3/6/12 months etc.)
- `size_min`, `size_max` (e.g. 2000, 30000)
- `subtype` (optional, e.g. "Warehouse")
- `county_filter` (optional, e.g. "Wake/Durham only" — applied post-export)

## Step 1 — Get a CoStar tab and navigate

```
mcp__Claude_in_Chrome__tabs_context_mcp(createIfEmpty: true)
mcp__Claude_in_Chrome__navigate(url: "https://product.costar.com/search/sale-comps/", tabId: ...)
```

Wait 4s. **Do not** use the Sales > Sale Comps nav menu — direct URL is more reliable (anti-patterns AP-9).

If the tab loads but redirects to a login page, surface "CoStar session expired — please log in to CoStar in your main Chrome and re-run." Don't try to authenticate.

## Step 2 — Apply filters in batch

Use a single `browser_batch` call to chain the filter clicks (much faster than individual calls). Skip screenshots between steps — the verification step at the end catches failures.

### 2a — Location

```
browser_batch([
  click(89, 90),
  wait(1),
  type("Raleigh-Durham"),
  wait(2),
  // Use find() ONLY for the autocomplete option, since it's positionally variable
])
```

Then `find('Raleigh/Durham/Chapel Hill option in dropdown')` → click the resulting ref.

### 2b — Property Type

```
browser_batch([
  click(222, 90),
  wait(1),
  click(193, 156),  // Industrial checkbox row (3rd in list)
  wait(1),
  click(800, 400)   // close dropdown
])
```

### 2c — Sale Date

For preset match (3/6/12/24 months), click the preset directly in the panel. For custom range:

```
browser_batch([
  click(325, 90),
  wait(2),
  triple_click(314, 178),   // start date field
  type("MM/DD/YYYY"),
  key("Tab"),
  click(400, 178),
  type("MM/DD/YYYY"),
  key("Tab"),
  wait(2)
])
```

The Tab key after the end date often opens the next dropdown (Property Size) — that's fine, you'll handle it next.

### 2d — Property Size

```
browser_batch([
  // If Property Size dropdown is already open from previous Tab, skip click(428, 90)
  click(425, 117),         // Min SF input
  type("2000"),
  key("Tab"),
  type("30000"),
  key("Tab"),
  click(800, 400)          // close
])
```

### 2e — Subtype (only if broker asked)

Click Filters at (1190, 90). Click Building tab. Click Secondary Type. Type the value (e.g. "Warehouse"). Click the matching option. Click Done.

## Step 3 — Verify

Take ONE screenshot to verify all filter chips are visible and the record count is reasonable.

```
screenshot(...)
```

Parse the screenshot for: filter chips reading the expected values, "Filters N" badge count matching the number of filters applied, record-count `N Records / M Properties` in top right.

If anything is off, fall back to find()/click for the missing filter only — don't restart.

## Step 4 — Decide narrow/loosen

If `N Records` is 7-10, proceed to export.
If `N Records` is 11-25, proceed to export — the rank step will trim.
If `N Records` is >25 or <5, surface narrow/loosen options to the broker per rule #5. Wait for their decision before exporting.
If broker said "show me all of them," skip the count check.

## Step 5 — Export

```
browser_batch([
  click(1502, 90),       // LIST view icon
  wait(3),
  click(24, 138),        // column-header select-all checkbox
  wait(1),
  click(1378, 90),       // More button
  wait(1),
  click(1380, 135),      // Export menu item
  wait(2),
  click(968, 689),       // Export confirm in dialog
  wait(6)                // download time
])
```

The dialog defaults are correct (Default List View layout, Microsoft Excel File). Don't change them.

## Step 6 — Read the file

```
ls -lat /sessions/.../mnt/Downloads/CostarExport*.xlsx | head -1
```

Take the most-recent file (Chrome may have appended `(N)` — anti-patterns AP-5). Copy to outputs/ and read with openpyxl.

Field set is ~66 columns. The ones you need for ranking:
`Property Address, Property City, Property State, Building SF, Sale Price, Price Per SF, Sale Date, Sale Status, Sale Type, Year Built, Secondary Type, Building Class, Submarket Name, Property County, Buyer (True) Company, Seller (True) Company`

## Step 7 — Rank and present

### Filter rules

- **DROP** rows with `Sale Price = N/A` or `Property Type` outside what the broker asked for. (CoStar sometimes returns "Industrial (Strip Center)" or similar oddities for buildings that span types.)
- **TAG, DON'T DROP** rows with `Sale Status = "Under Contract"` — display them in a separate sub-table at the bottom labeled "Under Contract."
- **TAG** rows with `Price Per SF` extreme outliers (e.g. $14, $25, $33 per SF for warehouse — usually portfolio-allocated values from multi-property deals). Add ⚠ marker in notes.
- **APPLY county filter** if broker specified one (e.g. Wake/Durham only). Drop rows where `Property County` is not in the allowed list.

### Ranking score (composite)

For each remaining row, compute:
- **Recency score:** months_since_sale_date (lower = better)
- **Size proximity score:** abs(building_sf - target_size) where target_size = (size_min + size_max) / 2
- **Geo score:** in-core MSA submarkets (Glenwood/Creedmoor, South Durham, SE Wake, etc.) score higher than edge submarkets

Sort by `recency * 0.4 + size_proximity * 0.3 + geo * 0.3`, ascending.

### Output

Markdown table (top 7-10), columns:
`# | Address | City | SF | Sale Price | $/SF | Sale Date | YB | Class | Type | Submarket | Notes`

Include a "Quick read" paragraph below summarizing the PSF range and any anomalies.

Attach the raw `CostarExport.xlsx` as a backup file via `present_files`.
