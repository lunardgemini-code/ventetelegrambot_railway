"""Periodic and on-demand synchronization for external supplier catalogs."""

from __future__ import annotations

import asyncio
import logging
import random
import time

from database.suppliers import (
    get_supplier_mapping_by_local_product,
    get_supplier_product_by_local_product,
    get_supplier_units_per_usd,
    supplier_available_stock,
    sync_supplier_products,
)
from database.db import get_db
from services.supplier_api import SupplierAPIError
from services.supplier_registry import (
    get_supplier_balance,
    is_supplier_configured,
    list_supplier_products,
    list_supplier_providers,
)


logger = logging.getLogger(__name__)

_SYNC_LOCKS: dict[str, asyncio.Lock] = {}
_LAST_SUCCESSFUL_SYNC: dict[str, float] = {}
_LAST_FULL_SYNC: dict[str, float] = {}
_LAST_SYNC_RESULTS: dict[str, dict] = {}


def _sync_lock(supplier_code: str) -> asyncio.Lock:
    code = str(supplier_code or "").strip().lower()
    lock = _SYNC_LOCKS.get(code)
    if lock is None:
        lock = asyncio.Lock()
        _SYNC_LOCKS[code] = lock
    return lock


async def sync_supplier_catalog(
    supplier_code: str,
    *,
    min_interval_seconds: float = 0,
    refresh_balance: bool = False,
    refresh_disabled: bool = True,
) -> dict:
    """Refresh one supplier without duplicating concurrent outbound requests."""
    code = str(supplier_code or "").strip().lower()
    if not is_supplier_configured(code):
        return {"supplier_code": code, "status": "not_configured", "synced": 0}

    async with _sync_lock(code):
        now = time.monotonic()
        last_sync = _LAST_SUCCESSFUL_SYNC.get(code, 0.0)
        if last_sync and now - last_sync < max(0.0, float(min_interval_seconds)):
            return dict(_LAST_SYNC_RESULTS[code])

        units_per_usd = await get_supplier_units_per_usd(code)
        products = await list_supplier_products(code, units_per_usd=units_per_usd)
        if not products:
            raise SupplierAPIError(
                f"{code} returned an empty catalog; cached stock was preserved",
                retryable=True,
            )

        if refresh_disabled:
            result = await sync_supplier_products(products, code)
        else:
            result = await sync_supplier_products(
                products,
                code,
                refresh_disabled=False,
            )
        if refresh_balance:
            balance = await get_supplier_balance(
                code,
                units_per_usd=units_per_usd,
                force=True,
            )
            if balance.get("stale"):
                raise SupplierAPIError(
                    f"{code} wallet balance could not be refreshed",
                    retryable=True,
                )

        normalized = {**result, "status": "synced"}
        _LAST_SUCCESSFUL_SYNC[code] = time.monotonic()
        if refresh_disabled:
            _LAST_FULL_SYNC[code] = _LAST_SUCCESSFUL_SYNC[code]
        _LAST_SYNC_RESULTS[code] = normalized
        return dict(normalized)


async def refresh_supplier_product_stock(
    local_product_id: int,
    *,
    min_interval_seconds: float = 3,
    reservation_order_id: int | None = None,
) -> int | None:
    """Return fresh purchasable stock, or None for a non-supplier product."""
    mapping = await get_supplier_mapping_by_local_product(local_product_id)
    if not mapping:
        return None
    if not bool(mapping.get("enabled")):
        return 0

    supplier_code = str(mapping.get("supplier_code") or "canboso")
    await sync_supplier_catalog(
        supplier_code,
        min_interval_seconds=min_interval_seconds,
        refresh_balance=True,
        refresh_disabled=False,
    )
    refreshed = await get_supplier_product_by_local_product(local_product_id)
    if not refreshed:
        return 0
    available = await supplier_available_stock(refreshed)

    db = await get_db()
    try:
        if reservation_order_id is None:
            cursor = await db.execute(
                """SELECT COALESCE(SUM(quantity), 0) AS reserved
                   FROM orders
                   WHERE product_id = ?
                     AND status IN ('PENDING', 'AWAITING_PAYMENT', 'PROCESSING')
                     AND created_at >= datetime('now', '-300 seconds')""",
                (int(local_product_id),),
            )
        else:
            # Earlier orders keep priority. A later pending order must not make
            # an already-reserved checkout reject its own stock.
            cursor = await db.execute(
                """SELECT COALESCE(SUM(quantity), 0) AS reserved
                   FROM orders
                   WHERE product_id = ?
                     AND id < ?
                     AND status IN ('PENDING', 'AWAITING_PAYMENT', 'PROCESSING')
                     AND created_at >= datetime('now', '-300 seconds')""",
                (int(local_product_id), int(reservation_order_id)),
            )
        row = await cursor.fetchone()
        reserved = int(row["reserved"] or 0) if row else 0
    finally:
        await db.close()
    return max(0, int(available) - reserved)


async def supplier_catalog_sync_worker(
    interval_seconds: int = 90,
    full_interval_seconds: int = 1800,
) -> None:
    """Continuously refresh configured supplier catalogs."""
    interval = max(60, int(interval_seconds))
    full_interval = max(interval, int(full_interval_seconds))
    while True:
        try:
            providers = [
                provider
                for provider in list_supplier_providers()
                if is_supplier_configured(str(provider["code"]))
            ]
            for index, provider in enumerate(providers):
                code = str(provider["code"])
                try:
                    last_full_sync = _LAST_FULL_SYNC.get(code, 0.0)
                    refresh_disabled = (
                        not last_full_sync
                        or time.monotonic() - last_full_sync >= full_interval
                    )
                    result = await sync_supplier_catalog(
                        code,
                        min_interval_seconds=max(1, interval - 5),
                        refresh_disabled=refresh_disabled,
                    )
                    log = logger.info if (
                        result.get("scope") == "full"
                        or int(result.get("changed") or 0) > 0
                        or int(result.get("zeroed") or 0) > 0
                    ) else logger.debug
                    log(
                        "Supplier catalog synchronized: %s scope=%s "
                        "received=%d compared=%d changed=%d zeroed=%d "
                        "skipped=%d transaction_ms=%.1f",
                        code,
                        result.get("scope", "unknown"),
                        int(result.get("synced") or 0),
                        int(result.get("compared") or 0),
                        int(result.get("changed") or 0),
                        int(result.get("zeroed") or 0),
                        int(result.get("skipped_disabled") or 0),
                        float(result.get("transaction_ms") or 0),
                    )
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    logger.warning("Supplier catalog sync failed for %s: %s", code, exc)
                if index < len(providers) - 1:
                    await asyncio.sleep(random.uniform(1.0, 3.0))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Supplier catalog synchronization cycle failed: %s", exc)
        await asyncio.sleep(interval)


def reset_supplier_sync_state() -> None:
    """Reset process-local state for tests and clean restarts."""
    _SYNC_LOCKS.clear()
    _LAST_SUCCESSFUL_SYNC.clear()
    _LAST_FULL_SYNC.clear()
    _LAST_SYNC_RESULTS.clear()


__all__ = [
    "refresh_supplier_product_stock",
    "reset_supplier_sync_state",
    "supplier_catalog_sync_worker",
    "sync_supplier_catalog",
]
