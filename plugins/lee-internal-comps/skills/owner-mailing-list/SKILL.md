---
name: owner-mailing-list
description: Produce a deduplicated owner + mailing-address list for a Lee & Associates broker from county parcel data. Given an area + criteria request (subject address + radius + property type/land class + acreage or size), calls the lee-raleigh connector's pull_owner_mailing_list tool against the statewide NC OneMap parcel mirror and returns a clean CSV of owner names + mailing addresses + site addresses in seconds, deduplicated by mailing address and filtered to private owners (drops government/exempt/HOA/cemetery parcels). Use for any "owners of <criteria> within <radius> of <address>" / "mailing list for <area>" / "who owns the vacant land near <site>" request. Covers Wake, Durham, New Hanover, Lee, Orange, Johnston, and Chatham counties (NC); coverage grows by county. v1 returns the CSV; Avery labels are a separate skill (gi-plugins #38).
---

# Owner Mailing List

Produce a deduplicated, private-owner mailing-address CSV from county parcel
data. The data work runs **server-side** on the lee-raleigh connector
(`pull_owner_mailing_list`), reading a pre-staged statewide parcel mirror —
no browser, no extension, results in seconds.

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

## Coverage

Wake, Durham, New Hanover, Lee, Orange, Johnston, Chatham (NC), served from
the NC OneMap statewide parcel mirror. For any other county, tell the broker:

> [County name] isn't covered yet. For [county name], go directly to its
> county GIS site and export the owner list from there.

(The tool answers from whatever counties are staged — when in doubt, run the
query; an out-of-footprint address comes back with zero rows or a clear
locate error, never a traceback.)

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

> Got it — I'll pull owners of [land_class] land, [size range if given], within [radius] miles of [address]. Running the parcel query now.

If `radius_mi` is `None`, ask the broker: "How many miles out from [address] should I search?"
If `subject_property.address` is blank, ask the broker for the subject address before continuing.

Acreage handling: `size.min_acres` / `size.max_acres` may be present, one-sided ("3+ acres" → only `min_acres`), or absent — pass through whichever exist.

---

## Step 2 — Call the MCP tool

Call **`pull_owner_mailing_list`** on the lee-raleigh connector:

```json
{
  "address": "100 Walnut St, Cary NC",
  "radius_mi": 3,
  "min_acres": 2,
  "max_acres": 5,
  "land_class": "vacant",
  "private_only": true,
  "dedup_by_mailing": true
}
```

- Always pass `private_only: true` and `dedup_by_mailing: true` (the broker
  contract: private owners, one row per mailing address).
- Omit `min_acres` / `max_acres` / `land_class` when the broker didn't give them.
- `land_class` accepts: `vacant`, `commercial`, `industrial`, `residential`,
  `agricultural`.

The tool returns `{ok, subject, rows, total_matched, truncated, latencyMs}`;
each row carries `owner_raw`, `owner_mail_address`, `address`,
`lot_size_acres`, `land_use`, `distance_mi`. An `ERROR:` text response is
already broker-legible — relay its substance, never a traceback.

---

## Step 3 — Write the CSV file

1. Map tool rows to CSV rows (deterministic, in the sandbox):
   ```python
   rows = helpers.rows_from_mcp(result["rows"])
   ```
2. Write the file:
   ```python
   from datetime import date
   path = helpers.format_csv(rows, request, date.today().isoformat())
   ```
   `format_csv` derives the flat filename via `default_output_path` — e.g.
   `owners-100-walnut-st-cary-nc-2026-06-10.csv`.

**Report to the broker:**

> Done — **[len(rows)] private owners** of [land_class] land within [radius] miles of [address].
> [total_matched] matching parcels; deduplicated by mailing address, government/exempt/HOA/cemetery parcels dropped.
>
> CSV saved: `[filename]`

If `truncated` is true, add: "The list was capped at [len(rows)] rows — tighten the radius or criteria for a complete list."

---

## Output

**One CSV file**, short flat filename, written directly to the working directory:

```
owners-<address-slug>-<YYYY-MM-DD>.csv
```

Example: `owners-100-walnut-st-cary-nc-2026-06-10.csv`

**Rules (load-bearing — Windows 218-char path limit):**
- **Never create a subfolder.** No nested paths.
- **Never use a long descriptive name.** The slug comes from the subject address only; the filename is generated by `helpers.default_output_path(request, date)` — do not construct it manually.
- Brokers run Cowork on Windows where the base output path is already ~125 chars deep; a subfolder + long name tips the total over 218 and Excel refuses to open the file.

**CSV columns** (in this order): `owner`, `mail_addr`, `site_addr`, `acreage`, `land_class`
Note: `land_class` is the county's land-use code (terse in some counties, e.g. `V` for vacant) — best-effort. `owner` + `mail_addr` (street + city + state + zip) are the load-bearing columns.

---

## Errors — broker-legible only, never a Python traceback

| Situation | Message |
|---|---|
| Tool returns `ERROR: Could not locate ...` | "I couldn't locate [address] — can you confirm the full street address including city and state?" |
| Tool returns `ERROR: radius_mi ...` | Ask the broker for a radius up to 25 miles. |
| Zero rows returned | "No parcels matched [criteria] within [radius] miles of [address]. Try widening the radius or adjusting the acreage range." |
| Rows exist but all filtered | "All matching parcels were government/exempt/HOA/cemetery owned — no private prospects in that area. Try widening the radius." |
| Connector unavailable | "The lee-raleigh connector isn't responding — try again in a few minutes." |

**Never surface** a Python exception, a stack trace, or a raw tool error payload to the broker.
