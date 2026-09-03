---
name: drive-time-isochrones
description: Map how far you can get from a property in 5, 10, and 15 minutes by car (or on foot / by bike) for any NC address. Use when a broker asks "what's within a 10-minute drive", wants a drive-time map for a flyer, OM, or BOV, wants trade-area reach instead of crude mile rings, or asks for drive-time isochrones. Returns per-band reach areas and a Lee-branded map card PDF (isochrone GeoJSON on request for downstream programs). Not for point-to-point "how long to drive from A to B" questions. Wraps the lee-raleigh-mcp pull_drive_time_isochrones tool.
---

# Drive-Time Isochrones (Lee & Associates)

Pull drive-time reach polygons (isochrones) for any NC address — the "where can you
get to in N minutes" map that paid GIS platforms charge a premium for.

## When to use

Anything that asks how far you can travel from a site in a given time, or wants that
reach drawn on a map.

Triggers:

- `/drive-time-isochrones <address>` (slash command)
- "What's within a 10-minute drive of 100 Walnut St, Cary?"
- "Drive-time map for [address]"
- "Trade area / drive-time rings for [listing]"
- "How far can you get in 15 minutes from [site]?"

**Don't apply this skill to:**

- Fixed mile-ring demographics (use `demographic-summary` / `business-key-facts`).
- "How long does it take to drive from A to B" / "drive times to RDU, Duke, ..." —
  point-to-point questions. This tool draws reach polygons from one site; it does not
  route between two addresses. Say so and offer the drive-time map instead.
- Rush-hour or time-of-day commute analysis — v1 returns free-flow times only.
- Non-NC addresses (v1 supports NC only).

## Process

1. Extract the address as a single free-text string. Don't pre-validate — the
   Census Geocoder (with Nominatim fallback) resolves it server-side.
2. Defaults are 5/10/15 minutes driving. Honor explicit asks: "20-minute drive" →
   `minutes: [20]` (1–60, up to 5 bands); "walking distance" → `profile: "walking"`;
   "bike" → `profile: "biking"`.
3. `anchors` is a programmatic input for the flyer engine (the time-to-anchors table
   on a flyer page reads `anchor_reach`). Do not offer or use it to answer "how long
   to drive from the site to RDU" in chat — that is a point-to-point question this
   tool does not answer (see "Don't apply this skill to"). If a broker asks it, say
   so plainly and offer the drive-time map instead.
4. Call the MCP tool `pull_drive_time_isochrones` with
   `{ address, minutes?, profile? }`. Typical latency ~5–15s (first pull of
   an address calls the routing engine; repeats are cached and faster). **Never pass
   `detail: "full"` in a chat session** — the default summary (~2K chars) is the shape
   you can read; `full` adds ~365K chars of polygon geometry that overflows the tool
   result, and then you cannot read the answer at all. `full` exists only for programs
   that consume the JSON directly (the flyer engine).
5. Read the JSON directly from the tool result — it is small enough to read whole.
   Each band's `area_sq_miles` is the headline — lead with the widest band ("~99 sq mi
   is within a 15-minute drive of the site"). One pull answers the ask: do not re-run
   with narrower `minutes` windows, and do not switch to a public routing or maps
   service to sharpen a number — those are a different engine and not what the broker
   asked for.
6. If `pdf_url` is a non-null string, surface it as a "📄 Open PDF" link with a
   1-hour expiry note: *"Link expires in ~1 hour — download or share it now."* If
   `pdf_url` is `null` (transient render failure — the JSON is non-fatal on PDF
   errors), deliver the numbers and suggest the broker re-run.
7. `meta.free_flow_only` is always true in v1: travel times assume posted speeds with
   no congestion. If the broker asks about rush hour, say so plainly — peak-hour
   reach is typically 15–30% smaller in urban areas.

## Error handling

Same envelope as sibling skills — relay the `message` verbatim, it is written for
brokers:

- `geocode_failed` / `not_found` -- a miss, not a dead end: follow the miss protocol below (call the server's next step, show its nearest candidates). Do not ask the broker for a city, state, or cleaner address on the first miss.
- `out_of_region` -- state the coverage boundary first (NC only), per the miss protocol; do not retry the same input.
- `quota_exceeded` — the routing service hit its daily budget. Previously pulled
  addresses still work; new addresses are available again tomorrow.
- `rate_limited` — you've hit today's per-broker pull cap (100/day). It resets at
  midnight UTC; cached addresses still work in the meantime.
- `upstream_failed` — routing service hiccup. Cached addresses still work; ask the
  broker to retry a new address in a few minutes.
- `internal` — anything else. Apologize, surface a short message, and ask David /
  Bonner to check.

## What's in the response

- `bands[]` — per drive-time band: `minutes`, `area_sq_miles` (reach area),
  Lee-maroon `fill_color`/`stroke_color` (light = close, dark = far).
- `meta.detail` — `"summary"` (the default; what you get in chat) or `"full"`.
- `anchor_reach[]` (only when a program passed `anchors`) — per named destination, its
  smallest containing band ("<= 25 min") or "beyond N min". Flyer-engine input; not a
  chat feature.
- `geojson` + `fragment_html` — **only with `detail: "full"`** (programmatic consumers):
  the isochrone FeatureCollection (one Feature per band) and a compact polygons-only
  SVG card for inline composition. Absent from the default summary.
- `pdf_url` — Lee-branded flyer-component card (map over OSM basemap + reach table),
  fit-to-content at the standard 6.5-in component width.
- `meta` — engine (OpenRouteService), road-network vintage, `free_flow_only: true`,
  attribution.

## What's deliberately NOT in v1

- Time-of-day / `depart_at` isochrones (rush-hour shrinkage) — the v2 Valhalla path,
  roadmap #57.
- Point-to-point drive times and distance matrices.
- Drive-time-band demographics (population within the 10-min polygon) — lands when
  the demographic tools adopt this isochrone primitive.
- Multi-state coverage — NC only.

## Files

- `SKILL.md` — this file. The skill is a thin orchestrator over
  `pull_drive_time_isochrones`; no Python helpers and no local assets.

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
