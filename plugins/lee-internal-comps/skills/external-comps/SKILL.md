---
name: external-comps
description: Pull external lease or sale comps for a Lee & Associates broker. Broker pastes a free-form comp request into chat; skill parses, calls the typed external-comps MCP tools (search_external_sale_comps / search_external_lease_comps / get_external_comp_detail), and produces a Markdown table in chat plus an Excel deliverable and draft email reply. PDF deferred to v1.1.
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
- Reference a specific comp by external_id or CoStar Property ID.

Pattern: the request names some combination of asset type, geography, size, date window, or transaction type AND points to external data (or asks generically and the broker confirms external when asked). That's the trigger.

**Don't apply this skill to:**

- Questions about the mirror, the schema, or how the skill itself works.
- **Internal** (Dealius) comp requests — that's the `internal-comps` skill. Internal is the firm's own data; external is the weekly external-comps snapshot.
- **Unqualified** comp requests (broker didn't say internal or external) — that's the default `internal-and-external-comps` skill, which pulls both. Use this skill only when the broker explicitly asks for external/CoStar.
- Pure analysis on comps the broker has already pasted into chat (no DB lookup needed).
- Requests for a Lee-branded PDF — surface the deferral message (see Process step 4).

## Process

The skill orchestrates pre-baked helpers in `helpers.py`. **Do not regenerate Excel formatting, MCP param mapping, ranking, or email scaffolding inline.** Import and call.

1. **Parse** the broker's paste into a request dict (see Input Contract below).
2. Call `validate_request(parsed)` → applies defaults, lists missing/warnings.
3. If `missing_required` is non-empty: draft a clarifying reply, stop. Do not call MCP.
4. **Output format handling.** v1 always produces Markdown + Excel. If the broker explicitly asks for a PDF, reply once with the v1.1 deferral message:

   > Lee-branded PDF for external comps is coming in the next update (depends on a small server-side change). For now I can deliver the Markdown table + an Excel — that work for you?

   Then proceed.

5. Call `build_mcp_params(validated)` → `(tool_name, params_dict)`. `tool_name` is `"search_external_sale_comps"` or `"search_external_lease_comps"` depending on `transaction_type`. **Helpers do NOT call MCP.** The model invokes the MCP tool directly.
6. Invoke the MCP tool with the params dict. The response shape is `{"rows": [...], "freshness": "..."}` (a JSON-stringified text block from the MCP server — parse it). Each row contains all typed CoStar columns plus `external_id` and `raw_fields_json`. **If `freshness` is present, emit it verbatim as the very first line of your chat reply to the broker** (it looks like `ℹ️ External sale comps: ingested 2026-05-16 17:12 UTC (10 days ago)`). The freshness line tells the broker how current the external snapshot is — it is not optional, never omit or rephrase it.
7. **Handle the county filter strategy.** Call `null_county_rate(rows)` → `(null_count, total_count, share)`. If `share > NULL_COUNTY_DIALOG_THRESHOLD` (0.20) AND `post_filter_counties` is non-None, surface the 3-strategy dialog (see "Null-county strategy dialog" in the Geography registry section). Wait for the broker's choice. Below threshold, default to strategy 1 (silent city-map enrichment). Then call `apply_post_filters(rows, validated, post_filter_counties, city_to_county=<map or None>)` → `(filtered_rows, applied_filters)`. `applied_filters` is a list of human-readable strings describing what was filtered/inferred, surfaced in the email body and Methodology sheet.
8. Call `rank_comps(filtered_rows, validated)` → returns `(top, tagged_under_contract, tagged_sublet, tagged_rent_undisclosed)`. `top` is the ranked sweet-spot list (typically 7-10).
9. Call `format_excel(filtered_rows, validated, xlsx_path, applied_defaults, warnings, applied_filters, last_sync)` → writes a 3-sheet workbook to the sandbox. The full filtered set goes into the Excel, not just the top N — brokers want the working file with everything. **The filename is forced to a tiny constant stub (`c.xlsx`, enumerating `c1.xlsx`/`c2.xlsx` on repeat) by the helper regardless of what you pass as `xlsx_path`; `format_excel` returns the name actually written — use it when you reference the file to the broker, and tell them they can rename it. This is load-bearing for Windows brokers; see the "Excel filename rule" in Output below.**
10. Call `markdown_table(top, tagged_under_contract, tagged_sublet, tagged_rent_undisclosed, validated)` → returns a Markdown string for the chat reply.
11. Call `draft_email(filtered_rows, top, validated, xlsx_path, applied_defaults, warnings, applied_filters)` → returns `{subject, body}`. The body surfaces total filtered count, top-N ranked count, stats summary, applied defaults, warnings, applied filters, and a narrow-or-widen question if the top-N count is below `target_count`. **No auto-expansion** — the broker drives.
12. After the broker confirms / closes the loop: ask the three feedback questions, call `format_feedback(...)`, then send via connected email tool (Gmail / Outlook MCP) or write the fallback file.

## Behavioral rules — follow these closely

Borrowed from the prior external-comps SOP. These compound with the Process steps above.

1. **Aim for around 7-10 best matches as a soft default.** Mention this in your first confirmation. Treat it as guidance, not a rule — defer if the broker wants more, fewer, or all of them.
2. **Ask only for what's missing.** Never re-ask anything the broker already gave you, including in earlier turns.
3. **If the broker uses a term you don't recognize** ("IOS," "the Triangle," internal nicknames, etc.), ask them to describe what it maps to in CoStar terms. Don't translate or guess. This rule applies to broker-internal shorthand, not CoStar's own labels.
4. **Confirm the resolved query back to the broker before you call the MCP.** Wait for explicit "yes" or "go" before executing.
5. **Narrow/loosen is a separate conversation.** When the result count is far from 7-10, propose adjustments — narrowing axes (tighter date, tighter size, smaller geo, property-type subset) or loosening — and let the broker decide. They can override with "show me all of them" or pick a different target count.

## Input Contract

The dict you pass to `validate_request`. `asset_type` and `transaction_type` are load-bearing; everything else is open-shaped — the helpers tolerate missing optional keys and ignore unknown keys.

| Key | Required | Shape |
|---|---|---|
| `asset_type` | yes | `"industrial"` \| `"office"` \| `"retail"` \| `"flex"` \| `"medical"` \| `"multifamily"` \| `"student"` \| `"land"` \| `"hospitality"` \| `"health_care"` \| `"specialty"` |
| `transaction_type` | yes | `"lease"` \| `"sale"` |
| `geography` | no | `{"named_market": str}` or `{"cities": [str, ...]}` |
| `size_range` | no | `{"min_sf": int, "max_sf": int}` |
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
| `property_type` | str | CoStar taxonomy (`"Industrial"`, `"Office"`, ...). |
| `min_sale_date` / `max_sale_date` | str (ISO `YYYY-MM-DD`) | inclusive. |
| `min_building_sf` / `max_building_sf` | int | inclusive. |
| `min_sale_price` / `max_sale_price` | int | whole dollars. |
| `min_cap_rate` / `max_cap_rate` | float | `0.075` = 7.5%. |
| `limit` | int | default 50, max 200. |

Response: `{"rows": [...]}` with all typed sale columns plus `external_id`, `raw_fields_json`.

### `search_external_lease_comps`

| Param | Shape | Notes |
|---|---|---|
| `city`, `state`, `zip` | str | same as sale. |
| `property_type` | str | CoStar taxonomy. |
| `min_lease_start_date` / `max_lease_start_date` | str (ISO) | inclusive. |
| `min_building_sf` / `max_building_sf` | int | inclusive. |
| `min_base_rent` / `max_base_rent` | float | $/SF/yr. |
| `min_lease_term_months` / `max_lease_term_months` | int | inclusive. |
| `tenant_industry` | str | exact match. |
| `limit` | int | default 50, max 200. |

Response: `{"rows": [...]}` with all typed lease columns plus `external_id`, `raw_fields_json`.

### `get_external_comp_detail`

| Param | Shape | Notes |
|---|---|---|
| `external_id` | str | preferred. |
| `costar_property_id` | str | alternate. |

Response: `{"row": {...}}` with all typed columns AND `raw_fields` (parsed JSON of the unpromoted CoStar columns). Use after a search to drill into one row.

## Geography registry (V1)

`"RDU MSA"` (and aliases `"RDU"`, `"Triangle"`, `"Raleigh-Durham"`) resolves to a county whitelist applied **post-fetch** by `apply_post_filters`: `{Wake, Durham, Orange, Chatham, Johnston, Franklin, Granville}`. The MCP call passes `state="NC"` and no `city`.

For `{"cities": [...]}`, the skill calls the MCP once per city (each MCP query expects a single exact-match `city`) and unions the results. Pass the cities verbatim — CoStar stores them as title case (e.g. `"Raleigh"`, `"Garner"`, `"Cary"`).

Sub-regional broker shorthand (e.g. "Garner / South Raleigh", "North Hills") is NOT enriched in V1. Parse the cities explicitly with the broker (rule #3) and pass `geography={"cities": [...]}`.

### Null-county fallback (city → county map)

The external weekly snapshot occasionally lands with `county` null on some or all rows (depends on which export shape Will pulls — the "Everything" export populates it; leaner exports don't). When `apply_post_filters` runs the RDU county whitelist on rows with null county, it can optionally fall back to a `property_city → county` lookup. The fallback map ships with the skill as `helpers.RDU_CITY_TO_COUNTY` and is mirrored here so brokers can override per-deal:

| County | Cities |
|---|---|
| Wake | Raleigh, Cary, Garner, Apex, Wake Forest, Holly Springs, Morrisville, Knightdale, Rolesville, Wendell, Zebulon, Fuquay-Varina |
| Durham | Durham |
| Orange | Chapel Hill, Carrboro, Hillsborough |
| Chatham | Pittsboro, Siler City |
| Johnston | Smithfield, Clayton, Selma, Benson, Four Oaks |
| Franklin | Louisburg, Youngsville, Bunn |
| Granville | Creedmoor, Oxford, Butner |

If a broker says "treat Chapel Hill as Durham" or names a city not in the map, override by passing a modified dict to `apply_post_filters` for that request. The map is just a default — the broker drives.

### Null-county strategy dialog

When `null_county_rate(rows)` returns a `share` greater than `NULL_COUNTY_DIALOG_THRESHOLD` (default 20%) AND a county filter is requested, the model pauses before calling `apply_post_filters` and surfaces this dialog to the broker:

> Snapshot has {N} of {M} rows with null county ({pct}%). Three options for the RDU filter:
> 1. **Infer county from city** using the RDU map (default — Raleigh→Wake, Durham→Durham, etc.)
> 2. **Skip the county filter** and return all NC rows in your size/date range
> 3. **Drop the null-county rows** (strictest — only keep rows with populated county in the whitelist)
>
> Which?

The broker's choice maps to:
- (1) → `apply_post_filters(rows, validated, post_filter_counties, city_to_county=RDU_CITY_TO_COUNTY)`
- (2) → `apply_post_filters(rows, validated, post_filter_counties=None)`
- (3) → `apply_post_filters(rows, validated, post_filter_counties, city_to_county=None)` (no enrichment — null counties fall out of whitelist)

The chosen strategy is logged in `applied_filters` so the email body and Methodology sheet are auditable. **Remember the choice for the rest of the conversation, scoped to the current geography context.** Don't re-ask on follow-up queries that keep the same `named_market` (e.g. "widen the size range"). A new `named_market`, an explicit `cities` override, or a fresh transaction_type resets the choice — re-evaluate the threshold and ask again if needed.

Below threshold, default to silent enrichment (strategy 1) — don't pause for trivial null counts.

## CoStar terminology check-in

Broker shorthand → CoStar taxonomy mappings worth knowing (cached from the stashed costar-comps SOP, last verified 2026-05-07):

- "Raleigh-Durham" / "Triangle" / "RDU" → `named_market: "RDU MSA"` → county whitelist applied post-fetch.
- "industrial" → `property_type: "Industrial"`.
- "warehouse" → ambiguous; CoStar's `Secondary Type` carries Warehouse/Distribution/Light Manufacturing etc. — but the typed MCP tools do NOT expose `Secondary Type` as a filter. Ask the broker to confirm `property_type: "Industrial"` and note "warehouse" in `notes`; post-filtering by secondary type is V1.1+.
- "IOS" (industrial outdoor storage) → CoStar has no clean tag. Confirmed with the broker. Suggest `property_type: "Industrial"` or `"Flex"` and surface in the email that this is the closest proxy.
- "flex" → `property_type: "Flex"`.
- "office" → `property_type: "Office"`.
- "medical" / "medical office" → `property_type: "Medical"` (lease) or `"Health Care"` (sale — CoStar's sale taxonomy differs).

When the broker uses a term that isn't in this list, behavioral rule #3 applies: ask, don't guess.

## Schema crib — typed columns the search tools return

The model does not need to memorize the column list, but for ranking and the Markdown table here is what to expect (full list in `column_map.py`):

**Sale (`search_external_sale_comps`):** `external_id`, `property_address`, `property_city`, `property_state`, `property_zip`, `county`, `submarket`, `market`, `costar_property_id`, `costar_property_url`, `property_type`, `property_secondary_type`, `building_sf`, `year_built`, `sale_price`, `price_per_sf`, `sale_date`, `actual_cap_rate`, `noi`, `percent_leased`, `sale_type`, `sale_conditions`, `days_on_market`, `sale_notes`, `buyer_true_company`, `seller_true_company`, `buyers_broker_company`, `listing_broker_company`, ...

**Lease (`search_external_lease_comps`):** `external_id`, `property_address`, `property_city`, `property_state`, `property_zip`, `county`, `submarket`, `market`, `costar_property_id`, `property_type`, `building_sf`, `lease_start_date`, `lease_term_months`, `lease_expiration_date`, `base_rent`, `rent_type`, `escalations`, `free_rent_months`, `ti_allowance`, `tenant_name`, `tenant_industry`, `floor`, `suite`, `space_type`, ...

Both shapes also include `raw_fields_json` — a stringified JSON blob of unpromoted CoStar columns. Don't surface it directly to the broker; use `get_external_comp_detail` to inspect a specific row's full record.

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

Per-request orchestration code should be well under 1K characters — basically `validate → confirm → build_mcp_params → [invoke MCP] → post_filter → rank → format_excel → markdown_table → draft_email → format_feedback`. No expansion loop; below-target results trigger a broker ask in the email, not a re-query.

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
