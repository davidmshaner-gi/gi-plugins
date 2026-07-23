---
name: owner-lookup
description: Look up the owner of record and owner mailing address for a US property in the counties covered by the owner-graph bulk ingest (Wake, Durham, New Hanover, and Lee — NC). Accepts a street address OR a parcel ID / PIN. Returns the parcel's assessor record (owner name, mailing address, year built, lot size, building SF, assessed value, last sale, zoning, jurisdiction). When the same street address exists more than once, returns a candidate list of parcel IDs to re-run with; near-miss addresses (reordered wording, wrong house number, abbreviation variants) return a ranked did-you-mean candidate list instead of a dead not-found. Wraps the lee-raleigh-mcp owner_lookup tool.
---

# Owner Lookup (Lee & Associates)

Resolve a US street address to the owner of record + owner mailing address plus the parcel's assessor facts, by reading the Cloudflare D1 owner graph. Data is bulk-staged from county GIS endpoints; this skill never hits a county API at request time, so it's sub-second.

## When to use

Anything that asks "who owns X," "what's the mailing address for X," or "give me the assessor facts on X" for a property in the four covered NC counties.

Triggers:

- `/owner-lookup <address>` (slash command)
- "Who owns 100 Connemara Dr, Cary NC?"
- "Mailing address for 1500 W Main St, Durham"
- "Who's the owner of record at 201 N Front St, Wilmington?"
- "Owner + assessed value for [address]"

**Don't apply this skill to:**

- Addresses outside Wake, Durham, New Hanover, or Lee NC. Other counties land in v1.1.
- Phone or email for owners — those are NULL in v1 (contact enrichment is deferred).
- Portfolio rollups ("what else does this owner own?") — the graph supports it but a portfolio tool is a separate v1.1 skill.
- Owner history (prior deeds) — v1 returns the CURRENT owner only.
- Sale / lease comp requests (those are `internal-comps` / `external-comps`).
- Demographic profiles (those are `demographic-summary` / `demographic-detail` / `business-key-facts`).

## Process

1. Parse the broker's request to extract the address as a single free-text string. Comma-separated `street, city, state` is best; the engine normalizes (uppercases, strips punctuation, expands directionals and suffixes) and, when the same street address exists more than once, uses the city after the comma to auto-pick the right parcel — so always keep the city/state the broker gave you.
2. **If the broker gives you a parcel ID / PIN instead of (or in addition to) an address** — a value that's all digits with optional dots/dashes, e.g. `0763592649` (Wake/Lee) or `3117-79-5148.000` (New Hanover OneMap parno) — pass it as `parcel_id`. (A bare PIN passed as `address` is also recognized, but `parcel_id` is clearer.) This is the disambiguation path: when a multi-match response lists candidate parcel IDs, re-run with the one the broker wants.
3. If the broker explicitly mentions the county OR a multi-match response says the candidates span more than one county, pass `county` as one of: `Wake`, `Durham`, `NEW_HANOVER`, `Lee`. Do NOT pass a county to resolve a same-county collision — it can't; use `parcel_id` for that.
4. Call the MCP tool `owner_lookup` with `{address: "<the extracted address>", county: "<county-or-omit>", parcel_id: "<PIN-or-omit>"}`. The tool is sub-second (indexed D1 lookup, no external APIs on the request path).
5. The response is a JSON parcel record. Render the broker-facing essentials inline conversationally — county, parcel_id, owner_raw, owner_mail_address, assessed_value_total, year_built, lot_size_acres, building_sf, land_use, last_sale_date, last_sale_price. Format the mailing address as multi-line (it's stored with embedded `\n`).
6. **REQUIRED — every successful response MUST end with the verification footer.** This is not optional, not dependent on broker phrasing, not skippable when the data looks "obviously fine." See "Verification footer" below for the exact rendering — choose the URL template from the table that matches the parcel's `county` field, substitute the PIN for Wake (URL-encoded), and emit the markdown link inline at the end of the response. If the parcel is in WAKE the link IS a deep-link (the broker clicks once); for DURHAM / NEW_HANOVER / LEE the link opens a search form and the response must also include the literal `search by PIN: \`<PIN>\`` text so the broker has the PIN to paste.
7. If the tool returns an error, fall through to the Error Handling section below.

## Error handling

The tool returns broker-legible error messages directly; surface them as-is and apologize if needed:

- **"No parcel found for ..."** — the address (or PIN) didn't match. Possible reasons: outside the covered counties (Wake, Durham, NHC, Lee NC), or the address needs city / state to disambiguate. Echo the input back and ask for a more specific spelling or county hint.
- **"No exact match for ... Closest parcels on record:"** — the address didn't match exactly, but the tool found near-misses (reordered wording, a slightly different house number, an abbreviation like "Saint" vs "St"). Handle it EXACTLY like the multi-match list below: show the broker the candidates (each has a parcel_id, locality, county, and site address, ranked nearest-first) and **re-run `owner_lookup` with `parcel_id` set to their choice**. Note: a reordered-but-identical address (e.g. "1917 NC Highway 98 E" vs the county's "1917 E NC 98 HWY") now resolves automatically — no broker action needed, you'll just get the parcel.
- **"Multiple parcels match ...":** the same street address exists more than once. The message lists each candidate as `parcel_id <PIN> — <locality> (<county>), <site address>`. Show the broker the list and ask which one, then **re-run `owner_lookup` with `parcel_id` set to their choice** (NOT the address again). Only when the message explicitly says the candidates span different counties does passing `county` help; for a same-county collision (e.g. two `100 Walnut St` in Wake — Cary vs Wendell) the parcel_id is the only resolver. If the broker already named the city, include it in the address (`100 Walnut St, Cary NC`) and the tool auto-picks.
- Anything else (HTTP error, timeout, etc.) — apologize, surface the short message, suggest a retry. Worst case, point the broker to the county's municipal GIS (Wake iMaps, Durham GoMaps, NHC GIS Map, Lee NC GIS) for manual lookup.

