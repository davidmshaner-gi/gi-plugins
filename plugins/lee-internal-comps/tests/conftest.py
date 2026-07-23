"""Shared test plumbing for the lee-internal-comps suite (gi-plugins#137).

Several skills each ship their own `helpers.py`. Historically some test files did
`sys.path.insert(<skill dir>); import helpers` — whichever skill's module landed in
`sys.modules["helpers"]` first won, so a full-dir `pytest plugins/lee-internal-comps/tests/`
run resolved later bare imports to the WRONG skill's helpers (14 false failures), while
each file passed in isolation.

The rule: never import a skill's helpers by the bare name `helpers`, and never mutate
`sys.path` to reach a skill dir. Load by file path under a unique per-skill module name
via `load_skill_helpers` below (the pattern test_lee_brand_excel.py pioneered).
"""

import importlib.util
import os
import sys

SKILLS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills")


def load_skill_helpers(skill: str):
    """Load `<skills>/<skill>/helpers.py` under the unique module name
    `helpers_<skill_snake>`. Cached in sys.modules so repeated calls are cheap and
    every test file sharing a skill gets the same module object. No sys.path
    mutation — skills' own sibling imports (`load_sibling`) are also path-based,
    so nothing needs the skill dir on sys.path.
    """
    mod_name = f"helpers_{skill.replace('-', '_')}"
    if mod_name in sys.modules:
        return sys.modules[mod_name]
    path = os.path.join(SKILLS_DIR, skill, "helpers.py")
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"load_skill_helpers: cannot build import spec for {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    return mod
