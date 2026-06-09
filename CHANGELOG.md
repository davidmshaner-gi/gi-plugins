# Changelog

All notable changes to the `gi-plugins` marketplace (the `lee-internal-comps` plugin for
Lee & Associates Raleigh brokers). Follows [Semantic Versioning](https://semver.org/).

Brokers pick up releases by syncing the marketplace in Cowork (auto-sync toggle on), or
via `/plugin update`. `marketplace.json` and `plugins/lee-internal-comps/.claude-plugin/plugin.json`
carry the same version as of 1.4.0.

## [1.13.0] - 2026-06-09

### Added
- **`nearby-businesses` skill** — a broker asks "what's around [address]" / "map the nearby amenities" (or `/nearby-businesses <address>`) and gets an **Area Amenities map kit** for any NC address: the recognizable nearby businesses (grocery, retail, restaurants, coffee, gyms, pharmacies, hotels, healthcare) ranked by prominence with their brand logos, laid out on a basemap with 1/3/5-mile rings, returned as a downloadable designer kit (basemap + `logos/` + `placements.json` manifest + Lee `brand.json`) behind a 15-minute signed link. The marketing team composes the flyer's amenities map in Claude Design. Thin orchestrator over the lee-raleigh-mcp `pull_nearby_businesses` tool (lee-raleigh-mcp v0.10.0; Google Places discovery + Wikidata/favicon logos warm-cached in R2). Basemap is a PDF in v1 (high-res PNG tracked separately). (#57)

## [1.12.1] - 2026-06-09

### Changed
- **`vpd-lookup` now surfaces the PDF flyer card.** `pull_vpd_lookup` returns a signed `pdf_url` (lee-raleigh-mcp v0.9.3), so the skill now offers a "📄 Open PDF" link (1-hour expiry) — the polished Lee-branded traffic-counts card — instead of only the raw HTML fragment. Falls back to the inline top-5 if the render is unavailable. (#75)

## [1.12.0] - 2026-06-09

### Added
- **`vpd-lookup` skill** — a broker asks "traffic counts near [address]" (or `/vpd-lookup <address>`) and gets the top-5 nearby road segments by AADT (vehicles per day) for any NC address: ranked by road class then traffic volume, each with the annual average daily traffic, the count year, and distance from the site, plus a ready-to-place `vpd-card` flyer fragment for a retail / QSR / flex listing. Thin orchestrator over the lee-raleigh-mcp `pull_vpd_lookup` tool (NCDOT AADT, ~49k stations staged statewide to D1). NC-only, single address, top-5 within 1.5 mi in v1. (#73)

## [1.11.0] - 2026-06-08

### Added
- **`lee-flyer-brief` skill** — a broker says "build a flyer for my listing" (or drops a listing agreement) and gets walked through assembling everything a marketing flyer needs: the skill auto-pulls owner of record, business key facts, and demographics, then runs the comp set, key facts, and demographics each through a **present → augment → select → narrate** loop so the broker adds their own data and picks exactly what appears. It writes a provenance-tagged **flyer brief** (every figure tagged `internal comps DB` / `external (CoStar cache)` / `broker-provided` / `listing agreement` / `county record` / `Census`) and hands the broker carry-over instructions into **Claude Design** (Lee design system) for visual polish. Replaces Lee marketing's Formstack "New Listing Marketing Request" intake. Write-back of broker-provided comps + the subject listing to the comps DB is **confirmation-gated** (no auto-write). Prototype validated through Rings 1–3 (simulated + two live Cowork runs + Claude Design number-fidelity diffs). (#67)
  - **Pending (does not block this release, gates broker self-serve distribution):** the listing-agreement **compliance-gate** decision (David/Jamie — must an agreement be confirmed on file before a flyer ships?); Ring 4 (verify `lee_comps_add_write` accepts an on-market/subject-listing record) and Ring 5 (Will's first live end-to-end run). Reliability deps lee-and-associates #75 (comps MCP hardening) and #29 (external lease backfill) are non-blocking — the skill carries inline workarounds and degrades gracefully.

## [1.10.0] - 2026-06-08

### Added
- **`labor-shed` skill** — show the labor force around a commercial site for any NC address, sliced by industry, for 1/3/5-mile rings: the resident labor pool a tenant can recruit (RAC) and the existing employer mix already in the area (WAC), with the industrial-family workforce (construction, manufacturing, wholesale trade, transportation & warehousing) called out. Thin orchestrator over the `lee-raleigh-mcp` `pull_labor_shed` tool (lee-raleigh-mcp v0.8.0). (#25, lee-and-associates #25)

## [1.9.0] - 2026-06-08

### Added
- **`process-mapping` skill** — a guided interview that helps anyone at the firm (any function — brokerage, marketing, operations, finance, research, leadership) map one of their own repeatable processes into a clean, linear, text-only process-map document, before any automation. Opens with Grounded Intelligence branding, walks five gates, and ends by drafting an email that hands the finished map back to GI for the next phase. CRE appears only as firm context; the user's role stays agnostic. (#69)

## [1.8.2] - 2026-06-03

### Fixed
- **`add-comps`: documented the helpers `sys.path` import** so a script that uses the deterministic helpers doesn't hit `ModuleNotFoundError` in the Cowork sandbox (where `helpers.py` is mounted under `.remote-plugins/`, not the working dir). Surfaced during the first live `/add-comps` run, which self-recovered; this makes the next run clean. (#11 follow-up)

## [1.8.1] - 2026-06-03

### Fixed
- **Unified "all comps": external Comp ID now shows a short, broker-readable id** (CoStar property id / `external_comp_id`) instead of the 64-char `external_id` address hash that was dumped into the Comp ID column. Internal ids unchanged. (#57)

## [1.8.0] - 2026-06-02

### Added
- **`add-comps` skill** — turn a contributed comp set a broker pastes, forwards, or uploads (a forwarded email with several brokerage comp tables, an xlsx/csv export, a pasted tab/pipe table, or a screenshot) into canonical records tagged by source and provenance, and ingest them into the comps database as a **third source** alongside internal Dealius + external CoStar. Handles lease and sale; flags (never drops) incomplete rows for review. Brokers can then query across all three sources from one surface via the new `pull_unified_comps` MCP tool. Backed by lee-raleigh-mcp v0.7.0 (`comp_imports` + `comps_added` tables, a unit-reconciled `comps_unified` view, and the `lee_comps_add_write` MCP tool). (#11, coupled with lee-and-associates #64)

## [1.7.1] - 2026-06-02

### Fixed
- **`owner-mailing-list`: faster, cleaner pulls (post-live-QA).** Three fixes from the first live runs: (1) the skill now drives the **Claude in Chrome** extension's `javascript_tool` instead of "Control Chrome" (whose JS execution fails) — no more wasted retries and a failed false-start; (2) the whole fetch → dedupe → CSV pipeline now runs in **one** browser call (`buildOwnerMailingCsv` in `arcgis_query.js`, node-tested) and the file is written in deterministic line-batches, cutting a pull from ~139 tool calls to a handful; (3) results are **filtered to private owners** — government, municipal, exempt, HOA/COA, cemetery, utility, and railroad parcels (plus blank-owner rows) are dropped, so the list is broker-mailable prospects. Example: New Hanover went from 71 raw parcels to 29 private owners; Onslow 76 → 46. (#1)

## [1.7.0] - 2026-06-02

### Added
- **New skill: `internal-and-external-comps` — the default "all comps" experience.** When a broker asks for comps **without** saying internal or external, this skill runs both the internal (Dealius) and external (CoStar) pulls in parallel and returns **one** combined deliverable: a chat table, an Excel (an "All Comps" sheet plus per-source detail sheets), and **one Lee-branded unified PDF**, with every row tagged by **Source** (`Internal — Dealius` / `External — CoStar`). No dedup — a property in both sources shows as two tagged rows. Works for sale and lease. Explicit "internal comps" / "external comps" requests still route to the single-source skills. The unified PDF is powered by the new `cache_external_rows` MCP tool + `unified` template on `lee-raleigh-mcp` v0.6.0. (#29, coupled with lee-and-associates#45)

## [1.6.0] - 2026-06-02

### Added
- **New skill: `owner-mailing-list`.** Build a deduplicated owner + mailing-address list for an area + criteria request — e.g. "owners of 2–5 acre vacant land within 3 miles of 100 Walnut St, Cary." The skill drives Claude-for-Chrome against a county's public ArcGIS parcel service to find matching parcels, then returns a clean CSV of owner names + mailing + site addresses, deduped by mailing address. Covers **19 NC counties** (Triangle, Sandhills, Wilmington-coast, Triad, eastern NC), each live-validated against its parcel service. Requires the `chrome-control` extension; the skill detects it and walks the broker through enabling it if absent. (Avery-label printing is a separate forthcoming skill.) (#1)

## [1.5.3] - 2026-06-02

Reconciling release: four broker-facing / owner-lookup changes had merged to `main` since `v1.5.2` without a version bump. Bundled here so the version string matches `main`.

### Fixed
- **internal-comps: LAND sale comps price on `$/Acre`, not `$/SF`.** For a sale pull where `asset_type == "land"`, the Excel shows a `$/Acre` column (`price_per_acre = sale_price / acres`, whole-dollar currency, blank when acres is null/zero) where `$/SF` used to be; the `Acres` column stays. Non-land asset types and all lease pulls are unchanged. $/SF is meaningless for raw land. Broker request from Mike Glennon. (#28 / PR #39)
- **owner-lookup: Lee County verify link uses `mode=realprop`, not `parid`.** The Lee County verify-footer link used a Tyler mode that throws; it now opens the working real-property search. (#18 / PR #44)
- **lee-internal-comps: stripped the "CoStar" brand from broker-facing surfaces.** (#6 / PR #37)

### Added
- **owner-lookup verify-link QA harness** (`scripts/qa/verify-links/`) — drives each county verify-footer portal with a sentinel PIN and asserts the parcel resolves, catching a load-fine/search-broken portal before a broker hits it. Run before any release that touches owner-lookup verify links. (#19)

## [1.5.2] - 2026-06-01

### Fixed
- **tenants-in-market: removed the smoke check from the routine flow.** "Step 0 — run first on any new build" was being executed on every invocation, listing Gmail and writing a throwaway `smoke-*` record each run (noise on the hourly scheduled task). Routine runs now go straight to Step 1; one-time deploy validation moved to a manual appendix that uses a real email instead of a junk record. (#25)

## [1.5.1] - 2026-06-01

### Fixed
- **tenants-in-market: `reason` now set on listing rows.** The screening rationale was only captured for requirements (it was bundled in the requirement-only field-extraction step), leaving `reason` null on every listing. It is now a per-record instruction, required on requirements AND listings. Existing rows backfill on the next ingest pass (UPSERT). (#23)

## [1.5.0] - 2026-06-01

### Added
- **`tenants-in-market` skill** — scheduled Cowork ingest of Triangle Pairlist tenant-requirement emails. Screens each as requirement vs listing, extracts requirement fields, and writes every screened email to the shared `tenant_requirements` store via the new `lee_tenant_requirement_write` MCP tool (lee-raleigh-mcp v0.3.0). A `queryable` flag gates the future broker query surface; investment/$-budget ISOs are captured audit-only. Ingest runs on a Cowork Scheduled Task (hourly, pinned to Haiku). Broker query surface is a follow-up. (#20)

## [1.4.0] - 2026-05-29

First tagged release since `v1.1.0`. Consolidates the 1.2.0–1.3.4 work (which shipped to
brokers via commit-sync but was never tagged) into one clean release, and re-syncs the
two version manifests (`marketplace.json` had drifted to 0.7.1).

### Added
- **owner-lookup skill** — owner of record, mailing address, and assessor facts for any
  property in Wake, Durham, New Hanover, or Lee NC, sub-second from a bulk-staged owner
  graph (~2M parcels). (1.2.0)
- **daily-debrief skill** — Will-facing interview-style classification of yesterday's
  broker requests, capturing off-plugin asks (plugin_broke / known_gap / new_opportunity)
  so the rollup drives the roadmap conversation. (1.3.0)

### Changed
- Comps skills now **surface the data freshness banner** so brokers can see how current
  the Dealius/CoStar data is before relying on it.
- `internal-comps` description corrected to advertise **both lease and sale** comps (it
  previously read lease-only).

### Fixed
- **Excel export filenames** on Windows — short, flat filenames + a `format_excel` guard
  for the 218-character path limit Will hit (roadmap #61).

### Internal (not broker-facing)
- skill-contract-check pre-commit hook + reviewer tooling (`scripts/`).
- PR template for the plugin-development-process.
- Version manifests re-synced: `marketplace.json` + `plugin.json` both `1.4.0`.

## [1.1.0] - earlier
Last previously-tagged release. See git history before this changelog existed.
