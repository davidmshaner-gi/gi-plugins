# plugins/lee-internal-comps/tests/test_owner_mailing_list.py
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "owner-mailing-list"))
import helpers
import county_registry as reg

def test_slugify_basic():
    assert helpers.slugify("100 Walnut St, Cary NC") == "100-walnut-st-cary-nc"

def test_default_output_path_is_flat_and_short():
    req = {"subject_property": {"address": "100 Walnut St, Cary NC"}}
    p = helpers.default_output_path(req, date="2026-06-02")
    # flat: no directory separators, no subfolder
    assert "/" not in p and "\\" not in p
    assert p == "owners-100-walnut-st-cary-nc-2026-06-02.csv"
    # whole filename comfortably under the 218-char budget worst case
    assert len(p) < 80

def test_parse_request_extracts_core_fields():
    text = "owners of 2-5 acre vacant land within 3 miles of 100 Walnut St, Cary NC"
    r = helpers.parse_request(text)
    assert r["subject_property"]["address"].startswith("100 Walnut St")
    assert r["radius_mi"] == 3.0
    assert r["size"] == {"min_acres": 2.0, "max_acres": 5.0}
    assert "vacant" in r["land_class"].lower()

def test_parse_request_missing_radius_returns_none():
    r = helpers.parse_request("owners near 4204 Six Forks Rd, retail")
    assert r["radius_mi"] is None
    assert r["subject_property"]["address"].startswith("4204 Six Forks")

def test_parse_request_from_connector():
    r = helpers.parse_request("2 miles from 4204 Six Forks Rd, Cary NC")
    assert r["radius_mi"] == 2.0
    assert r["subject_property"]["address"].startswith("4204")

def test_dedupe_by_mailing_address():
    rows = [
        {"owner": "ACME LLC", "mail_addr": "PO Box 5, Cary NC", "site_addr": "0 Maple"},
        {"owner": "ACME LLC", "mail_addr": "po box 5, cary nc",  "site_addr": "0 Oak"},   # dup (case/space)
        {"owner": "BETA LP",  "mail_addr": "1 Main St, Apex NC",  "site_addr": "2 Elm"},
    ]
    out, report = helpers.dedupe_by_mailing_address(rows)
    assert len(out) == 2
    assert report == {"input": 3, "output": 2, "dropped": 1}

def test_dedupe_preserves_no_address_rows():
    rows = [
        {"owner": "ACME LLC", "mail_addr": None,   "site_addr": "0 Maple"},
        {"owner": "BETA LP",  "mail_addr": "",      "site_addr": "2 Elm"},
        {"owner": "GAMMA INC", "mail_addr": "  ",   "site_addr": "4 Oak"},
    ]
    out, report = helpers.dedupe_by_mailing_address(rows)
    assert len(out) == 3
    assert report == {"input": 3, "output": 3, "dropped": 0}

def test_format_csv_writes_flat_file(tmp_path):
    rows = [{"owner": "ACME LLC", "mail_addr": "PO Box 5", "site_addr": "0 Maple",
             "acreage": "3.1", "land_class": "Vacant"}]
    req = {"subject_property": {"address": "100 Walnut St, Cary NC"}}
    out = helpers.format_csv(rows, req, date="2026-06-02", out_dir=str(tmp_path))
    assert out.endswith("owners-100-walnut-st-cary-nc-2026-06-02.csv")
    with open(out) as f:
        header = f.readline().strip()
    assert header == "owner,mail_addr,site_addr,acreage,land_class"

def test_registry_resolves_wake_case_insensitive():
    e = reg.resolve_county("Wake County")
    assert e is not None
    assert "arcgis" in e["service_url"].lower() or "MapServer" in e["service_url"]
    fm = e["field_map"]
    for k in ("acreage", "land_class", "bldg_val", "owner", "mail_addr", "site_addr"):
        assert k in fm

def test_registry_returns_none_for_uncovered():
    assert reg.resolve_county("Mecklenburg County") is None


def test_build_rows_joins_mail_concat_fields():
    # split mailing address (street + city + state + zip) must survive
    entry = {
        "field_map": {"acreage": "AC", "land_class": "LC", "bldg_val": "BV",
                      "owner": "OWN", "mail_addr": "M1", "site_addr": "SITE"},
        "mail_concat": ["M1", "M2", "CITY", "ST", "ZIP"],
    }
    raw = [{"OWN": "ACME LLC", "M1": "PO BOX 5", "M2": "", "CITY": "CARY",
            "ST": "NC", "ZIP": "27513", "SITE": "0 MAPLE", "AC": 3.1, "LC": "Vacant"}]
    out = helpers.build_rows(raw, entry)
    assert out == [{"owner": "ACME LLC", "mail_addr": "PO BOX 5 CARY NC 27513",
                    "site_addr": "0 MAPLE", "acreage": 3.1, "land_class": "Vacant"}]

def test_build_rows_without_concat_uses_field_map():
    entry = {"field_map": {"acreage": "AC", "land_class": "LC", "bldg_val": "BV",
                           "owner": "OWN", "mail_addr": "MAIL", "site_addr": "SITE"}}
    raw = [{"OWN": "BETA", "MAIL": "1 Main St, Apex NC", "SITE": "2 Elm", "AC": 5.0, "LC": "V"}]
    out = helpers.build_rows(raw, entry)
    assert out[0]["mail_addr"] == "1 Main St, Apex NC"
    assert out[0]["site_addr"] == "2 Elm"

def test_build_rows_empty_site_field_is_blank_not_error():
    # Orange County has site_addr="" (no situs field) -> must not raise, returns ""
    entry = {"field_map": {"acreage": "AC", "land_class": "LC", "bldg_val": "BV",
                           "owner": "OWN", "mail_addr": "A1", "site_addr": ""},
             "mail_concat": ["A1", "A2"]}
    raw = [{"OWN": "X", "A1": "123 Rd", "A2": "Durham NC", "AC": 2, "LC": "v"}]
    out = helpers.build_rows(raw, entry)
    assert out[0]["site_addr"] == ""
    assert out[0]["mail_addr"] == "123 Rd Durham NC"

def test_build_rows_against_real_wake_entry():
    # integration: real Wake registry entry + a realistic ArcGIS row
    e = reg.resolve_county("Wake")
    raw = [{"OWNER": "WAKE STONE CORP", "ADDR1": "PO BOX 190", "ADDR2": "",
            "ADDR3": "KNIGHTDALE NC 27545", "SITE_ADDRESS": "0 OLD US 1",
            "DEED_ACRES": 4.2, "LAND_CLASS_DECODE": "Vacant"}]
    out = helpers.build_rows(raw, e)
    assert out[0]["owner"] == "WAKE STONE CORP"
    assert out[0]["mail_addr"] == "PO BOX 190 KNIGHTDALE NC 27545"
