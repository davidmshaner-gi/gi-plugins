---
name: lee-tenant-search
description: Answers "what tenants are in the market?" — searches the shared Lee Raleigh tenant-requirements pool for active tenant requirements matching an asset type, size range, or location, and returns each match with the originating broker's contact so you can pair a listing. Use when a broker asks who is looking for space ("what tenants are in the market for 5-10k SF industrial in Garner?", "anyone seeking retail in Cary?", "any tenant requirements for medical office?", "who's looking for land near Apex?"). Read-only; queries pull_tenants_in_market on lee-raleigh-mcp. Requirements are sourced from Triangle Pairlist broker blasts, ingested continuously since June 2026.
---

# /lee-tenant-search

Search the shared tenant-requirements pool and present matches a broker can act on.
The pool holds active space requirements (a broker representing a tenant SEEKING
space). Listings and investment/$-budget ISOs never appear — the store filters them
out server-side.

## Step 1 — Map the ask to filters
From the broker's question, set only the filters they actually stated:
- `asset_type`: one canonical word — industrial, retail, office, medical, flex, land, restaurant. ("warehouse" → industrial; "shop space" → retail.)
- `min_sf` / `max_sf`: their size window as plain integers (e.g. "5-10k SF" → 5000 / 10000).
- `location`: one place string verbatim ("Garner", "Cary", "Apex"). Don't expand to nearby towns — matching is server-side substring; the pool stores free-text locations.
- `since`: ISO date (YYYY-MM-DD), only when the broker asks for recency ("this month" → the first of the month).

Leave everything they didn't say unset. A bare "who's in the market?" calls with no
filters.

## Step 2 — Call the tool once
Call `pull_tenants_in_market` with those filters. Do not page or re-call with
variations unless Step 3 ends in zero matches.

## Step 3 — Present matches (the pairing view)
Matching is LENIENT by design — the tool's `matching_note` explains it. You do the
final trim:
- **Size:** `min_sf` is NOT filtered server-side (the store records each requirement's
  minimum SF only). Read `requirement_sf` verbatim ("5,000 - 7,000 SF") and drop rows
  whose stated range clearly cannot reach the broker's window. Keep rows with a null
  `requirement_sf` and flag them "size unspecified".
- **Location:** rows with a null `preferred_location` are included — flag them
  "location unspecified" rather than dropping.

Present a short list, newest first — for each match: **tenant** (as described),
**size** (verbatim `requirement_sf`), **location**, **asset type**, **tenure**
(lease/purchase/both), **received** (date), and the action line: **originating
broker contact** (name, email, phone) — that's who to call to pair a listing.
Include `additional_details` when it carries real requirements (parking, ceiling
height, timeline).

Zero matches after trimming: say so plainly, then offer ONE broadening step (drop
the location filter, or widen the SF window) and re-call once if the broker wants
it. Never invent or extrapolate a requirement.

## Notes
- Shared pool: every Lee Raleigh broker sees the same requirements; provenance is
  Triangle Pairlist (ingested continuously since June 2026 by the
  lee-tenants-in-market scheduled skill).
- Results are capped at the 50 newest rows server-side. If a broad ask hits the
  cap, say the view is the 50 most recent and suggest a filter.
