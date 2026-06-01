---
name: lee-tenants-in-market
description: Ingests Triangle Pairlist tenant-requirement emails. On a schedule, reads the running user's inbox for [Triangle Pairlist] messages, screens each as a tenant requirement (a broker seeking space/investment) vs a listing (a broker marketing a property), extracts the requirement fields, and writes every screened email to the shared tenant-requirements store via lee_tenant_requirement_write. Run on a Cowork Scheduled Task (hourly, workday), pinned to Haiku. Reading uses the Gmail connector; writing uses lee-raleigh-mcp.
---

# /lee-tenants-in-market

Scheduled ingest of Triangle Pairlist emails into the shared tenant-requirements D1 store. Capture-everything: store both requirements and listings (audit). A `queryable` flag gates the future broker query surface.

## Prerequisites (one-time, per runner)
- **Gmail connector** enabled in Cowork (Settings -> Connectors -> Gmail). This reads the runner's own inbox server-side; it is the ONLY supported way to read mail from a Cowork session.
- **lee-raleigh-mcp** connector enabled and the runner's email on the LEE_TENANT_WRITERS allowlist.

## Step 0 - Smoke check (run first on any new build)
Confirm both dependencies are reachable before processing real mail:
1. Gmail connector: list 1 message matching `subject:"[Triangle Pairlist]"`. If it errors, STOP and report `Gmail connector: BLOCKED`.
2. lee-raleigh-mcp: call `lee_tenant_requirement_write` with a throwaway record (`source_message_id: "smoke-<date>"`, `record_type: "listing"`, `queryable: false`, `is_investment: false`, `raw_json: "{}"`). Expect `{ok:true}`. If `forbidden`, the runner is not on LEE_TENANT_WRITERS - escalate to David.
Print `REACHABLE` / `BLOCKED` per dependency, then proceed.

## Step 1 - Read
Via the Gmail connector, fetch messages matching `subject:"[Triangle Pairlist]" newer_than:2d`. (Rolling 2-day window; UPSERT makes re-reads harmless.)

## Step 2 - Screen each email (the judgement call)
For each message decide `record_type`:
- **requirement** - the sender is representing a tenant/buyer/investor SEEKING space or an investment. Tells: "ISO" (In Search Of), "seeking", "client looking for", "we need", an explicit requirement list.
- **listing** - the sender is MARKETING a property they have. Tells: "For Lease", "For Sale", "Now Leasing", "Available", "New to Market", "development opportunity", "reduced price".
Judge by who-wants-what, not by stray keywords ("Now Leasing 2,000 SF available" is a LISTING even though it has a size).

Then set, **on EVERY record (requirement AND listing)**:
- `reason`: **always required** — a one-clause rationale for the requirement-vs-listing call (e.g. "broker marketing a property they have" for a listing, "broker representing a tenant seeking space" for a requirement). Set it on listings too; it is the audit trail. A null `reason` is a bug.
- `is_investment`: true only if it seeks an INVESTMENT / $-budget property rather than space.
- `queryable`: true for space requirements; **false** for `is_investment` requirements (audit-only) and for all listings.

For **requirements only**, also extract (leave these null on listings): `tenant`, `requirement_sf` (verbatim), `sf_min` (int or null), `budget` (verbatim $ or null), `preferred_location`, `asset_type`, `tenure` (lease/purchase/both/null), `additional_details`.

Worked anchors (from the validated Phase-1 corpus):
- "ISO: 5,000-7,000 SF Medical | Garner" -> requirement, queryable, asset_type=medical, tenure=both, sf_min=5000.
- "ISO Investment $1.5M" -> requirement, is_investment=true, queryable=false, budget="$1.5M".
- "ISO 2nd Gen Restaurant Garner" -> requirement, queryable (sf=null, matchable by type+location).
- "North Graham Business Center Now Leasing" -> listing, queryable=false.

## Step 3 - Resolve broker contact
Triangle Pairlist runs on gaggle.email and encodes the original sender as `triangle-pairlist+<name>_at_<domain>@gaggle.email` -> `<name>@<domain>`.
- If the message's envelope `From:` is a gaggle alias (reading Pairlist directly, e.g. on Will's machine), decode it.
- Else parse the forwarded body's `From:` header (David reading Will's forwards now).
Set `broker_name`, `broker_email`, `broker_phone` (from the signature).

## Step 4 - Write
For EACH screened message, call `lee_tenant_requirement_write` with:
- `source_message_id`: the email's RFC822 Message-ID if the connector exposes it; else the connector's stable per-message id. (This is the dedup key.)
- `received_date`: the email date (YYYY-MM-DD).
- all screened fields from Step 2-3, **including `reason` on every call** (a listing row carries `record_type`, `reason`, broker contact, and `raw_json`; the requirement-only fields stay null).
- `raw_json`: the full email (headers + body) as a JSON string.
Re-running is safe (UPSERT on source_message_id).

## Step 5 - Report
Summarize: N read, M requirements (K queryable), (N-M) listings, write errors. Do not collapse requirements and listings.
