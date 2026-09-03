---
name: internal-comps
description: Pull internal sale or lease comps from the Dealius mirror for Lee & Associates brokers, by city, by county, or across the RDU market. Broker pastes a free-form comp request into chat; skill parses, queries sale_comps_safe or lease_comps_safe via MCP, and produces a formatted Excel and/or PDF deliverable plus a draft email reply. Confidentiality enforced server-side.
---

# Internal Comps (Lee & Associates / Dealius)

Pull internal lease comps from the Dealius mirror MCP and produce a formatted Excel and/or PDF deliverable, a draft email reply, and a feedback capture.

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
- External comp requests (external sources outside Lee's Dealius) — that's a different skill.
- **Unqualified** comp requests (broker didn't say internal or external) — that's the default `internal-and-external-comps` skill, which pulls both. Use this skill only when the broker explicitly asks for internal/Dealius.
- Pure analysis on comps the broker has already pasted into chat (no DB lookup needed).

## Process

The skill orchestrates pre-baked helpers in `helpers.py`. **Do not regenerate Excel formatting, SQL composition, or email scaffolding inline.** Import and call.

1. **Parse** the broker's paste into a request dict (see Input Contract below).
2. Call `validate_request(parsed)` → applies defaults, lists missing/warnings.
3. If `missing_required` is non-empty: draft a clarifying reply, stop. Do not run SQL.
4. **Ask the broker which deliverable to produce.** If the original request explicitly names a format, set `output_format` from that signal and skip to step 5. Format-trigger words map as follows:

   - `"PDF"`, `"BPO"`, `"send as BPO"`, `"client-facing"` → `output_format = "pdf"`
   - `"Excel"`, `"spreadsheet"`, `"working file"` → `output_format = "excel"`
   - `"both"`, `"Excel and PDF"`, `"send both"` → `output_format = "both"`

   Otherwise (no trigger word present) reply once with:

   > Got it — pulling [N] [asset_type] [transaction_type] comps in [region] for the past [X] months. How would you like the deliverable?
   > - **Excel** (working file with all rows + summary stats)
   > - **PDF** (client-facing, Lee-branded, drop into a BPO)
   > - **Both**

   Wait for the broker's reply before continuing. On follow-up requests in the same thread (e.g., "widen the size range"), reuse the previously-chosen format unless the broker overrides.

5. Set `validated["output_format"] = "excel" | "pdf" | "both"` from step 4. (`output_format` is not auto-defaulted — the skill blocks until the broker explicitly chooses.)
6. Call `build_sql(validated)` → SQL string against `lease_comps_safe` or `sale_comps_safe`.
7. Run the SQL via MCP `read_query`. (The MCP tool, not a helper — helpers run in the Cowork sandbox and have no MCP access.) **The response is an object `{"rows": [...], "query_id": "<uuid>", "freshness": "..."}`, not a bare array.** Extract `rows` for downstream helpers and **save `query_id` for `render_comps_pdf`**. If `query_id` is absent (KV write failed server-side), degrade gracefully: deliver Excel-only and inform the broker that the PDF path is temporarily unavailable. **If `freshness` is present, emit it verbatim as the very first line of your chat reply to the broker** (it looks like `ℹ️ Heads up: I'm pulling from Dealius sale comps, which were last updated May 26 (2 days ago). ℹ️` — bookended by `ℹ️`, broker-voice, no UTC timestamps). The freshness line tells the broker how current the comp data is — it is not optional, never omit or rephrase it.
8. Format the deliverable(s):
   - If `output_format` is `"excel"` or `"both"`: call `format_excel(rows, validated, xlsx_path, applied_defaults, warnings, last_sync)` → writes the workbook to the sandbox. **The filename is forced to a tiny constant stub (`c.xlsx`) by the helper regardless of what you pass as `xlsx_path` — `format_excel` returns the actual name it wrote (`c.xlsx`, or `c1.xlsx`/`c2.xlsx` if you produce more than one in a session). Use the returned name when you tell the broker about the file, and add: "saved as `c.xlsx` — rename it to whatever you like." This is load-bearing for Windows brokers; see the "Excel filename rule" in Output below.**
   - If `output_format` is `"pdf"` or `"both"`: call MCP tool `render_comps_pdf` with `{query_id, validated, template_name: "internal", output_format}`. The tool returns one of two shapes (discriminated by `mode`):
     - **`mode: "url"` (happy path):** `{mode, pdf_url, expires_at, estimated_page_count, summary_stats}`. The signed `pdf_url` expires after approximately 1 hour (see `expires_at`).
     - **`mode: "bytes"` (R2-failure fallback):** `{mode, pdf_bytes_b64, expires_at, estimated_page_count, summary_stats}`. Write the decoded bytes to `/tmp/<filename>.pdf` in the sandbox and treat that local path as the deliverable instead of a URL.
     - `estimated_page_count` is a heuristic — do not quote it as authoritative to the broker.

   **Error handling for `render_comps_pdf`:**
   - **`cache_miss`** — `query_id` expired in the 10-min KV TTL (broker took too long to reply on the format question). Re-run `read_query` with the same SQL to get a fresh `query_id`, then retry `render_comps_pdf` once.
   - **`render_failed`** — Service Binding threw during render. Fall back to Excel-only and add a note in the broker email body: *"PDF render failed (transient issue); Excel attached. Investigation in flight."*

9. Call `draft_email(rows, validated, xlsx_path?, pdf_url?, pdf_local_path?)` → returns subject + body. **`pdf_url` and `pdf_local_path` are mutually exclusive** — pass `pdf_url` on the `mode: "url"` happy path, `pdf_local_path` on the `mode: "bytes"` fallback. The body includes the signed PDF URL with a 1-hour expiry note when applicable, or the local sandbox path on the bytes-fallback path. If the result count is below `target_count`, the email asks the broker which dimension (size, date, geography) to widen. **No auto-expansion** — the broker drives.
10. After the broker confirms / closes the loop: ask the three feedback questions, call `format_feedback(...)`, then send via connected email tool (Gmail / Outlook MCP) or write the fallback file.

## Input Contract

The dict you pass to `validate_request`. `asset_type` and `transaction_type` are load-bearing from the broker's request; `output_format` is resolved at step 4 before SQL runs. Everything else is open-shaped — the helpers tolerate missing optional keys and ignore unknown keys.

| Key | Required | Shape |
|---|---|---|
| `asset_type` | yes | `"industrial"` \| `"flex"` \| `"office"` \| `"retail"` \| `"medical_office"` \| `"lab"` \| `"land"` |
| `transaction_type` | yes | `"lease"` \| `"sale"` |
| `output_format` | yes (set in step 4) | `"excel"` \| `"pdf"` \| `"both"` |
| `geography` | no | `{"named_market": str}` or `{"cities": [str, ...]}` or `{"counties": [str, ...]}` or `{"anchor": str, "radius_mi": int}` |
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

`output_format` is **not** auto-defaulted. The skill blocks at Process step 4 until the broker explicitly chooses (Excel / PDF / Both) or the request names a format directly.

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

The typed comps tools (`search_external_*`, `pull_unified_comps`) apply this same family table
server-side, case-insensitively, since Worker 0.59.0 (lee#532; the table is data in
`src/tools/comps/property_type.ts`, documented as comps.md D20). For Route A SQL this table is
still yours to spell out; `describe_table` `conventions` now carries the rule too.

**Industrial outdoor storage / IOS / yard deals:** there is no clean SQL filter — confirmed by the broker. The data fields that would identify them (zoning, yard_sf, yard_type, comp name keywords, notes) are essentially unpopulated. Brokers tag these mentally. If a request mentions IOS, route as `flex` with a `min_acres` filter (broker's recommendation) and surface in the email that this is the closest proxy, not an exact match.

### Geography registry (V1)

**County asks (lee#496).** A request that names counties — "retail leases in Brunswick County", "Wake and Durham only" — maps to `geography={"counties": [...]}`, NOT to a city enumeration. `build_sql` then filters on **`county_normalized`**, and drops the city predicate entirely.

`county_normalized` exists because the raw `county` column on both safe views stores the **suffixed** spelling ("Brunswick County" — 100% of the non-blank rows), while the external comp book stores the bare name. A generated `WHERE county = 'Brunswick'` therefore returns 0 rows from a fully populated column, with no error — which is exactly what cost a broker four on-point comps on 2026-08-25. `county_normalized` is the trimmed, lowercased name with a trailing " county" removed, so `'brunswick'` matches whichever spelling the broker used. **Filter on `county_normalized`; select `county` for display.** `read_query`'s tool description and `describe_table`'s `conventions` block both say so — if you are ever unsure of a stored value's shape on these views, call `describe_table` and read `conventions` before writing the WHERE clause.

`"RDU MSA"` (and aliases `"RDU"`, `"Triangle"`, `"Raleigh-Durham"`) resolves to a hand-curated city list inside the helpers. **Sub-regional broker shorthand is not enriched in V1** (data cleanup is deferred to a later SOW). For phrasings like "Garner / South Raleigh," parse the cities explicitly and pass `geography={"cities": ["Garner", "Raleigh"]}` — don't try to register a sub-market. Anything that doesn't match a registered named market falls back to RDU MSA with a warning.

## Sale comps

The mirror exposes both `lease_comps_safe` and `sale_comps_safe`. `build_sql` branches on `transaction_type`:

- **lease** → `lease_comps_safe`, date column `lease_execution`, size filter on `COALESCE(space_sf, square_feet_sold)`, no price floor.
- **sale** → `sale_comps_safe`, date column `actual_close_date`, size filter on `COALESCE(square_feet_sold, building_size)`, `sale_price >= min_price` (default $500K junk filter).

Sale uses a different display layout (`DISPLAY_COLUMNS_SALE`) and stat shape (sale price, $/SF, total volume) — both selected automatically by `format_excel` based on `validated["transaction_type"]`. Sheet name inserts `Sale` between asset and geography (e.g., `"Industrial Sale Garner, Raleigh Comps"`).

**LAND sale exception:** when `asset_type == "land"` on a sale pull, `format_excel` uses `DISPLAY_COLUMNS_SALE_LAND`, which swaps the `$/SF` column for `$/Acre` (`price_per_acre = sale_price / acres`, computed in-loop, blank when acres is null/zero). The `Acres` column is retained; all other columns and the color scale are unchanged. $/SF is meaningless for raw land — brokers price land by acreage (broker request, gi-plugins#28).

## Confidentiality

Confidential and NDA rows are filtered server-side at the `lease_comps_safe` view. The model never sees them.

If a broker references a specific comp by ID or address that doesn't appear in results, reply verbatim:

> That comp is confidential and not retrievable through this channel.

Do not speculate about deletion, alternate IDs, broker error, or any other reason. The view filter is the explanation; saying anything else is hallucination.

## Output — deliverable shapes

The broker chooses one of three output shapes at Process step 4. All three start from the same SQL result set.

### Excel (`output_format = "excel"`)

`format_excel` writes a three-sheet workbook. Layout is frozen. Do not parameterize beyond what the helper signature exposes.

**Excel filename rule (load-bearing — do not skip).** The workbook is written to a tiny constant filename, `c.xlsx`, in the current working directory. You do not choose the name — `safe_xlsx_name` forces `c.xlsx` (enumerating `c1.xlsx`, `c2.xlsx`, ... if you produce more than one in the same session) no matter what `xlsx_path` you pass. `format_excel` returns the name actually written; use that when you reference the file to the broker, and tell them they can rename it.

- **Never create a subfolder** (`os.makedirs`, nested paths). The descriptive title lives on the Sheet 1 tab name; the file on disk stays a tiny stub.
- **Why:** brokers run this in Cowork on Windows, where output lands in a per-session directory that runs **~200 characters deep** (`C:\Users\<user>\AppData\Roaming\Claude\local-agent-mode-sessions\<session-id>\...\outputs\` — the session-id slug is long). Excel refuses to *open* any workbook whose full path exceeds **218 characters** (stricter than Windows' own 260 limit), throwing *"the file path is too long."* The file saves fine; it just won't open. With ~200 chars already spent by the fixed session dir, a descriptive name like `comps-industrial-2026-05-28.xlsx` (33 chars) tips past 218; `c.xlsx` (6) fits. The session dir is Cowork's and the file must land there, so the **filename is the only lever** — which is why it's forced to the shortest stable stub. (The broker, or Cowork on request, can rename it afterward — renaming to something short still opens fine.)

- **Sheet 1: `"{Asset Title} {Geography} Comps"`** (e.g., `"Industrial RDU MSA Comps"`, `"Retail Raleigh Comps"`).
  - Dark blue header fill, white bold; frozen panes; autofilter.
  - Color scale (red → yellow → green) on `effective_rate` column.
  - 23-column canonical layout matching `internal-comps-db/cowork-runs/2026-04-29_industrial-RDU-2k-30k-4mo/build_comps.py`.
- **Sheet 2: `"Summary"`** — count, avg/median/min/max effective $/SF, avg/median leased SF.
- **Sheet 3: `"Methodology"`** — pulled_for, pull_date, source, geography, property_types, size_range, date_window, rate_convention, applied_defaults, warnings, last_sync, caveat.

### PDF (`output_format = "pdf"`)

`render_comps_pdf` produces a Lee-branded, client-facing PDF using the server-side internal template (Dealius data). The tool returns a discriminated-union response:

- **`mode: "url"`** — R2 happy path. The `pdf_url` is a signed URL that expires approximately 1 hour after generation (`expires_at` field). Surface the URL in the broker email body with an explicit note about the 1-hour expiry so the broker knows to share it promptly. `estimated_page_count` is a heuristic; do not quote it as authoritative.
- **`mode: "bytes"`** — R2-failure fallback. `pdf_bytes_b64` contains the PDF encoded as base64. Decode and write to `/tmp/<filename>.pdf` in the sandbox, then treat that local path as the deliverable (e.g., attach to the email if the connected tool supports it). The `expires_at` and `estimated_page_count` fields are still present.

### Both (`output_format = "both"`)

Run `format_excel` (Excel) and `render_comps_pdf` (PDF) against the same `rows` / `query_id`. Deliver both. If the PDF step fails, deliver Excel-only and note the failure in the email body (see `render_failed` handling in Process step 8).

### No-result behavior

There is no `<3 results → email summary` branch and no `0 results → no-comps email` branch in the deliverable. The `draft_email` reply describes the count in prose and asks the broker how to widen if the count is below target. Excel is produced whenever `output_format` includes `"excel"` (i.e., `"excel"` or `"both"`), even on empty result sets — the methodology sheet explains the empty result. PDF is produced whenever `output_format` includes `"pdf"` (i.e., `"pdf"` or `"both"`), even on empty result sets — an empty-result PDF is unusual but valid.

## Email draft

`draft_email` returns `{subject, body}`. The body always surfaces:

- Result count and a one-line stats summary (mirror of Sheet 2).
- Any defaults `validate_request` applied — broker should be able to push back.
- Any warnings (e.g., size range not specified).
- If the count is below `target_count`: a single line asking the broker which dimension to widen (size, date, geography). The broker drives expansion via reply — the model never auto-widens.
- The confidentiality response template if a referenced comp wasn't found.
- If a PDF was produced and `mode: "url"`: the signed `pdf_url` with an explicit 1-hour expiry note (e.g., *"Link expires in ~1 hour — download or share promptly"*). On the `mode: "bytes"` fallback path, describe the local path instead.

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

The Python the model writes per request should be small. Cowork's unprompted runs were 10K-41K characters of generated Python per query (the 41K was a *simpler* question, expanding 4× as it reasoned its way through the same problem). With this skill, per-request orchestration code should be well under 1K characters — basically `validate → [format question] → build_sql → read_query → format_excel? → render_comps_pdf? → draft_email → format_feedback`. No expansion loop; below-target results trigger a broker ask in the email, not a re-query.

If you find yourself regenerating openpyxl formatting, hand-writing date math, or reconstructing the city list, **stop**. Call the helper. The flexibility tradeoff was deliberate: the dict is open-shaped so weird broker phrasings still slot in, but the deterministic surface (SQL, Excel, email scaffolding) is locked.

## Files

- `SKILL.md` — this file.
- `helpers.py` — atomic helpers (validate, build_sql, format_excel, draft_email, format_feedback). The `render_comps_pdf` step is an MCP tool call, not a Python helper — the sandbox calls the MCP directly.
- `lee_logo.png` — bundled with the skill; used by `format_excel`. This is a byte-identical copy of the canonical logo in the `lee-branding` skill; each in-session skill carries its own copy because the Cowork sandbox has no outbound network access at runtime and cannot fetch the logo from the server (gotcha registry G17). Keep it in sync with `skills/lee-branding/lee_logo.png`.

Lives next to the skill on disk but **not in the bundle**:

- `regression-tests.md` — wild query test set used to verify the skill end-to-end. Held outside SKILL.md so Cowork doesn't pattern-match worked examples.
- `internal-comp-skill-design-notes.md`, `process-table-internal-comps.md`, `learnings.md` — design references.

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
