# Canonical miss protocol (gi-plugins#164; program lee#530; folds gi-plugins#139)

This file is the single source of truth for the miss-protocol section embedded in every
lee-internal-comps SKILL.md that calls a lee-raleigh lookup tool. **Edit the block below
(between the BEGIN/END markers), then run `scripts/sync-miss-protocol.sh` to propagate it**
-- never hand-edit the copy inside an individual SKILL.md.
`scripts/test/miss-protocol-guidance.test.sh` fails the build on any drift and on any
surviving "ask the broker for a city + state hint" prose.

The same text ships in the Worker as `MISS_PROTOCOL_INSTRUCTIONS`
(`sow_1_analyst_pilot/mcp-server/src/lib/miss.ts`, lee#531) and, once wired, in the
McpServer `instructions` field, so the protocol applies even when a broker calls the
connector without a skill. The lee repo pins byte parity against a checked-in copy of this
block (`test/fixtures/miss-protocol.block.md`) and `npm run check:parity` compares it to
this file on `main`. Keep the block ASCII-only: it lives in a TypeScript string literal.

Why this exists (spec: GI repo `95_agent_ops/superpowers/specs/2026-08-26-miss-contract-design.md`):
between 2026-05 and 2026-08, 35 cards across both GI repos were the same failure -- a broker
asked, a tool returned zero or `not_found`, and the data was in our system the whole time.
Fifteen of the twenty fixes were point patches. The skill prose was where the punt lived
("ask for a city + state hint"). David ruled on 2026-08-26: the server does the deterministic
hops over our own data and hands the client a structured `miss`; the client does the
world-knowledge hops from `next[]`, at most three, and only asks the broker when the server
says the ladder is exhausted.

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
