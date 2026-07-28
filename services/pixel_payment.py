"""Pixel Gemini Points Payment & Top-Up Service.

Handles top-ups of Pixel Points using internal Wallet balance, Binance Pay,
and Crypto Pay (NOWPayments/CryptoBot).
"""

import logging
from database.db import get_db
from database.models import (
    get_user_pixel_points,
    add_user_pixel_points,
    deduct_user_pixel_points,
    get_pixel_point_packs,
    get_pixel_settings,
)

logger = logging.getLogger(__name__)


async def topup_pixel_points_via_wallet(user_id: int, pack_id: int) -> dict:
    """Purchase a Pixel Point Pack using internal Wallet USD balance."""
    try:
        packs = await get_pixel_point_packs()
        pack = next((p for p in packs if p["id"] == pack_id and p.get("is_active", 1)), None)
        if not pack:
            return {"success": False, "error": "pack_not_found"}

        cost_usd = float(pack["price_usd"])
        points_to_add = float(pack["points"])

        db = await get_db()
        cursor = await db.execute("SELECT wallet_balance FROM users WHERE telegram_id = ?", (int(user_id),))
        row = await cursor.fetchone()
        if not row or row[0] is None or float(row[0]) < cost_usd:
            return {"success": False, "error": "insufficient_wallet", "cost_usd": cost_usd, "current_balance": float(row[0] or 0)}

        # Deduct wallet balance
        await db.execute(
            "UPDATE users SET wallet_balance = wallet_balance - ? WHERE telegram_id = ?",
            (cost_usd, int(user_id))
        )
        cursor = await db.execute("SELECT wallet_balance FROM users WHERE telegram_id = ?", (int(user_id),))
        new_wallet_bal = float((await cursor.fetchone())[0] or 0)

        # Record wallet transaction
        await db.execute(
            """
            INSERT INTO wallet_transactions (user_telegram_id, type, amount, balance_after, description)
            VALUES (?, 'debit', ?, ?, ?)
            """,
            (int(user_id), -cost_usd, new_wallet_bal, f"Achat de Pack {points_to_add} Points Pixel Gemini")
        )
        await db.commit()

        # Credit Pixel Points
        new_points_balance = await add_user_pixel_points(
            user_id=user_id,
            points=points_to_add,
            usd_cost=cost_usd,
            transaction_type="topup_wallet",
            ref_id=f"pack_{pack_id}"
        )

        return {
            "success": True,
            "points_added": points_to_add,
            "cost_usd": cost_usd,
            "new_points_balance": new_points_balance,
        }
    except Exception as exc:
        logger.error("Failed wallet topup for user %s, pack %s: %s", user_id, pack_id, exc, exc_info=True)
        return {"success": False, "error": str(exc)}
