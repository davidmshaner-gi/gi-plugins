# Changelog

All notable changes to the `gi-plugins` marketplace (the `lee-internal-comps` plugin for
Lee & Associates Raleigh brokers). Follows [Semantic Versioning](https://semver.org/).

Brokers pick up releases by syncing the marketplace in Cowork (auto-sync toggle on), or
via `/plugin update`. `marketplace.json` and `plugins/lee-internal-comps/.claude-plugin/plugin.json`
carry the same version as of 1.4.0.

## [1.38.0] - 2026-08-25

### Added
- **Comps can be pulled by county (lee#496).** `internal-comps`, `external-comps` and
  `internal-and-external-comps` accept a new geography shape, `{"counties": [...]}`. Until now the
  skills had only `named_market` and `cities`, so "retail leases in Brunswick County" was enumerated
  as beach towns: on 2026-08-25 a broker got four correct city-level zeroes and no comps, while every
  Brunswick retail lease we hold sits in Leland, Shallotte or Southport (43 Brunswick lease comps and
  191 sale comps in the external book, plus one in the internal one).
  - `external-comps` issues one MCP call per county carrying the new typed `county` param
    (Worker 0.51.0). No post-filter, so the `named_market` null-county dialog does not apply.
  - `internal-comps` emits a `county_normalized` predicate against the safe views instead of a city
    list. The raw `county` column stores the **suffixed** spelling ("Brunswick County"), so filtering
    it directly returns 0 rows from a fully populated column; `county` is for display only.
  - Pass the broker's spelling **verbatim** on both paths. The two comp books store counties
    oppositely and the Worker normalizes both sides, so either form matches either book.

### Changed
- `internal-comps` / `external-comps` frontmatter descriptions now name county as a supported
  geography, so a county-shaped ask routes to them.
- A `counties` geography now takes precedence over `named_market` in BOTH skills (they previously
  disagreed), and a `counties` list that holds only blanks is treated as "not a county ask" and
  falls back to the normal geography default rather than dropping every geography predicate --
  silently returning the whole statewide book to a broker who asked about one county would be
  worse than the zero this release replaces.
- Requires Worker **0.51.0** for the external `county` param and the `county_normalized` view column.

### Fixed
- **County-shaped internal pulls no longer ship a blank geography label.** `_geography_label` had
  no `counties` branch, so the Excel sheet name read "Retail Comps" instead of
  "Retail Brunswick County Comps" and the email body ended "for ." Found in review before release.
- **The marketplace card now matches the plugin manifest.** `marketplace.json` -- the description a
  broker actually reads when syncing -- had drifted from `plugin.json`. New guard
  `scripts/test/manifest-parity.sh` asserts both `version` and `description` agree for every listed
  plugin, so the convention is enforced instead of remembered.

## [1.37.0] - 2026-08-25

### Changed
- **demographic-summary: growth presentation follows the Worker's 0.50.0 blend (lee#497).**
  The skill now reads the blended rate's `source` for the county window (ACS 1-year for
  the 44 NC counties the Census publishes it for, ACS 5-year for the other 56) and for the
  "state rate substituted" note that appears when a ring's own change is inside the
  survey's margin of error. A `null` blended rate is reported as "GI blended growth rate
  unavailable: <notes>" -- never as an MOE suppression, never with a pointer to
  county-level Census estimates (the lee#487 Cowork pass misattributed the gap that way).

## [1.36.0] - 2026-08-24

### Added
- **add-comps: duplicate check before every write + import undo (lee#74; Worker 0.47.0).**
  The skill now calls `lee_comps_add_write` with `dry_run: true` first, shows the broker
  any rows that look like comps already in the contributed book (same address, deal
  size, and rent/tenant or price/buyer), and only writes after they decide. Remaining
  likely duplicates are flagged, never dropped. A mistaken import is reversible with
  `lee_comps_delete_import` by its `import_id`.

## [1.35.0] - 2026-08-24

### Added

- **Custom ring radii on the demographic summary** (Worker 0.47.0, lee-and-associates#487):
  `demographic-summary` passes `radii` when a broker names ring sizes ("3/5/7 like the OM");
  default stays 1/3/5. Response ring keys follow the radii (`3mi`/`5mi`/`7mi`), listed in
  `radii_miles`.
- **GI blended growth per ring** (`gi_blended_growth_annual_pct`) is the headline growth figure;
  the ring's own raw Decennial->ACS rate is now MOE-guarded (null with a note when the change is
  inside the ACS 90% margin of error -- the brentway -23.7%/yr artifact). The skill's
  growth-presentation rules are rewritten accordingly.

## [1.34.0] - 2026-08-21

### Fixed

- **External lease comps size on the space leased, not the building** (Worker
  0.43.0, lee-and-associates#469, closes lee-and-associates#180 / the
  gi-plugins#105 interim): a broker's lease size range used to go out as
  `min/max_building_sf`, and `building_sf` (the building footprint) is empty on
  most external lease rows, so any size-bounded external lease search returned
  ~0 (Christian Sommer's Apex 2,000–20,000 SF ask on 2026-08-21). The Worker now
  carries `leased_sf` (the external platform's "Size Leased SF", promoted and
  backfilled) and `search_external_lease_comps` takes `min/max_leased_sf`;
  `external-comps` sends the lease size range there (sales still filter
  `building_sf`), and every lease size surface (Excel column, Summary stats,
  chat table, ranking) reads `leased_sf`. `internal-and-external-comps` retires
  the #105 blank: external lease rows show their real "Leased SF", never the
  building size, blank only when the row has no leased size.

## [1.33.0] - 2026-08-20

### Added

- **Empty external comp searches explain themselves** (Worker 0.42.0,
  lee-and-associates#463): when `search_external_sale_comps` /
  `search_external_lease_comps` return no rows, the response now carries
  `empty_result` (the binding filter, the nearest comps just past it with how far
  each misses, a one-line note). `external-comps` and `internal-and-external-comps`
  read it and tell the broker which filter cut the last candidates, show the near
  misses as a short table, and offer the relaxation as a yes/no instead of a bare
  "no comps found". The same Wilmington ask that returned silence on 2026-08-20
  now surfaces 3241 Pennington Dr at 13,508 sf over the ceiling.

## [1.32.0] - 2026-08-20

### Added

- **`labor-shed` by drive time** (Worker 0.41.0, lee-and-associates#464): "how many
  workers live within a 30-minute drive of this site" now passes
  `geometry: "drive_time"` + `minutes` to `pull_labor_shed` and presents the
  resident labor pool and employer mix per drive-time band (15/30/45 by default).
  Mile-ring asks are unchanged. Free-flow drive times; same routing budget and
  error envelope as the drive-time map.

## [1.31.1] - 2026-08-20

### Fixed

- **`drive-time-isochrones` reads the tool result instead of overflowing it** (Worker
  0.40.0, lee-and-associates#460): `pull_drive_time_isochrones` now returns a chat-sized
  summary by default (`geojson` + `fragment_html` moved behind `detail: "full"`). The
  skill tells the session never to request `full` in chat, to present anchor reach as
  bands from the one pull, and never to re-run narrower windows or fall back to public
  routing services for exact minutes. Re-scoped (David, 2026-08-20): `anchors` /
  `anchor_reach` is a flyer-engine input, not a chat feature -- the skill no longer
  advertises "drive times to RDU" asks (point-to-point questions are out of scope).
  Closes the 4a finding from lee-and-associates#458
  (the session dumped the 365K-char result to a file and answered from Google Maps via
  seven quota-burning pulls). Hard-linked sibling of lee-and-associates#460 (G11 sub-case d).

## [1.31.0] - 2026-08-19

### Changed

- **`drive-time-isochrones` now drives the new `anchors[]` param** (Worker 0.39.0,
  lee-and-associates#458 / gi-plugins#148): broker asks like "with drive times to RDU,
  downtown Durham, ..." pass named destinations to `pull_drive_time_isochrones`
  and present each one's smallest containing band ("<= 25 min") or "beyond 60 min".
  Hard-linked sibling of lee-and-associates#458 -- shipped together so the live
  param is never inert (G11 sub-case d).

## [1.30.1] - 2026-08-19

### Changed

- **Plugin description rewritten** (marketplace.json + plugin.json). The old one was a
  run-on catalogue of every skill's internals; it's now a short broker-facing summary of
  what the toolkit does. No functional change.

## [1.30.0] - 2026-08-15

### Changed

- **External comps response fields follow the lee#442 contract rename.** The MCP server's
  external tables now serve `external_property_id` / `external_property_url` (previously the
  vendor-branded names); the external-comps and unified-comps helpers read the new fields.
  Broker-visible effect: none when plugin and server are both current. A plugin older than
  this version pointed at the renamed server falls back to the short `external_comp_id` in
  the Comp ID column and leaves Source URL blank until the marketplace sync picks this up.
  Guards tightened: the response-shape identifier exemption is retired.

## [1.29.0] - 2026-08-14

### Changed

- **Source-neutrality sweep (company policy).** The comps database replaces the reference
  spreadsheets brokers already keep; what a broker chooses to load into it is their own
  prerogative. Accordingly, no third-party data vendor is named anywhere in this repo:
  all prose, skill instructions, deliverable strings, and code comments now say
  "external" / "the external platform." Broker-visible strings changed: the unified
  Source tag is now `External` (was branded) and the Excel detail sheet is now
  `External` (was branded). Live data-contract identifiers (`external_property_id`,
  `external_property_url`, the MCP response shapes) are unchanged — renaming those is
  tracked separately. The stashed platform-specific SOP skill was removed.

## [1.28.5] - 2026-07-23

### Fixed
- **Test suite: full-dir pytest runs no longer fail with cross-skill import
  collisions (gi-plugins#137).** Several skills each ship a `helpers.py`; some test
  files did `sys.path.insert(<skill dir>); import helpers`, so whichever skill's
  module loaded first poisoned `sys.modules["helpers"]` for every later test file —
  14 false failures on a full-dir run while each file passed alone. All skill-helper
  imports now go through a shared `conftest.load_skill_helpers` (unique per-skill
  module names, zero sys.path mutation), a static guard test pins the rule, and the
  suite now runs as a required `pytest` job in pr-checks CI (which is why the
  collision survived for weeks — nothing ran it). Test infra only; zero broker-visible
  behavior change.

## [1.28.4] - 2026-07-23

### Fixed
- **lee-branding now bundles Minion Pro — flyers stop falling back to Georgia
  (gi-plugins#127).** The Lee brand guidelines name Minion Pro as the accent/headline
  serif, but the font was never shipped with the skill, so every rendered flyer
  substituted Georgia. The skill now carries 8 brand-relevant WOFF weights (converted
  losslessly from David's licensed Adobe OTFs, which are bundled alongside for
  re-conversion) plus the matching `@font-face` block in `SKILL.md`. Per PR #128, the
  same OTFs were also pushed to the Claude Design system project at the paths its
  `tokens/fonts.css` already referenced. Licensing note (commercial Adobe font) is
  flagged in `fonts/README.md`.

## [1.28.3] - 2026-07-23

### Fixed
- **Connector-auth copy now retries before it reconnects (gi-plugins#135).** A live
  incident (2026-07-23) proved Claude's app can display a tool call as auth-failed
  while the Worker's audit log shows the same call authorized and served — the broker
  was walked through a pointless sign-in for a connection that was never broken. The
  canonical connector-auth block now ladders the response: on the FIRST auth-looking
  failure with the lee-raleigh tools loaded, the broker is told this is most likely a
  Claude glitch (Anthropic's side, not the Lee tools) and to reply "you do have
  access — try again"; only a SECOND consecutive failure — or the tools missing from
  the session entirely (the genuine-disconnect signature) — gets the full
  sign-in walkthrough. Both replies now carry the david@groundedintelligence.io
  escalation contact. Propagated to all 19 lee-raleigh-riding skills via
  `scripts/sync-connector-auth.sh`. Copy/guidance only — zero changes to the auth
  system.

## [1.28.1] - 2026-07-20

### Fixed
- **Connector-auth guidance across all 19 lee-raleigh-riding skills (gi-plugins#117).**
  Two broker-facing failure modes, one fix: (A) an agent could *reason* itself into a
  false "connector not authorized" refusal without ever attempting a tool call (Bonner,
  2026-07-15 — the call worked on the first real attempt); (B) on a genuine dropped
  OAuth grant the improvised fallback copy ("authorize via /mcp or the connector
  settings") was too developer-y to self-serve (James Bailey, 2026-07-08). Every skill
  that rides the lee-raleigh connector now carries a canonical **attempt-the-call-first**
  directive (only a tool-level `401`/`invalid_token` from an actual call counts as
  unauthorized) plus warm, broker-legible reconnect steps linking
  `/setup#connect-sign-in` (including the "expired link → just request another" step).
  Canonical source: `plugins/lee-internal-comps/shared/connector-auth.md`, propagated by
  `scripts/sync-connector-auth.sh`, drift-guarded by
  `scripts/test/connector-auth-guidance.test.sh`. The owner-mailing-list "Connector
  unavailable → try again in a few minutes" row is split into transient vs auth
  failures. Copy/guidance only — zero changes to the auth system.

## [1.28.0] - 2026-07-20

### Removed
- `tenants-in-market` ingest skill retired (gi-plugins#98). The Triangle Pairlist
  ingest now runs as a deterministic GI-operated Mac Studio job
  (`grounded-intelligence/40_delivery/pairlist-ingest/`): Gmail REST manifest,
  claude-CLI screening, writes through `lee_tenant_requirement_write` with a
  bearer token. Removes the Cowork Scheduled Task fragility (silent connector
  failures, 2-day window loss) behind the 2026-06-15 dark-run incident. The
  broker query surface (`tenant-search`) is unchanged; its notes now point at
  the server-side ingest.

## [1.27.0] - 2026-07-15

### Removed
- **`daily-debrief` skill removed — the in-plugin daily debrief is fully retired, replaced by
  an automated email flow.** The daily analyst debrief now runs as an automated email loop: a
  Mac Studio mailer emails the analyst their daily debrief and captures the reply into D1
  (`debrief_mailer_log` for sends, `debrief_log` for replies), and the Slack "Lee Plugin Status"
  digest surfaces a live "Daily debrief" line off those tables. The Worker-side MCP tools that
  backed the interactive skill (`lee_debrief_write`, `lee_debrief_fetch_yesterday`) were
  deprecated / unregistered in the lee-raleigh-mcp server, and this release removes the last
  in-plugin piece — the `/lee-daily-debrief` Cowork skill (`skills/daily-debrief/`). Its
  description clause and both READMEs' mentions are dropped. The skill was analyst-only
  (never broker-invocable). Historical CHANGELOG entries about it (the gi-plugins #99 rework)
  are left intact as history.

## [1.26.0] - 2026-07-10

### Changed
- **`lee-branding` now leads with branding what you're building in the chat, not the Claude Design setup (#118).** The skill shipped optimized for the wrong primary path — "set up the Lee design system in Claude Design" — when the everyday broker case is a quick riff: "make me a PDF of this and make it look good," "brand this," "make this on-brand for Lee." The skill now leads with applying the Lee brand to a deliverable in the same session (flyer, one-pager, BOV/OM section, deck slide, chart, email header), with concrete render-time guidance an agent can act on: the exact `@font-face` block to embed the bundled Avenir Next WOFFs (with the Cyrillic-cut family-name and `woff`-format gotchas called out), the color rules (Lee Red `#98002E` as an accent — never a full-document wash — Charcoal for small text, secondary/accent palettes for charts only), and the logo placement rules (minimum size, clear space, the never-do list). The one-time Claude Design setup is retained but reframed as the marketing-team edge case. Because the frontmatter description now routes plain broker asks like "make this look good for Lee" to the skill, brokers reach it in more of the moments they'd want it — a router/behavior change, hence a minor bump. No asset, Worker, or MCP change.

## [1.25.0] - 2026-07-10

### Added
- **`lee-branding` skill — apply the official Lee & Associates brand to any deliverable (#118).** Brokers no longer have to hand-feed Bonner's brand zip to Claude Design each time. The skill ships the official Lee brand package — logo (SVG + PNG), the full color system (`brand-colors.json` + guidelines), the Avenir Next brand fonts (WOFF), and the logo/color usage rules — and a contract telling Claude how to apply Lee branding two ways: set up the Lee design system in Claude Design once (so every flyer/deck/graphic comes out on-brand automatically), or brand a specific deliverable on the spot. Brand assets are bundled in the skill because the Cowork sandbox can't fetch them over the network at runtime; the skill is now the canonical on-disk home for the Lee logo, and the existing per-skill logo copies in `internal-comps` / `external-comps` are documented as the deliberate sandbox-side pattern. No Worker change — the Worker already serves the logo and bundles the fonts for its own server-side renders. Sourced from Bonner's 2026-07-09 "Lee & Associates Design Package."

## [1.24.5] - 2026-07-09

### Fixed
- **Owner mailing lists can now be filtered by land class in every county, not just Wake (lee#140).** Asking for "vacant / commercial / industrial / residential / agricultural" owners used to return zero results outside Wake County, because each county records land use in its own vocabulary and the filter only understood Wake's codes. The `owner-mailing-list` skill now documents that land-class filtering works per-county (Wake, Durham, Johnston, New Hanover, Chatham), and relays the tool's new `land_class_no_data_counties` field so the broker is told when a county can't be land-class filtered — Lee and Orange (their land-use data is empty in our mirror) and New Hanover / Chatham for "vacant" specifically (no vacant category) — instead of getting a silent empty list. Ships with the lee MCP fix (`0.25.0`).

## [1.24.4] - 2026-07-09

### Fixed
- **Business Key Facts now explains when a report is simplified to stay under the render size limit (lee#212).** The `pull_business_key_facts` MCP tool used to fail with an opaque error on large-footprint addresses (e.g. 527 Keisler Dr, Cary) when the full street-map tile mosaic pushed the PDF past its size cap — the broker got nothing. The tool now degrades instead: it falls back to a simplified radius-ring map (PDF still delivered), or, if it's still too large, returns the key facts with no PDF and a note to re-run. This skill now relays the new `degraded_note` field to the broker verbatim so a simplified map or missing PDF is explained rather than silent. Ships with the lee MCP fix.

## [1.24.3] - 2026-06-25

### Fixed
- **Comps summary stats no longer print "$0.00" from placeholder zeros (#82).** Roughly 89 of 225 staging sale comps store `price_per_sf=0` (and similar) as an "unknown-value" placeholder, not a real value. Including those zeros in the workbook Summary sheet and the draft-email summary printed misleading figures like "Median $/SF: $0.00." All three comps skills now exclude non-positive values from the stat aggregations (`sale_price`, `price_per_sf`, `effective_rate`, `asking_rate`, and square footage; a zero in one SF column now falls through to the next). The comp **count is unchanged** — placeholders are excluded from the math, not dropped from the row set. Mirrors the Worker-side fix already in the lee MCP `summary_stats.ts`.
- **Unified all-comps table now sorts by true date across both sources (#62).** The default `internal-and-external-comps` skill merged internal (MM/DD/YYYY) and external (ISO YYYY-MM-DD) rows and sorted them as raw strings, which interleaved the two formats out of order. Rows now sort by a parsed date, most-recent-first, with missing or unparseable dates falling to the bottom instead of jumbling the order.

## [1.24.2] - 2026-06-25

### Fixed
- **owner-mailing-list CSV "the file path is too long" error on Windows (#7 generalization).** A scan of every skill for local file outputs found one other writer with the same Windows-218 exposure that 1.24.1 fixed for comps: the owner mailing-list CSV. Its 1.24.0 guard capped the filename at 60 chars, but on Cowork's ~190–210-char Windows session directory a 60-char name still blows past Excel's 218-char open limit, so the CSV wouldn't open. It now writes to a tiny fixed name — `o.csv` (enumerating `o1.csv`, `o2.csv`, … for a second pull in the same session) — which keeps the full path under 218. The descriptive address no longer enters the filename; rename the file once it opens. Same convention as the comps `c.xlsx` fix, now documented in the comps architecture doc (§5 DELIVER) as the rule for all broker file outputs. (#112)

## [1.24.1] - 2026-06-25

### Fixed
- **Comps Excel "the file path is too long" error on Windows (Will / Bonner).** Windows brokers couldn't *open* the comps workbook: Excel refuses to open any file whose full path exceeds 218 characters, and Cowork's per-session output directory already runs ~190–210 characters deep before the filename — so a descriptive name like `comps-industrial-2026-05-28.xlsx` pushed the full path over the limit. The skill can't relocate that directory, so the only lever is the filename. All three comps skills (`internal-comps`, `external-comps`, `internal-and-external-comps`) now write the workbook to a tiny fixed name — `c.xlsx` — which keeps the full path safely under 218. A second comps pull in the same session enumerates `c1.xlsx`, `c2.xlsx`, … so an earlier deliverable is never overwritten. The descriptive title still appears on the Sheet 1 tab; rename the file to whatever you like once it opens. **Supersedes the 1.23.0 flatten-to-basename guard**, which still overflowed because a 50-char filename on top of the ~200-char session dir exceeded 218; a fixed tiny name is the only thing that fits. Enforced in code (the helper forces the name regardless of what the skill builds), so it can't regress. (#7)

## [1.24.0] - 2026-06-24

### Added
- **`owner-mailing-list` can now build a list of *building / improved-parcel* owners, not just land owners.** When the broker asks for "owners of the buildings near…" / "improved parcels within…" (anything mentioning buildings / improved / built / structures), the skill passes `improved_only: true` to `pull_owner_mailing_list` and the result is limited to parcels that have a structure on them. The CSV gains two building-relevant columns — `building_sf` (building square footage) and `year_built` — so the output is no longer just acreage + land class. A "vacant land" request still pulls raw land as before. When a county in the search area carries no building data yet (the tool reports this per-query in `no_building_data_counties`, derived from live data — not a hard-coded list), the skill names that county and offers to pull all owners or filter by acreage instead, so a thin/empty improved result is explained rather than read as "nothing matched." Pairs with lee-raleigh-mcp v0.19.0. (#176)
- **owner-mailing-list path guard (#7 slice).** The owner-mailing-list CSV save site now flattens any caller-prepended directory to a short filename in the working directory (mirrors the comps-Excel guard shipped in 1.23.0), so the Windows 218-char path limit can't leave the CSV unopenable. (#7)

## [1.23.0] - 2026-06-24

### Changed
- **Comps Excel: three broker-flagged lease/export fixes (Will Fogleman, 2026-06-17 feedback).**
  - **External lease comps no longer show building size as "Leased SF."** The external platform's external lease data carries the building footprint, not the true leased premises area, so in the unified all-comps output (`internal-and-external-comps`) the "Leased SF" column now renders **blank** for external lease rows instead of mislabeling building size as leased area. Internal (Dealius) lease rows are unchanged — they keep their real leased area. (#105)
  - **Removed the "Lease Executed" column** from the internal lease comps Excel, per broker request. The lease execution date is still used to filter and sort the results; it is just no longer shown as a column. (#106)
  - **Lease comps Excel number formatting is now correct.** The internal lease export had several columns formatted as the wrong type (Lease Type and Tenant rendered as currency, TI $/SF rendered as a plain integer) because the formatting was keyed to fixed column positions; it is now derived from each column by name, so Leased SF / Building SF / Free Rent read as numbers and the $/SF columns read as currency — and the layout can change without re-introducing a mismatch. (#106)

### Fixed
- **Comps Excel workbooks now open reliably on Windows regardless of save location (#7).** The Windows 218-character path limit could leave a comps workbook unopenable when a deep folder path was prepended to the filename. Every comps Excel skill (`internal-comps`, `external-comps`, and the unified `internal-and-external-comps`) now flattens the output to a short filename in the working directory via one shared guard, so a deep or long path can no longer produce a file Excel refuses to open. (#7)

## [1.22.1] - 2026-06-23

### Fixed
- **`owner-lookup` (the most-used skill) now handles same-address duplicates and accepts a parcel ID/PIN.** Two field gaps from David's 2026-06-11 QA: (1) when the same street address exists twice in one county (e.g. `100 Walnut St` in both Cary and Wendell, both Wake), the skill no longer tells the broker to "pass a county" (which can't disambiguate a same-county collision) — the tool returns a candidate list (`parcel_id — locality (county), site address`) and the skill re-runs with the chosen `parcel_id`; a city in the input (`100 Walnut St, Cary NC`) auto-picks in one call. (2) A broker can now paste a PIN — the skill passes it as `parcel_id` (or a bare PIN in `address`) and gets the parcel directly. Frontmatter description, Process, Error-handling, and Examples updated; router contract (G12) now advertises PIN input. Pairs with lee-raleigh-mcp v0.18.3. (#126)

## [1.22.0] - 2026-06-23

### Added
- **New skill: `/site-infrastructure` — who serves this site.** The documented utility baseline for any NC address, five rows in one pull: broadband (broker-verified row with a parcel-centered FCC National Broadband Map link to start from), electric (retail service territory, overlapping territories all named), water and sewer operators (county GIS, statewide service-area maps, and a curated registry, in that order), and natural gas provider. Every row carries a confidence tag and its source, so the answer is honest about how documented it is. Returns the rows inline plus a flyer-ready `si-card` fragment and a Lee-branded component PDF. Capacity figures (MW, gpm, allocation, pressure) stay utility-conversation territory by design. Requires lee-raleigh-mcp v0.17.0 (`pull_site_infrastructure`, live in prod since 2026-06-11). (gi-plugins #93, closes #68)

## [1.21.0] - 2026-06-23

### Added
- **New skill: `/drive-time-isochrones` — how far can you get from a property in N minutes.** Drive-time reach polygons (isochrones) for any NC address: 5/10/15 minutes by default, configurable 1–60, by car, on foot, or by bike. The trade-area answer that replaces crude mile rings — per-band reach areas in sq miles, isochrone GeoJSON for downstream maps, and a Lee-branded map card PDF (reach polygons over an OSM basemap, fit-to-content flyer component). Free-flow travel times in v1 (no rush-hour adjustment). Requires lee-raleigh-mcp v0.16.0 (`pull_drive_time_isochrones`, live in prod since 2026-06-11). (lee#24, gi-plugins #92)

## [1.19.3] - 2026-06-22

### Fixed
- **`daily-debrief` is now completable by a broker unassisted (gi-plugins #99).** Will couldn't finish the debrief through the skill — the interview dumped multi-part questions (3 fields per plugin session, 5 numbered questions per off-plugin ask) that he answered as one long chat reply, so a stray edit wiped several answers and his place at once, and nothing told him it was safe to restart. He fell back to plain-email debriefs, which blinds the Stage-4 validation funnel. The interview is rewritten to ask **one question per turn with one-word answers**, **save and confirm after each session/ask** ("Saved ✅"), open with a one-line orientation, and explicitly tell him re-running is safe (UPSERT, never duplicates) — so a chat mishap costs one keyword, not the session, and recovery is just re-running. SKILL.md only; the `lee_debrief_write` / `lee_debrief_fetch_yesterday` tool contract is unchanged.

## [1.19.2] - 2026-06-12

### Fixed
- **Lee-branded the comps Excel workbooks on the main sheet (gi-plugins #90).** Opening a comps Excel now shows the Lee & Associates logo at the top of the first (comps) sheet and the official Lee Red (`#98002E`, PMS 202) on the header row — across both `internal-comps` and `external-comps`, sale and lease. Previously `external-comps` shipped a generic dark-blue header with the logo buried on the Methodology sheet, and `internal-comps` used a near-but-not-official maroon. Palette now matches the brand source used by the Worker renders (lee-and-associates #28). A missing logo asset stays non-fatal but is now surfaced as a workbook warning so an unbranded workbook can't ship unnoticed.

## [1.19.1] - 2026-06-11

### Removed
- **`business-list` pulled from the broker surface pending a cost redesign (gi-plugins #64, back to Backlog).** Live runs priced at $3-88 per census against a <$1.00/run tolerance — the sweep architecture over-subdivides on Google relevance padding. The Worker tools stay live for internal research only; the skill returns once the redesign meets tolerance.

## [1.19.0] - 2026-06-11

### Added
- **`business-list`: market census of active businesses (gi-plugins #64).** A broker names genre(s) + market ("all the boat dealerships active in NC") and gets a complete, deduplicated, Lee-branded 3-sheet Excel workbook (Likely Matches / All Results / Method) via a ~30-day signed link. Runs as a background sweep with live progress — county/city in about a minute, statewide in 5-15 minutes. Backed by lee-raleigh-mcp v0.15.0 (`pull_business_list` + `check_business_list`).

## [1.18.0] - 2026-06-11

### Added
- **New skill: `/parcel-lookup` — the full county property record for an address.** Owner of record + mailing address, PIN, lot size, building SF, year built, tax assessed value, last sale, zoning code with a link to the ordinance, and the last 5 years of building permits — the pre-tour / pre-call homework in one shot. Returns the record inline plus a flyer-ready `pl-card` fragment and a one-page Lee-branded Property Facts PDF. Covers Wake, Durham, New Hanover, Lee, Johnston, Orange & Chatham NC (zoning + permits depth varies by county; permits cover Raleigh, Cary, Durham & New Hanover). Requires lee-raleigh-mcp v0.13.0 (`pull_parcel_lookup`). (lee#22)

## [1.17.0] - 2026-06-10

### Added
- **tenant-search** — new broker skill: "what tenants are in the market for 5-10k SF industrial in Garner?" Searches the shared tenant-requirements pool (Triangle Pairlist-sourced, ingested continuously since June 2026) and returns matches with the originating broker's contact to pair a listing. The query half of tenants-in-market — the ingest has been capturing requirements since v1.5.0; this is the first way brokers can read them. Requires lee-raleigh-mcp v0.13.0 (`pull_tenants_in_market`). (#27)

## [1.16.0] - 2026-06-10

### Added
- **New skill: `/development-pipeline` — what's being built around an address.** Pull the commercial development pipeline within a radius of any covered NC address (Triangle, Harnett, Lee County NC, Wilmington/New Hanover — 12 municipal feeds): stage counts from Submitted through Under Construction, a sorted project table, flyer-ready narrative bullet lines ("115,846 SF of multifamily under construction 2.2 mi away"), and a drop-in flyer component PDF. You pick the product types — office, retail, industrial, multifamily, mixed use, hospitality, institutional, residential, or all of it — and the skill reports exactly what your selection filtered out, by category. Infrastructure noise (sewer extensions, retaining walls, repaints) and amendment duplicates are screened automatically. Data is pre-staged nightly into the Lee data engine, so pulls are fast and don't depend on county websites being up. (#66)

## [1.15.0] - 2026-06-10

### Changed
- **owner-mailing-list now answers in seconds, with no browser extension.** The skill
  queries the new `pull_owner_mailing_list` MCP tool on the lee-raleigh connector,
  which reads a pre-staged statewide NC OneMap parcel mirror — replacing the
  Claude-in-Chrome browser pipeline (60–180s per pull, extension required). Same
  request, same CSV (owner, mailing address, site address, acreage, land class),
  private owners only, deduplicated by mailing address.
- Owner data refreshed statewide from NC OneMap, with parcel coordinates for every
  covered county (New Hanover gains coordinates for the first time) and three new
  counties added: Orange, Johnston, Chatham. Coverage: Wake, Durham, New Hanover,
  Lee, Orange, Johnston, Chatham.

## [1.14.2] - 2026-06-10

### Fixed
- **`tenants-in-market` scheduled ingest now completes.** Past scheduled runs pulled full 60-85KB Pairlist digest threads into the session and batch-fetched them in parallel, overflowing the context window mid-run — the session reset, restarted the Gmail search from scratch, and stalled at the first batch all day (Jun 2: ran 05:33-21:45 without finishing; Jun 3: froze at 9%). The skill now screens each email from a small extract (subject + snippet + at most ~2KB of the single message body — never a thread fetch), works strictly sequentially in batches of 5 with each UPSERT write completing before the next message, caps the stored `raw_json` at the screening extract, and recovers from any interruption by re-running from a fresh search so re-runs converge instead of thrashing. Also reconciled the scheduled-task cadence claim (any cadence from hourly to daily converges) and removed the stale `smoke-2026-06-02` row from the prod tenant-requirements store. (#61)

## [1.14.1] - 2026-06-09

### Fixed
- **`comp-map` rings now scale to the search radius** instead of a fixed 1/3/5. Caught in Stage-4a Cowork ship-QA: a 1-mile search radius still offered "1/3/5 mile rings", drawing 3- and 5-mile rings well outside where any comps exist. The SKILL.md now instructs rings as round-number bands that end at `radius_mi` and never exceed it (5 mi → 1/3/5; 1 mi → 0.25/0.5/1). Intake-guidance only; no MCP/Worker change. (#80)

## [1.14.0] - 2026-06-09

### Added
- **`comp-map` skill** — a broker asks "map the comps around [address]" / "show the comps near my listing" (or `/comp-map <address>`) and gets a **Lee-branded competitive-set map**. **Deal mode** (a subject) maps the comps around it — numbered pins ordered by distance, optional radius rings, and a paired comp table whose rows match the pins. **Database mode** (no subject) maps the whole internal comp set, or a broker's deal history (`map every deal my team closed in this market`). Returns a **shareable ~30-day interactive Google map link** (forwardable to a client, no login), a **print-ready static PNG**, and a **`csm-*` comp-table fragment** for flyers/OMs/BOVs. A single map shows at most ~10% of the database (a governance guardrail, surfaced when it fires). Distance rings only in v1 — drive-time bands are a fast-follow (gi-plugins#77). Thin orchestrator over the lee-raleigh-mcp `pull_comp_map` tool (lee-raleigh-mcp v0.10.0; compose/render ported from the `map-builder` engine, comp geocodes pre-staged in D1). (#65)

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
- **`lee-flyer-brief` skill** — a broker says "build a flyer for my listing" (or drops a listing agreement) and gets walked through assembling everything a marketing flyer needs: the skill auto-pulls owner of record, business key facts, and demographics, then runs the comp set, key facts, and demographics each through a **present → augment → select → narrate** loop so the broker adds their own data and picks exactly what appears. It writes a provenance-tagged **flyer brief** (every figure tagged `internal comps DB` / `external (comps cache)` / `broker-provided` / `listing agreement` / `county record` / `Census`) and hands the broker carry-over instructions into **Claude Design** (Lee design system) for visual polish. Replaces Lee marketing's Formstack "New Listing Marketing Request" intake. Write-back of broker-provided comps + the subject listing to the comps DB is **confirmation-gated** (no auto-write). Prototype validated through Rings 1–3 (simulated + two live Cowork runs + Claude Design number-fidelity diffs). (#67)
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
- **Unified "all comps": external Comp ID now shows a short, broker-readable id** (external property id / `external_comp_id`) instead of the 64-char `external_id` address hash that was dumped into the Comp ID column. Internal ids unchanged. (#57)

## [1.8.0] - 2026-06-02

### Added
- **`add-comps` skill** — turn a contributed comp set a broker pastes, forwards, or uploads (a forwarded email with several brokerage comp tables, an xlsx/csv export, a pasted tab/pipe table, or a screenshot) into canonical records tagged by source and provenance, and ingest them into the comps database as a **third source** alongside internal Dealius + external the external platform. Handles lease and sale; flags (never drops) incomplete rows for review. Brokers can then query across all three sources from one surface via the new `pull_unified_comps` MCP tool. Backed by lee-raleigh-mcp v0.7.0 (`comp_imports` + `comps_added` tables, a unit-reconciled `comps_unified` view, and the `lee_comps_add_write` MCP tool). (#11, coupled with lee-and-associates #64)

## [1.7.1] - 2026-06-02

### Fixed
- **`owner-mailing-list`: faster, cleaner pulls (post-live-QA).** Three fixes from the first live runs: (1) the skill now drives the **Claude in Chrome** extension's `javascript_tool` instead of "Control Chrome" (whose JS execution fails) — no more wasted retries and a failed false-start; (2) the whole fetch → dedupe → CSV pipeline now runs in **one** browser call (`buildOwnerMailingCsv` in `arcgis_query.js`, node-tested) and the file is written in deterministic line-batches, cutting a pull from ~139 tool calls to a handful; (3) results are **filtered to private owners** — government, municipal, exempt, HOA/COA, cemetery, utility, and railroad parcels (plus blank-owner rows) are dropped, so the list is broker-mailable prospects. Example: New Hanover went from 71 raw parcels to 29 private owners; Onslow 76 → 46. (#1)

## [1.7.0] - 2026-06-02

### Added
- **New skill: `internal-and-external-comps` — the default "all comps" experience.** When a broker asks for comps **without** saying internal or external, this skill runs both the internal (Dealius) and external pulls in parallel and returns **one** combined deliverable: a chat table, an Excel (an "All Comps" sheet plus per-source detail sheets), and **one Lee-branded unified PDF**, with every row tagged by **Source** (`Internal — Dealius` / `External`). No dedup — a property in both sources shows as two tagged rows. Works for sale and lease. Explicit "internal comps" / "external comps" requests still route to the single-source skills. The unified PDF is powered by the new `cache_external_rows` MCP tool + `unified` template on `lee-raleigh-mcp` v0.6.0. (#29, coupled with lee-and-associates#45)

## [1.6.0] - 2026-06-02

### Added
- **New skill: `owner-mailing-list`.** Build a deduplicated owner + mailing-address list for an area + criteria request — e.g. "owners of 2–5 acre vacant land within 3 miles of 100 Walnut St, Cary." The skill drives Claude-for-Chrome against a county's public ArcGIS parcel service to find matching parcels, then returns a clean CSV of owner names + mailing + site addresses, deduped by mailing address. Covers **19 NC counties** (Triangle, Sandhills, Wilmington-coast, Triad, eastern NC), each live-validated against its parcel service. Requires the `chrome-control` extension; the skill detects it and walks the broker through enabling it if absent. (Avery-label printing is a separate forthcoming skill.) (#1)

## [1.5.3] - 2026-06-02

Reconciling release: four broker-facing / owner-lookup changes had merged to `main` since `v1.5.2` without a version bump. Bundled here so the version string matches `main`.

### Fixed
- **internal-comps: LAND sale comps price on `$/Acre`, not `$/SF`.** For a sale pull where `asset_type == "land"`, the Excel shows a `$/Acre` column (`price_per_acre = sale_price / acres`, whole-dollar currency, blank when acres is null/zero) where `$/SF` used to be; the `Acres` column stays. Non-land asset types and all lease pulls are unchanged. $/SF is meaningless for raw land. Broker request from Mike Glennon. (#28 / PR #39)
- **owner-lookup: Lee County verify link uses `mode=realprop`, not `parid`.** The Lee County verify-footer link used a Tyler mode that throws; it now opens the working real-property search. (#18 / PR #44)
- **lee-internal-comps: stripped the "the external platform" brand from broker-facing surfaces.** (#6 / PR #37)

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
  the Dealius/external data is before relying on it.
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
