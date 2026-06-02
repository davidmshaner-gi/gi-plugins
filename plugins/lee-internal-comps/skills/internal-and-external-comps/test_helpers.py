from helpers import load_sibling


def test_load_sibling_imports_internal_and_external():
    internal = load_sibling("internal-comps")
    external = load_sibling("external-comps")
    assert hasattr(internal, "validate_request")
    assert hasattr(internal, "build_sql")
    assert hasattr(external, "validate_request")
    assert hasattr(external, "build_mcp_params")
