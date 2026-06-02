"""Helpers for the internal-and-external-comps skill — the unified "all comps" default.

This skill is a thin orchestrator: it reuses the parse/validate/query logic of the
sibling `internal-comps` and `external-comps` skills (via load_sibling) and adds only
the combine layer (to_core, combine, format_unified_excel, unified_markdown_table).
"""
import importlib.util
import sys
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
