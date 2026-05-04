"""
helpers.py — atomic helpers for the internal-comps skill.

Run in the Cowork sandbox. The model orchestrates; helpers are deterministic.
None of these helpers call MCP tools — SQL execution and email sending are
the model's responsibility (the model has MCP access; the sandbox does not).

Design contract:
  - Open-shaped dicts in / dicts out. Helpers tolerate extra keys.
  - Three load-bearing keys on the request: asset_type, transaction_type,
    geography. Everything else is optional and may be absent.
  - Frozen output layout — see SKILL.md "Output" section. Do not parameterize
    beyond what these signatures expose.
"""

import os
from datetime import date
from typing import Optional, Literal

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from openpyxl.formatting.rule import ColorScaleRule
from openpyxl.drawing.image import Image as XLImage

LEE_BRAND_MAROON = "97012D"  # rgb(151, 1, 45) — Lee & Associates Raleigh
LEE_LOGO_FILENAME = "lee_logo.png"  # ships alongside helpers.py

# =====================================================================
# Constants — registries the helpers read from
# =====================================================================

RDU_MSA_CITIES: list[str] = [
    "Raleigh", "Cary", "Morrisville", "Durham", "Apex", "Holly Springs",
    "Wake Forest", "Chapel Hill", "Garner", "Knightdale", "Wendell",
    "Zebulon", "Rolesville", "Fuquay Varina", "Fuquay-Varina", "Clayton",
]

# Named markets the broker might say. All map to the RDU MSA city list for V1.
NAMED_MARKETS: dict[str, list[str]] = {
    "RDU MSA":        RDU_MSA_CITIES,
    "RDU":            RDU_MSA_CITIES,
    "Triangle":       RDU_MSA_CITIES,
    "Raleigh-Durham": RDU_MSA_CITIES,
}

# property_type values exactly as stored in Dealius. Note the misspelling on
# medical office — that is canonical, not a bug.
PROPERTY_TYPE_MAP: dict[str, Optional[list[str]]] = {
    "industrial":     ["Industrial", "Flex Warehouse", "100% Warehouse"],
    "flex":           ["Flex Warehouse"],
    "office":         ["Office"],
    "retail":         ["Retail"],
    "medical_office": ["Medcial Office"],
    "lab":            ["Lab Space"],
    "land":           ["Land"],
}

CANONICAL_COLUMNS_LEASE: list[str] = [
    "comps_id", "comp_name", "street_address", "city", "state", "zip_code",
    "county", "property_type", "space_sf", "square_feet_sold", "building_size",
    "acres",
    "lease_execution", "lease_commencement", "term", "lease_type",
    "free_rent_months", "ti_allowance_per_sf", "asking_rate_per_sf",
    "effective_rate",
    "tenant", "landlord", "lead_broker_s",
    "landlord_rep_agents", "tenant_rep_agents", "link_to_comp_profile",
]

CANONICAL_COLUMNS_SALE: list[str] = [
    "comps_id", "comp_name", "street_address", "city", "state", "zip_code",
    "county", "property_type", "square_feet_sold", "building_size", "acres",
    "property_year_built", "actual_close_date",
    "asking_price", "sale_price", "price_per_sf",
    "asking_cap_rate", "actual_cap_rate", "investment_sale", "off_market_sale",
    "buyer", "buyer_dba", "seller", "seller_dba",
    "buyer_rep_agents", "seller_rep_agents", "link_to_comp_profile",
]

# Display layout for the Comps sheet — (header label, dict key from row).
# Order is frozen and matches Run 1's gold-standard output.
# Lease: space_sf is the primary "Leased SF" column (69% populated). When null,
# format_excel falls back to square_feet_sold (85% populated).
DISPLAY_COLUMNS_LEASE: list[tuple[str, str]] = [
    ("Comp ID",          "comps_id"),
    ("Property Type",    "property_type"),
    ("Property/Comp",    "comp_name"),
    ("Address",          "street_address"),
    ("City",             "city"),
    ("County",           "county"),
    ("Leased SF",        "space_sf"),
    ("Building SF",      "building_size"),
    ("Lease Executed",   "lease_execution"),
    ("Lease Commence",   "lease_commencement"),
    ("Term",             "term"),
    ("Asking $/SF",      "asking_rate_per_sf"),
    ("Effective $/SF",   "effective_rate"),
    ("Lease Type",       "lease_type"),
    ("Free Rent (mo)",   "free_rent_months"),
    ("TI ($/SF)",        "ti_allowance_per_sf"),
    ("Tenant",           "tenant"),
    ("Landlord",         "landlord"),
    ("Landlord Rep",     "landlord_rep_agents"),
    ("Tenant Rep",       "tenant_rep_agents"),
    ("Comp Profile",     "link_to_comp_profile"),
]

