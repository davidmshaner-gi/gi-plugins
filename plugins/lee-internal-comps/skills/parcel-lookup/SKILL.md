---
name: parcel-lookup
description: Pull the full county property record for a US property address in the covered NC counties (Wake, Durham, New Hanover, Lee, Johnston, Orange, Chatham) — owner of record + mailing address, parcel ID (PIN), lot size, building SF, year built, tax assessed value, last sale date/price, zoning code with ordinance link, and building permits from the last 5 years. Returns the record inline, a flyer-ready Property Facts fragment, and a Lee-branded PDF card. Near-miss addresses (reordered wording, wrong house number, abbreviation variants) return a ranked did-you-mean candidate list instead of a dead not-found. Use for "what is this property," "property record card," "zoning for," "permits at," or pre-tour/pre-call homework on an address. Wraps the lee-raleigh-mcp pull_parcel_lookup tool.
---

# Parcel Lookup (Lee & Associates)

Resolve a US street address to the official county parcel record — owner, lot/building facts, valuation, last sale, zoning, and the last 5 years of building permits — by reading the Cloudflare D1 parcel substrate. All county data is bulk-staged offline; this skill never hits a county API at request time, so it's seconds, not minutes. It also returns a flyer-ready `pl-card` HTML fragment and a one-page Lee-branded **Property Facts** PDF card.

## When to use

Anything that asks "what is this property," "give me the property record / parcel card on X," "what's X zoned," "any permits pulled at X," or the standard pre-tour / pre-call homework on an address.

Triggers:

- `/parcel-lookup <address>` (slash command)
- "What's the property record on 421 Fayetteville St, Raleigh?"
- "What's 7600 Poole Rd zoned?"
- "Any building permits at 100 Walnut St, Cary in the last few years?"
- "Property facts card for [address] for my flyer"

**Don't apply this skill to:**

- "Who owns X" / "mailing address for X" ONLY — `owner-lookup` is the lighter tool for that single question (this skill includes owner facts too, but owner-lookup is the dedicated path).
- Prospecting lists by criteria — that's `owner-mailing-list`.
- Sale / lease comps — `internal-comps` / `external-comps` / `internal-and-external-comps`.
- Demographics — `demographic-summary` / `demographic-detail` / `business-key-facts`.
- Addresses outside the seven covered NC counties.

## Process

1. Extract the address as one free-text string (comma-separated `street, city, state` works best; the engine normalizes case, punctuation, directionals, suffixes).
2. If the broker names the county, or a previous attempt returned a multi-county collision, pass `county` as one of: `Wake`, `Durham`, `NEW_HANOVER`, `Lee`, `Johnston`, `Orange`, `Chatham`.
3. Call the MCP tool `pull_parcel_lookup` with `{address: "<address>", county: "<county-or-omit>"}`.
4. Render the broker-facing essentials inline conversationally:
   - **Property:** situs address, county, PIN, jurisdiction
   - **Facts:** lot size (acres), building SF, year built, assessed value, last sale (price + date)
   - **Zoning:** code + jurisdiction label, with the `definition_url` as a clickable ordinance link; when `zoning` is null say "zoning: see municipal GIS"
   - **Permits:** when `permits_available` is true, list `permits_last_5y` (date, short description, value, status) or say "no permits in the last 5 years"; when false, say permit data isn't available for that jurisdiction
   - **Owner:** owner of record + mailing address (multi-line; stored with embedded `\n`), and the NC SOS search link when `owner_sos_search_url` is present
5. **PDF card:** if `pdf_url` is non-null, end with a "📄 Open the Property Facts card (PDF)" link and note the link expires in about an hour. If `pdf_url` is null, deliver the inline record and suggest re-running if the broker wanted the card. The `fragment_html` field is for flyer composition — don't paste it into chat.
6. **REQUIRED — every successful response MUST end with the verification footer** (below). Same contract as `owner-lookup`: choose the portal from the per-county table, deep-link for Wake, paste-the-PIN hint for the others.
7. On error, fall through to Error handling.

## Error handling

The tool returns broker-legible errors; surface them as-is:

- **"No parcel found for ..."** — outside the covered counties, or the address needs a city/state. Echo the input back and ask for a more specific spelling or a county hint.
- **"No exact match for ... Closest parcels on record:"** — near-miss recovery: the address didn't match exactly but close candidates exist (reordered wording, slightly different house number, abbreviation variants). Show the broker the candidate list (ranked nearest-first, each with parcel_id, county, and site address) and re-run with the exact site address shown — or use `owner-lookup` with the candidate's parcel_id (PIN). Reordered-but-identical addresses now resolve automatically with no broker action.
- **"Multiple parcels match ..."** — same street address in more than one county; the error lists candidates. Ask which county and re-call with `county`.
- **geocode_failed / out_of_region** — the address didn't geocode or isn't NC; ask for a cleaner address.
- Anything else — apologize, surface the short message, suggest a retry; worst case point the broker at the county GIS portal (table below).

