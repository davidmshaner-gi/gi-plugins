"""Helpers for the internal-and-external-comps skill — the unified "all comps" default.

This skill is a thin orchestrator: it reuses the parse/validate/query logic of the
sibling `internal-comps` and `external-comps` skills (via load_sibling) and adds the
contributed leg (contributed_params, filter_contributed, lee-and-associates#636) and the
combine layer (to_core, combine, format_unified_excel, unified_markdown_table).

`python3 helpers.py plan '<request json>'` prints the exact call for all three legs.
"""
import importlib.util
import json
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path


def load_sibling(skill_name: str):
    """Import a sibling skill's helpers.py by skill-dir name.

    Sibling skills live at ../<skill_name>/helpers.py relative to this file. Returns the
    imported module. Cached in sys.modules so repeated calls are cheap and idempotent.
    """
    path = Path(__file__).resolve().parent.parent / skill_name / "helpers.py"
    mod_name = f"_sibling_{skill_name.replace('-', '_')}"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"load_sibling: cannot build import spec for {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod


# =====================================================================
# Core schema + combine  (the unified "all comps" merge layer)
# =====================================================================

SOURCE_INTERNAL = "Internal — Dealius"
SOURCE_EXTERNAL = "External"
# lee-and-associates#636: comps GI loaded from broker-forwarded comp sets
# (`source = broker_added` in the unified view). Their own label, never folded
# into Internal or External.
SOURCE_CONTRIBUTED = "Contributed"


def _first(row: dict, *keys):
    """First non-empty value among keys (None/"" treated as empty)."""
    for k in keys:
        v = row.get(k)
        if v not in (None, ""):
            return v
    return None


def to_core(row: dict, source: str, tx_type: str) -> dict:
    """Map one source row (internal Dealius or external) to the unified CORE schema.

    The core row carries BOTH display-label keys (what the unified table/Excel/PDF render)
    AND the snake_case stat keys that the MCP `computeSummaryStats` reads server-side
    (sale: sale_price/price_per_sf/square_feet_sold; lease: effective_rate/
    asking_rate_per_sf/space_sf). Internal rows already use those snake_case names; external
    rows are mapped onto them here so stats work regardless of source.
    """
    if source == SOURCE_CONTRIBUTED:
        return _contributed_core(row, tx_type)
    is_internal = source.startswith("Internal")
    if is_internal:
        comp_id = row.get("comps_id")
        address = row.get("street_address")
        city = row.get("city")
        url = ""
    else:
        # Broker-readable id: prefer the external platform's id, then the short external_comp_id.
        # NEVER external_id (a 64-char address hash that overflows the comp table).
        comp_id = row.get("external_property_id") or row.get("external_comp_id") or ""
        address = row.get("property_address")
        city = row.get("property_city")
        url = row.get("external_property_url") or ""
    county = row.get("county")
    asset = row.get("property_type")

    if tx_type == "sale":
        if is_internal:
            size = _first(row, "square_feet_sold", "building_size")
            date = row.get("actual_close_date")
        else:
            size = row.get("building_sf")
            date = row.get("sale_date")
        cap = _first(row, "actual_cap_rate", "asking_cap_rate")
        sale_price = row.get("sale_price")
        ppsf = row.get("price_per_sf")
        return {
            "Source": source,
            "Comp ID": comp_id,
            "Address": address,
            "City": city,
            "County": county,
            "Asset Type": asset,
            "Size (SF)": size,
            "Sale Price": sale_price,
            "$/SF": ppsf,
            "Cap Rate": cap,
            "Date": date,
            "Source URL": url,
            # snake_case stat keys (server-side computeSummaryStats parity)
            "sale_price": sale_price,
            "price_per_sf": ppsf,
            "square_feet_sold": size,
        }

    # lease
    if is_internal:
        leased = _first(row, "space_sf", "square_feet_sold")
        rent = _first(row, "effective_rate", "asking_rate_per_sf")
        asking = row.get("asking_rate_per_sf")
        date = _first(row, "lease_execution", "lease_commencement")
        lease_type = row.get("lease_type")
    else:
        # leased_sf is the external platform's "Size Leased SF", promoted to a
        # typed column and backfilled (lee#469, closes lee#180). building_sf is the
        # building footprint and must NEVER stand in for the leased premises
        # (gi-plugins#105, Will Fogleman 2026-06-17): a row without leased_sf
        # renders BLANK rather than mislabel building size. 0 is an unknown-value
        # placeholder, never a real size (gi-plugins#82), so it renders blank too.
        leased = row.get("leased_sf") or None
        rent = row.get("base_rent")
        asking = None
        date = row.get("lease_start_date")
        lease_type = row.get("rent_type")
    return {
        "Source": source,
        "Comp ID": comp_id,
        "Address": address,
        "City": city,
        "County": county,
        "Asset Type": asset,
        "Leased SF": leased,
        "Rent": rent,
        "Date": date,
        "Lease Type": lease_type,
        "Source URL": url,
        # snake_case stat keys (server-side computeSummaryStats parity)
        "effective_rate": rent,
        "asking_rate_per_sf": asking,
        "space_sf": leased,
    }


