---
name: site-infrastructure
description: Who serves this site? For any NC property address, pull the documented utility baseline a buyer or tenant asks about first - broadband (broker-verified row with FCC map link), electric utility (retail service territory, overlapping territories surfaced), water and sewer operators (county GIS + service-area maps + curated registry), and natural gas provider. Every row carries a confidence tag and source. Returns a flyer-ready si-card PDF plus structured JSON. Answers "who serves this site", "what utilities serve [address]", "site infrastructure for [address]", "is there water/sewer/gas at [site]" for industrial and land listings, BOVs, and OMs. Wraps the lee-raleigh-mcp pull_site_infrastructure tool.
---

# Site Infrastructure (Lee & Associates)

Answer one broker question: **"who serves this site, and what's documented?"** For any NC address, the five-row utility baseline - broadband, electric, water, sewer, gas - each row carrying the provider (or the right place to look), a confidence tag, and the source, plus a ready-to-place flyer card.

## When to use

Anything that asks which utilities or providers serve a property - especially industrial and land subjects where an OM, BOV, or buyer call needs the documented baseline.

Triggers:

- `/site-infrastructure <address>` (slash command)
- "Who serves 9725 Stone Quarry Rd, Sanford?"
- "What utilities serve [address]?"
- "Is there water and sewer at [site]?"
- "Who's the electric provider at [address]?"
- "Site infrastructure for [listing]"

**Don't apply this skill to:**

- Capacity questions - megawatts available, water gpm, sewer allocation, gas pressure. Those need a utility conversation; the card's footer says so. Quote the footer, don't guess.
- Demographics / population (use `demographic-summary` or `demographic-detail`).
- Traffic counts (use `vpd-lookup`).
- Nearby businesses / retail context (use `business-key-facts` or `nearby-businesses`).
- Parcel ownership / assessor records (use `parcel-lookup` or `owner-lookup`).
- Non-NC addresses (v1 is NC only).
- Multi-address batch requests (one address at a time).

## Process

1. Parse the broker's request to extract the address as a single free-text string. Don't canonicalize or pre-validate; the geocoder does that server-side.
2. Call the MCP tool `pull_site_infrastructure` with `{address: "<the extracted address>"}`.
3. The response is structured JSON:
   - `subject` - geocoded address, lat/lng, `county_fips` + `county_name`.
   - `layers` - one entry each for `broadband`, `electric`, `water`, `sewer`, `gas`. Each carries `provider` (null when the answer is a link), `confidence_label` (e.g. `parcel-verified`, `service area (2004 NC OneMap)`, `territory (HIFLD 2022)`, `county-level`, `broker-verified`, `see source`), `note`, `link` + `link_label`, and `sources` with vintages.
   - `fragment_html` - the composable si-card fragment (lee-listing-flyer composition path).
   - `pdf_url` - signed link to the rendered flyer card, or `null`.
4. If `pdf_url` is a non-null string, surface it as a "📄 Open PDF" link with an expiry note: *"Link expires soon - download or share it now."* That is the Lee-branded card a broker drops into a flyer / OM / BOV. If `pdf_url` is `null`, deliver the five rows inline and note the card couldn't render this time (suggest a re-run).

## How to present it

Lead with the five-row summary, one line per service, ALWAYS carrying the confidence tag - these are documented baselines, not capacity claims:

> **Electric:** Duke Energy Progress (investor-owned); Central Electric Membership Corp. (cooperative) - *territory (HIFLD 2022)*. Overlapping territories: confirm the serving utility.
> **Water:** TriRiver Water - *county-level* (mains mapped within 500 m, Lee County GIS).
> ...

Presentation rules:

- **Broadband is the broker's row to verify.** It always renders as *broker-verified* with the FCC National Broadband Map link as the starting point - no free source names the provider at parcel level. Say that plainly; never imply a broadband provider was looked up.
- **Overlapping electric territories are normal** (an investor-owned utility and a co-op often both map a point). Name every territory returned and tell the broker to confirm which one serves the parcel.
- **Vintages matter.** A `service area (2004 NC OneMap)` answer means boundaries have grown since - say so when it's the deciding row.
- **Never quote capacity.** The card's footer disclaimer ("Capacity figures ... require utility confirmation") is part of the deliverable.

## Error handling

Same envelope as sibling skills:

- `geocode_failed` - the address didn't resolve. Echo the broker's input back and ask for a city + state hint (rural and raw-land addresses sometimes need the nearest numbered address).
- `out_of_region` - matched address is not in NC. Tell the broker v1 supports NC only.
- `upstream_failed` - geocoder or data lookup hiccup. Apologize and ask the broker to retry.
- `rate_limited` (HTTP 429) - the daily cap (100 pulls/broker/day) is reached; it resets at midnight UTC.
- `internal` - anything else. Apologize, surface a short message, ask David / Bonner to check.

A degraded row (provider null, "see county GIS" / "see NCUC" link) is NOT an error - deliver it as the row's answer with its link. The card always has five rows.

## What's deliberately NOT in v1

- Capacity figures (MW, gpm, sewer allocation, gas pressure) - utility-conversation territory by design.
- Broadband provider names - the row is broker-verified with the FCC map as the aid.
- Non-NC coverage; multi-address batch.

## Files

- `SKILL.md` - this file. The skill is a thin orchestrator over `pull_site_infrastructure`; no Python helpers, no local assets.
- Numeric/copy parity reference: the `site-infrastructure` Python engine at `40_delivery/site-infrastructure/` (Wake Stone Deep River + cold Wilmington samples) in the parent GI repo.

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
   > tools) — the connection is usually fine. Tell me **"YOU DO HAVE ACCESS! TRY
   > AGAIN!"** and I'll re-run it. If it still fails on the retry, a quick sign-in
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
