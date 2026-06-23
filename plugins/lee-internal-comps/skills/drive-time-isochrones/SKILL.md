---
name: drive-time-isochrones
description: Map how far you can get from a property in 5, 10, and 15 minutes by car (or on foot / by bike) for any NC address. Use when a broker asks "what's within a 10-minute drive", wants a drive-time map for a flyer, OM, or BOV, wants trade-area reach instead of crude mile rings, or asks for drive-time isochrones. Returns per-band reach areas, isochrone GeoJSON, and a Lee-branded map card PDF. Wraps the lee-raleigh-mcp pull_drive_time_isochrones tool.
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
- "How long does it take to drive from A to B" point-to-point questions (this tool
  draws reach polygons from one site; it does not route between two addresses).
- Rush-hour or time-of-day commute analysis — v1 returns free-flow times only.
- Non-NC addresses (v1 supports NC only).

## Process

1. Extract the address as a single free-text string. Don't pre-validate — the
   Census Geocoder (with Nominatim fallback) resolves it server-side.
2. Defaults are 5/10/15 minutes driving. Honor explicit asks: "20-minute drive" →
   `minutes: [20]` (1–60, up to 5 bands); "walking distance" → `profile: "walking"`;
   "bike" → `profile: "biking"`.
3. Call the MCP tool `pull_drive_time_isochrones` with
   `{ address, minutes?, profile? }`. Typical latency ~5–15s (first pull of an
   address calls the routing engine; repeats are cached and faster).
4. Read the JSON: each band's `area_sq_miles` is the headline — lead with the widest
   band ("~99 sq mi is within a 15-minute drive of the site"). `geojson` carries the
   polygon geometry for anyone composing maps downstream.
5. If `pdf_url` is a non-null string, surface it as a "📄 Open PDF" link with a
   1-hour expiry note: *"Link expires in ~1 hour — download or share it now."* If
   `pdf_url` is `null` (transient render failure — the JSON is non-fatal on PDF
   errors), deliver the numbers and suggest the broker re-run.
6. `meta.free_flow_only` is always true in v1: travel times assume posted speeds with
   no congestion. If the broker asks about rush hour, say so plainly — peak-hour
   reach is typically 15–30% smaller in urban areas.

## Error handling

Same envelope as sibling skills — relay the `message` verbatim, it is written for
brokers:

- `geocode_failed` — the address didn't resolve. Echo the input back and ask for
  clarification (city + state hint helps).
- `out_of_region` — matched address is not in NC. v1 supports NC only.
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
- `geojson` — the isochrone FeatureCollection (one Feature per band).
- `fragment_html` — a compact polygons-only SVG card for inline composition.
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
