"""
Lee branding skill asset contract (gi-plugins#118).

The lee-branding skill bundles Lee's official brand package so a broker can apply
Lee branding to a deliverable (or set up the Lee design system in Claude Design)
without hand-feeding the zip. These tests lock the bundle: every asset present,
the color tokens parse with the canonical Lee Red, and the bundled logo is
byte-identical to the logo the Worker serves at /lee_logo.png (one brand, one
logo -- no drift). Assets are BUNDLED, not fetched, because the Cowork sandbox
has no outbound HTTPS (gotcha registry G17).
"""

import hashlib
import json
import os

SKILL_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "skills",
    "lee-branding",
)
_SKILLS_ROOT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "skills"
)
INTERNAL_COMPS_LOGO = os.path.join(_SKILLS_ROOT, "internal-comps", "lee_logo.png")
EXTERNAL_COMPS_LOGO = os.path.join(_SKILLS_ROOT, "external-comps", "lee_logo.png")
LEE_RED = "#98002E"  # PMS 202, canonical (lee-and-associates#28)
FONT_FILES = [
    "AvenirNextCyr-Regular.woff",
    "AvenirNextCyr-Italic.woff",
    "AvenirNextCyr-Medium.woff",
    "AvenirNextCyr-MediumItalic.woff",
    "AvenirNextCyr-Bold.woff",
]


def _md5(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def test_core_assets_present():
    for name in [
        "SKILL.md",
        "brand-colors.json",
        "lee_logo.png",
        "lee_logo.svg",
        "lee-associates-brand-guidelines.md",
        "claude-design-setup.md",
    ]:
        assert os.path.isfile(os.path.join(SKILL_DIR, name)), f"missing {name}"


def test_all_five_fonts_present():
    for name in FONT_FILES:
        p = os.path.join(SKILL_DIR, "fonts", name)
        assert os.path.isfile(p), f"missing font {name}"
    assert os.path.isfile(os.path.join(SKILL_DIR, "fonts", "README.md"))


def test_colors_json_parses_with_canonical_red():
    with open(os.path.join(SKILL_DIR, "brand-colors.json")) as f:
        colors = json.load(f)
    assert colors["primary"]["red"]["hex"].upper() == LEE_RED


def test_bundled_logo_matches_every_in_session_copy():
    # One brand, one logo: this skill is the canonical on-disk home, and every
    # in-session skill that renders a Lee deliverable bundles its own byte-identical
    # copy (the sandbox can't fetch it at runtime). Guard against any copy drifting.
    # (The Worker's served logo lives in the separate lee-and-associates repo and is
    # not reachable from here; this locks the gi-plugins copies to each other.)
    canonical = _md5(os.path.join(SKILL_DIR, "lee_logo.png"))
    assert canonical == _md5(INTERNAL_COMPS_LOGO)
    assert canonical == _md5(EXTERNAL_COMPS_LOGO)


def test_skill_md_frontmatter_is_broker_vocabulary():
    with open(os.path.join(SKILL_DIR, "SKILL.md")) as f:
        text = f.read()
    assert text.startswith("---\n"), "SKILL.md must open with YAML frontmatter"
    fm = text.split("---\n", 2)[1].lower()
    assert "name: lee-branding" in fm
    # description present, broker-facing, mentions the want in broker terms
    assert "description:" in fm
    assert "brand" in fm and "logo" in fm
    # no developer/router jargon leaking into the router contract
    for jargon in ["helpers.py", "worker", "d1", "mcp tool", "esbuild"]:
        assert jargon not in fm, f"remove dev jargon from description: {jargon}"


def test_description_leads_with_applying_the_brand_not_claude_design():
    # #118 4a course-correction: the primary path is applying the brand to a
    # deliverable in-session; the Claude Design setup is the marketing-team edge
    # case. Lock the router so it fires on broker riffs ("make this on-brand")
    # and doesn't regress to leading with Claude Design.
    with open(os.path.join(SKILL_DIR, "SKILL.md")) as f:
        fm = f.read().split("---\n", 2)[1].lower()
    assert "on-brand" in fm, "description should route broker 'on-brand' riffs"
    # If Claude Design is mentioned at all, it must come after the apply-the-brand
    # lead, not open the description.
    if "claude design" in fm:
        assert fm.index("on-brand") < fm.index(
            "claude design"
        ), "lead with applying the brand, demote Claude Design to later in the description"
