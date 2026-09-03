---
name: demographic-summary
description: Pull a demographic summary (one Lee infographic page per ring) for any NC address -- 1/3/5-mile rings by default, or the broker's own radii (e.g. 3/5/7). Returns population, households, income, education, workforce mix, daytime population, and growth (a GI blended annual rate plus an MOE-guarded raw rate) with per-metric methodology metadata, plus a Lee-branded PDF link (1-hour signed URL). Wraps the lee-raleigh-mcp pull_demographic_summary tool.
---

# Intellisite Demographic Infographic (Lee & Associates)

Pull a demographic profile for concentric rings around any NC address -- 1, 3, and 5 miles by default, or the ring sizes the broker names (up to three, e.g. 3/5/7 to match an OM).

## When to use

Anything that asks for a "demographic profile" or an "infographic" around a property address. The phrasing is open — what matters is the intent.

Triggers:

- `/demographic-summary <address>` (slash command)
- "Pull infographic for 100 Walnut St, Cary"
- "Demographic profile of 200 Main St, Raleigh"
- "Site report for [address]"
- "What does the demographic look like around [address]"

**Don't apply this skill to:**

- Sale or lease comp requests (those are `internal-comps` / `external-comps`).
- Multi-address batch requests (v1 supports one address at a time).

## Process

1. Parse the broker's request to extract the address as a single free-text string. Don't try to canonicalize or pre-validate — the Census Geocoder does that server-side.
2. Call the MCP tool `pull_demographic_summary` with `{address: "<the extracted address>"}`. The tool takes ~10-15 seconds. **Ring sizes:** omit `radii` unless the broker names ring sizes. If they do ("3, 5 and 7 miles", "a 2-mile ring", "match the OM's 3/5/7"), pass `radii` as ascending miles, up to 3 values, each 0.5-10 (e.g. `{address, radii: [3, 5, 7]}`). Never invent radii the broker did not ask for. If the tool returns `invalid_radii`, relay its message and ask for radii that fit (up to three, 0.5-10 miles, ascending).
3. The response is structured JSON with one top-level key per ring, named `<miles>mi` -- iterate `radii_miles` (e.g. `[3, 5, 7]` -> `3mi`, `5mi`, `7mi`; default `[1, 3, 5]` -> `1mi`, `3mi`, `5mi`) -- plus metadata. Render it inline conversationally — Claude already handles ring-keyed objects well; no custom formatting helper is needed.
4. If `pdf_url` is a non-null string (the expected v1.1 path), surface it as a "📄 Open PDF" link with a 1-hour expiry note: *"Link expires in ~1 hour — download or share it now."* If `pdf_url` is `null` (transient render failure — the JSON response is non-fatal on PDF errors), deliver the structured data as usual and add a short note: *"The PDF render hit a snag this run; the data is fully present. Re-run the command to regenerate the PDF."*

## Error handling

The tool returns structured errors:

