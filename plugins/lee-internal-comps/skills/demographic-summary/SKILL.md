---
name: demographic-summary
description: Pull a 1/3/5-mile demographic summary (single-page Lee infographic) for any NC address. Returns population, households, income, education, workforce mix, daytime population, and growth rates with per-metric methodology metadata, plus a Lee-branded PDF link (1-hour signed URL). Wraps the lee-raleigh-mcp pull_demographic_summary tool.
---

# Intellisite Demographic Infographic (Lee & Associates)

Pull a demographic profile for 1, 3, and 5-mile rings around any NC address.

## When to use

Anything that asks for a "demographic profile" or an "infographic" around a property address. The phrasing is open — what matters is the intent.

Triggers:

- `/demographic-summary <address>` (slash command)
- "Pull infographic for 100 Walnut St, Cary"
- "Demographic profile of 200 Main St, Raleigh"
- "Site report for [address]"
- "What does the demographic look like around [address]"

**Don't apply this skill to:**

- Sale or lease comp requests (those are `internal-comps` / `external-comps`).
- Multi-address batch requests (v1 supports one address at a time).
- Custom ring sizes (v1 is hardcoded to 1/3/5 mi).

## Process

1. Parse the broker's request to extract the address as a single free-text string. Don't try to canonicalize or pre-validate — the Census Geocoder does that server-side.
2. Call the MCP tool `pull_demographic_summary` with `{address: "<the extracted address>"}`. The tool takes ~10-15 seconds.
3. The response is structured JSON with three top-level ring keys (`1mi`, `3mi`, `5mi`) plus metadata. Render it inline conversationally — Claude already handles ring-keyed objects well; no custom formatting helper is needed.
4. If `pdf_url` is a non-null string (the expected v1.1 path), surface it as a "📄 Open PDF" link with a 1-hour expiry note: *"Link expires in ~1 hour — download or share it now."* If `pdf_url` is `null` (transient render failure — the JSON response is non-fatal on PDF errors), deliver the structured data as usual and add a short note: *"The PDF render hit a snag this run; the data is fully present. Re-run the command to regenerate the PDF."*

## Error handling

The tool returns structured errors:

- `geocode_failed` — the address didn't resolve. Echo the broker's input back and ask for clarification (city + state hint helps).
- `out_of_region` — matched address is not in NC. Tell the broker that v1 supports NC only; the team will expand coverage as demand surfaces.
- `upstream_failed` — Census or TIGER API is having a moment. Apologize and ask the broker to retry in a few minutes.
- `internal` — anything else. Apologize, surface a short message, and ask David / Bonner to check.

## What's in the response

Per-ring metrics, each carrying inline `method` / `source` / `vintage`:

- **Counts**: population, households, housing units, mean & median household income, median home value, median age
- **Mix**: bachelor's or higher %, workforce office/services/trades %
- **Baseline**: Decennial 2020 + recent ACS 5yr pop + housing, with the annualized growth rate between them
- **LEHD-derived**: employee count, resident workers, daytime population (`total_pop - resident_workers + workplace_workers`), daytime ratio

`methodology_version` is the Bonner package version this Worker port is calibrated against. `methodology_doc` points at the design spec.

## CRITICAL: how to present growth rates

`pop_growth_annual_pct` and `housing_growth_annual_pct` are **backward-looking** annual rates derived from 2020 Decennial → 2023 ACS 5-year, NOT current/forward growth.

The ACS 5-year vintage labeled "2023" is a *rolling average* of 2019–2023 survey responses. In fast-growth markets — Cary, Apex, Holly Springs, Raleigh exurbs, anywhere with post-2020 in-migration — this rolling average smooths over the actual growth and frequently produces **negative annual rates even where the area is visibly booming**. This is a real methodology artifact, not a data error.

**When the broker sees a negative growth rate in an obvious-growth market:**
- DO present the number as-is — don't hide it
- DO NOT editorialize "this is unusual" or "this might be wrong"
- DO add a one-line context note when growth is negative or surprising: *"Note: this is a backward-looking annual rate from the 2020 Decennial → 2023 ACS 5-year rolling average; it lags actual on-the-ground growth in fast-moving submarkets. Forward-projection growth (Esri-style 2025/2028 estimates) arrives in v1.2."*
- Housing growth tends to be more reliable than population growth at small rings (Cary 3mi/5mi housing growth +3.2%/+2.2% is in line with what you'd expect)

If both pop growth AND housing growth are negative at all rings, that's typically the rolling-average artifact, not a real signal. Flag the data, don't doubt the data.

## CRITICAL: per-metric source/vintage disclosure

Every metric in the response has `source` (e.g. "ACS 5yr B01003_001E") and `vintage` (e.g. 2022). If the broker asks "where is this from" or "how recent is this", quote the inline `source` + `vintage` for the specific metric — don't paraphrase. The methodology is the contract; surface it accurately.

## CRITICAL: daytime population is workforce-only

`daytime_population = total_pop - resident_workers + workplace_workers`. This counts workers but **does not** impute shoppers, students, hospital patients, or other non-worker daytime presence. Esri BAO's daytime number is typically 10-15% higher for retail/commercial centers because it adds those non-worker flows. If a broker compares our number to a BAO printout for a retail site, expect a gap and explain why — don't assume our number is wrong.

## What's deliberately NOT in v1

- Tapestry segmentation, Wealth Index, Total Sales, Largest Businesses in Area — Esri-only data, not portable.
- Forward-projection growth (e.g. "Population (2025)") — deferred to a future version.
- Multi-state coverage — NC only for v1.
- Charts (age distribution, income, race breakdowns) — v1.1 PDF is tile-grid only; charts arrive in v1.2 once the JSON shape widens to carry the breakdowns the charts plot.

## Files

- `SKILL.md` — this file. The skill is a thin orchestrator over `pull_demographic_summary`; no Python helpers.

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
   > tools) — the connection is usually fine. Tell me **"you do have access — try
   > again"** and I'll re-run it. If it still fails on the retry, a quick sign-in
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