# Sale: square_feet_sold is the primary "Building SF" (63% on sale view); falls
# back to building_size (50%). Format_excel handles the coalesce.
DISPLAY_COLUMNS_SALE: list[tuple[str, str]] = [
    ("Comp ID",          "comps_id"),
    ("Property Type",    "property_type"),
    ("Property/Comp",    "comp_name"),
    ("Address",          "street_address"),
    ("City",             "city"),
    ("County",           "county"),
    ("Building SF",      "square_feet_sold"),
    ("Acres",            "acres"),
    ("Year Built",       "property_year_built"),
    ("Asking Price",     "asking_price"),
    ("Sale Price",       "sale_price"),
    ("$/SF",             "price_per_sf"),
    ("Asking Cap %",     "asking_cap_rate"),
    ("Actual Cap %",     "actual_cap_rate"),
    ("Close Date",       "actual_close_date"),
    ("Investment Sale",  "investment_sale"),
    ("Buyer",            "buyer"),
    ("Buyer DBA",        "buyer_dba"),
    ("Seller",           "seller"),
    ("Seller DBA",       "seller_dba"),
    ("Buyer Rep",        "buyer_rep_agents"),
    ("Seller Rep",       "seller_rep_agents"),
    ("Comp Profile",     "link_to_comp_profile"),
]

ASSET_TITLE_MAP: dict[str, str] = {
    "industrial":     "Industrial",
    "flex":           "Flex",
    "office":         "Office",
    "retail":         "Retail",
    "medical_office": "Medical Office",
    "lab":            "Lab",
    "land":           "Land",
}


# =====================================================================
# Validation
# =====================================================================

def validate_request(parsed: dict) -> dict:
    """
    Apply defaults and surface gaps in a parsed broker request.

    Args:
        parsed: dict from the model's parse of the broker paste. Must contain
            'asset_type' and 'transaction_type'. May contain geography,
            size_range, date_window, target_count, min_price, notes, plus any
            extras (preserved unread).

    Returns:
        {
            'validated': dict,           # parsed + defaults; original keys preserved
            'missing_required': list,    # blocking — caller must clarify before SQL
            'applied_defaults': list,    # human-readable; surfaced in email body
            'warnings': list,            # human-readable; surfaced in email body
        }

    Defaults:
        - geography missing → {"named_market": "RDU MSA"}, applied_defaults entry
        - date_window missing → {"lookback_months": 12}, applied_defaults entry
        - target_count missing → 8, applied_defaults entry
        - min_price missing AND transaction_type=="sale" → 500000, applied_defaults entry
        - size_range missing → no default; warning only

    Validation:
        - asset_type unknown → missing_required entry
        - transaction_type not in {"lease", "sale"} → missing_required entry
        - geography references a sub-region we cannot resolve → warning, fall back
          to broader market
    """
    validated = dict(parsed)
    missing_required: list[str] = []
    applied_defaults: list[str] = []
    warnings: list[str] = []

    asset_type = validated.get("asset_type")
    if asset_type not in PROPERTY_TYPE_MAP:
        missing_required.append(
            f"asset_type unknown: {asset_type!r}. Expected one of {list(PROPERTY_TYPE_MAP)}."
        )

    transaction_type = validated.get("transaction_type")
    if transaction_type not in ("lease", "sale"):
        missing_required.append(
            f"transaction_type must be 'lease' or 'sale'. Got {transaction_type!r}."
        )

    geo = validated.get("geography")
    if not geo:
        validated["geography"] = {"named_market": "RDU MSA"}
        applied_defaults.append("geography: RDU MSA (no geography specified)")
    elif "named_market" in geo:
        nm = geo["named_market"]
        if nm not in NAMED_MARKETS:
            warnings.append(
                f"Geography {nm!r} did not resolve to a registered market — falling back to RDU MSA."
            )
            validated["geography"] = {"named_market": "RDU MSA"}
    elif "anchor" in geo:
        warnings.append(
            "Anchor + radius geography is not yet supported (no lat/long in export). Falling back to RDU MSA city list."
        )
        validated["geography"] = {"named_market": "RDU MSA"}

    if not validated.get("date_window"):
        validated["date_window"] = {"lookback_months": 12}
        applied_defaults.append("date window: trailing 12 months (no date window specified)")

    if not validated.get("target_count"):
        validated["target_count"] = 8
        applied_defaults.append("target count: 8")

    if transaction_type == "sale" and not validated.get("min_price"):
        validated["min_price"] = 500000
        applied_defaults.append("min price: $500K (sale junk filter)")

    if not validated.get("size_range"):
        warnings.append("Size range not specified — query will return all sizes.")

    if validated.get("min_acres") and transaction_type == "lease":
        warnings.append(
            "Acreage filter on lease comps: only ~16% of lease records have acres populated, "
            "so this filter will drop a lot of comps that may actually qualify but lack the data."
        )

    return {
        "validated": validated,
        "missing_required": missing_required,
        "applied_defaults": applied_defaults,
        "warnings": warnings,
    }


