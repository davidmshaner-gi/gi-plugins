"""
Windows 218-char path guard for the comps Excel exports (gi-plugins#7).

Brokers open these workbooks in Excel on Windows, where the full path cannot
exceed 218 chars ("the file path is too long") and Cowork's per-session output
dir already runs ~200 chars deep. The file MUST land in that fixed session dir,
so the only lever the skill controls is the FILENAME. Every comps skill that
writes an .xlsx therefore emits a tiny constant stub — `c.xlsx` — instead of
a descriptive name, enumerating `c1.xlsx`, `c2.xlsx`, ... on collision so
a second pull in the same session never clobbers the first. The descriptive title
lives on the Sheet 1 tab; the broker renames the file.

This test pins the shared `safe_xlsx_name` helper (canonical in internal-comps)
AND asserts each skill's workbook builder actually writes that short stub name.

Card: davidmshaner-gi/gi-plugins#7 (re-opened).
"""

import os
import tempfile

from conftest import load_skill_helpers

# Generous ceiling: the stub + enumeration suffix stays well under this. The point
# of the change is that the name is tiny (~6 chars), not the old 50-char cap. The
# expected stub itself is read from the helper's XLSX_STUB so this test never needs
# editing if the stub is shortened further.
MAX_NAME_LEN = 16


# Skill helpers load via the shared conftest loader (unique module name, no
# sys.path mutation — the old per-skill sys.path.insert here armed the bare
# `import helpers` collision that gi-plugins#137 fixed).
_load = load_skill_helpers


# ---------------------------------------------------------------------------
# 1. The shared helper itself (canonical in internal-comps).
# ---------------------------------------------------------------------------

internal = _load("internal-comps")

# Expected names derive from the helper's own stub, so shortening XLSX_STUB
# (e.g. "comps" -> "c" for deep Windows session dirs) needs no test edits.
STUB = internal.XLSX_STUB
STUB_NAME = f"{STUB}.xlsx"


def test_safe_xlsx_name_ignores_descriptive_path_and_emits_stub():
    # Whatever the caller prepends — deep dir, descriptive name, Windows backslashes —
    # the helper returns the tiny constant stub, in an empty CWD.
    with tempfile.TemporaryDirectory() as d:
        cwd = os.getcwd()
        os.chdir(d)
        try:
            deep = "/" + "/".join(["a-very-long-directory-segment"] * 8) + "/wake_sale.xlsx"
            assert internal.safe_xlsx_name(deep) == STUB_NAME
            assert internal.safe_xlsx_name(r"C:\Users\bonne\Deep\industrial_lease_comps_2026.xlsx") == STUB_NAME
            assert internal.safe_xlsx_name("") == STUB_NAME
            out = internal.safe_xlsx_name(deep)
            assert os.sep not in out and "/" not in out and "\\" not in out
            assert len(out) <= MAX_NAME_LEN
        finally:
            os.chdir(cwd)


def test_safe_xlsx_name_enumerates_on_collision():
    # A second / third pull in the same session must not clobber the first.
    with tempfile.TemporaryDirectory() as d:
        cwd = os.getcwd()
        os.chdir(d)
        try:
            assert internal.safe_xlsx_name() == f"{STUB}.xlsx"
            open(f"{STUB}.xlsx", "w").close()
            assert internal.safe_xlsx_name() == f"{STUB}1.xlsx"
            open(f"{STUB}1.xlsx", "w").close()
            assert internal.safe_xlsx_name() == f"{STUB}2.xlsx"
        finally:
            os.chdir(cwd)


def test_safe_xlsx_name_always_ends_in_xlsx():
    with tempfile.TemporaryDirectory() as d:
        cwd = os.getcwd()
        os.chdir(d)
        try:
            assert internal.safe_xlsx_name("/tmp/comps").endswith(".xlsx")
        finally:
            os.chdir(cwd)


def test_external_comps_mirror_matches_canonical():
    # The standalone mirror must behave identically to the canonical helper.
    ext = _load("external-comps")
    with tempfile.TemporaryDirectory() as d:
        cwd = os.getcwd()
        os.chdir(d)
        try:
            assert ext.safe_xlsx_name("/deep/descriptive_name_2026.xlsx") == STUB_NAME
            assert ext.XLSX_STUB == STUB  # mirror must agree on the stub
            open(f"{STUB}.xlsx", "w").close()
            assert ext.safe_xlsx_name() == f"{STUB}1.xlsx"
        finally:
            os.chdir(cwd)


# ---------------------------------------------------------------------------
# 2. Every comps skill's workbook builder writes the short stub to the CWD.
#    (The bug in #7: a builder that computes the safe name but saves the
#    original descriptive/deep path anyway, or has no guard at all.)
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
