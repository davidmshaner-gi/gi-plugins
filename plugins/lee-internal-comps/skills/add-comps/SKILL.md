---
name: add-comps
description: Normalize a contributed comp set a Lee broker pastes or forwards (e.g. a forwarded email with several brokerage comp tables) into canonical AddCompRow records ready for ingestion via the lee_comps_add_write MCP tool. parse_email extracts the comp tables from a forwarded email body, attaches the contributing source (JLL, Foundry, etc.) to each row, and skips signature / confidentiality decoy tables. detect_transaction_type decides lease vs. sale from the column headers. apply_alias_map folds contributor headers into the canonical keys, coerces numerics (strips $ , %), preserves the verbatim Transaction Type as txn_subtype, and keeps any unmapped columns in raw_fields_json. validate_row flags (never drops) rows missing the minimum keys. Email adapter only in v0.1 — MCP write is the model's job.
---

# Add Comps (Lee & Associates)

Turn a contributed comp set — most often a forwarded email where another
brokerage shop has pasted several comp tables — into clean, canonical
`AddCompRow` records the broker can review and then push into the internal
comps database via the `lee_comps_add_write` MCP tool.

The helpers are deterministic and run in the Cowork sandbox. The model
orchestrates and performs the MCP write; the sandbox has no MCP access.

## When to use

When a broker pastes or forwards a set of comps they want added to the internal
database. Typical shapes:

- A forwarded email titled like "Full Set of 2025 Industrial Comps" with one
  table per contributing source, each preceded by a bold `<Source> Comps:`
  header.
- A single pasted comp table.

## What it does (v0.1 — normalization)

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

## Schema

The output keys match the `lee_comps_add_write` MCP tool's `AddCompRow` exactly
(see `helpers.py` `CANONICAL_KEYS`). Do not rename them.

## Out of scope (v0.1)

- The MCP write itself (`lee_comps_add_write`) — the model performs it after the
  broker reviews the normalized rows.
- Sources other than a forwarded email / pasted HTML tables (xlsx upload, etc.).

## Tests

```
cd plugins/lee-internal-comps/skills/add-comps
python3 -m pytest tests/ -v
```

The golden fixture `tests/fixtures/silas_email.html` is a structurally faithful
synthetic email (4 comp tables: JLL 12, Foundry 4, Tri Property 9, Prologis 5 =
30 rows, plus 2 decoys) — parse_email must yield exactly 30 lease rows.
