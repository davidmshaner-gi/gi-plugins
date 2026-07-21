---
name: development-pipeline
description: Use when a broker asks what's being built, coming, or "going up" around an address or listing; when a flyer, OM, or BOV needs a development pipeline / market momentum / supply-side section; or when scouting new construction and entitlement activity in a covered NC submarket (Triangle, Harnett, Lee County NC, Wilmington/New Hanover). Read this file before invoking -- defaults and product-type selection rules are not guessable from this description.
---

# Development Pipeline (Lee & Associates)

What's being built, approved, or under review around an address -- the commercial development pipeline within a radius, from 12 pre-staged NC municipal feeds, with flyer-ready narrative bullet lines and a drop-in flyer component PDF.

## When to use

Triggers:

- `/development-pipeline <address>` (slash command)
- "What's going up around [address]?"
- "Development pipeline near [listing]"
- "What's in the pipeline near the interchange?"
- "A flyer/OM needs a Development Pipeline section" (the Atlanta-office flyer pattern, widened to all commercial)
- "How much competing product is moving through entitlement nearby?" (BOV supply-side context)

**Don't apply this skill to:**

- Who owns a property / parcel facts (use `owner-lookup` / parcel tools).
- Comps requests (those are `internal-comps` / `external-comps` / `internal-and-external-comps`).
- Demographics or workforce around a site (use `demographic-summary` / `labor-shed`).
- What businesses operate nearby today (use `nearby-businesses`). This skill reports what's being BUILT, not what's open.
- Non-NC addresses, or NC addresses far outside the covered jurisdictions (see Coverage).

## The broker selects the product types -- never assume for them

