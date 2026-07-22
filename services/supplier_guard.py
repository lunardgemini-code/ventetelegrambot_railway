"""Last-moment supplier checks before an external wallet is charged."""

from __future__ import annotations

import asyncio
from decimal import Decimal, InvalidOperation
import os
import time

from services.supplier_api import SupplierAPIError


_LIVE_OFFER_TTL_SECONDS = max(
    0.25, float(os.environ.get("SUPPLIER_LIVE_OFFER_TTL_SECONDS", "2"))
)
_CATALOG_CACHE: dict[str, tuple[float, list[dict]]] = {}
_CATALOG_LOCKS: dict[str, tuple[asyncio.AbstractEventLoop, asyncio.Lock]] = {}


def _money(value) -> Decimal:
    try:
        result = Decimal(str(value or 0))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0")
    return result if result.is_finite() and result > 0 else Decimal("0")


def _catalog_lock(supplier_code: str) -> asyncio.Lock:
    loop = asyncio.get_running_loop()
    current = _CATALOG_LOCKS.get(supplier_code)
    if current is None or current[0] is not loop:
        lock = asyncio.Lock()
        _CATALOG_LOCKS[supplier_code] = (loop, lock)
        return lock
    return current[1]


async def _fresh_catalog(supplier_code: str) -> list[dict]:
    """Share very recent catalogs across simultaneous checkouts."""
    code = str(supplier_code or "").strip().lower()
    async with _catalog_lock(code):
        now = time.monotonic()
        cached = _CATALOG_CACHE.get(code)
        if cached and now - cached[0] <= _LIVE_OFFER_TTL_SECONDS:
            return cached[1]

        from database.suppliers import get_supplier_units_per_usd
        from services.supplier_registry import list_supplier_products

        units_per_usd = await get_supplier_units_per_usd(code)
        catalog = await list_supplier_products(code, units_per_usd=units_per_usd)
        if not catalog:
            raise SupplierAPIError(
                f"{code} returned an empty catalog before purchase",
                retryable=True,
            )
        _CATALOG_CACHE[code] = (time.monotonic(), catalog)
        return catalog


async def verify_supplier_candidate(
    candidate: dict,
    *,
    quantity: int,
    unit_revenue: float,
) -> dict:
    """Return a live, profitable candidate or fail before the supplier POST."""
    code = str(candidate.get("supplier_code") or "canboso").strip().lower()
    external_id = str(candidate.get("external_product_id") or "")
    wanted = max(1, int(quantity))
    revenue = _money(unit_revenue)
    if not external_id or revenue <= 0:
        raise SupplierAPIError("Supplier route has invalid purchase limits")

    catalog = await _fresh_catalog(code)
    live = next(
        (
            product
            for product in catalog
            if str(product.get("external_product_id") or "") == external_id
        ),
        None,
    )
    if live is None:
        raise SupplierAPIError("Supplier product is no longer available")

    cost = _money(live.get("base_price"))
    stock = max(0, int(live.get("remote_stock") or 0))
    if cost <= 0 or cost >= revenue:
        raise SupplierAPIError("Supplier price is no longer profitable")
    if stock < wanted:
        raise SupplierAPIError("Supplier stock changed before purchase")

    from database.suppliers import get_supplier_units_per_usd
    from services.supplier_registry import get_supplier_balance

    units_per_usd = await get_supplier_units_per_usd(code)
    wallet = await get_supplier_balance(
        code,
        units_per_usd=units_per_usd,
        force=True,
    )
    if bool(wallet.get("stale")) or _money(wallet.get("balance")) < cost * wanted:
        raise SupplierAPIError("Supplier wallet cannot fund this purchase")

    return {
        **candidate,
        "base_price": float(cost),
        "remote_stock": stock,
        "live_checked_at": time.time(),
    }


def reset_supplier_guard_state() -> None:
    _CATALOG_CACHE.clear()
    _CATALOG_LOCKS.clear()


__all__ = ["reset_supplier_guard_state", "verify_supplier_candidate"]
