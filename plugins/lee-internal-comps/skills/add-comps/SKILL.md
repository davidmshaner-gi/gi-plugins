---
name: add-comps
description: Normalize a contributed comp set a Lee broker pastes, forwards, or uploads (a forwarded email with several brokerage comp tables, an xlsx/csv export, a pasted tab/pipe table, or a screenshot) into canonical AddCompRow records ready for ingestion via the lee_comps_add_write MCP tool. parse_email extracts the comp tables from a forwarded email body, attaches the contributing source (JLL, Foundry, etc.) to each row, and skips signature / confidentiality decoy tables. parse_spreadsheet reads an xlsx or csv, picks the comp-shaped sheet(s) and skips prose/view tabs, and raises AmbiguousSheetError when more than one comp sheet is present so the operator can choose. parse_text parses a pasted tab- or pipe-delimited table. parse_image and llm_fallback extract rows via an injected model-vision callable (the skill's own Claude runtime) for screenshots or blobs the deterministic parsers can't handle. detect_transaction_type decides lease vs. sale from the column headers. apply_alias_map folds contributor headers into the canonical keys, coerces numerics (strips $ , %), preserves the verbatim Transaction Type as txn_subtype, and keeps any unmapped columns in raw_fields_json. validate_row flags (never drops) rows missing the minimum keys. dry_run_summary reports total + per-source counts + flagged rows for operator review, and build_write_payload assembles the exact AddCompsPayload (with parser_version) for the lee_comps_add_write MCP tool. The model then calls lee_comps_add_write with dry_run=true first, shows the broker any likely duplicates already in the contributed book, and only then writes; a bad import is reversible with lee_comps_delete_import by its import_id.
---

# Add Comps (Lee & Associates)

Turn a contributed comp set — most often a forwarded email where another
brokerage shop has pasted several comp tables — into clean, canonical
`AddCompRow` records the broker can review and then push into the internal
comps database via the `lee_comps_add_write` MCP tool.

The helpers are deterministic and run in the Cowork sandbox. The model
orthestrates and performs the dry run and the MCP write (see "Write flow"
below); the sandbox has no MCP access.

## When to use

When a broker pastes or forwards a set of comps they want added to the internal
database. Typical shapes:

- A forwarded email titled like "Full Set of 2025 Industrial Comps" with one
  table per contributing source, each preceded by a bold `<Source> Comps:`
  header.
- A single pasted comp table (tab- or pipe-delimited).
- An xlsx/csv export (possibly multi-tab).
- A screenshot of a comp table.

## What it does (normalization)

1. **`parse_email(html)`** — extracts every HTML table from the email body. For
   each table it finds the nearest preceding bold `<Source> Comps:` header and
   stamps every row's `original_source` with the source name (`JLL Comps:` ->
   `JLL`, `Tri Property Comps:` -> `Tri Property`). Tables with no comp-shaped
   header row — email signatures, confidentiality notices — are skipped. Each
   data row is run through detection, alias folding, and validation. Returns a
   list of normalized rows.
2. **`detect_transaction_type(headers)`** — returns `"lease"` for a header set
   with Sign Date / Term / Base Rent / Tenant; `"sale"` for Sale Date / Sale
   Price / Buyer / Seller / Cap.
3. **`apply_alias_map(raw_row, txn_type)`** — folds contributor headers into the
   canonical AddCompRow keys, coerces numerics (strips `$`, `,`, `%`; sizes and
   term to int, rents to float), preserves the verbatim Transaction Type value
   as `txn_subtype` (`New Lease`, `Sublease`, `Renewal`, `Renewal/Expansion`,
   `New (pending)`), and stores any unmapped columns in `raw_fields_json` so
   nothing the contributor typed is lost.
4. **`validate_row(row)`** — sets `flagged=1` plus a `flag_reason` when minimum
   keys are missing (lease: address + size + base rent + date; sale: address +
   sale price + sale date); otherwise `flagged=0`. Never drops a row.
5. **`parse_spreadsheet(path)`** — reads an `.xlsx` or `.csv`. For a multi-tab
   xlsx it considers only comp-shaped sheets (header row matches >= 3 alias
   keys) and skips prose / view tabs; if more than one comp-shaped sheet is
   found it raises `AmbiguousSheetError(sheet_names)` so the operator can choose
   (never a silent pick). Each sheet is routed by `detect_transaction_type`, so
   a SALE sheet fills the sale block and the lease block stays None.
