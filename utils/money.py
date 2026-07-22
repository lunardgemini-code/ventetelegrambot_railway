"""Consistent decimal boundaries for USD values stored as SQLite REAL."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


def usd_decimal(value, *, places: int = 4, allow_zero: bool = True) -> Decimal:
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("INVALID_USD_AMOUNT") from exc
    if not amount.is_finite() or amount < 0 or (not allow_zero and amount == 0):
        raise ValueError("INVALID_USD_AMOUNT")
    quantum = Decimal(1).scaleb(-max(0, min(int(places), 8)))
    return amount.quantize(quantum, rounding=ROUND_HALF_UP)


def usd_float(value, *, places: int = 4, allow_zero: bool = True) -> float:
    return float(usd_decimal(value, places=places, allow_zero=allow_zero))


__all__ = ["usd_decimal", "usd_float"]
