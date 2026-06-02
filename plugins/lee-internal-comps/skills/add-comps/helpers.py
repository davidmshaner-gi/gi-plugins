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

import csv
import json
import os
import re
from collections import Counter
from html.parser import HTMLParser
from typing import Any, Callable, Dict, List, Optional


# Parser version stamped onto every write payload so downstream ingest can tell
# which normalization logic produced a row set. Bump on contract-affecting
# changes to the adapters.
PARSER_VERSION = "add-comps/v1"

# import_method values the lee_comps_add_write MCP tool accepts.
_VALID_IMPORT_METHODS = {
    "email_paste", "xlsx_upload", "text_paste", "image_paste",
}


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


# ---------------------------------------------------------------------------
# B4 — spreadsheet + text adapters
# ---------------------------------------------------------------------------
class AmbiguousSheetError(Exception):
    """Raised when an xlsx has multiple comp-shaped sheets and we can't pick one.

    The skill layer catches this to ask the operator which sheet to ingest —
    we never silently guess.
    """

    def __init__(self, sheet_names: List[str]):
        self.sheet_names = list(sheet_names)
        super().__init__(
            "Multiple comp-shaped sheets found; specify which one: "
            + ", ".join(self.sheet_names)
        )


def _header_is_comp_shaped(header_cells: List[str]) -> bool:
    """A header row is comp-shaped if >= 3 of its cells map to a canonical key
    under either alias map (i.e. apply_alias_map would fold them in), OR they
    match the comp-header token set used by the email adapter.

    Pure-header probe — no data rows needed.
    """
    norm = [str(c).strip().lower() for c in header_cells if c is not None]
    norm = [c for c in norm if c]
    alias_hits = sum(
        1 for c in norm
        if c in LEASE_ALIASES or c in SALE_ALIASES
    )
    if alias_hits >= 3:
        return True
    # Fallback to the token-substring heuristic the email adapter uses.
    return _is_comp_header(header_cells)


def _normalize_table(header: List[str], data_rows: List[List[Any]]) -> List[Dict[str, Any]]:
    """Shared detect + alias + validate pipeline for a single tabular block.

    `header` is the header cell list; `data_rows` is a list of cell lists.
    Skips fully-blank rows. Returns normalized, validated rows.
    """
    txn_type = detect_transaction_type([str(h) if h is not None else "" for h in header])
    out: List[Dict[str, Any]] = []
    for data_row in data_rows:
        cells = [("" if c is None else c) for c in data_row]
        if not any(str(c).strip() for c in cells):
            continue  # blank row
        raw = {header[i]: cells[i]
               for i in range(min(len(header), len(cells)))
               if header[i] is not None and str(header[i]).strip() != ""}
        if not raw:
            continue
        norm = apply_alias_map(raw, txn_type)
        validate_row(norm)
        out.append(norm)
    return out


def _parse_csv(path: str) -> List[Dict[str, Any]]:
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.reader(fh)
        rows = [r for r in reader]
    rows = [r for r in rows if any(str(c).strip() for c in r)]
    if not rows:
        return []
    header = [str(c).strip() for c in rows[0]]
    return _normalize_table(header, rows[1:])


def _parse_xlsx(path: str) -> List[Dict[str, Any]]:
    import openpyxl  # local import: only needed for the xlsx path

    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        comp_sheets: List[str] = []
        sheet_headers: Dict[str, List[Any]] = {}
        sheet_data: Dict[str, List[List[Any]]] = {}
        for ws in wb.worksheets:
            grid = [list(r) for r in ws.iter_rows(values_only=True)]
            # Find the first non-blank row as the header.
            header_idx = None
            for i, r in enumerate(grid):
                if any(c is not None and str(c).strip() != "" for c in r):
                    header_idx = i
                    break
            if header_idx is None:
                continue
            header = grid[header_idx]
            if _header_is_comp_shaped(header):
                comp_sheets.append(ws.title)
                sheet_headers[ws.title] = header
                sheet_data[ws.title] = grid[header_idx + 1:]

        if not comp_sheets:
            return []
        if len(comp_sheets) > 1:
            raise AmbiguousSheetError(comp_sheets)

        only = comp_sheets[0]
        header = [str(c).strip() if c is not None else "" for c in sheet_headers[only]]
        return _normalize_table(header, sheet_data[only])
    finally:
        wb.close()