6. **`parse_text(blob)`** — parses a pasted tab- or pipe-delimited table (header
   row + data rows) through the same detect + alias + validate pipeline.
7. **`parse_image(image_ref, model_extract)`** / **`llm_fallback(blob,
   model_extract)`** — extract rows via an injected `model_extract` vision
   callable (the skill's own Claude runtime in production; a mock in tests).
   The callable returns already-canonical row dicts; the adapter runs each
   through `validate_row`. No network or API key inside the sandbox.
8. **`dry_run_summary(rows)`** — returns `total`, per-`original_source` counts,
   and the flagged rows (with `flag_reason`) for the operator to review before
   the write.
9. **`build_write_payload(rows, meta)`** — assembles the exact `AddCompsPayload`
   dict the `lee_comps_add_write` MCP tool expects (`added_by`,
   `import_method`, `raw_blob`, `parser_version` from the `PARSER_VERSION`
   constant, `rows`, plus optional `client_id` / `source_label` /
   `raw_blob_ref` / `notes`). The model performs the dry run and the actual MCP
   write (see "Write flow").

## Write flow (the model's job — do this every time)

1. **Dry run first.** Call `lee_comps_add_write` with the assembled payload **plus
   `dry_run: true`**. It returns, per row, `new` or `likely_duplicate` with the
   matching `added_comp_id` / `import_id` / `original_source` from the contributed
   book. Nothing is written. (This is the server-side duplicate check against the
   book, separate from the local `dry_run_summary` helper, which only reports
   missing fields.) The response must echo `dry_run: true` and `import_id: null`;
   if it instead returns a numeric `import_id`, the server wrote — tell the broker
   immediately and offer the undo in step 4.
2. **Show the broker the likely duplicates** (address, tenant or buyer, size, rent or
   price, and which earlier import they match). Ask whether to drop them from this
   import, keep them, or stop. Rows the broker drops: remove them from `rows` before
   the real write. Never silently drop or merge on the broker's behalf. If every row
   matches the same earlier `import_id`, this set is already loaded — say so and
   stop; do not write. If the broker drops every row, there is nothing to write — stop.
3. **Write.** Call `lee_comps_add_write` again WITHOUT `dry_run`. Any remaining likely
   duplicates are inserted but flagged (`flagged=1`, `flag_reason` names the match) and
   echoed back as `likely_duplicates` — tell the broker `added`, the likely-duplicate
   count, and the `import_id`.
4. **Undo.** If the broker says the import was a mistake, call
   `lee_comps_delete_import` with that `import_id` (confirm first — it deletes every
   comp that import wrote and the import record, and cannot be undone). The same file
   can then be re-imported after corrections.

## Importing the helpers (read before writing a script)

`helpers.py` lives in THIS skill's own directory, which is **not** on the Cowork
sandbox's default Python path — so a bare `from helpers import ...` in a script
you write to your working dir raises `ModuleNotFoundError: No module named
'helpers'`. Locate the skill dir and put it on `sys.path` first:

```python
import sys, os, glob
_hits = (glob.glob('/sessions/*/mnt/.remote-plugins/*/skills/add-comps/helpers.py')
         or glob.glob(os.path.join(os.path.expanduser('~'), '**/skills/add-comps/helpers.py'), recursive=True))
sys.path.insert(0, os.path.dirname(_hits[0]))
from helpers import (validate_row, apply_alias_map, detect_transaction_type,
                     parse_email, parse_spreadsheet, parse_text,
                     dry_run_summary, build_write_payload)
```

(Alternatively, copy `helpers.py` next to your script first.) The skill's base
directory is also printed in the launch message ("Base directory for this
skill: ...") if you prefer that path directly.

## Schema

The output keys match the `lee_comps_add_write` MCP tool's `AddCompRow` exactly
(see `helpers.py` `CANONICAL_KEYS`). Do not rename them.

## Out of scope

- The helpers never call MCP — the sandbox has no MCP access. The model performs
  the dry run, the write, and any undo per "Write flow" above (`build_write_payload`
  assembles the payload; the model calls the tools).

## Tests

```
cd plugins/lee-internal-comps/skills/add-comps
python3 -m pytest tests/ -v
```

The golden fixture `tests/fixtures/silas_email.html` is a structurally faithful
synthetic email (4 comp tables: JLL 12, Foundry 4, Tri Property 9, Prologis 5 =
30 rows, plus 2 decoys) — parse_email must yield exactly 30 lease rows.

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
