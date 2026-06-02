# Changelog

All notable changes to the `gi-plugins` marketplace (the `lee-internal-comps` plugin for
Lee & Associates Raleigh brokers). Follows [Semantic Versioning](https://semver.org/).

Brokers pick up releases by syncing the marketplace in Cowork (auto-sync toggle on), or
via `/plugin update`. `marketplace.json` and `plugins/lee-internal-comps/.claude-plugin/plugin.json`
carry the same version as of 1.4.0.

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
