# services/delivery.py — Service de livraison de comptes numériques
# Gère l'attribution FIFO des articles en stock aux commandes payées.

from __future__ import annotations

import logging

from database.models import (
    get_available_stock_items,
    get_order,
    get_stock_count,
    mark_stock_sold,
    set_order_stock,
)
from config import LOW_STOCK_THRESHOLD

logger = logging.getLogger(__name__)


async def deliver_order(order_id: int, product_id: int) -> list[dict] | None:
    """Livre les comptes numériques au client pour une commande donnée (gestion quantité FIFO)."""
    # Récupérer la commande pour connaître la quantité
    order = await get_order(order_id)
    if not order:
        logger.warning("Livraison impossible — commande %d introuvable", order_id)
        return None

    quantity = order.get("quantity", 1)

    # Récupérer les articles non vendus correspondants (FIFO)
    stock_items = await get_available_stock_items(product_id, quantity)

    if len(stock_items) < quantity:
        logger.warning(
            "Livraison impossible — stock insuffisant (%d disponible(s) sur %d demandé(s)) pour le produit %d "
            "(commande %d)",
            len(stock_items),
            quantity,
            product_id,
            order_id,
        )
        return None

    # Marquer les articles comme vendus (atomique — vérifie is_sold = 0)
    delivered_items = []
    for item in stock_items:
        if await mark_stock_sold(item["id"], order_id):
            delivered_items.append(item)
        else:
            logger.warning(
                "Stock item %d already sold (race condition prevented) for order %d",
                item["id"], order_id,
            )

    if len(delivered_items) < quantity:
        logger.warning(
            "Partial delivery for order %d: %d/%d items (some were already sold). Rolling back.",
            order_id, len(delivered_items), quantity,
        )
        from database.models import release_stock_item
        for item in delivered_items:
            await release_stock_item(item["id"])
        return None

    stock_items = delivered_items

    # Associer le premier article à la commande pour des raisons de compatibilité schéma
    if stock_items:
        await set_order_stock(order_id, stock_items[0]["id"])

    logger.info(
        "Commande %d livrée — %d article(s) (produit %d)",
        order_id,
        len(stock_items),
        product_id,
    )

    return stock_items


async def check_low_stock(product_id: int) -> bool:
    """Vérifie si le stock d'un produit est en dessous du seuil d'alerte.

    Args:
        product_id: Identifiant du produit à vérifier.

    Returns:
        ``True`` si le stock est inférieur à ``LOW_STOCK_THRESHOLD``.
    """
    count = await get_stock_count(product_id)
    return count < LOW_STOCK_THRESHOLD
