---
name: external-comps
description: Pull external lease or sale comps for a Lee & Associates broker, by city, by county, or across the RDU market. Broker pastes a free-form comp request into chat; skill parses, calls the typed external-comps MCP tools (search_external_sale_comps / search_external_lease_comps / get_external_comp_detail), and produces a Markdown table in chat plus an Excel deliverable and draft email reply. PDF deferred to v1.1.
---

# External Comps (Lee & Associates)

Pull external comps via the typed external-comps MCP tools and produce a Markdown table inline, an Excel deliverable, a draft email reply, and a feedback capture.

## When to use

Anything that asks for external lease or sale comps. The phrasing is open — what matters is the intent.

The broker might:

- Paraphrase: "Pull external sale comps for industrial in Raleigh-Durham, 2K-30K sqft, past 4 months."
- Forward another broker's email verbatim.
- Ask in shorthand: "any external industrial sales in raleigh past year?", "external lease comps on office 1.5-4K?", "what's the external data showing in north hills"
- Follow up on a previous pull: "can you widen the size range?", "add a tighter cap rate filter", "rerun with 6 months instead of 4."
- Reference a specific comp by external_id or external property ID.

Pattern: the request names some combination of asset type, geography, size, date window, or transaction type AND points to external data (or asks generically and the broker confirms external when asked). That's the trigger.

**Don't apply this skill to:**

