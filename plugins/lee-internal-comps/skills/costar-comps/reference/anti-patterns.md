# Anti-Patterns — Things NOT to Do

Last verified: 2026-05-07.

These are real dead ends I (or earlier sessions) have hit. Each one cost meaningful tokens to discover. Don't re-discover them.

## AP-1 — Lease Activity has NO Excel export

**Don't:** Click More → Export on the Lease Activity page. The More dropdown only contains "Removed Comps" — there is no Export option. The Reports button does exist but only outputs PDFs (3 Leases Per Page, 5 Leases Per Page, Classic One Page, Comprehensive Report, Map Summary and List of Leases) — none of which are parseable for ranking.

**Do:** Switch to MAP view and scrape the side-panel cards. See `flows/lease-comp-pull.md` for the scrape procedure. Each card has full address + city + ZIP + SF + rent + sign date + lease type + tenant.

## AP-2 — No City/County columns in Lease Activity Modify Table

**Don't:** Open Modify Table on Lease Activity, then search Available Fields for "City" or "County" or "Submarket." None of those fields exist in the Lease Activity field set. The closest options are "Effective Rent/SF/Year" (matches "City" because of "Effe**ctiv**e") and "Location Type" — neither is what you want.

**Do:** Get city/ZIP from the side-panel cards in MAP view (they include full address). Get county by lookup from the city (cached in `flows/lease-comp-pull.md`).

## AP-3 — No County filter in Lease Activity Filters → Location panel

**Don't:** Try to add a County filter to constrain to Wake/Durham only at the CoStar level on the lease path. The Filters → Location tab exposes only Submarket, Market, Postcode, City, Country, Country Divisions — **not County.** (Sale Comps does have County in its advanced filters, FYI.)

**Do:** Keep the MSA-level location filter applied in CoStar (the Raleigh/Durham/Chapel Hill polygon includes Johnston, Orange, Chatham, Franklin in addition to Wake and Durham), then drop non-Wake/Durham rows at the **rank step**. Mention the dropped rows in the chat summary.

## AP-4 — MAP-view Sale Comps export is incomplete

**Don't:** Click More → Export → Export while in MAP view on Sale Comps. The export captures only records visible in the side panel — often 6 of 20.

**Do:** Switch to LIST view first. Use the column-header checkbox (or click each row's checkbox) to select all rows. THEN export. The export will then capture all rows, not just the visible ones.

## AP-5 — Chrome appends (1), (2) instead of overwriting Sale Comps exports

**Don't:** Assume the export "overwrites" the previous CostarExport.xlsx. Chrome saves repeated downloads as `CostarExport (1).xlsx`, `CostarExport (2).xlsx`, etc.

**Do:** When reading the file post-export, read the **most recent** xlsx in the Downloads folder — match the highest `(N)` suffix or sort by mtime. The bash sandbox path is `/sessions/.../mnt/Downloads/`; use `ls -lat` to find the latest.

## AP-6 — "Hospitality Market" label on Raleigh/Durham/Chapel Hill is a red herring

**Don't:** Skip the top "Raleigh/Durham/Chapel Hill - NC (USA)" autocomplete option because it's labeled "Hospitality Market." That label refers to the boundary type, not a property-type filter. The option applies as a **geographic** filter and works correctly for industrial/office/retail/all property types on both sale and lease paths.

**Do:** Pick this option as the default for any "Raleigh-Durham" market scope, regardless of property type.

## AP-7 — Lease Activity LIST-view "select all" header checkbox doesn't exist

**Don't:** Look for or click a select-all checkbox in the LIST-view column header on Lease Activity. There isn't one. The first column has empty header space; clicking row checkboxes is per-row only.

**Do:** This is moot anyway because Lease Activity has no Excel export (AP-1). For the side-panel scrape, no selection is needed — you scrape all visible cards.

## AP-8 — Sale Comps "select all" can produce unreliable results without LIST view

**Don't:** Try to select all records via accessibility tree's "select all" reference (e.g. `find` for "select all checkbox") while in MAP view. The find tool may identify a row checkbox instead of the header, selecting only one row. Then export captures only the visibly-selected subset.

**Do:** Switch to LIST view first. Then click the column-header checkbox at coordinates near (24, 138) — it's at the top of the leftmost icon column, above the data rows. Verify the toolbar shows a selection count > 0 before exporting.

## AP-9 — Direct URL navigation works for both pages — skip the nav menu

**Don't:** Click Sales > Sale Comps or Leasing > Lease Activity through the top nav menu. The first-time hover-then-click pattern is fragile (sometimes the dropdown closes before the click registers).

**Do:** Use direct URL navigation:
- Sale Comps: `https://product.costar.com/search/sale-comps/`
- Lease Activity: `https://product.costar.com/suiteapps/lease-activity?new_search=true`

Both inherit the Chrome cookie-based login. Saves 2-3 round-trips per run.

## AP-10 — The kickoff prompt's #3 rule applies to broker terminology, not CoStar terminology

**Don't:** Pause and ask the broker about CoStar's own labels (e.g. "should we use Space Use or Property Type?"). CoStar's labels are documented in `terminology.md` — pick the right one and proceed.

**Do:** Pause and ask only when the broker uses **broker-internal** shorthand you don't recognize ("IOS," "the Triangle," internal nicknames, etc.). Translate broker terms to CoStar terms via the broker's confirmation, then drive using CoStar's labels.
