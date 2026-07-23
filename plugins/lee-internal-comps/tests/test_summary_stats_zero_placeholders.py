"""Zero-placeholder exclusion in _compute_stats (gi-plugins#82).

89 of 225 staging sale comps store price_per_sf=0 (and similar) as an
"unknown-value" placeholder, not a real value. Including them printed
"Median $/SF: $0.00" on broker-facing Excel + email summaries. These tests pin
positive-only aggregation: the zeros are excluded from the stat math, while the
row COUNT still reflects every row (we drop nothing). Mirrors the Worker-side
fix in mcp-server/src/lib/summary_stats.ts.

Card: davidmshaner-gi/gi-plugins#82.
"""

from conftest import load_skill_helpers

helpers = load_skill_helpers("internal-comps")


def test_sale_stats_exclude_zero_placeholders():
    rows = [
        {"sale_price": 1_000_000, "price_per_sf": 100, "square_feet_sold": 10_000},
        {"sale_price": 3_000_000, "price_per_sf": 300, "square_feet_sold": 30_000},
        # placeholder row: all zeros = "unknown", must not drag stats to 0
        {"sale_price": 0, "price_per_sf": 0, "square_feet_sold": 0},
    ]
    s = helpers._compute_stats(rows, is_sale=True)

    # Count is unchanged — we exclude zeros from the math, not from the row set.
    assert s["count"] == 3

    # $/SF median is over the positive values only (100, 300) -> 200, NOT 0.
    assert s["median_price_per_sf"] == 200
    assert s["avg_price_per_sf"] == 200
    # Sale price aggregations skip the placeholder zero.
    assert s["median_sale_price"] == 2_000_000
    assert s["avg_sale_price"] == 2_000_000
    assert s["min_sale_price"] == 1_000_000
    assert s["max_sale_price"] == 3_000_000
    assert s["total_sale_volume"] == 4_000_000
    # Building SF: zero in square_feet_sold excluded (no building_size to fall back to).
    assert s["avg_building_sf"] == 20_000


def test_sale_building_sf_zero_falls_through_to_building_size():
    rows = [
        {"sale_price": 1_000_000, "price_per_sf": 100,
         "square_feet_sold": 0, "building_size": 20_000},
    ]
    s = helpers._compute_stats(rows, is_sale=True)
    # square_feet_sold=0 is a placeholder -> coalesce to building_size (20_000).
    assert s["avg_building_sf"] == 20_000


def test_lease_stats_exclude_zero_placeholders():
    rows = [
        {"effective_rate": 10.0, "asking_rate_per_sf": 12.0, "space_sf": 5_000},
        {"effective_rate": 20.0, "asking_rate_per_sf": 24.0, "space_sf": 15_000},
        {"effective_rate": 0, "asking_rate_per_sf": 0, "space_sf": 0},
    ]
    s = helpers._compute_stats(rows, is_sale=False)

    assert s["count"] == 3
    # Effective rate median over positives (10, 20) -> 15, NOT 0.
    assert s["median_effective_rate"] == 15.0
    assert s["avg_effective_rate"] == 15.0
    assert s["min_effective_rate"] == 10.0
    assert s["max_effective_rate"] == 20.0
    assert s["avg_asking_rate"] == 18.0
    assert s["avg_leased_sf"] == 10_000
    assert s["median_leased_sf"] == 10_000


def test_lease_leased_sf_zero_falls_through_to_square_feet_sold():
    rows = [
        {"effective_rate": 10.0, "space_sf": 0, "square_feet_sold": 8_000},
    ]
    s = helpers._compute_stats(rows, is_sale=False)
    assert s["avg_leased_sf"] == 8_000
