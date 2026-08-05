# gi-plugins — Repo Instructions

Cross-cutting context for the GI plugin marketplace. Per GI convention, individual
skills self-document in their own `SKILL.md` — do not register per-skill sections here.

## Design System (Claude Design)
Lee & Associates now has a **Claude Design design system** — the source of truth for
Lee broker-facing UI. Any skill in this repo that renders a Lee-facing visual artifact
(listing flyer, broker brief, BOV/OM fragments, demographic/infographic cards, map
cards) should conform to it rather than an ad-hoc palette.
- **Project:** "Lee & Associates Design System" — https://claude.ai/design/p/ee2e9025-1b6f-4bf8-89b7-4b415fb09b09
- **Access:** `claude_design` MCP (auth once via `/design-login`). Before building or
  restyling Lee UI, load it with
  `get_claude_design_prompt(design_system_id="ee2e9025-1b6f-4bf8-89b7-4b415fb09b09")`.
- **Brand package on disk:** `plugins/lee-internal-comps/skills/lee-branding/`
  (guidelines, colors `#98002E`, Avenir Next fonts, logo, `claude-design-setup.md`).
  The `claude-design-setup.md` describes how the system was *built*; the system is now
  live at the project above — reference it, don't rebuild it.
