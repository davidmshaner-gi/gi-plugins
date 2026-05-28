"""Test fixture: a helpers module whose capabilities match SKILL.md exactly."""

SUPPORTED_TXN_TYPES = ("sale", "lease")


def validate(validated: dict) -> None:
    if validated.get("transaction_type") not in SUPPORTED_TXN_TYPES:
        raise ValueError("transaction_type must be one of: sale, lease")


def build_sql(validated: dict) -> str:
    is_sale = validated["transaction_type"] == "sale"
    view = "example_sale_safe" if is_sale else "example_lease_safe"
    return f"SELECT * FROM {view}"
