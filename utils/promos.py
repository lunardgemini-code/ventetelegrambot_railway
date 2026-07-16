from __future__ import annotations

import math


PROMO_DISCOUNT_TYPES = {"percent", "fixed", "product_price"}


def parse_applicable_product_ids(value: object) -> list[int]:
    """Return unique positive product IDs while preserving their order."""
    if value is None:
        return []
    if isinstance(value, str):
        raw_values = value.split(",")
    elif isinstance(value, (list, tuple, set)):
        raw_values = value
    else:
        raw_values = [value]

    product_ids: list[int] = []
    for raw in raw_values:
        try:
            product_id = int(str(raw).strip())
        except (TypeError, ValueError):
            continue
        if product_id > 0 and product_id not in product_ids:
            product_ids.append(product_id)
    return product_ids


def calculate_promo_price(
    original_amount: float,
    quantity: int,
    discount_type: str,
    discount_value: float,
) -> tuple[float, float]:
    """Return ``(discount, final_amount)`` without ever increasing the order total."""
    amount = float(original_amount)
    value = float(discount_value)
    if not math.isfinite(amount) or not math.isfinite(value):
        raise ValueError("Promo amounts must be finite numbers")
    amount = max(amount, 0.0)
    value = max(value, 0.0)
    qty = max(int(quantity or 1), 1)

    if discount_type == "percent":
        discount = amount * min(value, 100.0) / 100.0
    elif discount_type == "fixed":
        discount = value
    elif discount_type == "product_price":
        target_total = value * qty
        discount = max(amount - target_total, 0.0)
    else:
        raise ValueError(f"Unsupported promo discount type: {discount_type}")

    discount = min(max(discount, 0.0), amount)
    final_amount = max(amount - discount, 0.0)
    return round(discount, 8), round(final_amount, 8)
