"""Digital stock delivery service."""

from __future__ import annotations

import logging

from database.models import get_stock_count, reserve_stock_items_for_order
from config import LOW_STOCK_THRESHOLD

logger = logging.getLogger(__name__)


async def deliver_order(order_id: int, product_id: int) -> list[dict] | None:
    """Deliver FIFO stock items for an order in one database transaction."""
    stock_items = await reserve_stock_items_for_order(order_id, product_id)
    if not stock_items:
        logger.warning(
            "Delivery failed: insufficient stock or missing order for product %d (order %d)",
            product_id,
            order_id,
        )
        return None

    logger.info(
        "Order %d delivered: %d item(s) for product %d",
        order_id,
        len(stock_items),
        product_id,
    )
    return stock_items


async def check_low_stock(product_id: int) -> bool:
    """Return True when the product stock is below the configured alert threshold."""
    count = await get_stock_count(product_id)
    return count < LOW_STOCK_THRESHOLD