def parse_spreadsheet(path: str) -> List[Dict[str, Any]]:
    """Parse an `.xlsx` or `.csv` comp file into normalized, validated rows.

    For a multi-tab xlsx, only comp-shaped sheets (header row matches >= 3 alias
    keys) are considered; prose / view tabs are skipped. If more than one
    comp-shaped sheet is found, raises AmbiguousSheetError(list_of_sheet_names)
    so the skill layer can ask the operator which sheet to ingest — we never
    silently pick. Each sheet is routed by detect_transaction_type, so a SALE
    sheet fills the sale block and the lease block stays None.
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        return _parse_csv(path)
    if ext in (".xlsx", ".xlsm"):
        return _parse_xlsx(path)
    raise ValueError(
        "parse_spreadsheet supports .csv and .xlsx; got: %s" % (ext or "<none>")
    )


def _split_delimited(line: str) -> List[str]:
    """Split a pasted table line on tab or pipe (whichever the line uses).

    Tab wins if present (Excel paste); otherwise pipe. Pipe cells are stripped
    and any leading/trailing empty cells from a `| a | b |` border are dropped.
    """
    if "\t" in line:
        return [c.strip() for c in line.split("\t")]
    if "|" in line:
        cells = [c.strip() for c in line.split("|")]
        # Drop empty leading/trailing cells produced by border pipes.
        while cells and cells[0] == "":
            cells.pop(0)
        while cells and cells[-1] == "":
            cells.pop()
        return cells
    # Single column / no delimiter.
    return [line.strip()]


def parse_text(blob: str) -> List[Dict[str, Any]]:
    """Parse a pasted tab- or pipe-delimited comp table (header row + data rows)
    into normalized, validated rows via the detect + alias + validate pipeline.
    """
    lines = [ln for ln in blob.splitlines() if ln.strip()]
    if not lines:
        return []
    header = _split_delimited(lines[0])
    data_rows = [_split_delimited(ln) for ln in lines[1:]]
    return _normalize_table(header, data_rows)


# ---------------------------------------------------------------------------
# B5 — image + LLM-fallback adapters (dependency-injected model vision)
# ---------------------------------------------------------------------------
# Contract for the injected `model_extract` callable:
#   - signature: model_extract(ref) -> list[dict]
#     where `ref` is the image reference (parse_image) or the raw table blob
#     (llm_fallback).
#   - it MUST return a list of ALREADY-CANONICAL row dicts (keys drawn from
#     CANONICAL_KEYS, with `transaction_type` set). We do NOT re-alias the
#     model's output — the model is responsible for emitting canonical keys.
#   - these adapters then run each returned row through validate_row (flag,
#     never drop) so the dry-run + write path treats them identically to the
#     deterministic adapters.
# In production the skill's own Claude runtime IS the model; in tests a mock is
# injected. There is no module-level default — calling without a model raises.

def _run_model_extract(ref: Any, model_extract: Optional[Callable[[Any], List[Dict[str, Any]]]]) -> List[Dict[str, Any]]:
    if model_extract is None:
        raise ValueError(
            "no model_extract callable provided; this adapter requires an "
            "injected model (the skill's Claude runtime in production, a mock "
            "in tests)."
        )
    rows = model_extract(ref)
    if rows is None:
        return []
    out: List[Dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        # Default transaction_type to lease if the model omitted it, mirroring
        # detect_transaction_type's default, so validate_row picks a branch.
        if not row.get("transaction_type"):
            row["transaction_type"] = "lease"
        validate_row(row)
        out.append(row)
    return out


def parse_image(image_ref: Any, model_extract: Optional[Callable[[Any], List[Dict[str, Any]]]]) -> List[Dict[str, Any]]:
    """Extract comp rows from an image (a pasted screenshot of a comp table).

    `model_extract` is an injected vision callable returning already-canonical
    row dicts; this adapter validates each one. No network, no API key here —
    the model is the skill's own runtime in production.
    """
    return _run_model_extract(image_ref, model_extract)


def llm_fallback(table_blob: Any, model_extract: Optional[Callable[[Any], List[Dict[str, Any]]]]) -> List[Dict[str, Any]]:
    """Last-resort adapter for a table blob the deterministic parsers couldn't
    handle: hand it to the injected `model_extract` and validate the canonical
    rows it returns.
    """
    return _run_model_extract(table_blob, model_extract)


# ---------------------------------------------------------------------------
# B6 — dry-run summary + write-payload builder
# ---------------------------------------------------------------------------
def dry_run_summary(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Summarize a normalized row set for operator review before write.

    Returns: total count, per-`original_source` counts, and the flagged rows
    (their index + original_source + flag_reason). Used to show the operator
    what will be written and what needs attention.
    """
    by_source = Counter()
    for r in rows:
        src = r.get("original_source")
        by_source[src if src is not None else "(unattributed)"] += 1

    flagged: List[Dict[str, Any]] = []
    for i, r in enumerate(rows):
        if r.get("flagged") == 1:
            flagged.append({
                "index": i,
                "original_source": r.get("original_source"),
                "property_address": r.get("property_address"),
                "flag_reason": r.get("flag_reason", ""),
            })

    return {
        "total": len(rows),
        "by_source": dict(by_source),
        "flagged_count": len(flagged),
        "flagged": flagged,
    }


def build_write_payload(rows: List[Dict[str, Any]], meta: Dict[str, Any]) -> Dict[str, Any]:
    """Build the exact AddCompsPayload dict the lee_comps_add_write MCP tool
    expects.

    Required from `meta`: added_by, import_method (one of email_paste |
    xlsx_upload | text_paste | image_paste), raw_blob.
    Optional from `meta`: client_id, source_label, raw_blob_ref, notes.
    `parser_version` is always stamped from the PARSER_VERSION module constant.
    `rows` passes through unchanged.
    """
    added_by = meta.get("added_by")
    if not added_by:
        raise ValueError("meta['added_by'] is required")

    import_method = meta.get("import_method")
    if import_method not in _VALID_IMPORT_METHODS:
        raise ValueError(
            "meta['import_method'] must be one of %s; got %r"
            % (sorted(_VALID_IMPORT_METHODS), import_method)
        )

    payload: Dict[str, Any] = {
        "added_by": added_by,
        "import_method": import_method,
        "raw_blob": meta.get("raw_blob", ""),
        "parser_version": PARSER_VERSION,
        "rows": rows,
    }

    # Optional passthroughs — only include when present (non-empty).
    for opt in ("client_id", "source_label", "raw_blob_ref", "notes"):
        val = meta.get(opt)
        if val is not None and val != "":
            payload[opt] = val

    return payload