- `geocode_failed` / `not_found` -- a miss, not a dead end: follow the miss protocol below (call the server's next step, show its nearest candidates). Do not ask the broker for a city, state, or cleaner address on the first miss.
- `out_of_region` -- state the coverage boundary first (NC only), per the miss protocol; do not retry the same input.
- `upstream_failed` — Census or TIGER API is having a moment. Apologize and ask the broker to retry in a few minutes.
- `internal` — anything else. Apologize, surface a short message, and ask David / Bonner to check.

## What's in the response

`radii_miles` lists the ring radii; ring blocks are keyed `<miles>mi`. Per-ring metrics, each carrying inline `method` / `source` / `vintage`:

- **Counts**: population, households, housing units, mean & median household income, median home value, median age
- **Mix**: bachelor's or higher %, workforce office/services/trades %
- **Baseline**: Decennial 2020 + recent ACS 5yr pop + housing, with the MOE-guarded annualized raw rate between them, and the GI blended annual growth rate (`gi_blended_growth_annual_pct`)
- **LEHD-derived**: employee count, resident workers, daytime population (`total_pop - resident_workers + workplace_workers`), daytime ratio

`methodology_version` is the Bonner package version this Worker port is calibrated against. `methodology_doc` points at the design spec.

## CRITICAL: how to present growth

Each ring carries two growth fields:

- **`gi_blended_growth_annual_pct`** -- the headline. GI's blended annual rate (0.55 county + 0.25 state + 0.10 ring + 0.10 national). Read the block's `source`: the county slice runs Decennial 2020 -> ACS 1-year where the Census publishes it (counties of 65k+), and Decennial 2020 -> ACS 5-year for the smaller counties (the `source` says which); when the ring's own change is inside the survey's margin of error the ring slice carries the state rate instead and the `source` says "state rate substituted". This is the rate the projection engine uses and the one the PDF prints. Present it as "Growth (GI blended): +1.8%/yr". If the broker asks where it comes from, quote the `source` string as written -- do not restate the formula from memory.
- **If `gi_blended_growth_annual_pct.value` is `null`** (it should not be for any NC address; if it is, something upstream is down), say "GI blended growth rate unavailable: <its `notes`>" and nothing more. Never describe a missing blended rate as an MOE suppression, and never send the broker to "county-level Census estimates" for a growth figure -- that is what the blend already carries.
- **`pop_growth_annual_pct` / `housing_growth_annual_pct`** -- the ring's own raw Decennial 2020 -> ACS 5-year rate, **MOE-guarded**: when the endpoint change does not clear the ACS 90% margin of error (`endpoint_delta <= moe_90pct`) the `value` is `null` and `notes` says why. A null here is a finding, not a failure: "the ring's own change is inside the survey's margin of error, so we don't print it." Do NOT substitute the blended rate into the raw field or vice versa; if the broker asks for the ring's own rate and it is suppressed, say so and point at the blended rate.

Do not editorialize a surprising blended rate; quote its `source`. The raw rate, where it prints, is backward-looking (a 2019-2023 rolling ACS average against the 2020 count) and lags fast-moving submarkets -- say that in one line if it is negative in an obvious-growth market.

## CRITICAL: per-metric source/vintage disclosure

Every metric in the response has `source` (e.g. "ACS 5yr B01003_001E") and `vintage` (e.g. 2022). If the broker asks "where is this from" or "how recent is this", quote the inline `source` + `vintage` for the specific metric — don't paraphrase. The methodology is the contract; surface it accurately.

## CRITICAL: daytime population is workforce-only

`daytime_population = total_pop - resident_workers + workplace_workers`. This counts workers but **does not** impute shoppers, students, hospital patients, or other non-worker daytime presence. Esri BAO's daytime number is typically 10-15% higher for retail/commercial centers because it adds those non-worker flows. If a broker compares our number to a BAO printout for a retail site, expect a gap and explain why — don't assume our number is wrong.

## What's deliberately NOT in v1

- Tapestry segmentation, Wealth Index, Total Sales, Largest Businesses in Area — Esri-only data, not portable.
- Multi-state coverage — NC only for v1.
- Charts (age distribution, income, race breakdowns) — v1.1 PDF is tile-grid only; charts arrive in v1.2 once the JSON shape widens to carry the breakdowns the charts plot.

## Files

- `SKILL.md` — this file. The skill is a thin orchestrator over `pull_demographic_summary`; no Python helpers.

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
   ends in a question, and it carries the exact question to ask. If `ask_broker` is null,
   you have hops or candidates left -- use them.
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
   the same three-hop cap applies.

Field glossary: `tried` = what the server already attempted (strategy, input, result);
`nearest` = close matches from our own data; `next` = the ordered calls to make; `coverage`
= whether the input falls inside the counties we hold; `ask_broker` = the one question to
ask, or null.
<!-- END MISS-PROTOCOL BLOCK -->
