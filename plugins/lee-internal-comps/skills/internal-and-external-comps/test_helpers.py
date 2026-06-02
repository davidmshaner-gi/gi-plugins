from helpers import load_sibling


def test_load_sibling_imports_internal_and_external():
    internal = load_sibling("internal-comps")
    external = load_sibling("external-comps")
    assert hasattr(internal, "validate_request")
    assert hasattr(internal, "build_sql")
    assert hasattr(external, "validate_request")
    assert hasattr(external, "build_mcp_params")


from helpers import to_core, combine, SOURCE_INTERNAL, SOURCE_EXTERNAL


def test_to_core_internal_sale():
    row = {"comps_id": "i1", "street_address": "1 A St", "city": "Garner", "county": "Wake",
           "property_type": "Industrial", "building_size": 50000, "sale_price": 5000000,
           "price_per_sf": 100, "actual_cap_rate": 6.5, "actual_close_date": "2025-03-01"}
    core = to_core(row, SOURCE_INTERNAL, "sale")
    assert core["Source"] == SOURCE_INTERNAL
    assert core["Comp ID"] == "i1"
    assert core["Address"] == "1 A St"
    assert core["Size (SF)"] == 50000
    assert core["Sale Price"] == 5000000
    assert core["$/SF"] == 100
    assert core["Cap Rate"] == 6.5
    assert core["Date"] == "2025-03-01"
    # snake_case stat keys present for summary_stats parity
    assert core["sale_price"] == 5000000 and core["price_per_sf"] == 100
    assert core["square_feet_sold"] == 50000


def test_to_core_external_sale():
    row = {"external_id": "e1", "property_address": "2 B St", "property_city": "Cary",
           "county": "Wake", "property_type": "Industrial", "building_sf": 60000,
           "sale_price": 7200000, "price_per_sf": 120, "actual_cap_rate": 6.0,
           "sale_date": "2025-06-01", "costar_property_url": "https://costar/e1"}
    core = to_core(row, SOURCE_EXTERNAL, "sale")
    assert core["Comp ID"] == "e1"
    assert core["City"] == "Cary"
    assert core["Size (SF)"] == 60000
    assert core["Date"] == "2025-06-01"
    assert core["Source URL"] == "https://costar/e1"
    assert core["square_feet_sold"] == 60000  # external building_sf mapped to stat key


def test_to_core_internal_lease():
    row = {"comps_id": "i2", "street_address": "3 C St", "city": "Apex", "county": "Wake",
           "property_type": "Industrial", "space_sf": 12000, "effective_rate": 9.5,
           "asking_rate_per_sf": 10.0, "lease_execution": "2025-04-01", "lease_type": "NNN"}
    core = to_core(row, SOURCE_INTERNAL, "lease")
    assert core["Leased SF"] == 12000
    assert core["Rent"] == 9.5
    assert core["Date"] == "2025-04-01"
    assert core["Lease Type"] == "NNN"
    assert core["_leased_sf_is_building_size"] is False
    assert core["effective_rate"] == 9.5 and core["space_sf"] == 12000


def test_to_core_external_lease_unit_mismatch_flag():
    # W1: external lease "Leased SF" comes from building_sf (building size, not leased area)
    row = {"external_id": "e2", "property_address": "4 D St", "property_city": "Apex",
           "county": "Wake", "property_type": "Industrial", "building_sf": 40000,
           "base_rent": 11.0, "lease_start_date": "2025-05-01", "rent_type": "Gross"}
    core = to_core(row, SOURCE_EXTERNAL, "lease")
    assert core["Leased SF"] == 40000
    assert core["Rent"] == 11.0
    assert core["Lease Type"] == "Gross"
    assert core["_leased_sf_is_building_size"] is True
    assert core["effective_rate"] == 11.0 and core["space_sf"] == 40000


def test_combine_keeps_both_rows_and_sorts_desc():
    internal = [to_core({"comps_id": "i1", "street_address": "1 A St",
                         "actual_close_date": "2025-01-01", "building_size": 1,
                         "sale_price": 1, "price_per_sf": 1}, SOURCE_INTERNAL, "sale")]
    external = [to_core({"external_id": "e1", "property_address": "1 A St",
                         "sale_date": "2025-09-01", "building_sf": 1,
                         "sale_price": 1, "price_per_sf": 1}, SOURCE_EXTERNAL, "sale")]
    out = combine(internal, external, "sale")
    assert len(out) == 2                       # same address in both → BOTH kept (no dedup)
    assert out[0]["Date"] == "2025-09-01"      # most recent first
    assert {r["Source"] for r in out} == {SOURCE_INTERNAL, SOURCE_EXTERNAL}
