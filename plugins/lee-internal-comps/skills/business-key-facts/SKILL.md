---
name: business-key-facts
description: Pull a Lee-branded BAO-style Business Key Facts PDF (3-page landscape) for any NC address. Returns key statistics, households table, site map with 1/3/5 mile rings, education attainment + workforce charts, and population/housing growth with backward-rate context. Wraps the lee-raleigh-mcp pull_business_key_facts tool.
---

# Business Key Facts (Lee & Associates)

Pull a BAO-style Business Key Facts infographic for 1, 3, and 5-mile rings around any NC address.

## When to use

Anything that asks for a "BAO infographic," "business key facts," "business summary," or an ESRI-style demographic infographic with the site map + education + workforce visuals.

Triggers:

- `/business-key-facts <address>` (slash command)
- "BAO infographic for 100 Walnut St, Cary"
- "Business key facts for [address]"
- "Business summary for [address]"
- "Pull the BAO-style report for [address]"

**Don't apply this skill to:**

- Single-page demographic handouts (use `demographic-summary` instead).
- Multi-page OM-attachment demographic reports (use `demographic-detail` instead).
- Sale or lease comp requests (those are `internal-comps` / `external-comps`).
- Multi-address batch requests (v1 supports one address at a time).
- Custom ring sizes (v1 is hardcoded to 1/3/5 mi).
- Non-NC addresses (v1 supports NC only).

## Process

1. Parse the broker's request to extract the address as a single free-text string. Don't try to canonicalize or pre-validate — the Census Geocoder (with Nominatim fallback) does that server-side.
2. Call the MCP tool `pull_business_key_facts` with `{address: "<the extracted address>"}`. The tool takes ~10-20 seconds (D1 demographics + R2 tile reads + Browser Rendering).
3. The response is structured JSON with three top-level ring keys (`1mi`, `3mi`, `5mi`) + chart SVGs + a `pdf_url`. Render the JSON inline conversationally — focus on the highest-signal numbers (population, daytime population, mean HH income, workforce mix).
4. If `pdf_url` is a non-null string, surface it as a "📄 Open PDF" link with a 1-hour expiry note: *"Link expires in ~1 hour — download or share it now."* If `pdf_url` is `null` (transient render failure — the JSON response is non-fatal on PDF errors), deliver the structured data and suggest the broker re-run.
5. **If `degraded_note` is a non-null string, always relay it to the broker verbatim** (in addition to whatever you do with `pdf_url`). It fires only when the report had to shrink to stay under the render size limit, and it comes in two flavors: (a) the PDF rendered but the site map fell back to simple radius rings instead of the full street map — `pdf_url` is present, so still give the link *and* mention the map was simplified; (b) the report was too large to render a PDF at all — `pdf_url` is `null`, so deliver the key facts and pass along the note (which tells the broker to re-run). When `degraded_note` is `null` (the normal case), say nothing about it.

## Error handling

Same envelope as sibling skills:

- `geocode_failed` — the address didn't resolve. Echo the broker's input back and ask for clarification (city + state hint helps).
- `out_of_region` — matched address is not in NC. Tell the broker that v1 supports NC only.
- `upstream_failed` — Census or D1 lookup hiccup. Apologize and ask the broker to retry.
- `internal` — anything else. Apologize, surface a short message, and ask David / Bonner to check.

## What's in the response

Per-ring metrics for 1/3/5 mile rings (with inline `method` / `source` / `vintage`):

- **Counts**: population, households, housing units, mean HH income
- **Workforce-derived**: daytime population, daytime/total ratio
- **Visuals (1-mi only)**: education attainment 8-bucket bar chart, workforce 3-slice pie chart, site map with rings overlay
- **Growth**: 2020/2023 population + annualized growth rate (backward-looking, see CRITICAL note below)

## CRITICAL: how to present growth rates

`pop_growth_annual_pct` and `housing_growth_annual_pct` are **backward-looking** annual rates derived from 2020 Decennial → 2023 ACS 5-year, NOT current/forward growth. Same caveat as `demographic-summary`.

The ACS 5-year vintage labeled "2023" is a *rolling average* of 2019–2023 survey responses. In fast-growth markets — Cary, Apex, Holly Springs, Raleigh exurbs, anywhere with post-2020 in-migration — this rolling average smooths over the actual growth and frequently produces **negative annual rates even where the area is visibly booming**. This is a real methodology artifact, not a data error.

The PDF carries an inline context note on page 3 explaining this. Echo the note's content if a broker asks about negative growth: *"Backward-looking annual rate from the 2020 Decennial → 2023 ACS 5-year rolling average; it lags actual on-the-ground growth in fast-moving submarkets. Forward-projection growth (Esri-style 2025/2028 estimates) arrives in a later version."*

If both pop growth AND housing growth are negative at all rings, that's the rolling-average artifact, not a real signal.

## What's deliberately NOT in v1

- Tapestry segmentation, Wealth Index, Total Sales, Largest Businesses, exact business counts — Esri-only data, not portable.
- Forward-projection growth (2025/2028) — deferred to a future version, same as `demographic-summary` v1.
- Multi-state coverage — NC only for v1.
- Drive-time isochrones — roadmap #57 covers the isochrone overlay across all of `demographic-summary`, `demographic-detail`, and `business-key-facts` together.
- Fragment.html + record.json output for `/lee-listing-flyer` composition — v2 scope.

## Files

- `SKILL.md` — this file. The skill is a thin orchestrator over `pull_business_key_facts`; no Python helpers and no local assets. The Lee logo is served into the PDF by the `pdf-renderer` Worker via its ASSETS route.

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
