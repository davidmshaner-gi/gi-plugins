# owner-lookup verify-link QA

Catches a broken county **verify-footer** link before a broker does.

The `owner-lookup` skill ends every response with a freshness footer that links the
broker to the authoritative county portal and tells them to paste a PIN to confirm
the data (see `plugins/lee-internal-comps/skills/owner-lookup/SKILL.md`). If that
link's search form silently changes — a renamed search mode, a moved form field —
the broker finds out mid-deal, on an offer letter. This harness pushes a real PIN
through each portal's **actual search form** and asserts the parcel comes back.

## Why a browser and not `curl`

Every one of these portals returns **HTTP 200 on the search page even when the
search itself is broken**. A load-only check (`curl … | grep 200`) passes on all
four — including Lee, where the form loads fine and then throws `An Error has
Occurred` the moment you submit a PIN (the bug in gi-plugins #18 / lee-and-associates
#18). Tyler iasWorld portals also gate behind a click-through disclaimer that sets a
session cookie. Only a real browser submit reproduces what the broker experiences.

## What it checks

| County | Portal | How the PIN round-trips | Sentinel PIN |
|---|---|---|---|
| Wake | Wake iMaps | `?pin=` deep-link → accept disclaimer → assert info pane shows the parcel | `0734835370` |
| Durham | Durham Tax CAMA | PIN tab → fill PIN box → search → assert PropertySummary | `0822419440` |
| New Hanover | NHC etax (Tyler iasWorld) | accept disclaimer → `#inpParid` → `#btSearch` → assert results row | `R04720-007-011-000` |
| Lee | Lee County Tax Access (Tyler iasWorld) | same Tyler flow | `9645-45-9484-00` |

The sentinel PINs are the real worked-example parcels from the SKILL.md footer, so
this file and the skill always agree on what "good" looks like.

## Current state (last full run: 2026-06-02)

| County | Result | Baseline | Notes |
|---|---|---|---|
| Wake | ✅ PASS | pass | `100 CONNEMARA DR` / PNC OF NORTH CAROLINA LLC renders in the info pane |
| Durham | ✅ PASS | pass | resolves to `PropertySummary.aspx?PIN=0822419440` (DUKE UNIVERSITY) |
| New Hanover | ✅ PASS | pass | results row echoes `R04720-007-011-000` |
| Lee | ❌ FAIL | **fail (known #18)** | `mode=parid` throws `An Error has Occurred` on submit. Expected-broken until the sibling fix flips the footer to a working search mode (`mode=realprop`). |

4/4 match baseline → exit 0. Had this harness existed, it would have caught the Lee
bug. NHC was "TBD" in the issue; this run confirms it **passes**.

## Run it

```bash
cd scripts/qa/verify-links
pip install -r requirements.txt
python3 -m playwright install chromium      # one-time, fetches the browser binary
python3 verify_links.py                       # all counties; writes out/report.md + out/<county>.png
```

Options: `--county LEE` (one county), `--headed` (watch it drive), `--out <dir>`,
`--no-screenshots`. Full run is ~30s.

### Exit codes

| Code | Meaning |
|---|---|
| `0` | Every county checked matches its baseline. Safe. |
| `1` | A county **diverged** from baseline — a regression or an unexpected fix (see below). |
| `2` | Harness error driving a portal (timeout, crash) — investigate, not necessarily a real failure. |

## Baseline model — how it stays honest

Each county's known-good state is the `expected` field in `counties.py`. The harness
only fails loudly (exit 1) when **live state diverges from baseline**:

- **A passing county now FAILS → `REGRESSION`.** The portal or our linked URL
  changed; brokers are blocked. Fix the SKILL.md footer (and `counties.py`) before
  the next release.
- **A known-broken county now PASSES → `FIXED`.** The bug got fixed elsewhere (e.g.
  Lee #18 lands). Flip that county's `expected` to `pass` in `counties.py` and update
  the SKILL.md footer to the now-working URL.

A *steady* known-broken county (Lee today) is reported but does **not** fail the run,
so this can gate releases without being permanently blocked by a separately-tracked
bug. Divergences are retried once automatically to absorb a flaky-portal blip before
they're trusted.

## When to run it

- **Pre-release (recommended):** before tagging a `gi-plugins` release that touched
  `owner-lookup` — part of Stage 3a (diff-against-last-tag) in the GI
  plugin-development-process. A red run means a broker-facing link rotted.
- **Ad-hoc:** any time the owner-lookup verification footer table changes (a new
  county, a changed URL/mode, a new sentinel PIN). Update `counties.py` to match the
  SKILL.md, then run.

## Adding a county

1. Add the county's footer row to the SKILL.md table (URL + sentinel PIN).
2. Add a `County(...)` entry in `counties.py` (mirror the SKILL.md values; pick an
   `adapter`; set `expect_any` to a token the result page will show; set `expected`).
3. If the portal is a new kind, add an adapter function in `adapters.py` and register
   it in `ADAPTERS`. The two Tyler iasWorld portals already share `tyler_iasworld`.
4. `python3 verify_links.py --county <KEY> --headed` until it passes, then commit.

## Files

| File | Role |
|---|---|
| `verify_links.py` | CLI + harness: runs adapters, retries divergences once, renders the report, sets exit code |
| `counties.py` | The registry + baseline. Single source of truth, mirrors the SKILL.md footer table |
| `adapters.py` | Per-portal drivers: `wake_imaps`, `durham_cama`, `tyler_iasworld` (NHC + Lee) |
| `test_verify_links.py` | Offline unit tests for the decision logic (no network) — `python3 test_verify_links.py` |
| `requirements.txt` | `playwright` (browser binary fetched separately) |

## Constraints

- **Offline QA tooling only.** This never runs on the broker request path — gotcha G2
  (no county API on the request path). `owner-lookup` reads only from D1 at request
  time; this harness hits the county sites out-of-band, pre-release.