# =====================================================================
# SQL composition
# =====================================================================

def _sql_quote(s) -> str:
    return "'" + str(s).replace("'", "''") + "'"


def _date_cutoff(date_window: dict) -> Optional[str]:
    """Return YYYYMMDD string for the lower bound, or None if no window applies."""
    if not date_window:
        return None
    if "lookback_months" in date_window:
        from datetime import timedelta
        cutoff = date.today() - timedelta(days=int(date_window["lookback_months"] * 30))
        return cutoff.strftime("%Y%m%d")
    if "from" in date_window:
        return date_window["from"].replace("-", "")
    return None


def _resolve_cities(geography: dict) -> list[str]:
    """Geography dict → concrete city list. Falls back to RDU MSA on unknowns."""
    if not geography:
        return list(RDU_MSA_CITIES)
    if "cities" in geography:
        return list(geography["cities"])
    if "named_market" in geography:
        nm = geography["named_market"]
        if nm in NAMED_MARKETS:
            return list(NAMED_MARKETS[nm])
        return list(RDU_MSA_CITIES)
    return list(RDU_MSA_CITIES)


def _date_as_yyyymmdd(col: str) -> str:
    """Return a SQL fragment that converts an MM/DD/YYYY text column to YYYYMMDD."""
    return f"(substr({col},7,4) || substr({col},1,2) || substr({col},4,2))"


def build_sql(validated: dict) -> dict:
    """
    Build a parameterized SQL string against lease_comps_safe / sale_comps_safe.

    Helper does NOT execute — Cowork sandbox has no MCP access. Caller passes
    the returned 'sql' to the MCP read_query tool.

    Args:
        validated: output of validate_request()['validated'].

    Returns:
        {'sql': str}    # ready to pass to read_query

    SELECTs only CANONICAL_COLUMNS. Filters by property_type taxonomy, city list,
    date window (MM/DD/YYYY → YYYYMMDD conversion in SQL), size range, and
    min_price (sale only).

    No auto-expansion. If the result count is below target_count, draft_email
    asks the broker which dimension to widen — the broker drives, not the model.
    """
    asset_type = validated.get("asset_type")
    transaction_type = validated.get("transaction_type")

    if transaction_type not in ("lease", "sale"):
        raise ValueError(f"transaction_type must be 'lease' or 'sale'. Got {transaction_type!r}.")

    types = PROPERTY_TYPE_MAP.get(asset_type)
    if not types:
        raise ValueError(f"asset_type {asset_type!r} has no taxonomy mapping.")

    is_sale = transaction_type == "sale"
    view = "sale_comps_safe" if is_sale else "lease_comps_safe"
    date_col = "actual_close_date" if is_sale else "lease_execution"
    cols = CANONICAL_COLUMNS_SALE if is_sale else CANONICAL_COLUMNS_LEASE
    # Sale: building SF is in square_feet_sold (denser), falls back to building_size.
    # Lease: leased SF is in space_sf (denser for leases), falls back to square_feet_sold.
    size_expr = (
        "CAST(COALESCE(square_feet_sold, building_size) AS INTEGER)"
        if is_sale
        else "CAST(COALESCE(space_sf, square_feet_sold) AS INTEGER)"
    )

    size = validated.get("size_range")
    date_window = validated.get("date_window") or {"lookback_months": 12}
    cutoff = _date_cutoff(date_window)
    cities = _resolve_cities(validated.get("geography", {}))

    where: list[str] = []
    where.append(f"property_type IN ({', '.join(_sql_quote(t) for t in types)})")
    if cities:
        where.append(f"city IN ({', '.join(_sql_quote(c) for c in cities)})")
    if size:
        where.append(f"{size_expr} BETWEEN {int(size['min_sf'])} AND {int(size['max_sf'])}")
    if cutoff:
        where.append(f"{_date_as_yyyymmdd(date_col)} >= '{cutoff}'")
    if is_sale and validated.get("min_price"):
        where.append(f"CAST(sale_price AS INTEGER) >= {int(validated['min_price'])}")
    if validated.get("min_acres"):
        where.append(f"CAST(acres AS REAL) >= {float(validated['min_acres'])}")

    sql = (
        f"SELECT {', '.join(cols)}\n"
        f"FROM {view}\n"
        f"WHERE {' AND '.join(where)}\n"
        f"ORDER BY {_date_as_yyyymmdd(date_col)} DESC;"
    )

    return {"sql": sql}


# =====================================================================
# Excel
# =====================================================================

