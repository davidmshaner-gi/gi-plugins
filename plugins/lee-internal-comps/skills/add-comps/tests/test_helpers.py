"""
Tests for the add-comps skill helpers (B1-B3).

The add-comps skill lets a Lee operator paste a contributed comp set (e.g. a
forwarded email with several brokerage comp tables) and normalize it into the
canonical AddCompRow schema for ingestion via the `lee_comps_add_write` MCP
tool. These tests are pure-Python; the model orchestrates MCP, the helpers are
deterministic.

Run from the skill dir: python3 -m pytest tests/ -v
"""

import os
import sys
from collections import Counter

# Import helpers.py from the skill dir (parent of tests/).
sys.path.insert(
    0, os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from helpers import (  # noqa: E402
    apply_alias_map,
    detect_transaction_type,
    parse_email,
    validate_row,
)


# ---------------------------------------------------------------------------
# B1 — normalized-row schema + validation
# ---------------------------------------------------------------------------

def test_validate_lease_row_missing_rate_and_size_flags():
    """A lease row missing rate and size gets flagged=1 with a reason; not dropped."""
    row = {
        "transaction_type": "lease",
        "property_address": "1779 Example Dr",
        "lease_start": "2025Q3",
        # no base_rent, no leased_sf / building_sf
    }
    out = validate_row(row)
    assert out["flagged"] == 1
    assert out["flag_reason"]  # non-empty
    assert "base_rent" in out["flag_reason"]


def test_validate_complete_lease_row_not_flagged():
    """A complete lease row (address + size + rate + date) is flagged=0."""
    row = {
        "transaction_type": "lease",
        "property_address": "1779 Example Dr",
        "leased_sf": 25500,
        "base_rent": 13.07,
        "lease_start": "2025Q3",
    }
    out = validate_row(row)
    assert out["flagged"] == 0
    assert not out.get("flag_reason")


def test_validate_lease_row_size_via_building_sf_ok():
    """building_sf satisfies the size requirement when leased_sf is absent."""
    row = {
        "transaction_type": "lease",
        "property_address": "1779 Example Dr",
        "building_sf": 25500,
        "base_rent": 13.07,
        "lease_start": "2025Q3",
    }
    out = validate_row(row)
    assert out["flagged"] == 0


def test_validate_complete_sale_row_not_flagged():
    row = {
        "transaction_type": "sale",
        "property_address": "100 Main St",
        "sale_price": 6_000_000,
        "sale_date": "2025-03-01",
    }
    out = validate_row(row)
    assert out["flagged"] == 0


def test_validate_sale_row_missing_price_flags():
    row = {
        "transaction_type": "sale",
        "property_address": "100 Main St",
        "sale_date": "2025-03-01",
    }
    out = validate_row(row)
    assert out["flagged"] == 1
    assert "sale_price" in out["flag_reason"]


def test_validate_never_drops_row():
    """validate_row mutates/returns the same row; even an empty one survives."""
    row = {"transaction_type": "lease"}
    out = validate_row(row)
    assert out is not None
    assert out["flagged"] == 1


# ---------------------------------------------------------------------------
# B2 — alias maps + Txn-Type vocab + lease-vs-sale detection
# ---------------------------------------------------------------------------

def test_detect_transaction_type_lease():
    headers = [
        "Type of Property", "Class", "Tenant", "Landlord", "Sign Date",
        "SF", "Transaction Type", "Term (months)", "Year One Base Rent NNN",
    ]
    assert detect_transaction_type(headers) == "lease"


def test_detect_transaction_type_sale():
    headers = [
        "Address", "Sale Price", "Sale Date", "Buyer", "Seller", "Cap Rate",
    ]
    assert detect_transaction_type(headers) == "sale"


def test_apply_alias_map_lease_folds_headers():
    raw = {
        "Type of Property": "Industrial",
        "Class": "A",
        "Tenant": "Tenant 0",
        "Landlord": "Landlord 0",
        "Sign Date": "2025Q3",
        "SF": "25,500",
        "Transaction Type": "Sublease",
        "Term (months)": "60",
        "Year One Base Rent NNN": "$13.07",
        "Escalations": "3.00%",
        "Free Rent (months)": "3",
        "TI / SF; concessions": "$13/SF TIA",
        "Address (Park)": "1779 Example Dr",
        "City": "Durham",
        "Submarket": "South Wake",
    }
    out = apply_alias_map(raw, "lease")
    assert out["property_type"] == "Industrial"
    assert out["building_class"] == "A"
    assert out["tenant_name"] == "Tenant 0"
    assert out["landlord"] == "Landlord 0"
    assert out["lease_start"] == "2025Q3"
    assert out["leased_sf"] == 25500
    assert out["txn_subtype"] == "Sublease"
    assert out["lease_term_months"] == 60
    assert out["base_rent"] == 13.07
    assert out["escalations"] == "3.00%"
    assert out["free_rent_months"] == 3.0
    assert out["ti_concessions"] == "$13/SF TIA"
    assert out["property_address"] == "1779 Example Dr"
    assert out["property_city"] == "Durham"
    assert out["submarket"] == "South Wake"


def test_apply_alias_map_sale_folds_headers():
    raw = {
        "Address": "100 Main St",
        "Sale Price": "$6,000,000",
        "$/SF": "$120.00",
        "Sale Date": "2025-03-01",
        "Cap Rate": "6.5%",
        "Buyer": "Acme REIT",
        "Seller": "Old Owner LLC",
        "% Leased": "95%",
    }
    out = apply_alias_map(raw, "sale")
    assert out["sale_price"] == 6_000_000
    assert out["sale_price_per_sf"] == 120.0
    assert out["sale_date"] == "2025-03-01"
    assert out["buyer"] == "Acme REIT"
    assert out["seller"] == "Old Owner LLC"


def test_apply_alias_map_base_rent_dollar_coercion():
    out = apply_alias_map({"Year One Base Rent NNN": "$12.50"}, "lease")
    assert out["base_rent"] == 12.50


def test_apply_alias_map_subtype_preserved_verbatim():
    for subtype in ["New Lease", "Sublease", "Renewal", "Renewal/Expansion", "New (pending)"]:
        out = apply_alias_map({"Transaction Type": subtype}, "lease")
        assert out["txn_subtype"] == subtype


def test_apply_alias_map_unmapped_cols_into_raw_fields_json():
    import json
    raw = {"Tenant": "T", "Mystery Column": "keepme"}
    out = apply_alias_map(raw, "lease")
    assert "raw_fields_json" in out
    preserved = json.loads(out["raw_fields_json"])
    assert preserved["Mystery Column"] == "keepme"


def test_apply_alias_map_size_aliases():
    a = apply_alias_map({"Size Leased SF": "12,000"}, "lease")
    assert a["leased_sf"] == 12000
    b = apply_alias_map({"Bldg SF": "80,000"}, "lease")
    assert b["building_sf"] == 80000


# ---------------------------------------------------------------------------
# B3 — email adapter (golden test)
# ---------------------------------------------------------------------------

def test_silas_email_parses_30_rows_4_sources():
    html = open(
        os.path.join(os.path.dirname(__file__), "fixtures", "silas_email.html")
    ).read()
    rows = parse_email(html)
    assert len(rows) == 30
    assert Counter(r["original_source"] for r in rows) == {
        "JLL": 12, "Foundry": 4, "Tri Property": 9, "Prologis": 5,
    }
    assert all(r["transaction_type"] == "lease" for r in rows)
    subl = [r for r in rows if r.get("txn_subtype") == "Sublease"]
    assert any(r.get("leased_sf") == 25500 for r in subl)


def test_silas_email_ignores_decoy_tables():
    """Signature + confidentiality decoys must not produce rows."""
    html = open(
        os.path.join(os.path.dirname(__file__), "fixtures", "silas_email.html")
    ).read()
    rows = parse_email(html)
    # No row should carry the decoy text in any value.
    blob = " ".join(str(v) for r in rows for v in r.values())
    assert "Confidentiality Notice" not in blob
    assert "Research Analyst" not in blob


def test_silas_email_rows_are_validated():
    """Every parsed row carries a flagged key (validate_row ran)."""
    html = open(
        os.path.join(os.path.dirname(__file__), "fixtures", "silas_email.html")
    ).read()
    rows = parse_email(html)
    assert all("flagged" in r for r in rows)
    assert all(r["flagged"] in (0, 1) for r in rows)