# =====================================================================
# Contributed leg (lee-and-associates#636)
# =====================================================================

CONTRIBUTED_LIMIT = 500
# Columns of a unified row that are GI bookkeeping, never broker content: who
# loaded the comp and the tenant key. Kept out of the Contributed sheet.
_CONTRIBUTED_PRIVATE = ("added_by", "client_id")


def _iso_window(date_window: dict) -> tuple:
    """(from_iso, to_iso) for a validated date_window: explicit from/to, or a
    lookback of N months counted as N x 30 days (the internal leg's rule)."""
    w = date_window or {}
    today = date.today()
    if w.get("from"):
        return str(w["from"]), str(w.get("to") or today.isoformat())
    months = int(w.get("lookback_months", 12))
    return (today - timedelta(days=months * 30)).isoformat(), today.isoformat()


def contributed_params(validated: dict) -> dict:
    """The one pull_unified_comps call for the contributed leg.

    Lease asks size the space leased (`leased_sf_*`): contributed lease rows carry
    no building SF, so a building band reaches none of them. Sale asks size the
    building. The unified tool has no location filter; run filter_contributed on
    the rows it returns.
    """
    if "validated" in validated and "transaction_type" not in validated:
        validated = validated["validated"]
    tx = validated["transaction_type"]
    asset = str(validated.get("asset_type") or "")
    params = {"transaction_type": tx, "sources": ["broker_added"],
              "limit": CONTRIBUTED_LIMIT}
    if asset:
        params["property_type"] = asset  # family-aware on the Worker (0.59.0)
    params["date_from"], params["date_to"] = _iso_window(validated.get("date_window"))
    sr = validated.get("size_range") or {}
    key = "leased_sf" if tx == "lease" else "building_sf"
    if sr.get("min_sf") is not None:
        params[f"{key}_min"] = int(sr["min_sf"])
    if sr.get("max_sf") is not None:
        params[f"{key}_max"] = int(sr["max_sf"])
    return {"tool_name": "pull_unified_comps", "params": params}


def filter_contributed(rows: list, validated: dict) -> tuple:
    """Apply the ask's geography to contributed rows. Returns (kept, note).

    Cities and named markets match `property_city` case-insensitively (a named
    market resolves to its city list, the internal leg's rule; the RDU market also
    takes every city the RDU table places in its seven counties, the external
    leg's rule, so Smithfield or Hillsborough is never dropped). County asks map
    the city to its county with the RDU city table. A row with no city is kept
    and counted in the note (where it is cannot be checked); a row whose city
    is known and outside the ask is dropped and counted. For a county outside
    the Triangle the table cannot place cities, so rows there are kept and
    counted as unchecked.
    """
    if "validated" in validated and "transaction_type" not in validated:
        validated = validated["validated"]
    internal = load_sibling("internal-comps")
    external = load_sibling("external-comps")
    geo = validated.get("geography") or {}
    city_to_county = {c.lower(): k.lower() for c, k in external.RDU_CITY_TO_COUNTY.items()}
    rdu_counties = {c.lower() for c in external.RDU_MSA_COUNTIES}
    counties = set(internal._resolve_counties(geo))
    cities = {c.lower() for c in internal._resolve_cities(geo)} if not counties else set()
    rdu_cities = {c.lower() for c in internal.RDU_MSA_CITIES}
    if cities and not geo.get("cities") and cities == rdu_cities:
        cities |= {c for c, k in city_to_county.items() if k in rdu_counties}

    kept, dropped, cityless, unchecked = [], 0, 0, 0
    for r in rows:
        city = str(r.get("property_city") or "").strip().lower()
        if not city:
            kept.append(r)
            cityless += 1
            continue
        if counties:
            county = city_to_county.get(city)
            if county in counties:
                kept.append(r)
            elif county is None and counties - rdu_counties:
                kept.append(r)
                unchecked += 1
            else:
                dropped += 1
        elif city in cities:
            kept.append(r)
        else:
            dropped += 1

    parts = [f"Contributed: {len(kept)} comps"]
    if dropped:
        parts.append(f"{dropped} outside the requested area left out")
    if cityless:
        parts.append(f"{cityless} with no city on file kept (location not checked)")
    if unchecked:
        parts.append(f"{unchecked} whose county could not be checked kept")
    return kept, "; ".join(parts) + "."


