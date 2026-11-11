"""
The default comps skill reaches contributed comps (lee-and-associates#636).

A broker asked for industrial lease comps, 20,000-200,000 SF, last 24 months,
and the comps GI had already loaded as contributed comps never came back: the
skill ran only the internal and external legs, and the one tool that can see
contributed comps sized lease asks on building SF, which contributed lease rows
do not carry.

Failure modes this file guards:
  C1  The default skill builds no contributed call, so contributed rows never
      reach a default ask.
  C2  The contributed call sizes a lease ask on building SF (reaches nothing)
      instead of the leased band; or sizes a sale on the leased band.
  C3  Contributed rows are relabelled Internal or External, or dropped by
      combine / the Excel, so the broker cannot tell where a comp came from.
  C4  The unified tool has no location filter, so an out-of-market contributed
      comp (a Wilmington lease on a Triangle ask) lands in the deliverable.
  C6  The default Triangle ask drops in-market contributed comps whose city is
      not on the internal leg's city list (Smithfield, Hillsborough), though the
      external leg reaches those counties.
  C7  `plan` reports success when the external leg refused the market, so the
      session runs the other two legs against the wrong market.
  C8  GI bookkeeping (who loaded a comp, the tenant key) lands in the broker's Excel.
  C5  A quarter-string lease date ("2025Q2", how the first contributed import
      stores it) sorts as undated and falls to the bottom.

Fixture: a synthetic pull_unified_comps response in the shape prod returned on
2026-11-11 (building_sf null, leased_sf set, quarter-string dates, one blank
city, one row outside the Triangle). Addresses are invented.
"""

import json
import os
import subprocess
import sys

from conftest import SKILLS_DIR, load_skill_helpers

HERE = os.path.dirname(os.path.abspath(__file__))
unified = load_skill_helpers("internal-and-external-comps")
SOURCE_CONTRIBUTED = unified.SOURCE_CONTRIBUTED
SOURCE_EXTERNAL = unified.SOURCE_EXTERNAL
SOURCE_INTERNAL = unified.SOURCE_INTERNAL
combine = unified.combine
contributed_params = unified.contributed_params
filter_contributed = unified.filter_contributed
format_unified_excel = unified.format_unified_excel
load_sibling = unified.load_sibling
source_counts = unified.source_counts
to_core = unified.to_core
HELPERS = os.path.join(SKILLS_DIR, "internal-and-external-comps", "helpers.py")

with open(os.path.join(HERE, "fixtures", "unified_contributed_lease.json")) as fh:
    RESPONSE = json.load(fh)
ROWS = RESPONSE["rows"]

ASK = {
    "asset_type": "industrial",
    "transaction_type": "lease",
    "size_range": {"min_sf": 20000, "max_sf": 200000},
    "date_window": {"from": "2024-11-10", "to": "2026-11-10"},
}


def _validated(ask):
    return load_sibling("internal-comps").validate_request(dict(ask))["validated"]


def test_c1_c2_lease_call_uses_the_leased_band_and_contributed_source():
    call = contributed_params(_validated(ASK))
    assert call["tool_name"] == "pull_unified_comps"
    p = call["params"]
    assert p["sources"] == ["broker_added"]
    assert p["transaction_type"] == "lease"
    assert p["property_type"] == "industrial"
    assert (p["leased_sf_min"], p["leased_sf_max"]) == (20000, 200000)
    assert "building_sf_min" not in p and "building_sf_max" not in p
    assert (p["date_from"], p["date_to"]) == ("2024-11-10", "2026-11-10")


def test_c2_sale_call_sizes_the_building():
    call = contributed_params(_validated({**ASK, "transaction_type": "sale"}))
    p = call["params"]
    assert (p["building_sf_min"], p["building_sf_max"]) == (20000, 200000)
    assert "leased_sf_min" not in p


def test_c2_lookback_window_resolves_to_iso_dates():
    v = _validated({k: v for k, v in ASK.items() if k != "date_window"})
    p = contributed_params(v)["params"]
    assert len(p["date_from"]) == 10 and p["date_from"][4] == "-"
    assert p["date_from"] < p["date_to"]


def test_c4_triangle_ask_drops_out_of_market_rows_and_keeps_cityless_ones():
    kept, note = filter_contributed(ROWS, _validated(ASK))
    cities = {r.get("property_city") for r in kept}
    out_of_market = [r for r in ROWS if r.get("property_city") == "Wilmington"]
    assert out_of_market, "fixture must carry an out-of-market row"
    assert "Wilmington" not in cities
    blank = [r for r in ROWS if not r.get("property_city")]
    assert blank and all(r in kept for r in blank)
    assert str(len(out_of_market)) in note and str(len(blank)) in note


def test_c4_county_ask_maps_city_to_county():
    v = _validated({**ASK, "geography": {"counties": ["Durham County"]}})
    kept, _ = filter_contributed(ROWS, v)
    named = [r for r in kept if r.get("property_city")]
    assert named and all(r["property_city"] == "Durham" for r in named)