## What's in the response

For a matched parcel:

- **county** — `WAKE`, `DURHAM`, `NEW_HANOVER`, or `LEE`
- **parcel_id** — the county's canonical PIN
- **address** — the assessor's situs address (the on-file street + number)
- **owner_raw** — owner name(s) exactly as recorded by the assessor
- **owner_mail_address** — owner mailing address with embedded newlines (street, then city/state/zip line)
- **year_built**, **lot_size_acres**, **building_sf**, **assessed_value_total** — assessor's structural + valuation facts
- **land_use**, **zoning_code** — assessor's land-use classification and zoning code (zoning_code may be null for some parcels)
- **last_sale_date**, **last_sale_price** — most-recent recorded sale; null when never sold or not yet refreshed
- **jurisdiction** — the assessor's jurisdiction code (e.g., `CARY`, `RA`, `WC` for Wake; varies by county)

## REQUIRED: Verification footer

**Every successful `owner_lookup` response MUST end with a verification footer that includes a county-specific link.** This is the load-bearing UX of the skill — brokers use the link to confirm freshness against the authoritative county portal before relying on the data for offer letters or deed work. Omitting the footer is a skill-output bug, not a stylistic choice.

The footer paragraph format is:

> Heads-up on freshness: this is from our bulk-staged copy of {COUNTY} County's GIS, refreshed roughly quarterly — not live. For anything time-sensitive (offer letters, deed work), verify against **[{Portal Name}]({Resolved URL})**{paste-hint}.

Where:
- `{COUNTY}` is the human-readable county name (`Wake`, `Durham`, `New Hanover`, or `Lee`).
- `{Portal Name}` and `{Resolved URL}` come from the table below.
- `{paste-hint}` is empty string for WAKE (the link IS a deep-link to the parcel); for DURHAM / NEW_HANOVER / LEE it is the exact literal text ` — search by PIN: \`<PIN>\`` so the broker can paste the PIN into the search form on the other side.

### Per-county verification portals

These were verified via Chrome DevTools on 2026-05-23 with the sentinel PINs and they do what's described in the "Behavior" column. For Wake, substitute `{PIN}` with the parcel's `parcel_id` value (URL-encode if needed).

| County | Portal | URL template | Behavior |
|---|---|---|---|
| **WAKE** | Wake iMaps | `https://maps.raleighnc.gov/imaps/?pin={PIN}` | **Direct deep-link.** Opens iMaps with the parcel pre-selected; the broker accepts a one-time disclaimer and lands on the parcel's full Info pane (owner, mail, valuation, last sale, building). |
| **DURHAM** | Durham Tax CAMA | `https://taxcama.dconc.gov/camapwa/#PIN` | Opens Durham's CAMA portal with the PIN search tab already expanded. Broker pastes the 10-digit PIN and clicks search. |
| **NEW_HANOVER** | NHC etax | `https://etax.nhcgov.com/PT/search/commonsearch.aspx?mode=parid` | Tyler iasWorld. After accepting the disclaimer (once per session), opens the Parcel ID search form. Broker pastes the PIN and clicks Search. |
| **LEE** | Lee County Tax Access | `https://taxaccess.leecountync.gov/pt/search/commonsearch.aspx?mode=realprop` | Tyler iasWorld, like NHC — but Lee's working entry point is the Real Estate Property search (`mode=realprop`), **not** `mode=parid`, which throws an error page on this county's instance. Accept the disclaimer, paste the PIN, click Search. |

