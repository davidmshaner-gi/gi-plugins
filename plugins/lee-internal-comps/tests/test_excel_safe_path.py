"""
Windows 218-char path guard for the comps Excel exports (gi-plugins#7).

Brokers open these workbooks in Excel on Windows, where the full path cannot
exceed 218 chars and the Cowork base dir is already ~125 deep. Every comps
skill that writes an .xlsx must flatten whatever directory the caller prepended
down to a basename in the CWD and cap the filename, so a deep or long path
cannot survive even if the model ignores the SKILL.md rule.

This test pins the shared `safe_xlsx_name` helper (canonical in internal-comps)
AND asserts each skill's workbook builder actually flattens-to-CWD + caps the
filename, mirroring tests/test_land_price_per_acre.py.

Card: davidmshaner-gi/gi-plugins#7 (re-opened).
"""

import importlib.util
import os
import sys
import tempfile

from openpyxl import Workbook, load_workbook

SKILLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "skills",
)

# Filename cap the guard enforces (the `[:45] + ".xlsx"` slice → 50 chars total).
MAX_NAME_LEN = 50
MAX_STEM_LEN = 45


def _load(skill_name):
    """Import a skill's helpers.py as a uniquely-named module (isolated per skill)."""
    path = os.path.join(SKILLS_DIR, skill_name, "helpers.py")
    mod_name = f"_skill_{skill_name.replace('-', '_')}"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    # Each skill dir must be importable for any in-file `load_sibling` calls.
    sys.path.insert(0, os.path.join(SKILLS_DIR, skill_name))
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# 1. The shared helper itself (canonical in internal-comps).
# ---------------------------------------------------------------------------

internal = _load("internal-comps")


def test_safe_xlsx_name_flattens_a_deep_path_to_basename():
    deep = "/" + "/".join(["a-very-long-directory-segment"] * 8) + "/wake_sale.xlsx"
    out = internal.safe_xlsx_name(deep)
    assert out == "wake_sale.xlsx"
    assert os.sep not in out and "/" not in out and "\\" not in out


def test_safe_xlsx_name_flattens_windows_backslash_path():
    out = internal.safe_xlsx_name(r"C:\Users\bonne\Deep\Nested\path\comps.xlsx")
    assert out == "comps.xlsx"


def test_safe_xlsx_name_caps_long_filename_to_50_chars():
    long_stem = "industrial_lease_comps_raleigh_durham_chapel_hill_triangle_2026"
    out = internal.safe_xlsx_name(f"/tmp/{long_stem}.xlsx")
    assert len(out) <= MAX_NAME_LEN
    assert out.endswith(".xlsx")
    assert out[:-5] == long_stem[:MAX_STEM_LEN]


def test_safe_xlsx_name_appends_xlsx_when_missing():
    assert internal.safe_xlsx_name("/tmp/comps").endswith(".xlsx")


def test_safe_xlsx_name_empty_basename_falls_back():
    # A path that is just a directory (trailing slash) → fallback name, still .xlsx.
    out = internal.safe_xlsx_name("/tmp/some/dir/")
    assert out.endswith(".xlsx")
    assert os.sep not in out


# ---------------------------------------------------------------------------
# 2. Every comps skill's workbook builder flattens-to-CWD + caps the name.
#    (The bug in #7: a builder that computes the safe name but saves the
#    original path anyway, or has no guard at all.)
# ---------------------------------------------------------------------------

# A long, deep path the caller might prepend — must NOT survive to disk.
def _deep_long_path(stem):
    return (
        "/Users/bonne/Cowork/a/very/deep/base/dir/that/eats/the/budget/"
        + stem
        + "_industrial_lease_comps_raleigh_durham_2026_extended.xlsx"
    )


def test_internal_comps_format_excel_writes_safe_basename():
    rows = [{
        "comps_id": "L-1", "comp_name": "Acme", "street_address": "1 Main St",
        "city": "Raleigh", "county": "Wake", "property_type": "Industrial",
        "space_sf": 10000, "building_size": 40000, "asking_rate_per_sf": 12.5,
        "effective_rate": 11.0, "lease_execution": "2026-01-01",
    }]
    validated = {"asset_type": "industrial", "transaction_type": "lease",
                 "geography": {"named_market": "Triangle"}}
    with tempfile.TemporaryDirectory() as d:
        cwd = os.getcwd()
        os.chdir(d)
        try:
            res = internal.format_excel(rows, validated, _deep_long_path("int"), [], [])
            written = res["path"]
            assert os.sep not in written, f"path not flattened: {written!r}"
            assert len(written) <= MAX_NAME_LEN
            assert os.path.exists(os.path.join(d, written))
        finally:
            os.chdir(cwd)


def test_external_comps_writer_writes_safe_basename():
    ext = _load("external-comps")
    rows = [{
        "external_id": "E-1", "property_address": "2 Oak St", "property_city": "Cary",
        "county": "Wake", "submarket": "RTP", "property_type": "Industrial",
        "building_sf": 50000, "lease_start_date": "2026-01-01", "base_rent": 9.5,
        "rent_type": "NNN", "tenant_name": "BigCo",
    }]
    validated = {"asset_type": "industrial", "transaction_type": "lease",
                 "geography": {"named_market": "RDU MSA"}}
    with tempfile.TemporaryDirectory() as d:
        cwd = os.getcwd()
        os.chdir(d)
        try:
            written = ext.format_excel(
                rows, validated, _deep_long_path("ext"), [], [], []
            )
            assert os.sep not in written, f"path not flattened: {written!r}"
            assert len(written) <= MAX_NAME_LEN
            assert os.path.exists(os.path.join(d, written))
        finally:
            os.chdir(cwd)


def test_internal_and_external_comps_writer_writes_safe_basename():
    unified = _load("internal-and-external-comps")
    internal_core = []
    external_core = [unified.to_core({
        "costar_property_id": "C-1", "property_address": "3 Pine St",
        "property_city": "Durham", "county": "Durham", "property_type": "Industrial",
        "building_sf": 60000, "base_rent": 10.0, "rent_type": "NNN",
        "lease_start_date": "2026-01-01",
    }, unified.SOURCE_EXTERNAL, "lease")]
    core_rows = unified.combine(internal_core, external_core, "lease")
    validated = {"transaction_type": "lease"}
    with tempfile.TemporaryDirectory() as d:
        cwd = os.getcwd()
        os.chdir(d)
        try:
            written = unified.format_unified_excel(
                core_rows, [], external_core, validated, _deep_long_path("unified")
            )
            assert os.sep not in written, f"path not flattened: {written!r}"
            assert len(written) <= MAX_NAME_LEN
            assert os.path.exists(os.path.join(d, written))
        finally:
            os.chdir(cwd)
