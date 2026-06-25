# plugins/lee-internal-comps/tests/test_owner_mailing_list.py
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "owner-mailing-list"))
import helpers

def test_safe_csv_name_emits_constant_stub(tmp_path):
    # The filename is a tiny constant (gi#7 / #112) — never the descriptive address.
    assert helpers._safe_csv_name(str(tmp_path)) == f"{helpers.CSV_STUB}.csv"
    assert helpers._safe_csv_name(str(tmp_path)) == "o.csv"

def test_safe_csv_name_enumerates_on_collision(tmp_path):
    # A second / third pull in the same session must not clobber the first.
    assert helpers._safe_csv_name(str(tmp_path)) == "o.csv"
    (tmp_path / "o.csv").write_text("")
    assert helpers._safe_csv_name(str(tmp_path)) == "o1.csv"
    (tmp_path / "o1.csv").write_text("")
    assert helpers._safe_csv_name(str(tmp_path)) == "o2.csv"

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
             "acreage": "3.1", "building_sf": 4200, "year_built": 1998,
             "land_class": "Vacant"}]
    req = {"subject_property": {"address": "100 Walnut St, Cary NC"}}
    out = helpers.format_csv(rows, req, date="2026-06-02", out_dir=str(tmp_path))
    assert os.path.basename(out) == "o.csv"
    with open(out) as f:
        header = f.readline().strip()
    assert header == "owner,mail_addr,site_addr,acreage,building_sf,year_built,land_class"


def test_format_csv_name_is_independent_of_address(tmp_path):
    # gi#7 / #112: the Windows 218-char limit means the descriptive address can
    # never enter the filename — a 200-char address still yields the tiny stub.
    rows = [{"owner": "ACME LLC", "mail_addr": "PO Box 5", "site_addr": "0 Maple"}]
    long_addr = "X" * 200 + " St, Cary NC"
    req = {"subject_property": {"address": long_addr}}
    out = helpers.format_csv(rows, req, date="2026-06-02", out_dir=str(tmp_path))
    base = os.path.basename(out)
    assert base == "o.csv"
    assert "/" not in base and "\\" not in base
    assert os.path.exists(out)
    # a second pull in the same dir enumerates rather than clobbering
    out2 = helpers.format_csv(rows, req, date="2026-06-02", out_dir=str(tmp_path))
    assert os.path.basename(out2) == "o1.csv"
    assert os.path.exists(out2)


def test_parse_request_improved_keyword_sets_improved_only():
    for text in [
        "owners of buildings within 2 miles of 100 Walnut St, Cary NC",
        "improved parcels within 2 miles of 100 Walnut St, Cary NC",
        "who owns the commercial buildings near 100 Walnut St, Cary NC",
        "parcels with a structure within 2 miles of 100 Walnut St, Cary NC",
    ]:
        r = helpers.parse_request(text)
        assert r["improved_only"] is True, text


def test_parse_request_vacant_request_is_not_improved():
    r = helpers.parse_request(
        "owners of 2-5 acre vacant land within 3 miles of 100 Walnut St, Cary NC")
    assert r["improved_only"] is False


def test_parse_request_contradiction_vacant_wins_over_improved():
    # "vacant buildings" is contradictory; vacant wins, improved_only off, so we
    # never send the tool land_class=vacant AND improved_only=true.
    r = helpers.parse_request(
        "owners of vacant buildings within 2 miles of 100 Walnut St, Cary NC")
    assert r["land_class"] == "vacant"
    assert r["improved_only"] is False


def test_rows_from_mcp_maps_tool_rows_to_csv_shape():
    mcp = [{
        "county": "WAKE", "parcel_id": "0763592649",
        "owner_raw": "ACME LLC",
        "owner_mail_address": "PO BOX 5\nCARY NC 27513",
        "address": "0 MAPLE ST", "lot_size_acres": 3.1,
        "building_sf": 4200, "year_built": 1998,
        "land_use": "V", "distance_mi": 0.4,
    }]
    out = helpers.rows_from_mcp(mcp)
    assert out == [{"owner": "ACME LLC", "mail_addr": "PO BOX 5 CARY NC 27513",
                    "site_addr": "0 MAPLE ST", "acreage": 3.1,
                    "building_sf": 4200, "year_built": 1998, "land_class": "V"}]


def test_rows_from_mcp_tolerates_nulls():
    out = helpers.rows_from_mcp([{"owner_raw": None, "owner_mail_address": None,
                                  "address": None, "lot_size_acres": None,
                                  "building_sf": None, "year_built": None,
                                  "land_use": None}])
    assert out == [{"owner": "", "mail_addr": "", "site_addr": "",
                    "acreage": "", "building_sf": "", "year_built": "",
                    "land_class": ""}]
