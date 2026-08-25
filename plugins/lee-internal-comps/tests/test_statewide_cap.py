"""
gi-plugins#158: a no-city external comps search over 200 rows silently dropped the rest.

Two mechanisms, one card:

1. The RDU path fetched STATEWIDE with intent that was REGIONAL. `named_market: RDU MSA`
   was one `state="NC"` call at `limit: 200` (newest first), post-filtered to the 7 RDU
   counties in Python -- so the cap bound on the whole NC book before the county filter
   ran, and 22-58% of RDU comps (by type) never reached the broker. Now it is one
   server-side `county` call per whitelist county (lee#496's typed param, Worker 0.51.0).

2. Any capped search said nothing. Worker 0.53.0 returns `truncated` (returned,
   total_available, limit, ordered_by, oldest_returned, note) when the result stopped at
   the cap with rows behind it; the skill pages by date cursor and says how much it got.

The reproducer for (1) is the shape from the card: an NC book whose 200 newest rows are
all outside RDU, with the RDU comps older than every one of them.
"""

from conftest import load_skill_helpers

helpers = load_skill_helpers("external-comps")

RDU_SALE = {
    "asset_type": "retail", "transaction_type": "sale",
    "geography": {"named_market": "RDU MSA"},
    "date_window": {"from": "2025-08-25", "to": "2026-08-25"},
    "min_sale_price": 500_000,
}


# --- a stand-in for the Worker's search: eq filters, date bounds, newest-first, LIMIT ---

def _iso(days_before: int, anchor: str = "2026-08-25") -> str:
    from datetime import date, timedelta
    y, m, d = (int(x) for x in anchor.split("-"))
    return (date(y, m, d) - timedelta(days=days_before)).isoformat()


def fake_worker(book: list[dict], params: dict) -> list[dict]:
    rows = book
    for key, col in (("city", "property_city"), ("county", "county"), ("state", "property_state"),
                     ("property_type", "property_type")):
        if key in params:
            rows = [r for r in rows if (r.get(col) or "") == params[key]]
    if "min_sale_date" in params:
        rows = [r for r in rows if r["sale_date"] >= params["min_sale_date"]]
    if "max_sale_date" in params:
        rows = [r for r in rows if r["sale_date"] <= params["max_sale_date"]]
    if "min_sale_price" in params:
        rows = [r for r in rows if r["sale_price"] >= params["min_sale_price"]]
    rows = sorted(rows, key=lambda r: r["sale_date"], reverse=True)
    return rows[: min(200, params.get("limit", 50))]


def statewide_book() -> list[dict]:
    """260 NC retail sales in window: the 200 newest are Charlotte / Mecklenburg,
    then 60 older Raleigh / Wake ones -- exactly the rows the old path never saw."""
    book = []
    for i in range(200):
        book.append({"external_id": f"clt{i}", "property_city": "Charlotte", "county": "Mecklenburg",
                     "property_state": "NC", "property_type": "Retail",
                     "sale_date": _iso(i), "sale_price": 1_000_000 + i})
    for i in range(60):
        book.append({"external_id": f"rdu{i}", "property_city": "Raleigh", "county": "Wake",
                     "property_state": "NC", "property_type": "Retail",
                     "sale_date": _iso(200 + i), "sale_price": 2_000_000 + i})
    return book


# --- 1. the RDU path goes server-side ---------------------------------------------------

def test_rdu_ask_fans_out_one_server_side_county_call_per_whitelist_county():
    out = helpers.build_mcp_params(RDU_SALE)
    assert out["tool_name"] == "search_external_sale_comps"
    counties = [p["county"] for p in out["params_list"]]
    assert counties == sorted(helpers.RDU_MSA_COUNTIES)
    assert all("city" not in p and p["state"] == "NC" for p in out["params_list"])
    # nothing left to post-filter: the whitelist is applied by the Worker now
    assert out["post_filter_counties"] is None


