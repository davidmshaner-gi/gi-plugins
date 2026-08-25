"""lee#496: a county-shaped ask must reach the server-side county filter.

Before this the skill had only `named_market` and `cities`, so "retail leases in
Brunswick County" was enumerated as beach towns and came back empty while 43
Brunswick lease comps sat in the external book (audit_log 4153-4159, 2026-08-25).
"""
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "ec_helpers", Path(__file__).with_name("helpers.py")
)
helpers = importlib.util.module_from_spec(spec)
sys.modules["ec_helpers"] = helpers
spec.loader.exec_module(helpers)


def _validated(**over):
    base = {
        "transaction_type": "lease",
        "asset_type": "retail",
        "geography": {"counties": ["Brunswick"]},
        "date_window": {"lookback_months": 24},
    }
    base.update(over)
    return base


def test_counties_geography_emits_one_call_per_county():
    out = helpers.build_mcp_params(
        _validated(geography={"counties": ["Brunswick", "New Hanover"]})
    )
    assert out["tool_name"] == "search_external_lease_comps"
    assert [p["county"] for p in out["params_list"]] == ["Brunswick", "New Hanover"]
    assert all("city" not in p for p in out["params_list"])
    assert out["post_filter_counties"] is None


def test_county_suffix_is_passed_through_untouched():
    # the Worker normalizes; the skill must not second-guess the broker's spelling
    out = helpers.build_mcp_params(_validated(geography={"counties": ["Brunswick County"]}))
    assert out["params_list"][0]["county"] == "Brunswick County"


def test_counties_work_for_sale_too():
    out = helpers.build_mcp_params(
        _validated(transaction_type="sale", geography={"counties": ["Brunswick"]})
    )
    assert out["tool_name"] == "search_external_sale_comps"
    assert out["params_list"][0]["county"] == "Brunswick"


def test_named_market_path_is_unchanged():
    out = helpers.build_mcp_params(_validated(geography={"named_market": "RDU MSA"}))
    assert len(out["params_list"]) == 1
    assert "county" not in out["params_list"][0]
    assert out["post_filter_counties"] == set(helpers.RDU_MSA_COUNTIES)


def test_cities_path_is_unchanged():
    out = helpers.build_mcp_params(_validated(geography={"cities": ["Raleigh", "Cary"]}))
    assert [p["city"] for p in out["params_list"]] == ["Raleigh", "Cary"]
    assert all("county" not in p for p in out["params_list"])


def test_counties_reach_the_sheet_title_and_email_geography():
    v = _validated(geography={"counties": ["Brunswick"]})
    assert "Brunswick" in helpers._sheet_title(v)
