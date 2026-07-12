# database/models.py â€” Fonctions CRUD asynchrones pour toutes les tables
# Chaque fonction ouvre sa propre connexion, exÃ©cute, commit et ferme.

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import secrets
import uuid
import logging
import time
from datetime import datetime, timedelta, timezone

from .db import get_db, is_transient_db_connection_error

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    """Return naive UTC for compatibility with existing SQLite timestamps."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


# â”€â”€ Caches en mÃ©moire pour optimiser la performance (Ã©viter les appels rÃ©seau Turso rÃ©pÃ©titifs) â”€â”€
_USER_LANG_CACHE: dict[int, str] = {}
_USER_BANNED_CACHE: dict[int, bool] = {}
_CATEGORIES_CACHE: list[dict] | None = None
_PRODUCTS_CACHE: list[dict] | None = None
_PRODUCT_BY_ID_CACHE: dict[int, dict | None] = {}
_TIERS_CACHE: dict[int, list[dict]] = {}
_STOCK_COUNTS_CACHE: tuple[float, dict[int, int]] | None = None
_STOCK_COUNTS_CACHE_TTL = 2.0
_SETTINGS_CACHE: dict[str, str | None] = {}
_DEFAULT_BINANCE_ACCOUNT_CACHE: dict | None = None
_DEFAULT_BINANCE_ACCOUNT_LOADED = False
_RESELLER_LAST_USED_TOUCH_CACHE: dict[int, float] = {}
_RESELLER_LAST_USED_TOUCH_INTERVAL = 60.0
_RESELLER_AUTH_CACHE: dict[str, tuple[float, dict]] = {}
_RESELLER_AUTH_CACHE_TTL = 30.0
_GET_STATS_CACHE = {}
_GET_STATS_CACHE_TTL = 30


def _clear_stock_cache() -> None:
    global _STOCK_COUNTS_CACHE
    _STOCK_COUNTS_CACHE = None


def invalidate_stats_cache() -> None:
    """Clear cached dashboard/statistics values after business data changes."""
    _GET_STATS_CACHE.clear()


def _clear_binance_account_cache() -> None:
    global _DEFAULT_BINANCE_ACCOUNT_CACHE, _DEFAULT_BINANCE_ACCOUNT_LOADED
    _DEFAULT_BINANCE_ACCOUNT_CACHE = None
    _DEFAULT_BINANCE_ACCOUNT_LOADED = False


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
# â•‘  UTILISATEURS                                                    â•‘
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


async def get_or_create_user(
    telegram_id: int,
    username: str | None,
    first_name: str,
    referred_by: int | None = None,
) -> dict:
    """Retry the idempotent user upsert when a pooled Turso stream expires."""
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            return await _get_or_create_user_once(
                telegram_id,
                username,
                first_name,
                referred_by=referred_by,
            )
        except Exception as exc:
            last_exc = exc
            if not is_transient_db_connection_error(exc) or attempt == 2:
                raise
            logger.info(
                "Retrying user upsert on a fresh connection after stale Turso stream: %s",
                exc,
            )
    raise RuntimeError("User database operation unavailable") from last_exc


async def _get_or_create_user_once(
    telegram_id: int,
    username: str | None,
    first_name: str,
    referred_by: int | None = None,
) -> dict:
    """RÃ©cupÃ¨re un utilisateur existant ou en crÃ©e un nouveau, en enregistrant le parrain si applicable."""
    db = await get_db(fresh=True)
    try:
        cursor = await db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cursor.fetchone()
        if row:
            # Mettre Ã  jour le nom d'utilisateur et le prÃ©nom s'ils ont changÃ©
            await db.execute(
                "UPDATE users SET username = ?, first_name = ? WHERE telegram_id = ?",
                (username, first_name, telegram_id),
            )
            await db.commit()
            # Build updated dict without a redundant second SELECT
            user_dict = dict(row)
            user_dict["username"] = username
            user_dict["first_name"] = first_name
            _USER_LANG_CACHE[telegram_id] = user_dict.get("language") or "fr"
            _USER_BANNED_CACHE[telegram_id] = bool(user_dict.get("is_banned"))
            return user_dict
        else:
            # Nouveau compte - Valider le parrain
            valid_referrer = None
            if referred_by and int(referred_by) != telegram_id:
                ref_cursor = await db.execute(
                    "SELECT telegram_id FROM users WHERE telegram_id = ?", (int(referred_by),)
                )
                ref_row = await ref_cursor.fetchone()
                if ref_row:
                    valid_referrer = int(referred_by)

            await db.execute(
                "INSERT INTO users (telegram_id, username, first_name, language, referred_by) VALUES (?, ?, ?, NULL, ?)",
                (telegram_id, username, first_name, valid_referrer),
            )
            await db.commit()
            cursor = await db.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            )
            row = await cursor.fetchone()
            user_dict = dict(row)
            _USER_LANG_CACHE[telegram_id] = "fr"
            _USER_BANNED_CACHE[telegram_id] = False
            return user_dict
    finally:
        await db.close()


async def get_user(telegram_id: int) -> dict | None:
    """RÃ©cupÃ¨re un utilisateur par son identifiant Telegram."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cursor.fetchone()
        if row:
            user_dict = dict(row)
            _USER_LANG_CACHE[telegram_id] = user_dict.get("language") or "fr"
            _USER_BANNED_CACHE[telegram_id] = bool(user_dict.get("is_banned"))
            return user_dict
        return None
    finally:
        await db.close()


async def get_all_users() -> list[dict]:
    """Return all users, retrying an expired pooled Turso stream."""
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            return await _get_all_users_once()
        except Exception as exc:
            last_exc = exc
            if not is_transient_db_connection_error(exc) or attempt == 2:
                raise
            logger.info(
                "Retrying broadcast recipient read on a fresh connection: %s",
                exc,
            )
    raise RuntimeError("Broadcast recipient database operation unavailable") from last_exc


async def _get_all_users_once() -> list[dict]:
    """Retourne la liste de tous les utilisateurs enregistrés avec leur nombre de filleuls."""
    db = await get_db()
    try:
        cursor = await db.execute("""
            SELECT u.*, COUNT(f.telegram_id) as referrals_count
            FROM users u
            LEFT JOIN users f ON f.referred_by = u.telegram_id
            GROUP BY u.id
            ORDER BY u.created_at DESC
        """)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_users_paginated(limit: int = 20, offset: int = 0, search: str = "", sort: str = "joined", order: str = "desc") -> tuple[list[dict], int]:
    """Retourne la liste des utilisateurs paginée, filtrée et triée avec le nombre total."""
    db = await get_db()
    try:
        where_clause = ""
        params = []
        if search:
            where_clause = " WHERE CAST(u.telegram_id AS TEXT) LIKE ? OR CAST(u.referred_by AS TEXT) LIKE ? OR u.username LIKE ? OR u.first_name LIKE ?"
            search_param = f"%{search}%"
            params = [search_param, search_param, search_param, search_param]
        
        count_query = f"SELECT COUNT(*) as cnt FROM users u {where_clause}"
        cursor_count = await db.execute(count_query, params)
        row_count = await cursor_count.fetchone()
        total = row_count["cnt"] if row_count else 0

        # Mapping des colonnes pour le tri
        sort_mapping = {
            "telegram_id": "u.telegram_id",
            "username": "LOWER(u.username)",
            "orders": "u.total_orders",
            "spent": "u.total_spent",
            "wallet": "u.wallet_balance",
            "referrals": "referrals_count",
            "joined": "u.created_at",
            "referral_earnings": "u.referral_earnings"
        }
        
        sort_col = sort_mapping.get(sort, "u.created_at")
        order_dir = "ASC" if order.lower() == "asc" else "DESC"

        paginated_query = f"""
            SELECT u.*, COUNT(f.telegram_id) as referrals_count
            FROM users u
            LEFT JOIN users f ON f.referred_by = u.telegram_id
            {where_clause}
            GROUP BY u.id
            ORDER BY {sort_col} {order_dir}, u.created_at DESC
            LIMIT ? OFFSET ?
        """
        params_paginated = params + [limit, offset]
        cursor = await db.execute(paginated_query, params_paginated)
        rows = await cursor.fetchall()
        
        return [dict(r) for r in rows], total
    finally:
        await db.close()


async def get_user_count() -> int:
    """Retourne le nombre total d'utilisateurs."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM users")
        row = await cursor.fetchone()
        return row["cnt"]
    finally:
        await db.close()


def clear_products_cache():
    global _PRODUCTS_CACHE, _PRODUCT_BY_ID_CACHE
    _PRODUCTS_CACHE = None
    _PRODUCT_BY_ID_CACHE.clear()
    invalidate_stats_cache()

async def get_user_lang(telegram_id: int) -> str:
    """Retourne la langue prÃ©fÃ©rÃ©e de l'utilisateur (par dÃ©faut 'fr')."""
    if telegram_id in _USER_LANG_CACHE:
        return _USER_LANG_CACHE[telegram_id]
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT language FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cursor.fetchone()
        lang = row["language"] if row and row["language"] else "fr"
        _USER_LANG_CACHE[telegram_id] = lang
        return lang
    finally:
        await db.close()


async def set_user_language(telegram_id: int, language: str) -> None:
    """DÃ©finit la langue prÃ©fÃ©rÃ©e de l'utilisateur."""
    _USER_LANG_CACHE[telegram_id] = language
    db = await get_db()
    try:
        await db.execute(
            "UPDATE users SET language = ? WHERE telegram_id = ?",
            (language, telegram_id),
        )
        await db.commit()
    finally:
        await db.close()


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
# â•‘  CATÃ‰GORIES                                                      â•‘
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


async def get_categories() -> list[dict]:
    """Retourne les catégories actives, triées par sort_order."""
    global _CATEGORIES_CACHE
    if _CATEGORIES_CACHE is not None:
        return _CATEGORIES_CACHE
    db = await get_db()
    try:
        try:
            cursor = await db.execute(
                "SELECT * FROM categories WHERE is_active = 1 AND is_deleted = 0 ORDER BY sort_order ASC, id ASC"
            )
            rows = await cursor.fetchall()
        except Exception:
            # Fallback if is_deleted column does not exist yet
            cursor = await db.execute(
                "SELECT * FROM categories WHERE is_active = 1 ORDER BY sort_order ASC, id ASC"
            )
            rows = await cursor.fetchall()
        _CATEGORIES_CACHE = [dict(r) for r in rows]
        return _CATEGORIES_CACHE
    finally:
        await db.close()



async def get_category(category_id: int) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM categories WHERE id = ?", (category_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()

async def add_category(
    name: str,
    emoji: str = "📂",
    description: str = "",
) -> int:
    global _CATEGORIES_CACHE
    _CATEGORIES_CACHE = None
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO categories (name, emoji, description) VALUES (?, ?, ?)",
            (name, emoji, description),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()

async def update_category(category_id: int, **kwargs) -> None:
    global _CATEGORIES_CACHE
    _CATEGORIES_CACHE = None
    allowed = {"name", "emoji", "description", "sort_order", "is_active", "is_deleted"}
    safe_kwargs = {k: v for k, v in kwargs.items() if k in allowed}
    if not safe_kwargs:
        return
    columns = ", ".join(f"{k} = ?" for k in safe_kwargs)
    values = list(safe_kwargs.values()) + [category_id]
    db = await get_db()
    try:
        await db.execute(f"UPDATE categories SET {columns} WHERE id = ?", values)
        await db.commit()
    finally:
        await db.close()

async def delete_category(category_id: int) -> None:
    global _CATEGORIES_CACHE
    _CATEGORIES_CACHE = None
    db = await get_db()
    try:
        await db.execute("UPDATE categories SET is_deleted = 1 WHERE id = ?", (category_id,))
        await db.commit()
    finally:
        await db.close()



