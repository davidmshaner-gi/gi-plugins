## CRITICAL: Never Use Left-Border Accent Callouts

NEVER render a callout, admonition, note, tip, warning, or "highlight" box with an accent bar
down its left edge — the tinted-background-plus-colored-left-rule pattern. Not in HTML, not in
CSS, not in email, not in slides, not in generated docs, not in artifacts, not anywhere. It is
the loudest visual tell of AI-generated design. **David banned it outright, 2026-08-12. There
are no exceptions and no "sparing use" carve-out.**

This covers every variant, whatever it is called: left-border accent, side rail, accent bar,
admonition block, callout card, notice box, `border-left: Npx solid <color>`, Tailwind
`border-l-4` / `border-l-2`, GitHub `> [!NOTE]` blocks, MkDocs / Docusaurus / Notion
admonitions, and blockquotes restyled into notice boxes.

**Carry emphasis with type and space, never with chrome:**
- Bold or larger type on the lead line, normal type for the body
- A horizontal rule above, or hairlines top and bottom
- Whitespace and position in the hierarchy
- A background tint with NO border at all, if a container is genuinely required

If you catch yourself reaching for a bordered notice box, the answer is plain text, set well.

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

## CRITICAL: Source Neutrality — Never Name Comps-Data Vendors

The comps database replaces the reference spreadsheets brokers already keep. What a broker
chooses to load into it is their own prerogative — the schema accommodates whatever they
bring. Accordingly, no third-party comps-data vendor is named anywhere in this repo: skill
prose, deliverable strings, comments, manifests, CHANGELOG, filenames, commit messages.
Say "external" / "the external platform" instead.
(Policy set by David, 2026-08-14; supersedes the broker-surfaces-only scope of #6.)

- **Client-export test fixtures are the only code exemption** — lee#442 (2026-08-15) landed
  the live-contract renames (external_property_id / external_property_url response fields).
- **Guards (both in CI):** `bash scripts/test/source-neutrality.sh` (repo-wide) and
  `bash scripts/test/no-costar-broker-surfaces.sh` (broker-surface pin).
