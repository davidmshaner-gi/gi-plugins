"""
helpers.py — atomic helpers for the add-comps skill.

Run in the Cowork sandbox. The model orchestrates; helpers are deterministic.
None of these helpers call MCP tools — MCP invocation (the `lee_comps_add_write`
write) is the model's responsibility (the model has MCP access; the sandbox does
not).

What this module does (B1-B3):
  - validate_row(row): flag (never drop) rows missing minimum keys.
  - detect_transaction_type(headers): lease vs. sale from a header set.
  - apply_alias_map(raw_row, txn_type): fold contributor headers into the
    canonical AddCompRow keys, coerce numerics, preserve unmapped columns into
    raw_fields_json.
  - parse_email(html): the email adapter — pull comp tables out of a forwarded
    email, attach the contributing source, normalize + validate each row, and
    skip non-comp decoy tables (signatures, confidentiality notices).

Canonical schema: the keys written below MUST match the MCP write tool's
AddCompRow exactly. Do not rename them.

HTML parsing uses the stdlib `html.parser` (no third-party dependency) so the
skill stays light in the Cowork sandbox.

Design contract:
  - Open-shaped dicts in / dicts out. Helpers tolerate extra keys.
  - Numeric coercion is best-effort: a value that won't cast is left as-is
    (the contributed data is human-typed and messy; we never raise on a cell).
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Canonical AddCompRow keys (must match the MCP write tool exactly).
# ---------------------------------------------------------------------------
CANONICAL_KEYS = [
    "transaction_type", "txn_subtype", "original_source",
    "property_address", "property_city", "property_state", "property_zip",
    "property_type", "building_class", "building_sf", "year_built",
    "submarket", "market",
    "tenant_name", "landlord", "leased_sf", "pct_of_building",
    "lease_start", "lease_term_months", "lease_expiration",
    "base_rent", "rent_type", "escalations", "free_rent_months",
    "ti_concessions",
    "sale_price", "sale_price_per_sf", "sale_date", "asking_price",
    "cap_rate", "noi", "percent_leased", "buyer", "seller",
    "data_confidence", "note", "flagged", "flag_reason", "raw_fields_json",
]


# ---------------------------------------------------------------------------
# Alias maps — contributor header -> canonical key.
# Keys are matched case-insensitively against the stripped header text.
# ---------------------------------------------------------------------------
LEASE_ALIASES: Dict[str, str] = {
    "type of property": "property_type",
    "property type": "property_type",
    "class": "building_class",
    "tenant": "tenant_name",
    "landlord": "landlord",
    "sign date": "lease_start",
    "lease start": "lease_start",
    "sf": "leased_sf",
    "size leased sf": "leased_sf",
    "leased sf": "leased_sf",
    "building size sf": "building_sf",
    "bldg sf": "building_sf",
    "transaction type": "txn_subtype",
    "term (months)": "lease_term_months",
    "term": "lease_term_months",
    "year one base rent nnn": "base_rent",
    "rate (nnn)": "base_rent",
    "rate": "base_rent",
    "base rent": "base_rent",
    "escalations": "escalations",
    "free rent (months)": "free_rent_months",
    "free rent": "free_rent_months",
    "ti / sf; concessions": "ti_concessions",
    "ti/sf; concessions": "ti_concessions",
    "concessions": "ti_concessions",
    "address (park)": "property_address",
    "address": "property_address",
    "city": "property_city",
    "submarket": "submarket",
}

SALE_ALIASES: Dict[str, str] = {
    "type of property": "property_type",
    "property type": "property_type",
    "class": "building_class",
    "address (park)": "property_address",
    "address": "property_address",
    "city": "property_city",
    "submarket": "submarket",
    "sale price": "sale_price",
    "$/sf": "sale_price_per_sf",
    "price/sf": "sale_price_per_sf",
    "close date": "sale_date",
    "sale date": "sale_date",
    "cap rate": "cap_rate",
    "cap": "cap_rate",
    "noi": "noi",
    "buyer": "buyer",
    "purchaser": "buyer",
    "seller": "seller",
    "grantor": "seller",
    "% leased": "percent_leased",
    "occupancy": "percent_leased",
}

# Canonical keys that should be coerced to int / float after the $,% strip.
INT_KEYS = {"building_sf", "leased_sf", "lease_term_months", "sale_price",
            "asking_price", "noi", "year_built"}
FLOAT_KEYS = {"base_rent", "free_rent_months", "sale_price_per_sf",
              "cap_rate", "pct_of_building", "percent_leased"}

# Lease / sale detection vocab (normalized header substrings).
_LEASE_SIGNALS = {"sign date", "term", "base rent", "tenant", "rate"}
_SALE_SIGNALS = {"sale date", "sale price", "buyer", "seller", "cap", "close date"}


# ---------------------------------------------------------------------------
# Numeric coercion
# ---------------------------------------------------------------------------
def _coerce_number(value: Any, want: str) -> Any:
    """Strip $ , % and cast to int/float. Leave un-castable values untouched."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value) if want == "int" else float(value)
    s = str(value).strip()
    if s == "":
        return value
    cleaned = s.replace("$", "").replace(",", "").replace("%", "").strip()
    try:
        if want == "int":
            return int(round(float(cleaned)))
        return float(cleaned)
    except (ValueError, TypeError):
        return value


