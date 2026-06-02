---
name: internal-and-external-comps
description: The DEFAULT comps skill for Lee & Associates — pull a unified "all comps" set covering BOTH internal Dealius AND external CoStar in one deliverable. Use whenever a broker asks for comps WITHOUT specifying internal or external (e.g. "pull industrial sale comps in Garner, 2yr", "any retail comps in Raleigh past year"). Runs both queries in parallel, normalizes both sources into one table tagged by Source (Internal — Dealius / External — CoStar), and produces one combined chat table, one Excel (an "All Comps" sheet plus per-source detail sheets), and one Lee-branded combined PDF. Keeps both rows when a property appears in both sources (no dedup). Handles sale and lease. Only defer to the separate internal-comps / external-comps skills when the broker explicitly asks for internal-only or external-only.
---

# Internal-and-External Comps (Lee & Associates) — the unified "all comps" default

Pull a combined internal (Dealius) + external (CoStar) comp set and produce ONE deliverable:
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
- "external comps" / "CoStar" → use the `external-comps` skill.
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
   - External: build params with `external.build_mcp_params(validated)` → `(tool_name, params)`;
     invoke MCP `search_external_sale_comps` or `search_external_lease_comps`. Response is
     `{"rows": [...], "freshness": "..."}`.
   - **Surface BOTH freshness lines verbatim as the first two lines of your reply.** They are
     not optional and must never be omitted or rephrased — one for Dealius, one for the CoStar
     snapshot.
   - If one source errors or returns 0 rows, deliver the other with a clear note (e.g.
     "External returned 0 — showing internal only"). Never silently drop a source.
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
     external_native=external_rows, validated=validated, xlsx_path=...)`. **Set `xlsx_path` to a
     short, flat filename — `comps-all-<asset>-<YYYY-MM-DD>.xlsx` — written to the working
     directory. No subfolders, no long names. Load-bearing for Windows brokers.**
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
5. **W1 — lease size caveat.** For external (CoStar) lease rows, "Leased SF" reflects building
   size, not leased area. The combined Excel/table surfaces this footnote automatically when an
   external lease row is present; don't strip it.

## Output

- One combined chat table (Source column first).
- One Excel: an **All Comps** sheet (core columns, Source first) plus **Internal (Dealius)** and
  **External (CoStar)** detail sheets preserving each source's native columns.
- One Lee-branded combined PDF rendered via the `unified` template.
- A draft email reply and a feedback capture.

## Don't

- Don't dedup or collapse rows across sources.
- Don't re-rank across sources in v1 (sort is most-recent-Date first).
- Don't omit either freshness line.
- Don't apply this skill when the broker explicitly asked for internal-only or external-only.
