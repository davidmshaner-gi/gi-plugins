---
name: internal-and-external-comps
description: The DEFAULT comps skill for Lee & Associates — pull a unified "all comps" set covering BOTH internal Dealius AND external in one deliverable. Use whenever a broker asks for comps WITHOUT specifying internal or external (e.g. "pull industrial sale comps in Garner, 2yr", "any retail comps in Raleigh past year"). Runs both queries in parallel, normalizes both sources into one table tagged by Source (Internal — Dealius / External), and produces one combined chat table, one Excel (an "All Comps" sheet plus per-source detail sheets), and one Lee-branded combined PDF. Keeps both rows when a property appears in both sources (no dedup). Handles sale and lease. Only defer to the separate internal-comps / external-comps skills when the broker explicitly asks for internal-only or external-only.
---

# Internal-and-External Comps (Lee & Associates) — the unified "all comps" default

Pull a combined internal (Dealius) + external comp set and produce ONE deliverable:
a combined chat table, a combined Excel, and a Lee-branded combined PDF. This is what a
broker gets by default when they ask for "comps" without qualifying the source — they want
the best picture, not two separate runs.

## When to use

Any comps request that does **not** explicitly say internal-only or external-only. The
phrasing is open — what matters is the intent.

- "Pull industrial sale comps in Raleigh-Durham, 2K-30K sqft, past 4 months."
- "any retail comps in raleigh past year?"
- "what's leasing in north hills"
- A forwarded broker email asking for comps.

**Defer to the single-source skills only when the broker is explicit:**
- "internal comps" / "Dealius" / "our data" → use the `internal-comps` skill.
- "external comps" → use the `external-comps` skill.
- Pure analysis on comps already pasted into chat (no DB lookup) → neither skill.

## Architecture

This skill is a thin orchestrator. It reuses the sibling skills' parse/validate/query logic
via `load_sibling()` and adds only the combine + unified-output layer. Both source queries
run in parallel; there is no server-side merge. Helpers run in the Cowork sandbox and have
NO MCP access — the model invokes every MCP tool directly.

```python
from helpers import load_sibling, to_core, combine, unified_markdown_table, format_unified_excel, SOURCE_INTERNAL, SOURCE_EXTERNAL
internal = load_sibling("internal-comps")
external = load_sibling("external-comps")
```

## Process

1. **Parse** the broker's request into a request dict (same shape the sibling skills expect:
   asset_type, transaction_type, geography, size_range, date_window, …).
2. **Validate.** Call `internal.validate_request(parsed)`. If `missing_required` is
   non-empty, draft a clarifying reply and stop — do NOT query. (Internal and external share
   the same required fields; validating once is sufficient.)
3. **Pick the deliverable format.** Reuse the internal-comps Excel / PDF / Both dialog. If
   the request names a format ("PDF", "BPO", "Excel", "both"), set it and skip the prompt.
   Otherwise ask once, then wait for the broker's choice.
