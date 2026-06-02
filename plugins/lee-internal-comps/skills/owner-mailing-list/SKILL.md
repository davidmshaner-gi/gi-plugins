---
name: owner-mailing-list
description: Produce a deduplicated owner + mailing-address list for a Lee & Associates broker from public county parcel data. Given an area + criteria request (subject address + radius + property type/land class + acreage or size), drives the Claude in Chrome browser extension against the county's public ArcGIS parcel service to find matching parcels, then returns a clean CSV of owner names + mailing addresses + site addresses, deduplicated by mailing address and filtered to private owners (drops government/exempt/HOA/cemetery parcels). Use for any "owners of <criteria> within <radius> of <address>" / "mailing list for <area>" / "who owns the vacant land near <site>" request. Requires the Claude in Chrome browser extension; the skill detects it and walks the broker through enabling it if absent. NC counties only; coverage grows by county (see QA_MATRIX.md). v1 returns the CSV; Avery labels are a separate skill (gi-plugins #38).
---

# Owner Mailing List

Produce a deduplicated, private-owner mailing-address CSV from public county parcel data. All data work runs **in the browser** via the Claude in Chrome extension, because the Cowork sandbox has no outbound network — the browser is the only egress path.

## When to use / not

**Use this skill when a broker wants:**
- A property-owner mailing list by area and criteria: "owners of 2–5 acre vacant land within 3 miles of 100 Walnut St, Cary NC"
- "Mailing list for [area/property type]"
- "Who owns the vacant land near [address]?"
- Any "owners of `<criteria>` within `<radius>` of `<address>`" pattern

**Do NOT use this skill for:**
- **Comps** (internal or external) — use `internal-comps` or `external-comps`
- **Single-address owner lookup** — use `owner-lookup` (different skill)
- **Demographics** — use `demographics-report`
- **Avery 5160 label PDFs** — deferred to gi-plugins #38 (separate skill)
- **Phone/email enrichment** — deferred to lee #35/#36

---

## Step 0 — Detect Claude in Chrome

**Before doing anything else**, confirm the **Claude in Chrome** browser tools are available in this session — the ones prefixed `mcp__Claude_in_Chrome__` (e.g. `mcp__Claude_in_Chrome__javascript_tool`, `mcp__Claude_in_Chrome__navigate`, `mcp__Claude_in_Chrome__tabs_context_mcp`). Those tools ARE the signal that Claude in Chrome is enabled.

> **Do NOT use the `mcp__Control_Chrome__*` ("Control Chrome") tools for this skill.** Control Chrome's `execute_javascript` fails in this environment ("Google Chrome is not running") and wastes calls. This skill drives Claude in Chrome exclusively.

**If the Claude in Chrome tools are NOT available:**

> I need the **Claude in Chrome** extension enabled to pull owner data from the county parcel service. It's a one-time, in-session step.
>
> See the install guide: `plugins/lee-internal-comps/skills/owner-mailing-list/INSTALL_CLAUDE_FOR_CHROME.md`
>
> Once it's on and you've opened a tab, come back here and I'll run the pull.

**HALT.** Do not attempt the pull without the Claude in Chrome tools present. There is no fallback (Control Chrome does not work, and the sandbox has no network).

---

## Step 1 — Parse the request

Call `helpers.parse_request(text)` on the broker's request string. The function returns:

```python
{
    "subject_property": {"address": "100 Walnut St, Cary NC"},
    "radius_mi": 3.0,          # None if not specified
    "size": {"min_acres": 2.0, "max_acres": 5.0},  # {} if not specified
    "land_class": "vacant",    # "" if not specified
    "raw": "<original text>",
}
```

**Confirm back to the broker before proceeding:**

> Got it — I'll pull owners of [land_class] land, [size range if given], within [radius] miles of [address]. Running the county parcel lookup now.

If `radius_mi` is `None`, ask the broker: "How many miles out from [address] should I search?"
If `subject_property.address` is blank, ask the broker for the subject address before continuing.

Acreage handling: `size.min_acres` / `size.max_acres` may be present, one-sided ("3+ acres" → only `min_acres`), or absent. Build the acreage clause accordingly in Step 4.

---

## Step 2 — Resolve county

Determine the county from the subject address (parse it, e.g. "Cary NC" → Wake County).

