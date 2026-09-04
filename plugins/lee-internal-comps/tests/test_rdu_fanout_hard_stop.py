"""gi-plugins#168: a Triangle ask can never silently run statewide.

Bonner's three 1.40.0 runs (audit_log 5222-5232, 5259-5263, 2026-09-03) sent
helper-exact params (360-day window, max=today, limit 200, $500K floor) with NO
county, ONE dict paged by cursor, then a client-side whitelist that dropped 286
rows. That is the shape of build_mcp_params' silent statewide fallback for a
named_market the exact-match alias set does not recognise ("Triangle (RDU MSA)",
"the Triangle", "RDU MSA / Triangle"). Tonight's Sonnet run (audit 5281-5287)
skipped the helpers entirely and hand-derived seven county calls from the prose,
so the helper API also has to be one command the session can paste from.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest
from conftest import load_skill_helpers

HERE = Path(__file__).parent.parent / "skills" / "external-comps"
helpers = load_skill_helpers("external-comps")


def _req(geo):
    return {
        "transaction_type": "sale",
        "asset_type": "retail",
        "geography": geo,
        "date_window": {"lookback_months": 12},
    }


@pytest.mark.parametrize(
    "spelling",
    [
        "Triangle",
        "the Triangle",
        "Triangle (RDU MSA)",
        "RDU MSA / Triangle",
        "Raleigh-Durham (Triangle)",
        "rdu",
        "Research Triangle",
    ],
)
def test_every_triangle_spelling_resolves_to_the_seven_county_fan_out(spelling):
    out = helpers.validate_request(_req({"named_market": spelling}))
    params = helpers.build_mcp_params(out["validated"])
    assert [p["county"] for p in params["params_list"]] == sorted(helpers.RDU_MSA_COUNTIES)
    assert all("city" not in p for p in params["params_list"])


def test_an_unregistered_named_market_never_falls_through_to_statewide():
    out = helpers.validate_request(_req({"named_market": "Charlotte MSA"}))
    with pytest.raises(helpers.UnknownMarket) as exc:
        helpers.build_mcp_params(out["validated"])
    assert "Charlotte MSA" in str(exc.value)
    assert "counties" in str(exc.value)


def test_an_empty_geography_dict_never_falls_through_to_statewide():
    out = helpers.validate_request(_req({}))
    params = helpers.build_mcp_params(out["validated"])
    # the RDU default applies, exactly like a missing geography
    assert {p["county"] for p in params["params_list"]} == set(helpers.RDU_MSA_COUNTIES)


def test_build_mcp_params_accepts_the_validate_request_wrapper_directly():
    # tonight's Sonnet session hit KeyError: transaction_type calling
    # build_mcp_params(validate_request(parsed)) and abandoned the helpers
    wrapped = helpers.validate_request(_req({"named_market": "Triangle"}))
    params = helpers.build_mcp_params(wrapped)
    assert len(params["params_list"]) == 7


def test_stale_connector_drop_is_a_hard_stop_not_a_note():
    v = helpers.validate_request(_req({"named_market": "Triangle"}))["validated"]
    rows = [
        {"county": "Wake", "property_address": "1 Main"},
        {"county": "Mecklenburg", "property_address": "2 Trade St"},
    ]
    kept, applied = helpers.apply_post_filters(rows, v, set(helpers.RDU_MSA_COUNTIES), keep_blank_county=True)
    assert len(kept) == 1
    assert helpers.STALE_CONNECTOR_NOTICE in applied
    with pytest.raises(helpers.StaleConnectorError) as e1:
        helpers.format_excel(kept, v, "c.xlsx", [], [], applied)
    with pytest.raises(helpers.StaleConnectorError) as e2:
        helpers.draft_email(kept, kept, v, "c.xlsx", [], [], applied)
    assert "Refresh tools list" in str(e1.value)
    assert "Refresh tools list" in str(e2.value)


def test_no_drop_means_no_notice_and_deliverables_compose():
    v = helpers.validate_request(_req({"named_market": "Triangle"}))["validated"]
    rows = [{"county": "Wake"}, {"county": ""}]
    kept, applied = helpers.apply_post_filters(rows, v, set(helpers.RDU_MSA_COUNTIES), keep_blank_county=True)
    assert len(kept) == 2
    assert helpers.STALE_CONNECTOR_NOTICE not in applied
    email = helpers.draft_email(kept, kept, v, "c.xlsx", [], [], applied)
    assert "subject" in email


def test_plan_cli_prints_the_exact_calls_to_paste(tmp_path):
    req = _req({"named_market": "the Triangle"})
    p = tmp_path / "req.json"
    p.write_text(json.dumps(req))
    out = subprocess.run(
        [sys.executable, str(HERE / "helpers.py"), "plan", str(p)],
        capture_output=True, text=True, check=True,
    )
    plan = json.loads(out.stdout)
    assert plan["tool_name"] == "search_external_sale_comps"
    assert [c["county"] for c in plan["params_list"]] == sorted(helpers.RDU_MSA_COUNTIES)
    assert plan["missing_required"] == []
    assert "applied_defaults" in plan and "post_filter_counties" in plan


def test_plan_cli_reports_an_unknown_market_instead_of_statewide(tmp_path):
    p = tmp_path / "req.json"
    p.write_text(json.dumps(_req({"named_market": "Charlotte MSA"})))
    out = subprocess.run(
        [sys.executable, str(HERE / "helpers.py"), "plan", str(p)],
        capture_output=True, text=True,
    )
    assert out.returncode != 0
    plan = json.loads(out.stdout)
    assert plan["params_list"] == []
    assert "Charlotte MSA" in plan["error"]


def test_skill_md_drives_the_plan_command_not_a_hand_built_call():
    text = (HERE / "SKILL.md").read_text()
    assert "helpers.py plan" in text
    assert "UnknownMarket" in text or "unregistered market" in text.lower()
    assert "STALE_CONNECTOR_NOTICE" in text or "Refresh tools list" in text


# --- review round 1 (PR #173) -------------------------------------------------

def _rdu():
    return helpers.validate_request(_req({"named_market": "Triangle"}))["validated"]


def test_blank_county_rows_never_trip_the_hard_stop_even_when_the_kwarg_is_omitted():
    # lee#515: blank county = the Worker matched it geometrically. A session that
    # forgets keep_blank_county=True must not be told its connector is broken.
    rows = [{"county": "Wake"}, {"county": ""}, {"county": None}]
    kept, applied = helpers.apply_post_filters(rows, _rdu(), set(helpers.RDU_MSA_COUNTIES))
    assert len(kept) == 3
    assert helpers.STALE_CONNECTOR_NOTICE not in applied
    assert "subject" in helpers.draft_email(kept, kept, _rdu(), "c.xlsx", [], [], applied)


def test_a_genuine_out_of_whitelist_row_trips_the_stop_with_the_kwarg_omitted():
    rows = [{"county": "Wake"}, {"county": "Mecklenburg"}]
    kept, applied = helpers.apply_post_filters(rows, _rdu(), set(helpers.RDU_MSA_COUNTIES))
    assert [r["county"] for r in kept] == ["Wake"]
    assert helpers.STALE_CONNECTOR_NOTICE in applied


def test_markdown_table_is_gated_too():
    v = _rdu()
    with pytest.raises(helpers.StaleConnectorError):
        helpers.markdown_table([], [], [], [], v, applied_filters=[helpers.STALE_CONNECTOR_NOTICE])
    assert isinstance(helpers.markdown_table([], [], [], [], v), str)


@pytest.mark.parametrize("geo", [{"cities": []}, {"cities": ["", "  "]}, {"counties": [], "cities": []}])
def test_blank_cities_default_to_rdu_like_blank_counties(geo):
    out = helpers.validate_request(_req(geo))
    assert out["validated"]["geography"] == {"named_market": "RDU MSA"}
    params = helpers.build_mcp_params(out["validated"])
    assert {p["county"] for p in params["params_list"]} == set(helpers.RDU_MSA_COUNTIES)


@pytest.mark.parametrize("spelling", ["Perdue", "Purdue", "Verdun", "Rduville", "Golden Triangle"])
def test_word_fragments_and_other_triangles_do_not_resolve_to_rdu(spelling):
    out = helpers.validate_request(_req({"named_market": spelling}))
    assert out["validated"]["geography"]["named_market"] != "RDU MSA"


@pytest.mark.parametrize("spelling", ["Raleigh/Durham", "Raleigh–Durham", "Raleigh - Durham", "RDU-MSA"])
def test_separator_variants_of_the_triangle_resolve_to_rdu(spelling):
    out = helpers.validate_request(_req({"named_market": spelling}))
    assert out["validated"]["geography"]["named_market"] == "RDU MSA"


def test_behavioral_rule_3_no_longer_tells_the_session_to_bounce_the_triangle():
    text = (HERE / "SKILL.md").read_text()
    rule3 = [l for l in text.splitlines() if l.startswith("3. **If the broker uses a term")]
    assert rule3 and "\"the Triangle,\"" not in rule3[0] and "IS recognized" in rule3[0]
    assert "plan → confirm" in text or "plan -> confirm" in text


def test_plan_cli_emits_json_on_malformed_input(tmp_path):
    out = subprocess.run([sys.executable, str(HERE / "helpers.py"), "plan", "{not json"], capture_output=True, text=True)
    assert out.returncode == 1
    assert "error" in json.loads(out.stdout)