# ---------------------------------------------------------------------------
# B2 — detection + alias folding
# ---------------------------------------------------------------------------
def detect_transaction_type(headers: List[str]) -> str:
    """Return 'lease' or 'sale' from a header set.

    Sale signals (Sale Date / Sale Price / Buyer / Seller / Cap) take
    precedence when present, since a sale comp set is the rarer, more
    distinctive shape. Otherwise default to lease.
    """
    norm = {str(h).strip().lower() for h in headers if h is not None}

    def _hit(signals):
        return sum(1 for sig in signals if any(sig in h for h in norm))

    sale_hits = _hit(_SALE_SIGNALS)
    lease_hits = _hit(_LEASE_SIGNALS)
    if sale_hits >= 2 and sale_hits >= lease_hits:
        return "sale"
    return "lease"


def apply_alias_map(raw_row: Dict[str, Any], txn_type: str) -> Dict[str, Any]:
    """Fold contributor headers into canonical keys + coerce numerics.

    Unmapped columns are preserved verbatim into raw_fields_json (a JSON string
    of the ORIGINAL row, so nothing typed by the contributor is ever lost).
    """
    aliases = SALE_ALIASES if txn_type == "sale" else LEASE_ALIASES
    out: Dict[str, Any] = {"transaction_type": txn_type}

    for header, value in raw_row.items():
        canonical = aliases.get(str(header).strip().lower())
        if canonical is None:
            continue  # unmapped — preserved via raw_fields_json below
        if canonical in INT_KEYS:
            out[canonical] = _coerce_number(value, "int")
        elif canonical in FLOAT_KEYS:
            out[canonical] = _coerce_number(value, "float")
        elif canonical == "txn_subtype":
            out[canonical] = value  # verbatim Transaction Type value
        else:
            out[canonical] = value

    # Preserve the full original row (including mapped cols) for traceability.
    out["raw_fields_json"] = json.dumps(raw_row, default=str)
    return out


# ---------------------------------------------------------------------------
# B1 — validation (flag, never drop)
# ---------------------------------------------------------------------------
def _has(row: Dict[str, Any], key: str) -> bool:
    v = row.get(key)
    if v is None:
        return False
    if isinstance(v, str) and v.strip() == "":
        return False
    return True


def validate_row(row: Dict[str, Any]) -> Dict[str, Any]:
    """Set flagged=1 + flag_reason when minimum keys are missing; else flagged=0.

    Minimum keys:
      lease — property_address + a size (leased_sf OR building_sf) + base_rent
              + a date (lease_start)
      sale  — property_address + sale_price + sale_date

    Mutates and returns the same dict. Never drops a row.
    """
    txn = row.get("transaction_type")
    missing: List[str] = []

    if txn == "sale":
        if not _has(row, "property_address"):
            missing.append("property_address")
        if not _has(row, "sale_price"):
            missing.append("sale_price")
        if not _has(row, "sale_date"):
            missing.append("sale_date")
    else:  # lease (default)
        if not _has(row, "property_address"):
            missing.append("property_address")
        if not (_has(row, "leased_sf") or _has(row, "building_sf")):
            missing.append("size (leased_sf or building_sf)")
        if not _has(row, "base_rent"):
            missing.append("base_rent")
        if not _has(row, "lease_start"):
            missing.append("date (lease_start)")

    if missing:
        row["flagged"] = 1
        row["flag_reason"] = "missing required fields: " + ", ".join(missing)
    else:
        row["flagged"] = 0
        row["flag_reason"] = ""
    return row


