---
name: lee-branding
description: Apply the official Lee & Associates brand to a deliverable — the Lee logo, the brand red, the Avenir Next fonts, and the logo do's and don'ts. Use when a broker says "make this on-brand for Lee," "add the Lee logo," "brand this flyer/deck/one-pager," "use our brand colors," or wants to set up the Lee brand in Claude Design so every design comes out on-brand automatically. Ships the official Lee brand package (logo, colors, guidelines, fonts).
---

# Lee & Associates Branding

Apply official Lee & Associates branding to a deliverable, or set up the Lee
design system in Claude Design once so everything after it comes out on-brand.

This skill carries Lee's official brand package — the logo, the exact colors, the
brand guidelines, and the Avenir Next brand fonts — so you never have to ask the
broker to hand over brand files. It is the same package Lee's marketing team
distributes; the assets live right next to this file.

## Two ways to use it

**1. Set up the Lee design system in Claude Design (do this once per organization).**
This is the highest-leverage path: after it's done, every flyer, one-pager, deck,
or graphic Claude makes for Lee comes out on-brand automatically, without
re-explaining the rules each time. Point the broker to the bundled
`claude-design-setup.md` and have them upload these bundled files into Claude
Design's design-system onboarding flow:

- `lee-associates-brand-guidelines.md` — the brand rules Claude reads.
- `lee_logo.svg` (preferred) with `lee_logo.png` as a backup.
- `brand-colors.json` — the exact color values.
- the five WOFF files in `fonts/` — the real Avenir Next brand typeface.

Then a plain-language prompt like "make a listing flyer on-brand for Lee & Associates"
just works.

**2. Brand a specific deliverable right now.** When the broker wants one output
Lee-branded on the spot (a flyer, a cover, a social graphic), use the bundled
`lee_logo.svg`/`lee_logo.png` and apply the rules below directly.

## The brand in one glance

- **Primary red:** `#98002E`. Supporting: Slate `#7E8083`, Charcoal `#303C42`,
  White `#FFFFFF`.
- **Primary font:** Avenir Next (bundled in `fonts/`). Fallback: Nunito Sans, then
  Arial.
- **Headline / accent font:** Minion Pro. Lee has not provided Minion Pro yet, so
  use the Georgia fallback until it arrives.
- **Tagline:** LOCAL EXPERTISE. INTERNATIONAL REACH. WORLD CLASS.

## Logo rules — never break these

- The logo must appear **at least once in every communication**.
- **Never** redraw, recolor, stretch, skew, rotate, outline, or add shadows/glows
  to the logo. It may never be re-typed or reconstructed.
- **Minimum width 1.125 in.** Keep clear space on all sides equal to the height of
  the icon; no text or graphic may intrude on it.
- The icon is **never** used on its own in place of the full logo.
- One-color use is **100% black** (or 50% gray) — no other tints or colors.

## Color rules

- Secondary colors (Navy, Sky, Frost) and accent colors (Merlot, Bright Red, Green,
  Mint) are **never** the primary color of a document.
- Accent colors are for **charts, infographics, and diagrams only**, used sparingly.
  Green and Mint are never used together; a Merlot/Bright Red pairing is never
  combined with Green or Mint.
- For text smaller than 10pt, use **Charcoal** (`#303C42`), not Slate, for legibility.

Full detail — tints, the icon gradient, photography style, templates — is in
`lee-associates-brand-guidelines.md`. Never invent a brand rule that isn't in the
guidelines.

## Files

- `SKILL.md` — this file.
- `lee-associates-brand-guidelines.md` — Lee's full brand standards (logo, colors,
  fonts, photography, templates).
- `brand-colors.json` — machine-readable color tokens (HEX / PMS / CMYK / RGB,
  tints, the icon gradient).
- `lee_logo.svg` — the logo as a vector (sharpest; preferred).
- `lee_logo.png` — the logo as an image (240×73 RGBA; use when a tool won't take SVG).
- `claude-design-setup.md` — the step-by-step guide for building the Lee design
  system in Claude Design (the broker uploads this + the assets above).
- `fonts/` — the five Avenir Next WOFF files + a README; the real Lee primary
  typeface so designs render in-brand instead of a fallback.

**Canonical brand home.** This skill is the canonical on-disk home for the Lee logo
and brand assets. Other skills that render a Lee-branded deliverable in-session
(`internal-comps`, `external-comps`) bundle their **own** byte-identical copy of
`lee_logo.png` rather than reading this one, because the Cowork sandbox has no
outbound network access at runtime — an in-session skill cannot fetch an asset over
the network, so each must carry the file it needs. Those copies are intentional and
must stay byte-identical to `lee_logo.png` here (the asset test enforces the match).

## Access & approvals

For brand-asset access or approvals, the Lee corporate contact in the guidelines is
**Pamela Murphy, Director of Marketing & PR** (pmurphy@lee-associates.com), or
lee-hq.com. Don't promise approvals or invent contacts beyond what the guidelines
state.