def _asset_title(asset_type: str) -> str:
    return ASSET_TITLE_MAP.get(asset_type, asset_type.replace("_", " ").title())


def _geography_label(geography: dict) -> str:
    if not geography:
        return ""
    if "named_market" in geography:
        return geography["named_market"]
    if "anchor" in geography:
        return f"{geography['anchor']} + {geography.get('radius_mi', '?')}mi"
    if "cities" in geography:
        cities = geography["cities"]
        if len(cities) <= 3:
            return ", ".join(cities)
        return f"{cities[0]} +{len(cities) - 1} more"
    return ""


def _to_number(x):
    if x is None or x == "":
        return None
    try:
        return float(x)
    except (TypeError, ValueError):
        return x


def _to_int(x):
    if x is None or x == "":
        return None
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return x


def _describe_size_range(size_range: Optional[dict]) -> str:
    if not size_range:
        return "Not specified — all sizes returned"
    return f"{size_range.get('min_sf', 0):,} – {size_range.get('max_sf', 0):,} sq ft (leased SF; falls back to building SF if leased SF null)"


def _describe_date_window(date_window: Optional[dict]) -> str:
    if not date_window:
        return "Not specified"
    if "lookback_months" in date_window:
        return f"Trailing {date_window['lookback_months']} months from pull date"
    if "from" in date_window or "to" in date_window:
        return f"{date_window.get('from','?')} to {date_window.get('to','?')}"
    return "Not specified"


def _describe_property_types(asset_type: str) -> str:
    types = PROPERTY_TYPE_MAP.get(asset_type)
    if not types:
        return f"{asset_type} (no taxonomy mapping)"
    return ", ".join(types)


def _compute_stats(rows: list[dict], is_sale: bool = False) -> dict:
    """Compute summary stats from row dicts. Tolerates string-typed numerics."""
    if not rows:
        return {"count": 0}

    def _nums(key):
        out = []
        for r in rows:
            v = _to_number(r.get(key))
            if isinstance(v, (int, float)):
                out.append(v)
        return out

    def _median(xs):
        if not xs:
            return None
        s = sorted(xs)
        n = len(s)
        return s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2

    if is_sale:
        sale = _nums("sale_price")
        ppsf = _nums("price_per_sf")
        # Building SF: coalesce square_feet_sold with building_size to match display.
        bsf = []
        for r in rows:
            v = _to_number(r.get("square_feet_sold"))
            if not isinstance(v, (int, float)):
                v = _to_number(r.get("building_size"))
            if isinstance(v, (int, float)):
                bsf.append(v)
        return {
            "count":                len(rows),
            "avg_sale_price":       sum(sale) / len(sale) if sale else None,
            "median_sale_price":    _median(sale),
            "min_sale_price":       min(sale) if sale else None,
            "max_sale_price":       max(sale) if sale else None,
            "avg_price_per_sf":     sum(ppsf) / len(ppsf) if ppsf else None,
            "median_price_per_sf":  _median(ppsf),
            "avg_building_sf":      sum(bsf) / len(bsf) if bsf else None,
            "total_sale_volume":    sum(sale) if sale else None,
        }

    eff = _nums("effective_rate")
    ask = _nums("asking_rate_per_sf")
    # Leased SF: coalesce space_sf with square_feet_sold to match display.
    sf = []
    for r in rows:
        v = _to_number(r.get("space_sf"))
        if not isinstance(v, (int, float)):
            v = _to_number(r.get("square_feet_sold"))
        if isinstance(v, (int, float)):
            sf.append(v)
    return {
        "count": len(rows),
        "avg_effective_rate":    sum(eff) / len(eff) if eff else None,
        "median_effective_rate": _median(eff),
        "min_effective_rate":    min(eff) if eff else None,
        "max_effective_rate":    max(eff) if eff else None,
        "avg_asking_rate":       sum(ask) / len(ask) if ask else None,
        "avg_leased_sf":         sum(sf) / len(sf) if sf else None,
        "median_leased_sf":      _median(sf),
    }