4. **Run BOTH queries in parallel:**
   - Internal: build SQL with `internal.build_sql(validated)`, run MCP `read_query`. Response
     is `{"rows": [...], "query_id": "...", "freshness": "..."}`.
   - External: build params with `external.build_mcp_params(validated)` →
     `{"tool_name", "params_list", ...}`; invoke MCP `search_external_sale_comps` or
     `search_external_lease_comps` once per entry in `params_list` (one per county for a
     `counties` ask and for the RDU default, one per city for `cities`; issue them in parallel in
     one turn) and union the rows with `external.merge_rows(*pages)`. Response is
     `{"rows": [...], "freshness": "..."}`. Then `external.apply_post_filters(rows, validated,
     post_filter_counties, keep_blank_county=True)`: a no-op on `counties`/`cities`; on the RDU
     default it is the G26 stale-connector guard — a "dropped N rows outside […]" entry means the
     connector stripped the `county` param (tell the broker to "Refresh tools list").
   - **When an external call carries `truncated`** (Worker 0.53.0, gi-plugins#158) it stopped at
     the 200-row cap with more rows behind it — the rows are the NEWEST only. Page it exactly as
     the `external-comps` skill does (Process step 6 there): `external.next_page_params(params,
     response)` until it returns `None` or `external.MAX_PAGES` (5) pages, then put one
     `external.truncation_note(retrieved, total_available, pages, label=<county or city>)` per
     truncated params dict in the note / Methodology (`total_available` from that dict's FIRST
     page; `retrieved` its de-duplicated count) so the broker knows how much of the matching book
     they are looking at. Never present a clipped
     external leg as the complete external picture.
   - **County asks flow through both legs automatically (lee#496).** A `geography={"counties": [...]}` request needs no handling here: `internal.build_sql` emits a `county_normalized` predicate against the safe views and `external.build_mcp_params` emits one call per county carrying the typed `county` param. Pass the broker's spelling verbatim to both — each side normalizes, and the two comp books store opposite spellings ("Brunswick County" internal, "Brunswick" external).
   - **Surface BOTH freshness lines verbatim as the first two lines of your reply.** They are
     not optional and must never be omitted or rephrased — one for Dealius, one for the external platform
     snapshot.
   - If one source errors or returns 0 rows, deliver the other with a clear note (e.g.
     "External returned 0 — showing internal only"). Never silently drop a source.
   - **When external returns 0 rows it also returns `empty_result`** (Worker 0.42.0,
     lee-and-associates#463): `tightest` names the filter that cut the last candidates and
     `nearest[]` holds up to 3 comps just past that bound with `miss.by` / `miss.unit`. Put
     that in the note instead of a bare zero — "External: 0 in the 100k–200k band; the 200k
     ceiling cut it, nearest is 3241 Pennington Dr at 213,508 sf (13,508 over). Lift it?" —
     and let the broker decide whether to re-run wider. Never list a near miss as a match.
     If BOTH sources return 0, the reply is that explanation plus the offer to relax; no
     empty Excel or PDF.
5. **Normalize + combine.**
   ```python
   internal_core = [to_core(r, SOURCE_INTERNAL, validated["transaction_type"]) for r in internal_rows]
   external_core = [to_core(r, SOURCE_EXTERNAL, validated["transaction_type"]) for r in external_rows]
   core_rows = combine(internal_core, external_core, validated["transaction_type"])
   ```
   `combine` concatenates and sorts most-recent-Date first. There is **no dedup** — a property
   in both sources stays as two rows, each tagged by Source.
6. **Render the deliverable(s):**
   - **Excel** (if chosen): `format_unified_excel(core_rows, internal_native=internal_rows,
     external_native=external_rows, validated=validated, xlsx_path=...)`. **The filename is forced
     to a tiny constant stub (`c.xlsx`, enumerating `c1.xlsx`/`c2.xlsx` on repeat) by
     the shared `safe_xlsx_name` helper regardless of what you pass as `xlsx_path`; the call returns
     the name actually written — use it when you reference the file to the broker, and tell them
     they can rename it. Load-bearing for Windows brokers (Excel won't open a path >218 chars, and
     Cowork's session dir already eats ~200).**
   - **Chat table:** `unified_markdown_table(core_rows, validated)`.
   - **PDF** (if chosen): cache the combined rows and render one branded combined PDF:
     - MCP `cache_external_rows` with `{rows: core_rows, comp_type: validated["transaction_type"]}`
       → `{query_id}`.
     - MCP `render_comps_pdf` with `{query_id, validated, template_name: "unified", output_format}`.
       The `validated` object MUST carry `transaction_type` (`"sale"` / `"lease"`) — the server
       reads it to compute sale-vs-lease summary stats. Returns a signed `pdf_url` (≈1-hour
       expiry) or a `bytes` fallback (write to `/tmp` and treat as the deliverable).
7. **Draft the email reply + feedback capture.** Reuse the external-comps email/feedback
   scaffolding; note BOTH sources and the per-source counts in the body.

## Behavioral rules

1. **Ask only for what's missing.** Never re-ask anything the broker already provided.
2. **Confirm the resolved query before querying.** State the asset type, transaction type,
   geography, size, and date window, plus "pulling both internal and external," and wait for go.
3. **One transaction type per request.** If the broker mixes sale and lease, ask them to split
   into two runs (same rule as the single-source skills).
4. **Source tagging is non-negotiable.** Every row, in every output, shows its Source.
5. **External lease "Leased SF" is the leased premises, never the building.** External lease
   rows carry `leased_sf` (the space the tenant took; lee#469) and the "Leased SF" column shows
   it. `building_sf` is the building footprint and is never shown as Leased SF (gi-plugins#105);
   a row without `leased_sf` renders blank. Internal (Dealius) lease rows keep `space_sf`.
   When the external pull takes a size range for a lease, send it as `min/max_leased_sf`.

## Output

- One combined chat table (Source column first).
- One Excel: an **All Comps** sheet (core columns, Source first) plus **Internal (Dealius)** and
  **External** detail sheets preserving each source's native columns.
- One Lee-branded combined PDF rendered via the `unified` template.
- A draft email reply and a feedback capture.

## Don't

- Don't dedup or collapse rows across sources.
- Don't re-rank across sources in v1 (sort is most-recent-Date first).
- Don't omit either freshness line.
- Don't apply this skill when the broker explicitly asked for internal-only or external-only.

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