### Worked examples of the verification footer (copy this format exactly)

**Wake** (parcel `0734835370`):
> Heads-up on freshness: this is from our bulk-staged copy of Wake County's GIS, refreshed roughly quarterly — not live. For anything time-sensitive (offer letters, deed work), verify against **[Wake iMaps](https://maps.raleighnc.gov/imaps/?pin=0734835370)**.

**Durham** (parcel `0822419440`):
> Heads-up on freshness: this is from our bulk-staged copy of Durham County's GIS, refreshed roughly quarterly — not live. For anything time-sensitive (offer letters, deed work), verify against **[Durham Tax CAMA](https://taxcama.dconc.gov/camapwa/#PIN)** — search by PIN: `0822419440`.

**New Hanover** (parcel `R04720-007-011-000`):
> Heads-up on freshness: this is from our bulk-staged copy of New Hanover County's GIS, refreshed roughly quarterly — not live. For anything time-sensitive (offer letters, deed work), verify against **[NHC etax](https://etax.nhcgov.com/PT/search/commonsearch.aspx?mode=parid)** — search by PIN: `R04720-007-011-000`.

**Lee** (parcel `9645-45-9484-00`):
> Heads-up on freshness: this is from our bulk-staged copy of Lee County's GIS, refreshed roughly quarterly — not live. For anything time-sensitive (offer letters, deed work), verify against **[Lee County Tax Access](https://taxaccess.leecountync.gov/pt/search/commonsearch.aspx?mode=realprop)** — search by PIN: `9645-45-9484-00`.

**Do NOT** ship the response without this footer, ever. **Do NOT** use a generic Wake-only link when the parcel is in Durham, NHC, or Lee.

### Known data gaps

NHC parcels have **null lat/lng** in v1 (the County's PropertyOwners layer doesn't carry usable polygon geometry on the free endpoint); this is a known limitation, not a defect.

Lee NC parcels have **null `last_sale_date`, `last_sale_price`, and `zoning_code`** in v1 — those fields live in separate Lee GIS layers and are deferred to v2.

## Examples

### Example 1 — happy path

Broker: "Who owns 100 Connemara Dr in Cary?"
Skill: calls `owner_lookup({address: "100 Connemara Dr, Cary NC"})`.
Tool: returns `{county: "WAKE", parcel_id: "0734835370", owner_raw: "PNC OF NORTH CAROLINA LLC", owner_mail_address: "7930 SKYLAND RIDGE PKWY\nRALEIGH NC 27617-6813", ...}`.
Skill renders: "Owner of 100 Connemara Dr, Cary (WAKE/0734835370): PNC OF NORTH CAROLINA LLC. Mailing address: 7930 Skyland Ridge Pkwy, Raleigh NC 27617-6813. Assessed value: $X, building SF: Y, last sale Z/$W."

### Example 2 — same-county collision, then resolve by parcel ID

Broker: "Who owns 100 Walnut St?"
Skill: calls `owner_lookup({address: "100 Walnut St"})`.
Tool: returns a multi-match list:
> Multiple parcels match "100 Walnut St":
>   - parcel_id 0763592649 — CARY (WAKE), 100 WALNUT ST
>   - parcel_id 1783894364 — WENDELL (WAKE), 100 WALNUT ST
> Re-run owner_lookup with the exact parcel_id of the one you want (pass it as `address` or as `parcel_id`).

Skill: "There are two 100 Walnut St in Wake — one in Cary, one in Wendell. Which one?" Broker: "Cary." Skill: re-runs `owner_lookup({parcel_id: "0763592649"})` and returns that parcel (with the verification footer). (If the broker had said "100 Walnut St, Cary NC" up front, the tool would have auto-picked Cary in one call.)

### Example 2b — broker has a PIN

Broker: "Pull the owner for PIN 0763592649."
Skill: calls `owner_lookup({parcel_id: "0763592649"})`.
Tool: returns the WAKE parcel directly. Skill renders the owner + footer.