## What's in the response

- `subject` — parcel_id (PIN), county, jurisdiction (normalized, e.g. `RALEIGH`), situs address, owner, owner_mail_address, owner_sos_search_url, lat/lng, matched_address
- `assessor` — year_built, lot_size_acres, building_sf, assessed_value_total, last_sale_date, last_sale_price (any can be null; render `n/a`)
- `zoning` — `{code, jurisdiction, definition_url}` or null (null ⇒ "see municipal GIS")
- `permits_available` — whether a permits feed covers this jurisdiction (Raleigh, Cary, Durham County, New Hanover County: yes; Lee + Johnston/Orange/Chatham: not yet)
- `permits_last_5y` — up to 25 permits, newest first: permit_number, permit_type, description, issued_date, status, estimated_value
- `sources` — the staged data layers behind the record
- `fragment_html` — the `pl-card` flyer fragment (for composition, not chat)
- `pdf_url` — signed ~1-hour link to the Property Facts PDF card, or null

### Coverage + known gaps (be upfront when asked)

- **Zoning:** Raleigh + Cary (Wake), Durham (city + county), New Hanover (all munis), Lee (county-wide). Other Wake municipalities (Apex, Morrisville, …) and Johnston/Orange/Chatham show "see municipal GIS."
- **Permits:** Raleigh, Cary, Durham County, New Hanover County feeds, last 5 years. Lee County has no public permits endpoint (upstream gap); the new counties aren't staged yet.
- **year_built:** null for Durham + New Hanover (lives in the counties' internal CAMA systems, not their open GIS) — that's upstream, not a defect.
- **building_sf / last sale:** best-effort from the county assessor; null renders as `n/a`.

## REQUIRED: Verification footer

Every successful response MUST end with the freshness footer — same rule and same per-county portal table as the `owner-lookup` skill:

> Heads-up on freshness: this is from our bulk-staged copy of {COUNTY} County's records (parcels refreshed roughly quarterly; permits roughly monthly) — not live. For anything time-sensitive (offer letters, deed work), verify against **[{Portal Name}]({Resolved URL})**{paste-hint}.

| County | Portal | URL template | Behavior |
|---|---|---|---|
| **WAKE** | Wake iMaps | `https://maps.raleighnc.gov/imaps/?pin={PIN}` | Direct deep-link; parcel pre-selected. |
| **DURHAM** | Durham Tax CAMA | `https://taxcama.dconc.gov/camapwa/#PIN` | PIN search tab open; broker pastes the 10-digit PIN — include `search by PIN: \`<PIN>\``. |
| **NEW_HANOVER** | NHC etax | `https://etax.nhcgov.com/PT/search/commonsearch.aspx?mode=parid` | Parcel-ID search form; include the paste hint. |
| **LEE** | Lee County Tax Access | `https://taxaccess.leecountync.gov/pt/search/commonsearch.aspx?mode=realprop` | Real Estate Property search (NOT `mode=parid`); include the paste hint. |
| **JOHNSTON / ORANGE / CHATHAM** | county GIS | name the county GIS portal in prose | no verified deep-link yet — tell the broker to search the county GIS by address. |

## Examples

### Example 1 — happy path (Raleigh)

Broker: "Property record on 421 Fayetteville St, Raleigh?"
Skill: calls `pull_parcel_lookup({address: "421 Fayetteville St, Raleigh NC"})`.
Renders: owner (Highwoods Realty LP + mailing), PIN 1703761946, 0.55 ac, 395,760 SF, built 1985, assessed $74.85M, last sale $68.05M / 2014-09, zoning DX-40-SH (City of Raleigh, ordinance link), recent permits list, the PDF card link, then the Wake iMaps verification footer.

### Example 2 — zoning-only ask

Broker: "What's 100 Walnut St in Cary zoned?"
Skill: same tool call; leads with the zoning code + Cary ordinance link, gives the rest of the record briefly, PDF link, footer.

### Example 3 — uncovered permits

Broker: "Permits at 100 Industrial Dr, Sanford?"
Skill: returns the Lee parcel record, says permit data isn't available for Lee County yet (no public county endpoint), still gives zoning + facts + footer.

## Files

- `SKILL.md` — this file. Thin orchestrator over the `pull_parcel_lookup` MCP tool on `lee-raleigh-mcp`. No local helpers; everything is server-side in the Worker.

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