async def get_product_sales_momentum(days: int = 30) -> dict:
    """Return daily completed sales quantities and revenue per product."""
    days = max(1, min(int(days), 365))
    start_date = (_utcnow() - timedelta(days=days - 1)).date()
    day_labels = [
        (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(days)
    ]
    since_timestamp = f"{day_labels[0]} 00:00:00"
    yesterday = (_utcnow() - timedelta(days=1)).date().strftime("%Y-%m-%d")

    db = await get_db()
    try:
        cursor = await db.execute(
            """
            SELECT
                o.product_id as id,
                p.name,
                p.emoji,
                DATE(o.created_at) as day,
                COALESCE(SUM(CASE WHEN o.quantity IS NULL OR o.quantity < 1 THEN 1 ELSE o.quantity END), 0) as qty_sold,
                COALESCE(SUM(o.amount_usd), 0) as revenue
            FROM orders o
            LEFT JOIN products p ON p.id = o.product_id
            WHERE o.status = 'COMPLETED'
              AND o.product_id IS NOT NULL
              AND o.created_at >= ?
            GROUP BY o.product_id, p.name, p.emoji, DATE(o.created_at)
            ORDER BY day ASC, qty_sold DESC
            """,
            (since_timestamp,),
        )
        rows = await cursor.fetchall()

        products: dict[int, dict] = {}
        day_index = {day: idx for idx, day in enumerate(day_labels)}

        for row in rows:
            product_id = row["id"]
            if product_id is None:
                continue

            product = products.setdefault(
                int(product_id),
                {
                    "id": int(product_id),
                    "name": row["name"] or f"Product #{product_id}",
                    "emoji": row["emoji"] or "📦",
                    "series": [0 for _ in day_labels],
                    "revenue_series": [0.0 for _ in day_labels],
                    "total_sold": 0,
                    "total_revenue": 0.0,
                    "yesterday_sold": 0,
                    "yesterday_revenue": 0.0,
                },
            )

            day = row["day"]
            idx = day_index.get(day)
            if idx is None:
                continue

            qty = int(row["qty_sold"] or 0)
            revenue = float(row["revenue"] or 0)
            product["series"][idx] = qty
            product["revenue_series"][idx] = revenue
            product["total_sold"] += qty
            product["total_revenue"] += revenue
            if day == yesterday:
                product["yesterday_sold"] = qty
                product["yesterday_revenue"] = revenue

        return {
            "days": day_labels,
            "yesterday": yesterday,
            "products": sorted(
                products.values(),
                key=lambda p: (p["total_sold"], p["total_revenue"]),
                reverse=True,
            ),
        }
    finally:
        await db.close()


async def get_stock_forecast(days: int = 7) -> dict[int, dict]:
    """Return recent sales velocity per product for stock runway estimates."""
    days = max(1, min(int(days), 90))
    since = (_utcnow() - timedelta(days=days - 1)).strftime("%Y-%m-%d 00:00:00")
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT product_id,
                      COALESCE(SUM(CASE WHEN quantity IS NULL OR quantity < 1 THEN 1 ELSE quantity END), 0) as sold
               FROM orders
               WHERE status = 'COMPLETED'
                 AND product_id IS NOT NULL
                 AND created_at >= ?
               GROUP BY product_id""",
            (since,),
        )
        rows = await cursor.fetchall()
        result: dict[int, dict] = {}
        for row in rows:
            sold = int(row["sold"] or 0)
            avg_daily = sold / days
            result[int(row["product_id"])] = {
                "sold": sold,
                "avg_daily_sales": avg_daily,
            }
        return result
    finally:
        await db.close()


async def record_product_view(product_id: int, user_telegram_id: int) -> None:
    """Record at most one view per user/product in a six-hour window."""
    try:
        db = await get_db()
    except Exception as exc:
        logger.debug("Could not open DB for product view %s: %s", product_id, exc)
        return
    try:
        await db.execute(
            """INSERT INTO product_views (product_id, user_telegram_id)
               SELECT ?, ?
               WHERE NOT EXISTS (
                   SELECT 1 FROM product_views
                   WHERE product_id = ? AND user_telegram_id = ?
                     AND viewed_at >= datetime('now', '-6 hours')
               )""",
            (int(product_id), int(user_telegram_id), int(product_id), int(user_telegram_id)),
        )
        await db.commit()
    except Exception as exc:
        logger.debug("Could not record product view for product %s: %s", product_id, exc)
    finally:
        try:
            await db.close()
        except Exception:
            pass


async def get_dead_product_alerts(days: int = 7, min_views: int = 10, max_conversion: float = 0.05) -> list[dict]:
    """Products with many views but weak sales conversion."""
    days = max(1, min(int(days), 90))
    min_views = max(1, int(min_views))
    max_conversion = max(0.0, float(max_conversion))
    since = (_utcnow() - timedelta(days=days - 1)).strftime("%Y-%m-%d 00:00:00")
    db = await get_db()
    try:
        cursor = await db.execute(
            """WITH views AS (
                   SELECT product_id, COUNT(*) as view_count
                   FROM product_views
                   WHERE viewed_at >= ?
                   GROUP BY product_id
               ),
               sales AS (
                   SELECT product_id,
                          COALESCE(SUM(CASE WHEN quantity IS NULL OR quantity < 1 THEN 1 ELSE quantity END), 0) as sold_count
                   FROM orders
                   WHERE status = 'COMPLETED'
                     AND product_id IS NOT NULL
                     AND created_at >= ?
                   GROUP BY product_id
               )
               SELECT p.id, p.name, p.emoji,
                      COALESCE(v.view_count, 0) as views,
                      COALESCE(s.sold_count, 0) as sold
               FROM products p
               JOIN views v ON v.product_id = p.id
               LEFT JOIN sales s ON s.product_id = p.id
               WHERE COALESCE(p.is_active, 1) = 1
                 AND COALESCE(p.is_deleted, 0) = 0
                 AND COALESCE(v.view_count, 0) >= ?
               ORDER BY v.view_count DESC""",
            (since, since, min_views),
        )
        rows = await cursor.fetchall()
        alerts = []
        for row in rows:
            views = int(row["views"] or 0)
            sold = int(row["sold"] or 0)
            conversion = (sold / views) if views else 0.0
            if conversion <= max_conversion:
                alerts.append({
                    "id": int(row["id"]),
                    "name": row["name"],
                    "emoji": row["emoji"] or "📦",
                    "views": views,
                    "sold": sold,
                    "conversion": conversion,
                    "days": days,
                })
        return alerts
    except Exception as exc:
        logger.warning("Could not load dead product alerts: %s", exc)
        return []
    finally:
        await db.close()


async def add_product_stock_alert(user_telegram_id: int, product_id: int) -> bool:
    """Subscribe a user to one restock notification. Returns True if newly added."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT id FROM product_stock_alerts
               WHERE product_id = ?
                 AND user_telegram_id = ?
                 AND notified_at IS NULL
               LIMIT 1""",
            (int(product_id), int(user_telegram_id)),
        )
        existing = await cursor.fetchone()
        if existing:
            return False

        try:
            await db.execute(
                """INSERT INTO product_stock_alerts (product_id, user_telegram_id)
                   VALUES (?, ?)""",
                (int(product_id), int(user_telegram_id)),
            )
            await db.commit()
            return True
        except Exception as exc:
            if "UNIQUE" in str(exc).upper():
                try:
                    await db.rollback()
                except Exception:
                    pass
                return False
            raise
    finally:
        await db.close()


async def get_pending_stock_alerts(product_id: int) -> list[dict]:
    """Return users waiting for a restock notification on a product."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT a.product_id, a.user_telegram_id,
                      COALESCE(u.language, 'fr') as language,
                      COALESCE(u.is_banned, 0) as is_banned,
                      u.username, u.first_name
               FROM product_stock_alerts a
               LEFT JOIN users u ON u.telegram_id = a.user_telegram_id
               WHERE a.product_id = ?
                 AND a.notified_at IS NULL""",
            (int(product_id),),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows if not r["is_banned"]]
    finally:
        await db.close()


async def mark_stock_alerts_notified(product_id: int, user_ids: list[int]) -> None:
    if not user_ids:
        return
    placeholders = ",".join("?" for _ in user_ids)
    db = await get_db()
    try:
        await db.execute(
            f"""UPDATE product_stock_alerts
                SET notified_at = CURRENT_TIMESTAMP
                WHERE product_id = ?
                  AND user_telegram_id IN ({placeholders})
                  AND notified_at IS NULL""",
            [int(product_id), *[int(uid) for uid in user_ids]],
        )
        await db.commit()
    finally:
        await db.close()



async def get_product(product_id: int) -> dict | None:
    """Récupère un produit par son identifiant."""
    if product_id in _PRODUCT_BY_ID_CACHE:
        return _PRODUCT_BY_ID_CACHE[product_id]
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM products WHERE id = ?", (product_id,)
        )
        row = await cursor.fetchone()
        res = dict(row) if row else None
        if res is not None:
            _PRODUCT_BY_ID_CACHE[product_id] = res
        return res
    finally:
        await db.close()


async def get_all_products() -> list[dict]:
    """Retourne la liste de tous les produits (actifs et inactifs, non supprimés)."""
    global _PRODUCTS_CACHE
    if _PRODUCTS_CACHE is not None:
        return _PRODUCTS_CACHE
    db = await get_db()
    try:
        try:
            cursor = await db.execute("SELECT * FROM products WHERE is_deleted = 0 ORDER BY category_id, sort_order ASC, id ASC")
            rows = await cursor.fetchall()
        except Exception:
            # Fallback if is_deleted column does not exist yet
            cursor = await db.execute("SELECT * FROM products ORDER BY category_id, id")
            rows = await cursor.fetchall()
        _PRODUCTS_CACHE = [dict(r) for r in rows]
        return _PRODUCTS_CACHE
    finally:
        await db.close()


async def add_product(
    category_id: int,
    name: str,
    description: str,
    price_usd: float,
    warranty_days: int = 0,
    emoji: str = "ðŸ“¦",
    custom_emoji_id: str | None = None,
    image_url: str | None = None,
    binance_account_id: int | None = None,
    description_fr: str = "",
    description_ar: str = "",
    description_zh: str = "",
    description_vi: str = "",
    description_ru: str = "",
    activation_message: str = "",
    activation_message_fr: str = "",
    activation_message_ar: str = "",
    activation_message_zh: str = "",
    activation_message_vi: str = "",
    activation_message_ru: str = "",
    confirmation_message: str = "",
    confirmation_message_fr: str = "",
    confirmation_message_ar: str = "",
    confirmation_message_zh: str = "",
    confirmation_message_vi: str = "",
    confirmation_message_ru: str = "",
    delivery_type: str = "stock",
) -> int:
    """Ajoute un nouveau produit et retourne son identifiant."""
    global _PRODUCTS_CACHE
    _PRODUCTS_CACHE = None
    _PRODUCT_BY_ID_CACHE.clear()
    invalidate_stats_cache()
    delivery_type = delivery_type if delivery_type in ("activation", "supplier_api") else "stock"
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO products
               (category_id, name, description, price_usd, warranty_days, emoji, custom_emoji_id, image_url, binance_account_id, description_fr, description_ar, description_zh, description_vi, description_ru, activation_message, activation_message_fr, activation_message_ar, activation_message_zh, activation_message_vi, activation_message_ru, confirmation_message, confirmation_message_fr, confirmation_message_ar, confirmation_message_zh, confirmation_message_vi, confirmation_message_ru, delivery_type)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (category_id, name, description, price_usd, warranty_days, emoji, custom_emoji_id, image_url, binance_account_id, description_fr, description_ar, description_zh, description_vi, description_ru, activation_message, activation_message_fr, activation_message_ar, activation_message_zh, activation_message_vi, activation_message_ru, confirmation_message, confirmation_message_fr, confirmation_message_ar, confirmation_message_zh, confirmation_message_vi, confirmation_message_ru, delivery_type),
        )
        await db.commit()
        return cursor.lastrowid  # type: ignore[return-value]
    finally:
        await db.close()


ALLOWED_PRODUCT_COLUMNS = {"category_id", "name", "description", "description_fr", "description_ar", "description_zh", "description_vi", "description_ru", "activation_message", "activation_message_fr", "activation_message_ar", "activation_message_zh", "activation_message_vi", "activation_message_ru", "confirmation_message", "confirmation_message_fr", "confirmation_message_ar", "confirmation_message_zh", "confirmation_message_vi", "confirmation_message_ru", "price_usd", "warranty_days", "emoji", "custom_emoji_id", "image_url", "is_active", "binance_account_id", "delivery_type", "dynamic_pricing_enabled", "dynamic_pricing_mode", "dynamic_min_price", "dynamic_max_price", "dynamic_base_price", "dynamic_target_daily_sales", "dynamic_max_change_pct", "dynamic_cooldown_hours", "dynamic_sensitivity", "dynamic_suggested_price", "dynamic_last_calculated_at", "dynamic_daily_cap_pct", "dynamic_weekly_cap_pct", "dynamic_min_confidence", "dynamic_psychological_rounding", "dynamic_last_input_hash", "dynamic_last_applied_hash", "dynamic_last_confidence"}


async def update_product(product_id: int, **kwargs) -> None:
    """Met Ã  jour un produit avec les champs fournis en kwargs."""
    global _PRODUCTS_CACHE
    _PRODUCTS_CACHE = None
    _PRODUCT_BY_ID_CACHE.clear()
    invalidate_stats_cache()
    safe_kwargs = {k: v for k, v in kwargs.items() if k in ALLOWED_PRODUCT_COLUMNS}
    if "delivery_type" in safe_kwargs:
        safe_kwargs["delivery_type"] = safe_kwargs["delivery_type"] if safe_kwargs["delivery_type"] in ("activation", "supplier_api") else "stock"
    if not safe_kwargs:
        return
    columns = ", ".join(f"{safe_k} = ?" for safe_k in safe_kwargs)
    values = list(safe_kwargs.values()) + [product_id]
    db = await get_db()
    try:
        await db.execute(
            f"UPDATE products SET {columns} WHERE id = ?", values
        )
        await db.commit()
    finally:
        await db.close()


# â”€â”€ Binance Accounts â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€


async def get_binance_accounts() -> list[dict]:
    """Return all Binance accounts."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM binance_accounts ORDER BY is_default DESC, id ASC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_binance_account(account_id: int) -> dict | None:
    """Return a single Binance account by ID."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM binance_accounts WHERE id = ?", (account_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def get_default_binance_account() -> dict | None:
    """Return the default Binance account (is_default=1), or the first one."""
    global _DEFAULT_BINANCE_ACCOUNT_CACHE, _DEFAULT_BINANCE_ACCOUNT_LOADED
    if _DEFAULT_BINANCE_ACCOUNT_LOADED:
        return dict(_DEFAULT_BINANCE_ACCOUNT_CACHE) if _DEFAULT_BINANCE_ACCOUNT_CACHE else None
    try:
        db = await get_db()
        try:
            cursor = await db.execute(
                "SELECT * FROM binance_accounts WHERE is_default = 1 LIMIT 1"
            )
            row = await cursor.fetchone()
            if not row:
                cursor = await db.execute("SELECT * FROM binance_accounts ORDER BY id ASC LIMIT 1")
                row = await cursor.fetchone()
            _DEFAULT_BINANCE_ACCOUNT_CACHE = dict(row) if row else None
            _DEFAULT_BINANCE_ACCOUNT_LOADED = True
            return dict(_DEFAULT_BINANCE_ACCOUNT_CACHE) if _DEFAULT_BINANCE_ACCOUNT_CACHE else None
        finally:
            await db.close()
    except Exception as exc:
        logger.error("Error in get_default_binance_account: %s", exc, exc_info=True)
        return None


async def add_binance_account(label: str, uid: str, api_key: str = "", api_secret: str = "", is_default: int = 0) -> int:
    """Add a new Binance account. If is_default=1, unset other defaults first."""
    _clear_binance_account_cache()
    db = await get_db()
    try:
        if is_default:
            await db.execute("UPDATE binance_accounts SET is_default = 0")
        cursor = await db.execute(
            "INSERT INTO binance_accounts (label, uid, api_key, api_secret, is_default) VALUES (?, ?, ?, ?, ?)",
            (label, uid, api_key, api_secret, is_default),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def update_binance_account(account_id: int, **kwargs) -> None:
    """Update a Binance account."""
    _clear_binance_account_cache()
    allowed = {"label", "uid", "api_key", "api_secret", "is_default"}
    fields = {k: v for k, v in kwargs.items() if k in allowed}
    if not fields:
        return
    db = await get_db()
    try:
        if fields.get("is_default"):
            await db.execute("UPDATE binance_accounts SET is_default = 0")
        sets = ", ".join(f"{k} = ?" for k in fields)
        vals = list(fields.values()) + [account_id]
        await db.execute(f"UPDATE binance_accounts SET {sets} WHERE id = ?", vals)
        await db.commit()
    finally:
        await db.close()


async def delete_binance_account(account_id: int) -> None:
    """Delete a Binance account."""
    _clear_binance_account_cache()
    db = await get_db()
    try:
        await db.execute("DELETE FROM binance_accounts WHERE id = ?", (account_id,))
        await db.execute("UPDATE products SET binance_account_id = NULL WHERE binance_account_id = ?", (account_id,))
        await db.commit()
    finally:
        await db.close()


async def toggle_product(product_id: int) -> None:
    """Inverse l'Ã©tat actif/inactif d'un produit."""
    global _PRODUCTS_CACHE
    _PRODUCTS_CACHE = None
    _PRODUCT_BY_ID_CACHE.clear()
    invalidate_stats_cache()
    db = await get_db()
    try:
        await db.execute(
            "UPDATE products SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id = ?",
            (product_id,),
        )
        await db.commit()
    finally:
        await db.close()


async def toggle_product_active(product_id: int) -> dict:
    _clear_stock_cache()
    global _PRODUCTS_CACHE
    _PRODUCTS_CACHE = None
    _PRODUCT_BY_ID_CACHE.clear()
    
    db = await get_db()
    try:
        cursor = await db.execute("SELECT is_active FROM products WHERE id = ?", (product_id,))
        row = await cursor.fetchone()
        if not row:
            raise ValueError(f"Product {product_id} not found")
        
        new_status = 1 if row[0] == 0 else 0
        await db.execute("UPDATE products SET is_active = ? WHERE id = ?", (new_status, product_id))
        await db.commit()
        return {"status": "success", "is_active": new_status}
    finally:
        await db.close()

async def delete_product(product_id: int) -> None:
    _clear_stock_cache()
    """Marque un produit comme supprimÃ© et supprime uniquement son stock non vendu."""
    global _PRODUCTS_CACHE
    _PRODUCTS_CACHE = None
    _PRODUCT_BY_ID_CACHE.clear()
    db = await get_db()
    try:
        # Ne pas toucher aux commandes.
        # Supprimer uniquement le stock non vendu.
        await db.execute("DELETE FROM stock_items WHERE product_id = ? AND is_sold = 0", (product_id,))
        # Soft delete le produit (is_deleted = 1, is_active = 0)
        await db.execute("UPDATE products SET is_deleted = 1, is_active = 0 WHERE id = ?", (product_id,))
        await db.commit()
    finally:
        await db.close()


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
# â•‘  PRIX PAR PALIERS (BATCH PRICING)                                â•‘
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


async def get_price_tiers(product_id: int) -> list[dict]:
    """Retourne les paliers de prix pour un produit, triÃ©s par min_qty."""
    global _TIERS_CACHE
    if product_id in _TIERS_CACHE:
        return _TIERS_CACHE[product_id]
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM price_tiers WHERE product_id = ? ORDER BY min_qty ASC",
            (product_id,),
        )
        rows = await cursor.fetchall()
        res = [dict(r) for r in rows]
        _TIERS_CACHE[product_id] = res
        return res
    finally:
        await db.close()


async def get_price_tiers_for_products(product_ids: list[int]) -> dict[int, list[dict]]:
    """Return price tiers for many products in one query."""
    ids = sorted({int(pid) for pid in product_ids if pid})
    if not ids:
        return {}

    result: dict[int, list[dict]] = {}
    missing = [pid for pid in ids if pid not in _TIERS_CACHE]
    for pid in ids:
        if pid in _TIERS_CACHE:
            result[pid] = list(_TIERS_CACHE[pid])

    if missing:
        placeholders = ",".join("?" for _ in missing)
        db = await get_db()
        try:
            cursor = await db.execute(
                f"""SELECT * FROM price_tiers
                    WHERE product_id IN ({placeholders})
                    ORDER BY product_id ASC, min_qty ASC""",
                missing,
            )
            rows = [dict(r) for r in await cursor.fetchall()]
        finally:
            await db.close()

        grouped = {pid: [] for pid in missing}
        for row in rows:
            grouped.setdefault(int(row["product_id"]), []).append(row)
        for pid, tiers in grouped.items():
            _TIERS_CACHE[pid] = tiers
            result[pid] = list(tiers)

    return result


async def set_price_tiers(product_id: int, tiers: list[dict]) -> None:
    """Remplace tous les paliers de prix d'un produit.

    Chaque tier est un dict avec min_qty, max_qty, price_usd.
    """
    global _TIERS_CACHE
    _TIERS_CACHE.pop(product_id, None)
    db = await get_db()
    try:
        await db.execute(
            "DELETE FROM price_tiers WHERE product_id = ?", (product_id,)
        )
        for tier in tiers:
            await db.execute(
                "INSERT INTO price_tiers (product_id, min_qty, max_qty, price_usd) VALUES (?, ?, ?, ?)",
                (product_id, int(tier["min_qty"]), int(tier["max_qty"]), float(tier["price_usd"])),
            )
        await db.commit()
    finally:
        await db.close()


async def get_effective_price(product_id: int, quantity: int) -> float:
    """Retourne le prix unitaire effectif pour une quantitÃ© donnÃ©e.

    Cherche le palier correspondant Ã  la quantitÃ©.
    Si aucun palier ne correspond, retourne le prix de base du produit.
    """
    product = await get_product(product_id)
    if not product:
        raise ValueError(f"Product #{product_id} not found")

    tiers = await get_price_tiers(product_id)
    for tier in tiers:
        if tier["min_qty"] <= quantity <= tier["max_qty"]:
            return dynamic_tier_price(product, float(tier["price_usd"]))

    # Fallback: prix de base du produit
    return float(product["price_usd"])


def dynamic_tier_price(product: dict, tier_price: float) -> float:
    """Scale an explicit quantity tier with the current dynamic base price."""
    if not product.get("dynamic_pricing_enabled"):
        return round(float(tier_price), 2)
    base_price = float(product.get("dynamic_base_price") or 0)
    current_price = float(product.get("price_usd") or 0)
    if base_price <= 0 or current_price <= 0:
        return round(float(tier_price), 2)
    return round(float(tier_price) * (current_price / base_price), 2)


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _dynamic_last_datetime(value) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    except (TypeError, ValueError):
        return None


def _psychological_dynamic_price(raw_price: float, minimum: float, maximum: float) -> float:
    rounded = round(_clamp(raw_price, minimum, maximum), 2)
    if rounded < 1:
        return rounded
    candidates = []
    whole = int(raw_price)
    for base in range(max(0, whole - 1), whole + 2):
        for ending in (0.49, 0.90, 0.99):
            candidate = round(base + ending, 2)
            if minimum <= candidate <= maximum:
                candidates.append(candidate)
    if not candidates:
        return rounded
    candidate = min(candidates, key=lambda value: abs(value - raw_price))
    return candidate if abs(candidate - raw_price) <= max(0.05, raw_price * 0.0125) else rounded


def _dynamic_confidence(sales_14d: float, views_7d: int) -> float:
    if sales_14d <= 0 and views_7d < 5:
        return 0.0
    sales_confidence = min(1.0, sales_14d / 10.0)
    views_confidence = min(1.0, views_7d / 50.0)
    return round(min(1.0, 0.20 + 0.60 * sales_confidence + 0.20 * views_confidence), 3)


def _dynamic_decision_key(product: dict, metrics: dict) -> str:
    payload = {
        "sales_3d": round(float(metrics.get("sales_3d", 0)), 4),
        "sales_7d": round(float(metrics.get("sales_7d", 0)), 4),
        "sales_14d": round(float(metrics.get("sales_14d", 0)), 4),
        "views_7d": int(metrics.get("views_7d", 0)),
        "stock_count": metrics.get("stock_count"),
        "revenue_7d": round(float(metrics.get("revenue_7d", 0)), 4),
        "revenue_prev_7d": round(float(metrics.get("revenue_prev_7d", 0)), 4),
        "mode": product.get("dynamic_pricing_mode"),
        "min": product.get("dynamic_min_price"),
        "max": product.get("dynamic_max_price"),
        "target": product.get("dynamic_target_daily_sales"),
        "max_change": product.get("dynamic_max_change_pct"),
        "daily_cap": product.get("dynamic_daily_cap_pct"),
        "weekly_cap": product.get("dynamic_weekly_cap_pct"),
        "min_confidence": product.get("dynamic_min_confidence"),
        "sensitivity": product.get("dynamic_sensitivity"),
        "psychological": product.get("dynamic_psychological_rounding"),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:32]


def _calculate_dynamic_decision(
    product: dict,
    current_price: float,
    metrics: dict,
    daily_base_price: float,
    weekly_base_price: float,
) -> dict:
    sales_3d = float(metrics.get("sales_3d") or 0)
    sales_7d = float(metrics.get("sales_7d") or 0)
    sales_14d = float(metrics.get("sales_14d") or 0)
    views_7d = int(metrics.get("views_7d") or 0)
    revenue_7d = float(metrics.get("revenue_7d") or 0)
    revenue_prev_7d = float(metrics.get("revenue_prev_7d") or 0)
    stock_count = metrics.get("stock_count")
    confidence = _dynamic_confidence(sales_14d, views_7d)
    min_confidence = _clamp(float(product.get("dynamic_min_confidence") or 0.30), 0.0, 1.0)
    min_price = float(product.get("dynamic_min_price") or current_price)
    max_price = float(product.get("dynamic_max_price") or current_price)

    if stock_count == 0:
        return {
            "status": "out_of_stock", "suggested_price": round(current_price, 2),
            "confidence": confidence, "score": 0.0, "change_ratio": 0.0,
            "stock_days": 0.0, "signals": {},
            "explanation": "Calcul suspendu : le produit est en rupture de stock.",
        }
    if confidence < min_confidence:
        return {
            "status": "insufficient_data", "suggested_price": round(current_price, 2),
            "confidence": confidence, "score": 0.0, "change_ratio": 0.0,
            "stock_days": None, "signals": {},
            "explanation": f"Données insuffisantes : confiance {confidence * 100:.0f}% (minimum {min_confidence * 100:.0f}%).",
        }

    recent_daily = sales_3d / 3.0
    medium_daily = sales_7d / 7.0
    long_daily = sales_14d / 14.0
    smoothed_daily = 0.50 * recent_daily + 0.30 * medium_daily + 0.20 * long_daily
    target = max(0.1, float(product.get("dynamic_target_daily_sales") or 1.0))
    demand_signal = _clamp((smoothed_daily - target) / target, -1.0, 1.0)
    momentum_denominator = max(long_daily, target * 0.25, 0.1)
    momentum_signal = _clamp((recent_daily - long_daily) / momentum_denominator, -1.0, 1.0)
    conversion_7d = sales_7d / views_7d if views_7d > 0 else 0.0
    conversion_signal = 0.0
    if views_7d >= 5:
        conversion_signal = _clamp((conversion_7d - 0.10) / 0.10, -1.0, 1.0)
    revenue_baseline = max(revenue_prev_7d, target * current_price * 7.0 * 0.25, 0.01)
    revenue_signal = _clamp((revenue_7d - revenue_prev_7d) / revenue_baseline, -1.0, 1.0)

    stock_days = None
    stock_signal = 0.0
    if stock_count is not None:
        velocity = max(smoothed_daily, 0.1)
        stock_days = float(stock_count) / velocity
        stock_signal = _clamp((14.0 - stock_days) / 14.0, -1.0, 1.0)
        score = (
            0.35 * demand_signal + 0.20 * momentum_signal + 0.15 * stock_signal
            + 0.10 * conversion_signal + 0.20 * revenue_signal
        )
    else:
        score = 0.45 * demand_signal + 0.25 * momentum_signal + 0.10 * conversion_signal + 0.20 * revenue_signal

    sensitivity_factor = {"cautious": 0.6, "normal": 1.0, "aggressive": 1.4}.get(
        str(product.get("dynamic_sensitivity") or "normal"), 1.0
    )
    max_change = _clamp(float(product.get("dynamic_max_change_pct") or 5.0), 0.5, 20.0) / 100.0
    change_ratio = _clamp(score * 0.05 * sensitivity_factor, -max_change, max_change)

    daily_cap = _clamp(float(product.get("dynamic_daily_cap_pct") or 10.0), 0.5, 100.0) / 100.0
    weekly_cap = _clamp(float(product.get("dynamic_weekly_cap_pct") or 25.0), 0.5, 200.0) / 100.0
    lower_bound = max(min_price, current_price * (1.0 - max_change), daily_base_price * (1.0 - daily_cap), weekly_base_price * (1.0 - weekly_cap))
    upper_bound = min(max_price, current_price * (1.0 + max_change), daily_base_price * (1.0 + daily_cap), weekly_base_price * (1.0 + weekly_cap))
    raw_price = _clamp(current_price * (1.0 + change_ratio), lower_bound, upper_bound)
    if product.get("dynamic_psychological_rounding"):
        raw_price = _psychological_dynamic_price(raw_price, lower_bound, upper_bound)
    suggested_price = round(raw_price, 2)
    if abs(suggested_price - current_price) < 0.01:
        suggested_price = round(current_price, 2)

    reasons = []
    reasons.append("ventes au-dessus de l’objectif" if demand_signal > 0.15 else "ventes sous l’objectif" if demand_signal < -0.15 else "ventes proches de l’objectif")
    if momentum_signal > 0.15:
        reasons.append("momentum récent positif")
    elif momentum_signal < -0.15:
        reasons.append("momentum récent en baisse")
    if stock_signal > 0.25:
        reasons.append("stock faible")
    elif stock_signal < -0.25:
        reasons.append("stock confortable")
    if conversion_signal > 0.25:
        reasons.append("conversion élevée")
    elif conversion_signal < -0.25:
        reasons.append("conversion faible")
    if revenue_signal > 0.25:
        reasons.append("revenu hebdomadaire en progression")
    elif revenue_signal < -0.25:
        reasons.append("revenu hebdomadaire en recul")
    direction = "hausse" if suggested_price > current_price else "baisse" if suggested_price < current_price else "maintien"
    explanation = f"{direction.capitalize()} recommandée : " + ", ".join(reasons) + "."
    return {
        "status": "ready", "suggested_price": suggested_price,
        "confidence": confidence, "score": round(score, 4), "change_ratio": change_ratio,
        "stock_days": stock_days, "conversion_7d": conversion_7d,
        "signals": {
            "demand": round(demand_signal, 3), "momentum": round(momentum_signal, 3),
            "stock": round(stock_signal, 3), "conversion": round(conversion_signal, 3),
            "revenue": round(revenue_signal, 3), "smoothed_daily_sales": round(smoothed_daily, 3),
        },
        "explanation": explanation,
    }


async def recalculate_dynamic_prices(
    product_id: int | None = None,
    force: bool = False,
    apply_automatic: bool = True,
) -> list[dict]:
    """Build idempotent recommendations and optionally apply automatic decisions."""
    db = await get_db()
    processed: list[dict] = []
    now = _utcnow()
    try:
        params: list = []
        where = "COALESCE(dynamic_pricing_enabled, 0) = 1 AND COALESCE(is_deleted, 0) = 0"
        if product_id is not None:
            where += " AND id = ?"
            params.append(int(product_id))
        cursor = await db.execute(f"SELECT * FROM products WHERE {where}", params)
        products = [dict(row) for row in await cursor.fetchall()]
        if not products:
            return []

        due_products = []
        for product in products:
            cooldown = max(1, int(product.get("dynamic_cooldown_hours") or 6))
            last = _dynamic_last_datetime(product.get("dynamic_last_calculated_at"))
            if force or last is None or now - last >= timedelta(hours=cooldown):
                due_products.append(product)
        if not due_products:
            return []

        product_ids = [int(product["id"]) for product in due_products]
        placeholders = ",".join("?" for _ in product_ids)
        paid_statuses = "'COMPLETED','AWAITING_ACTIVATION','AWAITING_ACTIVATION_INFO','PAID_PENDING_DELIVERY'"
        cursor = await db.execute(
            f"""SELECT product_id,
                       COALESCE(SUM(CASE WHEN datetime(created_at) >= datetime('now', '-3 days') THEN quantity ELSE 0 END), 0) AS sales_3d,
                       COALESCE(SUM(CASE WHEN datetime(created_at) >= datetime('now', '-7 days') THEN quantity ELSE 0 END), 0) AS sales_7d,
                       COALESCE(SUM(CASE WHEN datetime(created_at) >= datetime('now', '-14 days') THEN quantity ELSE 0 END), 0) AS sales_14d,
                       COALESCE(SUM(CASE WHEN datetime(created_at) >= datetime('now', '-7 days') THEN amount_usd ELSE 0 END), 0) AS revenue_7d,
                       COALESCE(SUM(CASE WHEN datetime(created_at) >= datetime('now', '-14 days') AND datetime(created_at) < datetime('now', '-7 days') THEN amount_usd ELSE 0 END), 0) AS revenue_prev_7d
                FROM orders
                WHERE product_id IN ({placeholders}) AND status IN ({paid_statuses})
                GROUP BY product_id""",
            product_ids,
        )
        sales = {int(row["product_id"]): dict(row) for row in await cursor.fetchall()}
        cursor = await db.execute(
            f"""SELECT product_id, COUNT(*) AS views_7d FROM product_views
                WHERE product_id IN ({placeholders}) AND datetime(viewed_at) >= datetime('now', '-7 days')
                GROUP BY product_id""",
            product_ids,
        )
        views = {int(row["product_id"]): int(row["views_7d"] or 0) for row in await cursor.fetchall()}
        cursor = await db.execute(
            f"""SELECT product_id, COUNT(*) AS stock_count FROM stock_items
                WHERE product_id IN ({placeholders}) AND is_sold = 0 GROUP BY product_id""",
            product_ids,
        )
        stocks = {int(row["product_id"]): int(row["stock_count"] or 0) for row in await cursor.fetchall()}
        cursor = await db.execute(
            f"""SELECT product_id, old_price, new_price, created_at FROM dynamic_price_history
                WHERE product_id IN ({placeholders}) AND COALESCE(applied, 0) = 1
                  AND datetime(created_at) >= datetime('now', '-7 days')
                ORDER BY datetime(created_at) ASC, id ASC""",
            product_ids,
        )
        applied_history: dict[int, list[dict]] = {}
        for row in await cursor.fetchall():
            applied_history.setdefault(int(row["product_id"]), []).append(dict(row))

        calculated_at = now.isoformat(sep=" ", timespec="seconds")
        for product in due_products:
            pid = int(product["id"])
            current_price = float(product.get("price_usd") or 0)
            product_metrics = dict(sales.get(pid, {}))
            product_metrics["views_7d"] = int(views.get(pid, 0))
            product_metrics["stock_count"] = None if product.get("delivery_type") == "activation" else int(stocks.get(pid, 0))
            history = applied_history.get(pid, [])
            weekly_base = float(history[0]["old_price"]) if history else current_price
            daily_rows = [row for row in history if (_dynamic_last_datetime(row.get("created_at")) or datetime.min) >= now - timedelta(days=1)]
            daily_base = float(daily_rows[0]["old_price"]) if daily_rows else current_price
            decision_key = _dynamic_decision_key(product, product_metrics)
            mode = "suggestion" if product.get("dynamic_pricing_mode") == "suggestion" else "automatic"

            if decision_key == product.get("dynamic_last_input_hash") and product.get("dynamic_suggested_price") is not None:
                stored_suggestion = round(float(product["dynamic_suggested_price"]), 2)
                should_apply = apply_automatic and mode == "automatic" and product.get("dynamic_last_applied_hash") != decision_key
                if should_apply and abs(stored_suggestion - current_price) >= 0.01:
                    await db.execute(
                        "UPDATE products SET price_usd = ?, dynamic_last_applied_hash = ? WHERE id = ?",
                        (stored_suggestion, decision_key, pid),
                    )
                    await db.execute(
                        """UPDATE dynamic_price_history SET applied = 1, new_price = ?, mode = 'automatic'
                           WHERE product_id = ? AND decision_key = ? AND COALESCE(applied, 0) = 0""",
                        (stored_suggestion, pid, decision_key),
                    )
                    await db.commit()
                    processed.append({
                        "product_id": pid, "status": "updated", "idempotent": True,
                        "old_price": current_price, "new_price": stored_suggestion,
                        "suggested_price": stored_suggestion,
                        "confidence": float(product.get("dynamic_last_confidence") or 0),
                        "explanation": "Recommandation existante appliquée après le délai configuré.",
                    })
                else:
                    processed.append({
                        "product_id": pid, "status": "unchanged", "idempotent": True,
                        "old_price": current_price, "new_price": current_price,
                        "suggested_price": stored_suggestion,
                        "confidence": float(product.get("dynamic_last_confidence") or 0),
                        "explanation": "Aucune nouvelle donnée : la recommandation reste inchangée.",
                    })
                continue

            decision = _calculate_dynamic_decision(product, current_price, product_metrics, daily_base, weekly_base)
            confidence = float(decision["confidence"])
            suggested_price = float(decision["suggested_price"])
            if decision["status"] != "ready":
                await db.execute(
                    """UPDATE products SET dynamic_suggested_price = ?, dynamic_last_calculated_at = ?,
                       dynamic_last_input_hash = ?, dynamic_last_confidence = ? WHERE id = ?""",
                    (suggested_price, calculated_at, decision_key, confidence, pid),
                )
                await db.commit()
                processed.append({
                    "product_id": pid, "status": decision["status"],
                    "old_price": current_price, "new_price": current_price,
                    "suggested_price": suggested_price, "confidence": confidence,
                    "explanation": decision["explanation"], "signals": decision.get("signals", {}),
                })
                continue

            apply_now = apply_automatic and mode == "automatic"
            new_price = suggested_price if apply_now else current_price
            applied_hash = decision_key if apply_now else product.get("dynamic_last_applied_hash")
            await db.execute(
                """UPDATE products SET price_usd = ?, dynamic_suggested_price = ?,
                   dynamic_last_calculated_at = ?, dynamic_last_input_hash = ?,
                   dynamic_last_applied_hash = ?, dynamic_last_confidence = ? WHERE id = ?""",
                (new_price, suggested_price, calculated_at, decision_key, applied_hash, confidence, pid),
            )
            signals = decision.get("signals", {})
            reason = "; ".join(f"{key}={value:+.2f}" for key, value in signals.items() if key != "smoothed_daily_sales")
            await db.execute(
                """INSERT INTO dynamic_price_history
                   (product_id, old_price, new_price, suggested_price, mode, reason,
                    sales_3d, sales_14d, stock_count, stock_days, views_7d, conversion_7d,
                    revenue_7d, score, confidence, applied, decision_key, explanation)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (pid, current_price, new_price, suggested_price, mode, reason,
                 float(product_metrics.get("sales_3d") or 0), float(product_metrics.get("sales_14d") or 0),
                 product_metrics.get("stock_count"), decision.get("stock_days"), int(product_metrics.get("views_7d") or 0),
                 float(decision.get("conversion_7d") or 0), float(product_metrics.get("revenue_7d") or 0),
                 float(decision["score"]), confidence, 1 if apply_now else 0, decision_key, decision["explanation"]),
            )
            await db.commit()
            processed.append({
                "product_id": pid,
                "status": "updated" if apply_now and abs(new_price - current_price) >= 0.01 else "recommended",
                "mode": mode, "old_price": current_price, "new_price": new_price,
                "suggested_price": suggested_price, "confidence": confidence,
                "score": decision["score"], "signals": signals,
                "explanation": decision["explanation"], "applied": apply_now,
            })

        clear_products_cache()
        return processed
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()