def format_excel(
    rows: list[dict],
    validated: dict,
    output_path: str,
    applied_defaults: list,
    warnings: list,
    last_sync: Optional[str] = None,
) -> dict:
    """
    Write the canonical 3-sheet workbook. Layout is frozen (see SKILL.md "Output").

    Args:
        rows: result rows from MCP read_query. Each row is a dict keyed by
            CANONICAL_COLUMNS (subset is fine — missing keys render blank).
        validated: validate_request output.
        output_path: absolute path to write the .xlsx.
        applied_defaults, warnings: surfaced on Methodology.
        last_sync: ISO timestamp of last mirror refresh; on Methodology.

    Returns:
        {'path', 'summary_stats', 'sheet_name', 'row_count'}.

    Sheet naming: "{Asset Title} {Geography} Comps".
    Empty result still produces a workbook with headers and an explanatory
    Methodology sheet.
    """
    asset_title = _asset_title(validated.get("asset_type", ""))
    geo_label = _geography_label(validated.get("geography", {}))
    is_sale = validated.get("transaction_type") == "sale"
    txn_token = " Sale" if is_sale else ""
    sheet_name = f"{asset_title}{txn_token} {geo_label} Comps".strip().replace("  ", " ")
    display_columns = DISPLAY_COLUMNS_SALE if is_sale else DISPLAY_COLUMNS_LEASE

    wb = Workbook()
    default_font = Font(name="Calibri", size=11)
    header_fill = PatternFill("solid", start_color=LEE_BRAND_MAROON)
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    center = Alignment(horizontal="center", vertical="center", wrap_text=True)
    left = Alignment(horizontal="left", vertical="center", wrap_text=True)
    thin = Side(border_style="thin", color="BFBFBF")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)

    # Locate the bundled logo (alongside helpers.py).
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), LEE_LOGO_FILENAME)
    logo_available = os.path.exists(logo_path)

    # ---------- Sheet 1: Comps ----------
    ws = wb.active
    ws.title = sheet_name[:31]  # Excel sheet name limit

    # Logo + title band at top, then header row, then data.
    header_row_idx = 4 if logo_available else 1

    if logo_available:
        ws.row_dimensions[1].height = 56
        img = XLImage(logo_path)
        ws.add_image(img, "A1")
        title_kind = "Sale Comps" if is_sale else "Comps"
        view_label = "sale_comps_safe" if is_sale else "lease_comps_safe"
        ws.cell(row=2, column=2, value=f"{asset_title} {title_kind} — {geo_label}").font = Font(
            name="Calibri", size=14, bold=True, color=LEE_BRAND_MAROON
        )
        ws.cell(row=3, column=2, value=f"Pulled {date.today().isoformat()} · Internal {view_label}").font = Font(
            name="Calibri", size=10, italic=True, color="555555"
        )

    headers = [label for label, _ in display_columns]
    keys = [key for _, key in display_columns]

    for col_idx, h in enumerate(headers, start=1):
        c = ws.cell(row=header_row_idx, column=col_idx, value=h)
        c.fill = header_fill
        c.font = header_font
        c.alignment = center
        c.border = border

    if is_sale:
        # Sale layout: cols 1..23 above
        # 7 Building SF, 8 Acres, 9 Year Built, 10 Asking Price, 11 Sale Price,
        # 12 $/SF, 13 Asking Cap %, 14 Actual Cap %, 15 Close Date,
        # 16 Investment Sale, 17 Buyer ... 23 Comp Profile
        left_align_cols = {3, 4, 5, 6, 16, 17, 18, 19, 20, 21, 22, 23}
        int_cols = {7, 9}                          # Building SF, Year Built
        acres_cols = {8}                           # Acres (decimal)
        large_money_cols = {10, 11}                # Asking Price, Sale Price
        money_per_sf_cols = {12}                   # $/SF
        pct_cols = {13, 14}                        # Asking Cap %, Actual Cap %
        color_scale_col = "L"                      # $/SF
    else:
        left_align_cols = {3, 4, 5, 6, 15, 19, 20, 21, 22, 23}
        int_cols = {7, 8, 16}                      # SF, free rent months
        acres_cols = set()
        large_money_cols = set()
        money_per_sf_cols = {12, 13, 14, 17}       # asking, base, effective, TI
        pct_cols = {18}                            # avg escalation
        color_scale_col = "N"                      # Effective $/SF

    data_start = header_row_idx + 1
    for row_offset, row in enumerate(rows):
        excel_row = data_start + row_offset
        for col_idx, key in enumerate(keys, start=1):
            raw = row.get(key)
            # Coalesce primary→fallback for the leased-SF / building-SF column.
            if key == "space_sf" and (raw is None or raw == ""):
                raw = row.get("square_feet_sold")
            if is_sale and key == "square_feet_sold" and (raw is None or raw == ""):
                raw = row.get("building_size")
            if col_idx in int_cols:
                val = _to_int(raw)
            elif col_idx in (money_per_sf_cols | large_money_cols | pct_cols | acres_cols):
                val = _to_number(raw)
            else:
                val = raw
            c = ws.cell(row=excel_row, column=col_idx, value=val)
            c.font = default_font
            c.border = border
            c.alignment = left if col_idx in left_align_cols else center

    last_row = header_row_idx + len(rows)

    if rows:
        for r in range(data_start, last_row + 1):
            for col_idx in int_cols:
                ws.cell(row=r, column=col_idx).number_format = "#,##0"
            for col_idx in acres_cols:
                ws.cell(row=r, column=col_idx).number_format = "0.00"
            for col_idx in large_money_cols:
                ws.cell(row=r, column=col_idx).number_format = "$#,##0"
            for col_idx in money_per_sf_cols:
                ws.cell(row=r, column=col_idx).number_format = "$#,##0.00"
            for col_idx in pct_cols:
                ws.cell(row=r, column=col_idx).number_format = '0.0"%"'

    if is_sale:
        widths = {
            1: 9, 2: 16, 3: 30, 4: 30, 5: 14, 6: 18, 7: 12, 8: 9, 9: 11,
            10: 14, 11: 14, 12: 11, 13: 12, 14: 12, 15: 12, 16: 13,
            17: 32, 18: 32, 19: 32, 20: 32, 21: 28, 22: 28, 23: 42,
        }
    else:
        widths = {
            1: 9, 2: 16, 3: 30, 4: 30, 5: 14, 6: 18, 7: 11, 8: 12, 9: 13, 10: 13,
            11: 12, 12: 11, 13: 11, 14: 13, 15: 18, 16: 11, 17: 11, 18: 13,
            19: 32, 20: 32, 21: 28, 22: 28, 23: 42,
        }
    for col, w in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = w

    ws.row_dimensions[header_row_idx].height = 32
    ws.freeze_panes = ws.cell(row=data_start, column=1).coordinate
    ws.auto_filter.ref = f"A{header_row_idx}:{get_column_letter(len(headers))}{max(last_row, header_row_idx)}"

    if rows:
        ws.conditional_formatting.add(
            f"{color_scale_col}{data_start}:{color_scale_col}{last_row}",
            ColorScaleRule(
                start_type="min", start_color="F8696B",
                mid_type="percentile", mid_value=50, mid_color="FFEB84",
                end_type="max", end_color="63BE7B",
            ),
        )

    # ---------- Sheet 2: Summary ----------
    ws2 = wb.create_sheet("Summary")
    ws2.column_dimensions["A"].width = 28
    ws2.column_dimensions["B"].width = 16

    ws2.cell(row=1, column=1, value="Summary").font = Font(
        name="Calibri", size=14, bold=True, color=LEE_BRAND_MAROON
    )

    summary_stats = _compute_stats(rows, is_sale=is_sale)
    if is_sale:
        stats_rows = [
            ("Comp count",         summary_stats.get("count", 0),               "#,##0"),
            ("Avg Sale Price",     summary_stats.get("avg_sale_price"),         "$#,##0"),
            ("Median Sale Price",  summary_stats.get("median_sale_price"),      "$#,##0"),
            ("Min Sale Price",     summary_stats.get("min_sale_price"),         "$#,##0"),
            ("Max Sale Price",     summary_stats.get("max_sale_price"),         "$#,##0"),
            ("Avg $/SF",           summary_stats.get("avg_price_per_sf"),       "$#,##0.00"),
            ("Median $/SF",        summary_stats.get("median_price_per_sf"),    "$#,##0.00"),
            ("Avg Building SF",    summary_stats.get("avg_building_sf"),        "#,##0"),
            ("Total Sale Volume",  summary_stats.get("total_sale_volume"),      "$#,##0"),
        ]
    else:
        stats_rows = [
            ("Comp count",            summary_stats.get("count", 0),                "#,##0"),
            ("Avg Effective $/SF",    summary_stats.get("avg_effective_rate"),      "$#,##0.00"),
            ("Median Effective $/SF", summary_stats.get("median_effective_rate"),   "$#,##0.00"),
            ("Min Effective $/SF",    summary_stats.get("min_effective_rate"),      "$#,##0.00"),
            ("Max Effective $/SF",    summary_stats.get("max_effective_rate"),      "$#,##0.00"),
            ("Avg Asking $/SF",       summary_stats.get("avg_asking_rate"),         "$#,##0.00"),
            ("Avg Leased SF",         summary_stats.get("avg_leased_sf"),           "#,##0"),
            ("Median Leased SF",      summary_stats.get("median_leased_sf"),        "#,##0"),
        ]
    for i, (label, value, fmt) in enumerate(stats_rows, start=3):
        a = ws2.cell(row=i, column=1, value=label)
        a.font = Font(bold=True)
        b = ws2.cell(row=i, column=2, value=value)
        b.number_format = fmt

    # ---------- Sheet 3: Methodology ----------
    ws3 = wb.create_sheet("Methodology")
    ws3.column_dimensions["A"].width = 26
    ws3.column_dimensions["B"].width = 90

    ws3.cell(row=1, column=1, value="Methodology").font = Font(
        name="Calibri", size=14, bold=True, color=LEE_BRAND_MAROON
    )
    method_start = 3

    pull_date = date.today().isoformat()
    if is_sale:
        source_text = "Internal sale_comps_safe (Dealius mirror, Lee & Associates Raleigh). Confidential and NDA rows filtered server-side."
        rate_convention = "Sale Price is the closed transaction amount. $/SF is sale price divided by building square footage. Asking Cap and Actual Cap are reported by the listing where disclosed; cap rates are sparse in the source."
        caveat = "Cap rates are populated for ~10% of sale comps; absence does not imply 0%. Buyer DBA and seller DBA may be blank for owner-occupied or single-purpose entities. Confirm against the comp profile link if material."
    else:
        source_text = "Internal lease_comps_safe (Dealius mirror, Lee & Associates Raleigh). Confidential and NDA rows filtered server-side."
        rate_convention = "Effective $/SF includes effects of free rent, TI, and escalations as recorded in the source. Asking $/SF is initial quoted rate. Both annualized."
        caveat = "TI and free-rent values that appear as 0 may be unpopulated in the source rather than truly zero. Confirm against the comp profile link if material."

    methodology_rows = [
        ("Pull date", pull_date),
        ("Source", source_text),
        ("Asset type", _asset_title(validated.get("asset_type", ""))),
        ("Property types in scope", _describe_property_types(validated.get("asset_type", ""))),
        ("Transaction type", validated.get("transaction_type", "")),
        ("Geography", geo_label or "Not specified"),
        ("Size range", _describe_size_range(validated.get("size_range"))),
        ("Min acres", f"{float(validated['min_acres']):g} acres" if validated.get("min_acres") else "Not specified"),
        ("Date window", _describe_date_window(validated.get("date_window"))),
        ("Target count", str(validated.get("target_count", ""))),
        ("Rate convention", rate_convention),
        ("Applied defaults", "; ".join(applied_defaults) if applied_defaults else "None"),
        ("Warnings", "; ".join(warnings) if warnings else "None"),
        ("Mirror last sync", last_sync or "Not provided"),
        ("Caveat", caveat),
    ]
    if validated.get("notes"):
        methodology_rows.insert(-1, ("Broker notes", validated["notes"]))
    if not rows:
        methodology_rows.insert(2, ("Result", "0 comps matched the criteria above. Reply if you want me to widen size, date, or geography."))

    for offset, (k, v) in enumerate(methodology_rows):
        r = method_start + offset
        a = ws3.cell(row=r, column=1, value=k)
        a.font = Font(bold=True)
        a.alignment = Alignment(vertical="top")
        b = ws3.cell(row=r, column=2, value=v)
        b.alignment = Alignment(wrap_text=True, vertical="top")
        ws3.row_dimensions[r].height = 30

    wb.save(output_path)

    return {
        "path": output_path,
        "summary_stats": summary_stats,
        "sheet_name": sheet_name,
        "row_count": len(rows),
    }


