---
name: internal-comps
description: Pull internal lease comps from the Dealius mirror for Lee & Associates brokers. Broker pastes a free-form comp request into chat; skill parses, queries the lease_comps_safe MCP, and produces a formatted Excel deliverable plus a draft email reply. Confidentiality enforced server-side. Always Excel — no email-summary branch.
---

# Internal Comps (Lee & Associates / Dealius)

Pull internal lease comps from the Dealius mirror MCP and produce a formatted Excel deliverable, a draft email reply, and a feedback capture.

## When to use

Anything that asks for internal lease (or sale) comps from the Dealius mirror. The phrasing is open — what matters is the intent, not the form.

The broker might:

- Paraphrase: "Pull internal lease comps for industrial in Raleigh-Durham, 2K-30K sqft, past 4 months."
- Forward another broker's email verbatim.
- Ask in shorthand: "any retail comps in raleigh past year?", "comps on medical office 1.5-4K?", "what's leasing in north hills"
- Follow up on a previous pull: "can you widen the size range?", "add Class B", "rerun with 6 months instead of 4."
- Reference a specific comp by ID or address.

Pattern: the request names some combination of asset type, geography, size, date window, or transaction type, and is asking the model to retrieve actual comp records from the internal database. That's the trigger — phrasing is not.

**Don't apply this skill to:**

