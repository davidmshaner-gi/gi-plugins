"""lee#496: an internal county ask must bind county_normalized, never county."""
import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "ic_helpers", Path(__file__).with_name("helpers.py")
)
helpers = importlib.util.module_from_spec(spec)
sys.modules["ic_helpers"] = helpers
spec.loader.exec_module(helpers)


def _validated(**over):
    base = {
        "transaction_type": "lease",
        "asset_type": "retail",
        "geography": {"counties": ["Brunswick County"]},
        "date_window": {"lookback_months": 24},
    }
    base.update(over)
    return base


def _sql(validated):
    out = helpers.build_sql(validated)
    return out["sql"] if isinstance(out, dict) else out


def test_normalize_county_matches_the_worker_rule():
    assert helpers.normalize_county("Brunswick County") == "brunswick"
    assert helpers.normalize_county("brunswick") == "brunswick"
    assert helpers.normalize_county("  NEW HANOVER COUNTY ") == "new hanover"
    assert helpers.normalize_county("") == ""


def test_counties_bind_the_normalized_column():
    sql = _sql(_validated())
    assert "county_normalized IN ('brunswick')" in sql
    # the raw column must never carry the predicate - that is the lee#496 bug
    assert "county IN (" not in sql.replace("county_normalized IN (", "")


def test_a_county_ask_does_not_also_filter_cities():
    sql = _sql(_validated())
    assert "city IN (" not in sql


def test_several_counties_and_either_spelling():
    sql = _sql(_validated(geography={"counties": ["Brunswick", "New Hanover County"]}))
    assert "county_normalized IN ('brunswick', 'new hanover')" in sql


def test_counties_work_for_sale_too():
    sql = _sql(_validated(transaction_type="sale"))
    assert "FROM sale_comps_safe" in sql
    assert "county_normalized IN ('brunswick')" in sql


def test_city_geography_is_unchanged():
    sql = _sql(_validated(geography={"cities": ["Raleigh"]}))
    assert "county_normalized" not in sql
    assert "city IN ('Raleigh')" in sql


def test_default_rdu_geography_is_unchanged():
    sql = _sql(_validated(geography={}))
    assert "county_normalized" not in sql
    assert "city IN (" in sql


def test_county_reaches_the_geography_label_for_excel_and_email():
    """lee#496 review: a blank label shipped 'Retail Comps' as the sheet name and
    'for .' in the email body -- a visibly broken broker artifact on the new path."""
    assert helpers._geography_label({"counties": ["Brunswick County"]}) == "Brunswick County"
    assert helpers._geography_label({"counties": ["A", "B", "C", "D"]}) == "A +3 more"


def test_blank_county_list_does_not_silently_widen_to_the_whole_book():
    sql = _sql(_validated(geography={"counties": ["   "]}))
    assert "county_normalized" not in sql
    assert "city IN (" in sql  # falls back to the normal geography, never no filter


def test_counties_take_precedence_over_named_market():
    sql = _sql(_validated(geography={"named_market": "RDU MSA", "counties": ["Brunswick"]}))
    assert "county_normalized IN ('brunswick')" in sql
    assert "city IN (" not in sql