def _contributed_core(row: dict, tx_type: str) -> dict:
    """Map one pull_unified_comps row (source broker_added) to the core schema."""
    base = {
        "Source": SOURCE_CONTRIBUTED,
        "Comp ID": row.get("comp_id"),
        "Address": row.get("property_address"),
        "City": row.get("property_city"),
        "County": None,
        "Asset Type": row.get("property_type"),
        "Source URL": "",
    }
    if tx_type == "sale":
        size = row.get("building_sf")
        return {**base, "Size (SF)": size, "Sale Price": row.get("sale_price"),
                "$/SF": row.get("sale_price_per_sf"), "Cap Rate": None,
                "Date": row.get("sale_date"),
                "sale_price": row.get("sale_price"),
                "price_per_sf": row.get("sale_price_per_sf"), "square_feet_sold": size}
    # The leased premises only, never the building (gi-plugins#105); 0 is unknown.
    leased = row.get("leased_sf") or None
    rent = row.get("base_rent")
    return {**base, "Leased SF": leased, "Rent": rent, "Date": row.get("lease_date"),
            "Lease Type": row.get("rent_type"),
            "effective_rate": rent, "asking_rate_per_sf": None, "space_sf": leased}


def source_counts(core_rows: list) -> dict:
    """Rows per Source label, for the reply's per-source counts."""
    out: dict = {}
    for r in core_rows:
        out[r.get("Source")] = out.get(r.get("Source"), 0) + 1
    return out


