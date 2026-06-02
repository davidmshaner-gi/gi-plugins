"""County verify-link registry for the owner-lookup QA harness.

Single source of truth, seeded directly from the owner-lookup SKILL.md
verification-footer table and worked examples. When that table changes
(URL, mode, or sentinel PIN), update this list and re-run the harness.

Each entry pins ONE real parcel so the harness can drive the county's actual
search form end-to-end (not just load the page) and prove a PIN round-trips.

The `expected` field is the KNOWN-GOOD BASELINE. The harness compares the live
result against it and only fails loudly when reality DIVERGES from baseline:
  - a county that was passing now fails       -> REGRESSION (portal changed / our URL rotted)
  - a county we know is broken now passes      -> FIXED (update this baseline + SKILL.md)
Both mismatches exit non-zero, because both mean the SKILL.md footer and this
file no longer agree with the live portals.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class County:
    key: str          # canonical owner_lookup county key (matches D1 `county`)
    name: str         # human-readable county name (for the footer prose)
    portal_name: str  # portal label shown in the broker footer
    url: str          # the exact URL the footer links to (resolved for deep-links)
    pin: str          # sentinel PIN to push through the real search form
    adapter: str      # which adapter drives this portal (see adapters.py)
    expected: str     # known-good baseline: "pass" or "fail"
    expected_note: str = ""  # why, if expected == "fail"
    # Strings expected to appear on the parcel-detail result. The round-trip
    # passes only if at least one is found (alphanumeric-normalized substring
    # match) AND no failure marker is present. Keep tolerant.
    expect_any: tuple = field(default_factory=tuple)


# Order mirrors the SKILL.md table: WAKE, DURHAM, NEW_HANOVER, LEE.
COUNTIES = [
    County(
        key="WAKE",
        name="Wake",
        portal_name="Wake iMaps",
        url="https://maps.raleighnc.gov/imaps/?pin=0734835370",
        pin="0734835370",
        adapter="wake_imaps",
        expected="pass",
        # 0734835370 == 100 Connemara Dr, Cary (SKILL.md Example 1).
        expect_any=("0734835370", "PNC OF NORTH CAROLINA", "CONNEMARA"),
    ),
    County(
        key="DURHAM",
        name="Durham",
        portal_name="Durham Tax CAMA",
        url="https://taxcama.dconc.gov/camapwa/#PIN",
        pin="0822419440",
        adapter="durham_cama",
        expected="pass",
        # Resolves to 1500 W Main St -> DUKE UNIVERSITY. Page shows "0822-41-9440".
        expect_any=("0822419440", "DUKE UNIVERSITY"),
    ),
    County(
        key="NEW_HANOVER",
        name="New Hanover",
        portal_name="NHC etax",
        url="https://etax.nhcgov.com/PT/search/commonsearch.aspx?mode=parid",
        pin="R04720-007-011-000",
        adapter="tyler_iasworld",
        expected="pass",
        # Tyler echoes the PIN in the result row; dashes are normalized away.
        expect_any=("R04720007011000", "R04720"),
    ),
    County(
        key="LEE",
        name="Lee",
        portal_name="Lee County Tax Access",
        url="https://taxaccess.leecountync.gov/pt/search/commonsearch.aspx?mode=parid",
        pin="9645-45-9484-00",
        adapter="tyler_iasworld",
        expected="fail",
        expected_note=(
            "Known bug (gi-plugins #18 / lee-and-associates #18): Tyler iasWorld "
            "rejects mode=parid on submit ('An Error has Occurred'). The page LOADS "
            "but the PIN search throws. Flip to 'pass' once the sibling fix changes "
            "the SKILL.md footer to the working search mode (mode=realprop)."
        ),
        expect_any=("9645459484", "9645-45-9484-00"),
    ),
]


def by_key(key: str) -> County:
    for c in COUNTIES:
        if c.key == key.upper():
            return c
    raise KeyError(f"No county with key {key!r}. Known: {[c.key for c in COUNTIES]}")
