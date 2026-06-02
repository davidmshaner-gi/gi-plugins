#!/usr/bin/env python3
"""owner-lookup verify-link QA harness.

Drives each county verification portal that the owner-lookup skill links brokers
to, pushes that county's sentinel PIN through the REAL search form, and asserts
the result page actually shows the parcel -- catching a broken search mode or a
changed form BEFORE a broker hits it mid-deal.

Why a browser and not curl: every one of these portals returns HTTP 200 on the
search page even when the search itself is broken (the Lee mode=parid bug is the
poster child -- the form loads, then throws on submit). Tyler iasWorld also
gates behind a click-through disclaimer that sets a session cookie. Only a real
browser submit exercises what the broker actually experiences.

Baseline-aware: each county's known-good state lives in counties.py. The harness
exits non-zero only when LIVE state diverges from baseline -- a regression (was
passing, now fails) or an unexpected fix (known-broken, now passes -> time to
update the baseline + the SKILL.md footer). A steady known-broken county (Lee
today) is reported but does NOT fail the run, so this can gate releases without
being blocked by a separately-tracked bug.

Usage:
  python3 verify_links.py                     # all counties, headless, writes report + screenshots to ./out
  python3 verify_links.py --county LEE         # one county
  python3 verify_links.py --headed             # watch it drive the portals
  python3 verify_links.py --out /tmp/qa        # custom output dir
  python3 verify_links.py --no-screenshots     # skip screenshots (faster)

Exit code 0 = live state matches baseline for every county checked.
Exit code 1 = at least one county diverged from baseline (regression or fix).
Exit code 2 = a harness/automation error (unexpected exception driving a portal).
"""

import argparse
import datetime
import sys
import traceback
from pathlib import Path

from playwright.sync_api import sync_playwright

from adapters import ADAPTERS
from counties import COUNTIES, by_key

HERE = Path(__file__).resolve().parent


def _verdict(actual_pass: bool, expected: str):
    """Return (ok_with_baseline, label) comparing live result to known baseline."""
    expected_pass = expected == "pass"
    if actual_pass and expected_pass:
        return True, "OK"
    if not actual_pass and not expected_pass:
        return True, "OK (known-broken)"
    if actual_pass and not expected_pass:
        return False, "FIXED -> update baseline + SKILL.md footer"
    return False, "REGRESSION -> portal/search changed; brokers are now blocked"


def _drive(browser, c, *, out: Path, screenshots: bool):
    """Run one county's adapter once in a fresh context. Returns (probe, error, shot)."""
    # Fresh context so the disclaimer / session-cookie step is genuinely exercised
    # every run (not cached from a prior county).
    ctx = browser.new_context(viewport={"width": 1400, "height": 1000})
    page = ctx.new_page()
    page.set_default_timeout(45000)
    shot = ""
    try:
        probe = ADAPTERS[c.adapter](page, c)
        error = None
    except Exception as exc:  # noqa: BLE001 -- harness must survive one bad portal
        probe = None
        error = f"{type(exc).__name__}: {exc}"
        traceback.print_exc()
    if screenshots:
        shot = str(out / f"{c.key.lower()}.png")
        try:
            page.screenshot(path=shot, full_page=False)
        except Exception:  # noqa: BLE001
            shot = ""
    ctx.close()
    return probe, error, shot


def _matches_baseline(probe, error, c) -> bool:
    if error is not None or probe is None:
        return False
    return _verdict(probe.found, c.expected)[0]


def run(counties, *, headed: bool, out: Path, screenshots: bool):
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not headed)
        for c in counties:
            probe, error, shot = _drive(browser, c, out=out, screenshots=screenshots)
            # These are live, occasionally-flaky government portals. A divergence
            # from baseline is the thing we act on (regression or fix), so confirm
            # it with one retry before trusting it -- avoids a network blip blocking
            # a release. A result that already matches baseline is left as-is.
            if not _matches_baseline(probe, error, c):
                print(f"[{c.key}] diverged from baseline; retrying once to rule out a transient hiccup...")
                probe, error, shot = _drive(browser, c, out=out, screenshots=screenshots)
            rows.append({"county": c, "probe": probe, "error": error, "shot": shot})
        browser.close()
    return rows


def render(rows, *, out: Path):
    now = datetime.datetime.now().astimezone()
    stamp = now.strftime("%Y-%m-%d %H:%M %Z")
    lines = [
        f"# Owner-Lookup Verify-Link QA — {stamp}",
        "",
        "Drives each county verify-footer portal and pushes the sentinel PIN through",
        "the real search form. PASS = the result page showed that parcel.",
        "",
        "| County | Portal | Sentinel PIN | Result | Baseline | Verdict |",
        "|---|---|---|---|---|---|",
    ]
    all_ok = True
    had_harness_error = False
    details = []
    for r in rows:
        c, probe, error = r["county"], r["probe"], r["error"]
        if error is not None:
            had_harness_error = True
            result_cell, ok, label = "⚠️ ERROR", False, "harness error driving portal"
            details.append(f"- **{c.name}** ⚠️ harness error: {error}")
        else:
            actual_pass = probe.found
            ok, label = _verdict(actual_pass, c.expected)
            result_cell = "✅ PASS" if actual_pass else "❌ FAIL"
            note = f"  ({c.expected_note})" if (c.expected == "fail" and c.expected_note) else ""
            details.append(f"- **{c.name}** {result_cell}: {probe.detail}{note}")
        all_ok = all_ok and ok
        baseline_cell = c.expected + (" (known #18)" if c.expected == "fail" else "")
        verdict_cell = ("✓ " if ok else "🔴 ") + label
        lines.append(
            f"| {c.name} | {c.portal_name} | `{c.pin}` | {result_cell} | {baseline_cell} | {verdict_cell} |"
        )
    lines += ["", "## Detail", *details, ""]
    matched = sum(1 for r in rows if r["error"] is None and _verdict(r["probe"].found, r["county"].expected)[0])
    total = len(rows)
    lines.append(f"**Summary:** {matched}/{total} counties match baseline.")
    if all_ok and not had_harness_error:
        lines.append("All portals behave as expected. No broker-facing regression.")
    else:
        lines.append("⚠️ At least one county diverged from baseline — see verdicts above. "
                     "If a known-broken county now PASSES, flip its `expected` in counties.py "
                     "and update the SKILL.md footer. If a passing county now FAILS, the portal "
                     "or our linked URL changed and brokers are blocked — fix before release.")
    report = "\n".join(lines) + "\n"
    (out / "report.md").write_text(report)
    return report, all_ok, had_harness_error


def main(argv=None):
    ap = argparse.ArgumentParser(description="owner-lookup verify-link QA harness")
    ap.add_argument("--county", help="run a single county by key (e.g. LEE)", default=None)
    ap.add_argument("--headed", action="store_true", help="show the browser")
    ap.add_argument("--out", default=str(HERE / "out"), help="output dir for report + screenshots")
    ap.add_argument("--no-screenshots", dest="screenshots", action="store_false", help="skip screenshots")
    args = ap.parse_args(argv)

    counties = [by_key(args.county)] if args.county else COUNTIES
    out = Path(args.out)
    rows = run(counties, headed=args.headed, out=out, screenshots=args.screenshots)
    report, all_ok, had_harness_error = render(rows, out=out)
    print(report)
    print(f"(report + screenshots written to {out})")
    if had_harness_error:
        return 2
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
