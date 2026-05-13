# costar-comps — STASHED 2026-05-13

This skill is intentionally outside `skills/` so it does not surface as a slash command. The bundle is kept in-repo as dormant prior art.

## Why stashed
Replaced by Will's weekly Excel handoff into the `external-comps-db/` ingest pipeline (see docs/superpowers/specs/2026-05-13-external-comps-weekly-excel-design.md, § 3.2). The browser-automation path was fragile (DOM coord drift, headless auth handshakes, rate-limit risk) and was never wired to D1.

## Resurrection cost (estimate from spec § 7.5)
- Move folder back into `skills/`: ~5 min
- Refresh CoStar DOM coords against current UI: a few hours
- Re-run Bonner's validation fixtures: ~1 hour
- Total: ~1 day to bring back online

## Resurrection trigger
Will's weekly export becomes unreliable (he leaves, CoStar changes export UX, file format changes).
