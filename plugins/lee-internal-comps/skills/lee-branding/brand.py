#!/usr/bin/env python3
"""
brand.py — the lee-branding render gate (gi-plugins#169).

Two commands, no dependencies beyond the standard library:

  python3 brand.py call
      Prints the exact pull_brand_package call to make (tool, arguments, and the
      filename to save the response under). Run this first, every render.

  python3 brand.py tokens brand_package.json
      Validates that the file is a pull_brand_package RESPONSE and prints the CSS the
      render uses: the :root color variables, the gradient, the type stacks, the
      @font-face block for the bundled WOFFs, the logo path, and the usage rules as
      comments. It REFUSES the bundled brand-colors.json (and anything else that is not
      the tool's response), so a deliverable cannot be composed from local files alone.

Why a command and not a sentence: on 2026-09-03 two Sonnet sessions rendered Lee flyers
with zero pull_brand_package rows while the connector was on. The instruction was prose;
prose gets read as description (gotcha registry G33). The values the HTML needs now come
out of this command, and this command only accepts what the tool returned.
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLED = os.path.join(HERE, "brand-colors.json")
SAVE_AS = "brand_package.json"

# Fields only the Worker's response carries. The bundled brand-colors.json has none of
# these (its color entries are {hex, pms, rgb, cmyk} objects, it carries no
# brand_version / token_count / usage_rules / logo / notes), which is what lets the gate
# tell the two apart without a shared secret.
REQUIRED = ("brand_version", "local_package_current", "colors", "usage_rules", "logo", "token_count", "notes")

FONT_FACES = [
    ("Avenir Next", 400, "normal", "AvenirNextCyr-Regular.woff"),
    ("Avenir Next", 400, "italic", "AvenirNextCyr-Italic.woff"),
    ("Avenir Next", 500, "normal", "AvenirNextCyr-Medium.woff"),
    ("Avenir Next", 500, "italic", "AvenirNextCyr-MediumItalic.woff"),
    ("Avenir Next", 700, "normal", "AvenirNextCyr-Bold.woff"),
    ("Minion Pro", 400, "normal", "MinionPro-Regular.woff"),
    ("Minion Pro", 400, "italic", "MinionPro-It.woff"),
    ("Minion Pro", 500, "normal", "MinionPro-Medium.woff"),
    ("Minion Pro", 500, "italic", "MinionPro-MediumIt.woff"),
    ("Minion Pro", 600, "normal", "MinionPro-Semibold.woff"),
    ("Minion Pro", 600, "italic", "MinionPro-SemiboldIt.woff"),
    ("Minion Pro", 700, "normal", "MinionPro-Bold.woff"),
    ("Minion Pro", 700, "italic", "MinionPro-BoldIt.woff"),
]


class NotAToolResponse(ValueError):
    pass


def _fail(msg: str) -> int:
    print(json.dumps({"ok": False, "error": msg}))
    return 1


def bundled_version() -> str:
    with open(BUNDLED) as fh:
        return json.load(fh)["version"]


def validate_response(payload: Any) -> dict:
    """Return the payload if it is a pull_brand_package response; raise otherwise."""
    if not isinstance(payload, dict):
        raise NotAToolResponse("the file is not a JSON object")
    missing = [k for k in REQUIRED if k not in payload]
    if "version" in payload and "brand_version" not in payload:
        raise NotAToolResponse(
            "this is the bundled brand-colors.json (it has `version`, not `brand_version`), "
            "not a pull_brand_package response. Call the tool first (python3 brand.py call), "
            f"save its response as {SAVE_AS}, and pass that file."
        )
    if missing:
        raise NotAToolResponse(
            "not a pull_brand_package response: missing " + ", ".join(missing) +
            ". Only the tool's response carries these; the bundled files cannot feed this command. "
            "Call the tool first (python3 brand.py call)."
        )
    colors = payload["colors"]
    if not isinstance(colors, dict) or not colors:
        raise NotAToolResponse("colors must be a non-empty object of color groups")
    n = 0
    for group, entries in colors.items():
        if not isinstance(entries, dict):
            raise NotAToolResponse(f"colors.{group} must be an object of name -> hex")
        for name, hexv in entries.items():
            if not (isinstance(hexv, str) and hexv.startswith("#") and len(hexv) in (4, 7)):
                raise NotAToolResponse(
                    f"colors.{group}.{name} is {hexv!r}, not a hex string; the bundled file's "
                    "{hex, pms, rgb, cmyk} objects are not the tool's shape"
                )
            n += 1
    if payload["token_count"] != n:
        raise NotAToolResponse(
            f"token_count {payload['token_count']} does not match the {n} colors in the payload; "
            "this is not the response the Worker sent"
        )
    if not isinstance(payload["usage_rules"], dict) or not payload["usage_rules"]:
        raise NotAToolResponse("usage_rules is empty; not the tool's response")
    if not isinstance(payload["notes"], list):
        raise NotAToolResponse("notes must be a list")
    return payload


def render_css(payload: dict) -> str:
    out: list[str] = []
    if payload.get("local_package_current") is False or payload.get("notes"):
        for note in payload.get("notes") or ["Brand package mismatch: render from these values and tell your GI contact."]:
            out.append(f"/* NOTE FROM pull_brand_package: {note} */")
    out.append(f"/* Lee & Associates brand, served by pull_brand_package (brand_version {payload['brand_version']}). */")
    out.append("/* Render from THESE values. usage_rules (constraints, not notes): */")
    for k, v in payload["usage_rules"].items():
        out.append(f"/*   {k}: {v} */")
    logo = payload.get("logo") or {}
    out.append(
        f"/* logo: lee_logo.svg (or lee_logo.png); min width {logo.get('min_width_in', 1.125)} in; "
        f"clear space {logo.get('clear_space', 'equal to the height of the icon on all sides')}; "
        f"never {', '.join(logo.get('prohibited', []))}. Must appear at least once. */"
    )
    out.append("")
    for face, weight, style, fname in FONT_FACES:
        out.append(
            f"@font-face {{ font-family:'{face}'; font-weight:{weight}; font-style:{style}; "
            f"src:url('{os.path.join(HERE, 'fonts', fname)}') format('woff'); }}"
        )
    out.append("")
    out.append(":root {")
    for group, entries in payload["colors"].items():
        for name, hexv in entries.items():
            out.append(f"  --lee-{name.replace('_', '-')}: {hexv};")
    grad = (payload.get("gradient") or {}).get("css")
    if grad:
        out.append(f"  --lee-gradient: {grad};")
    typ = payload.get("type") or {}
    out.append(f"  --sans: {typ.get('stack_sans', chr(39) + 'Avenir Next' + chr(39) + ', ' + chr(39) + 'Nunito Sans' + chr(39) + ', Arial, Tahoma, sans-serif')};")
    out.append(f"  --serif: {typ.get('stack_serif', chr(39) + 'Minion Pro' + chr(39) + ', Georgia, serif')};")
    out.append("}")
    out.append("body { font-family: var(--sans); color: var(--lee-charcoal); background: var(--lee-white); }")
    out.append(f"/* logo file: {os.path.join(HERE, 'lee_logo.svg')} */")
    tagline = payload.get("tagline")
    if tagline:
        out.append(f"/* tagline: {tagline} */")
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
    if not argv or argv[0] not in ("call", "tokens"):
        print("usage: python3 brand.py call | python3 brand.py tokens brand_package.json", file=sys.stderr)
        return 2
    if argv[0] == "call":
        print(json.dumps({
            "tool": "pull_brand_package",
            "connector": "lee-raleigh",
            "arguments": {"local_version": bundled_version()},
            "save_as": SAVE_AS,
            "then": f"python3 brand.py tokens {SAVE_AS}",
        }, indent=2))
        return 0
    if len(argv) < 2:
        return _fail(f"usage: python3 brand.py tokens {SAVE_AS}")
    path = argv[1]
    try:
        with open(path) as fh:
            payload = json.load(fh)
    except Exception as e:
        return _fail(f"could not read {path}: {e}. Save the pull_brand_package response as {SAVE_AS} first.")
    try:
        payload = validate_response(payload)
    except NotAToolResponse as e:
        return _fail(str(e))
    sys.stdout.write(render_css(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
