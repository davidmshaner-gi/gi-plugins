# plugins/lee-internal-comps/tests/test_owner_mailing_list.py
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "owner-mailing-list"))
import helpers

def test_slugify_basic():
    assert helpers.slugify("100 Walnut St, Cary NC") == "100-walnut-st-cary-nc"

def test_default_output_path_is_flat_and_short():
    req = {"subject_property": {"address": "100 Walnut St, Cary NC"}}
    p = helpers.default_output_path(req, date="2026-06-02")
    # flat: no directory separators, no subfolder
    assert "/" not in p and "\\" not in p
    assert p == "owners-100-walnut-st-cary-nc-2026-06-02.csv"
    # whole filename comfortably under the 218-char budget worst case
    assert len(p) < 80