async def get_dynamic_price_history(product_id: int, limit: int = 20) -> list[dict]:
    query_params = (int(product_id), max(1, min(int(limit), 100)))
    for attempt in range(2):
        db = await get_db()
        try:
            cursor = await db.execute(
                """SELECT * FROM dynamic_price_history
                   WHERE product_id = ? ORDER BY created_at DESC, id DESC LIMIT ?""",
                query_params,
            )
            return [dict(row) for row in await cursor.fetchall()]
        except Exception as exc:
            if attempt or not is_transient_db_connection_error(exc):
                raise
            logger.info("Retrying dynamic price history after a stale Turso stream: %s", exc)
        finally:
            await db.close()

    return []


async def apply_dynamic_price_suggestion(product_id: int) -> dict:
    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute("SELECT * FROM products WHERE id = ?", (int(product_id),))
        row = await cursor.fetchone()
        if not row:
            await db.rollback()
            raise ValueError("Product not found")
        product = dict(row)
        if not product.get("dynamic_pricing_enabled"):
            await db.rollback()
            raise ValueError("Dynamic pricing is disabled")
        suggestion = product.get("dynamic_suggested_price")
        if suggestion is None:
            await db.rollback()
            raise ValueError("No dynamic price suggestion available")
        old_price = float(product["price_usd"])
        min_price = float(product.get("dynamic_min_price") or old_price)
        max_price = float(product.get("dynamic_max_price") or old_price)
        new_price = round(_clamp(float(suggestion), min_price, max_price), 2)
        if abs(new_price - old_price) < 0.01:
            await db.rollback()
            return {
                "product_id": int(product_id), "old_price": old_price,
                "new_price": old_price, "status": "unchanged",
            }
        decision_key = product.get("dynamic_last_input_hash")
        await db.execute(
            "UPDATE products SET price_usd = ?, dynamic_last_applied_hash = ? WHERE id = ?",
            (new_price, decision_key, int(product_id)),
        )
        updated = await db.execute(
            """UPDATE dynamic_price_history
               SET applied = 1, new_price = ?, mode = 'manual',
                   explanation = 'Recommandation appliquée manuellement.'
               WHERE product_id = ? AND decision_key = ? AND COALESCE(applied, 0) = 0""",
            (new_price, int(product_id), decision_key),
        )
        if updated.rowcount <= 0:
            await db.execute(
                """INSERT INTO dynamic_price_history
                   (product_id, old_price, new_price, suggested_price, mode, reason,
                    confidence, applied, decision_key, explanation)
                   VALUES (?, ?, ?, ?, 'manual', 'Recommendation applied manually', ?, 1, ?,
                           'Recommandation appliquée manuellement.')""",
                (int(product_id), old_price, new_price, new_price,
                 float(product.get("dynamic_last_confidence") or 0), decision_key),
            )
        await db.commit()
        clear_products_cache()
        return {
            "product_id": int(product_id), "old_price": old_price,
            "new_price": new_price, "status": "applied",
        }
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()


async def simulate_dynamic_pricing(product_id: int, days: int = 30) -> dict:
    """Backtest dynamic pricing without writing prices or history."""
    days = max(7, min(int(days), 90))
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM products WHERE id = ?", (int(product_id),))
        row = await cursor.fetchone()
        if not row:
            raise ValueError("Product not found")
        product = dict(row)
        paid_statuses = "'COMPLETED','AWAITING_ACTIVATION','AWAITING_ACTIVATION_INFO','PAID_PENDING_DELIVERY'"
        cursor = await db.execute(
            f"""SELECT date(created_at) AS day, COALESCE(SUM(quantity), 0) AS sales,
                       COALESCE(SUM(amount_usd), 0) AS revenue
                FROM orders WHERE product_id = ? AND status IN ({paid_statuses})
                  AND datetime(created_at) >= datetime('now', ?)
                GROUP BY date(created_at)""",
            (int(product_id), f"-{days + 14} days"),
        )
        order_days = {str(item["day"]): dict(item) for item in await cursor.fetchall()}
        cursor = await db.execute(
            """SELECT date(viewed_at) AS day, COUNT(*) AS views FROM product_views
               WHERE product_id = ? AND datetime(viewed_at) >= datetime('now', ?)
               GROUP BY date(viewed_at)""",
            (int(product_id), f"-{days + 14} days"),
        )
        view_days = {str(item["day"]): int(item["views"] or 0) for item in await cursor.fetchall()}
        cursor = await db.execute(
            "SELECT COUNT(*) AS stock_count FROM stock_items WHERE product_id = ? AND is_sold = 0",
            (int(product_id),),
        )
        stock_row = await cursor.fetchone()
        stock_count = None if product.get("delivery_type") == "activation" else int(stock_row["stock_count"] or 0)

        today = _utcnow().date()
        all_dates = [today - timedelta(days=offset) for offset in range(days + 13, -1, -1)]
        daily_sales = [float(order_days.get(day.isoformat(), {}).get("sales") or 0) for day in all_dates]
        daily_revenue = [float(order_days.get(day.isoformat(), {}).get("revenue") or 0) for day in all_dates]
        daily_views = [int(view_days.get(day.isoformat(), 0)) for day in all_dates]
        current_price = float(product.get("dynamic_base_price") or product.get("price_usd") or 0)
        start_price = current_price
        simulated_prices: list[float] = []
        points = []
        interval_days = max(1, (max(1, int(product.get("dynamic_cooldown_hours") or 6)) + 23) // 24)
        last_decision_index = -interval_days
        decision_count = 0

        for index in range(14, len(all_dates)):
            day = all_dates[index]
            metrics = {
                "sales_3d": sum(daily_sales[index - 2:index + 1]),
                "sales_7d": sum(daily_sales[index - 6:index + 1]),
                "sales_14d": sum(daily_sales[index - 13:index + 1]),
                "views_7d": sum(daily_views[index - 6:index + 1]),
                "revenue_7d": sum(daily_revenue[index - 6:index + 1]),
                "revenue_prev_7d": sum(daily_revenue[index - 13:index - 6]),
                "stock_count": stock_count,
            }
            daily_base = simulated_prices[-1] if simulated_prices else current_price
            weekly_base = simulated_prices[max(0, len(simulated_prices) - 7)] if simulated_prices else current_price
            if index - last_decision_index >= interval_days:
                decision = _calculate_dynamic_decision(product, current_price, metrics, daily_base, weekly_base)
                if decision["status"] == "ready":
                    current_price = float(decision["suggested_price"])
                    decision_count += 1
                last_decision_index = index
            else:
                decision = {
                    "status": "cooldown", "confidence": _dynamic_confidence(metrics["sales_14d"], metrics["views_7d"]),
                    "explanation": "Aucune décision : délai de sécurité actif.",
                }
            simulated_prices.append(round(current_price, 2))
            points.append({
                "date": day.isoformat(), "simulated_price": round(current_price, 2),
                "sales": daily_sales[index], "revenue": round(daily_revenue[index], 2),
                "views": daily_views[index], "confidence": round(float(decision.get("confidence") or 0), 3),
                "status": decision["status"], "explanation": decision["explanation"],
            })

        return {
            "product_id": int(product_id), "days": days, "points": points,
            "summary": {
                "start_price": round(start_price, 2), "end_price": round(current_price, 2),
                "min_price": min(simulated_prices) if simulated_prices else round(current_price, 2),
                "max_price": max(simulated_prices) if simulated_prices else round(current_price, 2),
                "decisions": decision_count,
                "observed_sales": sum(point["sales"] for point in points),
                "observed_revenue": round(sum(point["revenue"] for point in points), 2),
            },
            "assumption": "Simulation en lecture seule utilisant le stock disponible actuel.",
        }
    finally:
        await db.close()


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
# â•‘  STOCK                                                           â•‘
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


async def get_all_stock_counts() -> dict[int, int]:
    """Retourne le nombre d'articles non vendus et non rÃ©servÃ©s pour TOUS les produits en une seule requÃªte.

    Returns:
        Dictionnaire {product_id: count}
    """
    global _STOCK_COUNTS_CACHE
    now = time.monotonic()
    if _STOCK_COUNTS_CACHE is not None:
        cached_at, cached_counts = _STOCK_COUNTS_CACHE
        if now - cached_at < _STOCK_COUNTS_CACHE_TTL:
            return dict(cached_counts)

    db = await get_db()
    try:
        # 1. Obtenir le stock total non vendu pour chaque produit
        cursor = await db.execute(
            "SELECT product_id, COUNT(*) as cnt FROM stock_items WHERE is_sold = 0 GROUP BY product_id"
        )
        rows = await cursor.fetchall()
        stocks = {r["product_id"]: r["cnt"] for r in rows}

        # 2. Obtenir les rÃ©servations actives (crÃ©Ã©es dans les derniÃ¨res 300 secondes / 5 minutes)
        cursor = await db.execute(
            """SELECT product_id, COALESCE(SUM(quantity), 0) as reserved 
               FROM orders 
               WHERE status IN ('PENDING', 'AWAITING_PAYMENT', 'PROCESSING') 
                 AND created_at >= datetime('now', '-300 seconds')
               GROUP BY product_id"""
        )
        rows_res = await cursor.fetchall()
        reservations = {r["product_id"]: r["reserved"] for r in rows_res}

        # 3. Calculer le stock net disponible
        result = {}
        for p_id, total in stocks.items():
            reserved = reservations.get(p_id, 0)
            result[p_id] = max(0, total - reserved)
        from database.suppliers import supplier_stock_counts
        result.update(await supplier_stock_counts())
        _STOCK_COUNTS_CACHE = (now, dict(result))
        return result
    finally:
        await db.close()

def _row_int(row, *keys, default: int = 0) -> int:
    """Safely extract an int from a DB row (dict / sqlite3.Row / tuple)."""
    if row is None:
        return default
    for key in keys:
        try:
            val = row[key]
            if val is None:
                return default
            return int(val)
        except Exception:
            continue
    try:
        return int(row[0])
    except Exception:
        return default


async def get_product_full_details(product_id: int) -> tuple[dict | None, int, list[dict], int]:
    """Retourne (product, stock_count, tiers, sold_count) avec une seule connexion pour optimiser la latence."""
    db = await get_db()
    try:
        # 1. Produit
        cursor = await db.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        row = await cursor.fetchone()
        product = dict(row) if row else None
        
        if not product:
            return None, 0, [], 0

        # 2. Stock non vendu
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM stock_items WHERE product_id = ? AND is_sold = 0",
            (product_id,),
        )
        row = await cursor.fetchone()
        total_unsold = _row_int(row, "cnt")

        # Stock réservé (dernières 5 minutes)
        reserved = 0
        try:
            cursor = await db.execute(
                "SELECT COALESCE(SUM(quantity), 0) as reserved FROM orders "
                "WHERE product_id = ? AND status IN ('PENDING', 'AWAITING_PAYMENT', 'PROCESSING') "
                "AND created_at >= datetime('now', '-300 seconds')",
                (product_id,),
            )
            row = await cursor.fetchone()
            reserved = _row_int(row, "reserved")
        except Exception as exc:
            logger.warning("Reserved stock query failed for product %s: %s", product_id, exc)
            reserved = 0
        stock_count = max(0, total_unsold - reserved)
        if product.get("delivery_type") == "supplier_api":
            from database.suppliers import get_supplier_product_by_local_product, supplier_available_stock
            supplier_product = await get_supplier_product_by_local_product(product_id)
            stock_count = await supplier_available_stock(supplier_product) if supplier_product else 0

        # 3. Paliers de prix (Tiers) via cache si possible
        global _TIERS_CACHE
        if product_id in _TIERS_CACHE:
            tiers = _TIERS_CACHE[product_id]
        else:
            try:
                cursor = await db.execute(
                    "SELECT * FROM price_tiers WHERE product_id = ? ORDER BY min_qty ASC",
                    (product_id,),
                )
                rows = await cursor.fetchall()
                tiers = [dict(r) for r in rows]
            except Exception:
                tiers = []
            _TIERS_CACHE[product_id] = tiers

        # 4. Nombre de ventes
        sold_count = 0
        try:
            cursor = await db.execute(
                "SELECT COUNT(id) as cnt FROM stock_items WHERE product_id = ? AND is_sold = 1",
                (product_id,),
            )
            row = await cursor.fetchone()
            sold_count = _row_int(row, "cnt")
        except Exception:
            sold_count = 0

        return product, stock_count, tiers, sold_count
    finally:
        await db.close()

