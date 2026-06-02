---
name: owner-mailing-list
description: Produce a deduplicated owner + mailing-address list for a Lee & Associates broker from public county parcel data. Given an area + criteria request (subject address + radius + property type/land class + acreage or size), drives Claude-for-Chrome against the county's public ArcGIS parcel service to find matching parcels, then returns a clean CSV of owner names + mailing addresses + site addresses, deduplicated by mailing address. Use for any "owners of <criteria> within <radius> of <address>" / "mailing list for <area>" / "who owns the vacant land near <site>" request. Requires Claude-for-Chrome (the chrome-control extension); the skill detects it and walks the broker through enabling it if absent. NC counties only; coverage grows by county (see QA_MATRIX.md). v1 returns the CSV; Avery labels are a separate skill (gi-plugins #38).
---

# Owner Mailing List

Produce a deduplicated owner + mailing-address CSV from public county parcel data, driven by Claude-for-Chrome against the county's ArcGIS REST service.

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

## Step 0 — Detect Claude-for-Chrome

**Before doing anything else**, check whether the `chrome-control` tools are available in this session. The presence of any of these tools signals that Claude-for-Chrome is enabled: `get_current_tab`, `open_url`, `execute_javascript`.

**If chrome-control tools are NOT available:**

> I need the Claude-for-Chrome extension ("Control Chrome") enabled to pull owner data from the county parcel service. It's a one-time, in-session step.
>
> See the install guide: `plugins/lee-internal-comps/skills/owner-mailing-list/INSTALL_CLAUDE_FOR_CHROME.md`
>
> Once you've enabled it (Settings → Extensions → Control Chrome → toggle on) and confirmed with "open google.com", come back here and I'll run the pull.

**HALT.** Do not attempt the ArcGIS pull without chrome-control tools present. There is no fallback path.

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

---

## Step 2 — Resolve county

Determine the county from the subject address (parse it from the address string, e.g. "Cary NC" → Wake County).

Call:
```python
import county_registry
entry = county_registry.resolve_county("Wake County")
```

**If `resolve_county` returns `None`:**

> [County name] isn't covered yet — the skill only has parcel data wired for a subset of NC counties. For [county name], go directly to [county GIS site] and export the owner list from there.

**HALT.** Do not attempt any ArcGIS query. Do not show a Python traceback.

If `resolve_county` returns a registry entry, proceed with `entry["service_url"]`, `entry["field_map"]`, and `entry["vacant_filter"]` (if applicable).

---

## Step 3 — Geocode the subject address

Use the chrome-control `open_url` tool to open the Census geocoder (or the county geocoder) and extract the center lat/lon for the subject address.

**Option A — Census geocoder (preferred):**
```
open_url: https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?address=<url-encoded-address>&benchmark=2020&format=json
```
Then use `get_page_content` or `execute_javascript` to read the response and extract `result.addressMatches[0].coordinates` → `{ x: lon, y: lat }`.

**Option B — Wake/county-specific geocoder:**
If the Census geocoder fails, try the county's own GIS geocoder endpoint (e.g. for Wake: `https://maps.wake.gov/arcgis/rest/services/Locators/...`).

Record the center coordinates as `{ lat, lon }` for use in Step 4. Include the geocoded address in your response to the broker for traceability.

---

## Step 4 — Query all pages (truncation guard)

**You MUST loop until `exceededTransferLimit` is false. Partial results are a silent failure — stopping after the first page will miss parcels.**

The `arcgis_query.js` `fetchAllParcels` function handles pagination automatically. Run it via `execute_javascript`:

### 4a — Inject the script

Use the snippet below — the browser-adapted form of `arcgis_query.js` with `export` removed and the function assigned to `window` — directly as the `execute_javascript` payload. (The `arcgis_query.js` file itself keeps `export` for the Node test and is not injectable as-is; use this window-form snippet.)

```javascript
window.fetchAllParcels = async function(serviceUrl, params, fetchImpl = fetch) {
  const all = [];
  let offset = 0;
  const pageSize = 1000;
  while (true) {
    const u = new URL(serviceUrl + "/query");
    u.searchParams.set("f", "json");
    u.searchParams.set("outFields", params.outFields || "*");
    u.searchParams.set("where", params.where || "1=1");
    if (params.geometry) {
      u.searchParams.set("geometry", params.geometry);
      u.searchParams.set("geometryType", "esriGeometryPoint");
      u.searchParams.set("distance", String(params.distance));
      u.searchParams.set("units", "esriSRUnit_StatuteMile");
      u.searchParams.set("spatialRel", "esriSpatialRelIntersects");
      u.searchParams.set("inSR", "4326");
    }
    u.searchParams.set("returnGeometry", "false");
    u.searchParams.set("resultOffset", String(offset));
    u.searchParams.set("resultRecordCount", String(pageSize));
    const resp = await fetchImpl(u.toString());
    const data = await resp.json();
    const feats = data.features || [];
    all.push(...feats.map((x) => x.attributes));
    if (!data.exceededTransferLimit || feats.length === 0) break;
    offset += feats.length;
  }
  return all;
};
return "ok";
```

### 4b — Build and run the query

Build the `where` clause from the registry entry and the parsed request. Resolve the acreage field name from the registry once so this works for **any** county, not just Wake — never hardcode a county's column name:

