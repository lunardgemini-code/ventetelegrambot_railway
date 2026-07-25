"""Product warm cache preloader for instant catalog views."""

from __future__ import annotations

import asyncio
import logging
import time

from database.models import (
    get_all_products,
    get_product_full_details,
    get_all_stock_counts,
)
from services.runtime_metrics import record_cache_access

logger = logging.getLogger(__name__)

_WARM_PRELOAD_COMPLETED: bool = False
_LAST_PRELOAD_TIME: float = 0.0


async def preload_active_products(limit: int = 15) -> int:
    """Preload top active product details into in-memory hot cache."""
    global _WARM_PRELOAD_COMPLETED, _LAST_PRELOAD_TIME
    start_time = time.monotonic()
    try:
        products = await get_all_products()
        active = [
            p for p in products
            if p.get("is_active", 1)
        ][:limit]

        if not active:
            return 0

        # Load all stock counts once
        await get_all_stock_counts()

        # Concurrently warm up product full details
        tasks = [get_product_full_details(p["id"]) for p in active]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        warmed = sum(1 for r in results if not isinstance(r, Exception))

        _WARM_PRELOAD_COMPLETED = True
        _LAST_PRELOAD_TIME = time.monotonic()
        elapsed_ms = round((_LAST_PRELOAD_TIME - start_time) * 1000, 1)
        record_cache_access("product_warm_preload", hit=True)
        logger.info("Warmed up %d/%d active product caches in %sms", warmed, len(active), elapsed_ms)
        return warmed
    except Exception as exc:
        logger.warning("Product warm preload failed: %s", exc)
        return 0


def is_warm_preload_ready() -> bool:
    return _WARM_PRELOAD_COMPLETED
