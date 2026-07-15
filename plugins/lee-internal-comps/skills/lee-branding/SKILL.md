---
name: lee-branding
description: Make anything you're building for a Lee & Associates broker look on-brand — apply the Lee logo, the brand red, and the Avenir Next fonts to a flyer, one-pager, deck, chart, PDF, or email header right here in the chat. Use when a broker says "make me a PDF of this and make it look good," "brand this," "make this on-brand for Lee," "add the Lee logo," "use our brand colors," or is riffing on a deliverable and wants it polished to the Lee look. Ships Lee's official brand package on disk (logo, colors, guidelines, fonts) so you apply it without asking the broker for files. Also covers the one-time Claude Design setup for the marketing team.
---

# Lee & Associates Branding

Make what you're building for a Lee broker look like Lee. This skill carries Lee's
official brand package — the logo, the exact colors, the brand guidelines, and the
Avenir Next brand fonts — on disk, right next to this file. You never have to ask the
broker to hand over brand files; apply the brand directly to whatever's being composed.

## Primary use: brand a deliverable you're building right now

The common case: a broker is riffing in the chat, wants a quick-turnaround deliverable
— a listing flyer, a one-pager, a BOV/OM section, a deck slide, a chart, an email
header, a cover — and wants it to come out on-brand for Lee. Do it in place, in this
session. You do **not** need to leave for another tool, and you do **not** need Claude
Design set up first. Everything you need is the bundled assets below plus the render
rules that follow.

When you compose HTML that will be rendered to PDF or image (headless Chrome / print
CSS), wire in the three brand signals — **fonts, color, logo** — like this.

### Fonts — embed the real Avenir Next

