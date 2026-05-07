"""
helpers.py — atomic helpers for the external-comps skill.

Run in the Cowork sandbox. The model orchestrates; helpers are deterministic.
None of these helpers call MCP tools or drive the browser — Chrome bridging
is the model's responsibility (the model has bridge access; the sandbox does not).

Design contract:
  - Open-shaped dicts in / dicts out. Helpers tolerate extra keys.
  - Three load-bearing keys on the request: comp_type, property_type, location.
  - Row schema mirrors Dealius `lease_comps_safe`/`sale_comps_safe` columns
    plus `source` + provenance + `corrections: []` for the future audit seam.
"""