async def get_sold_count(product_id: int) -> int:
    """Retourne le nombre d'articles vendus pour un produit."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT COUNT(id) FROM stock_items WHERE product_id = ? AND is_sold = 1",
            (product_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0
    finally:
        await db.close()
async def get_stock_count(product_id: int) -> int:
    """Retourne le nombre d'articles en stock non vendus et non rÃ©servÃ©s pour un produit."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT remote_stock, base_price FROM supplier_products WHERE local_product_id = ? AND enabled = 1 LIMIT 1",
            (int(product_id),),
        )
        supplier_row = await cursor.fetchone()
        if supplier_row:
            from database.suppliers import supplier_available_stock
            return await supplier_available_stock(dict(supplier_row))
        # 1. Stock total non vendu en base
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM stock_items WHERE product_id = ? AND is_sold = 0",
            (product_id,),
        )
        row = await cursor.fetchone()
        total_unsold = row["cnt"] if row else 0

        # 2. Stock rÃ©servÃ© (commandes PENDING ou AWAITING_PAYMENT crÃ©Ã©es il y a moins de 300 secondes / 5 minutes)
        cursor = await db.execute(
            """SELECT COALESCE(SUM(quantity), 0) as reserved 
               FROM orders 
               WHERE product_id = ? 
                 AND status IN ('PENDING', 'AWAITING_PAYMENT', 'PROCESSING') 
                 AND created_at >= datetime('now', '-300 seconds')""",
            (product_id,),
        )
        row = await cursor.fetchone()
        reserved = row["reserved"] if row else 0

        return max(0, total_unsold - reserved)
    finally:
        await db.close()


async def add_stock_items(product_id: int, items: list[str]) -> int:
    _clear_stock_cache()
    invalidate_stats_cache()
    """Ajoute plusieurs articles en stock et retourne le nombre ajoutÃ©."""
    db = await get_db()
    try:
        await db.executemany(
            "INSERT INTO stock_items (product_id, account_data) VALUES (?, ?)",
            [(product_id, item) for item in items],
        )
        await db.commit()
        return len(items)
    finally:
        await db.close()


async def get_available_stock_item(product_id: int) -> dict | None:
    """Retourne l'article en stock le plus ancien non vendu (FIFO)."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM stock_items WHERE product_id = ? AND is_sold = 0 ORDER BY added_at ASC LIMIT 1",
            (product_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def get_available_stock_items(product_id: int, limit: int = 1) -> list[dict]:
    """Retourne les articles en stock les plus anciens non vendus (FIFO) avec une limite."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM stock_items WHERE product_id = ? AND is_sold = 0 ORDER BY added_at ASC LIMIT ?",
            (product_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def mark_stock_sold(stock_id: int, order_id: int) -> bool:
    _clear_stock_cache()
    """Marque un article comme vendu de maniÃ¨re atomique.
    
    Utilise WHERE is_sold = 0 pour Ã©viter la double-livraison en cas de requÃªtes concurrentes.
    Retourne True si l'article a Ã©tÃ© marquÃ©, False s'il Ã©tait dÃ©jÃ  vendu.
    """
    db = await get_db()
    try:
        cursor = await db.execute(
            "UPDATE stock_items SET is_sold = 1, sold_to_order_id = ?, sold_at = CURRENT_TIMESTAMP WHERE id = ? AND is_sold = 0",
            (order_id, stock_id),
        )
        await db.commit()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def release_stock_item(stock_id: int) -> None:
    _clear_stock_cache()
    """RelÃ¢che un article (annule la vente). UtilisÃ© en cas de livraison partielle Ã©chouÃ©e."""
    db = await get_db()
    try:
        await db.execute(
            "UPDATE stock_items SET is_sold = 0, sold_to_order_id = NULL, sold_at = NULL WHERE id = ?",
            (stock_id,),
        )
        await db.commit()
    finally:
        await db.close()


async def reserve_stock_items_for_order(
    order_id: int,
    product_id: int,
    allowed_statuses: tuple[str, ...] = (
        "PENDING",
        "AWAITING_PAYMENT",
        "PROCESSING",
        "PAID_PENDING_DELIVERY",
    ),
) -> list[dict] | None:
    """Reserve stock once, retrying safely when a Turso stream disappears."""
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            return await _reserve_stock_items_for_order_once(
                order_id,
                product_id,
                allowed_statuses,
            )
        except Exception as exc:
            last_exc = exc
            if not is_transient_db_connection_error(exc) or attempt == 2:
                raise
            logger.warning(
                "Retrying stock reservation for order %s on a fresh connection: %s",
                order_id,
                exc,
            )
            await asyncio.sleep(0.1 * (attempt + 1))
    raise RuntimeError("Stock reservation unavailable") from last_exc


async def _reserve_stock_items_for_order_once(
    order_id: int,
    product_id: int,
    allowed_statuses: tuple[str, ...],
) -> list[dict] | None:
    """Reserve stock for an order once, returning the same items on retries."""
    _clear_stock_cache()
    invalidate_stats_cache()
    db = await get_db(fresh=True)
    try:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            "SELECT id, quantity, status FROM orders WHERE id = ? AND product_id = ?",
            (order_id, product_id),
        )
        order = await cursor.fetchone()
        if not order:
            await db.rollback()
            return None

        quantity = max(1, int(order["quantity"] or 1))

        cursor = await db.execute(
            "SELECT id, account_data FROM stock_items WHERE sold_to_order_id = ? ORDER BY sold_at ASC, id ASC",
            (order_id,),
        )
        existing_items = [dict(r) for r in await cursor.fetchall()]
        if existing_items:
            await db.commit()
            return existing_items

        if order["status"] not in allowed_statuses:
            await db.rollback()
            return None

        cursor = await db.execute(
            "SELECT id, account_data FROM stock_items WHERE product_id = ? AND is_sold = 0 ORDER BY added_at ASC LIMIT ?",
            (product_id, quantity),
        )
        stock_items = [dict(r) for r in await cursor.fetchall()]
        if len(stock_items) < quantity:
            await db.rollback()
            return None

        if stock_items:
            batch_size = 50
            for i in range(0, len(stock_items), batch_size):
                batch = stock_items[i:i+batch_size]
                placeholders = ",".join("?" for _ in batch)
                params = [order_id] + [item["id"] for item in batch]
                cursor = await db.execute(
                    f"UPDATE stock_items SET is_sold = 1, sold_to_order_id = ?, sold_at = CURRENT_TIMESTAMP WHERE id IN ({placeholders}) AND is_sold = 0",
                    params
                )
                if cursor.rowcount != -1 and cursor.rowcount < len(batch):
                    await db.rollback()
                    return None

        await db.execute(
            "UPDATE orders SET stock_item_id = ? WHERE id = ?",
            (stock_items[0]["id"], order_id),
        )
        await db.commit()
        return stock_items
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()


async def get_stock_items_for_product(product_id: int) -> list[dict]:
    """Retourne tous les articles en stock pour un produit (vendus et non vendus)."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM stock_items WHERE product_id = ? ORDER BY added_at DESC",
            (product_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_stock_items_for_order(order_id: int) -> list[dict]:
    """Retourne les articles livrÃ©s pour une commande spÃ©cifique."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM stock_items WHERE sold_to_order_id = ?",
            (order_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def delete_stock_item(stock_id: int) -> None:
    _clear_stock_cache()
    invalidate_stats_cache()
    """Supprime un article du stock (uniquement si non vendu)."""
    db = await get_db()
    try:
        await db.execute(
            "DELETE FROM stock_items WHERE id = ? AND is_sold = 0",
            (stock_id,),
        )
        await db.commit()
    finally:
        await db.close()


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
# â•‘  COMMANDES                                                       â•‘
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


async def create_order(
    user_telegram_id: int,
    product_id: int,
    amount_usd: float,
    quantity: int = 1,
) -> dict:
    _clear_stock_cache()
    invalidate_stats_cache()
    """CrÃ©e une nouvelle commande avec un merchant_trade_no unique et une quantitÃ©."""
    merchant_trade_no = uuid.uuid4().hex[:12].upper()
    db = await get_db()
    try:
        # Cancel any existing PENDING orders for this user (prevent duplicates)
        await db.execute(
            "UPDATE orders SET status = 'CANCELLED' WHERE user_telegram_id = ? AND status = 'PENDING'",
            (user_telegram_id,),
        )
        cursor = await db.execute(
            """INSERT INTO orders
               (user_telegram_id, product_id, amount_usd, merchant_trade_no, status, quantity)
               VALUES (?, ?, ?, ?, 'PENDING', ?)""",
            (user_telegram_id, product_id, amount_usd, merchant_trade_no, quantity),
        )
        await db.commit()
        order_id = cursor.lastrowid
        cursor = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = await cursor.fetchone()
        return dict(row)
    finally:
        await db.close()


async def get_order(order_id: int) -> dict | None:
    """RÃ©cupÃ¨re une commande par son identifiant."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def get_order_by_merchant_id(merchant_trade_no: str) -> dict | None:
    """RÃ©cupÃ¨re une commande par son numÃ©ro de transaction marchand."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM orders WHERE merchant_trade_no = ?", (merchant_trade_no,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def get_total_users_count() -> int:
    db = await get_db()
    try:
        cursor = await db.execute("SELECT COUNT(*) AS cnt FROM users")
        row = await cursor.fetchone()
        return int(row["cnt"] if row else 0)
    finally:
        await db.close()


async def cleanup_product_views(retention_days: int = 90) -> int:
    """Delete analytics rows older than the configured retention period."""
    retention_days = max(7, min(int(retention_days), 3650))
    db = await get_db()
    try:
        cursor = await db.execute(
            "DELETE FROM product_views WHERE viewed_at < datetime('now', ?)",
            (f"-{retention_days} days",),
        )
        await db.commit()
        return max(0, int(cursor.rowcount)) if cursor.rowcount != -1 else 0
    finally:
        await db.close()


async def purchase_order_with_wallet(order_id: int, user_telegram_id: int) -> dict:
    """Debit, reserve stock and finalize a wallet order in one transaction."""
    _clear_stock_cache()
    invalidate_stats_cache()
    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            """SELECT o.*, p.delivery_type
               FROM orders o
               JOIN products p ON p.id = o.product_id
               WHERE o.id = ? AND o.user_telegram_id = ?""",
            (int(order_id), int(user_telegram_id)),
        )
        row = await cursor.fetchone()
        if not row:
            await db.rollback()
            raise ValueError("ORDER_NOT_FOUND")

        order = dict(row)
        if order.get("status") not in ("PENDING", "AWAITING_PAYMENT"):
            await db.rollback()
            raise ValueError(f"ORDER_NOT_PAYABLE:{order.get('status')}")

        amount = round(float(order.get("amount_usd") or 0), 4)
        cursor = await db.execute(
            """UPDATE users
               SET wallet_balance = MAX(0.0, COALESCE(wallet_balance, 0) - ?)
               WHERE telegram_id = ?
                 AND COALESCE(wallet_balance, 0) >= ?
               RETURNING wallet_balance""",
            (amount, int(user_telegram_id), amount - 1e-5),
        )
        balance_row = await cursor.fetchone()
        if not balance_row:
            await db.rollback()
            raise ValueError("INSUFFICIENT_BALANCE")
        balance_after = float(balance_row["wallet_balance"])

        quantity = max(1, int(order.get("quantity") or 1))
        delivery_type = order.get("delivery_type") or "stock"
        stock_items: list[dict] = []

        if delivery_type == "activation":
            next_status = "AWAITING_ACTIVATION_INFO"
        elif delivery_type == "supplier_api":
            next_status = "PAID_PENDING_DELIVERY"
        else:
            cursor = await db.execute(
                """SELECT id, account_data
                   FROM stock_items
                   WHERE product_id = ? AND is_sold = 0
                   ORDER BY added_at ASC, id ASC
                   LIMIT ?""",
                (int(order["product_id"]), quantity),
            )
            stock_items = [dict(item) for item in await cursor.fetchall()]
            if len(stock_items) < quantity:
                await db.rollback()
                raise ValueError("INSUFFICIENT_STOCK")

            ids = [int(item["id"]) for item in stock_items]
            placeholders = ",".join("?" for _ in ids)
            cursor = await db.execute(
                f"""UPDATE stock_items
                    SET is_sold = 1,
                        sold_to_order_id = ?,
                        sold_at = CURRENT_TIMESTAMP
                    WHERE id IN ({placeholders}) AND is_sold = 0""",
                [int(order_id), *ids],
            )
            if cursor.rowcount != -1 and cursor.rowcount != len(ids):
                await db.rollback()
                raise ValueError("STOCK_CONFLICT")
            next_status = "COMPLETED"

        await db.execute(
            """INSERT INTO wallet_transactions
               (user_telegram_id, type, amount, balance_after, description)
               VALUES (?, 'purchase', ?, ?, ?)""",
            (int(user_telegram_id), amount, balance_after, f"Order #{int(order_id)}"),
        )

        first_stock_id = stock_items[0]["id"] if stock_items else None
        await db.execute(
            """UPDATE orders
               SET status = ?, payment_method = 'wallet', paid_at = CURRENT_TIMESTAMP,
                   stock_item_id = COALESCE(?, stock_item_id)
               WHERE id = ?""",
            (next_status, first_stock_id, int(order_id)),
        )
        if next_status == "COMPLETED":
            await _apply_completion_effects_tx(
                db,
                order,
                "wallet",
                enforce_promo_limits=True,
            )

        await db.commit()
        order["status"] = next_status
        order["payment_method"] = "wallet"
        order["stock_item_id"] = first_stock_id
        return {
            "order": order,
            "items": stock_items,
            "balance_after": balance_after,
            "delivery_type": delivery_type,
        }
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()


async def cancel_order_if_allowed(order_id: int, allowed_statuses: tuple[str, ...] = ("PENDING", "AWAITING_PAYMENT")) -> dict | None:
    """Cancel only unpaid/payable orders. Returns the cancelled order or None."""
    _clear_stock_cache()
    invalidate_stats_cache()
    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute("SELECT * FROM orders WHERE id = ?", (int(order_id),))
        row = await cursor.fetchone()
        if not row:
            await db.rollback()
            return None
        order = dict(row)
        if order.get("status") == "CANCELLED":
            await db.commit()
            return order
        if order.get("status") not in allowed_statuses:
            await db.rollback()
            raise ValueError(f"Order cannot be cancelled from status {order.get('status')}")
        await db.execute(
            "UPDATE orders SET status = 'CANCELLED' WHERE id = ?",
            (int(order_id),),
        )
        await db.commit()
        order["status"] = "CANCELLED"
        return order
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()


ALLOWED_ORDER_COLUMNS = {
    "binance_order_id",
    "paid_at",
    "payment_method",
    "quantity",
    "amount_usd",
    "promo_code_id",
    "promo_discount",
    "activation_identifier",
    "activation_status",
    "activation_requested_at",
    "activated_at",
}


async def _increment_promo_usage_tx(
    db,
    promo_id: int,
    user_telegram_id: int,
    *,
    enforce_limits: bool = False,
) -> None:
    cursor = await db.execute(
        "SELECT max_uses, max_uses_per_user, used_count FROM promo_codes WHERE id = ? AND is_active = 1",
        (int(promo_id),),
    )
    promo = await cursor.fetchone()
    if not promo:
        if enforce_limits:
            raise ValueError("PROMO_UNAVAILABLE")
        return
    max_uses = int(promo["max_uses"] or 0)
    if enforce_limits and max_uses > 0 and int(promo["used_count"] or 0) >= max_uses:
        raise ValueError("PROMO_GLOBAL_LIMIT_REACHED")

    max_per_user = int(promo["max_uses_per_user"] or 0)
    cursor = await db.execute(
        """SELECT usage_count FROM promo_code_usages
           WHERE promo_code_id = ? AND user_telegram_id = ?""",
        (int(promo_id), int(user_telegram_id)),
    )
    usage = await cursor.fetchone()
    if enforce_limits and max_per_user > 0 and int(usage["usage_count"] if usage else 0) >= max_per_user:
        raise ValueError("PROMO_USER_LIMIT_REACHED")

    await db.execute(
        "UPDATE promo_codes SET used_count = used_count + 1 WHERE id = ?",
        (int(promo_id),),
    )
    await db.execute(
        """INSERT INTO promo_code_usages
           (promo_code_id, user_telegram_id, usage_count, last_used_at)
           VALUES (?, ?, 1, CURRENT_TIMESTAMP)
           ON CONFLICT(promo_code_id, user_telegram_id)
           DO UPDATE SET usage_count = usage_count + 1,
                         last_used_at = CURRENT_TIMESTAMP""",
        (int(promo_id), int(user_telegram_id)),
    )


async def _apply_completion_effects_tx(
    db,
    order: dict,
    payment_method: str | None,
    *,
    enforce_promo_limits: bool = False,
) -> None:
    amount_usd = float(order.get("amount_usd") or 0)
    telegram_id = order.get("user_telegram_id")
    if telegram_id:
        await db.execute(
            """UPDATE users
               SET total_orders = COALESCE(total_orders, 0) + 1,
                   total_spent = COALESCE(total_spent, 0) + ?
               WHERE telegram_id = ?""",
            (amount_usd, int(telegram_id)),
        )

    promo_id = order.get("promo_code_id")
    if promo_id and telegram_id:
        await _increment_promo_usage_tx(
            db,
            int(promo_id),
            int(telegram_id),
            enforce_limits=enforce_promo_limits,
        )

    if payment_method != "wallet":
        method_suffix = {
            "bep20": "bep20",
            "nowpayments_bep20": "bep20",
            "trc20": "trc20",
            "binance_pay": "binance",
            "binance": "binance",
            "manual": "binance",
        }.get((payment_method or "binance").lower(), "binance")
        setting_key = f"finance_bot_balance_{method_suffix}"
        await db.execute(
            """INSERT INTO settings (key, value) VALUES (?, ?)
               ON CONFLICT(key) DO UPDATE SET
                   value = CAST(COALESCE(settings.value, '0') AS REAL) + CAST(excluded.value AS REAL)""",
            (setting_key, str(amount_usd)),
        )


async def update_order_status(
    order_id: int,
    status: str,
    *,
    expected_statuses: tuple[str, ...] | None = None,
    **kwargs,
) -> bool:
    """Update an order atomically, retrying safely on a fresh Turso stream."""
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            return await _update_order_status_once(
                order_id,
                status,
                expected_statuses=expected_statuses,
                **kwargs,
            )
        except Exception as exc:
            last_exc = exc
            if not is_transient_db_connection_error(exc) or attempt == 2:
                raise
            logger.warning(
                "Retrying status update for order %s on a fresh connection: %s",
                order_id,
                exc,
            )
            await asyncio.sleep(0.1 * (attempt + 1))
    raise RuntimeError("Order status update unavailable") from last_exc


async def _update_order_status_once(
    order_id: int,
    status: str,
    *,
    expected_statuses: tuple[str, ...] | None = None,
    **kwargs,
) -> bool:
    _clear_stock_cache()
    invalidate_stats_cache()
    """Met Ã  jour le statut d'une commande avec des champs optionnels."""
    set_parts = ["status = ?"]
    values: list = [status]
    safe_kwargs = {k: v for k, v in kwargs.items() if k in ALLOWED_ORDER_COLUMNS}
    for key, val in safe_kwargs.items():
        set_parts.append(f"{key} = ?")
        values.append(val)
    values.append(order_id)
    db = await get_db(fresh=True)
    try:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = await cursor.fetchone()
        if not row:
            await db.rollback()
            return False
        current_order = dict(row)
        if expected_statuses is not None and current_order.get("status") not in expected_statuses:
            await db.rollback()
            return False

        transitioned = current_order.get("status") != status
        if status == "COMPLETED" and "paid_at" not in safe_kwargs:
            set_parts.append("paid_at = COALESCE(paid_at, CURRENT_TIMESTAMP)")
        await db.execute(
            f"UPDATE orders SET {', '.join(set_parts)} WHERE id = ?", values
        )
        if status == "COMPLETED" and transitioned:
            pay_method = kwargs.get("payment_method") or current_order.get("payment_method")
            await _apply_completion_effects_tx(db, current_order, pay_method)

        await db.commit()
        return transitioned
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()


_NOWPAYMENTS_ACTIVE_STATUSES = (
    "creating",
    "creation_unknown",
    "waiting",
    "confirming",
    "confirmed",
    "sending",
    "spending",
    "partially_paid",
)


async def prepare_nowpayments_attempt(order_id: int, price_amount: float) -> dict:
    """Create one provider attempt or return the existing active attempt."""
    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        placeholders = ",".join("?" for _ in _NOWPAYMENTS_ACTIVE_STATUSES)
        cursor = await db.execute(
            f"""SELECT * FROM nowpayments_payments
                WHERE order_id = ? AND provider_status IN ({placeholders})
                ORDER BY id DESC LIMIT 1""",
            (int(order_id), *_NOWPAYMENTS_ACTIVE_STATUSES),
        )
        existing = await cursor.fetchone()
        if existing:
            await db.commit()
            result = dict(existing)
            result["created"] = False
            return result

        request_key = f"np-{int(order_id)}-{uuid.uuid4().hex}"
        cursor = await db.execute(
            """INSERT INTO nowpayments_payments
               (order_id, request_key, provider_status, price_amount, price_currency, pay_currency)
               VALUES (?, ?, 'creating', ?, 'usd', 'usdtbsc')""",
            (int(order_id), request_key, round(float(price_amount), 2)),
        )
        attempt_id = cursor.lastrowid
        await db.commit()
        cursor = await db.execute("SELECT * FROM nowpayments_payments WHERE id = ?", (attempt_id,))
        result = dict(await cursor.fetchone())
        result["created"] = True
        return result
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()


async def attach_nowpayments_payment(request_key: str, payload: dict) -> dict:
    payment_id = str(payload.get("payment_id") or "").strip()
    if not payment_id:
        raise ValueError("NOWPAYMENTS_PAYMENT_ID_MISSING")

    provider_status = str(payload.get("payment_status") or "waiting").lower()
    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            """UPDATE nowpayments_payments SET
                   payment_id = ?, provider_status = ?, pay_amount = ?, pay_currency = ?,
                   pay_address = ?, network = ?, valid_until = ?, raw_payload = ?,
                   updated_at = CURRENT_TIMESTAMP, processing_error = NULL
               WHERE request_key = ? AND payment_id IS NULL
               RETURNING *""",
            (
                payment_id,
                provider_status,
                float(payload.get("pay_amount") or 0),
                str(payload.get("pay_currency") or "usdtbsc").lower(),
                str(payload.get("pay_address") or ""),
                str(payload.get("network") or ""),
                payload.get("valid_until") or payload.get("expiration_estimate_date"),
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                request_key,
            ),
        )
        row = await cursor.fetchone()
        if not row:
            cursor = await db.execute(
                "SELECT * FROM nowpayments_payments WHERE request_key = ?",
                (request_key,),
            )
            row = await cursor.fetchone()
        await db.commit()
        if not row:
            raise ValueError("NOWPAYMENTS_ATTEMPT_NOT_FOUND")
        return dict(row)
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()


