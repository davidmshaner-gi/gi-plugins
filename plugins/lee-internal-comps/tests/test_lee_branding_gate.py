"""gi-plugins#169: the lee-branding render cannot proceed from the bundled files alone.

Bonner's two 1.40.0 Sonnet runs (2026-09-03) delivered Lee-branded flyers with zero
`pull_brand_package` rows in prod audit_log, the second in a task that provably had the
connector on. The gate was prose ("Every branded deliverable starts with one tool
call"). G33: prose-only mandatory steps get skipped. The structural gate: the CSS the
render needs comes from `python3 brand.py tokens brand_package.json`, and that command
accepts only a pull_brand_package RESPONSE (brand_version, token_count, usage_rules,
logo, notes), never the bundled brand-colors.json.
"""
import json
import subprocess
import sys
from pathlib import Path

SKILL = Path(__file__).parent.parent / "skills" / "lee-branding"
BRAND_PY = SKILL / "brand.py"


def _response(**over):
    colors = {
        "primary": {"red": "#98002E", "slate": "#7E8083", "charcoal": "#303C42", "white": "#FFFFFF"},
        "secondary": {"navy": "#003146", "sky": "#009AD9", "frost": "#A9C3CB"},
        "accent": {"merlot": "#4E131E", "bright_red": "#CD1442", "green": "#8A941E", "mint": "#6FC9C4"},
    }
    r = {
        "brand_version": "2021.02",
        "local_package_current": True,
        "local_version": "2021.02",
        "tagline": "LOCAL EXPERTISE. INTERNATIONAL REACH. WORLD CLASS.",
        "colors": colors,
        "tints": {"primary_pct": [80, 60, 40]},
        "gradient": {"css": "linear-gradient(145deg, #CD1442 0%, #98002E 65%, #4E131E 100%)"},
        "type": {"stack_sans": "'Avenir Next', 'Nunito Sans', Arial, Tahoma, sans-serif", "stack_serif": "'Minion Pro', Georgia, serif"},
        "usage_rules": {"small_text_under_10pt": "Use charcoal (#303C42) instead of slate (#7E8083) for legibility."},
        "logo": {"min_width_in": 1.125, "clear_space": "equal to the height of the icon on all sides", "prohibited": ["redraw"]},
        "token_count": 11,
        "notes": [],
    }
    r.update(over)
    return r


def _run(*args, cwd=None):
    return subprocess.run([sys.executable, str(BRAND_PY), *args], capture_output=True, text=True, cwd=cwd or SKILL)


def test_tokens_refuses_the_bundled_brand_colors_json():
    out = _run("tokens", str(SKILL / "brand-colors.json"))
    assert out.returncode != 0
    err = json.loads(out.stdout)["error"]
    assert "pull_brand_package" in err and "bundled" in err


def test_tokens_accepts_a_pull_brand_package_response(tmp_path):
    p = tmp_path / "brand_package.json"
    p.write_text(json.dumps(_response()))
    out = _run("tokens", str(p))
    assert out.returncode == 0, out.stdout + out.stderr
    css = out.stdout
    assert "--lee-red: #98002E" in css
    assert "--lee-charcoal: #303C42" in css
    assert "@font-face" in css and "AvenirNextCyr-Bold.woff" in css
    assert "--lee-gradient:" in css
    assert "lee_logo.svg" in css
    assert "small_text_under_10pt" in css


def test_tokens_rejects_a_response_whose_token_count_does_not_match_its_colors(tmp_path):
    p = tmp_path / "brand_package.json"
    p.write_text(json.dumps(_response(token_count=4)))
    out = _run("tokens", str(p))
    assert out.returncode != 0
    assert "token_count" in json.loads(out.stdout)["error"]


def test_tokens_rejects_a_payload_missing_the_fields_only_the_tool_returns(tmp_path):
    r = _response()
    for k in ("brand_version", "usage_rules", "logo", "notes", "local_package_current"):
        r.pop(k)
    p = tmp_path / "brand_package.json"
    p.write_text(json.dumps(r))
    out = _run("tokens", str(p))
    assert out.returncode != 0
    assert "brand.py call" in json.loads(out.stdout)["error"]  # no key enumeration (review #175)


