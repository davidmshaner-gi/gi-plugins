---
name: lee-branding
description: Make anything you're building for a Lee & Associates broker look on-brand — apply the Lee logo, the brand red, and the Avenir Next fonts to a flyer, one-pager, deck, chart, PDF, or email header right here in the chat. Use when a broker says "make me a PDF of this and make it look good," "brand this," "make this on-brand for Lee," "add the Lee logo," "use our brand colors," or is riffing on a deliverable and wants it polished to the Lee look. Ships Lee's official brand package on disk (logo, colors, guidelines, fonts) so you apply it without asking the broker for files, and checks that bundled package against the current one on every run so a deliverable never goes out against stale brand values. Also covers the one-time Claude Design setup for the marketing team.
---

# Lee & Associates Branding

Make what you're building for a Lee broker look like Lee. This skill carries Lee's
official brand package — the logo, the exact colors, the brand guidelines, and the
Avenir Next brand fonts — on disk, right next to this file. You never have to ask the
broker to hand over brand files. One tool call comes first (below), then you apply the
brand directly to whatever's being composed.

## Before you render anything: pull the brand package

**Every branded deliverable starts with one tool call.** Call the lee-raleigh MCP
tool `pull_brand_package`, passing the `version` value from the bundled
`brand-colors.json` (currently `2021.02`):

```
pull_brand_package({ local_version: "2021.02" })
```

Render from what it returns. It carries the authoritative colors, tints, gradient,
font stacks, tagline and logo rules, plus `usage_rules` — and those are
constraints, not notes (they are what tells you charcoal, never slate, carries
text under 10pt). It also answers the one question this skill cannot answer on its
own: whether the brand package bundled with this plugin is still the current one.
`local_package_current` is that answer, and `notes` tells you what to say if the
two copies have diverged.

**If the call cannot be completed, stop and say so. Do not fall back to the
bundled files.** The fonts and the logo on disk are still there, but a deliverable
built without this call is unverified against Lee's current brand, and going ahead
anyway hides a broker whose plugin was never fully set up.

Which failure you have decides what you say. Work through these in order:

- **`pull_brand_package` is not in your available tools, but the other lee-raleigh
  tools are.** This is a stale tools list, not a broken connection — the tool is new
  and the connector caches its list. Do NOT send them to sign in. Tell them warmly:
  *"One quick thing — open the Lee Raleigh connector, choose Refresh tools list from
  its menu, then ask me again. The brand tool is new and your connector hasn't picked
  it up yet."* Then retry once they confirm.
- **The call returned an authorization error.** Follow the connector-auth ladder at the
  end of this file, and follow it as written — a FIRST auth failure with the lee-raleigh
  tools loaded is usually a Claude glitch, so rule 3's retry offer is the right reply,
  not a refusal. Only a second failure in a row, or the lee-raleigh tools being missing
  entirely, is a real sign-in problem.
- **The call failed some other way** (a timeout, a server error). Never give it the
  sign-in copy. Say the brand service didn't answer, and to try again in a few minutes, because that is not an auth problem.

## Primary use: brand a deliverable you're building right now

The common case: a broker is riffing in the chat, wants a quick-turnaround deliverable
— a listing flyer, a one-pager, a BOV/OM section, a deck slide, a chart, an email
header, a cover — and wants it to come out on-brand for Lee. Do it in place, in this
session. You do **not** need to leave for another tool, and you do **not** need Claude
Design set up first. Everything you need is the `pull_brand_package` response above,
the bundled assets below, and the render rules that follow.

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
@font-face { font-family:'Minion Pro'; font-weight:500; font-style:italic;
  src:url('fonts/MinionPro-MediumIt.woff') format('woff'); }
@font-face { font-family:'Minion Pro'; font-weight:600; font-style:normal;
  src:url('fonts/MinionPro-Semibold.woff') format('woff'); }
@font-face { font-family:'Minion Pro'; font-weight:600; font-style:italic;
  src:url('fonts/MinionPro-SemiboldIt.woff') format('woff'); }
@font-face { font-family:'Minion Pro'; font-weight:700; font-style:normal;
  src:url('fonts/MinionPro-Bold.woff') format('woff'); }
@font-face { font-family:'Minion Pro'; font-weight:700; font-style:italic;
  src:url('fonts/MinionPro-BoldIt.woff') format('woff'); }

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

Pull exact values from the `colors` in the `pull_brand_package` response (the bundled
`brand-colors.json` is the version you sent it, not the source you render from). The
load-bearing rules, which also come back as `usage_rules`:

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
asks to "set up the shared Lee design system," **call `pull_brand_package` first, the
same as any render** — this path matters MORE, not less, because a stale palette
uploaded as the org-wide design system propagates to every Lee design indefinitely.
Upload the values the tool returns; if they differ from the bundled file, the tool's
response wins and you say so. If the call cannot be completed, stop here too.

