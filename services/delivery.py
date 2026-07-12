"""Digital stock delivery service."""

from __future__ import annotations

import logging

from database.models import get_stock_count, reserve_stock_items_for_order
from config import LOW_STOCK_THRESHOLD

logger = logging.getLogger(__name__)


async def deliver_order(order_id: int, product_id: int) -> list[dict] | None:
    """Deliver FIFO stock items for an order in one database transaction."""
    from database.models import get_order
    from database.suppliers import (
        claim_supplier_order,
        decoded_supplier_items,
        fail_supplier_order,
        finish_supplier_order,
        get_supplier_product_by_local_product,
    )

    mapping = await get_supplier_product_by_local_product(product_id)
    if mapping:
        from services.supplier_api import SupplierAPIError, purchase_canboso_product

        order = await get_order(order_id)
        if not order:
            return None
        quantity = max(1, int(order.get("quantity") or 1))
        supplier_order = await claim_supplier_order(order_id, mapping, quantity)
        if not supplier_order.get("claimed"):
            if supplier_order.get("status") == "completed":
                return decoded_supplier_items(supplier_order)
            logger.warning("Supplier order %s is already %s", order_id, supplier_order.get("status"))
            return None
        try:
            result = await purchase_canboso_product(mapping["external_product_id"], quantity)
            items = await finish_supplier_order(int(supplier_order["id"]), result)
            logger.info("Supplier order %d delivered %d item(s)", order_id, len(items))
            return items
        except SupplierAPIError as exc:
            await fail_supplier_order(
                int(supplier_order["id"]),
                str(exc),
                unknown=bool(exc.outcome_unknown),
            )
            logger.error("Supplier delivery failed for order %d: %s", order_id, exc)
            return None

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
