---
name: owner-mailing-list
description: Produce a deduplicated owner + mailing-address list for a Lee & Associates broker from county parcel data. Given an area + criteria request (subject address + radius + property type/land class + acreage or size + whether to limit to improved/built parcels vs. raw land), calls the lee-raleigh connector's pull_owner_mailing_list tool against the statewide NC OneMap parcel mirror and returns a clean CSV of owner names + mailing addresses + site addresses + building square footage + year built in seconds, deduplicated by mailing address and filtered to private owners (drops government/exempt/HOA/cemetery parcels). Use for any "owners of <criteria> within <radius> of <address>" / "mailing list for <area>" / "who owns the vacant land near <site>" / "owners of the buildings near <site>" / "improved parcels within <radius>" request. Covers Wake, Durham, New Hanover, Lee, Orange, Johnston, and Chatham counties (NC); coverage grows by county. v1 returns the CSV; Avery labels are a separate skill (gi-plugins #38).
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
    "improved_only": False,    # True when the broker asked for buildings / improved parcels
    "raw": "<original text>",
}
```

`improved_only` is `True` when the request mentions **buildings / improved / built / structures** ("owners of the buildings near…", "improved parcels within…"); `False` for raw-land or unspecified requests. It means "parcels with a structure on them, not vacant land."

**Confirm back to the broker before proceeding:**

> Got it — I'll pull owners of [improved → "improved (built) parcels" / else "[land_class] land"], [size range if given], within [radius] miles of [address]. Running the parcel query now.

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
  "improved_only": false,
  "private_only": true,
  "dedup_by_mailing": true
}
```

- Always pass `private_only: true` and `dedup_by_mailing: true` (the broker
  contract: private owners, one row per mailing address).
- Omit `min_acres` / `max_acres` / `land_class` when the broker didn't give them.
- `land_class` accepts: `vacant`, `commercial`, `industrial`, `residential`,
  `agricultural`. **It now works per-county** — each county records land use in
  its own vocabulary, and the tool maps the class to that county's actual values
  (Wake, Durham, Johnston, New Hanover, and Chatham are all classified per class).
  Two things to tell the broker when relevant: **Lee and Orange county parcels
  can't be land-class filtered yet** (their land-use field is empty in our data),
  and **New Hanover and Chatham have no separate "vacant" category** — the tool
  reports both cases in `land_class_no_data_counties` (see below), so you never
  have to guess.
- **`improved_only`** — pass `true` (from `request["improved_only"]`) when the
  broker wants **parcels with a building**, not raw land. The tool keeps a parcel
  only if it has a structure (building square footage or a year built on record).
  Omit / `false` for vacant-land or unspecified requests. `improved_only` and
  `land_class: "vacant"` are opposites — never send both.

The tool returns `{ok, subject, rows, total_matched, truncated, no_building_data_counties, land_class_no_data_counties, latencyMs}`;
each row carries `owner_raw`, `owner_mail_address`, `address`,
`lot_size_acres`, `building_sf`, `year_built`, `land_use`, `distance_mi`. An
`ERROR:` text response is already broker-legible — relay its substance, never a
traceback.

**When you filtered by `land_class`, read `land_class_no_data_counties`.**
This array lists counties **in the search area whose parcels can't be filtered by
the requested land class** — either their land-use field is empty in our mirror
(Lee, Orange) or they have no code for that class (New Hanover and Chatham have no
"vacant" category). It's computed live from the data, not a fixed list. If it's
**non-empty**, tell the broker, e.g.:

> Heads up — I couldn't filter **[county names]** by land class (their land-use
> data isn't classified in our mirror yet), so those counties aren't in this list.
> I can pull all owners there instead, or filter by acreage — want me to?

If a land class was requested and **every** in-range county is in
`land_class_no_data_counties` (so `rows` is empty), lead with that explanation
rather than reporting an empty list as if nothing matched.

**Building data is not in every county — read `no_building_data_counties`.**
When you pass `improved_only: true`, the tool returns a
`no_building_data_counties` array: counties **in the search area that have
parcels but carry no building data in the mirror yet**, so they contribute zero
improved parcels. This is computed from the live data (NOT a fixed list — county
coverage grows over time). If that array is **non-empty**, tell the broker, e.g.:

> Heads up — **[county names]** don't carry building data in our parcel mirror
> yet, so I couldn't filter to improved parcels there. The list covers the other
> counties in range. For [those counties] I can pull all owners instead, or
> filter by acreage — want me to?

If `improved_only` was set and **every** county in range is in
`no_building_data_counties` (so `rows` is empty), lead with that explanation
rather than reporting an empty list as if nothing matched.

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
   `format_csv` writes to a tiny constant filename, `o.csv` (enumerating `o1.csv`,
   `o2.csv`, … for a second pull in the same session), and returns the name actually
   written. Use that returned name when you report the file to the broker, and tell
   them they can rename it.

**Report to the broker:**