def test_tokens_surfaces_a_stale_bundle_note_at_the_top_of_the_css(tmp_path):
    p = tmp_path / "brand_package.json"
    p.write_text(json.dumps(_response(local_package_current=False, local_version="2020.01",
                                      notes=["Brand package mismatch: yours is 2020.01, ours is 2021.02."])))
    out = _run("tokens", str(p))
    assert out.returncode == 0
    assert "Brand package mismatch" in out.stdout.splitlines()[0] or "mismatch" in out.stdout[:400].lower()


def test_call_prints_the_exact_tool_call_to_make():
    out = _run("call")
    assert out.returncode == 0
    d = json.loads(out.stdout)
    assert d["tool"] == "pull_brand_package"
    assert d["arguments"] == {"local_version": json.loads((SKILL / "brand-colors.json").read_text())["version"]}
    assert d["save_as"] == "brand_package.json"


def test_skill_md_drives_the_gate_command_and_names_the_tool_call_first():
    text = (SKILL / "SKILL.md").read_text()
    assert "brand.py call" in text and "brand.py tokens brand_package.json" in text
    fm = text.split("---")[1]
    desc = [l for l in fm.splitlines() if l.startswith("description:")][0]
    # the router contract (G12) names the tool call before it advertises the bundled assets
    assert desc.index("pull_brand_package") < desc.index("bundle")
    assert "without asking the broker for files" not in desc


# --- review round 1 (PR #175) -------------------------------------------------

def test_tokens_unwraps_the_raw_tool_result_the_session_saves_verbatim(tmp_path):
    # the MCP client hands the session {content:[{type:"text", text:"<json>"}]}
    wrapped = {"content": [{"type": "text", "text": json.dumps(_response())}]}
    p = tmp_path / "brand_package.json"
    p.write_text(json.dumps(wrapped))
    out = _run("tokens", str(p))
    assert out.returncode == 0, out.stdout
    assert "--lee-red: #98002E" in out.stdout


def test_tokens_unwraps_a_bare_json_string(tmp_path):
    p = tmp_path / "brand_package.json"
    p.write_text(json.dumps(json.dumps(_response())))
    out = _run("tokens", str(p))
    assert out.returncode == 0, out.stdout


def test_refusal_does_not_enumerate_the_missing_keys():
    out = _run("tokens", str(SKILL / "brand-colors.json"))
    err = json.loads(out.stdout)["error"]
    for key in ("token_count", "usage_rules", "brand_version"):
        assert key not in err
    assert "brand.py call" in err


def test_tokens_requires_the_four_primary_colors(tmp_path):
    r = _response()
    r["colors"] = {"accent": {"merlot": "#4E131E"}}
    r["token_count"] = 1
    p = tmp_path / "brand_package.json"
    p.write_text(json.dumps(r))
    out = _run("tokens", str(p))
    assert out.returncode != 0


def test_css_names_and_type_variables(tmp_path):
    p = tmp_path / "brand_package.json"
    p.write_text(json.dumps(_response()))
    css = _run("tokens", str(p)).stdout
    assert "--lee-bright-red: #CD1442" in css
    assert "--lee-sans:" in css and "--lee-serif:" in css
    assert "never ." not in css


def test_empty_prohibited_list_does_not_print_a_dangling_never(tmp_path):
    r = _response(); r["logo"]["prohibited"] = []
    p = tmp_path / "brand_package.json"; p.write_text(json.dumps(r))
    css = _run("tokens", str(p)).stdout
    assert "never ." not in css


def test_mismatch_note_is_the_first_line(tmp_path):
    p = tmp_path / "brand_package.json"
    p.write_text(json.dumps(_response(local_package_current=False, local_version="2020.01",
                                      notes=["Brand package mismatch: yours is 2020.01, ours is 2021.02."])))
    assert "Brand package mismatch" in _run("tokens", str(p)).stdout.splitlines()[0]


def test_tokens_without_an_argument_prints_json_and_fails():
    out = _run("tokens")
    assert out.returncode != 0 and "error" in json.loads(out.stdout)


def test_skill_md_no_longer_ships_a_paste_ready_stylesheet_from_bundled_files():
    text = (SKILL / "SKILL.md").read_text()
    assert "src:url('fonts/AvenirNextCyr-Regular.woff')" not in text
    assert "brand.py call" in text.split("## Edge case")[1]  # the Claude Design path uses the gate too
    assert "this skill's folder" in text or "absolute path" in text
