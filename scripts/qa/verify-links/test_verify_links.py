#!/usr/bin/env python3
"""Offline unit tests for the verify-link QA harness decision logic.

No network, no browser -- covers the pure parts most likely to be edited later:
baseline verdicts, PIN normalization, and result-page assertion (success, the
Tyler error page, dash-formatted PINs, empty results). Run:

    python3 test_verify_links.py        # prints OK or fails loudly
"""

from types import SimpleNamespace

from adapters import _assert_parcel, _norm
from verify_links import _verdict


def _c(*expect):
    return SimpleNamespace(expect_any=tuple(expect))


def test_norm_strips_dashes_and_spaces():
    assert _norm("0822-41-9440") == "0822419440"
    assert _norm("R04720-007-011-000") == "R04720007011000"
    assert _norm(" pnc llc ") == "PNCLLC"


def test_verdict_baseline_matrix():
    # (actual_pass, expected) -> ok_with_baseline
    assert _verdict(True, "pass")[0] is True          # healthy
    assert _verdict(False, "fail")[0] is True          # known-broken, steady (none today)
    assert _verdict(False, "pass")[0] is False         # REGRESSION -> loud
    assert _verdict(True, "fail")[0] is False          # FIXED -> loud (update baseline)
    assert "REGRESSION" in _verdict(False, "pass")[1]
    assert "FIXED" in _verdict(True, "fail")[1]


def test_assert_parcel_success_with_dash_formatted_pin():
    body = "Property Summary\nPIN # 0822-41-9440\nProperty Owner DUKE UNIVERSITY"
    ok, detail = _assert_parcel(body, _c("0822419440", "DUKE UNIVERSITY"))
    assert ok is True, detail


def test_assert_parcel_catches_tyler_error_page():
    body = "An Error has Occurred\nThe system encountered a problem and cannot complete the requested action."
    ok, detail = _assert_parcel(body, _c("9645459484"))
    assert ok is False
    assert "rejected the PIN" in detail


def test_assert_parcel_catches_empty_results():
    body = "Search by Parcel ID\nNo records found for your search."
    ok, detail = _assert_parcel(body, _c("0734835370"))
    assert ok is False


def test_assert_parcel_fails_when_pin_absent():
    # Page loaded, no failure marker, but the expected parcel isn't shown.
    body = "Welcome to the property search portal. Please enter a parcel id."
    ok, detail = _assert_parcel(body, _c("0734835370", "PNC OF NORTH CAROLINA"))
    assert ok is False
    assert "did not show" in detail


def test_assert_parcel_success_token_beats_generic_failure_word():
    # The correct parcel IS shown, but the page chrome contains a generic word
    # from FAILURE_MARKERS ("invalid"). Token-first ordering must still PASS --
    # otherwise a footer/help-text change would false-FAIL the release gate.
    body = (
        "Parcel R04720-007-011-000 — OWNER: ACME HOLDINGS LLC\n"
        "Footer: to report invalid assessment data, contact the county."
    )
    ok, detail = _assert_parcel(body, _c("R04720007011000"))
    assert ok is True, detail


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  ok  {t.__name__}")
    print(f"\n{len(tests)} passed")


if __name__ == "__main__":
    main()
