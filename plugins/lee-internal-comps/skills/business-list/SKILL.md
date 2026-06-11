---
name: business-list
description: Pull a complete census of active businesses of any type across a market ("all the boat dealerships in North Carolina", "med spas in Wake County", "Thai restaurants in Raleigh") and deliver it as a Lee & Associates-branded Excel workbook with name, address, phone, website, and ratings for every operational business. Use when a broker asks for a census, list, roster, or inventory of a business category in a state, county, metro, or city. Wraps the lee-raleigh-mcp pull_business_list + check_business_list tools (background job: statewide sweeps take 5-15 minutes).
---

# Business List (Lee & Associates)

A complete census of operational businesses for any genre × market — swept from Google Places, deduplicated, triaged for relevance, and delivered as a branded 3-sheet Excel workbook the broker can forward as-is.

## When to use

A broker wants *every* business of a type in a market — not the best few near a site.

Triggers:

- `/business-list <genre(s)> in <market>` (slash command)
- "Get me a list of all the boat dealerships and RV dealerships active in NC"
- "Every med spa in Wake County"
- "Census of Thai restaurants in Raleigh"
- "Who are all the machine shops in the Triangle?"

**Don't apply this skill to:**

- "What's *near* this address" discovery (use `nearby-businesses` — that ranks the best ~dozens around a point; this sweeps a whole market).
- Establishment *counts* by industry around a site (use `business-key-facts`).
- Tenant prospecting from the requirements database (use `tenants-in-market`).
- Comp requests (those are `internal-comps` / `external-comps`).
- Owner or mailing-list pulls (use `owner-lookup` / `owner-mailing-list`).

## Process

1. **Extract genres + market** in the broker's own words. Genres are plain phrases ("boat dealerships", "med spas") — up to 5 per ask. Market is a state, county, metro, or city ("North Carolina", "Wake County", "Wilmington NC").
2. **Confirm scope before launching a statewide sweep.** If the broker named a state (or the market is ambiguous between a city and something bigger), confirm: a statewide census takes 5–15 minutes and is a deliberate choice; a county/city census takes about a minute. If they clearly asked for the state, proceed — just set the expectation.
3. **Start the job:** call `pull_business_list` with `{genres: [...], market: "..."}`. The response carries `job_id` (the polling handle — keep it internal) and an `expectation` line — relay the expectation to the broker verbatim. If the start response carries a `message`, relay that too (it's broker-legible).
4. **Poll:** call `check_business_list` with `{job_id}` every 20–30 seconds while the job runs. Narrate progress conversationally from the response (`cells_swept`/`cells_total`, `businesses_found`) — e.g. *"Swept 14 of 18 zones, 212 businesses so far…"*. Phases run sweeping → enriching (phone/website lookups) → rendering → done.
5. **Deliver:** when `phase` is `done`, present:
   - The **📄 Excel workbook link** (`excel_url`) with its expiry (`excel_expires_at` — links last ~30 days).
   - The headline numbers from `summary`: likely matches vs. total found, by-genre counts.
   - A few sample rows from `summary.sample` so the broker can sanity-check instantly.
   - Every entry in `warnings` **verbatim** — these are coverage notes (call-budget cuts, dense zones that maxed out, failed contact lookups) the broker needs for client delivery.
6. **Re-asks are free:** the same genres + market re-attaches to the finished job and returns the same workbook instantly (no new sweep). If the link has expired, the same ask automatically re-runs fresh.

## What the workbook contains

Three sheets, Lee-branded:

1. **Likely Matches** — the working list (relevance triage `yes` + `maybe`).
2. **All Results** — everything found, with the match flag, so nothing is silently discarded; the broker can rescue edge cases.
3. **Method** — market, date, query variants, API call count, coverage notes. Provenance a broker can read aloud.

Columns: business, match flag, genre, city, state, address, phone, website, rating, review count, Google type, Maps link, place id. Phone/website are looked up for likely matches only (capped at 500 per census).

## How to present it

Lead with the answer, not the mechanics:

> Found **412 businesses**, **186 likely matches** for boat & RV dealerships across North Carolina. Workbook attached — Likely Matches is your working list; All Results keeps everything found so nothing's discarded. Two coverage notes are on the Method sheet.

If `warnings` mentions a call-budget cut, tell the broker plainly: coverage is partial and a narrower market (or a re-run) closes the gap.

## Error handling

Same envelope as sibling skills — the `message` field is broker-legible, relay it directly:

- Market didn't resolve → ask for a state, county, or "City, ST".
- `rate_limited` — daily census limit reached; resets midnight UTC.
- Job `phase: "error"` — relay `message` (e.g. Google rate-limiting: try again in a few minutes).
- "No census job found with that id" on a check → the job id was mistyped or never started; start fresh with `pull_business_list`.

## Limits (v1)

- Google Places is the source of truth — captures what businesses publish to Google; very-low-web-presence businesses won't appear.
- State markets filter cross-border bleed by address; county/city sweeps use the geocoded bounding box, so a result just over the line can appear (the broker can filter by the City/State columns).
- Up to 5 genres per census; one market per census.
