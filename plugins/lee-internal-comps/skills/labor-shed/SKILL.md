---
name: labor-shed
description: Show the labor force around a commercial site sliced by industry, for any NC address. Returns the resident labor pool a tenant can recruit (LEHD LODES residence data) and the existing employer mix already in the area (LODES workplace data) for 1/3/5-mile rings, or for drive-time bands ("how many workers live within a 30-minute drive") when the broker asks in minutes, with the industrial-family workforce (manufacturing, wholesale, transportation & warehousing, construction) called out. Wraps the lee-raleigh-mcp pull_labor_shed tool.
---

# Labor Shed (Lee & Associates)

Show the workforce around a site, sliced by industry, for 1/3/5-mile rings or drive-time bands around any NC address. Answers "who can a tenant recruit here" (resident labor pool) and "who is already here" (existing employer mix).

## When to use

Anything that asks about the labor force, workforce, or labor pool around a site, especially for an industrial / flex BOV or OM.

Triggers:

- `/labor-shed <address>` (slash command)
- "Labor shed for 7144 Deep River Rd, Sanford"
- "What's the labor pool around [address]?"
- "Is there an industrial workforce near [address]?"
- "Who can a tenant recruit at [address]?"
- "Workforce by industry for [address]"
- "How many workers live within a 30-minute drive of [address]?"
- "Labor shed by drive time for [address], 15/30/45 minutes"

**Don't apply this skill to:**

- General population / income handouts (use `demographic-summary`).
- Multi-page OM demographic reports (use `demographic-detail`).
- Business Key Facts infographics (use `business-key-facts`).
- Sale or lease comp requests (those are `internal-comps` / `external-comps`).
- Counts of *businesses* / *establishments* by industry. This tool reports the
  *workforce* (jobs and where workers live), not establishment counts.
- Multi-address batch requests (v1 supports one address at a time).
- Custom ring sizes (rings are fixed at 1/3/5 mi; for other reaches use drive-time bands).
- Non-NC addresses (v1 supports NC only).

## Process

1. Parse the broker's request to extract the address as a single free-text string. Don't canonicalize or pre-validate; the Census Geocoder does that server-side.
2. Call the MCP tool `pull_labor_shed` with `{address: "<the extracted address>"}`. If the broker frames reach in **minutes** ("within a 30-minute drive", "commute shed", "drive-time labor shed"), pass `geometry: "drive_time"` and `minutes` (1–60, up to 5 bands; omit for the default 15/30/45). Drive-time pulls take ~5–15s the first time (the routing engine draws the bands; repeats are cached).
3. The response is structured JSON keyed by band: `1mi`/`3mi`/`5mi` for rings, or `15min`/`30min`/`45min` (your minutes) for drive time. Each band carries a resident labor pool (`rac`) and existing employer mix (`wac`), sliced by NAICS sector, plus an industrial subtotal + share. `request.bands` lists the keys in order. Render inline conversationally, leading with the headline numbers of the **outermost** band (5-mile, or your widest drive-time band): labor pool, industrial-eligible workforce + share, existing jobs, existing industrial jobs. For drive time, say "within a 30-minute drive", never "within 30 miles", and note times are free-flow (no rush hour); `meta.drive_time` carries the routing source if asked.
4. If `pdf_url` is a non-null string, surface it as a "📄 Open PDF" link with a 1-hour expiry note: *"Link expires in ~1 hour, download or share it now."* If `pdf_url` is `null`, deliver the structured data and suggest the broker re-run.

## How to present it

Lead with the broker question, not the table:

> Within 5 miles of [site] (or: within a 30-minute drive of [site]), the resident labor pool is **X** workers, **Y (Z%)** of them already in industrial-family jobs (manufacturing, wholesale, transportation & warehousing, construction). There are **W** jobs already located in that radius, **V%** of them industrial, so the site sits inside an existing industrial cluster rather than a green-field labor market.

Then offer the per-ring or per-sector breakdown if they want it.

"Industrial" here means construction (NAICS 23), manufacturing (31-33), wholesale trade (42), and transportation & warehousing (48-49). Say so if a broker asks what counts.

## Error handling

Same envelope as sibling skills:

- `geocode_failed` / `not_found` -- a miss, not a dead end: follow the miss protocol below (call the server's next step, show its nearest candidates). Do not ask the broker for a city, state, or cleaner address on the first miss.
- `out_of_region` -- state the coverage boundary first (NC only), per the miss protocol; do not retry the same input.
- `upstream_failed` — Census or D1 lookup hiccup. Apologize and ask the broker to retry.
- `quota_exceeded` (drive time only) — the routing service hit its daily budget. Previously pulled addresses still work; offer the 1/3/5-mile version or try a new address tomorrow.
- `rate_limited` — today's per-broker cap (100/day); resets at midnight UTC.
- `internal` — anything else. Apologize, surface a short message, ask David / Bonner to check.

## What's deliberately NOT in v1

- Drive-time bands for the *demographic* tools (population within the 30-minute band) — the labor shed has them now; demographics still ring-based.
- Establishment counts by NAICS (the BAO "businesses" stat) — needs County Business Patterns / QCEW, separate tracked work.
- Multi-state coverage — NC only for v1.
- Multi-address batch.

## Files

- `SKILL.md` — this file. The skill is a thin orchestrator over `pull_labor_shed`; no Python helpers, no local assets.
- Numeric parity reference: the `labor_shed` Python engine at `40_delivery/labor-shed/`. Worker port spec: `40_delivery/labor-shed/WORKER_PORT_SPEC.md`.

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