# ---------------------------------------------------------------------------
# B3 — email adapter
# ---------------------------------------------------------------------------
class _EmailParser(HTMLParser):
    """Walk an email body, collecting tables (as lists of cell-rows) plus the
    bold text that immediately precedes each table.

    Output: self.tables is a list of (preceding_bold_text, rows) where rows is a
    list of lists of cell strings. The first row of a comp table is its header.
    """

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables: List[Dict[str, Any]] = []
        self._last_bold: Optional[str] = None  # most recent bold run
        self._bold_depth = 0
        self._bold_buf: List[str] = []
        # table state
        self._in_table = False
        self._cur_rows: List[List[str]] = []
        self._cur_row: Optional[List[str]] = None
        self._cur_cell: Optional[List[str]] = None
        self._table_preceding_bold: Optional[str] = None

    def handle_starttag(self, tag, attrs):
        if tag in ("b", "strong"):
            self._bold_depth += 1
            self._bold_buf = []
        elif tag == "table":
            self._in_table = True
            self._cur_rows = []
            self._table_preceding_bold = self._last_bold
        elif tag == "tr" and self._in_table:
            self._cur_row = []
        elif tag in ("td", "th") and self._in_table:
            self._cur_cell = []

    def handle_endtag(self, tag):
        if tag in ("b", "strong"):
            if self._bold_depth > 0:
                self._bold_depth -= 1
                text = "".join(self._bold_buf).strip()
                if text:
                    self._last_bold = text
                self._bold_buf = []
        elif tag == "table" and self._in_table:
            self.tables.append({
                "preceding_bold": self._table_preceding_bold,
                "rows": self._cur_rows,
            })
            self._in_table = False
            self._cur_rows = []
        elif tag == "tr" and self._in_table:
            if self._cur_row is not None:
                self._cur_rows.append(self._cur_row)
            self._cur_row = None
        elif tag in ("td", "th") and self._in_table:
            if self._cur_cell is not None and self._cur_row is not None:
                self._cur_row.append("".join(self._cur_cell).strip())
            self._cur_cell = None

    def handle_data(self, data):
        if self._bold_depth > 0:
            self._bold_buf.append(data)
        if self._cur_cell is not None:
            self._cur_cell.append(data)


# Header text that marks a comp-shaped table. We require a couple of these to be
# present so signature / confidentiality decoy tables (which have none) are
# skipped.
_COMP_HEADER_TOKENS = {
    "tenant", "landlord", "sign date", "sf", "transaction type",
    "base rent", "rate", "submarket", "sale price", "sale date",
    "buyer", "seller", "cap rate", "term",
}


def _is_comp_header(header_cells: List[str]) -> bool:
    norm = [c.strip().lower() for c in header_cells]
    hits = sum(
        1 for cell in norm
        if any(tok == cell or tok in cell for tok in _COMP_HEADER_TOKENS)
    )
    return hits >= 3


def _source_from_bold(bold: Optional[str]) -> Optional[str]:
    """`JLL Comps:` -> `JLL`; `Tri Property Comps:` -> `Tri Property`."""
    if not bold:
        return None
    text = bold.strip()
    # strip a trailing colon then a trailing ' Comps'
    m = re.match(r"^(.*?)\s*comps\s*:?\s*$", text, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return None


def parse_email(html: str) -> List[Dict[str, Any]]:
    """Parse a forwarded comp email into a list of normalized, validated rows.

    For each HTML table: find the nearest preceding `<Source> Comps:` bold
    header and stamp every row's original_source with the source name; skip
    tables with no comp-shaped header row (signature + confidentiality decoys);
    run detect_transaction_type + apply_alias_map + validate_row per data row.
    """
    parser = _EmailParser()
    parser.feed(html)

    out: List[Dict[str, Any]] = []
    for table in parser.tables:
        rows = table["rows"]
        if not rows:
            continue
        header = rows[0]
        if not _is_comp_header(header):
            continue  # decoy table (signature, confidentiality, etc.)

        source = _source_from_bold(table["preceding_bold"])
        txn_type = detect_transaction_type(header)

        for data_row in rows[1:]:
            if not any(cell.strip() for cell in data_row):
                continue  # blank row
            raw = {header[i]: data_row[i]
                   for i in range(min(len(header), len(data_row)))}
            norm = apply_alias_map(raw, txn_type)
            if source:
                norm["original_source"] = source
            validate_row(norm)
            out.append(norm)

    return out
