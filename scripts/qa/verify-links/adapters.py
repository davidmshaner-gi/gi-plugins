"""Per-portal adapters for the owner-lookup verify-link QA harness.

An adapter drives ONE kind of county portal end-to-end: load the page, clear any
disclaimer, push the sentinel PIN through the REAL search form, and report
whether the result page actually shows that parcel. This is the whole point of
the QA -- a plain HTTP GET would 200 on every portal even when the search form
is broken (see Lee, mode=parid). Only a real form submit catches that.

Each adapter returns a Probe. Adapters never raise for an expected portal state
(error page, no results); they catch and report it as found=False so the harness
can render a clean verdict. They only let truly unexpected exceptions bubble.
"""

from dataclasses import dataclass

from playwright.sync_api import Page

# Substrings (matched case-insensitively against the result body) that mean the
# PIN search did NOT land on a real parcel -- a thrown error or an empty result.
FAILURE_MARKERS = (
    "an error has occurred",
    "system encountered a problem",
    "cannot complete the requested action",
    "no records",
    "0 records",
    "no results",
    "no parcels",
    "not found",
    "invalid",
)


@dataclass
class Probe:
    found: bool      # did the sentinel PIN round-trip to a real parcel detail?
    detail: str      # broker-legible one-liner
    final_url: str   # where we ended up (useful when a portal redirects on error)


def _norm(s: str) -> str:
    """Alphanumeric-only, uppercased -- so '0822-41-9440' matches '0822419440'."""
    return "".join(ch for ch in s if ch.isalnum()).upper()


def _assert_parcel(body: str, county) -> tuple[bool, str]:
    """Did the result page actually show this parcel?

    Success token FIRST: if the expected PIN/owner is on the page, it PASSES even
    if some generic word like "invalid" appears elsewhere in the chrome (a footer
    "report invalid data" link, a help tooltip). Only when NO expected token is
    present do we scan the failure markers -- and at that point we already know
    it's a fail, so the markers just pick the most specific reason. This ordering
    keeps a portal changing its surrounding text from producing a false FAIL on
    what is meant to be a trusted release gate.
    """
    nbody = _norm(body)
    for token in county.expect_any:
        if _norm(token) in nbody:
            return True, f"parcel detail confirmed (matched {token!r})"
    low = body.lower()
    for marker in FAILURE_MARKERS:
        if marker in low:
            return False, f"result page shows '{marker}' -- search form rejected the PIN"
    return False, (
        "page loaded but the parcel detail did not show the expected PIN/owner "
        f"({', '.join(county.expect_any)}) -- the form may have silently changed"
    )


def _click_first_visible(page: Page, texts) -> bool:
    for t in texts:
        try:
            btn = page.query_selector(f"button:has-text('{t}')") or page.query_selector(
                f"input[type=submit][value='{t}']"
            )
            if btn and btn.is_visible():
                btn.click()
                return True
        except Exception:  # noqa: BLE001 -- a bad selector on one disclaimer variant must not abort
            continue
    return False


# --------------------------------------------------------------------------- #
# WAKE -- Wake iMaps. A JS map SPA reached by a ?pin= deep-link. There is no
# form to submit; the deep-link IS the round-trip. We accept the one-time
# disclaimer and assert the parcel info pane renders the PIN + owner.
# --------------------------------------------------------------------------- #
def wake_imaps(page: Page, county) -> Probe:
    page.goto(county.url, wait_until="domcontentloaded")
    page.wait_for_timeout(4000)  # the map app hydrates slowly
    _click_first_visible(page, ["OK", "I Agree", "Agree", "Accept", "Continue", "Acknowledge"])
    # Give the info pane time to resolve the pin and populate.
    deadline_ticks = 0
    body = ""
    while deadline_ticks < 8:
        page.wait_for_timeout(2000)
        body = page.inner_text("body")
        if _norm(county.pin) in _norm(body):
            break
        deadline_ticks += 1
    ok, detail = _assert_parcel(body, county)
    return Probe(ok, detail, page.url)


# --------------------------------------------------------------------------- #
# DURHAM -- Durham Tax CAMA (ASP.NET webforms, tabbed search). Activate the PIN
# tab, fill the PIN textbox, click the PIN search button, assert PropertySummary.
# --------------------------------------------------------------------------- #
def durham_cama(page: Page, county) -> Probe:
    page.goto(county.url, wait_until="domcontentloaded")
    page.wait_for_timeout(2500)
    tab = page.query_selector("a[href='#PIN']")
    if tab:
        tab.click()
        page.wait_for_timeout(800)
    inp = page.query_selector("#ctl00_ContentPlaceHolder1_PINNumberTextBox")
    if not inp:
        return Probe(False, "PIN search box not found -- Durham CAMA form layout changed", page.url)
    inp.fill(county.pin)
    page.click("#ctl00_ContentPlaceHolder1_PinButton")
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(3000)
    ok, detail = _assert_parcel(page.inner_text("body"), county)
    return Probe(ok, detail, page.url)


# --------------------------------------------------------------------------- #
# TYLER iasWorld -- NHC etax + Lee Tax Access (same software). Accept the
# session disclaimer (#btAgree), fill the Parcel ID box (#inpParid), submit
# (#btSearch). A working portal returns a #searchResults row / datalet echoing
# the PIN; a broken search mode throws "An Error has Occurred" (the Lee bug).
# --------------------------------------------------------------------------- #
def tyler_iasworld(page: Page, county) -> Probe:
    page.goto(county.url, wait_until="domcontentloaded")
    page.wait_for_timeout(2000)
    if page.query_selector("#btAgree"):
        page.click("#btAgree")
        page.wait_for_load_state("domcontentloaded")
        page.wait_for_timeout(2500)
    inp = page.query_selector("#inpParid")
    if not inp:
        return Probe(False, "Parcel ID box (#inpParid) not found -- Tyler search form changed", page.url)
    inp.fill(county.pin)
    btn = page.query_selector("#btSearch")
    if not btn:
        return Probe(False, "Search button (#btSearch) not found -- Tyler search form changed", page.url)
    btn.click()
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(3000)
    # The Tyler error page drops its title to "An Error has Occurred".
    if "error has occurred" in (page.title() or "").lower():
        return Probe(False, "result page is the Tyler error page -- search mode rejected the PIN", page.url)
    ok, detail = _assert_parcel(page.inner_text("body"), county)
    return Probe(ok, detail, page.url)


ADAPTERS = {
    "wake_imaps": wake_imaps,
    "durham_cama": durham_cama,
    "tyler_iasworld": tyler_iasworld,
}
