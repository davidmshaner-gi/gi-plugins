---
name: nearby-businesses
description: Area Amenities map kit for any NC address — the recognizable businesses (grocery, retail, restaurants, coffee, gyms, pharmacies, hotels, healthcare) near a listing, ranked by prominence with their brand logos, laid out on a basemap. Returns a downloadable designer kit (basemap + logo images + a placements manifest) the marketing team drops into Claude Design to compose the flyer's amenities map. Answers "what's around this site", "nearby businesses / amenities near [address]", "map the retail around [address]" for a flyer / OM / BOV. Wraps the lee-raleigh-mcp pull_nearby_businesses tool.
---

# Nearby Businesses — Area Amenities Kit (Lee & Associates)

Build the "Area Amenities" panel for a listing: the well-known businesses near a site (the Harris Teeter, the Starbucks, the Costco), grouped on a map with their logos, for any NC address. The output is a **designer asset-kit** — a downloadable folder the marketing team composes into the final flyer map in Claude Design. It does NOT return a finished image; it returns the ingredients (a basemap, the brand logos, and a placements manifest that says where each business goes).

## When to use

Anything that asks about the businesses, retail, or amenities *around* a site — the "look how well-located this property is" panel on a flyer / OM / BOV.

Triggers:

- `/nearby-businesses <address>` (slash command)
- "What businesses are near 100 Connemara Dr, Cary?"
- "Map the nearby retail / amenities around [address]"
- "Area amenities for [listing]"
- "What's around this site?"
- "Build the amenities map for [address]"

**Don't apply this skill to:**

- Traffic counts / vehicles-per-day on the roads (use `vpd-lookup`).
- Population / income / demographics around a site (use `demographic-summary` or `demographic-detail`).
- Workforce / labor pool (use `labor-shed`).
- The single-property data sheet with the 1/3/5-mile site map (use `business-key-facts`).
- Sale or lease comps (`internal-comps` / `external-comps`).
- A fully-composed, ready-to-send flyer (this returns the kit; a designer composes it in Claude Design — or use `lee-flyer-brief` for the guided whole-flyer intake).
- Non-NC addresses (v1 is validated on NC).

## Process

1. Parse the broker's request to extract the address as a single free-text string. Don't canonicalize or pre-validate; the geocoder does that server-side. (Optional: if the broker specifies a radius, pass `radius_miles` — default is 3 miles.)
2. Call the MCP tool `pull_nearby_businesses` with `{address: "<the extracted address>"}` (add `radius_miles` only if the broker asked for a specific radius).
3. The response is structured JSON:
   - `kit_url` — a **signed download link (expires in ~15 minutes)** to the kit zip. This is the deliverable.
   - `kit_expires_at` — ISO timestamp of expiry.
   - `subject` — the geocoded address (`address`, `matched_address`, `lat`, `lng`).
   - `summary` — `discovered_total`, `within_map_radius`, `mapped`, and `by_category` counts.
   - `businesses_count` — how many businesses were placed on the map.
   - `placements_preview` — the top ~10 placed businesses (`name`, `category`, `dist_mi`) for a quick chat preview.
4. Surface the `kit_url` prominently as a "📦 Download the Area Amenities kit" link with the expiry note: *"Link expires in ~15 minutes — download it now."* Then give the broker the preview (the headline anchors) so they know what's in it before they open it.

## How to present it

Lead with the headline anchors, then the kit:

> Near **[matched_address]**, I mapped **[businesses_count]** recognizable businesses — anchors include **[top 3–4 names from placements_preview]**. Here's the Area Amenities kit to drop into Claude Design: **📦 [kit_url]** (expires in ~15 min).

Then, if useful, the category mix from `summary.by_category` (e.g. "grocery 12, restaurants 12, coffee 7…") and the full top-10 preview.

**What's in the kit (so the broker / designer knows):** a `basemap` of the area with the property pinned and 1/3/5-mile rings, a `logos/` folder of the brand logos, a `placements.json` manifest (where each business sits on the map + which need a text label), `brand.json` (Lee colors), and a `HOW_TO_USE.md` for the designer. They unzip it and compose the map in Claude Design.

> Note: the basemap currently downloads as a **PDF** (a sharp high-res PNG is in progress). It's frame-accurate and convertible/placeable; the logos and the placements manifest are the same regardless.

## Error handling

Same envelope as sibling skills:

- `geocode_failed` — the address didn't resolve. Echo the broker's input back and ask for a city + state hint.
- `out_of_region` — matched address is not in NC. Tell the broker v1 supports NC only.
- `upstream_failed` — a geocoder / discovery hiccup. Apologize and ask the broker to retry.
- `rate_limited` (HTTP 429) — the broker hit the daily cap (100 pulls/broker/day). Relay it plainly: the daily limit is reached and resets at midnight UTC.
- `internal` — anything else. Apologize, surface a short message, ask David / Bonner to check.

If `businesses_count` is 0 (or the kit is empty), there were no rating-qualified businesses within the radius — uncommon outside deep-rural sites. Tell the broker plainly and suggest a wider radius or a nearer commercial node.

## What's deliberately NOT in v1

- A finished, composed map image — this returns the **kit**; a designer composes it (that's the 2026-06-02 designer-kit decision).
- A high-res PNG basemap (currently PDF; tracked separately).
- Custom category selection or a configurable top-N (v1 maps the prominence-ranked set within the radius).
- Multi-address batch.
- Non-NC coverage.

## Files

- `SKILL.md` — this file. A thin orchestrator over `pull_nearby_businesses`; no Python helpers, no local assets.
- Parity reference: the `nearby-businesses` Python engine at `40_delivery/nearby-businesses/`. The Worker tool ports its discovery + ranking + logo-resolution + layout; brand logos accumulate in R2 across pulls (warm cache).

<!-- BEGIN CONNECTOR-AUTH BLOCK (canonical: shared/connector-auth.md — edit there, then scripts/sync-connector-auth.sh) -->
## Connector auth — attempt the call first

**Never tell the broker the lee-raleigh connector is "not authorized", "not connected",
or "needs to be authorized" unless an actual tool call just failed with an auth error.**

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
3. **First auth failure in this conversation, with the lee-raleigh tools loaded:** the
   most likely cause is a known Claude bug that reports a successful call as failed —
   the connection is usually fine, so do NOT send the broker to sign-in yet. Reply
   warmly, in broker language:

   > That error is most likely a Claude glitch (on Anthropic's side, not the Lee
   > tools) — the connection is usually fine. Tell me **"you do have access — try
   > again"** and I'll re-run it; that clears it most of the time. If it still fails
   > on the retry, a quick sign-in refresh usually fixes it
   > (https://leeraleigh.groundedintelligence.io/setup#connect-sign-in) — or email
   > David at david@groundedintelligence.io and he'll get you sorted.

   When the broker prompts the retry, attempt the call again.
4. **Second consecutive auth failure in this conversation — or the lee-raleigh tools
   are missing from this session entirely:** treat it as a genuine sign-in problem.
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