The broker picks what they want tracked. Do not silently exclude categories and do not bias toward any product type. The only silent default is for AUTO-invocation (an orchestrator like `lee-flyer-brief` calling with no broker in the loop), which runs core commercial: office, retail, industrial, multifamily, mixed use, hospitality, PLUS untagged/unspecified projects (several feeds don't tag every row; dropping those would silently understate the pipeline). To get this default, **omit the `use` parameter entirely** -- do not enumerate the categories yourself, or you lose the unspecified rows.

### The broker's questions, in order

1. **Where?** The subject address. Skip if the listing context already gives it.
2. **Which product types?** ALWAYS ask on a broker-driven run unless the broker already named them. Offer the full menu, flat, no recommendation: Office / Retail / Industrial / Multifamily / Mixed Use / Hospitality / Institutional (churches, schools, civic) / Residential (single-family, townhomes) -- any combination, or "all of it." Pass the answer as `use` (category values: `office`, `retail`, `industrial`, `multifamily`, `mixed_use`, `hospitality`, `institutional`, `residential`, or `["all"]`). Two non-menu categories exist in the data and may appear in exclusion counts: `unspecified` (the feed didn't tag the project's use -- ALWAYS include it alongside any explicit selection so the pipeline isn't understated) and `other` (parks, greenways, open space).
3. **How far out?** Offer the 3-mile default in the same breath: "I'll look 3 miles around it unless you want tighter or wider." Not a standalone question (`radius_mi`, ceiling 15 miles -- catch a wider ask before the call and say so).
4. *(Defaulted, ask nothing)* Lookback (36 months of substantive activity; `lookback_months`) and table length (14 rows + "+N more"; `max_rows`). Surface only if the broker asks for older history or a longer list.
5. **After the run -- curation.** Walk the broker through the project list; they cull or keep rows before the fragment goes anywhere near a flyer. Their selection is the narrative.

Questions 1 and 2 are the only hard stops. Everything else has a default and the broker can steer after seeing output.

### Invocation rules

- **Broker already named the product type(s)** ("industrial pipeline near the site", "what retail is coming") -- pass it straight through as `use`; question 2 is answered, do not re-ask.
- **Broker's ask is finer-grained than a category** ("church projects", "townhome development"): the engine's finest grain is the category -- "institutional" = churches + schools + civic + government; "residential" = single-family + townhomes. Ask one short question ("Churches only, or all institutional -- schools, civic, government too? I can flag just the churches in the results either way") and never hand back the whole category as if it answered the narrower ask.
- **Reporting exclusions:** the record carries `excluded_by_use_breakdown` -- per-category counts of what the broker's selection filtered out. Quote it per category ("12 residential and 3 institutional projects were outside your selection") and offer the rerun: "That's the {selection} picture -- I can widen to all product types if you want the full market story."
- **Minor works are screened automatically.** Infrastructure filed as its own case (retaining walls, sewer extensions, storm drains) and cosmetic work (facade revisions, repaints, parking lots) are dropped by name keywords regardless of use tag; amendment cases collapse into the parent row. Counters: `excluded_minor_works`, `deduped_amendments`. `include_minor_works: true` opts back in.

## Process

1. Resolve the address + product types per the question flow above.
2. Call the MCP tool `pull_development_pipeline` with `{address, use?, radius_mi?, include_minor_works?, lookback_months?, max_rows?}`. Address is a single free-text string; don't pre-validate.
3. The response is a JSON record: `projects` (sorted by lifecycle stage then distance), `stage_counts`, exclusion counters (incl. `excluded_by_use_breakdown`), `narrative_bullets`, `sources` (per-feed health), `data_as_of`, `fragment_html`, `pdf_url`.
4. **Lead with the narrative bullets** -- they are the flyer-ready one-liners brokers hand-write today ("115,846 SF of multifamily under construction 2.2 mi away"). Then the stage picture (counts by Submitted / Under Review / Approved / Under Construction / Completed, plus "Status Unclear" when a feed's status didn't map -- include it or the counts won't sum to the project total), then the project table on request. If `projects_truncated` is true the table was capped at 200 rows (`project_count` carries the real total) -- suggest tightening the radius or the product-type selection.
5. If `pdf_url` is a non-null string, surface it as a "📄 Open PDF" link with an expiry note (use `pdf_expires_at` when present; otherwise "~1 hour"): *"Link expires soon, download or share it now."* If `pdf_url` is `null`, deliver the structured data and suggest the broker re-run.
6. `fragment_html` is the `dpt-*` flyer fragment -- a composition input for flyer/OM workflows (`lee-flyer-brief`); mention it only in that context, not on a conversational pull.

## How to present it

Lead with the broker question, not the table:

> Within 3 miles of [site], **N** commercial projects are moving through the pipeline: **A** under construction, **B** approved, **C** in review. The biggest: [top narrative bullet]. [Second bullet.]

Then offer the full table, the per-category exclusion picture, and the PDF.

## Coverage and freshness

Twelve feeds: Raleigh, Cary, Durham (city-county), Apex, Garner, Morrisville, Wake County (unincorporated), Wake Forest, Chapel Hill, Harnett County, Lee County NC (Sanford + Broadway), New Hanover County (Wilmington + beach towns; building permits cover the back half of the pipeline there, so "under review" runs thin). No machine-readable source exists for Holly Springs, Johnston County towns, Fuquay-Varina, Knightdale/Wendell/Zebulon, Hillsborough/Carrboro/Orange, Chatham towns, Franklin, or Granville -- addresses there come back sparse rather than wrong; say so up front, do not silently deliver thin data.

Data is pre-staged nightly into the Lee data engine (no live municipal calls at request time -- responses are fast and reliable). `data_as_of` is the staging date; the `sources` array names any feed that failed its last refresh. The store also accumulates per-project status-transition history the counties themselves overwrite.

## Form-driven invocation (New Listing Marketing Request)

When the run originates from the marketing team's form / `lee-flyer-brief` rather than a live broker conversation:

| Form field | Skill input |
|---|---|
| Address | Subject address (question 1 answered) |
| Property Type (e.g. Office + Retail) | NOT the tracking selection -- it describes the listing. Run `use: ["all"]`; the broker selects at curation |
| Office (Raleigh / Wilmington...) | Coverage check: outside the feed list the result will be sparse -- say so up front |
| Parcel Number(s), Zoning | Not this skill |

`narrative_bullets` feed the form's Lease/Sale Bullet Points section; `fragment_html` feeds the flyer's pipeline panel.

## Error handling

Same envelope as sibling skills:

- `geocode_failed` -- the address didn't resolve. Echo the broker's input back and ask for a city + state hint.
- `out_of_region` -- matched address is not in NC. Tell the broker v1 supports NC only.
- `internal` with an `invalid_use_category` message -- re-map the broker's product-type words onto the category menu and retry.
- `internal` (anything else) -- apologize, surface a short message, ask David / Bonner to check.

## What's deliberately NOT in v1

- A pin map (composes later with `comp-map`).
- Construction stage for Raleigh/Cary/Durham (those feeds stop at approval; building-permit joins are tracked follow-up work).
- Jurisdictions with no machine-readable feed (see Coverage).
- Multi-address batch.

## Files

- `SKILL.md` -- this file. The skill is a thin orchestrator over `pull_development_pipeline`; no Python helpers, no local assets.
- Parity reference: the Python engine at `40_delivery/development-pipeline-tracker/` (parent GI repo).

<!-- BEGIN CONNECTOR-AUTH BLOCK (canonical: shared/connector-auth.md — edit there, then scripts/sync-connector-auth.sh) -->
## Connector auth — attempt the call first

**Never tell the broker the lee-raleigh connector is "not authorized", "not connected",
or "needs to be authorized" unless an actual tool call just failed with an auth error.**

1. **Attempt first.** If the lee-raleigh tools appear in your available tools, call the
   one you need — do not assess authorization beforehand. A needs-auth flag, an empty
   credential field, a `/mcp` probe, or any other indirect signal is NOT authorization
   state; the only way to know is to make the call. If you have not attempted the call
   in this conversation, you do not know the auth state — so call it.
2. **Only a tool-level auth error counts.** Treat the connector as unauthorized ONLY
   when a call you just made returned an authorization error (`401` / `invalid_token`).
   Any other failure — a timeout, an empty result, a data error — is not an auth
   problem; handle it per this skill's error handling, and a plain retry line ("try
   again in a few minutes") is only ever for those transient, not-an-auth failures.
3. **On a genuine auth failure** — an attempted call returned `401`/`invalid_token`, or
   the lee-raleigh tools are missing from this session entirely — reply warmly, in
   broker language:

   > It looks like the Lee Raleigh connection needs a quick sign-in refresh — this can
   > happen after a reinstall, a new computer, or an app update. In Claude, open the
   > **Lee internal comps** plugin, go to its **Connectors** tab, and click the button
   > next to **lee-raleigh**. Sign in with the email you use for Claude (your Lee email
   > for most people) and send yourself the magic link. If the link says it expired,
   > that's normal — just request another from the sign-in page; the second request is
   > what signs you in. Full walkthrough with screenshots:
   > https://leeraleigh.groundedintelligence.io/setup#connect-sign-in — it takes about
   > a minute, then just ask me again.

   Never point a broker at "/mcp", never mention MCP or OAuth by name, and never answer
   an auth failure with "try again in a few minutes" — those leave them stuck.
<!-- END CONNECTOR-AUTH BLOCK -->