async def mark_nowpayments_creation_failed(request_key: str, *, uncertain: bool, error: str) -> None:
    db = await get_db()
    try:
        await db.execute(
            """UPDATE nowpayments_payments
               SET provider_status = ?, processing_error = ?, updated_at = CURRENT_TIMESTAMP
               WHERE request_key = ? AND payment_id IS NULL""",
            ("creation_unknown" if uncertain else "creation_failed", str(error)[:500], request_key),
        )
        await db.commit()
    finally:
        await db.close()


async def get_nowpayments_payment_for_order(order_id: int) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM nowpayments_payments WHERE order_id = ? ORDER BY id DESC LIMIT 1",
            (int(order_id),),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def get_nowpayments_payment(payment_id: str | int) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM nowpayments_payments WHERE payment_id = ?",
            (str(payment_id),),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def save_nowpayments_update(payload: dict) -> dict | None:
    """Persist a provider update, retrying safely on a fresh Turso stream."""
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            return await _save_nowpayments_update_once(payload)
        except Exception as exc:
            last_exc = exc
            if not is_transient_db_connection_error(exc) or attempt == 2:
                raise
            logger.info(
                "Retrying NOWPayments status update for %s on a fresh connection: %s",
                payload.get("payment_id"),
                exc,
            )
            await asyncio.sleep(0.1 * (attempt + 1))
    raise RuntimeError("NOWPayments status update unavailable") from last_exc


async def _save_nowpayments_update_once(payload: dict) -> dict | None:
    """Persist an authenticated provider update before asynchronous processing."""
    payment_id = str(payload.get("payment_id") or "").strip()
    if not payment_id:
        return None
    provider_status = str(payload.get("payment_status") or "").strip().lower()
    if not provider_status:
        return None

    db = await get_db(fresh=True)
    try:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            "SELECT * FROM nowpayments_payments WHERE payment_id = ?",
            (payment_id,),
        )
        existing = await cursor.fetchone()
        if not existing:
            await db.rollback()
            return None
        existing = dict(existing)
        callback_order_id = str(payload.get("order_id") or "").strip()
        if callback_order_id and callback_order_id != str(existing["order_id"]):
            await db.rollback()
            raise ValueError("NOWPAYMENTS_ORDER_MISMATCH")

        old_status = str(existing.get("provider_status") or "")
        status_rank = {
            "creating": 0,
            "creation_unknown": 0,
            "waiting": 1,
            "confirming": 2,
            "confirmed": 3,
            "sending": 4,
            "spending": 4,
            "partially_paid": 4,
            "finished": 5,
            "failed": 5,
            "refunded": 5,
            "expired": 5,
        }
        if provider_status != "finished" and status_rank.get(provider_status, 0) < status_rank.get(old_status, 0):
            provider_status = old_status
        cursor = await db.execute(
            """UPDATE nowpayments_payments SET
                   provider_status = ?,
                   pay_amount = COALESCE(?, pay_amount),
                   pay_currency = COALESCE(?, pay_currency),
                   pay_address = COALESCE(?, pay_address),
                   actually_paid = MAX(COALESCE(actually_paid, 0), ?),
                   network = COALESCE(?, network),
                   valid_until = COALESCE(?, valid_until),
                   raw_payload = ?,
                   updated_at = CURRENT_TIMESTAMP,
                   notified_at = CASE WHEN provider_status != ? THEN NULL ELSE notified_at END
               WHERE payment_id = ?
               RETURNING *""",
            (
                provider_status,
                float(payload["pay_amount"]) if payload.get("pay_amount") is not None else None,
                str(payload.get("pay_currency")).lower() if payload.get("pay_currency") else None,
                str(payload.get("pay_address")) if payload.get("pay_address") else None,
                float(payload.get("actually_paid") or 0),
                str(payload.get("network")) if payload.get("network") else None,
                payload.get("valid_until") or payload.get("expiration_estimate_date"),
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                provider_status,
                payment_id,
            ),
        )
        row = await cursor.fetchone()
        await db.commit()
        result = dict(row)
        result["status_changed"] = old_status != provider_status
        return result
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()


async def finalize_nowpayments_payment(payment_id: str | int) -> dict:
    """Retry idempotent payment finalization when a Turso stream expires."""
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            return await _finalize_nowpayments_payment_once(payment_id)
        except Exception as exc:
            last_exc = exc
            if not is_transient_db_connection_error(exc) or attempt == 2:
                raise
            logger.warning(
                "Retrying NOWPayments finalization for %s on a fresh Turso connection: %s",
                payment_id,
                exc,
            )
            await asyncio.sleep(0.15 * (attempt + 1))
    raise RuntimeError("NOWPayments finalization unavailable") from last_exc


async def _finalize_nowpayments_payment_once(payment_id: str | int) -> dict:
    """Finalize a finished provider payment exactly once, including stock and finance."""
    _clear_stock_cache()
    invalidate_stats_cache()
    db = await get_db(fresh=True)
    try:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            """SELECT np.*, o.user_telegram_id, o.product_id, o.quantity,
                      o.amount_usd, o.status AS order_status, o.payment_method,
                      o.promo_code_id, p.delivery_type, p.name AS product_name,
                      p.warranty_days
               FROM nowpayments_payments np
               JOIN orders o ON o.id = np.order_id
               JOIN products p ON p.id = o.product_id
               WHERE np.payment_id = ?""",
            (str(payment_id),),
        )
        row = await cursor.fetchone()
        if not row:
            await db.rollback()
            return {"action": "unknown"}
        payment = dict(row)
        provider_status = str(payment.get("provider_status") or "").lower()
        if provider_status != "finished":
            await db.commit()
            return {"action": provider_status or "waiting", "payment": payment}

        expected_currency = str(payment.get("pay_currency") or "").lower()
        expected_pay_amount = float(payment.get("pay_amount") or 0)
        actually_paid = float(payment.get("actually_paid") or 0)
        expected_price = round(float(payment.get("amount_usd") or 0), 2)
        from services.nowpayments import calculate_checkout_price
        expected_checkout_price = calculate_checkout_price(expected_price)
        stored_price = round(float(payment.get("price_amount") or 0), 2)
        error = None
        if expected_currency != "usdtbsc":
            error = f"Unexpected pay currency: {expected_currency or 'missing'}"
        elif min(
            abs(stored_price - expected_price),
            abs(stored_price - expected_checkout_price),
        ) > 0.01:
            error = (
                f"Order amount mismatch: expected {expected_checkout_price:.2f} "
                f"(legacy {expected_price:.2f}), stored {stored_price:.2f}"
            )
        elif expected_pay_amount <= 0 or actually_paid + 0.000001 < expected_pay_amount:
            error = f"Insufficient provider amount: paid {actually_paid}, expected {expected_pay_amount}"

        if error:
            await db.execute(
                "UPDATE nowpayments_payments SET processing_error = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (error, int(payment["id"])),
            )
            await db.commit()
            payment["processing_error"] = error
            return {"action": "review_required", "payment": payment}

        order_status = str(payment.get("order_status") or "")
        payment_method = str(payment.get("payment_method") or "")
        if order_status == "COMPLETED" and payment_method != "nowpayments_bep20":
            error = f"Order already completed with {payment_method or 'another method'}"
            await db.execute(
                "UPDATE nowpayments_payments SET processing_error = ? WHERE id = ?",
                (error, int(payment["id"])),
            )
            await db.commit()
            return {"action": "review_required", "payment": payment}

        cursor = await db.execute(
            "SELECT id, account_data FROM stock_items WHERE sold_to_order_id = ? ORDER BY id ASC",
            (int(payment["order_id"]),),
        )
        items = [dict(item) for item in await cursor.fetchall()]
        already_processed = payment.get("processed_at") is not None
        if already_processed:
            await db.commit()
            if order_status in ("AWAITING_ACTIVATION_INFO", "AWAITING_ACTIVATION"):
                action = "activation"
            elif order_status == "PAID_PENDING_DELIVERY":
                action = "paid_pending_delivery"
            else:
                action = "completed"
            return {"action": action, "payment": payment, "items": items, "already_processed": True}

        delivery_type = str(payment.get("delivery_type") or "stock")
        if delivery_type == "activation":
            next_status = order_status if order_status in ("AWAITING_ACTIVATION_INFO", "AWAITING_ACTIVATION") else "AWAITING_ACTIVATION_INFO"
            await db.execute(
                """UPDATE orders SET status = ?, payment_method = 'nowpayments_bep20',
                          binance_order_id = ?, paid_at = COALESCE(paid_at, CURRENT_TIMESTAMP)
                   WHERE id = ?""",
                (next_status, str(payment_id), int(payment["order_id"])),
            )
            await db.execute(
                "UPDATE nowpayments_payments SET processed_at = CURRENT_TIMESTAMP, processing_error = NULL WHERE id = ?",
                (int(payment["id"]),),
            )
            await db.commit()
            payment["order_status"] = next_status
            return {"action": "activation", "payment": payment, "items": []}

        if delivery_type == "supplier_api":
            await db.execute(
                """UPDATE orders SET status = 'PAID_PENDING_DELIVERY', payment_method = 'nowpayments_bep20',
                          binance_order_id = ?, paid_at = COALESCE(paid_at, CURRENT_TIMESTAMP)
                   WHERE id = ?""",
                (str(payment_id), int(payment["order_id"])),
            )
            await db.execute(
                "UPDATE nowpayments_payments SET processed_at = CURRENT_TIMESTAMP, processing_error = NULL WHERE id = ?",
                (int(payment["id"]),),
            )
            await db.commit()
            payment["order_status"] = "PAID_PENDING_DELIVERY"
            return {"action": "paid_pending_delivery", "payment": payment, "items": []}

        quantity = max(1, int(payment.get("quantity") or 1))
        if not items:
            cursor = await db.execute(
                """SELECT id, account_data FROM stock_items
                   WHERE product_id = ? AND is_sold = 0
                   ORDER BY added_at ASC, id ASC LIMIT ?""",
                (int(payment["product_id"]), quantity),
            )
            items = [dict(item) for item in await cursor.fetchall()]
            if len(items) < quantity:
                await db.execute(
                    """UPDATE orders SET status = 'PAID_PENDING_DELIVERY',
                              payment_method = 'nowpayments_bep20', binance_order_id = ?,
                              paid_at = COALESCE(paid_at, CURRENT_TIMESTAMP)
                       WHERE id = ?""",
                    (str(payment_id), int(payment["order_id"])),
                )
                await db.execute(
                    """UPDATE nowpayments_payments SET processed_at = CURRENT_TIMESTAMP,
                              processing_error = 'Insufficient stock after confirmed payment'
                       WHERE id = ?""",
                    (int(payment["id"]),),
                )
                await db.commit()
                payment["order_status"] = "PAID_PENDING_DELIVERY"
                return {"action": "paid_pending_delivery", "payment": payment, "items": []}

            ids = [int(item["id"]) for item in items]
            placeholders = ",".join("?" for _ in ids)
            cursor = await db.execute(
                f"""UPDATE stock_items SET is_sold = 1, sold_to_order_id = ?, sold_at = CURRENT_TIMESTAMP
                    WHERE id IN ({placeholders}) AND is_sold = 0""",
                [int(payment["order_id"]), *ids],
            )
            if cursor.rowcount != -1 and cursor.rowcount != len(ids):
                await db.rollback()
                raise ValueError("NOWPAYMENTS_STOCK_CONFLICT")

        first_stock_id = items[0]["id"] if items else None
        transitioned = order_status != "COMPLETED"
        await db.execute(
            """UPDATE orders SET status = 'COMPLETED', payment_method = 'nowpayments_bep20',
                      binance_order_id = ?, paid_at = COALESCE(paid_at, CURRENT_TIMESTAMP),
                      stock_item_id = COALESCE(?, stock_item_id)
               WHERE id = ?""",
            (str(payment_id), first_stock_id, int(payment["order_id"])),
        )
        if transitioned:
            await _apply_completion_effects_tx(db, payment, "nowpayments_bep20")
        await db.execute(
            "UPDATE nowpayments_payments SET processed_at = CURRENT_TIMESTAMP, processing_error = NULL WHERE id = ?",
            (int(payment["id"]),),
        )
        await db.commit()
        payment["order_status"] = "COMPLETED"
        return {"action": "completed", "payment": payment, "items": items}
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()


async def mark_nowpayments_notified(payment_id: str | int) -> None:
    db = await get_db()
    try:
        await db.execute(
            """UPDATE nowpayments_payments
               SET notified_at = CURRENT_TIMESTAMP, notification_claimed_at = NULL
               WHERE payment_id = ?""",
            (str(payment_id),),
        )
        await db.commit()
    finally:
        await db.close()


async def claim_nowpayments_notification(payment_id: str | int) -> bool:
    db = await get_db()
    try:
        cursor = await db.execute(
            """UPDATE nowpayments_payments
               SET notification_claimed_at = CURRENT_TIMESTAMP
               WHERE payment_id = ? AND notified_at IS NULL
                 AND (notification_claimed_at IS NULL
                      OR notification_claimed_at <= datetime('now', '-5 minutes'))
               RETURNING id""",
            (str(payment_id),),
        )
        row = await cursor.fetchone()
        await db.commit()
        return row is not None
    finally:
        await db.close()


async def release_nowpayments_notification(payment_id: str | int) -> None:
    db = await get_db()
    try:
        await db.execute(
            """UPDATE nowpayments_payments SET notification_claimed_at = NULL
               WHERE payment_id = ? AND notified_at IS NULL""",
            (str(payment_id),),
        )
        await db.commit()
    finally:
        await db.close()


async def list_nowpayments_to_finalize(limit: int = 25) -> list[dict]:
    """Read finalizable payments with a fresh-connection retry."""
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            return await _list_nowpayments_to_finalize_once(limit)
        except Exception as exc:
            last_exc = exc
            if not is_transient_db_connection_error(exc) or attempt == 2:
                raise
            logger.info("Retrying NOWPayments finalization queue read: %s", exc)
            await asyncio.sleep(0.1 * (attempt + 1))
    raise RuntimeError("NOWPayments finalization queue unavailable") from last_exc