def _parse_date(value) -> "date | None":
    """Parse a core-row Date into a real date for chronological sorting (gi-plugins#62).

    Internal rows carry MM/DD/YYYY (from actual_close_date / lease_execution); external
    rows carry ISO YYYY-MM-DD (from sale_date / lease_start_date). A naive string sort
    interleaves the two formats wrong (e.g. "12/01/2020" sorts after "2026-01-01").
    Returns None for missing/blank/unparseable values so they sort LAST, never crash.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    # Trim a time component if one rode along (e.g. "2026-01-15 00:00:00").
    s = s.split("T")[0].split(" ")[0]
    # "2025Q2": how the first contributed import stores its lease dates (lee#636).
    # Sorted at the quarter's midpoint, the 15th of its middle month (the Worker's
    # and lee#637's rule).
    q = re.fullmatch(r"(\d{4})-?Q([1-4])", s, flags=re.IGNORECASE)
    if q:
        return date(int(q.group(1)), 3 * int(q.group(2)) - 1, 15)
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def combine(internal_core: list, external_core: list, tx_type: str,
            contributed_core: list = ()) -> list:
    """Concatenate internal + external + contributed core rows, sort most-recent-Date
    first. NO dedup — a property present in several sources stays as one row per
    source, each tagged by Source.

    Dates are parsed to real dates before sorting (gi-plugins#62) because internal
    (MM/DD/YYYY) and external (ISO) formats can't be compared as raw strings. Rows with
    a missing/blank/unparseable Date sort last.
    """
    rows = list(internal_core) + list(external_core) + list(contributed_core)

    def _key(r):
        # (has_date, date) so real dates sort most-recent-first and blanks fall to the
        # bottom under reverse=True (False < True, and date.min anchors the blanks).
        d = _parse_date(r.get("Date"))
        return (d is not None, d or date.min)

    rows.sort(key=_key, reverse=True)
    return rows


# =====================================================================
# Unified output: chat table + Excel
# =====================================================================

CORE_COLUMNS_SALE = ["Source", "Comp ID", "Address", "City", "County", "Asset Type",
                     "Size (SF)", "Sale Price", "$/SF", "Cap Rate", "Date"]
CORE_COLUMNS_LEASE = ["Source", "Comp ID", "Address", "City", "County", "Asset Type",
                      "Leased SF", "Rent", "Date", "Lease Type"]

LEE_BRAND_MAROON = "97012D"


def _core_columns(tx_type: str) -> list:
    return CORE_COLUMNS_SALE if tx_type == "sale" else CORE_COLUMNS_LEASE


def _fmt(value) -> str:
    """Plain display formatting for a cell value (markdown + Excel fallback)."""
    if value is None or value == "":
        return ""
    return str(value)


def unified_markdown_table(core_rows: list, validated: dict) -> str:
    """Combined chat table over the core columns, Source first.

    External lease rows show the leased premises (`leased_sf`, lee#469) or blank when
    it is absent — never the building size (gi-plugins#105), so there is no
    building-size-substitution footnote.
    """
    tx_type = validated.get("comp_type") or validated.get("transaction_type") or "sale"
    cols = _core_columns(tx_type)
    lines = ["| " + " | ".join(cols) + " |",
             "| " + " | ".join("---" for _ in cols) + " |"]
    for r in core_rows:
        lines.append("| " + " | ".join(_fmt(r.get(c)) for c in cols) + " |")
    md = "\n".join(lines)
    return md


def format_unified_excel(core_rows: list, internal_native: list, external_native: list,
                         validated: dict, xlsx_path: str,
                         contributed_native: list = ()) -> str:
    """Write a 4-sheet workbook: 'All Comps' (core rows, Source first) + native detail
    sheets for each source (Internal, External, Contributed). Returns xlsx_path.
    Lee-maroon header row on every sheet."""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment

    header_fill = PatternFill("solid", start_color=LEE_BRAND_MAROON)
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    wrap = Alignment(horizontal="center", vertical="center", wrap_text=True)
    tx_type = validated.get("comp_type") or validated.get("transaction_type") or "sale"

    def _write_sheet(ws, columns, rows):
        for ci, col in enumerate(columns, start=1):
            c = ws.cell(row=1, column=ci, value=col)
            c.fill = header_fill
            c.font = header_font
            c.alignment = wrap
        for ri, row in enumerate(rows, start=2):
            for ci, col in enumerate(columns, start=1):
                ws.cell(row=ri, column=ci, value=row.get(col))

    wb = Workbook()
    # Sheet 1 — All Comps (core)
    ws_all = wb.active
    ws_all.title = "All Comps"
    _write_sheet(ws_all, _core_columns(tx_type), core_rows)

    # Sheet 2 — Internal (Dealius) native
    ws_int = wb.create_sheet("Internal (Dealius)")
    int_cols = list(internal_native[0].keys()) if internal_native else ["(no internal rows)"]
    _write_sheet(ws_int, int_cols, internal_native)

    # Sheet 3 — External native
    ws_ext = wb.create_sheet("External")
    ext_cols = list(external_native[0].keys()) if external_native else ["(no external rows)"]
    _write_sheet(ws_ext, ext_cols, external_native)

    # Sheet 4 — Contributed native (lee-and-associates#636)
    contributed_native = [{k: v for k, v in r.items() if k not in _CONTRIBUTED_PRIVATE}
                          for r in contributed_native]
    ws_con = wb.create_sheet("Contributed")
    con_cols = list(contributed_native[0].keys()) if contributed_native else ["(no contributed rows)"]
    _write_sheet(ws_con, con_cols, contributed_native)

    # Windows 218-char path guard (gi-plugins#7). This orchestrator already loads
    # its siblings, so reuse the canonical helper rather than duplicating it:
    # flatten to a CWD basename + cap the filename so a deep/long path can't survive.
    xlsx_path = load_sibling("internal-comps").safe_xlsx_name(xlsx_path)
    wb.save(xlsx_path)
    return xlsx_path


# =====================================================================
# plan: the exact call for every leg (G33: paste these, never derive them)
# =====================================================================

def plan(parsed: dict) -> dict:
    """Validate once and return the three legs' calls:
    internal (read_query SQL), external (the external skill's own plan), and
    contributed (one pull_unified_comps call)."""
    internal = load_sibling("internal-comps")
    external = load_sibling("external-comps")
    v = internal.validate_request(dict(parsed))
    out = {"validated": v["validated"], "missing_required": v["missing_required"],
           "applied_defaults": v["applied_defaults"], "warnings": v["warnings"],
           "internal": None, "external": None, "contributed": None, "error": None}
    if v["missing_required"]:
        out["error"] = "missing required fields: " + "; ".join(v["missing_required"])
        return out
    out["internal"] = {"tool_name": "read_query", **internal.build_sql(v["validated"])}
    out["external"] = external.plan(dict(parsed))
    out["contributed"] = contributed_params(v["validated"])
    # A market one leg refuses must stop all three: the internal validator falls
    # back to RDU on an unknown market, which would hand a Charlotte ask
    # Triangle comps from two legs while the third refused.
    if out["external"].get("error"):
        out["error"] = "external leg refused the ask: " + out["external"]["error"]
        out["internal"] = out["contributed"] = None  # nothing to call on a refused ask
    return out


def _main(argv: list) -> int:
    if len(argv) < 2 or argv[0] != "plan":
        print("usage: python3 helpers.py plan <request.json | '{...}'>", file=sys.stderr)
        return 2
    arg = argv[1]
    try:
        if os.path.exists(arg):
            with open(arg) as fh:
                parsed = json.load(fh)
        else:
            parsed = json.loads(arg)
        if not isinstance(parsed, dict):
            raise ValueError("request must be a JSON object")
    except Exception as e:  # always hand the session a JSON object to read
        print(json.dumps({"error": f"could not read request: {e}"}))
        return 1
    result = plan(parsed)
    print(json.dumps(result, indent=2, default=str))
    return 1 if result["error"] else 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv[1:]))
