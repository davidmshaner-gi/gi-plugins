# Flow: Lease Comp Pull

Last verified: 2026-05-07. Estimated tool-call count for happy path: **~14-18** (vs. ~35-40 for an uncached run — the savings are bigger here because the lease path has more dead ends to skip).

## Pre-flight

You should have already:
- Confirmed the resolved query with the broker (rule #4).
- Read `reference/terminology.md`, `reference/anti-patterns.md`, `reference/lease-activity-dom.md`.

Required inputs from the broker (resolved):
- `comp_type = lease`
- `space_use` (broker says "industrial" — that's the Space Use value, not Property Type)
- `location` (e.g. Raleigh-Durham → "Raleigh/Durham/Chapel Hill - NC (USA)")
- `date_range` (e.g. "last 6 months" → use the **6 months preset**, not custom dates)
- `size_min`, `size_max`
- `subtype` (optional, e.g. "Warehouse" → applied via Filters → Building → Secondary Type)
- `county_filter` (optional, e.g. "Wake/Durham only" — applied at rank step, NOT in the UI)

## Step 1 — Get a CoStar tab and navigate

```
mcp__Claude_in_Chrome__tabs_context_mcp(createIfEmpty: true)
mcp__Claude_in_Chrome__navigate(url: "https://product.costar.com/suiteapps/lease-activity?new_search=true", tabId: ...)
```

Wait 5s for the React app to hydrate. **Don't** navigate to `/search/lease-comps/` — that's a different (For Lease listings) page.

## Step 2 — Apply toolbar filters in batch

### 2a — Location

Same as Sale Comps. Click input at (85, 89), type the market, wait 2s. Use `find()` to click the matching autocomplete option.

### 2b — Space Use (NOT Property Type — different label)

```
browser_batch([
  click(203, 89),
  wait(1),
  click(173, 133),   // Industrial checkbox (2nd row: Office, Industrial, Retail, Flex, Medical)
  wait(1),
  click(800, 400)    // close
])
```

### 2c — Sign Date — USE PRESETS

Match the broker's date range to the closest preset. Preset y-coordinates (after clicking Sign Date at (405, 89)):

| Preset | y-coord |
|---|---|
| 3 months | 141 |
| 6 months | 161 |
| 1 year | 180 |
| 2 years | 199 |
| 3 years | 219 |
| 4 years | 239 |
| 5 years | 258 |
| 10 years | 277 |

```
browser_batch([
  click(405, 89),
  wait(2),
  click(161, 161),   // 6 months preset (or whichever matches)
  wait(2)
])
```

Only fall back to custom date entry if the broker requested a non-preset range (e.g. "Q1 2026 only").

### 2d — Size Leased

```
browser_batch([
  click(296, 89),
  wait(1),
  click(302, 119),
  type("5000"),
  key("Tab"),
  type("15000"),
  key("Tab"),
  click(800, 400)
])
```

### 2e — Subtype filter (only if broker asked, e.g. "warehouse only")

```
browser_batch([
  click(1196, 89),     // Filters button
  wait(3),
  click(1248, 149),    // Building tab
  wait(1),
  click(1369, 324),    // Secondary Type dropdown
  wait(1),
  type("Warehouse"),
  wait(1),
  click(1241, 346),    // matching option
  wait(2),
  click(1539, 730)     // Done
])
```

## Step 3 — Verify

Take ONE screenshot. Parse for filter chips and record count `N Leases / M Properties`.

If chip count or record count looks wrong, fall back to find() for the specific missing filter.

## Step 4 — Decide narrow/loosen

Same as sale path. If `N Leases` is far from 7-10, propose narrow/loosen options to the broker before scraping.

If the broker asked for a county filter, do NOT add it in the UI — apply it at rank step. (anti-patterns AP-3.)

## Step 5 — Switch to MAP view and scrape side panel

**There is no Excel export.** Skip every instinct to try More→Export, Reports, or Modify Table. (anti-patterns AP-1, AP-2.)

```
browser_batch([
  click(1469, 89),       // MAP view icon
  wait(3)
])
```

Then read the page text:

```
mcp__Claude_in_Chrome__get_page_text(tabId: ...)
```

The returned text contains all visible side-panel cards in DOM order. Each card follows this pattern:

```
{N}/{total}{SF} SF • ${rent}/SF {basis} {type} Rent
{Industrial} {Direct|Sublet} • Signed {Mon Year} • {term if present}
{tenant if disclosed} • Floor {N}
{street address}
{City}, {ST} {ZIP}
```

Parse with a regex like:

```python
import re
pattern = re.compile(
    r'(\d{1,3}(?:,\d{3})?)\s*SF'
    r'(?:\s*•\s*\$([\d.]+)/SF\s*([A-Z]+)\s*(?:Asking|Starting)\s*Rent)?'
    r'.*?Industrial\s*(Direct|Sublet)\s*•\s*Signed\s*(\w+\s+\d{4})'
    r'(?:\s*•\s*([\d\s]+\s+(?:Year|Month)s?))?'
    r'.*?\b(\d+\s+[\w\s.&]+(?:Rd|St|Ln|Ave|Dr|Blvd|Ct|Way|Pkwy|Hwy|Pl|Cir)\b[^\n]*?)'
    r'\s*([\w\s\-]+),\s*NC\s*(\d{5})',
    re.DOTALL
)
```

If the result count > 20, the side panel paginates. Scroll the side panel to load page 2, re-call `get_page_text`, append the additional rows.

## Step 6 — Build the backup xlsx yourself

The lease deliverable's backup file is a Cowork-built xlsx, not a CoStar export. Create it with openpyxl:

Columns: `Signed | Address | City | County | SF Leased | Rent ($/SF) | Rent Basis | Term (mo) | Lease Type | Tenant | In Wake/Durham?`

Apply the City→County mapping from `reference/lease-activity-dom.md`. Compute `In Wake/Durham?` from the county. Save as `Lease_Activity_<Market>_<Type>_<Subtype>.xlsx` and present via `mcp__cowork__present_files`.

## Step 7 — Rank and present

### Filter rules

- **APPLY county filter** if broker specified one. Drop non-Wake/Durham rows; mention how many were dropped in the chat summary.
- **TAG, DON'T DROP** Sublet rows. Display them in a separate sub-table labeled "Sublet."
- **TAG** rent-not-disclosed rows with ⚠ marker. Display them in a separate sub-table labeled "Rent not disclosed (activity signal only)."
- **TAG** Renewal deals — they may not be arms-length. Add a notes-column flag.

### Ranking score

For each remaining row with disclosed rent:
- **Recency score:** months_since_sign_date (lower = better)
- **Size proximity:** abs(sf_leased - target_size) where target_size = (size_min + size_max) / 2
- **Geo score:** Wake/Durham core submarkets (Glenwood/Creedmoor, South Durham, RTP) > edge cities

Sort ascending.

### Output

Markdown table (top 7-10), columns:
`# | Address | City | County | SF | Rent ($/SF) | Basis | Term | Tenant | Signed | Notes`

Plus the bonus tables for under-contract / rent-not-disclosed / sublet.

Quick-read paragraph: PSF range, NNN vs Modified Gross differences, term outliers.

Attach the Cowork-built xlsx via `present_files`.

## Common failure modes

- **Side panel doesn't load:** wait longer (CoStar is slower on lease than sale). If still empty, refresh the page and re-apply filters.
- **Page text scrape returns CSS junk before the records:** the parseable section starts after the toolbar text — find the first occurrence of the pattern `\d+\s+SF` and parse from there.
- **Less than 7 results:** propose loosening (longer date range, larger size band, drop the subtype filter, broaden geo).
- **More than 30 results:** propose narrowing (tighter date, tighter size band, add subtype filter if not present, restrict to specific submarket).