> Done — **[len(rows)] private owners** of [improved → "improved (built) parcels" / else "[land_class] land"] within [radius] miles of [address].
> [total_matched] matching parcels; deduplicated by mailing address, government/exempt/HOA/cemetery parcels dropped.
>
> CSV saved: `[filename]`

If `truncated` is true, add: "The list was capped at [len(rows)] rows — tighten the radius or criteria for a complete list."

---

## Output

**One CSV file**, a tiny constant filename, written directly to the working directory:

```
o.csv   (o1.csv, o2.csv, … for a second pull in the same session)
```

**Rules (load-bearing — Windows 218-char path limit):**
- **Never create a subfolder.** No nested paths.
- **The filename is forced to `o.csv` by `helpers.format_csv` (via `_safe_csv_name`) — you do not choose it, and the descriptive address never enters the filename.** Do not construct a name manually; use the name `format_csv` returns and tell the broker they can rename it.
- **Why:** brokers run Cowork on Windows where the per-session output dir is already ~190–210 chars deep; Excel refuses to open any file whose full path exceeds 218 chars, so a descriptive name like `owners-100-walnut-st-cary-nc-2026-06-10.csv` tips the total over 218 and the CSV won't open. A 5-char `o.csv` fits. (Same convention as the comps `c.xlsx`; see the comps architecture doc, §5 DELIVER.)

**CSV columns** (in this order): `owner`, `mail_addr`, `site_addr`, `acreage`, `building_sf`, `year_built`, `land_class`
Note: `building_sf` (building square footage) and `year_built` are the building-relevant columns — populated for improved parcels, blank for vacant land or counties without building data (e.g. Chatham). `land_class` is the county's land-use code (terse in some counties, e.g. `V` for vacant) — best-effort. `owner` + `mail_addr` (street + city + state + zip) are the load-bearing columns.

---

## Errors — broker-legible only, never a Python traceback

| Situation | Message |
|---|---|
| Tool returns `ERROR: Could not locate ...` | "I couldn't locate [address] — can you confirm the full street address including city and state?" |
| Tool returns `ERROR: radius_mi ...` | Ask the broker for a radius up to 25 miles. |
| Zero rows returned | "No parcels matched [criteria] within [radius] miles of [address]. Try widening the radius or adjusting the acreage range." |
| Rows exist but all filtered | "All matching parcels were government/exempt/HOA/cemetery owned — no private prospects in that area. Try widening the radius." |
| Connector transient failure (timeout / error that is **not an auth error**) | "The lee-raleigh connector isn't responding — try again in a few minutes." |
| Auth error (`401`/`invalid_token`) from an attempted call, or lee-raleigh tools missing entirely | The reconnect reply in **Connector auth — attempt the call first** below — never a plain retry-later line. |

**Never surface** a Python exception, a stack trace, or a raw tool error payload to the broker.

<!-- BEGIN CONNECTOR-AUTH BLOCK (canonical: shared/connector-auth.md — edit there, then scripts/sync-connector-auth.sh) -->
## Connector auth — attempt the call first

**Never tell the broker the lee-raleigh connector is "not authorized", "not connected",
or "needs to be authorized" unless an actual tool call just failed with an auth error.**

1. **Attempt first.** If the lee-raleigh tools appear in your available tools, call the
   one you need — do not assess authorization beforehand. A needs-auth flag, an empty
   credential field, a `/mcp` probe, or any other indirect signal is NOT authorization
   state; the only way to know is to make the call. If you have not attempted the call
   in this conversation, you do not know the auth state — so call it.
2. **Only a tool-level auth error counts.** Treat the connector as unauthorized ONLY
   when a call you just made returned an authorization error (`401` / `invalid_token`).
   Any other failure — a timeout, an empty result, a data error — is not an auth
   problem; handle it per this skill's error handling, and a plain retry line ("try
   again in a few minutes") is only ever for those transient, not-an-auth failures.
3. **On a genuine auth failure** — an attempted call returned `401`/`invalid_token`, or
   the lee-raleigh tools are missing from this session entirely — reply warmly, in
   broker language:

   > It looks like the Lee Raleigh connection needs a quick sign-in refresh — this can
   > happen after a reinstall, a new computer, or an app update. In Claude, open the
   > **Lee internal comps** plugin, go to its **Connectors** tab, and click the button
   > next to **lee-raleigh**. Sign in with the email you use for Claude (your Lee email
   > for most people) and send yourself the magic link. If the link says it expired,
   > that's normal — just request another from the sign-in page; the second request is
   > what signs you in. Full walkthrough with screenshots:
   > https://leeraleigh.groundedintelligence.io/setup#connect-sign-in — it takes about
   > a minute, then just ask me again.

   Never point a broker at "/mcp", never mention MCP or OAuth by name, and never answer
   an auth failure with "try again in a few minutes" — those leave them stuck.
<!-- END CONNECTOR-AUTH BLOCK -->
