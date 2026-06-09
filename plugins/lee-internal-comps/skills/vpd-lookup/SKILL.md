---
name: vpd-lookup
description: Traffic counts (vehicles per day / AADT) for the busiest roads near any NC address. Returns the top-5 nearby road segments ranked by road class then traffic volume, each with its annual average daily traffic, the count year, and distance from the site, plus a ready-to-place flyer card. Answers "how much traffic passes this site", "VPD on the nearby roads", "traffic counts near [address]" for a retail / QSR / flex listing. Wraps the lee-raleigh-mcp pull_vpd_lookup tool.
---

# VPD Lookup (Lee & Associates)

Show the traffic counts on the busiest roads near a site, for any NC address. Answers "how much traffic passes this corner" — the top-5 nearby road segments by AADT (annual average daily traffic, a.k.a. vehicles per day / VPD), each with the count year and distance from the site, plus a ready-to-place flyer card.

## When to use

Anything that asks about traffic volume, vehicle counts, or VPD/AADT on the roads around a site — especially for a retail, QSR, convenience, or flex listing where roadside exposure matters.

Triggers:

- `/vpd-lookup <address>` (slash command)
- "Traffic counts near 8541 Concord Mills Blvd, Concord"
- "What's the VPD on the roads by [address]?"
- "How much traffic passes [address]?"
- "AADT for [address]"
- "Vehicles per day near [site]"

**Don't apply this skill to:**

- Population / income / demographics around a site (use `demographic-summary` or `demographic-detail`).
- The workforce / labor pool around a site (use `labor-shed`).
- Nearby businesses / retail context (use `business-key-facts` or the nearby-businesses tooling).
- Sale or lease comp requests (those are `internal-comps` / `external-comps`).
- Turning-movement counts, peak-hour volumes, or trip generation — AADT is an annual daily average, not a peak-hour or directional count.
- Multi-address batch requests (v1 supports one address at a time).
- Non-NC addresses (v1 supports NC only — NCDOT data).

## Process

1. Parse the broker's request to extract the address as a single free-text string. Don't canonicalize or pre-validate; the Census Geocoder does that server-side.
2. Call the MCP tool `pull_vpd_lookup` with `{address: "<the extracted address>"}`.
3. The response is structured JSON: `subject` (geocoded address + 1.5-mi radius), `segments` (the ranked top-5 road segments — each with `route`, `rte_cls_label`, `value` / `value_rounded` AADT, `year`, `distance_miles`, and a `display.callout`), `meta` (provenance), and `fragment_html` (a self-contained flyer card). Lead with the busiest road, then offer the full top-5.
4. Surface `fragment_html` as the drop-in flyer card when the broker is building a flyer / OM / BOV — it is the same `vpd-card` fragment the lee-listing-flyer composes. If they just asked a question, the conversational summary is enough; mention the card is available.

## How to present it

Lead with the headline road, not the table:

> Within 1.5 miles of [site], the busiest road is **[road_name]** at **[value_rounded] VPD** ([year] count), about **[distance] mi** away. The next-busiest are [#2], [#3]… (top 5 by road class then volume).

Then offer the full ranked list or the flyer card if they want it. Each row reads `[AADT] VPD on [road] — [year] count, [distance] mi`.

Ranking is by road class first (Interstate > US > NC highway > secondary), then AADT descending, then proximity — so an Interstate a mile out leads a busier-feeling secondary road right at the door, which matches how brokers talk about a site's road network. Say so if a broker asks why a closer road ranks lower.

## Error handling

Same envelope as sibling skills:

- `geocode_failed` — the address didn't resolve. Echo the broker's input back and ask for a city + state hint.
- `out_of_region` — matched address is not in NC. Tell the broker v1 supports NC only.
- `upstream_failed` — Census geocoder or D1 lookup hiccup. Apologize and ask the broker to retry.
- `rate_limited` (HTTP 429) — the broker has hit the daily cap (100 lookups/broker/day). Relay the message plainly: the daily limit is reached and resets at midnight UTC.
- `internal` — anything else. Apologize, surface a short message, ask David / Bonner to check.

If the tool returns an empty `segments` list (and an empty `fragment_html`), there were no AADT-counted roads within 1.5 mi — common for a deep-rural site. Tell the broker plainly and suggest the nearest counted corridor is farther out.

## What's deliberately NOT in v1

- Custom radius or a configurable top-N (v1 is the top 5 within 1.5 mi).
- Peak-hour / directional / turning-movement counts — AADT is an annual daily average only.
- Multi-state coverage — NC only (NCDOT AADT stations).
- Multi-address batch.

## Files

- `SKILL.md` — this file. The skill is a thin orchestrator over `pull_vpd_lookup`; no Python helpers, no local assets.
- Numeric parity reference: the `vpd-lookup` Python engine at `40_delivery/vpd-lookup/` (Concord + Cary samples). The Worker tool stages NCDOT AADT statewide to D1 and reads only from storage on the request path.