def test_rdu_comps_older_than_the_200_newest_statewide_rows_are_returned():
    book = statewide_book()
    newest_200_statewide = {r["external_id"] for r in fake_worker(book, {"state": "NC", "property_type": "Retail", "limit": 200})}
    assert not any(eid.startswith("rdu") for eid in newest_200_statewide)   # the vanishing rows

    out = helpers.build_mcp_params(RDU_SALE)
    rows = helpers.merge_rows(*(fake_worker(book, p) for p in out["params_list"]))
    filtered, _ = helpers.apply_post_filters(rows, RDU_SALE, out["post_filter_counties"])
    got = {r["external_id"] for r in filtered}
    assert got == {f"rdu{i}" for i in range(60)}
    assert got.isdisjoint(newest_200_statewide)


def test_rdu_aliases_still_resolve_to_the_county_fan_out():
    v = helpers.validate_request({"asset_type": "office", "transaction_type": "lease",
                                  "geography": {"named_market": "Triangle"}})["validated"]
    out = helpers.build_mcp_params(v)
    assert [p["county"] for p in out["params_list"]] == sorted(helpers.RDU_MSA_COUNTIES)
    assert out["post_filter_counties"] is None


def test_cities_and_counties_paths_are_unchanged():
    cities = helpers.build_mcp_params({**RDU_SALE, "geography": {"cities": ["Raleigh", "Cary"]}})
    assert [p["city"] for p in cities["params_list"]] == ["Raleigh", "Cary"]
    assert all("county" not in p for p in cities["params_list"])
    counties = helpers.build_mcp_params({**RDU_SALE, "geography": {"counties": ["Brunswick"]}})
    assert [p["county"] for p in counties["params_list"]] == ["Brunswick"]
    assert counties["post_filter_counties"] is None


# --- 2. a capped search is paged, and the broker hears what was retrieved -----------------

def _truncated(oldest: str, returned: int = 200, total: int = 431) -> dict:
    return {"rows": [], "truncated": {
        "returned": returned, "total_available": total, "limit": 200,
        "ordered_by": "sale_date DESC", "oldest_returned": oldest, "note": "…"}}


def test_next_page_params_moves_the_max_date_to_the_oldest_row_returned():
    params = {"state": "NC", "property_type": "Retail",
              "min_sale_date": "2023-08-25", "max_sale_date": "2026-08-25", "limit": 200}
    nxt = helpers.next_page_params(params, _truncated("2024-11-02"))
    assert nxt == {**params, "max_sale_date": "2024-11-02"}
    assert params["max_sale_date"] == "2026-08-25"          # input untouched


def test_next_page_params_uses_the_lease_date_bound_for_leases():
    params = {"state": "NC", "property_type": "Office",
              "min_lease_start_date": "2026-02-25", "max_lease_start_date": "2026-08-25", "limit": 200}
    resp = _truncated("2026-05-14")
    resp["truncated"]["ordered_by"] = "lease_start_date DESC"
    assert helpers.next_page_params(params, resp)["max_lease_start_date"] == "2026-05-14"


def test_next_page_params_is_none_when_the_result_was_complete_or_cannot_advance():
    params = {"state": "NC", "property_type": "Retail", "max_sale_date": "2026-08-25", "limit": 200}
    assert helpers.next_page_params(params, {"rows": []}) is None
    # a page whose oldest row is already the bound would re-fetch the same page forever
    assert helpers.next_page_params(params, _truncated("2026-08-25")) is None
    assert helpers.next_page_params(params, _truncated(None)) is None


def test_merge_rows_dedupes_on_external_id_keeping_the_first_seen():
    a = [{"external_id": "x1", "v": 1}, {"external_id": "x2", "v": 1}]
    b = [{"external_id": "x2", "v": 2}, {"external_id": "x3", "v": 2}]
    merged = helpers.merge_rows(a, b)
    assert [r["external_id"] for r in merged] == ["x1", "x2", "x3"]
    assert merged[1]["v"] == 1


def test_truncation_note_says_how_much_of_the_book_the_broker_is_looking_at():
    partial = helpers.truncation_note(retrieved=1000, total_available=1431, pages=5)
    assert "1,000" in partial and "1,431" in partial and "431" in partial
    assert "oldest" in partial.lower()
    complete = helpers.truncation_note(retrieved=431, total_available=431, pages=3)
    assert "431" in complete and "3 pages" in complete
    assert "not included" not in complete


def test_max_pages_bounds_a_runaway_survey():
    assert helpers.MAX_PAGES == 5
