"""Guard against the bare-`helpers` import collision returning (gi-plugins#137).

Several skills each ship a `helpers.py`. A test file that does
`sys.path.insert(<skill dir>); import helpers` poisons `sys.modules["helpers"]`
for every later-collected test file — each file passes alone while the full-dir
run fails with cross-skill AttributeErrors. The fix is the shared
`conftest.load_skill_helpers` loader (unique per-skill module names, no sys.path
mutation); this test statically pins the rule so a new test file can't
reintroduce the pattern.
"""

import os
import re

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))

BARE_HELPERS_IMPORT = re.compile(r"^\s*(import helpers\b|from helpers import)", re.M)
SYS_PATH_MUTATION = re.compile(r"^\s*sys\.path\.(insert|append)", re.M)


def _test_sources():
    for name in sorted(os.listdir(TESTS_DIR)):
        if name.endswith(".py") and name != os.path.basename(__file__):
            with open(os.path.join(TESTS_DIR, name)) as f:
                yield name, f.read()


def test_no_bare_helpers_import():
    offenders = [n for n, src in _test_sources() if BARE_HELPERS_IMPORT.search(src)]
    assert not offenders, (
        f"bare `import helpers` in {offenders} — use "
        "`from conftest import load_skill_helpers` (see conftest.py docstring)"
    )


def test_no_sys_path_mutation():
    offenders = [n for n, src in _test_sources() if SYS_PATH_MUTATION.search(src)]
    assert not offenders, (
        f"sys.path mutation in {offenders} — load skill helpers via "
        "`conftest.load_skill_helpers` instead (no sys.path needed)"
    )
