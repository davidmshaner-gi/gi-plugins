---
name: lee-tenant-search
description: Answers "what tenants are in the market?" — searches the shared Lee Raleigh tenant-requirements pool for active tenant requirements matching an asset type, size, or location, and returns each match with the originating broker's contact so you can pair a listing. Size can be a single target SF (matched as a tolerance band, e.g. a 10,000 SF space pulls ~7,000-14,000 SF requirements) or an explicit min/max window. Location can be a city OR a county name that rolls up to its cities ("Wake County" matches Raleigh, Cary, Apex, Morrisville, Wake Forest, Garner, Fuquay-Varina...), and a tenant listed in several cities matches a search for any one of them. Use when a broker asks who is looking for space ("what tenants are in the market for 5-10k SF industrial in Garner?", "anyone seeking retail in Cary?", "tenants in Wake County?", "who's looking for land near Apex?"). Read-only; queries pull_tenants_in_market on lee-raleigh-mcp. Requirements are sourced from Triangle Pairlist broker blasts, ingested continuously since June 2026.
---

# /lee-tenant-search

Search the shared tenant-requirements pool and present matches a broker can act on.
The pool holds active space requirements (a broker representing a tenant SEEKING
space). Listings and investment/$-budget ISOs never appear — the store filters them
out server-side.

## Step 1 — Map the ask to filters
From the broker's question, set only the filters they actually stated:
- `asset_type`: one canonical word — industrial, retail, office, medical, flex, land, restaurant. ("warehouse" → industrial; "shop space" → retail.)
- **Size — pick ONE form:**
  - `target_sf`: a single SF figure when the broker has a specific space in mind ("a 10,000 SF building" → `target_sf: 10000`). The server matches requirements within a ±30% tolerance band (so ~7,000–13,000 SF), by range overlap. This is the usual case.
  - `min_sf` / `max_sf`: an explicit window when the broker states a range ("5–10k SF" → `min_sf: 5000, max_sf: 10000`). Both bounds are now real server-side filters.
- `location`: a place string. Pass a **city** verbatim ("Garner", "Cary", "Apex"), OR a **county** name ("Wake County" / "Wake") — the server rolls a county up to its cities, so "Wake County" finds tenants listed under Raleigh, Cary, Apex, Morrisville, Wake Forest, Garner, Fuquay-Varina, etc. A tenant listed in several cities matches a search for any one. (You no longer need to avoid town names — the server handles the rollup.)
- `since`: ISO date (YYYY-MM-DD), only when the broker asks for recency ("this month" → the first of the month).

Leave everything they didn't say unset. A bare "who's in the market?" calls with no
filters.

## Step 2 — Call the tool once
Call `pull_tenants_in_market` with those filters. Do not page or re-call with
variations unless Step 3 ends in zero matches.

## Step 3 — Present matches (the pairing view)
Matching is LENIENT by design — the tool's `matching_note` explains it. Size and
location are now matched server-side (SF by range overlap against the band; county
roll-up applied), so your job is a light sanity check, not the primary filter:
- **Size:** the server already filtered to the tolerance band. Just glance at the
  verbatim `requirement_sf` and flag a row only if it is an obvious mismatch. Rows
  with a null `requirement_sf` are included — flag them "size unspecified".
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
