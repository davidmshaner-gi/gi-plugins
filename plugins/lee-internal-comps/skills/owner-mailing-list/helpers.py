"""Owner mailing list helpers (pure Python, no network)."""
import re

def slugify(text):
    s = re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")
    return re.sub(r"-{2,}", "-", s)

def default_output_path(request, date):
    addr = (request.get("subject_property") or {}).get("address", "area")
    return f"owners-{slugify(addr)}-{date}.csv"