The five brand-font WOFFs live in this skill's `fonts/` folder. Embed them with
`@font-face` so the render uses the real Lee typeface instead of a fallback. Two
gotchas baked into the block below: the files are the *Cyrillic* cut whose internal
family names are split, so each face must **declare `font-family: 'Avenir Next'` with
an explicit weight/style** (don't rely on the embedded name); and they're `woff`
(v1), so the `format('woff')` hint matters.

```css
@font-face { font-family:'Avenir Next'; font-weight:400; font-style:normal;
  src:url('fonts/AvenirNextCyr-Regular.woff') format('woff'); }
@font-face { font-family:'Avenir Next'; font-weight:400; font-style:italic;
  src:url('fonts/AvenirNextCyr-Italic.woff') format('woff'); }
@font-face { font-family:'Avenir Next'; font-weight:500; font-style:normal;
  src:url('fonts/AvenirNextCyr-Medium.woff') format('woff'); }
@font-face { font-family:'Avenir Next'; font-weight:500; font-style:italic;
  src:url('fonts/AvenirNextCyr-MediumItalic.woff') format('woff'); }
@font-face { font-family:'Avenir Next'; font-weight:700; font-style:normal;
  src:url('fonts/AvenirNextCyr-Bold.woff') format('woff'); }

/* Minion Pro — accent/headline serif (bundled as WOFF, converted from the licensed OTFs in fonts/minion-pro/) */
@font-face { font-family:'Minion Pro'; font-weight:400; font-style:normal;
  src:url('fonts/MinionPro-Regular.woff') format('woff'); }
@font-face { font-family:'Minion Pro'; font-weight:400; font-style:italic;
  src:url('fonts/MinionPro-It.woff') format('woff'); }
@font-face { font-family:'Minion Pro'; font-weight:500; font-style:normal;
  src:url('fonts/MinionPro-Medium.woff') format('woff'); }
@font-face { font-family:'Minion Pro'; font-weight:600; font-style:normal;
  src:url('fonts/MinionPro-Semibold.woff') format('woff'); }
@font-face { font-family:'Minion Pro'; font-weight:600; font-style:italic;
  src:url('fonts/MinionPro-SemiboldIt.woff') format('woff'); }
@font-face { font-family:'Minion Pro'; font-weight:700; font-style:normal;
  src:url('fonts/MinionPro-Bold.woff') format('woff'); }

:root { --sans:'Avenir Next','Nunito Sans',Arial,Tahoma,sans-serif;
        --serif:'Minion Pro',Georgia,serif; }
body { font-family:var(--sans); }
```

The `url('fonts/...')` paths resolve when the HTML file you render sits in this skill
folder (write your temp HTML here, or point `url()` at the absolute path to these
files). If you're rendering somewhere the relative path won't resolve, base64-embed
the WOFFs into the `src:` instead — the sandbox has no network, so a remote font URL
will silently fall back. **Minion Pro is now bundled** (WOFF in `fonts/`, converted from
the licensed Adobe OTFs in `fonts/minion-pro/`); use it for accent/headline serif.
Georgia stays the sanctioned fallback if a weight is missing — don't invent a substitute.

**Type hierarchy:** Avenir Next Bold (700) for headings, Medium (500) for subheads and
emphasis, Regular (400) for body. Optional Minion Pro / Georgia serif for a headline or
pull-quote accent.

### Color — Lee Red is an accent, not a wash

Pull exact values from the bundled `brand-colors.json`. The load-bearing rules:

- **Red `#98002E`** (PMS 202) is the signature accent — rules, a header bar, a key
  figure, the logo lockup. It is **never the background wash of the whole document**.
- **Charcoal `#303C42`** for body text — and **required** over Slate for any text under
  10pt (Slate `#7E8083` is too light at small sizes). Slate for secondary labels/rules.
- **White `#FFFFFF`** grounds the layout; Lee's look is clean and white-forward with red
  as the punch.
- **Secondary** (Navy `#003146`, Sky `#009AD9`, Frost `#A9C3CB`) and **accent** (Merlot
  `#4E131E`, Bright Red `#CD1442`, Green `#8A941E`, Mint `#6FC9C4`) are **for charts,
  infographics, and diagrams only**, used sparingly — never a document's primary color.
  Green and Mint never appear together; a Merlot/Bright-Red pairing never combines with
  Green or Mint.
- The **icon gradient** (`linear-gradient(145deg,#CD1442 0%,#98002E 65%,#4E131E 100%)`,
  in `brand-colors.json`) is available for a bold signature block when a flat red isn't
  enough — use it deliberately, not as default chrome.

### Logo — place it, never touch it

Use the bundled `lee_logo.svg` (sharpest; preferred) or `lee_logo.png` (when a tool
won't take SVG). Rules that are non-negotiable:

- The logo **must appear at least once** in every deliverable.
- **Minimum width 1.125 in** (~108px at 96dpi). Keep **clear space on all sides equal to
  the height of the icon** — no text or graphic intrudes.
- **Never** redraw, recolor, stretch, skew, rotate, outline, or add a shadow/glow. Never
  reconstruct or re-type it. Never use the icon alone in place of the full logo.
- On a red or dark background, use a white/inverted treatment; one-color use is 100%
  black (or 50% gray) only.

### The brand in one glance

- **Red** `#98002E` · **Slate** `#7E8083` · **Charcoal** `#303C42` · **White** `#FFFFFF`
- **Primary font** Avenir Next (bundled) → Nunito Sans → Arial. **Accent serif** Minion
  Pro (bundled) → Georgia.
- **Tagline:** LOCAL EXPERTISE. INTERNATIONAL REACH. WORLD CLASS.

Full detail — every tint, the photography style, template structures (BOV/OM/flyer),
the double-curve element — is in `lee-associates-brand-guidelines.md`. Read it only when
you need something beyond the above; don't re-read all 451 lines every render. **Never
invent a brand rule that isn't in the guidelines.**

## Edge case: hand the design system to Claude Design

Separate, less-common path — this is marketing-team-shaped work, not the day-to-day
broker riff. When the **marketing team** wants the Lee brand set up **once** in Claude
Design so every design across the org inherits it automatically, or a broker explicitly
asks to "set up the shared Lee design system," walk them through the bundled
`claude-design-setup.md` and stage these files for upload into Claude Design's
design-system onboarding: `lee-associates-brand-guidelines.md`, `lee_logo.svg` (+
`lee_logo.png` backup), `brand-colors.json`, and the five WOFFs in `fonts/`. That's a
one-time org setup; the primary path above is what you reach for on an individual
deliverable.

## Files

- `SKILL.md` — this file.
- `brand-colors.json` — machine-readable color tokens (HEX / PMS / CMYK / RGB, tints, the
  icon gradient). Pull exact values from here at render time.
- `fonts/` — the five Avenir Next WOFFs + a README; the real Lee primary typeface.
- `lee_logo.svg` — the logo as a vector (sharpest; preferred).
- `lee_logo.png` — the logo as an image (240×73 RGBA; use when a tool won't take SVG).
- `lee-associates-brand-guidelines.md` — Lee's full brand standards (logo, colors, fonts,
  photography, templates). Deep reference, not a per-render read.
- `claude-design-setup.md` — the step-by-step guide for the one-time Claude Design setup.

**Canonical brand home.** This skill is the canonical on-disk home for the Lee logo and
brand assets. Other skills that render a Lee-branded deliverable in-session
(`internal-comps`, `external-comps`) bundle their **own** byte-identical copy of
`lee_logo.png` rather than reading this one, because the Cowork sandbox has no outbound
network access at runtime — an in-session skill cannot fetch an asset over the network,
so each carries the file it needs. Those copies are intentional and must stay
byte-identical to `lee_logo.png` here (the asset test enforces the match).

## Access & approvals

For brand-asset access or approvals, the Lee corporate contact in the guidelines is
**Pamela Murphy, Director of Marketing & PR** (pmurphy@lee-associates.com), or
lee-hq.com. Don't promise approvals or invent contacts beyond what the guidelines state.
