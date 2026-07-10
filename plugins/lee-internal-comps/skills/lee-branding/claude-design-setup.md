# Add the Lee & Associates Brand to Claude Design

This package gives Claude everything it needs to design on-brand for Lee & Associates:
the brand standards, the exact color values, the logo, and the brand fonts. You feed these files in once
to build your **design system**, and after that every flyer, one-pager, deck, or graphic
Claude makes follows the Lee look automatically, without you re-explaining the rules each
time.

Takes about 5 minutes, and you only do it once per organization.

---

## What's in this package

| File | What it is |
|---|---|
| `lee-associates-brand-guidelines.md` | The full Lee brand standards (logo rules, colors, fonts, photography, templates). This is the main document Claude reads to learn the rules. |
| `brand-colors.json` | The exact color values (HEX, PMS, CMYK) in a clean, machine-readable form. |
| `lee_logo.svg` | The logo as a vector file (sharpest, preferred). |
| `lee_logo.png` | The logo as an image file (use if a tool will not take the SVG). |
| `fonts/` | The Avenir Next brand font files (WOFF) -- the real Lee primary typeface, so designs render in-brand instead of a fallback. See `fonts/README.md`. |
| `claude-design-setup.md` | This guide (Markdown). |

The brand standards were transcribed from Lee's official *Brand Standards and Usage
Guidelines* (updated February 2021). The original PDF lives in the Marketing & PR section
of lee-hq.com and remains the source of truth.

---

## How to build the Lee design system

Claude Design builds **one design system per organization** and shares it with the whole
team. One person sets it up, publishes it, and everyone else inherits it. There is no single
button labeled "Create design system." You create the system by running the onboarding flow
and feeding it the brand files below.

1. **Open Claude Design.** Sign in at **claude.ai** and go to **claude.ai/design**.

2. **Pick your organization.** In the **lower-left corner**, click the current organization
   name and **select your Lee & Associates organization** (or create it if it does not exist
   yet). The design system is tied to this organization.

3. **Open the design-system setup.** Go to **Organization settings**, then the
   **Design systems** section, and start the **onboarding** (setup) flow. On a brand-new
   organization this flow often opens on its own right after step 2. Running this flow is what
   creates the design system.

4. **Drop the brand files in.** The onboarding flow asks you to add the materials that
   represent your brand. This is where the files in this package go. Add:
   - **Brand guidelines:** upload `lee-associates-brand-guidelines.md`, the document Claude
     reads to learn the red, the fonts, the logo do's and don'ts, and the photography style.
   - **Logo:** add `lee_logo.svg` (SVG preferred; add `lee_logo.png` as a backup).
   - **Colors:** upload `brand-colors.json`, or paste the hex codes when Claude asks for your
     palette.
   - **Fonts:** add the files in the `fonts/` folder (Avenir Next, the Lee primary typeface)
     so Claude renders the real brand type instead of a fallback.

   > You only need one source to get started, but adding all of them gives Claude more to
   > work with, so use the whole package.

5. **Let Claude generate the system, then check it.** Claude builds your design system: a
   color palette, typography, and reusable components. Run a quick test prompt ("make a
   simple listing flyer in our brand") to confirm it looks like Lee.

6. **Publish it to the team.** Turn the **Published** toggle **on** so the Lee design system
   is available to everyone in the organization.

### To change it later

Open Claude Design, click **Open** next to the Lee design system, then click **Remix** in
the **upper-right corner** to open a chat where you can request changes in plain language
(for example, "use Charcoal for body text under 10pt" or "add the navy as a secondary").

---

## How to use it once it's set up

Just ask in plain language. For example:

- "Make a one-page listing flyer for this property, on brand for Lee & Associates."
- "Design a market-report cover using our brand colors and fonts."
- "Build a LinkedIn graphic for this new deal in the Lee style."

Claude pulls the Lee red (`#98002E`), the right fonts, the logo, and the usage rules from
your design system automatically. You do not need to paste the colors or rules into every
request.

---

## The brand in one glance

- **Primary red:** `#98002E`. Slate `#7E8083`, Charcoal `#303C42`, White `#FFFFFF`.
- **Primary font:** Avenir Next. Fallback: Nunito Sans, then Arial.
- **Headline / accent font:** Minion Pro. Fallback: Georgia.
- **Logo:** never redraw, recolor, stretch, skew, or add shadows. It should appear at least
  once in every communication. Minimum width 1.125 in, with clear space equal to the height
  of the icon on all sides.
- **Accent colors** (Merlot, Bright Red, Green, Mint) are for charts and infographics only,
  used sparingly. Never the main color of a document.
- **Tagline:** LOCAL EXPERTISE. INTERNATIONAL REACH. WORLD CLASS.

Full detail is in `lee-associates-brand-guidelines.md`.

---

## Questions

For brand asset access or approvals, the corporate contact in the guidelines is
**Pamela Murphy, Director of Marketing & PR** (pmurphy@lee-associates.com), or
visit **lee-hq.com**.