```python
import county_registry
entry = county_registry.resolve_county("Wake County")
```

**If `resolve_county` returns `None`:**

> [County name] isn't covered yet — the skill only has parcel data wired for a subset of NC counties. For [county name], go directly to its county GIS site and export the owner list from there.

**HALT.** Do not attempt any ArcGIS query. Do not show a Python traceback.

If it returns an entry, you now have `entry["service_url"]`, `entry["field_map"]`, `entry["vacant_filter"]`, and (where present) `entry["mail_concat"]` / `entry["site_concat"]`. You'll pass these into the browser pipeline as `cfg` in Step 4.

---

## Step 3 — Geocode the subject address (Claude in Chrome)

Geocode to a center lat/lon using the Census geocoder, via Claude in Chrome:

1. `mcp__Claude_in_Chrome__navigate` (or `browser_batch` → navigate) to:
   `https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address=<url-encoded-address>&benchmark=2020&format=json`
2. Read the JSON with `mcp__Claude_in_Chrome__javascript_tool` (`action: "javascript_exec"`):
   ```javascript
   JSON.parse(document.body.innerText).result.addressMatches[0].coordinates  // -> {x: lon, y: lat}
   ```

Record `{ lon, lat }` for Step 4. If `addressMatches` is empty, the geocode failed — see the Errors table. Include the geocoded address in your reply for traceability.

---

## Step 4 — Run the whole pipeline in ONE browser call

All of fetch → paginate (truncation guard) → field-map → drop exempt/blank owners → dedupe → CSV happens inside **one** `javascript_tool` call. Do **not** pull rows back into the sandbox row-by-row, and do **not** re-implement any of this inline — the tested pipeline lives in `arcgis_query.js`.