- Questions about the mirror, the schema, or how the skill itself works.
- **Internal** (Dealius) comp requests — that's the `internal-comps` skill. Internal is the firm's own data; external is the weekly external-comps snapshot.
- **Unqualified** comp requests (broker didn't say internal or external) — that's the default `internal-and-external-comps` skill, which pulls both. Use this skill only when the broker explicitly asks for external.
- Pure analysis on comps the broker has already pasted into chat (no DB lookup needed).
- Requests for a Lee-branded PDF — surface the deferral message (see Process step 4).

## Process

The skill orchestrates pre-baked helpers in `helpers.py`. **Do not regenerate Excel formatting, MCP param mapping, ranking, or email scaffolding inline.** Import and call.

1. **Parse** the broker's paste into a request dict (see Input Contract below).
2. Call `validate_request(parsed)` → applies defaults, lists missing/warnings.
3. If `missing_required` is non-empty: draft a clarifying reply, stop. Do not call MCP.
4. **Output format handling.** v1 always produces Markdown + Excel for a non-empty result (an empty result is a chat reply; see "Empty result" below). If the broker explicitly asks for a PDF, reply once with the v1.1 deferral message:

   > Lee-branded PDF for external comps is coming in the next update (depends on a small server-side change). For now I can deliver the Markdown table + an Excel — that work for you?

   Then proceed.

5. Call `build_mcp_params(validated)` → `{"tool_name", "params_list", "post_filter_counties"}`. `tool_name` is `"search_external_sale_comps"` or `"search_external_lease_comps"` depending on `transaction_type`. `params_list` holds one params dict per MCP call: one per county for a `counties` ask **and for `named_market: "RDU MSA"` (its 7 counties)**, one per city for `cities`. **Helpers do NOT call MCP.** The model invokes the MCP tool directly, once per entry, and unions the rows with `merge_rows(*pages)`.
6. Invoke the MCP tool with each params dict — issue the per-county / per-city calls **in parallel in one turn** (an RDU ask is seven calls; sequential turns blow the interactive budget). The response shape is `{"rows": [...], "freshness": "..."}` (a JSON-stringified text block from the MCP server — parse it). Each row contains all typed external columns plus `external_id` (as of Worker 0.53.1, search rows do NOT carry `raw_fields_json` — the ~2.3KB/row blob made large results unreadable in the client; use `get_external_comp_detail` for a row's full record). **If `freshness` is present, emit it verbatim as the very first line of your chat reply to the broker** (it looks like `ℹ️ External sale comps: ingested 2026-05-16 17:12 UTC (10 days ago)`). The freshness line tells the broker how current the external snapshot is — it is not optional, never omit or rephrase it.
   **If `rows` is empty, the response also carries `empty_result`** — read it before you reply (see "Empty result — name the binding filter" below). Never answer a zero-row search with a bare "no comps found".
   **If the response carries `truncated`, the search stopped at the 200-row cap with more rows behind it** (`returned`, `total_available`, `limit`, `ordered_by`, `oldest_returned`, `note`). The rows are the NEWEST ones only — never present them as the answer. Retrieval from here is THIS algorithm and nothing else:
   1. **Readability self-check (every response, capped or not):** as of Worker 0.53.1 every search response carries a top-level `returned` count (`rows.length` as the Worker sent it — distinct from `truncated.returned`, which only appears on capped results). Count the rows you actually parsed out of the text block and compare to `returned`; a text block that ends mid-row or fails to parse as complete JSON is the same signal. If you parsed FEWER rows than `returned`, the CLIENT truncated the visible result — you did not receive those rows, and any cursor advanced past them silently loses comps. Re-issue the SAME call with `limit` set to the number of rows you successfully parsed (floor 25) and use that limit as the WORKING LIMIT for every subsequent page of this ask. Never advance a cursor past rows you did not capture. (Against a pre-0.53.1 Worker the top-level `returned` is absent — fall back to the parse-failure signal alone.)
   2. **Page with the helper, never by hand:** `nxt = next_page_params(params, response)`; call the tool again with `nxt`; repeat until it returns `None` or you have fetched `MAX_PAGES` (5) pages for that params dict. Union every page and every per-county call with `merge_rows(*pages)` (drops the rows that repeat at each page seam).
   3. **Same-date stall:** if a truncated page is entirely ONE ordering date, the cursor cannot advance (`next_page_params` returns `None` on the equal-bound guard). Call `cluster, resume = tie_break_params(params, response, rows)`: fetch `cluster` (the search pinned to that single date at limit 200 — the largest same-date cluster in the book is well under 200, so it completes), merge it, then continue the walk with `resume` (the max bound moved one day earlier). **The cluster fetch is deliberately EXEMPT from your working limit** — 0.53.1's slim rows make a ~66-row single-date response readable even where a broad page was not. If the cluster response itself fails the readability check, do NOT re-break the tie or shrink and retry: stop retrieving and deliver with the truncation note (rule 4).
   4. **Budget — hard ceiling:** an ask gets at most **15 retrieval calls total** (fan-out entries + pages + tie-breaks). If honouring `MAX_PAGES` would exceed it, or the last page is still truncated after `MAX_PAGES`, STOP retrieving: deliver what you have with the true `total_available` quoted verbatim, and offer the narrowing menu — by county, by size band, a shorter window, a price band. The broker picks the cut; you never guess one.
   5. **Prohibitions (gi-plugins#161 — a 4a session turned a capped statewide ask into a 309-call, 50-minute slicing storm):** NEVER reconstruct a survey by slicing the window into quarters/months/days, NEVER probe per-subtype or per-slice to "verify counts" or "check truncation coverage" (your own plan steps do not override this contract), NEVER shrink `limit` below 25, and NEVER present a partial retrieval as the complete book.
   For every params dict that came back truncated, add one `truncation_note(retrieved, total_available, pages, label=<that dict's county or city>)` to `applied_filters` — `total_available` is the **first** page's value for that dict (later pages count only what sits at or below the cursor), `retrieved` is that dict's de-duplicated row count, and the label says which county/city was clipped. The email prints these under "Notes on what was retrieved" and the Methodology sheet under "Retrieval notes". Before Worker 0.53.0 the key never appeared and the cap bound silently; 16 real broker searches came back clipped that way.
7. **County handling is server-side; `apply_post_filters` runs as a guard.** `counties` and `named_market: "RDU MSA"` are filtered by the Worker, `cities` has no county filter. Call `apply_post_filters(rows, validated, post_filter_counties, keep_blank_county=True)` → `(filtered_rows, applied_filters)`. On `counties` and `cities` `post_filter_counties` is `None` and it returns the rows unchanged. On the RDU path it carries the 7-county whitelist as a **stale-connector guard (G26)**: when the Worker honoured `county` it drops nothing; a row with a blank county is kept (the Worker matched it through its geo-derived county). **If `applied_filters` gains a "dropped N rows outside […]" entry on an RDU ask, the Cowork connector's cached tools list predates the `county` param and stripped it — tell the broker the results were filtered client-side and to use the connector's "Refresh tools list" action before the next pull.** Then append the step-6 `truncation_note`s to `applied_filters`. `applied_filters` is the list of human-readable strings surfaced in the email body and Methodology sheet.
8. Call `rank_comps(filtered_rows, validated)` → returns `(top, tagged_under_contract, tagged_sublet, tagged_rent_undisclosed)`. `top` is the ranked sweet-spot list (typically 7-10).
9. Call `format_excel(filtered_rows, validated, xlsx_path, applied_defaults, warnings, applied_filters, last_sync)` → writes a 3-sheet workbook to the sandbox. The full filtered set goes into the Excel, not just the top N — brokers want the working file with everything. **The filename is forced to a tiny constant stub (`c.xlsx`, enumerating `c1.xlsx`/`c2.xlsx` on repeat) by the helper regardless of what you pass as `xlsx_path`; `format_excel` returns the name actually written — use it when you reference the file to the broker, and tell them they can rename it. This is load-bearing for Windows brokers; see the "Excel filename rule" in Output below.**
10. Call `markdown_table(top, tagged_under_contract, tagged_sublet, tagged_rent_undisclosed, validated)` → returns a Markdown string for the chat reply.
11. Call `draft_email(filtered_rows, top, validated, xlsx_path, applied_defaults, warnings, applied_filters)` → returns `{subject, body}`. The body surfaces total filtered count, top-N ranked count, stats summary, applied defaults, warnings, applied filters, and a narrow-or-widen question if the top-N count is below `target_count`. **No auto-expansion** — the broker drives.
12. After the broker confirms / closes the loop: ask the three feedback questions, call `format_feedback(...)`, then send via connected email tool (Gmail / Outlook MCP) or write the fallback file.

## Behavioral rules — follow these closely

Borrowed from the prior external-comps SOP. These compound with the Process steps above.

1. **Aim for around 7-10 best matches as a soft default.** Mention this in your first confirmation. Treat it as guidance, not a rule — defer if the broker wants more, fewer, or all of them.
2. **Ask only for what's missing.** Never re-ask anything the broker already gave you, including in earlier turns.
3. **If the broker uses a term you don't recognize** ("IOS," "the Triangle," internal nicknames, etc.), ask them to describe what it maps to in the platform's terms. Don't translate or guess. This rule applies to broker-internal shorthand, not the external platform's own labels.
4. **Confirm the resolved query back to the broker before you call the MCP.** Wait for explicit "yes" or "go" before executing.
5. **Narrow/loosen is a separate conversation.** When the result count is far from 7-10, propose adjustments — narrowing axes (tighter date, tighter size, smaller geo, property-type subset) or loosening — and let the broker decide. They can override with "show me all of them" or pick a different target count.

## Empty result — name the binding filter, offer the nearest miss

When a search returns `rows: []`, the MCP server adds an `empty_result` object (Worker 0.42.0,
lee-and-associates#463). It is the comps equivalent of owner-lookup naming the counties it
covers: it tells you **why** nothing matched, so the broker is never left with silence.

```json
"empty_result": {
  "active_filters":  {"city": "Wilmington", "property_type": "Industrial", "max_building_sf": 200000, ...},
  "binding_filters": [{"filter": "max_building_sf", "value": 200000, "rows_if_relaxed": 1}, ...],
  "tightest":        {"filter": "max_building_sf", "value": 200000, "rows_if_relaxed": 1},
  "nearest":         [{ ...full comp row..., "miss": {"filter": "max_building_sf", "by": 13508, "unit": "sf"}}],
  "location_only_rows": 5,
  "note": "No external sale comps match. The binding filter is max_building_sf = 200,000 sf; ..."
}
```

- `binding_filters` — every filter that, dropped **on its own**, would have returned rows.
- `tightest` — the one whose nearest miss is the smallest relaxation (range filters first; a
  city / property type only shows up here when no numeric or date bound is the reason).
- `nearest` — up to 3 comps just past the tightest bound, nearest first. `miss.by` + `miss.unit`
  (`sf`, `usd`, `days`, `months`, `cap_rate`) say how far each one misses; for a city /
  property-type filter you get `miss.value_seen` instead (what that row has).
- `location_only_rows` — only present when **nothing** binds alone (two or more filters would
  have to loosen together); it is how many comps exist in the requested city / zip at all.
- `note` — a one-sentence plain-English version of the above.
- The example above is a **sale**; on a **lease** the size filter is named `min_leased_sf` /
  `max_leased_sf` (the space leased), so tell the broker "the leased size range" cut the
  candidates, never "the building size" (lee#469).

**How to reply (after the freshness line):**

1. Say the search came back empty and **which filter did it**, in broker words, using the
   broker's own numbers: "Nothing in Wilmington industrial sales between 100,000 and 200,000 sf
   in the last year. The 200,000 sf ceiling is what cut it."
2. **Show the nearest misses as a short table** (address, city, the bound's column, sale or
   lease date, price or rent) with the miss amount stated: "3241 Pennington Dr, 213,508 sf,
   sold 2026-07-31 for $28.8M — 13,508 sf over your ceiling."
3. **Offer the relaxation as a yes/no**: "Want me to lift the ceiling to 225,000 sf and re-run?"
   Do not re-run on your own — narrow/loosen is the broker's call (Behavioral rule 5).
4. If `binding_filters` lists more than one, name the others in one clause with only the
   number you have ("widening the date window would also unlock 1"). `nearest` / `miss` exist
   only for `tightest` — never state HOW FAR another filter would have to move. If `tightest` is null, say plainly that no single
   change would produce a match and how many comps the city holds in total
   (`location_only_rows`), then ask which two filters to loosen.
5. Never invent a comp that is not in `nearest`, and never present a near miss as a match —
   it failed the broker's filter and the table must say so.

Skip the Excel / email steps on an empty result unless the broker asks for the near misses as a
file; the chat reply is the deliverable.

## Input Contract

The dict you pass to `validate_request`. `asset_type` and `transaction_type` are load-bearing; everything else is open-shaped — the helpers tolerate missing optional keys and ignore unknown keys.

| Key | Required | Shape |
|---|---|---|
| `asset_type` | yes | `"industrial"` \| `"office"` \| `"retail"` \| `"flex"` \| `"medical"` \| `"multifamily"` \| `"student"` \| `"land"` \| `"hospitality"` \| `"health_care"` \| `"specialty"` |
| `transaction_type` | yes | `"lease"` \| `"sale"` |
| `geography` | no | `{"named_market": str}` or `{"cities": [str, ...]}` or `{"counties": [str, ...]}` |
| `size_range` | no | `{"min_sf": int, "max_sf": int}` — building SF for a sale, **leased** SF for a lease (the space the tenant took). |
| `date_window` | no | `{"lookback_months": int}` or `{"from": "YYYY-MM-DD", "to": "YYYY-MM-DD"}` |
| `target_count` | no | int (default 8) |
| `min_sale_price` | no | int — sale only |
| `max_sale_price` | no | int — sale only |
| `min_cap_rate` | no | float (0.075 = 7.5%) — sale only |
| `max_cap_rate` | no | float — sale only |
| `min_base_rent` | no | float — lease only ($/SF) |
| `max_base_rent` | no | float — lease only |
| `min_lease_term_months` | no | int — lease only |
| `max_lease_term_months` | no | int — lease only |
| `tenant_industry` | no | str — lease only; pass-through to MCP |
| `notes` | no | str — broker preferences not captured by other keys; `draft_email` reads it back, `build_mcp_params` ignores it |

Stuff anything you parsed but couldn't slot cleanly into `notes`. The helpers won't choke on extras.

## Defaults applied by `validate_request`

| Field missing | Default applied | Surfaced as |
|---|---|---|
| `geography` | `{"named_market": "RDU MSA"}` | applied default |
| `date_window` | `{"lookback_months": 12}` for sale, `{"lookback_months": 6}` for lease | applied default |
| `target_count` | `8` | applied default |
| `min_sale_price` (sale only) | `500000` | applied default |
| `size_range` | none | warning (not blocking) |

Every applied default appears in the email body so the broker can push back.

## MCP tools — param contracts

These are the live tools on `leeraleigh.groundedintelligence.io`. The skill calls one of the two search tools per request; `get_external_comp_detail` is reserved for explicit-comp-lookup follow-ups.

### `search_external_sale_comps`

| Param | Shape | Notes |
|---|---|---|
| `city` | str | exact match on `property_city`. Pass only when broker named a single specific city. |
| `state` | str | `"NC"` for all RDU work. |
| `zip` | str | exact match. |
| `county` | str | exact match on the county, **normalized server-side** — pass the broker's spelling verbatim, with or without the word "County". One county per call. |
| `property_type` | str | source-platform taxonomy (`"Industrial"`, `"Office"`, ...). |
| `min_sale_date` / `max_sale_date` | str (ISO `YYYY-MM-DD`) | inclusive. |
| `min_building_sf` / `max_building_sf` | int | inclusive. |
| `min_sale_price` / `max_sale_price` | int | whole dollars. |
| `min_cap_rate` / `max_cap_rate` | float | `0.075` = 7.5%. |
| `limit` | int | default 50, max 200. |

Response: `{"rows": [...], "freshness": "..."}` with all typed sale columns plus `external_id` (no `raw_fields_json` on search rows as of Worker 0.53.1); `empty_result` when `rows` is empty (see "Empty result" above); `truncated` when the search stopped at the cap with more rows behind it (`returned`, `total_available`, `limit`, `ordered_by` = `sale_date DESC`, `oldest_returned`, `note`) — page with `next_page_params` (Process step 6). Rows are newest-first.

### `search_external_lease_comps`

| Param | Shape | Notes |
|---|---|---|
| `city`, `state`, `zip` | str | same as sale. |
| `county` | str | same as sale — normalized server-side, one county per call. |
| `property_type` | str | source-platform taxonomy. |
| `min_lease_start_date` / `max_lease_start_date` | str (ISO) | inclusive. |
| `min_leased_sf` / `max_leased_sf` | int | inclusive. The space the tenant **leased** (`leased_sf`) — this is what a broker's size range means for a lease comp. `build_mcp_params` maps `size_range` here for leases. Never send a lease size range as `min/max_building_sf`: `building_sf` is the building footprint and is empty on most external lease rows, so that filter returns ~0 (lee#469). The Worker still accepts the old names as aliases for `leased_sf`. |
| `min_base_rent` / `max_base_rent` | float | $/SF/yr. |
| `min_lease_term_months` / `max_lease_term_months` | int | inclusive. |
| `tenant_industry` | str | exact match. |
| `limit` | int | default 50, max 200. |

Response: `{"rows": [...], "freshness": "..."}` with all typed lease columns plus `external_id` (no `raw_fields_json` on search rows as of Worker 0.53.1); `empty_result` when `rows` is empty (same shape as sale; the units are `sf`, `usd` for rent, `days`, `months`); `truncated` as on sale, with `ordered_by` = `lease_start_date DESC` and the cursor applied to `max_lease_start_date`.

### `get_external_comp_detail`

| Param | Shape | Notes |
|---|---|---|
| `external_id` | str | preferred. |
| `external_property_id` | str | alternate. |

Response: `{"row": {...}}` with all typed columns AND `raw_fields` (parsed JSON of the unpromoted external columns). Use after a search to drill into one row.

## Geography registry (V1)

`"RDU MSA"` (and aliases `"RDU"`, `"Triangle"`, `"Raleigh-Durham"`) resolves to its seven counties — `{Wake, Durham, Orange, Chatham, Johnston, Franklin, Granville}` — and is fetched exactly like a county ask: `build_mcp_params` emits **one MCP call per county** carrying the typed `county` param (`state="NC"`, no `city`), the Worker filters server-side, and `apply_post_filters` runs only as the G26 stale-connector guard (Process step 7). Until 1.39.1 this was ONE statewide call at `limit: 200` (newest first) post-filtered to the whitelist in Python, so the cap bound on the whole NC book before the county filter ran and 22-58% of RDU comps (by type) never reached the broker — silently, because a 200-row list looks complete (gi-plugins#158). RDU is also the applied default when a broker names no geography, so this was the common path.

For `{"cities": [...]}`, the skill calls the MCP once per city (each MCP query expects a single exact-match `city`) and unions the results. Pass the cities verbatim — the external platform stores them as title case (e.g. `"Raleigh"`, `"Garner"`, `"Cary"`).

Sub-regional broker shorthand (e.g. "Garner / South Raleigh", "North Hills") is NOT enriched in V1. Parse the cities explicitly with the broker (rule #3) and pass `geography={"cities": [...]}`.

### County asks go server-side (lee#496)

A request that names one or more **counties** — "retail leases in Brunswick County", "anything in New Hanover and Brunswick", "Wake and Durham only" — maps to `geography={"counties": [...]}`. Do **not** enumerate the county's cities: `build_mcp_params` issues one MCP call per county carrying the typed `county` param, and the Worker filters server-side.

Pass the broker's spelling **verbatim**. The two comp books spell counties oppositely (the external mirror stores `Brunswick`, the internal Dealius mirror stores `Brunswick County`); the Worker normalizes both sides, so either form matches either book. Never "helpfully" add or strip the word County.

Why this exists: on 2026-08-25 a broker asking for retail leases around Brunswick County got four separate zero-results because the skill had no county shape — it enumerated the four southwest beach towns, which genuinely hold no retail leases, while every Brunswick retail lease we hold sits in Leland, Shallotte or Southport. Each individual zero was correct; the county-level answer was wrong.

`post_filter_counties` is `None` on this path — there is nothing to post-filter. (On the RDU path it carries the whitelist as the stale-connector guard; see Process step 7.)

### Rows with no county

The external platform occasionally ships rows with no county (265 NC rows on 2026-08-25 — 254 sale, all from one early industrial/flex export with no county column, and 11 lease). A `county` filter cannot match a blank, so since Worker 0.53.0 the Worker derives the county **geometrically** from the geocode it already holds for every one of those rows (point-in-polygon over the NC county boundaries, stored in its own table that ingest never rewrites, the same mechanism the internal book uses) and the typed search tools match through it. The derived value is a match key only: such a row comes back with `county` still blank — never fill it in for display, and never treat a blank county on a county-filtered call as an error. A row with no geocode at all stays unreachable by a county ask; if a broker asks about coverage, say that plainly rather than guessing. The old three-way "null-county strategy" dialog (infer / skip the filter / drop) is gone with the post-filter it belonged to; do not re-ask it.

## Source-platform terminology check-in

Broker shorthand → source-platform taxonomy mappings worth knowing (cached from the retired platform-SOP SOP, last verified 2026-05-07):

- "Raleigh-Durham" / "Triangle" / "RDU" → `named_market: "RDU MSA"` → one server-side `county` call per RDU county (see Geography registry).
- "industrial" → `property_type: "Industrial"`.
- "warehouse" → ambiguous; the external platform's `Secondary Type` carries Warehouse/Distribution/Light Manufacturing etc. — but the typed MCP tools do NOT expose `Secondary Type` as a filter. Ask the broker to confirm `property_type: "Industrial"` and note "warehouse" in `notes`; post-filtering by secondary type is V1.1+.
- "IOS" (industrial outdoor storage) → the external platform has no clean tag. Confirmed with the broker. Suggest `property_type: "Industrial"` or `"Flex"` and surface in the email that this is the closest proxy.
- "flex" → `property_type: "Flex"`.
- "office" → `property_type: "Office"`.
- "medical" / "medical office" → `property_type: "Medical"` (lease) or `"Health Care"` (sale — the external platform's sale taxonomy differs).

When the broker uses a term that isn't in this list, behavioral rule #3 applies: ask, don't guess.

## Schema crib — typed columns the search tools return

The model does not need to memorize the column list, but for ranking and the Markdown table here is what to expect (full list in `column_map.py`):

**Sale (`search_external_sale_comps`):** `external_id`, `property_address`, `property_city`, `property_state`, `property_zip`, `county`, `submarket`, `market`, `external_property_id`, `external_property_url`, `property_type`, `property_secondary_type`, `building_sf`, `year_built`, `sale_price`, `price_per_sf`, `sale_date`, `actual_cap_rate`, `noi`, `percent_leased`, `sale_type`, `sale_conditions`, `days_on_market`, `sale_notes`, `buyer_true_company`, `seller_true_company`, `buyers_broker_company`, `listing_broker_company`, ...

**Lease (`search_external_lease_comps`):** `external_id`, `property_address`, `property_city`, `property_state`, `property_zip`, `county`, `submarket`, `market`, `external_property_id`, `property_type`, `leased_sf` (the leased premises — the lease comp's size; use it for the SF column, ranking, and size stats), `building_sf` (the building footprint, often empty), `lease_start_date`, `lease_term_months`, `lease_expiration_date`, `base_rent`, `rent_type`, `escalations`, `free_rent_months`, `ti_allowance`, `tenant_name`, `tenant_industry`, `floor`, `suite`, `space_type`, ...

Search rows do NOT include `raw_fields_json` (dropped in Worker 0.53.1 — the ~2.3KB/row blob of unpromoted external columns made large results unreadable in the client). A specific row's full record, including that blob, comes from `get_external_comp_detail`.

## Confidentiality

All external-comps queries are scoped server-side by `client_id` (Lee Raleigh's client_id, injected from the broker's authenticated session). The broker only sees rows their firm has ingested. If a broker references a specific comp by `external_id` or address that doesn't appear in results, reply verbatim:

> That comp isn't in the Lee Raleigh external-comps snapshot. It may not have been included in Will's most recent export, or the firm hasn't ingested that asset type yet. Want me to flag it for the next snapshot?

Do not speculate further.

## Output — deliverable shapes

v1 always produces both:

### Markdown table (inline in chat)

`markdown_table(top, tagged_under_contract, tagged_sublet, tagged_rent_undisclosed, validated)` returns one string with these blocks (only blocks with rows appear):

- **Main ranked table** (top 7-10). Sale columns: `# | Address | City | County | SF | Sale Price | $/SF | Sale Date | YB | Type | Submarket | Notes`. Lease columns: `# | Address | City | County | SF | Rent ($/SF) | Type | Term | Tenant | Signed | Notes`.
- **Under Contract** sub-table (sale only, if any).
- **Sublet** sub-table (lease only, if any).
- **Rent not disclosed** sub-table (lease only, if any — activity signal only).
- **Quick read** paragraph below: PSF range, term outliers, NNN-vs-MG split (lease), portfolio-allocated outliers (sale).

### Excel (`output_format = "excel"` implicit)

`format_excel` writes a 3-sheet workbook. Layout is frozen. Do not parameterize beyond what the helper signature exposes.

**Excel filename rule (load-bearing — do not skip).** The workbook is written to a tiny constant filename, `c.xlsx`, in the current working directory. You do not choose the name — `safe_xlsx_name` forces `c.xlsx` (enumerating `c1.xlsx`, `c2.xlsx`, ... if you produce more than one in a session) no matter what `xlsx_path` you pass. `format_excel` returns the name actually written; use that when you reference the file to the broker, and tell them they can rename it.

- **Never create a subfolder** (`os.makedirs`, nested paths). The descriptive title lives on the Sheet 1 tab name; the file on disk stays a tiny stub.
- **Why:** brokers run this in Cowork on Windows, where output lands in a per-session directory that runs **~200 characters deep** (`C:\Users\<user>\AppData\Roaming\Claude\local-agent-mode-sessions\<session-id>\...\outputs\` — the session-id slug is long). Excel refuses to *open* any workbook whose full path exceeds **218 characters** (stricter than Windows' own 260 limit), throwing *"the file path is too long."* The file saves fine; it just won't open. With ~200 chars already spent by the fixed session dir, a descriptive name like `comps-industrial-2026-05-28.xlsx` (33 chars) tips past 218; `c.xlsx` (6) fits. The session dir is Cowork's and the file must land there, so the **filename is the only lever** — which is why it's forced to the shortest stable stub. (The broker, or Cowork on request, can rename it afterward.)

- **Sheet 1: `"{Asset Title} {Geography} Comps"`** (e.g., `"Industrial Sale RDU MSA Comps"`, `"Retail Lease Raleigh Comps"`).
  - Dark blue header fill (matches internal-comps), white bold; frozen panes; autofilter.
  - Color scale (red → yellow → green) on the rate column: `price_per_sf` for sale, `base_rent` for lease.
  - Full filtered row set (not just the top N — brokers want the working file).
- **Sheet 2: `"Summary"`** — count, avg/median/min/max rate, avg/median size.
- **Sheet 3: `"Methodology"`** — pulled_for, pull_date, source (`"External weekly snapshot via lee-raleigh-mcp"`), geography, property_types, size_range, date_window, applied_defaults, warnings, applied_filters, last_sync, caveat.

### PDF — deferred to v1.1

Not produced in v1. PDF requires a `query_id` returned by a `read_query`-style MCP call, which external-comps does not have. The fix is a new `cache_external_rows` MCP tool on lee-raleigh-mcp; until that ships, the skill cannot reach `render_comps_pdf`. If the broker asks for PDF, surface the Process step 4 deferral message.

## Email draft

`draft_email(filtered_rows, top, validated, xlsx_path, applied_defaults, warnings, applied_filters)` returns `{subject, body}`. The body always surfaces:

- Result count and a one-line stats summary (mirror of Sheet 2).
- Any defaults `validate_request` applied — broker should be able to push back.
- Any warnings (e.g., size range not specified).
- Any post-filters applied (e.g., "dropped 4 rows outside Wake/Durham").
- If the count is below `target_count`: a single line asking which dimension to widen (size, date, geography, property-type subset). Broker drives expansion via reply — model never auto-widens.
- The confidentiality response template if a referenced comp wasn't found.

The model sends via the broker's connected email tool. The helper does not send.

## Feedback step

After the broker confirms the deliverable, ask three short questions:

1. Rating 1-5 — did this save you time vs. doing it yourself?
2. What worked?
3. What didn't?

Pass to `format_feedback(...)` which returns a structured payload. The model then:

- Tries the Gmail or Outlook MCP send tool if available, to `david@groundedintelligence.io`.
- Falls back to writing `fallback_content` to `feedback-{YYYY-MM-DD}.md` next to the Excel.

Keep the questions short. Long questionnaires get skipped.

## Success criteria

Per-request orchestration code should be well under 1K characters — basically `validate → confirm → build_mcp_params → [invoke MCP, page on truncated per the step-6 algorithm — never window-slice, merge_rows] → apply_post_filters (guard) → rank → format_excel → markdown_table → draft_email → format_feedback`. No expansion loop; below-target results trigger a broker ask in the email, not a re-query.

If you find yourself regenerating openpyxl formatting, hand-writing date math, or reconstructing the county whitelist, **stop**. Call the helper.

## Files

- `SKILL.md` — this file.
- `helpers.py` — atomic helpers (validate, build_mcp_params, post-filter, rank, format_excel, markdown_table, draft_email, format_feedback). None call MCP — the model has MCP access; the sandbox doesn't.
- `lee_logo.png` — bundled with the skill; used by `format_excel` (logo at the top of the main comps sheet). This is a byte-identical copy of the canonical logo in the `lee-branding` skill; each in-session skill carries its own copy because the Cowork sandbox has no outbound network access at runtime and cannot fetch the logo from the server (gotcha registry G17). Keep it in sync with `skills/lee-branding/lee_logo.png`.

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
