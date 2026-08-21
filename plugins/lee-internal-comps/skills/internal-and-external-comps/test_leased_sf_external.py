"""
External lease rows show the leased PREMISES size in "Leased SF" (lee#469),
and never the building SF (gi-plugins#105).

Broker request (Will Fogleman, Lee, 2026-06-17 'Initial Feedback' email):
"For external lease records, 'Leased SF' appears to be pulling the total
building square footage instead of the actual leased area. Please ensure this
field reflects the leased premises and not the building size."

History: the external lease ingest carried only `building_sf` in the typed
schema, so gi-plugins#105 blanked the column rather than show the footprint.
lee#469 promoted the raw "Size Leased SF" to `comps_external.leased_sf`
(backfilled), so the column now shows the real leased area. A row without
`leased_sf` (not yet backfilled) still renders blank, never the building size.

Cards: davidmshaner-gi/gi-plugins#105 (interim), lee-and-associates#469 (fix).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from helpers import (  # noqa: E402
    SOURCE_EXTERNAL,
    SOURCE_INTERNAL,
    combine,
    to_core,
    unified_markdown_table,
)

EXT_LEASE = {
    "external_property_id": "C-1", "property_address": "3 Pine St",
    "property_city": "Durham", "county": "Durham", "property_type": "Industrial",
    "building_sf": 60000, "leased_sf": 8400, "base_rent": 10.0, "rent_type": "NNN",
    "lease_start_date": "2026-01-01",
}

EXT_LEASE_NO_LEASED = {**EXT_LEASE, "leased_sf": None}

INT_LEASE = {
    "comps_id": "i1", "street_address": "1 A St", "city": "Garner", "county": "Wake",
    "property_type": "Industrial", "space_sf": 12500, "square_feet_sold": 60000,
    "effective_rate": 11.0, "asking_rate_per_sf": 12.0,
    "lease_execution": "2026-02-01",
}


def test_external_lease_leased_sf_is_the_leased_premises():
    core = to_core(EXT_LEASE, SOURCE_EXTERNAL, "lease")
    assert core["Leased SF"] == 8400
    assert core["Leased SF"] != EXT_LEASE["building_sf"]


def test_external_lease_without_leased_sf_is_blank_not_building_sf():
    core = to_core(EXT_LEASE_NO_LEASED, SOURCE_EXTERNAL, "lease")
    assert core["Leased SF"] in (None, ""), (
        f"external lease Leased SF must be blank, got {core['Leased SF']!r}"
    )
    assert core["Leased SF"] != EXT_LEASE["building_sf"]


def test_external_lease_does_not_flag_building_size_substitution():
    """With Leased SF blanked, nothing is being substituted, so the W1
    'building size, not leased area' flag/footnote must not fire."""
    core = to_core(EXT_LEASE, SOURCE_EXTERNAL, "lease")
    assert not core.get("_leased_sf_is_building_size")


def test_internal_lease_leased_sf_unchanged():
    core = to_core(INT_LEASE, SOURCE_INTERNAL, "lease")
    # Internal carries a real leased area (space_sf), which must still populate.
    assert core["Leased SF"] == 12500


def test_unified_lease_table_shows_external_leased_sf_never_building_sf():
    rows = combine(
        [to_core(INT_LEASE, SOURCE_INTERNAL, "lease")],
        [to_core(EXT_LEASE, SOURCE_EXTERNAL, "lease")],
        "lease",
    )
    md = unified_markdown_table(rows, {"comp_type": "lease"})
    # The external row's Leased SF is the leased area; the building size never
    # appears as a Leased SF value.
    assert "8400" in md
    assert "60000" not in md, "building SF leaked into the unified lease table"
    # The W1 'building size, not leased area' footnote should be gone.
    assert "building size, not leased area" not in md
    # Internal leased area still renders.
    assert "12500" in md
