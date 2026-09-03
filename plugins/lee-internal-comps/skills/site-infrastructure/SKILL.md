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

- `geocode_failed` / `not_found` -- a miss, not a dead end: follow the miss protocol below (call the server's next step, show its nearest candidates). Do not ask the broker for a city, state, or cleaner address on the first miss.
- `out_of_region` -- state the coverage boundary first (NC only), per the miss protocol; do not retry the same input.
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

<!-- BEGIN MISS-PROTOCOL BLOCK (canonical: shared/miss-protocol.md -- edit there, then scripts/sync-miss-protocol.sh) -->
## A miss is never final -- the miss protocol

A zero-result or not-found from a lee-raleigh lookup tool is a step in a ladder, not an
answer. The server has already tried the deterministic hops over our own data; what it hands
back tells you the next hop. Follow these rules on every empty or failed lookup.

1. **A miss is never final.** Never end your turn on a bare "not found" / "no results" /
   "could not locate". Read the response's `miss` object (a MissReport) before you reply.
2. **Call `next[]` in order, at most 3 hops.** Each entry is a concrete tool call
   `{tool, args, why}` the server has already vetted. Make the first one; if it misses, make
   the next. Never invent a retry the server did not offer (no guessed county, no
   re-spelling, no sibling tool the response did not name), and stop after three hops.
3. **Show `nearest[]` to the broker as choices.** When the server lists near candidates,
   present them as a short numbered list with the detail that tells them apart (`why_close`,
   county, id), and re-run with the broker's pick (by `id` when one is given). Do not pick
   for them unless the response already did.
4. **Ask the broker a question only when `ask_broker` is set.** It is the one branch that
   ends in a question, and it carries the exact question to ask. If `ask_broker` is null
   and `next[]` or `nearest[]` is non-empty, use them; if all three are empty, go to rule 6.
5. **Coverage wins over any retry.** If `coverage.in_coverage` is false, say so first
   (name the covered counties from `coverage.covered`), then stop retrying that input:
   more spelling will not put a county into the database.
6. **When the ladder is truly exhausted, say what was tried.** Only after `next[]` is empty,
   `nearest[]` is empty and `ask_broker` is answered (or null) may you tell the broker nothing
   was found -- and then say it in terms of `tried[]` ("I searched Wake exactly and fuzzy,
   then all covered counties, then geocoded it; none matched"), so they know what to fix.
7. **Pass the county on the first call when you can.** Before any parcel, owner, or address
   tool call, derive the NC county from the city or ZIP in the broker's request (your own
   knowledge, no lookup) and pass it as `county`. A county-scoped first call skips a retry
   round-trip and is the single biggest rescue on long or ambiguous street names.
8. **Legacy responses.** If a response carries no `miss` object but its text contains an
   instruction addressed to the assistant (a county retry, a candidate list, "look it up by
   PIN"), treat that instruction as `next[]`: it is the older form of the same ladder and
   the same three-hop cap applies. If a legacy response is a bare sentence with no
   instruction at all (the geocode family's "couldn't locate ..." today), you may make ONE
   hop of your own: re-call the same tool with the county from rule 7 if you did not pass
   it, otherwise with the street name and city only. If that also misses, ask the broker
   one question (the nearest numbered address, or the county). This is the only retry you
   may invent, and only for a legacy response.

Field glossary: `tried` = what the server already attempted (strategy, input, result);
`nearest` = close matches from our own data; `next` = the ordered calls to make; `coverage`
= whether the input falls inside the counties we hold; `ask_broker` = the one question to
ask, or null.
<!-- END MISS-PROTOCOL BLOCK -->
