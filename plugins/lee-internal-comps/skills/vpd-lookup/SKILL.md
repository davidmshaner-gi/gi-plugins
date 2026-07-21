---
name: vpd-lookup
description: Traffic counts (vehicles per day / AADT) near any NC address — either the busiest roads nearby, or the count for ONE specific roadway the broker names. Returns ranked road segments (each with its annual average daily traffic, count year, and distance) plus a ready-to-place flyer card. Answers "how much traffic passes this site", "VPD on the nearby roads", "traffic counts near [address]", and "traffic on [Road] near [address]" / "VPD on [Six Forks Rd / US-1]" for a retail / QSR / flex listing. Wraps the lee-raleigh-mcp pull_vpd_lookup tool.
---

# VPD Lookup (Lee & Associates)

Show traffic counts near a site, for any NC address — the top-5 **busiest roads nearby**, or, when the broker names a **specific roadway**, the count for **that road**. AADT = annual average daily traffic (a.k.a. vehicles per day / VPD), each with the count year and distance from the site, plus a ready-to-place flyer card.

Two modes, decided by whether the broker named a road:
- **Area mode** (no road named) — top-5 nearby roads by class then volume. "Traffic near this corner."
- **Road mode** (a road IS named) — only the stations on that roadway. "Traffic *on Glenwood Ave*." This is the right answer when a broker asks about a particular street — returning the busiest *other* road nearby (e.g. an interstate a block away) is the failure brokers complained about.

## When to use

Anything that asks about traffic volume, vehicle counts, or VPD/AADT on the roads around a site — especially for a retail, QSR, convenience, or flex listing where roadside exposure matters.

Triggers:

- `/vpd-lookup <address>` (slash command)
- "Traffic counts near 8541 Concord Mills Blvd, Concord" (area mode)
- "What's the VPD on the roads by [address]?" (area mode)
- "How much traffic passes [address]?" (area mode)
- "AADT for [address]" (area mode)
- "Vehicles per day near [site]" (area mode)
- "Traffic counts **on Glenwood Ave** near [address]" (road mode — road named)
- "VPD **on Six Forks Rd** at [address]" (road mode)
- "AADT **on US-1 / NC-54 / Highway 70** near [site]" (road mode)
- "How busy is **[Capital Blvd]** by [address]?" (road mode)

**Don't apply this skill to:**

- Population / income / demographics around a site (use `demographic-summary` or `demographic-detail`).
- The workforce / labor pool around a site (use `labor-shed`).
- Nearby businesses / retail context (use `business-key-facts` or the nearby-businesses tooling).
- Sale or lease comp requests (those are `internal-comps` / `external-comps`).
- Turning-movement counts, peak-hour volumes, or trip generation — AADT is an annual daily average, not a peak-hour or directional count.
- Multi-address batch requests (v1 supports one address at a time).
- Non-NC addresses (v1 supports NC only — NCDOT data).

## Process

1. Parse the broker's request to extract the **address** as a single free-text string. Don't canonicalize or pre-validate; the Census Geocoder does that server-side.
2. **Decide the mode — did the broker name a specific roadway?** If the ask is about a *particular* road ("traffic **on** Glenwood Ave", "VPD on Six Forks Rd", "how busy is US-1 / Capital Blvd / Highway 70"), extract that road name. If the ask is just about the area ("traffic near [address]", "VPD around here"), there's no road.
   - **The address that's also a street is NOT automatically the road.** "Traffic near 4325 Glenwood Ave" is *area* mode (the address happens to be on Glenwood). Only go to road mode when the broker is clearly asking about a road *as the subject* — usually signalled by "on [Road]", "[Road] traffic", or naming a road different from (or in addition to) the site address. When genuinely ambiguous, default to **area** mode (omit `road`).
3. Call the MCP tool `pull_vpd_lookup`:
   - **Area mode:** `{address: "<the extracted address>"}` — busiest roads nearby (the default).
   - **Road mode:** `{address: "<address>", road: "<the named road>"}` — pass the road exactly as the broker said it (e.g. `"Glenwood Ave"`, `"Six Forks Rd"`, `"US-1"`, `"Highway 70"`). The tool name-matches it against the NCDOT route id and local alias (tolerant of Rd/Road, Ave/Avenue, US 1/US-1 forms) and returns **only stations on that road**.