async def _list_nowpayments_to_finalize_once(limit: int = 25) -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT * FROM nowpayments_payments
               WHERE provider_status = 'finished'
                 AND ((processed_at IS NULL AND processing_error IS NULL) OR notified_at IS NULL)
               ORDER BY updated_at ASC LIMIT ?""",
            (max(1, min(int(limit), 100)),),
        )
        return [dict(row) for row in await cursor.fetchall()]
    finally:
        await db.close()


async def list_nowpayments_to_poll(limit: int = 20) -> list[dict]:
    """Read pollable payments with a fresh-connection retry."""
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            return await _list_nowpayments_to_poll_once(limit)
        except Exception as exc:
            last_exc = exc
            if not is_transient_db_connection_error(exc) or attempt == 2:
                raise
            logger.info("Retrying NOWPayments polling queue read: %s", exc)
            await asyncio.sleep(0.1 * (attempt + 1))
    raise RuntimeError("NOWPayments polling queue unavailable") from last_exc


async def _list_nowpayments_to_poll_once(limit: int = 20) -> list[dict]:
    db = await get_db()
    try:
        placeholders = ",".join("?" for _ in _NOWPAYMENTS_ACTIVE_STATUSES[2:])
        cursor = await db.execute(
            f"""SELECT * FROM nowpayments_payments
                WHERE payment_id IS NOT NULL
                  AND provider_status IN ({placeholders})
                  AND updated_at <= datetime('now', '-60 seconds')
                ORDER BY updated_at ASC LIMIT ?""",
            (*_NOWPAYMENTS_ACTIVE_STATUSES[2:], max(1, min(int(limit), 50))),
        )
        return [dict(row) for row in await cursor.fetchall()]
    finally:
        await db.close()


async def recover_stale_processing_wallet_orders(age_minutes: int = 5) -> dict[str, int]:
    """Recover wallet orders left in PROCESSING by an older interrupted deployment."""
    age_minutes = max(1, min(int(age_minutes), 1440))
    result = {"completed": 0, "activation": 0, "refunded": 0, "cancelled": 0}
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT id FROM orders
               WHERE status = 'PROCESSING'
                 AND payment_method = 'wallet'
                 AND created_at <= datetime('now', ?)""",
            (f"-{age_minutes} minutes",),
        )
        order_ids = [int(row["id"]) for row in await cursor.fetchall()]
    finally:
        await db.close()

    for order_id in order_ids:
        db = await get_db()
        try:
            await db.execute("BEGIN IMMEDIATE")
            cursor = await db.execute(
                """SELECT o.*, p.delivery_type
                   FROM orders o
                   JOIN products p ON p.id = o.product_id
                   WHERE o.id = ? AND o.status = 'PROCESSING' AND o.payment_method = 'wallet'""",
                (order_id,),
            )
            row = await cursor.fetchone()
            if not row:
                await db.rollback()
                continue
            order = dict(row)

            cursor = await db.execute(
                """SELECT id FROM wallet_transactions
                   WHERE user_telegram_id = ? AND type = 'purchase' AND description = ?
                   LIMIT 1""",
                (int(order["user_telegram_id"]), f"Order #{order_id}"),
            )
            debit = await cursor.fetchone()
            if not debit:
                await db.execute("UPDATE orders SET status = 'CANCELLED' WHERE id = ?", (order_id,))
                await db.commit()
                result["cancelled"] += 1
                continue

            if (order.get("delivery_type") or "stock") == "activation":
                await db.execute(
                    "UPDATE orders SET status = 'AWAITING_ACTIVATION_INFO', paid_at = COALESCE(paid_at, CURRENT_TIMESTAMP) WHERE id = ?",
                    (order_id,),
                )
                await db.commit()
                result["activation"] += 1
                continue

            quantity = max(1, int(order.get("quantity") or 1))
            cursor = await db.execute(
                "SELECT id, account_data FROM stock_items WHERE sold_to_order_id = ? ORDER BY id ASC",
                (order_id,),
            )
            items = [dict(item) for item in await cursor.fetchall()]
            missing = quantity - len(items)
            if missing > 0:
                cursor = await db.execute(
                    """SELECT id, account_data FROM stock_items
                       WHERE product_id = ? AND is_sold = 0
                       ORDER BY added_at ASC, id ASC LIMIT ?""",
                    (int(order["product_id"]), missing),
                )
                available = [dict(item) for item in await cursor.fetchall()]
                if len(available) == missing:
                    ids = [int(item["id"]) for item in available]
                    placeholders = ",".join("?" for _ in ids)
                    await db.execute(
                        f"""UPDATE stock_items SET is_sold = 1, sold_to_order_id = ?, sold_at = CURRENT_TIMESTAMP
                            WHERE id IN ({placeholders}) AND is_sold = 0""",
                        [order_id, *ids],
                    )
                    items.extend(available)

            if len(items) >= quantity:
                await db.execute(
                    """UPDATE orders SET status = 'COMPLETED', paid_at = COALESCE(paid_at, CURRENT_TIMESTAMP),
                              stock_item_id = COALESCE(stock_item_id, ?)
                       WHERE id = ?""",
                    (items[0]["id"], order_id),
                )
                await _apply_completion_effects_tx(db, order, "wallet")
                await db.commit()
                result["completed"] += 1
                continue

            refund_description = f"Refund: interrupted wallet order #{order_id}"
            cursor = await db.execute(
                "SELECT id FROM wallet_transactions WHERE user_telegram_id = ? AND description = ? LIMIT 1",
                (int(order["user_telegram_id"]), refund_description),
            )
            if not await cursor.fetchone():
                cursor = await db.execute(
                    """UPDATE users SET wallet_balance = COALESCE(wallet_balance, 0) + ?
                       WHERE telegram_id = ? RETURNING wallet_balance""",
                    (float(order["amount_usd"]), int(order["user_telegram_id"])),
                )
                balance = await cursor.fetchone()
                await db.execute(
                    """INSERT INTO wallet_transactions
                       (user_telegram_id, type, amount, balance_after, description)
                       VALUES (?, 'topup', ?, ?, ?)""",
                    (
                        int(order["user_telegram_id"]),
                        float(order["amount_usd"]),
                        float(balance["wallet_balance"]),
                        refund_description,
                    ),
                )
            await db.execute("UPDATE orders SET status = 'CANCELLED' WHERE id = ?", (order_id,))
            await db.commit()
            result["refunded"] += 1
        except Exception:
            try:
                await db.rollback()
            except Exception:
                pass
            logger.exception("Could not recover stale wallet order %s", order_id)
        finally:
            await db.close()

    if any(result.values()):
        _clear_stock_cache()
        invalidate_stats_cache()
    return result


async def cancel_all_pending_orders(user_telegram_id: int) -> int:
    """Cancel pending orders, retrying safely after a stale Turso stream."""
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            return await _cancel_all_pending_orders_once(user_telegram_id)
        except Exception as exc:
            last_exc = exc
            if not is_transient_db_connection_error(exc) or attempt == 2:
                raise
            logger.info(
                "Retrying pending-order cancellation for user %s on a fresh connection: %s",
                user_telegram_id,
                exc,
            )
            await asyncio.sleep(0.1 * (attempt + 1))
    raise RuntimeError("Pending-order cancellation unavailable") from last_exc


async def _cancel_all_pending_orders_once(user_telegram_id: int) -> int:
    _clear_stock_cache()
    invalidate_stats_cache()
    """Cancel all PENDING and AWAITING_PAYMENT orders for a user. Returns count cancelled."""
    db = await get_db(fresh=True)
    try:
        cursor = await db.execute(
            "UPDATE orders SET status = 'CANCELLED' WHERE user_telegram_id = ? AND status IN ('PENDING', 'AWAITING_PAYMENT')",
            (user_telegram_id,),
        )
        await db.commit()
        return cursor.rowcount if cursor.rowcount > 0 else 0
    finally:
        await db.close()


async def set_order_binance_id(order_id: int, binance_order_id: str) -> None:
    """Enregistre l'identifiant de commande Binance sur la commande."""
    db = await get_db()
    try:
        await db.execute(
            "UPDATE orders SET binance_order_id = ? WHERE id = ?",
            (binance_order_id, order_id),
        )
        await db.commit()
    finally:
        await db.close()


async def set_order_stock(order_id: int, stock_item_id: int) -> None:
    """Associe un article en stock Ã  une commande."""
    db = await get_db()
    try:
        await db.execute(
            "UPDATE orders SET stock_item_id = ? WHERE id = ?",
            (stock_item_id, order_id),
        )
        await db.commit()
    finally:
        await db.close()


async def get_user_orders(
    telegram_id: int,
    limit: int = 10,
    offset: int = 0,
) -> list[dict]:
    """Retourne les commandes d'un utilisateur avec pagination, incluant le nom et l'emoji du produit."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT o.*, p.name as product_name, p.emoji as product_emoji
               FROM orders o
               LEFT JOIN products p ON o.product_id = p.id
               WHERE o.user_telegram_id = ?
               ORDER BY o.created_at DESC LIMIT ? OFFSET ?""",
            (telegram_id, limit, offset),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_user_order_count(telegram_id: int) -> int:
    """Retourne le nombre total de commandes d'un utilisateur."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM orders WHERE user_telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        return row["cnt"]
    finally:
        await db.close()


async def get_pending_orders() -> list[dict]:
    """Retourne toutes les commandes en attente de paiement."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT * FROM orders
               WHERE status IN ('PENDING', 'AWAITING_PAYMENT', 'PAID_PENDING_DELIVERY')
               ORDER BY created_at ASC"""
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_pending_activation_order_for_user(user_telegram_id: int) -> dict | None:
    """Return the latest paid activation order waiting for the user's identifier."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT o.*, p.name as product_name, p.emoji as product_emoji
               FROM orders o
               LEFT JOIN products p ON o.product_id = p.id
               WHERE o.user_telegram_id = ?
                 AND o.status = 'AWAITING_ACTIVATION_INFO'
               ORDER BY o.created_at DESC
               LIMIT 1""",
            (user_telegram_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def submit_activation_identifier(order_id: int, identifier: str) -> bool:
    """Store the customer identifier and move the order to admin activation."""
    invalidate_stats_cache()
    db = await get_db()
    try:
        cursor = await db.execute(
            """UPDATE orders
               SET status = 'AWAITING_ACTIVATION',
                   activation_identifier = ?,
                   activation_status = 'pending',
                   activation_requested_at = ?
               WHERE id = ? AND status = 'AWAITING_ACTIVATION_INFO'
               RETURNING id""",
            (identifier, _utcnow().isoformat(), order_id),
        )
        updated = await cursor.fetchone()
        await db.commit()
        return updated is not None
    finally:
        await db.close()


async def get_stats(days: int = 30, method: str = None) -> dict:
    now = _utcnow().timestamp()
    cache_key = f"{days}_{method}"
    if cache_key in _GET_STATS_CACHE:
        cache_time, cached_data = _GET_STATS_CACHE[cache_key]
        if now - cache_time < _GET_STATS_CACHE_TTL:
            return cached_data
            
    data = await _get_stats_uncached(days, method)
    _GET_STATS_CACHE[cache_key] = (now, data)
    return data


async def get_dashboard_overview() -> dict:
    """Return the compact operational summary used by the dashboard home."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT
                   COALESCE(SUM(CASE WHEN status IN ('PENDING', 'AWAITING_PAYMENT') THEN 1 ELSE 0 END), 0) AS pending_payments,
                   COALESCE(SUM(CASE WHEN status IN ('AWAITING_ACTIVATION_INFO', 'AWAITING_ACTIVATION') THEN 1 ELSE 0 END), 0) AS pending_activations,
                   COALESCE(SUM(CASE WHEN status = 'PAID_PENDING_DELIVERY' THEN 1 ELSE 0 END), 0) AS delivery_issues,
                   COALESCE(SUM(CASE WHEN status = 'COMPLETED' AND DATE(created_at) = DATE('now') THEN 1 ELSE 0 END), 0) AS today_orders,
                   COALESCE(SUM(CASE WHEN status = 'COMPLETED' AND DATE(created_at) = DATE('now') THEN amount_usd ELSE 0 END), 0) AS today_revenue,
                   COALESCE(SUM(CASE WHEN status = 'COMPLETED' AND DATE(created_at) = DATE('now', '-1 day') THEN 1 ELSE 0 END), 0) AS yesterday_orders,
                   COALESCE(SUM(CASE WHEN status = 'COMPLETED' AND DATE(created_at) = DATE('now', '-1 day') THEN amount_usd ELSE 0 END), 0) AS yesterday_revenue
               FROM orders"""
        )
        summary = dict(await cursor.fetchone())

        cursor = await db.execute(
            "SELECT COUNT(*) AS cnt FROM support_tickets WHERE status = 'OPEN'"
        )
        ticket_row = await cursor.fetchone()

        cursor = await db.execute(
            """SELECT o.id, o.user_telegram_id, o.amount_usd, o.quantity,
                      o.status, o.payment_method, o.created_at,
                      u.username, u.first_name AS user_first_name,
                      p.name AS product_name, p.emoji AS product_emoji
               FROM orders o
               LEFT JOIN users u ON u.telegram_id = o.user_telegram_id
               LEFT JOIN products p ON p.id = o.product_id
               ORDER BY o.created_at DESC
               LIMIT 8"""
        )
        recent_orders = [dict(row) for row in await cursor.fetchall()]

        return {
            "today": {
                "orders": int(summary.get("today_orders") or 0),
                "revenue": float(summary.get("today_revenue") or 0),
            },
            "yesterday": {
                "orders": int(summary.get("yesterday_orders") or 0),
                "revenue": float(summary.get("yesterday_revenue") or 0),
            },
            "actions": {
                "pending_payments": int(summary.get("pending_payments") or 0),
                "pending_activations": int(summary.get("pending_activations") or 0),
                "delivery_issues": int(summary.get("delivery_issues") or 0),
                "open_tickets": int(ticket_row["cnt"] if ticket_row else 0),
            },
            "recent_orders": recent_orders,
        }
    finally:
        await db.close()

async def _get_stats_uncached(days: int = 30, method: str = None) -> dict:
    """Return dashboard statistics with four grouped database queries."""
    since = (_utcnow() - timedelta(days=days)).isoformat()
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT
                   COUNT(*) AS total_orders,
                   COALESCE(SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END), 0) AS completed_orders,
                   COALESCE(SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END), 0) AS pending_orders,
                   COALESCE(SUM(CASE WHEN status = 'COMPLETED'
                                      AND (payment_method IS NULL OR payment_method != 'wallet')
                                     THEN amount_usd ELSE 0 END), 0) AS order_revenue,
                   COALESCE(SUM(CASE WHEN status = 'COMPLETED'
                                      AND (payment_method IS NULL OR payment_method IN ('binance', 'binance_pay'))
                                     THEN amount_usd ELSE 0 END), 0) AS sales_binance,
                   COALESCE(SUM(CASE WHEN status = 'COMPLETED' AND payment_method IN ('bep20', 'nowpayments_bep20')
                                     THEN amount_usd ELSE 0 END), 0) AS sales_bep20,
                   COALESCE(SUM(CASE WHEN status = 'COMPLETED' AND payment_method = 'trc20'
                                     THEN amount_usd ELSE 0 END), 0) AS sales_trc20,
                   COALESCE(SUM(CASE WHEN status = 'COMPLETED' AND payment_method = 'wallet'
                                     THEN amount_usd ELSE 0 END), 0) AS sales_wallet
               FROM orders
               WHERE created_at >= ?""",
            (since,),
        )
        orders = dict(await cursor.fetchone())

        cursor = await db.execute(
            """SELECT
                   COALESCE(SUM(CASE WHEN type = 'topup'
                                      AND description NOT LIKE 'Admin%'
                                      AND description NOT LIKE 'Refund%'
                                     THEN amount ELSE 0 END), 0) AS topup_revenue,
                   COALESCE(SUM(CASE WHEN type = 'purchase' AND description LIKE 'Admin debit%'
                                     THEN amount ELSE 0 END), 0) AS admin_deductions,
                   COALESCE(SUM(CASE WHEN type = 'topup'
                                      AND description NOT LIKE 'Admin%'
                                      AND description NOT LIKE 'Refund%'
                                     THEN 1 ELSE 0 END), 0) AS topup_count
               FROM wallet_transactions
               WHERE created_at >= ?""",
            (since,),
        )
        wallet = dict(await cursor.fetchone())

        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE created_at >= ?", (since,)
        )
        new_users = (await cursor.fetchone())["cnt"]

        cursor = await db.execute(
            """SELECT COUNT(*) as cnt FROM (
                   SELECT user_telegram_id FROM orders
                   WHERE status = 'COMPLETED'
                   GROUP BY user_telegram_id
                   HAVING COUNT(*) >= 2
               )"""
        )
        returning_users = (await cursor.fetchone())["cnt"]

        order_revenue = float(orders["order_revenue"] or 0)
        topup_revenue = float(wallet["topup_revenue"] or 0)
        admin_deductions = float(wallet["admin_deductions"] or 0)

        return {
            "total_orders": int(orders["total_orders"] or 0),
            "total_revenue": order_revenue + topup_revenue - admin_deductions,
            "topup_revenue": topup_revenue,
            "order_revenue": order_revenue,
            "admin_deductions": admin_deductions,
            "completed_orders": int(orders["completed_orders"] or 0),
            "pending_orders": int(orders["pending_orders"] or 0),
            "sales_binance": float(orders["sales_binance"] or 0),
            "sales_bep20": float(orders["sales_bep20"] or 0),
            "sales_trc20": float(orders["sales_trc20"] or 0),
            "sales_wallet": float(orders["sales_wallet"] or 0),
            "topup_count": int(wallet["topup_count"] or 0),
            "new_users": new_users,
            "returning_users": returning_users,
        }
    finally:
        await db.close()


async def get_all_orders_filtered(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
    exclude_activation: bool = False,
) -> tuple[list[dict], int]:
    """Retourne les commandes avec filtre optionnel sur le statut + count total + username."""
    db = await get_db()
    try:
        if status:
            where = "WHERE o.status = ?"
            params: list = [status]
        elif exclude_activation:
            where = "WHERE o.status NOT IN ('AWAITING_ACTIVATION_INFO', 'AWAITING_ACTIVATION')"
            params = []
        else:
            where = ""
            params = []

        # Count total
        cursor = await db.execute(
            f"SELECT COUNT(*) as cnt FROM orders o {where}", params
        )
        total = (await cursor.fetchone())["cnt"]

        # Fetch page with user info and product info
        try:
            cursor = await db.execute(
                f"""SELECT o.*, u.username, u.first_name as user_first_name,
                           p.name as product_name, p.emoji as product_emoji, p.is_deleted as product_is_deleted
                    FROM orders o
                    LEFT JOIN users u ON o.user_telegram_id = u.telegram_id
                    LEFT JOIN products p ON o.product_id = p.id
                    {where} ORDER BY o.created_at DESC LIMIT ? OFFSET ?""",
                params + [limit, offset],
            )
            rows = await cursor.fetchall()
        except Exception:
            # Fallback if product columns or tables have issues (e.g. is_deleted missing from products table)
            cursor = await db.execute(
                f"""SELECT o.*, u.username, u.first_name as user_first_name
                    FROM orders o
                    LEFT JOIN users u ON o.user_telegram_id = u.telegram_id
                    {where} ORDER BY o.created_at DESC LIMIT ? OFFSET ?""",
                params + [limit, offset],
            )
            rows = await cursor.fetchall()
        return [dict(r) for r in rows], total
    finally:
        await db.close()


async def get_activation_orders(limit: int = 100, offset: int = 0) -> tuple[list[dict], int]:
    """Return manual activation orders with user and product details."""
    db = await get_db()
    try:
        where = "WHERE o.status IN ('AWAITING_ACTIVATION_INFO', 'AWAITING_ACTIVATION')"
        cursor = await db.execute(
            f"SELECT COUNT(*) as cnt FROM orders o {where}"
        )
        total = (await cursor.fetchone())["cnt"]

        cursor = await db.execute(
            f"""SELECT o.*, u.username, u.first_name as user_first_name,
                       p.name as product_name, p.emoji as product_emoji, p.is_deleted as product_is_deleted
                FROM orders o
                LEFT JOIN users u ON o.user_telegram_id = u.telegram_id
                LEFT JOIN products p ON o.product_id = p.id
                {where}
                ORDER BY o.created_at DESC
                LIMIT ? OFFSET ?""",
            (limit, offset),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows], total
    finally:
        await db.close()