- Questions about the mirror, the schema, or how the skill itself works.
- External comp requests (CoStar / RealNex outside Lee's Dealius) — that's a different skill.
- Pure analysis on comps the broker has already pasted into chat (no DB lookup needed).

## Process

The skill orchestrates pre-baked helpers in `helpers.py`. **Do not regenerate Excel formatting, SQL composition, or email scaffolding inline.** Import and call.

1. **Parse** the broker's paste into a request dict (see Input Contract below).
2. Call `validate_request(parsed)` → applies defaults, lists missing/warnings.
3. If `missing_required` is non-empty: draft a clarifying reply, stop. Do not run SQL.
4. Call `build_sql(validated)` → SQL string against `lease_comps_safe` or `sale_comps_safe`.
5. Run the SQL via MCP `read_query`. (The MCP tool, not a helper — helpers run in the Cowork sandbox and have no MCP access.)
6. Call `format_excel(rows, validated, output_path, ...)` → writes the workbook.
7. Call `draft_email(rows, validated, xlsx_path, ...)` → returns subject + body. If the result count is below `target_count`, the email asks the broker which dimension (size, date, geography) to widen. **No auto-expansion** — the broker drives.
8. After the broker confirms / closes the loop: ask the three feedback questions, call `format_feedback(...)`, then send via connected email tool (Gmail / Outlook MCP) or write the fallback file.

## Input Contract

The dict you pass to `validate_request`. Three keys are load-bearing; everything else is open-shaped — the helpers tolerate missing optional keys and ignore unknown keys.

| Key | Required | Shape |
|---|---|---|
| `asset_type` | yes | `"industrial"` \| `"flex"` \| `"office"` \| `"retail"` \| `"medical_office"` \| `"lab"` \| `"land"` |
| `transaction_type` | yes | `"lease"` \| `"sale"` |
| `geography` | no | `{"named_market": str}` or `{"cities": [str, ...]}` or `{"anchor": str, "radius_mi": int}` |
| `size_range` | no | `{"min_sf": int, "max_sf": int}` |
| `date_window` | no | `{"lookback_months": int}` or `{"from": "YYYY-MM-DD", "to": "YYYY-MM-DD"}` |
| `target_count` | no | int (default 8) |
| `min_price` | no | int — sale only |
| `min_acres` | no | float — minimum site acreage. Sparse on lease (~16% populated); applies as a hard filter so use sparingly there. Dense on sale (~68%). |
| `notes` | no | str — broker preferences not captured by other keys; `draft_email` reads it back, `build_sql` ignores it |

Stuff anything you parsed but couldn't slot cleanly into `notes`. The helpers won't choke on extras.

## Defaults applied by `validate_request`

| Field missing | Default applied | Surfaced as |
|---|---|---|
| `geography` | `{"named_market": "RDU MSA"}` | applied default |
| `date_window` | `{"lookback_months": 12}` | applied default |
| `target_count` | `8` | applied default |
| `min_price` (sale only) | `500000` | applied default |
| `size_range` | none | warning (not blocking) |

Every applied default appears in the email body so the broker can push back.

## Schema crib (`lease_comps_safe` view)

The model does not need to memorize the 365-column schema. The helpers select a fixed canonical column set. The boundaries that matter:

- **Rate column:** `effective_rate` is the only canonical rate column on `lease_comps_safe`. Use it directly. Don't mention or look for any other rate-style columns — they aren't in the view.
- **Size column:** `space_sf` preferred; fall back to `square_feet_sold`.
- **Dates:** `lease_execution` and `lease_commencement` are stored as MM/DD/YYYY text. Helpers handle conversion.
- **Always include:** `link_to_comp_profile` (the Dealius URL).

### Property type taxonomy

| `asset_type` value | SQL `property_type IN (...)` |
|---|---|
| `"industrial"` | `'Industrial', 'Flex Warehouse', '100% Warehouse'` |
| `"flex"` | `'Flex Warehouse'` (subset of industrial — use when broker says "flex" specifically) |
| `"office"` | `'Office'` |
| `"retail"` | `'Retail'` |
| `"medical_office"` | `'Medcial Office'` (sic — Dealius typo) |
| `"lab"` | `'Lab Space'` |
| `"land"` | `'Land'` |

**Industrial outdoor storage / IOS / yard deals:** there is no clean SQL filter — confirmed by the broker. The data fields that would identify them (zoning, yard_sf, yard_type, comp name keywords, notes) are essentially unpopulated. Brokers tag these mentally. If a request mentions IOS, route as `flex` with a `min_acres` filter (broker's recommendation) and surface in the email that this is the closest proxy, not an exact match.

### Geography registry (V1)

`"RDU MSA"` (and aliases `"RDU"`, `"Triangle"`, `"Raleigh-Durham"`) resolves to a hand-curated city list inside the helpers. **Sub-regional broker shorthand is not enriched in V1** (data cleanup is deferred to a later SOW). For phrasings like "Garner / South Raleigh," parse the cities explicitly and pass `geography={"cities": ["Garner", "Raleigh"]}` — don't try to register a sub-market. Anything that doesn't match a registered named market falls back to RDU MSA with a warning.

## Sale comps

The mirror exposes both `lease_comps_safe` and `sale_comps_safe`. `build_sql` branches on `transaction_type`:

- **lease** → `lease_comps_safe`, date column `lease_execution`, size filter on `COALESCE(space_sf, square_feet_sold)`, no price floor.
- **sale** → `sale_comps_safe`, date column `actual_close_date`, size filter on `COALESCE(square_feet_sold, building_size)`, `sale_price >= min_price` (default $500K junk filter).

Sale uses a different display layout (`DISPLAY_COLUMNS_SALE`) and stat shape (sale price, $/SF, total volume) — both selected automatically by `format_excel` based on `validated["transaction_type"]`. Sheet name inserts `Sale` between asset and geography (e.g., `"Industrial Sale Garner, Raleigh Comps"`).

## Confidentiality

Confidential and NDA rows are filtered server-side at the `lease_comps_safe` view. The model never sees them.

If a broker references a specific comp by ID or address that doesn't appear in results, reply verbatim:

> That comp is confidential and not retrievable through this channel.

Do not speculate about deletion, alternate IDs, broker error, or any other reason. The view filter is the explanation; saying anything else is hallucination.

## Output — frozen layout

`format_excel` writes a three-sheet workbook. Layout is frozen. Do not parameterize beyond what the helper signature exposes.

- **Sheet 1: `"{Asset Title} {Geography} Comps"`** (e.g., `"Industrial RDU MSA Comps"`, `"Retail Raleigh Comps"`).
  - Dark blue header fill, white bold; frozen panes; autofilter.
  - Color scale (red → yellow → green) on `effective_rate` column.
  - 23-column canonical layout matching `internal-comps-db/cowork-runs/2026-04-29_industrial-RDU-2k-30k-4mo/build_comps.py`.
- **Sheet 2: `"Summary"`** — count, avg/median/min/max effective $/SF, avg/median leased SF.
- **Sheet 3: `"Methodology"`** — pulled_for, pull_date, source, geography, property_types, size_range, date_window, rate_convention, applied_defaults, warnings, last_sync, caveat.

Always Excel. There is no `<3 results → email summary` branch and no `0 results → no-comps email` branch in the deliverable. The `draft_email` reply describes the count in prose, and asks the broker how to widen if the count is below target; the Excel itself is always attached (even if empty, with a methodology sheet explaining the empty result).

## Email draft

`draft_email` returns `{subject, body}`. The body always surfaces:

- Result count and a one-line stats summary (mirror of Sheet 2).
- Any defaults `validate_request` applied — broker should be able to push back.
- Any warnings (e.g., size range not specified).
- If the count is below `target_count`: a single line asking the broker which dimension to widen (size, date, geography). The broker drives expansion via reply — the model never auto-widens.
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

The Python the model writes per request should be small. Cowork's unprompted runs were 10K-41K characters of generated Python per query (the 41K was a *simpler* question, expanding 4× as it reasoned its way through the same problem). With this skill, per-request orchestration code should be well under 1K characters — basically `validate → build_sql → read_query → format_excel → draft_email → format_feedback`. No expansion loop; below-target results trigger a broker ask in the email, not a re-query.

If you find yourself regenerating openpyxl formatting, hand-writing date math, or reconstructing the city list, **stop**. Call the helper. The flexibility tradeoff was deliberate: the dict is open-shaped so weird broker phrasings still slot in, but the deterministic surface (SQL, Excel, email scaffolding) is locked.

## Files

- `SKILL.md` — this file.
- `helpers.py` — atomic helpers (validate, build_sql, format_excel, draft_email, format_feedback).
- `lee_logo.png` — bundled with the skill; used by `format_excel`.

Lives next to the skill on disk but **not in the bundle**:

- `regression-tests.md` — wild query test set used to verify the skill end-to-end. Held outside SKILL.md so Cowork doesn't pattern-match worked examples.
- `internal-comp-skill-design-notes.md`, `process-table-internal-comps.md`, `learnings.md` — design references.
