---
name: comp-map
description: Put your comps on a Lee-branded Google map for any NC listing. Deal mode — give it a subject address and it maps the comps around it (numbered pins, distance rings, and a matching numbered comp table) for a flyer / OM / BOV. Database mode — maps the whole internal comp set, filterable, or a broker's own deal history ("map every deal my team closed in this market"). Returns a shareable interactive map link (Lee-branded Google map, ~30-day link a broker can forward to a client), a print-ready static PNG, and a numbered csm-* comp-table fragment. Answers "map the comps around [address]", "show the comps near my listing", "map of all our comps", "map my deal history for the pitch". Wraps the lee-raleigh-mcp pull_comp_map tool.
---

# Comp Map — Competitive-Set Map (Lee & Associates)

Put comps on a Lee-branded Google map. Two modes:

- **Deal mode (a subject address):** the comps *around* a listing — numbered pins ordered by distance, optional radius rings, and a paired **comp table whose row numbers match the map pins**. This is the competitive-set map for a flyer / OM / BOV.
- **Database mode (no subject):** the whole internal comp set on one clustered, filterable map — or, with a broker filter, **a broker's deal history** ("map every deal my team closed in the Triangle for the pitch").

The deliverables: a **shareable interactive map link** (a real Google map the broker opens and can forward to a client — the link lives ~30 days, no login), a **print-ready static PNG** for dropping into a flyer, and the **numbered comp-table fragment** (`csm-*`).

## When to use

A broker wants to *see* comps on a map, or needs a competitive-set map / deal-history map for a marketing piece.

Triggers:

- `/comp-map <address>` (slash command)
- "Map the comps around 3020 Hillsborough St, Raleigh"
- "Show me the comps near my listing"
- "Put these comps on a map"
- "Map of all our industrial comps"
- "Map every deal Hunter Stewart closed in the last two years" (deal-history / rep map)
- "I need a competitive-set map for this flyer / OM"

**Don't apply this skill to:**

- Pulling the comps themselves as a table / Excel (use `internal-comps`, `external-comps`, or `internal-and-external-comps`). This skill *visualises* comps; reach for it after, or alongside, a comps pull.
- Nearby businesses / area amenities (use `nearby-businesses`).
- Demographics, labor shed, traffic counts, owner-of-record (their own skills).
- A fully-composed flyer (this returns the map assets; a designer / `lee-flyer-brief` composes the whole piece).
- Non-NC addresses (v1 is validated on NC).

## Process

1. Decide the **mode** from the request:
   - A subject property named → **deal mode**: pass `subject` (a single free-text address string; don't pre-validate — the geocoder resolves it server-side). Add `radius_mi` if the broker gave one (else the tool defaults). Add `rings_mi` if they want distance rings — **always scale the rings to the radius**: present/pass 2–3 round-number bands that end at `radius_mi` and **never exceed it**, so the outermost ring reads as the search boundary. Scale them: `radius_mi` 5 → `[1,3,5]`; 3 → `[1,2,3]`; 2 → `[0.5,1,2]`; 1 → `[0.25,0.5,1]`; for an unusual radius pick a few round bands up to it. Never offer a ring larger than the chosen radius (a 5-mile ring on a 1-mile radius map is meaningless — it sits where there are no comps).
   - "All our comps" / "map of the database" / a broker's deal history → **database mode**: omit `subject` (or set `mode:"database"`). For a deal-history / rep map, pass `brokers: ["<full name>", ...]` (any-involvement match across lead + the four rep-agent roles).
2. Optional filters either mode: `types` (`["sale"]`, `["lease"]`, or both), `since` (`YYYY-MM-DD`), `ttl_days` (override the ~30-day share link).
3. Call the MCP tool **`pull_comp_map`** with that input.
4. The response is structured JSON:
   - `map_url` — a **signed ~30-day link** to the interactive Lee-branded Google map (the headline deliverable; shareable with a client).
   - `static_png_url` — a signed ~30-day link to a **print-ready static PNG** of the same map (for dropping into a flyer / OM).
   - `table_html` — the **`csm-*` comp-table fragment** (numbered to match the map pins) for embedding in a flyer / OM / BOV.
   - `report` — `placed_comps`, `unplaced` (comps that couldn't be geocoded — named, never silently dropped), and `capped` (`{shown, matched}`) when the result was trimmed (see below).

## The 10% data-exposure cap (always surface it when it fires)

A single map shows at most ~10% of the total comp database (a governance guardrail so a shareable link never carries a large slice of the proprietary set). When `report.capped` is present, the map shows the nearest/first `shown` of `matched` matching comps — **tell the broker plainly and suggest narrowing**: *"Showing the nearest 95 of 240 matching comps — narrow by type, county, or date to see a different set."* Never imply it's the full set when it was capped.

## How to present it

Lead with the map link, then the supporting assets:

> Here's the competitive-set map for **[subject / "your deal history"]** — **[placed_comps]** comps mapped: **🗺️ [map_url]** (link works ~30 days, shareable with a client). Print-ready image: **[static_png_url]**. The numbered comp table (rows match the pins) is ready to drop into the flyer.

Then, if useful: the cap notice (if `report.capped`), and any `unplaced` comps by name ("N comps couldn't be placed: …") so the broker knows what's not on the map.

The `table_html` fragment is composable into a flyer / OM / BOV alongside the map image (same `lee-listing-flyer` fragment system as the other components).

## Error handling

Same envelope as sibling skills:

- `geocode_failed` / `not_found` -- a miss, not a dead end: follow the miss protocol below (call the server's next step, show its nearest candidates). Do not ask the broker for a city, state, or cleaner address on the first miss.
- `out_of_region` -- state the coverage boundary first (NC only), per the miss protocol; do not retry the same input.
- `rate_limited` (HTTP 429) — the broker hit the daily cap. Relay it plainly.
- `internal` / anything else — apologize, surface a short message, ask David / Bonner to check.

If `placed_comps` is 0, no comps matched the filters within range — tell the broker plainly and suggest a wider radius, fewer filters, or a different market.

## What's deliberately NOT in v1

- **Drive-time bands** (isochrones) — the map ships with straight-line distance rings only; drive-time bands are a planned fast-follow (tracked in gi-plugins#77).
- **External comps as a distinct layer** — v1 maps the internal Dealius set; external comps as a visually distinct third layer is follow-on scope.
- Database-mode free-text search / date-range UI beyond the `since` / `types` / `brokers` filters.
- Non-NC coverage.

## Files

- `SKILL.md` — this file. A thin orchestrator over `pull_comp_map`; no Python helpers, no local assets.
- Parity reference: the `map-builder` engine at `40_delivery/map-builder/`. The Worker tool ports its compose/render (deal + database modes, distance ordering, stacking, rings, the comp-table fragment); geocodes are pre-staged in D1 so renders never geocode comps live.

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