async def get_all_topups_filtered(
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Retourne les wallet topups formatés comme des commandes pour le dashboard."""
    db = await get_db()
    try:
        # Count total topups (exclude admin credits & refunds)
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM wallet_transactions WHERE type = 'topup' AND description NOT LIKE 'Admin%' AND description NOT LIKE 'Refund%'"
        )
        total = (await cursor.fetchone())["cnt"]

        # Fetch topups with user info
        cursor = await db.execute(
            """SELECT wt.id, wt.user_telegram_id, wt.amount, wt.balance_after,
                      wt.description, wt.created_at, wt.type,
                      u.username, u.first_name as user_first_name
               FROM wallet_transactions wt
               LEFT JOIN users u ON wt.user_telegram_id = u.telegram_id
               WHERE wt.type = 'topup'
                 AND wt.description NOT LIKE 'Admin%'
                 AND wt.description NOT LIKE 'Refund%'
               ORDER BY wt.created_at DESC LIMIT ? OFFSET ?""",
            (limit, offset),
        )
        rows = await cursor.fetchall()
        # Format as order-like dicts for dashboard compatibility
        result = []
        for r in rows:
            result.append({
                "id": f"T{r['id']}",
                "merchant_trade_no": f"TOPUP-{r['id']}",
                "user_telegram_id": r["user_telegram_id"],
                "username": r["username"],
                "user_first_name": r["user_first_name"],
                "product_id": None,
                "amount_usd": float(r["amount"]),
                "quantity": 1,
                "status": "TOPUP",
                "created_at": r["created_at"],
                "description": r["description"],
                "balance_after": float(r["balance_after"]) if r["balance_after"] is not None else 0,
            })
        return result, total
    finally:
        await db.close()


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
# â•‘  WALLET                                                          â•‘
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


async def get_wallet_balance(telegram_id: int) -> float:
    """Retourne le solde du wallet d'un utilisateur."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT wallet_balance FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        if row and row["wallet_balance"] is not None:
            return float(row["wallet_balance"])
        return 0.0
    finally:
        await db.close()


async def topup_wallet(telegram_id: int, amount: float, description: str = "", tx_hash: str = None) -> float:
    """CrÃ©dite le wallet et enregistre la transaction. Retourne le nouveau solde."""
    invalidate_stats_cache()
    db = await get_db()
    try:
        # Atomic update and fetch new balance
        cursor = await db.execute(
            "UPDATE users SET wallet_balance = COALESCE(wallet_balance, 0) + ? WHERE telegram_id = ? RETURNING wallet_balance",
            (amount, telegram_id),
        )
        row = await cursor.fetchone()
        new_balance = float(row["wallet_balance"]) if row else amount
        
        # Record transaction
        await db.execute(
            "INSERT INTO wallet_transactions (user_telegram_id, type, amount, balance_after, description, tx_hash) VALUES (?, 'topup', ?, ?, ?, ?)",
            (telegram_id, amount, new_balance, description, tx_hash),
        )
        # Increment finance_bot_balance if it's a real topup
        if not description.startswith("Admin") and not description.startswith("Refund"):
            method_suffix = "binance"
            if "BEP20" in description:
                method_suffix = "bep20"
            elif "TRC20" in description:
                method_suffix = "trc20"
            
            setting_key = f"finance_bot_balance_{method_suffix}"
            await db.execute(
                """INSERT INTO settings (key, value) VALUES (?, ?)
                   ON CONFLICT(key) DO UPDATE SET
                       value = CAST(COALESCE(settings.value, '0') AS REAL) + CAST(excluded.value AS REAL)""",
                (setting_key, str(amount)),
            )

        await db.commit()
        return new_balance
    finally:
        await db.close()


async def deduct_wallet(telegram_id: int, amount: float, description: str = "") -> float:
    """DÃ©bite le wallet. LÃ¨ve ValueError si solde insuffisant. Retourne le nouveau solde."""
    invalidate_stats_cache()
    db = await get_db()
    try:
        # Check current balance first to give a specific error message if user does not exist or has insufficient funds
        cursor = await db.execute(
            "SELECT wallet_balance FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError("User not found")
        val = row["wallet_balance"]
        balance = round(float(val) if val is not None else 0.0, 4)
        amount = round(float(amount), 4)
        
        if balance < amount:
            raise ValueError(f"Insufficient balance: {balance} < {amount}")

        # Atomic conditional update
        # We subtract a tiny epsilon (1e-5) in the WHERE clause to avoid float precision issues failing the atomic update.
        cursor = await db.execute(
            "UPDATE users SET wallet_balance = MAX(0.0, wallet_balance - ?) WHERE telegram_id = ? AND wallet_balance >= ? RETURNING wallet_balance",
            (amount, telegram_id, amount - 1e-5),
        )
        row = await cursor.fetchone()
        if not row:
            raise ValueError("Insufficient balance or update conflict")

        new_balance = float(row["wallet_balance"])
        
        # Record transaction
        await db.execute(
            "INSERT INTO wallet_transactions (user_telegram_id, type, amount, balance_after, description) VALUES (?, 'purchase', ?, ?, ?)",
            (telegram_id, amount, new_balance, description),
        )
        await db.commit()
        return new_balance
    finally:
        await db.close()


async def get_wallet_transactions(telegram_id: int, limit: int = 20) -> list[dict]:
    """Retourne les derniÃ¨res transactions du wallet."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM wallet_transactions WHERE user_telegram_id = ? ORDER BY created_at DESC LIMIT ?",
            (telegram_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_all_wallet_transactions(
    limit: int = 50,
    offset: int = 0,
    tx_type: str | None = None,
) -> tuple[list[dict], int]:
    """Retourne toutes les transactions wallet (tous users) pour le dashboard admin."""
    db = await get_db()
    try:
        where = "WHERE wt.type = ?" if tx_type else ""
        params: list = [tx_type] if tx_type else []

        cursor = await db.execute(
            f"SELECT COUNT(*) as cnt FROM wallet_transactions wt {where}", params
        )
        total = (await cursor.fetchone())["cnt"]

        cursor = await db.execute(
            f"""SELECT wt.*, u.username, u.first_name as user_first_name
                FROM wallet_transactions wt
                LEFT JOIN users u ON wt.user_telegram_id = u.telegram_id
                {where}
                ORDER BY wt.created_at DESC LIMIT ? OFFSET ?""",
            params + [limit, offset],
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows], total
    finally:
        await db.close()


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
# â•‘  TICKETS DE SUPPORT                                              â•‘
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


def _hash_reseller_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def _reseller_key_prefix(raw_key: str) -> str | None:
    parts = raw_key.split("_")
    if len(parts) < 4 or parts[0] != "vbr" or parts[1] != "live":
        return None
    return parts[2]


async def create_reseller_api_key(user_telegram_id: int, name: str = "") -> dict:
    """Crée une clé API revendeur. La clé brute est retournée une seule fois."""
    prefix = secrets.token_hex(5)
    secret = secrets.token_urlsafe(32)
    raw_key = f"vbr_live_{prefix}_{secret}"
    key_hash = _hash_reseller_key(raw_key)
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO reseller_api_keys
               (user_telegram_id, name, key_prefix, key_hash)
               VALUES (?, ?, ?, ?)""",
            (int(user_telegram_id), name.strip(), prefix, key_hash),
        )
        await db.commit()
        _RESELLER_AUTH_CACHE.clear()
        return {
            "id": cursor.lastrowid,
            "user_telegram_id": int(user_telegram_id),
            "name": name.strip(),
            "key_prefix": prefix,
            "api_key": raw_key,
        }
    finally:
        await db.close()


async def rotate_reseller_api_key(user_telegram_id: int, name: str = "Bot API") -> dict:
    """Create a new self-service reseller key and revoke older active keys for this user."""
    prefix = secrets.token_hex(5)
    secret = secrets.token_urlsafe(32)
    raw_key = f"vbr_live_{prefix}_{secret}"
    key_hash = _hash_reseller_key(raw_key)
    db = await get_db()
    try:
        await db.execute(
            "UPDATE reseller_api_keys SET is_active = 0 WHERE user_telegram_id = ? AND is_active = 1",
            (int(user_telegram_id),),
        )
        cursor = await db.execute(
            """INSERT INTO reseller_api_keys
               (user_telegram_id, name, key_prefix, key_hash)
               VALUES (?, ?, ?, ?)""",
            (int(user_telegram_id), name.strip(), prefix, key_hash),
        )
        await db.commit()
        _RESELLER_AUTH_CACHE.clear()
        return {
            "id": cursor.lastrowid,
            "user_telegram_id": int(user_telegram_id),
            "name": name.strip(),
            "key_prefix": prefix,
            "api_key": raw_key,
        }
    finally:
        await db.close()


async def get_active_reseller_api_key_info(user_telegram_id: int) -> dict | None:
    """Return metadata for the active reseller key. The raw key is never stored."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT id, user_telegram_id, name, key_prefix, is_active, created_at, last_used_at
               FROM reseller_api_keys
               WHERE user_telegram_id = ? AND is_active = 1
               ORDER BY created_at DESC
               LIMIT 1""",
            (int(user_telegram_id),),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def list_reseller_api_keys() -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT rk.id, rk.user_telegram_id, rk.name, rk.key_prefix, rk.is_active,
                      rk.created_at, rk.last_used_at,
                      u.username, u.first_name, COALESCE(u.wallet_balance, 0) as wallet_balance,
                      COUNT(rol.order_id) as order_count,
                      COALESCE(SUM(o.amount_usd), 0) as total_spent
               FROM reseller_api_keys rk
               LEFT JOIN users u ON u.telegram_id = rk.user_telegram_id
               LEFT JOIN reseller_order_links rol ON rol.reseller_user_telegram_id = rk.user_telegram_id
               LEFT JOIN orders o ON o.id = rol.order_id AND o.status = 'COMPLETED'
               GROUP BY rk.id
               ORDER BY rk.created_at DESC"""
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def revoke_reseller_api_key(key_id: int) -> bool:
    db = await get_db()
    try:
        cursor = await db.execute(
            "UPDATE reseller_api_keys SET is_active = 0 WHERE id = ?",
            (int(key_id),),
        )
        await db.commit()
        _RESELLER_AUTH_CACHE.clear()
        return cursor.rowcount > 0
    finally:
        await db.close()


async def _touch_reseller_api_key_last_used(key_id: int) -> None:
    """Best-effort timestamp update, isolated from reseller auth reads."""
    now = time.time()
    last_touch = _RESELLER_LAST_USED_TOUCH_CACHE.get(key_id, 0.0)
    if now - last_touch < _RESELLER_LAST_USED_TOUCH_INTERVAL:
        return
    _RESELLER_LAST_USED_TOUCH_CACHE[key_id] = now

    last_exc: Exception | None = None
    for attempt in range(2):
        db = None
        try:
            db = await get_db()
            await db.execute(
                "UPDATE reseller_api_keys SET last_used_at = CURRENT_TIMESTAMP WHERE id = ?",
                (key_id,),
            )
            await db.commit()
            return
        except Exception as exc:
            last_exc = exc
        finally:
            if db is not None:
                try:
                    await db.close()
                except Exception:
                    pass

    logger.warning("Failed to update last_used_at for reseller API key %d after retry: %s", key_id, last_exc)


async def get_reseller_by_api_key(raw_key: str) -> dict | None:
    prefix = _reseller_key_prefix(raw_key)
    if not prefix:
        return None
    key_digest = _hash_reseller_key(raw_key)
    cached = _RESELLER_AUTH_CACHE.get(key_digest)
    if cached and time.time() - cached[0] < _RESELLER_AUTH_CACHE_TTL:
        return dict(cached[1])

    last_exc: Exception | None = None
    for attempt in range(2):
        db = None
        try:
            db = await asyncio.wait_for(get_db(), timeout=6)
            cursor = await asyncio.wait_for(
                db.execute(
                    """SELECT rk.*, u.username, u.first_name, COALESCE(u.wallet_balance, 0) as wallet_balance,
                              COALESCE(u.is_banned, 0) as is_banned
                       FROM reseller_api_keys rk
                       JOIN users u ON u.telegram_id = rk.user_telegram_id
                       WHERE rk.key_prefix = ? AND rk.is_active = 1
                       LIMIT 1""",
                    (prefix,),
                ),
                timeout=5,
            )
            row = await asyncio.wait_for(cursor.fetchone(), timeout=5)
            if not row:
                return None
            data = dict(row)
            if not hmac.compare_digest(str(data.get("key_hash") or ""), key_digest):
                return None
            if data.get("is_banned"):
                return None
            data.pop("key_hash", None)
            _RESELLER_AUTH_CACHE[key_digest] = (time.time(), dict(data))
            asyncio.create_task(_touch_reseller_api_key_last_used(int(data["id"])))
            return data
        except Exception as exc:
            last_exc = exc
            if db is not None and hasattr(db, "has_error"):
                db.has_error = True
            if attempt == 0:
                logger.info("Retrying reseller authentication on a fresh connection: %s", exc)
        finally:
            if db is not None:
                try:
                    await asyncio.wait_for(db.close(), timeout=2)
                except Exception:
                    pass

    raise RuntimeError("Reseller authentication database unavailable") from last_exc


async def get_reseller_wallet_transactions(user_telegram_id: int, limit: int = 50, offset: int = 0) -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT * FROM wallet_transactions
               WHERE user_telegram_id = ?
               ORDER BY created_at DESC
               LIMIT ? OFFSET ?""",
            (int(user_telegram_id), max(1, min(int(limit), 100)), max(0, int(offset))),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def quote_reseller_order(product_id: int, quantity: int) -> dict:
    product = await get_product(product_id)
    if not product or not product.get("is_active", 1) or product.get("is_deleted", 0):
        raise ValueError("Product unavailable")
    quantity = max(1, int(quantity))
    unit_price = await get_effective_price(product_id, quantity)
    total = round(float(unit_price) * quantity, 2)
    stock = None
    if product.get("delivery_type") != "activation":
        stock = await get_stock_count(product_id)
        if quantity > stock:
            raise ValueError("Insufficient stock")
    return {
        "product_id": product_id,
        "quantity": quantity,
        "unit_price": unit_price,
        "total": total,
        "delivery_type": product.get("delivery_type") or "stock",
        "stock": stock,
    }


async def get_reseller_order(user_telegram_id: int, order_id: int) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT o.*, rol.customer_reference, rol.idempotency_key,
                      p.name as product_name, p.emoji as product_emoji, p.delivery_type
               FROM reseller_order_links rol
               JOIN orders o ON o.id = rol.order_id
               LEFT JOIN products p ON p.id = o.product_id
               WHERE rol.reseller_user_telegram_id = ? AND rol.order_id = ?""",
            (int(user_telegram_id), int(order_id)),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        order = dict(row)
        cursor = await db.execute(
            "SELECT id, account_data FROM stock_items WHERE sold_to_order_id = ? ORDER BY id ASC",
            (int(order_id),),
        )
        items = await cursor.fetchall()
        order["items"] = [dict(i) for i in items]
        return order
    finally:
        await db.close()


async def create_reseller_order(
    reseller_user_telegram_id: int,
    product_id: int,
    quantity: int = 1,
    activation_identifier: str | None = None,
    customer_reference: str = "",
    idempotency_key: str | None = None,
) -> dict:
    """Crée et paie une commande revendeur depuis le wallet du revendeur."""
    invalidate_stats_cache()
    reseller_user_telegram_id = int(reseller_user_telegram_id)
    product_id = int(product_id)
    quantity = max(1, int(quantity))
    customer_reference = (customer_reference or "").strip()[:120]
    idempotency_key = (idempotency_key or "").strip()[:120] or None
    activation_identifier = (activation_identifier or "").strip()

    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        if idempotency_key:
            cursor = await db.execute(
                """SELECT order_id FROM reseller_order_links
                   WHERE reseller_user_telegram_id = ? AND idempotency_key = ?""",
                (reseller_user_telegram_id, idempotency_key),
            )
            existing = await cursor.fetchone()
            if existing:
                await db.commit()
                order = await get_reseller_order(reseller_user_telegram_id, existing["order_id"])
                return {"idempotent": True, "order": order}

        cursor = await db.execute(
            "SELECT * FROM products WHERE id = ? AND is_active = 1 AND COALESCE(is_deleted, 0) = 0",
            (product_id,),
        )
        product_row = await cursor.fetchone()
        if not product_row:
            await db.rollback()
            raise ValueError("Product unavailable")
        product = dict(product_row)

        cursor = await db.execute(
            "SELECT * FROM price_tiers WHERE product_id = ? ORDER BY min_qty ASC",
            (product_id,),
        )
        tiers = [dict(r) for r in await cursor.fetchall()]
        unit_price = float(product["price_usd"])
        for tier in tiers:
            if int(tier["min_qty"]) <= quantity <= int(tier["max_qty"]):
                unit_price = dynamic_tier_price(product, float(tier["price_usd"]))
                break
        total = round(unit_price * quantity, 2)

        cursor = await db.execute(
            "UPDATE users SET wallet_balance = MAX(0.0, COALESCE(wallet_balance, 0) - ?) WHERE telegram_id = ? AND COALESCE(wallet_balance, 0) >= ? RETURNING wallet_balance",
            (total, reseller_user_telegram_id, total - 1e-5),
        )
        balance_row = await cursor.fetchone()
        if not balance_row:
            await db.rollback()
            raise ValueError("Insufficient wallet balance")
        balance_after = float(balance_row["wallet_balance"])

        delivery_type = product.get("delivery_type") or "stock"
        status = "COMPLETED"
        activation_status = None
        activation_requested_at = None
        stock_items: list[dict] = []

        if delivery_type == "activation":
            if activation_identifier:
                status = "AWAITING_ACTIVATION"
                activation_status = "pending"
                activation_requested_at = _utcnow().isoformat()
            else:
                status = "AWAITING_ACTIVATION_INFO"
        else:
            cursor = await db.execute(
                "SELECT * FROM stock_items WHERE product_id = ? AND is_sold = 0 ORDER BY added_at ASC LIMIT ?",
                (product_id, quantity),
            )
            stock_items = [dict(r) for r in await cursor.fetchall()]
            if len(stock_items) < quantity:
                await db.rollback()
                raise ValueError("Insufficient stock")

        merchant_trade_no = uuid.uuid4().hex[:12].upper()
        cursor = await db.execute(
            """INSERT INTO orders
               (user_telegram_id, product_id, amount_usd, merchant_trade_no, status,
                quantity, payment_method, paid_at, activation_identifier,
                activation_status, activation_requested_at)
               VALUES (?, ?, ?, ?, ?, ?, 'wallet', CURRENT_TIMESTAMP, ?, ?, ?)""",
            (
                reseller_user_telegram_id,
                product_id,
                total,
                merchant_trade_no,
                status,
                quantity,
                activation_identifier or None,
                activation_status,
                activation_requested_at,
            ),
        )
        order_id = cursor.lastrowid

        if stock_items:
            batch_size = 500
            for i in range(0, len(stock_items), batch_size):
                batch = stock_items[i:i+batch_size]
                placeholders = ",".join("?" for _ in batch)
                params = [order_id] + [item["id"] for item in batch]
                cursor = await db.execute(
                    f"UPDATE stock_items SET is_sold = 1, sold_to_order_id = ?, sold_at = CURRENT_TIMESTAMP WHERE id IN ({placeholders}) AND is_sold = 0",
                    params
                )
                if cursor.rowcount < len(batch):
                    await db.rollback()
                    raise ValueError("Stock conflict, please retry")
            await db.execute(
                "UPDATE orders SET stock_item_id = ? WHERE id = ?",
                (stock_items[0]["id"], order_id),
            )

        await db.execute(
            """INSERT INTO reseller_order_links
               (order_id, reseller_user_telegram_id, customer_reference, idempotency_key)
               VALUES (?, ?, ?, ?)""",
            (order_id, reseller_user_telegram_id, customer_reference, idempotency_key),
        )
        await db.execute(
            "INSERT INTO wallet_transactions (user_telegram_id, type, amount, balance_after, description) VALUES (?, 'purchase', ?, ?, ?)",
            (reseller_user_telegram_id, total, balance_after, f"Reseller API order #{order_id}"),
        )
        if status == "COMPLETED":
            completion_order = {
                "amount_usd": total,
                "user_telegram_id": reseller_user_telegram_id,
                "promo_code_id": None,
            }
            await _apply_completion_effects_tx(db, completion_order, "wallet")
        await db.commit()

        order = await get_reseller_order(reseller_user_telegram_id, order_id)
        return {
            "idempotent": False,
            "order": order,
            "balance_after": balance_after,
            "unit_price": unit_price,
            "total": total,
        }
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()


async def create_ticket(telegram_id: int, message: str) -> int:
    """CrÃ©e un ticket de support et retourne son identifiant."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO support_tickets (user_telegram_id, message) VALUES (?, ?)",
            (telegram_id, message),
        )
        await db.commit()
        return cursor.lastrowid  # type: ignore[return-value]
    finally:
        await db.close()


