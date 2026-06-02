"""Owner mailing list helpers (pure Python, no network)."""
import csv
import os
import re

def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)

def default_output_path(request, date):
    addr = (request.get("subject_property") or {}).get("address", "area")
    return f"owners-{slugify(addr)}-{date}.csv"

def _norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())

def dedupe_by_mailing_address(rows):
    seen, out = set(), []
    for r in rows:
        key = _norm(r.get("mail_addr"))
        if key in seen:
            continue
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
    # subject address: prefer "miles of <addr>" / "mile of <addr>", fall back to "near <addr>"
    s = re.search(r"(?:miles?|mi)\s+of\s+(\d[^,]*(?:,\s*[A-Za-z .]+(?:,?\s*[A-Z]{2})?)?)", t, re.I) or \
        re.search(r"(?:around|near)\s+(\d[^,]*(?:,\s*[A-Za-z .]+(?:,?\s*[A-Z]{2})?)?)", t, re.I)
    address = s.group(1).strip() if s else ""
    return {
        "subject_property": {"address": address},
        "radius_mi": radius,
        "size": size,
        "land_class": land_class,
        "raw": t,
    }

CSV_FIELDS = ["owner", "mail_addr", "site_addr", "acreage", "land_class"]

def format_csv(rows, request, date, out_dir="."):
    name = default_output_path(request, date)
    path = os.path.join(out_dir, name) if out_dir not in ("", ".") else name
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in CSV_FIELDS})
    return path