# =====================================================================
# Email draft
# =====================================================================

def draft_email(
    rows: list[dict],
    validated: dict,
    xlsx_path: Optional[str],
    applied_defaults: list,
    warnings: list,
    confidential_reference_unfound: bool = False,
) -> dict:
    """
    Compose the broker reply. Helper does not send — caller uses the connected
    email MCP tool with subject + body + recipient.

    Args:
        rows: query results (or [] for ios/empty paths).
        validated: validate_request output.
        xlsx_path: path to the Excel deliverable, or None for the IOS path
            where no workbook was generated.
        applied_defaults, warnings: surfaced in body.
        confidential_reference_unfound: set True if the broker referenced a
            specific comp by ID/address that didn't appear in results — the
            body inserts the canonical confidentiality response verbatim.

    Returns:
        {'subject': str, 'body': str}

    Special branches:
        - len(rows) == 0: body says no comps matched and asks which dimension
          to widen (size, date, geography). Excel is still attached.
        - 0 < len(rows) < target_count: body surfaces the shortfall and asks
          which dimension to widen.

    The body always reads validated['notes'] back if present, so any broker
    preferences the model parsed but didn't slot get acknowledged.
    """
    asset_title = _asset_title(validated.get("asset_type", ""))
    geo_label = _geography_label(validated.get("geography", {}))
    transaction_type = validated.get("transaction_type", "lease")
    is_sale = transaction_type == "sale"
    count = len(rows)

    stats = _compute_stats(rows, is_sale=is_sale)

    target = validated.get("target_count", 8)

    parts: list[str] = []
    parts.append(f"Hey,\n\nAttached: {count} internal {asset_title.lower()} {transaction_type} comp{'s' if count != 1 else ''}"
                 f" for {geo_label}." if count else
                 f"Hey,\n\nNo internal comps matched the criteria — Excel attached with what was queried. Want me to widen size, date, or geography?")

    if count:
        rate_bits = []
        if is_sale:
            if stats.get("avg_price_per_sf") is not None:
                rate_bits.append(f"avg ${stats['avg_price_per_sf']:.2f}/SF")
            if stats.get("median_price_per_sf") is not None:
                rate_bits.append(f"median ${stats['median_price_per_sf']:.2f}/SF")
            if stats.get("avg_sale_price") is not None:
                rate_bits.append(f"avg sale ${stats['avg_sale_price']:,.0f}")
            if stats.get("total_sale_volume") is not None:
                rate_bits.append(f"total volume ${stats['total_sale_volume']:,.0f}")
        else:
            if stats.get("avg_effective_rate") is not None:
                rate_bits.append(f"avg ${stats['avg_effective_rate']:.2f}/SF effective")
            if stats.get("median_effective_rate") is not None:
                rate_bits.append(f"median ${stats['median_effective_rate']:.2f}")
            if stats.get("min_effective_rate") is not None and stats.get("max_effective_rate") is not None:
                rate_bits.append(f"range ${stats['min_effective_rate']:.2f}–${stats['max_effective_rate']:.2f}")
        if rate_bits:
            parts.append("Quick stats: " + "; ".join(rate_bits) + ".")

    if applied_defaults:
        parts.append("Defaults I applied (push back if any are off):\n  - " + "\n  - ".join(applied_defaults))

    if warnings:
        parts.append("Heads up:\n  - " + "\n  - ".join(warnings))

    if count and count < target:
        parts.append(
            f"Got {count} of the {target} you asked for. Want me to widen size, date, or geography? "
            "Reply with what you want me to expand and I'll rerun."
        )

    if confidential_reference_unfound:
        parts.append("On the specific comp you referenced: that comp is confidential and not retrievable through this channel.")

    if validated.get("notes"):
        parts.append(f"Noted: {validated['notes']}")

    parts.append("Let me know if you want me to widen, narrow, or rerun differently.\n\n— Will (via the internal-comps tool)")

    subject_count = f"{count} result{'s' if count != 1 else ''}" if count else "no internal matches"
    subject_kind = "sale comps" if is_sale else "comps"
    subject = f"Internal {asset_title} {subject_kind} — {geo_label}, {subject_count}".replace("  ", " ").strip(" —")

    return {"subject": subject, "body": "\n\n".join(parts)}


