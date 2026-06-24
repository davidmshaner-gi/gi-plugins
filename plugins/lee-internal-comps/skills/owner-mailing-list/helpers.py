"""Owner mailing list helpers (pure Python, no network)."""
import csv
import os
import re

def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)

def default_output_path(request, date):
    addr = (request.get("subject_property") or {}).get("address", "area")
    slug = slugify(addr)[:60].rstrip("-")
    return f"owners-{slug}-{date}.csv"

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

def _safe_csv_name(output_path):
    """Flatten a caller-prepended directory to a basename and cap the length.

    Defense-in-depth for the Windows 218-char path limit (gi#7): brokers open
    this CSV on Windows where the full path cannot exceed 218 chars and the
    Cowork base dir is already ~125 deep. Flatten any directory and cap the
    filename so a deep or long path can't survive even if the model ignores the
    SKILL.md rule. Mirrors the internal-comps xlsx-save guard.
    """
    name = os.path.basename((output_path or "").replace("\\", "/")) or "owners.csv"
    if not name.lower().endswith(".csv"):
        name += ".csv"
    if len(name) > 60:
        name = name[:-4][:56] + ".csv"
    return name

def format_csv(rows, request, date, out_dir="."):
    name = _safe_csv_name(default_output_path(request, date))
    path = os.path.join(out_dir, name) if out_dir not in ("", ".") else name
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in CSV_FIELDS})
    return path