def test_c4_city_ask_matches_case_insensitively():
    v = _validated({**ASK, "geography": {"cities": ["garner"]}})
    kept, _ = filter_contributed(ROWS, v)
    named = [r for r in kept if r.get("property_city")]
    assert named and all(r["property_city"] == "Garner" for r in named)


def test_c3_contributed_rows_keep_their_own_source_through_combine_and_excel(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    kept, _ = filter_contributed(ROWS, _validated(ASK))
    contributed_core = [to_core(r, SOURCE_CONTRIBUTED, "lease") for r in kept]
    internal_core = [to_core({"comps_id": "i1", "street_address": "1 A St", "city": "Raleigh",
                              "space_sf": 30000, "effective_rate": 9.0,
                              "lease_execution": "03/01/2025"}, SOURCE_INTERNAL, "lease")]
    external_core = [to_core({"external_comp_id": 5, "property_address": "2 B St",
                              "property_city": "Cary", "leased_sf": 40000, "base_rent": 10.0,
                              "lease_start_date": "2025-04-01"}, SOURCE_EXTERNAL, "lease")]
    core = combine(internal_core, external_core, "lease", contributed_core=contributed_core)
    assert source_counts(core) == {
        SOURCE_INTERNAL: 1, SOURCE_EXTERNAL: 1, SOURCE_CONTRIBUTED: len(kept)}
    c = next(r for r in core if r["Source"] == SOURCE_CONTRIBUTED)
    assert c["Leased SF"] and c["Rent"] is not None and c["space_sf"] == c["Leased SF"]

    from openpyxl import load_workbook
    name = format_unified_excel(core, internal_native=[], external_native=[],
                                contributed_native=kept, validated=_validated(ASK),
                                xlsx_path="x.xlsx")
    wb = load_workbook(name)
    assert "Contributed" in wb.sheetnames
    all_sources = [row[0].value for row in wb["All Comps"].iter_rows(min_row=2)]
    assert all_sources.count(SOURCE_CONTRIBUTED) == len(kept)


def test_c5_quarter_dates_sort_with_real_dates():
    rows = [{"Source": "x", "Date": "2025Q2"}, {"Source": "x", "Date": "2024-01-01"},
            {"Source": "x", "Date": None}, {"Source": "x", "Date": "2025-03-01"}]
    out = combine(rows, [], "lease")
    assert [r["Date"] for r in out] == ["2025Q2", "2025-03-01", "2024-01-01", None]


def test_c1_plan_cli_prints_all_three_legs():
    out = subprocess.run([sys.executable, HELPERS, "plan", json.dumps(ASK)],
                         capture_output=True, text=True, check=True)
    plan = json.loads(out.stdout)
    assert plan["internal"]["tool_name"] == "read_query" and "lease_comps_safe" in plan["internal"]["sql"]
    assert plan["external"]["tool_name"] == "search_external_lease_comps"
    assert plan["external"]["params_list"]
    assert plan["contributed"]["params"]["leased_sf_min"] == 20000


def test_c6_default_triangle_ask_keeps_cities_in_the_seven_counties():
    rows = [dict(ROWS[0], comp_id=901, property_city="Smithfield"),
            dict(ROWS[0], comp_id=902, property_city="Hillsborough"),
            dict(ROWS[0], comp_id=903, property_city="Charlotte")]
    kept, note = filter_contributed(rows, _validated(ASK))
    assert sorted(r["property_city"] for r in kept) == ["Hillsborough", "Smithfield"]
    assert "1 outside" in note


def test_c6_an_explicit_city_list_is_not_widened():
    v = _validated({**ASK, "geography": {"cities": ["Raleigh"]}})
    rows = [dict(ROWS[0], comp_id=904, property_city="Smithfield")]
    kept, _ = filter_contributed(rows, v)
    assert kept == []


def test_c7_plan_fails_when_the_external_leg_refuses_the_market():
    ask = {**ASK, "geography": {"named_market": "Charlotte"}}
    out = subprocess.run([sys.executable, HELPERS, "plan", json.dumps(ask)],
                         capture_output=True, text=True)
    assert out.returncode != 0
    assert json.loads(out.stdout)["error"]


def test_c8_contributed_sheet_leaves_out_bookkeeping_columns(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from openpyxl import load_workbook
    core = [to_core(r, SOURCE_CONTRIBUTED, "lease") for r in ROWS]
    name = format_unified_excel(core, internal_native=[], external_native=[],
                                contributed_native=ROWS, validated=_validated(ASK),
                                xlsx_path="x.xlsx")
    header = [c.value for c in next(load_workbook(name)["Contributed"].iter_rows(max_row=1))]
    assert "original_source" in header
    assert "added_by" not in header and "client_id" not in header