# =====================================================================
# Feedback
# =====================================================================

def format_feedback(
    rating: int,
    what_worked: str,
    what_didnt: str,
    query_text: str,
    xlsx_path: Optional[str] = None,
) -> dict:
    """
    Format broker feedback as a structured payload. Helper does not send —
    caller routes via connected email MCP or writes the fallback file.

    Args:
        rating: 1-5.
        what_worked, what_didnt: short free-text answers.
        query_text: the broker's original paste.
        xlsx_path: path to the deliverable, if produced. Used for context in
            the email body and to locate the fallback directory.

    Returns:
        {
            'recipient': 'david@groundedintelligence.io',
            'subject': str,
            'body': str,                  # plaintext for email send
            'fallback_filename': str,     # 'feedback-{YYYY-MM-DD}.md'
            'fallback_content': str,      # markdown for file write
            'fallback_dir': str,          # dirname(xlsx_path) or CWD
        }

    Caller logic:
        1. Try Gmail MCP send (subject, body, recipient).
        2. Else try Outlook MCP send.
        3. Else write fallback_content to {fallback_dir}/{fallback_filename}.
    """
    today = date.today().isoformat()
    subject = f"internal-comps skill feedback — {today}"

    body_lines = [
        f"Skill: internal-comps",
        f"Date: {today}",
        f"Rating: {rating}/5",
        "",
        f"Original query:",
        query_text or "(not provided)",
        "",
        f"What worked:",
        what_worked or "(blank)",
        "",
        f"What didn't:",
        what_didnt or "(blank)",
    ]
    if xlsx_path:
        body_lines.extend(["", f"Deliverable: {xlsx_path}"])
    body = "\n".join(body_lines)

    fallback_md_lines = [
        f"# internal-comps feedback — {today}",
        "",
        f"- **Rating:** {rating}/5",
        f"- **Deliverable:** {xlsx_path or 'n/a'}",
        "",
        "## Original query",
        "",
        f"> {query_text}" if query_text else "(not provided)",
        "",
        "## What worked",
        "",
        what_worked or "(blank)",
        "",
        "## What didn't",
        "",
        what_didnt or "(blank)",
    ]
    fallback_content = "\n".join(fallback_md_lines)

    fallback_filename = f"feedback-{today}.md"
    fallback_dir = os.path.dirname(xlsx_path) if xlsx_path else os.getcwd()

    return {
        "recipient": "david@groundedintelligence.io",
        "subject": subject,
        "body": body,
        "fallback_filename": fallback_filename,
        "fallback_content": fallback_content,
        "fallback_dir": fallback_dir,
    }