async def get_ticket(ticket_id: int) -> dict | None:
    """RÃ©cupÃ¨re un ticket de support par son identifiant."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM support_tickets WHERE id = ?", (ticket_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def get_user_tickets(telegram_id: int) -> list[dict]:
    """Retourne tous les tickets d'un utilisateur."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM support_tickets WHERE user_telegram_id = ? ORDER BY created_at DESC",
            (telegram_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_open_tickets() -> list[dict]:
    """Retourne tous les tickets ouverts (en attente de rÃ©ponse admin)."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM support_tickets WHERE status = 'OPEN' ORDER BY created_at ASC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def reply_ticket(ticket_id: int, admin_reply: str) -> None:
    """Enregistre la rÃ©ponse d'un administrateur sur un ticket."""
    db = await get_db()
    try:
        await db.execute(
            "UPDATE support_tickets SET admin_reply = ?, status = 'REPLIED', replied_at = CURRENT_TIMESTAMP WHERE id = ?",
            (admin_reply, ticket_id),
        )
        await db.commit()
    finally:
        await db.close()


async def close_ticket(ticket_id: int) -> None:
    """Ferme un ticket de support."""
    db = await get_db()
    try:
        await db.execute(
            "UPDATE support_tickets SET status = 'CLOSED' WHERE id = ?",
            (ticket_id,),
        )
        await db.commit()
    finally:
        await db.close()


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
# â•‘  STATISTIQUES JOURNALIÃˆRES                                      â•‘
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


async def get_daily_stats(days: int = 30) -> list[dict]:
    """Retourne les revenus et commandes par jour sur les N derniers jours.
    Revenue includes completed orders + wallet topups - admin deductions."""
    days = max(1, min(int(days), 365))
    start_date = (_utcnow() - timedelta(days=days - 1)).date()
    day_labels = [
        (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(days)
    ]
    since = day_labels[0]
    db = await get_db()
    try:
        # Order stats per day
        cursor = await db.execute(
            """SELECT DATE(created_at) as day,
                      COUNT(*) as orders,
                      COALESCE(SUM(CASE WHEN status='COMPLETED' AND (payment_method IS NULL OR payment_method != 'wallet') THEN amount_usd ELSE 0 END), 0) as revenue,
                      SUM(CASE WHEN status='COMPLETED' THEN 1 ELSE 0 END) as completed
               FROM orders
               WHERE created_at >= ?
               GROUP BY DATE(created_at)
               ORDER BY day ASC""",
            (since,),
        )
        order_rows = {r["day"]: dict(r) for r in await cursor.fetchall()}

        # Wallet topup revenue per day (exclude admin credits & refunds)
        cursor = await db.execute(
            """SELECT DATE(created_at) as day,
                      COALESCE(SUM(amount), 0) as topup_rev
               FROM wallet_transactions
               WHERE type = 'topup'
                 AND description NOT LIKE 'Admin%'
                 AND description NOT LIKE 'Refund%'
                 AND created_at >= ?
               GROUP BY DATE(created_at)""",
            (since,),
        )
        topup_rows = {r["day"]: float(r["topup_rev"]) for r in await cursor.fetchall()}

        cursor = await db.execute(
            """SELECT DATE(created_at) as day,
                      COALESCE(SUM(amount), 0) as admin_debit
               FROM wallet_transactions
               WHERE type = 'purchase'
                 AND description LIKE 'Admin debit%'
                 AND created_at >= ?
               GROUP BY DATE(created_at)""",
            (since,),
        )
        admin_debit_rows = {r["day"]: float(r["admin_debit"]) for r in await cursor.fetchall()}

        result = []
        for day in day_labels:
            od = dict(order_rows.get(day, {"day": day, "orders": 0, "revenue": 0, "completed": 0}))
            od["orders"] = int(od.get("orders") or 0)
            od["completed"] = int(od.get("completed") or 0)
            od["revenue"] = float(od.get("revenue") or 0) + topup_rows.get(day, 0.0) - admin_debit_rows.get(day, 0.0)
            result.append(od)
        return result
    finally:
        await db.close()


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
# â•‘  GESTION UTILISATEURS (BAN)                                     â•‘
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


async def ban_user(telegram_id: int) -> None:
    """Bannit un utilisateur."""
    _USER_BANNED_CACHE[telegram_id] = True
    db = await get_db()
    try:
        await db.execute(
            "UPDATE users SET is_banned = 1 WHERE telegram_id = ?",
            (telegram_id,),
        )
        await db.commit()
    finally:
        await db.close()


async def unban_user(telegram_id: int) -> None:
    """DÃ©bannit un utilisateur."""
    _USER_BANNED_CACHE[telegram_id] = False
    db = await get_db()
    try:
        await db.execute(
            "UPDATE users SET is_banned = 0 WHERE telegram_id = ?",
            (telegram_id,),
        )
        await db.commit()
    finally:
        await db.close()


async def is_user_banned(telegram_id: int) -> bool:
    """VÃ©rifie si un utilisateur est banni."""
    if telegram_id in _USER_BANNED_CACHE:
        return _USER_BANNED_CACHE[telegram_id]
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT is_banned FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        banned = bool(row and row["is_banned"])
        _USER_BANNED_CACHE[telegram_id] = banned
        return banned
    finally:
        await db.close()


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
# â•‘  PROTECTION ANTI-REPLAY TRANSACTIONS                             â•‘
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


async def is_transaction_used(transaction_id: str) -> bool:
    """VÃ©rifie si un ID de transaction Binance a dÃ©jÃ  Ã©tÃ© utilisÃ©."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id FROM used_binance_transactions WHERE transaction_id = ?",
            (transaction_id,),
        )
        row = await cursor.fetchone()
        return row is not None
    finally:
        await db.close()


async def record_used_transaction(
    transaction_id: str,
    order_id: int | None = None,
    user_telegram_id: int | None = None,
    amount: float | None = None,
) -> bool:
    """Record a Binance transaction, retrying its idempotent insert if needed."""
    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            return await _record_used_transaction_once(
                transaction_id,
                order_id,
                user_telegram_id,
                amount,
            )
        except Exception as exc:
            last_exc = exc
            if not is_transient_db_connection_error(exc) or attempt == 2:
                raise
            logger.warning(
                "Retrying Binance anti-replay record for order %s: %s",
                order_id,
                exc,
            )
            await asyncio.sleep(0.1 * (attempt + 1))
    raise RuntimeError("Binance transaction record unavailable") from last_exc


async def _record_used_transaction_once(
    transaction_id: str,
    order_id: int | None = None,
    user_telegram_id: int | None = None,
    amount: float | None = None,
) -> bool:
    """Enregistre un ID de transaction comme utilisÃ©. Retourne False si dÃ©jÃ  utilisÃ©."""
    db = await get_db(fresh=True)
    try:
        try:
            await db.execute(
                "INSERT INTO used_binance_transactions (transaction_id, order_id, user_telegram_id, amount) VALUES (?, ?, ?, ?)",
                (transaction_id, order_id, user_telegram_id, amount),
            )
            await db.commit()
            return True
        except Exception as e:
            if "UNIQUE" in str(e).upper():
                await db.rollback()
                cursor = await db.execute(
                    "SELECT order_id, user_telegram_id FROM used_binance_transactions WHERE transaction_id = ?",
                    (transaction_id,),
                )
                existing = await cursor.fetchone()
                return bool(
                    existing
                    and existing["order_id"] == order_id
                    and existing["user_telegram_id"] == user_telegram_id
                )
            raise
    finally:
        await db.close()


# â•”â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â•—
# â•‘  CODES PROMO                                                     â•‘
# â•šâ• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• â• 


async def create_promo(
    code: str,
    discount_type: str = "percent",
    discount_value: float = 10,
    max_uses: int = 0,
    max_uses_per_user: int = 0,
    applicable_product_ids: str | None = None,
    max_qty_per_order: int = 0,
    expires_at: str | None = None,
) -> int:
    """CrÃ©e un code promo et retourne son identifiant."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO promo_codes (code, discount_type, discount_value, max_uses, max_uses_per_user, applicable_product_ids, max_qty_per_order, expires_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (code.upper(), discount_type, discount_value, max_uses, max_uses_per_user, applicable_product_ids, max_qty_per_order, expires_at),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def get_promo_by_code(code: str) -> dict | None:
    """RÃ©cupÃ¨re un code promo par son code texte."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM promo_codes WHERE code = ? AND is_active = 1",
            (code.upper(),),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        promo = dict(row)
        # VÃ©rifier expiration
        if promo.get("expires_at"):
            from datetime import datetime as dt, timezone
            try:
                exp = dt.fromisoformat(promo["expires_at"])
                now = dt.now(timezone.utc) if exp.tzinfo is not None else dt.utcnow()
                if now > exp:
                    return None
            except (ValueError, TypeError):
                pass
        # VÃ©rifier max uses
        if promo["max_uses"] > 0 and promo["used_count"] >= promo["max_uses"]:
            return None
        return promo
    finally:
        await db.close()

async def check_promo_usage(promo_id: int, user_telegram_id: int) -> bool:
    """VÃ©rifie si un utilisateur a le droit d'utiliser ce code (selon max_uses_per_user)."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT max_uses_per_user FROM promo_codes WHERE id = ?", (promo_id,))
        row = await cursor.fetchone()
        if not row:
            return False
        max_per_user = row["max_uses_per_user"]
        if max_per_user <= 0:
            return True # illimitÃ©
        
        c = await db.execute("SELECT usage_count FROM promo_code_usages WHERE promo_code_id = ? AND user_telegram_id = ?", (promo_id, user_telegram_id))
        r = await c.fetchone()
        usage_count = r["usage_count"] if r else 0
        return usage_count < max_per_user
    finally:
        await db.close()


async def increment_promo_usage(promo_id: int, user_telegram_id: int) -> None:
    """IncrÃ©mente le compteur d'utilisation d'un code promo."""
    db = await get_db()
    try:
        # 1. Update global count
        await db.execute(
            "UPDATE promo_codes SET used_count = used_count + 1 WHERE id = ?",
            (promo_id,),
        )
        await db.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Error updating global promo count: %s", e)
    finally:
        await db.close()

    # 2. Update user specific count
    db = await get_db()
    try:
        try:
            await db.execute(
                """INSERT INTO promo_code_usages (promo_code_id, user_telegram_id, usage_count)
                   VALUES (?, ?, 1)""",
                (promo_id, user_telegram_id)
            )
        except Exception:
            # Fallback for UNIQUE constraint violation
            await db.execute(
                """UPDATE promo_code_usages 
                   SET usage_count = usage_count + 1, last_used_at = CURRENT_TIMESTAMP 
                   WHERE promo_code_id = ? AND user_telegram_id = ?""",
                (promo_id, user_telegram_id)
            )
        await db.commit()
    except Exception as e:
        import logging
        logging.getLogger(__name__).error("Error updating user promo count: %s", e)
        # Send error directly to admin for immediate debugging
        try:
            from config import ADMIN_IDS
            from bot import tg_app
            import asyncio
            if tg_app and tg_app.bot:
                for aid in ADMIN_IDS:
                    asyncio.create_task(tg_app.bot.send_message(chat_id=aid, text=f"DEBUG SQLITE ERROR: {e}"))
        except:
            pass
    finally:
        await db.close()


async def get_all_promos() -> list[dict]:
    """Retourne tous les codes promo."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM promo_codes ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def delete_promo(promo_id: int) -> None:
    """Supprime un code promo."""
    db = await get_db()
    try:
        await db.execute("DELETE FROM promo_codes WHERE id = ?", (promo_id,))
        await db.commit()
    finally:
        await db.close()


async def get_referred_users_count(telegram_id: int) -> int:
    """Retourne le nombre d'utilisateurs parrainÃ©s par cet utilisateur."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE referred_by = ?", (telegram_id,)
        )
        row = await cursor.fetchone()
        return row["cnt"] if row else 0
    finally:
        await db.close()


async def get_referred_users_list(telegram_id: int) -> list[dict]:
    """Retourne la liste des utilisateurs parraines."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT telegram_id, username, first_name, created_at, referral_commission_paid FROM users WHERE referred_by = ? ORDER BY created_at DESC LIMIT 50", (telegram_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await db.close()



async def process_referral_payout(order_id: int) -> None:
    """Calcule et verse la commission de parrainage de 5% (max $5.00 par filleul) au parrain."""
    # DÃ©sactivÃ© : le parrainage se base maintenant sur 20 invitations pour obtenir un lien gratuit via le support.
    return
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        order = await cursor.fetchone()
        if not order or order["status"] != "COMPLETED":
            return

        buyer_id = order["user_telegram_id"]
        amount_usd = float(order["amount_usd"])

        # 2. Get the buyer (referred user) details to check if they have a referrer
        cursor = await db.execute("SELECT * FROM users WHERE telegram_id = ?", (buyer_id,))
        buyer = await cursor.fetchone()
        if not buyer or not buyer.get("referred_by"):
            return

        referrer_id = buyer["referred_by"]
        already_paid = float(buyer.get("referral_commission_paid") or 0.0)

        # Capped at $5.00 total cumulative commission per referred friend
        if already_paid >= 5.0:
            return

        commission = amount_usd * 0.05
        payout = min(5.0 - already_paid, commission)

        if payout <= 0.001:
            return

        # 3. Credit the referrer's wallet and update statistics
        # Update referrer wallet and referral earnings
        await db.execute(
            "UPDATE users SET wallet_balance = COALESCE(wallet_balance, 0) + ?, referral_earnings = COALESCE(referral_earnings, 0) + ? WHERE telegram_id = ?",
            (payout, payout, referrer_id)
        )
        # Update referred user's generated commission paid
        await db.execute(
            "UPDATE users SET referral_commission_paid = COALESCE(referral_commission_paid, 0) + ? WHERE telegram_id = ?",
            (payout, buyer_id)
        )

        # Get referrer's new balance to log
        cursor = await db.execute("SELECT wallet_balance FROM users WHERE telegram_id = ?", (referrer_id,))
        ref_row = await cursor.fetchone()
        new_balance = float(ref_row["wallet_balance"]) if (ref_row and ref_row["wallet_balance"] is not None) else payout

        # Record wallet transaction for referrer
        buyer_desc = f"@{buyer['username']}" if buyer.get("username") else f"ID {buyer_id}"
        tx_desc = f"Referral commission from {buyer_desc} (Order #{order_id})"
        await db.execute(
            "INSERT INTO wallet_transactions (user_telegram_id, type, amount, balance_after, description) VALUES (?, 'topup', ?, ?, ?)",
            (referrer_id, payout, new_balance, tx_desc)
        )
        await db.commit()

        # 4. Notify referrer asynchronously via Telegram
        try:
            # Import dynamically to avoid circular import issues
            from bot import tg_app
            if tg_app and tg_app.bot:
                from utils.locales import t
                from utils.helpers import format_price
                
                # Fetch referrer language
                ref_lang = "fr"
                cursor = await db.execute("SELECT language FROM users WHERE telegram_id = ?", (referrer_id,))
                lang_row = await cursor.fetchone()
                if lang_row and lang_row["language"]:
                    ref_lang = lang_row["language"]

                friend_name = buyer.get("first_name") or buyer_desc
                notify_text = (
                    t("referral_notif", ref_lang)
                    .replace("{amount}", format_price(payout))
                    .replace("{friend}", friend_name)
                )
                
                # Send the notification in the background
                import asyncio
                asyncio.create_task(
                    tg_app.bot.send_message(
                        chat_id=referrer_id,
                        text=notify_text,
                        parse_mode="HTML"
                    )
                )
        except Exception as notify_exc:
            logger.warning("Failed to notify referrer: %s", notify_exc)

    except Exception as exc:
        await db.rollback()
        logger.error("Error in process_referral_payout: %s", exc, exc_info=True)
    finally:
        await db.close()


async def is_bep20_transaction_used(tx_hash: str) -> bool:
    """VÃ©rifie si un Tx Hash BEP20 a dÃ©jÃ  Ã©tÃ© utilisÃ©."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id FROM used_bep20_transactions WHERE tx_hash = ?",
            (tx_hash.strip().lower(),),
        )
        row = await cursor.fetchone()
        return row is not None
    finally:
        await db.close()


async def record_used_bep20_transaction(
    tx_hash: str,
    order_id: int | None = None,
    user_telegram_id: int | None = None,
    amount: float | None = None,
) -> bool:
    """Enregistre un Tx Hash BEP20 comme utilisÃ©. Retourne False si dÃ©jÃ  utilisÃ©."""
    db = await get_db()
    try:
        try:
            await db.execute(
                "INSERT INTO used_bep20_transactions (tx_hash, order_id, user_telegram_id, amount) VALUES (?, ?, ?, ?)",
                (tx_hash.strip().lower(), order_id, user_telegram_id, amount),
            )
            await db.commit()
            return True
        except Exception as e:
            if "UNIQUE" in str(e).upper():
                await db.rollback()
                cursor = await db.execute(
                    "SELECT order_id, user_telegram_id FROM used_bep20_transactions WHERE tx_hash = ?",
                    (tx_hash.strip().lower(),),
                )
                existing = await cursor.fetchone()
                return bool(
                    existing
                    and existing["order_id"] == order_id
                    and existing["user_telegram_id"] == user_telegram_id
                )
            raise
    finally:
        await db.close()


# â”€â”€ settings CRUD â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def get_setting(key: str) -> str | None:
    if key in _SETTINGS_CACHE:
        return _SETTINGS_CACHE[key]
    """Retourne la valeur d'un paramÃ¨tre ou None."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        value = row["value"] if row else None
        _SETTINGS_CACHE[key] = value
        return value
    finally:
        await db.close()


async def set_setting(key: str, value: str) -> None:
    clean_value = value.strip()
    """Enregistre ou met Ã  jour un paramÃ¨tre."""
    db = await get_db()
    try:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, clean_value),
        )
        await db.commit()
        _SETTINGS_CACHE[key] = clean_value
    finally:
        await db.close()


# â”€â”€ TRC20 Transactions â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

async def is_trc20_transaction_used(tx_hash: str) -> bool:
    """VÃ©rifie si un Tx Hash TRC20 a dÃ©jÃ  Ã©tÃ© utilisÃ©."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id FROM used_trc20_transactions WHERE tx_hash = ?",
            (tx_hash.strip().lower(),),
        )
        row = await cursor.fetchone()
        return row is not None
    finally:
        await db.close()


async def record_used_trc20_transaction(
    tx_hash: str,
    order_id: int | None = None,
    user_telegram_id: int | None = None,
    amount: float | None = None,
) -> bool:
    """Enregistre un Tx Hash TRC20 comme utilisÃ©. Retourne False si dÃ©jÃ  utilisÃ©."""
    db = await get_db()
    try:
        try:
            await db.execute(
                "INSERT INTO used_trc20_transactions (tx_hash, order_id, user_telegram_id, amount) VALUES (?, ?, ?, ?)",
                (tx_hash.strip().lower(), order_id, user_telegram_id, amount),
            )
            await db.commit()
            return True
        except Exception as e:
            if "UNIQUE" in str(e).upper():
                await db.rollback()
                cursor = await db.execute(
                    "SELECT order_id, user_telegram_id FROM used_trc20_transactions WHERE tx_hash = ?",
                    (tx_hash.strip().lower(),),
                )
                existing = await cursor.fetchone()
                return bool(
                    existing
                    and existing["order_id"] == order_id
                    and existing["user_telegram_id"] == user_telegram_id
                )
            raise
    finally:
        await db.close()


async def get_transactions_for_export(start_date: str, end_date: str):
    import sqlite3
    from .db import get_db
    
    # Normalize ISO-8601 strings (with T/Z) to standard SQLite timestamp format (YYYY-MM-DD HH:MM:SS)
    if start_date:
        start_date = start_date.replace("T", " ").replace("Z", "")
        if "." in start_date:
            start_date = start_date.split(".")[0]
    if end_date:
        end_date = end_date.replace("T", " ").replace("Z", "")
        if "." in end_date:
            end_date = end_date.split(".")[0]
            
    db = await get_db()
    try:
        query = """
            SELECT 
                'Achat' as type,
                o.created_at as date,
                u.username,
                u.first_name,
                o.user_telegram_id,
                o.amount_usd as amount,
                o.payment_method as method,
                o.merchant_trade_no as identifier,
                o.binance_order_id as hash_id
            FROM orders o
            LEFT JOIN users u ON o.user_telegram_id = u.telegram_id
            WHERE o.status = 'COMPLETED' 
              AND (o.payment_method != 'wallet' OR o.payment_method IS NULL)
              AND o.created_at >= ? 
              AND o.created_at <= ?
            
            UNION ALL
            
            SELECT 
                'Topup' as type,
                w.created_at as date,
                u.username,
                u.first_name,
                w.user_telegram_id,
                w.amount as amount,
                CASE 
                    WHEN w.description LIKE '%Binance Pay%' THEN 'binance'
                    WHEN w.description LIKE '%BEP20%' THEN 'bep20'
                    WHEN w.description LIKE '%TRC20%' THEN 'trc20'
                    ELSE 'wallet'
                END as method,
                w.description as identifier,
                '' as hash_id
            FROM wallet_transactions w
            LEFT JOIN users u ON w.user_telegram_id = u.telegram_id
            WHERE (w.description LIKE 'Topup via%' OR w.description LIKE 'Binance Pay:%')
              AND w.created_at >= ? 
              AND w.created_at <= ?
            ORDER BY date DESC
        """
        cursor = await db.execute(query, (start_date, end_date, start_date, end_date))
        rows = await cursor.fetchall()
        
        results = []
        for r in rows:
            client = f"@{r['username']}" if r['username'] else (r['first_name'] or str(r['user_telegram_id']))
            ident = r['hash_id'] if r['hash_id'] else r['identifier']
            results.append({
                'Date': r['date'],
                'Type': r['type'],
                'Client': client,
                'Montant (USD)': float(r['amount']),
                'MÃ©thode': r['method'],
                'Identifiant': ident
            })
        return results
    finally:
        await db.close()


async def get_products_sales_stats() -> list[dict]:
    """Retourne les statistiques de vente cumulées par produit (quantité et chiffre d'affaires)."""
    db = await get_db()
    try:
        cursor = await db.execute("""
            SELECT 
                p.id, 
                p.name, 
                p.emoji, 
                p.price_usd,
                p.delivery_type,
                COALESCE(SUM(CASE WHEN o.quantity IS NULL OR o.quantity < 1 THEN 1 ELSE o.quantity END), 0) as total_qty_sold,
                COALESCE(SUM(o.amount_usd), 0) as total_revenue_usd
            FROM products p
            LEFT JOIN orders o ON o.product_id = p.id AND o.status = 'COMPLETED'
            WHERE p.is_deleted = 0
            GROUP BY p.id
            ORDER BY total_qty_sold DESC
        """)
        rows = await cursor.fetchall()
        
        from database.models import get_all_stock_counts
        stock_counts = await get_all_stock_counts()
        
        stats = []
        for r in rows:
            stats.append({
                "id": r["id"],
                "name": r["name"],
                "emoji": r["emoji"] or '📦',
                "price_usd": float(r["price_usd"]),
                "delivery_type": r["delivery_type"] or "stock",
                "total_sold": int(r["total_qty_sold"]),
                "total_revenue": float(r["total_revenue_usd"]),
                "stock": None if r["delivery_type"] == "activation" else stock_counts.get(r["id"], 0)
            })
        return stats
    finally:
        await db.close()


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—

async def get_products_by_category(category_id: int) -> list[dict]:
    """Retourne les produits actifs d'une catégorie."""
    db = await get_db()
    try:
        try:
            cursor = await db.execute(
                "SELECT * FROM products WHERE category_id = ? AND is_active = 1 AND is_deleted = 0 ORDER BY sort_order ASC, id ASC",
                (category_id,),
            )
            rows = await cursor.fetchall()
        except Exception:
            # Fallback if is_deleted column does not exist yet
            cursor = await db.execute(
                "SELECT * FROM products WHERE category_id = ? AND is_active = 1 ORDER BY id ASC",
                (category_id,),
            )
            rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()