1. **Read `arcgis_query.js`** (it's in this skill directory).
2. **Strip the module syntax for injection:** remove every `export ` keyword (so `export function` → `function`, `export const` → `const`, `export async function` → `async function`). The browser can't run ES-module `export`.
3. **Build `cfg`** from the registry entry + the geocoded point + the parsed criteria:
   ```javascript
   const cfg = {
     serviceUrl: <entry.service_url>,
     where: <vacant_filter + acreage clause, joined with " AND ">,   // see below
     geometry: JSON.stringify({ x: <lon>, y: <lat> }),
     distance: <radius_mi>,
     fieldMap: <entry.field_map>,        // the 6-key object, verbatim
     mailConcat: <entry.mail_concat or null>,
     siteConcat: <entry.site_concat or null>,
   };
   ```
   **Build `where` registry-driven — never hardcode a county's column.** Use the acreage field from the entry:
   ```javascript
   const acreageField = cfg.fieldMap.acreage;     // e.g. "DEED_ACRES" (Wake), "gisacres" (NC OneMap)
   const where = [ entry.vacant_filter,
     (size.min_acres != null ? `${acreageField} >= ${size.min_acres}` : null),
     (size.max_acres != null ? `${acreageField} <= ${size.max_acres}` : null),
   ].filter(Boolean).join(" AND ");
   ```
   Note: some `vacant_filter`s already contain `cntyname='...'` (the NC OneMap counties) or parentheses (Onslow) — keep them verbatim.
4. **Inject the stripped `arcgis_query.js` + this tail, as a single `javascript_tool` payload:**
   ```javascript
   // ...(the export-stripped contents of arcgis_query.js above this line)...
   const cfg = { /* built in step 3 above */ };
   const result = await buildOwnerMailingCsv(cfg);   // fetch+paginate+map+filter+dedupe+csv
   window.__omlCsv = result.csv;                     // stowed for retrieval in Step 5
   JSON.stringify(result.report);                    // returned now (small)
   ```
   The returned `report` is `{ parcels, after_exempt_filter, exempt_dropped, unique_owners, dedup_dropped }`.

**Truncation is handled inside `fetchAllParcels` (loops past `exceededTransferLimit`).** Do not stop after one page.

If `report.parcels` is 0 → "no parcels matched" (Errors table), HALT. If `report.unique_owners` is 0 but `parcels` > 0 → everything was filtered out as exempt; tell the broker the matches were all government/exempt parcels.

---

## Step 5 — Write the CSV file (deterministic, no base64)

The finished CSV is in `window.__omlCsv`. Retrieve it and write it to the working directory. **Do not** base64-encode it (Cowork blocks base64 returns) and **do not** ad-hoc slice it.

1. Get the filename (Python, sandbox): `helpers.default_output_path(request, date.today().isoformat())` → e.g. `owners-100-walnut-st-cary-nc-2026-06-02.csv`.
2. Get the line count: `javascript_tool` → `window.__omlCsv.split("\n").length`.
3. **Retrieve in fixed 50-line batches, in order, writing as you go.** For each batch `i` (0, 50, 100, …):
   ```javascript
   window.__omlCsv.split("\n").slice(i, i + 50).join("\n")   // javascript_tool
   ```
   Write the first batch to the file (create), append each subsequent batch (with a leading newline). Most lists are one or two batches. Use a Python write/append in the sandbox; the file lands in the working directory (no subfolder).
4. Verify: the written file's line count equals the count from step 2.

**Report to the broker:**

> Done — **[report.unique_owners] private owners** of [land_class] land within [radius] miles of [address] ([county]).
> Pulled [report.parcels] parcels; dropped [report.exempt_dropped] government/exempt/HOA/cemetery parcels and [report.dedup_dropped] duplicate mailing addresses.
>
> CSV saved: `[filename]`

---

## Output

**One CSV file**, short flat filename, written directly to the working directory:

```
owners-<address-slug>-<YYYY-MM-DD>.csv
```

Example: `owners-100-walnut-st-cary-nc-2026-06-02.csv`

**Rules (load-bearing — Windows 218-char path limit):**
- **Never create a subfolder.** No nested paths.
- **Never use a long descriptive name.** The slug comes from the subject address only; the filename is generated by `helpers.default_output_path(request, date)` — do not construct it manually.
- Brokers run Cowork on Windows where the base output path is already ~125 chars deep; a subfolder + long name tips the total over 218 and Excel refuses to open the file.

**CSV columns** (in this order): `owner`, `mail_addr`, `site_addr`, `acreage`, `land_class`
Note: `land_class` is best-effort — some counties don't expose a usable land-class field and the column will be blank for them. `owner` + `mail_addr` (street + city + state + zip) are the load-bearing columns.

---

## Errors — broker-legible only, never a Python traceback

| Situation | Message |
|---|---|
| Claude in Chrome tools not present | "I need the Claude in Chrome extension enabled first. See INSTALL_CLAUDE_FOR_CHROME.md for the one-time setup." + HALT |
| County not in registry | "[County] isn't covered yet — see the county GIS site directly." + HALT |
| Geocode fails (no addressMatches) | "I couldn't geocode [address] — can you confirm the full street address including city and state?" |
| ArcGIS service unreachable | "The [county] parcel service returned an error. The service may be down — try again in a few minutes, or go to the county GIS site directly." |
| Zero parcels matched | "No parcels matched [criteria] within [radius] miles of [address] in [county]. Try widening the radius or adjusting the acreage range." |
| All matches were exempt | "All [N] matching parcels were government/exempt/HOA/cemetery owned — no private prospects in that area. Try widening the radius." |

**Never surface** a Python exception, a stack trace, or a raw ArcGIS error to the broker.

---

## Files

- `SKILL.md` — this file (orchestration recipe).
- `arcgis_query.js` — **the pipeline** (`buildOwnerMailingCsv` + `fetchAllParcels`, `buildRows`, `isExemptOwner`, `dedupeByMailingAddress`, `toCsv`). Runs entirely in the browser; node-tested. Inject it (export-stripped) in Step 4.
- `helpers.py` — pure-Python helpers that run in the sandbox: `parse_request` (Step 1) and `default_output_path` / `slugify` (Step 5 filename). Also keeps `build_rows` / `dedupe_by_mailing_address` / `format_csv` as the tested Python parity reference for the JS pipeline. No network.
- `county_registry.py` — `COUNTY_REGISTRY` dict + `resolve_county(county_name)`. Source of truth for covered counties, service URLs, field names, `mail_concat`/`site_concat`, and vacant filters.
- `INSTALL_CLAUDE_FOR_CHROME.md` — broker install guide for the Claude in Chrome extension (linked in Step 0).
- `QA_MATRIX.md` — per-county QA ledger. Covered counties are PASS or explicitly "not yet covered." No silent gaps.