```javascript
const acreageField = entry.field_map.acreage;   // e.g. "DEED_ACRES" for Wake; other counties differ
const where = [
  entry.vacant_filter,                          // e.g. "LAND_CLASS_DECODE = 'Vacant'"
  `${acreageField} >= ${size.min_acres}`,
  `${acreageField} <= ${size.max_acres}`,
].filter(Boolean).join(" AND ");

const rows = await window.fetchAllParcels(
  entry.service_url,                            // e.g. "https://maps.wake.gov/arcgis/rest/services/Property/Parcels/MapServer/0"
  {
    where: where,
    geometry: JSON.stringify({ x: lon, y: lat }),
    distance: radius_mi,
    outFields: Object.values(entry.field_map).join(","),  // only the fields we need
  }
);
return JSON.stringify({ count: rows.length, rows: rows });
```

Use `execute_javascript` to run this in the page context. The `fetch` call goes out through the browser's network (residential egress) — this is the intentional design; the Cowork sandbox has no outbound HTTPS, but the browser does.

### 4c — Verify completeness

After the query completes, assert the returned count is stable by running a count-only re-query. This is pseudo-code — substitute the same `where` clause and geometry/distance values you built in Step 4b; do not run the placeholders literally:

```text
const countCheck = await fetch(entry.service_url + "/query?f=json&where=<the where built in 4b>&geometry=<the geometry built in 4b>&geometryType=esriGeometryPoint&distance=<radius_mi>&units=esriSRUnit_StatuteMile&spatialRel=esriSpatialRelIntersects&inSR=4326&returnCountOnly=true");
const cc = await countCheck.json();
return cc.count;
```

If the counts differ by more than 2, re-run the full query once. If they still differ, report the discrepancy to the broker rather than silently proceeding.

---

## Step 5 — Deduplicate and format

Map the raw ArcGIS attributes through the county `field_map` to produce normalized rows. For counties where the mailing address is split across `ADDR1`/`ADDR2`/`ADDR3` fields (like Wake), concatenate them:

```python
mail_addr = " ".join(filter(None, [
    r.get(entry["field_map"]["mail_addr"]),       # ADDR1
    r.get("ADDR2", ""),                           # ADDR2 if present
    r.get("ADDR3", ""),                           # ADDR3 if present
])).strip()
```

Build the normalized rows list:
```python
normalized = [
    {
        "owner":      r.get(entry["field_map"]["owner"], ""),
        "mail_addr":  mail_addr,
        "site_addr":  r.get(entry["field_map"]["site_addr"], ""),
        "acreage":    r.get(entry["field_map"]["acreage"], ""),
        "land_class": r.get(entry["field_map"]["land_class"], ""),
    }
    for r in raw_rows
]
```

Then deduplicate and write the CSV:

```python
import helpers
from datetime import date

deduped, report = helpers.dedupe_by_mailing_address(normalized)
out_path = helpers.format_csv(deduped, request, date=str(date.today()))
```

**Report the dedup numbers to the broker:**

> Done — found [report["input"]] matching parcels. After deduplication by mailing address: **[report["output"]] unique owners**. ([report["dropped"]] duplicate mailing addresses removed.)
>
> CSV saved: `[out_path]`

---

## Output

**One CSV file**, short flat filename, written directly to the working directory:

```
owners-<address-slug>-<YYYY-MM-DD>.csv
```

Example: `owners-100-walnut-st-cary-nc-2026-06-02.csv`

**Rules (load-bearing — Windows 218-char path limit):**
- **Never create a subfolder.** No `os.makedirs`, no nested paths.
- **Never use a long descriptive name.** No geography, size range, or date-window strings in the filename — the slug comes from the subject address only.
- The filename is generated by `helpers.default_output_path(request, date)` — do not construct it manually.
- Brokers run Cowork on Windows where the base output path is already ~125 chars deep. A subfolder + long name tips the total over 218 chars and Excel refuses to open the file.

**CSV columns** (in this order): `owner`, `mail_addr`, `site_addr`, `acreage`, `land_class`

---

## Errors — broker-legible only, never a Python traceback

Every error the broker might see must be in plain English:

| Situation | Message |
|---|---|
| chrome-control tools not present | "I need the Claude-for-Chrome extension enabled first. See INSTALL_CLAUDE_FOR_CHROME.md for the one-time setup." + HALT |
| County not in registry | "[County] isn't covered yet — see the county GIS site directly." + HALT |
| Geocode fails | "I couldn't geocode [address] — can you confirm the full street address including city and state?" |
| ArcGIS service unreachable | "The [county] parcel service returned an error ([HTTP status]). The service may be down — try again in a few minutes, or go to [county GIS URL] directly." |
| Zero parcels matched | "No parcels matched [criteria] within [radius] miles of [address] in [county]. Try widening the radius or adjusting the acreage range." |
| Count instability after re-query | "The parcel count varied between two queries ([N1] vs [N2]) — the county service may be under load. Proceeding with [N1] rows; treat the count as approximate." |

**Never surface** a Python exception, a stack trace, an `AttributeError`, or a raw ArcGIS error message to the broker.

---

## Files

- `SKILL.md` — this file (orchestration recipe).
- `helpers.py` — pure-Python helpers: `parse_request`, `dedupe_by_mailing_address`, `slugify`, `default_output_path`, `format_csv`. No network. Call these; do not re-implement inline.
- `county_registry.py` — `COUNTY_REGISTRY` dict + `resolve_county(county_name)`. Source of truth for covered counties and their ArcGIS field names.
- `arcgis_query.js` — paginated ArcGIS fetch template (`fetchAllParcels`). Inject via `execute_javascript` in Step 4.
- `INSTALL_CLAUDE_FOR_CHROME.md` — broker install guide for the chrome-control extension (linked in Step 0).
- `QA_MATRIX.md` — per-county QA ledger (created in Task 10, after per-county QA). Covered counties are PASS or explicitly "not yet covered." No silent gaps.