Then walk them through the bundled `claude-design-setup.md` and stage these files for
upload into Claude Design's design-system onboarding: `lee-associates-brand-guidelines.md`,
`lee_logo.svg` (+ `lee_logo.png` backup), `brand-colors.json`, and the bundled WOFFs in
`fonts/` (five Avenir Next + eight Minion Pro). That's a one-time org setup; the primary
path above is what you reach for on an individual deliverable.

## Files

- `SKILL.md` — this file. Calls the `pull_brand_package` MCP tool on `lee-raleigh`
  before rendering anything.
- `brand-colors.json` — machine-readable color tokens (HEX / PMS / CMYK / RGB, tints, the
  icon gradient). Its `version` is what you send as `local_version`; render from the
  tool's response, not from this file. Print-only values (PMS / CMYK / RGB) live here
  and are not served, so read them here when a print spec needs them.
- `fonts/` — the five Avenir Next WOFFs and eight Minion Pro WOFFs + a README; the real
  Lee primary typeface and its accent serif.
- `lee_logo.svg` — the logo as a vector (sharpest; preferred).
- `lee_logo.png` — the logo as an image (240×73 RGBA; use when a tool won't take SVG).
- `lee-associates-brand-guidelines.md` — Lee's full brand standards (logo, colors, fonts,
  photography, templates). Deep reference, not a per-render read.
- `claude-design-setup.md` — the step-by-step guide for the one-time Claude Design setup.

**The assets are bundled; the VALUES are confirmed per run.** `brand-colors.json` on
disk is the version stamp this skill sends to `pull_brand_package`, not the authority
it renders from — the tool's response is. The fonts and the logo stay on disk because
the sandbox has no network for file reads at render time.

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

<!-- BEGIN CONNECTOR-AUTH BLOCK (canonical: shared/connector-auth.md — edit there, then scripts/sync-connector-auth.sh) -->
## Connector auth — attempt the call first

**Never tell the broker the lee-raleigh connector is "not authorized", "not connected",
or "needs to be authorized" unless an actual tool call just failed with an auth error —
or the lee-raleigh tools are missing from this session entirely.**

1. **Attempt first.** If the lee-raleigh tools appear in your available tools, call the
   one you need — do not assess authorization beforehand. A needs-auth flag, an empty
   credential field, a `/mcp` probe, or any other indirect signal is NOT authorization
   state; the only way to know is to make the call. If you have not attempted the call
   in this conversation, you do not know the auth state — so call it.
2. **Only a tool-level auth error counts.** Treat a call as auth-failed ONLY when it
   returned an authorization error (`401` / `invalid_token`). Any other failure — a
   timeout, an empty result, a data error — is not an auth problem; handle it per this
   skill's error handling, and a plain retry line ("try again in a few minutes") is
   only ever for those transient, not-an-auth failures.
3. **Auth failure with the lee-raleigh tools loaded — and the immediately preceding
   attempt (if any) did NOT also auth-fail:** the most likely cause is a known Claude
   bug that reports a successful call as failed — the connection is usually fine, so
   do NOT send the broker to sign-in yet. This applies to any such failure, including
   one later in a conversation whose earlier glitch already healed. Reply warmly, in
   broker language:

   > That error is most likely a Claude glitch (on Anthropic's side, not the Lee
   > tools) — the connection is usually fine. Tell me **"YOU DO HAVE ACCESS! TRY
   > AGAIN!"** and I'll re-run it. If it still fails on the retry, a quick sign-in
   > refresh usually fixes it
   > (https://leeraleigh.groundedintelligence.io/setup#connect-sign-in) — or email
   > David at david@groundedintelligence.io and he'll get you sorted.

   When the broker prompts the retry, attempt the call again.
4. **Two auth failures in a row — or the lee-raleigh tools are missing from this
   session entirely:** treat it as a genuine sign-in problem.
   Reply warmly, in broker language:

   > It looks like the Lee Raleigh connection needs a quick sign-in refresh — this can
   > happen after a reinstall, a new computer, or an app update. In Claude, open the
   > **Lee internal comps** plugin, go to its **Connectors** tab, and click the button
   > next to **lee-raleigh**. Sign in with the email you use for Claude (your Lee email
   > for most people) and send yourself the magic link. If the link says it expired,
   > that's normal — just request another from the sign-in page; the second request is
   > what signs you in. Full walkthrough with screenshots:
   > https://leeraleigh.groundedintelligence.io/setup#connect-sign-in — it takes about
   > a minute, then just ask me again. If that doesn't get you back in, email David at
   > david@groundedintelligence.io and he'll get you sorted.

   Never point a broker at "/mcp", never mention MCP or OAuth by name, and never answer
   an auth failure with "try again in a few minutes" — those leave them stuck.
<!-- END CONNECTOR-AUTH BLOCK -->