4. The response is structured JSON: `subject` (geocoded address + 1.5-mi radius), `segments` (ranked road segments — each with `route`, `rte_cls_label`, `value` / `value_rounded` AADT, `year`, `distance_miles`, and a `display.callout`), `meta` (provenance; in road mode also `meta.road_filter = {requested, matched}`), `pdf_url` (a signed link to the rendered flyer card, or `null`), `fragment_html` (the same card as a composable HTML fragment), and — road mode only — an optional top-level `message`.
   - **Area mode:** lead with the busiest road, then offer the full top-5.
   - **Road mode, match found** (`segments` non-empty): lead with that road's count — this is the road the broker asked about.
   - **Road mode, NO match** — you passed `road` and `segments` is empty (the tool will also set `message` and `meta.road_filter.matched: 0`): **relay the `message` verbatim** — it explains there's no NCDOT count station on that road within 1.5 mi and points to nearby cross-streets / `trafficmap.ncdot.gov`. **Do NOT silently fall back to the busiest nearby road** — returning an unrelated road as if it were the requested one is the exact bug this mode fixes. You may *offer* to re-run in area mode ("want the busiest roads near there instead?"), but don't auto-substitute.
5. If `pdf_url` is a non-null string, surface it as a "📄 Open PDF" link with a 1-hour expiry note: *"Link expires in ~1 hour, download or share it now."* — that is the polished Lee-branded traffic-counts card a broker drops into a flyer / OM / BOV. If `pdf_url` is `null`, deliver the inline segments and note the card couldn't render this time (suggest a re-run). `fragment_html` is the same card as a raw HTML fragment for the lee-listing-flyer composition path — mention it only if the broker is assembling a flyer programmatically.

## How to present it

**Area mode** — lead with the headline road, not the table:

> Within 1.5 miles of [site], the busiest road is **[road_name]** at **[value_rounded] VPD** ([year] count), about **[distance] mi** away. The next-busiest are [#2], [#3]… (top 5 by road class then volume).

Then offer the full ranked list or the flyer card if they want it. Each row reads `[AADT] VPD on [road] — [year] count, [distance] mi`.

Area ranking is by road class first (Interstate > US > NC highway > secondary), then AADT descending, then proximity — so an Interstate a mile out leads a busier-feeling secondary road right at the door, which matches how brokers talk about a site's road network. Say so if a broker asks why a closer road ranks lower.

**Road mode (match)** — lead with the named road's count, not the area:

> **[Road]** near [site] carries **[value_rounded] VPD** ([year] count){, plus a second station at [value_rounded] VPD if more than one}. ([Note when the road is a US/NC route, e.g. "Glenwood Ave here is US-70."])

**Road mode (no match)** — relay the tool's `message`; don't substitute another road:

> There's no NCDOT count station on **[Road]** within 1.5 mi of [site]. [the tool's message — nearby cross-street / trafficmap.ncdot.gov]. Want the busiest roads near there instead?

## Error handling

Same envelope as sibling skills:

- `geocode_failed` — the address didn't resolve. Echo the broker's input back and ask for a city + state hint.
- `out_of_region` — matched address is not in NC. Tell the broker v1 supports NC only.
- `upstream_failed` — Census geocoder or D1 lookup hiccup. Apologize and ask the broker to retry.
- `rate_limited` (HTTP 429) — the broker has hit the daily cap (100 lookups/broker/day). Relay the message plainly: the daily limit is reached and resets at midnight UTC.
- `internal` — anything else. Apologize, surface a short message, ask David / Bonner to check.

Empty `segments` means different things by mode:
- **Area mode** (no `road` passed): no AADT-counted roads within 1.5 mi — common for a deep-rural site. Tell the broker plainly and suggest the nearest counted corridor is farther out.
- **Road mode** (`road` passed, `meta.road_filter.matched: 0`, `message` present): the named road simply has no count station in range — relay the `message` (see Process step 4); this is NOT "deep rural," so don't describe it that way.

## What's deliberately NOT in v1

- Custom radius or a configurable top-N (v1 is the top 5 within 1.5 mi).
- Peak-hour / directional / turning-movement counts — AADT is an annual daily average only.
- Multi-state coverage — NC only (NCDOT AADT stations).
- Multi-address batch.

## Files

- `SKILL.md` — this file. The skill is a thin orchestrator over `pull_vpd_lookup`; no Python helpers, no local assets.
- Numeric parity reference: the `vpd-lookup` Python engine at `40_delivery/vpd-lookup/` (Concord + Cary samples). The Worker tool stages NCDOT AADT statewide to D1 and reads only from storage on the request path.

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
