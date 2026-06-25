"""Owner mailing list helpers (pure Python, no network)."""
import csv
import os
import re

# The CSV lands in Cowork's per-session output dir, which on Windows runs ~190-210
# chars deep and can't be relocated. Excel refuses to OPEN any file whose full path
# exceeds 218 chars, so the only lever is the filename. A descriptive name like
# `owners-100-walnut-st-cary-nc-2026-06-02.csv` (44 chars) pushes the total well past
# 218; a tiny constant stub does not. Same fix + rationale as the comps `safe_xlsx_name`
# (XLSX_STUB) — see internal-comps/helpers.py and the comps architecture doc, §5 DELIVER.
# (gi-plugins#7 generalized in #112.)
CSV_STUB = "o"  # stub + enum suffix + ".csv" must stay <=~8 chars; "o" leaves room through o99.csv

def _norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())

def dedupe_by_mailing_address(rows):
    seen, out = set(), []
    for r in rows:
        key = _norm(r.get("mail_addr"))
        # Only dedupe non-blank mailing addresses; blank/None keys pass through
        # so real owners with no mailing address are never silently collapsed.
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        out.append(r)
    report = {"input": len(rows), "output": len(out), "dropped": len(rows) - len(out)}
    return out, report

def parse_request(text):
    t = text or ""
    # radius: "within N miles" / "N mi" / "N-mile"
    m = re.search(r"within\s+([\d.]+)\s*(?:miles?|mi)\b", t, re.I) or \
        re.search(r"\b([\d.]+)\s*-?\s*miles?\b", t, re.I)
    radius = float(m.group(1)) if m else None
    # acreage range "2-5 acre"
    a = re.search(r"([\d.]+)\s*-\s*([\d.]+)\s*acre", t, re.I)
    size = {"min_acres": float(a.group(1)), "max_acres": float(a.group(2))} if a else {}
    # land class: pick up "vacant"
    land_class = "vacant" if re.search(r"\bvacant\b", t, re.I) else ""
    # improved/built-parcel intent: the broker wants parcels WITH a building,
    # not raw land. Any of these phrasings flips improved_only on; it passes
    # straight through to the MCP tool's improved_only param (Step 2 of
    # SKILL.md). improved_only and land_class "vacant" are opposites; enforce
    # that in code (not just prose) -- if a request somehow says both (e.g.
    # "vacant buildings"), the explicit "vacant" wins and improved_only stays
    # off, so we never send the tool two contradictory filters.
    improved_only = bool(
        re.search(r"\b(?:improved|building|buildings|built|structure|structures)\b", t, re.I)
    ) and not land_class
    # subject address: prefer "miles of/from <addr>", fall back to "around/near <addr>"
    # v1 limitation: the address must start with a digit (street number); letter-only
    # street names like "Main St" return "" by design in v1.
    s = re.search(r"(?:miles?|mi)\s+(?:of|from)\s+(\d[^,]*(?:,\s*[A-Za-z .]+(?:,?\s*[A-Z]{2})?)?)", t, re.I) or \
        re.search(r"(?:around|near)\s+(\d[^,]*(?:,\s*[A-Za-z .]+(?:,?\s*[A-Z]{2})?)?)", t, re.I)
    address = s.group(1).strip() if s else ""
    return {
        "subject_property": {"address": address},
        "radius_mi": radius,
        "size": size,
        "land_class": land_class,
        "improved_only": improved_only,
        "raw": t,
    }

def rows_from_mcp(mcp_rows):
    """Map pull_owner_mailing_list rows to the CSV row shape.

    The tool's owner_mail_address is multiline (street\ncity st zip);
    the CSV contract is a single-line mail_addr. building_sf / year_built
    are the building-relevant columns (populated for improved parcels; blank
    for vacant land or counties that carry no building data).
    """
    out = []
    for r in mcp_rows:
        mail = (r.get("owner_mail_address") or "").replace("\n", " ").strip()
        acreage = r.get("lot_size_acres")
        building_sf = r.get("building_sf")
        year_built = r.get("year_built")
        out.append({
            "owner": r.get("owner_raw") or "",
            "mail_addr": mail,
            "site_addr": r.get("address") or "",
            "acreage": "" if acreage is None else acreage,
            "building_sf": "" if building_sf is None else building_sf,
            "year_built": "" if year_built is None else year_built,
            "land_class": r.get("land_use") or "",
        })
    return out


CSV_FIELDS = ["owner", "mail_addr", "site_addr", "acreage", "building_sf", "year_built", "land_class"]

def _safe_csv_name(out_dir="."):
    """Return the shortest stable .csv filename in out_dir, enumerating on collision.

    Emits `o.csv` (CSV_STUB + ".csv"); if that name already exists in out_dir (a
    second mailing-list pull in the same Cowork session), enumerates `o1.csv`,
    `o2.csv`, ... so a later pull never clobbers an earlier deliverable. The
    descriptive address never enters the filename — see the CSV_STUB note above for
    why it can't survive the Windows 218-char Excel-open limit (gi#7 / #112). Mirrors
    the comps `safe_xlsx_name`.
    """
    candidate = f"{CSV_STUB}.csv"
    n = 1
    while os.path.exists(os.path.join(out_dir, candidate)):
        candidate = f"{CSV_STUB}{n}.csv"
        n += 1
    return candidate

def format_csv(rows, request, date, out_dir="."):
    # request/date retained for caller back-compat; no longer used for the filename
    # (the name is forced to the CSV_STUB constant — see _safe_csv_name).
    name = _safe_csv_name(out_dir)
    path = os.path.join(out_dir, name) if out_dir not in ("", ".") else name
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in CSV_FIELDS})
    return path