### Example 3 — out of scope

Broker: "Who owns 500 Oak Ave, Charlotte NC?"
Skill: calls `owner_lookup({address: "500 Oak Ave, Charlotte NC"})`.
Tool: returns "No parcel found ... outside the covered counties (Wake, Durham, New Hanover, Lee NC)."
Skill: "I don't have Charlotte (Mecklenburg County) yet — coverage is currently Wake, Durham, New Hanover, and Lee in NC. For Charlotte, try Mecklenburg County's POLARIS GIS at https://polaris3g.mecklenburgcountync.gov/."

## What's deliberately NOT in v1

- **Owner phone / email** — contact enrichment layer is deferred (no free public source).
- **Portfolio rollups** ("everything owner X owns") — the owner graph supports this but a `portfolio-lookup` skill is a v1.1 deliverable.
- **Owner history / prior deeds** — current owner only.
- **More counties** — Johnston, Brunswick, Pender are next. Mecklenburg / Buncombe / Guilford are larger projects.
- **LLC resolution** (NC Secretary of State entity lookup) — v1.1.

## Files

- `SKILL.md` — this file. The skill is a thin orchestrator over the `owner_lookup` MCP tool on `lee-raleigh-mcp`. No Python helpers, no local assets, no PDFs. Everything happens server-side in the Worker.

<!-- BEGIN CONNECTOR-AUTH BLOCK (canonical: shared/connector-auth.md — edit there, then scripts/sync-connector-auth.sh) -->
## Connector auth — attempt the call first

**Never tell the broker the lee-raleigh connector is "not authorized", "not connected",
or "needs to be authorized" unless an actual tool call just failed with an auth error —
or the lee-raleigh tools are missing from this session entirely.**

1. **Attempt first.** If the lee-raleigh tools appear in your available tools, call the
   one you need — do not assess authorization beforehand. A needs-auth flag, an empty
   credential field, a `/mcp` probe, or any other indirect signal is NOT authorization
   state; the only way to know is to make the call. If you have not attempted the call
   in this conversation, you do not know the auth state — so call it.
2. **Only a tool-level auth error counts.** Treat a call as auth-failed ONLY when it
   returned an authorization error (`401` / `invalid_token`). Any other failure — a
   timeout, an empty result, a data error — is not an auth problem; handle it per this
   skill's error handling, and a plain retry line ("try again in a few minutes") is
   only ever for those transient, not-an-auth failures.
3. **Auth failure with the lee-raleigh tools loaded — and the immediately preceding
   attempt (if any) did NOT also auth-fail:** the most likely cause is a known Claude
   bug that reports a successful call as failed — the connection is usually fine, so
   do NOT send the broker to sign-in yet. This applies to any such failure, including
   one later in a conversation whose earlier glitch already healed. Reply warmly, in
   broker language:

   > That error is most likely a Claude glitch (on Anthropic's side, not the Lee
   > tools) — the connection is usually fine. Tell me **"you do have access — try
   > again"** and I'll re-run it. If it still fails on the retry, a quick sign-in
   > refresh usually fixes it
   > (https://leeraleigh.groundedintelligence.io/setup#connect-sign-in) — or email
   > David at david@groundedintelligence.io and he'll get you sorted.

   When the broker prompts the retry, attempt the call again.
4. **Two auth failures in a row — or the lee-raleigh tools are missing from this
   session entirely:** treat it as a genuine sign-in problem.
   Reply warmly, in broker language:

   > It looks like the Lee Raleigh connection needs a quick sign-in refresh — this can
   > happen after a reinstall, a new computer, or an app update. In Claude, open the
   > **Lee internal comps** plugin, go to its **Connectors** tab, and click the button
   > next to **lee-raleigh**. Sign in with the email you use for Claude (your Lee email
   > for most people) and send yourself the magic link. If the link says it expired,
   > that's normal — just request another from the sign-in page; the second request is
   > what signs you in. Full walkthrough with screenshots:
   > https://leeraleigh.groundedintelligence.io/setup#connect-sign-in — it takes about
   > a minute, then just ask me again. If that doesn't get you back in, email David at
   > david@groundedintelligence.io and he'll get you sorted.

   Never point a broker at "/mcp", never mention MCP or OAuth by name, and never answer
   an auth failure with "try again in a few minutes" — those leave them stuck.
<!-- END CONNECTOR-AUTH BLOCK -->
