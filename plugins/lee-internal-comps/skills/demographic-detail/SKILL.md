---
name: demographic-detail
description: Pull a multi-page Lee-branded Demographic and Income Profile for any NC address (~18 pages, content-driven via paged.js). Returns 1/3/5-mile rings with population/households/income/age/race breakdowns, four Esri-analog indices (Diversity, Median Net Worth, Wealth, Housing Affordability), 2020/2025/2030 projections via gi_permit_adjusted (Census BPS-aware) with gi_blended fallback, trend comparisons against State + US (Population, Households, Family HHs, Owner HUs), inline SVG charts per ring, plus a Lee-branded PDF (1-hour signed URL). Wraps the lee-raleigh-mcp pull_demographic_detail tool.
---

# Demographic Detail (Lee & Associates)

Pull a multi-page demographic and income profile for 1, 3, and 5-mile rings around any NC address. This is the OM-quality companion to the single-page Demographic Summary skill. Use this for investment package attachments; use the Summary for quick broker handouts or email blasts.

## When to use

Anything that asks for a "demographic report," "demographic and income profile," or a deep demographic deliverable around a property address.

Triggers:

- `/demographic-detail <address>` (slash command)
- "Pull a demographic report for 100 Walnut St, Cary"
- "I need the deep demographic for the OM at [address]"
- "Demographic and income profile of [address]"
- "Full demographic report for this site"

**Don't apply this skill to:**

- Quick broker handouts or email-blast deliverables -- use the `demographic-summary` skill instead.
- Sale or lease comp requests (those are `internal-comps` / `external-comps`).
- Multi-address batch requests (v1 supports one address at a time).
- Custom ring sizes (v1 is hardcoded to 1/3/5 mi).
- Non-NC addresses (v1 supports NC only; v2 expands the coverage).

## Process

1. Parse the broker's request to extract the address as a single free-text string. Don't try to canonicalize or pre-validate -- the Census Geocoder does that server-side.
2. Call the MCP tool `pull_demographic_detail` with `{address: "<the extracted address>"}`. The tool takes ~30-45 seconds (the wider data pull plus paged.js pagination + Census BPS lookup for the gi_permit_adjusted projection).
3. The response is structured JSON with three top-level ring keys (`1mi`, `3mi`, `5mi`), demographic atoms grouped by concept (`age_buckets`, `income_brackets`, `race_hispanic`, `indices`, `trend_rows`, projections), plus `state` metadata (FIPS code + name).
4. Render the JSON inline conversationally -- focus on the highest-signal numbers (projected 2025 population, trend rates vs state/national, the four indices). Claude already handles ring-keyed objects well; no custom formatter needed.
5. If `pdf_url` is a non-null string, surface it as a "Open Report" link with a 1-hour expiry note: *"Link expires in ~1 hour -- download or share it now."* If `pdf_url` is `null` (transient render failure), deliver the JSON and tell the broker to re-run.

## Error handling

The tool returns structured errors:

- `geocode_failed` / `not_found` -- a miss, not a dead end: follow the miss protocol below (call the server's next step, show its nearest candidates). Do not ask the broker for a city, state, or cleaner address on the first miss.
- `out_of_region` -- state the coverage boundary first (NC only), per the miss protocol; do not retry the same input.
- `upstream_error` -- transient Census API or D1 issue. Re-run.

## Relationship to the Demographic Summary skill

This skill and `demographic-summary` share the same underlying data pipeline. They differ in the output artifact:

- **This skill (`demographic-detail`)** produces a multi-page deep report (~18 pages, content-driven via paged.js) with inline SVG charts, race/income breakdowns, 2020/2025/2030 projections via gi_permit_adjusted (Census BPS-aware), and the four Esri-analog indices. Use for investment OMs, board packets, and deep due-diligence work.
- **`demographic-summary`** produces a single-page landscape tile-grid PDF with the core scalars only. Use for quick broker handouts, email blasts, or initial site scoping.

A broker can run both for the same address and pick the right artifact for the audience. No deprecation of the Summary is planned -- field feedback (target window: late May 2026) will determine whether both stick around long-term.

## Files

- `SKILL.md` -- this file. The skill is a thin orchestrator over `pull_demographic_detail`; no Python helpers.

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
