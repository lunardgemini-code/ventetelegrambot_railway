# database/models.py â€” Fonctions CRUD asynchrones pour toutes les tables
# Chaque fonction ouvre sa propre connexion, exÃ©cute, commit et ferme.

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
import logging
import time
from datetime import datetime, timedelta

from .db import get_db

logger = logging.getLogger(__name__)


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
    """RÃ©cupÃ¨re un utilisateur existant ou en crÃ©e un nouveau, en enregistrant le parrain si applicable."""
    db = await get_db()
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
    """Retourne la liste de tous les utilisateurs enregistrÃ©s avec leur nombre de filleuls."""
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


async def get_users_paginated(limit: int = 20, offset: int = 0, search: str = "") -> tuple[list[dict], int]:
    """Retourne la liste des utilisateurs paginÃ©e et filtrÃ©e avec le nombre total."""
    db = await get_db()
    try:
        where_clause = ""
        params = []
        if search:
            where_clause = " WHERE CAST(u.telegram_id AS TEXT) LIKE ? OR u.username LIKE ? OR u.first_name LIKE ?"
            search_param = f"%{search}%"
            params = [search_param, search_param, search_param]
        
        count_query = f"SELECT COUNT(*) as cnt FROM users u {where_clause}"
        cursor_count = await db.execute(count_query, params)
        row_count = await cursor_count.fetchone()
        total = row_count["cnt"] if row_count else 0

        paginated_query = f"""
            SELECT u.*, COUNT(f.telegram_id) as referrals_count
            FROM users u
            LEFT JOIN users f ON f.referred_by = u.telegram_id
            {where_clause}
            GROUP BY u.id
            ORDER BY u.created_at DESC
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
    start_date = (datetime.utcnow() - timedelta(days=days - 1)).date()
    day_labels = [
        (start_date + timedelta(days=i)).strftime("%Y-%m-%d")
        for i in range(days)
    ]
    yesterday = (datetime.utcnow() - timedelta(days=1)).date().strftime("%Y-%m-%d")

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
              AND DATE(o.created_at) >= ?
            GROUP BY o.product_id, p.name, p.emoji, DATE(o.created_at)
            ORDER BY day ASC, qty_sold DESC
            """,
            (day_labels[0],),
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
    since = (datetime.utcnow() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT product_id,
                      COALESCE(SUM(CASE WHEN quantity IS NULL OR quantity < 1 THEN 1 ELSE quantity END), 0) as sold
               FROM orders
               WHERE status = 'COMPLETED'
                 AND product_id IS NOT NULL
                 AND DATE(created_at) >= ?
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
    """Best-effort product view tracking for conversion alerts."""
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO product_views (product_id, user_telegram_id) VALUES (?, ?)",
            (int(product_id), int(user_telegram_id)),
        )
        await db.commit()
    except Exception as exc:
        logger.debug("Could not record product view for product %s: %s", product_id, exc)
    finally:
        await db.close()


async def get_dead_product_alerts(days: int = 7, min_views: int = 10, max_conversion: float = 0.05) -> list[dict]:
    """Products with many views but weak sales conversion."""
    days = max(1, min(int(days), 90))
    min_views = max(1, int(min_views))
    max_conversion = max(0.0, float(max_conversion))
    since = (datetime.utcnow() - timedelta(days=days - 1)).strftime("%Y-%m-%d")
    db = await get_db()
    try:
        cursor = await db.execute(
            """WITH views AS (
                   SELECT product_id, COUNT(*) as view_count
                   FROM product_views
                   WHERE DATE(viewed_at) >= ?
                   GROUP BY product_id
               ),
               sales AS (
                   SELECT product_id,
                          COALESCE(SUM(CASE WHEN quantity IS NULL OR quantity < 1 THEN 1 ELSE quantity END), 0) as sold_count
                   FROM orders
                   WHERE status = 'COMPLETED'
                     AND product_id IS NOT NULL
                     AND DATE(created_at) >= ?
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
    delivery_type = "activation" if delivery_type == "activation" else "stock"
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


ALLOWED_PRODUCT_COLUMNS = {"category_id", "name", "description", "description_fr", "description_ar", "description_zh", "description_vi", "description_ru", "activation_message", "activation_message_fr", "activation_message_ar", "activation_message_zh", "activation_message_vi", "activation_message_ru", "confirmation_message", "confirmation_message_fr", "confirmation_message_ar", "confirmation_message_zh", "confirmation_message_vi", "confirmation_message_ru", "price_usd", "warranty_days", "emoji", "custom_emoji_id", "image_url", "is_active", "binance_account_id", "delivery_type"}


async def update_product(product_id: int, **kwargs) -> None:
    """Met Ã  jour un produit avec les champs fournis en kwargs."""
    global _PRODUCTS_CACHE
    _PRODUCTS_CACHE = None
    _PRODUCT_BY_ID_CACHE.clear()
    invalidate_stats_cache()
    safe_kwargs = {k: v for k, v in kwargs.items() if k in ALLOWED_PRODUCT_COLUMNS}
    if "delivery_type" in safe_kwargs:
        safe_kwargs["delivery_type"] = "activation" if safe_kwargs["delivery_type"] == "activation" else "stock"
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
    tiers = await get_price_tiers(product_id)
    for tier in tiers:
        if tier["min_qty"] <= quantity <= tier["max_qty"]:
            return float(tier["price_usd"])

    # Fallback: prix de base du produit
    product = await get_product(product_id)
    if not product:
        raise ValueError(f"Product #{product_id} not found")
    return float(product["price_usd"])


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
        _STOCK_COUNTS_CACHE = (now, dict(result))
        return result
    finally:
        await db.close()

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
        cursor = await db.execute("SELECT COUNT(*) as cnt FROM stock_items WHERE product_id = ? AND is_sold = 0", (product_id,))
        row = await cursor.fetchone()
        total_unsold = row["cnt"] if row else 0

        # Stock rÃ©servÃ© (derniÃ¨res 5 minutes)
        cursor = await db.execute(
            "SELECT COALESCE(SUM(quantity), 0) as reserved FROM orders WHERE product_id = ? AND status IN ('PENDING', 'AWAITING_PAYMENT', 'PROCESSING') AND created_at >= datetime('now', '-300 seconds')",
            (product_id,),
        )
        row = await cursor.fetchone()
        reserved = row["reserved"] if row else 0
        stock_count = max(0, total_unsold - reserved)

        # 3. Paliers de prix (Tiers) via cache si possible
        global _TIERS_CACHE
        if product_id in _TIERS_CACHE:
            tiers = _TIERS_CACHE[product_id]
        else:
            cursor = await db.execute("SELECT * FROM price_tiers WHERE product_id = ? ORDER BY min_qty ASC", (product_id,))
            rows = await cursor.fetchall()
            tiers = [dict(r) for r in rows]
            _TIERS_CACHE[product_id] = tiers

        # 4. Nombre de ventes
        cursor = await db.execute("SELECT COUNT(id) as cnt FROM stock_items WHERE product_id = ? AND is_sold = 1", (product_id,))
        row = await cursor.fetchone()
        sold_count = row["cnt"] if row else 0

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
    allowed_statuses: tuple[str, ...] = ("PENDING", "AWAITING_PAYMENT", "PROCESSING", "CANCELLED"),
) -> list[dict] | None:
    """Reserve stock for an order once, returning the same items on retries."""
    _clear_stock_cache()
    invalidate_stats_cache()
    db = await get_db()
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

        for item in stock_items:
            cursor = await db.execute(
                "UPDATE stock_items SET is_sold = 1, sold_to_order_id = ?, sold_at = CURRENT_TIMESTAMP WHERE id = ? AND is_sold = 0",
                (order_id, item["id"]),
            )
            if cursor.rowcount <= 0:
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


async def claim_order_for_wallet_payment(order_id: int, user_telegram_id: int) -> dict | None:
    """Atomically mark a payable order as PROCESSING before debiting wallet."""
    _clear_stock_cache()
    invalidate_stats_cache()
    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            "SELECT * FROM orders WHERE id = ? AND user_telegram_id = ?",
            (int(order_id), int(user_telegram_id)),
        )
        row = await cursor.fetchone()
        if not row:
            await db.rollback()
            return None

        order = dict(row)
        if order.get("status") not in ("PENDING", "AWAITING_PAYMENT"):
            await db.rollback()
            return None

        order["_previous_status"] = order.get("status")
        order["_previous_payment_method"] = order.get("payment_method")
        cursor = await db.execute(
            """UPDATE orders
               SET status = 'PROCESSING', payment_method = 'wallet'
               WHERE id = ? AND user_telegram_id = ? AND status IN ('PENDING', 'AWAITING_PAYMENT')""",
            (int(order_id), int(user_telegram_id)),
        )
        if cursor.rowcount <= 0:
            await db.rollback()
            return None

        await db.commit()
        order["status"] = "PROCESSING"
        order["payment_method"] = "wallet"
        return order
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()


async def restore_order_after_failed_wallet_claim(order_id: int, claimed_order: dict | None = None) -> None:
    """Put a PROCESSING order back to its previous payable state after wallet failure."""
    previous_status = (claimed_order or {}).get("_previous_status") or "PENDING"
    previous_payment_method = (claimed_order or {}).get("_previous_payment_method")
    if previous_status not in ("PENDING", "AWAITING_PAYMENT"):
        previous_status = "PENDING"
    await update_order_status(order_id, previous_status, payment_method=previous_payment_method)


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


async def update_order_status(order_id: int, status: str, **kwargs) -> None:
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
    db = await get_db()
    try:
        # Get current order state in the same connection (avoids a second round trip)
        cursor = await db.execute("SELECT status, amount_usd, payment_method, promo_code_id, user_telegram_id FROM orders WHERE id = ?", (order_id,))
        current_order = None
        row = await cursor.fetchone()
        if row:
            current_order = dict(row)
        await db.execute(
            f"UPDATE orders SET {', '.join(set_parts)} WHERE id = ?", values
        )
        
        # If the order is transitioning to COMPLETED, update bot balance
        if status == "COMPLETED" and current_order and current_order.get("status") != "COMPLETED":
            # Increment finance_bot_balance if paid externally
            pay_method = kwargs.get("payment_method") or current_order.get("payment_method")
            if pay_method != "wallet":
                method_suffix = "binance"
                if pay_method == "bep20":
                    method_suffix = "bep20"
                elif pay_method == "trc20":
                    method_suffix = "trc20"
                elif pay_method == "binance_pay":
                    method_suffix = "binance"
                
                setting_key = f"finance_bot_balance_{method_suffix}"
                cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (setting_key,))
                row = await cursor.fetchone()
                bal = float(row["value"]) if row else 0.0
                await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (setting_key, str(bal + float(current_order.get("amount_usd", 0)))))

        await db.commit()
    finally:
        await db.close()

    # Trigger referral payout and promo usage outside the DB connection (they open their own)
    if status == "COMPLETED" and current_order and current_order.get("status") != "COMPLETED":
        try:
            promo_id = current_order.get("promo_code_id")
            if promo_id:
                await increment_promo_usage(promo_id, current_order.get("user_telegram_id"))
            # Trigger referral payout
            await process_referral_payout(order_id)
        except Exception as e:
            logger.error("Error in post-completion triggers for order %s: %s", order_id, e)


async def cancel_all_pending_orders(user_telegram_id: int) -> int:
    _clear_stock_cache()
    invalidate_stats_cache()
    """Cancel all PENDING and AWAITING_PAYMENT orders for a user. Returns count cancelled."""
    db = await get_db()
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
            "SELECT * FROM orders WHERE status IN ('PENDING', 'AWAITING_PAYMENT') ORDER BY created_at ASC"
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


async def submit_activation_identifier(order_id: int, identifier: str) -> None:
    """Store the customer identifier and move the order to admin activation."""
    invalidate_stats_cache()
    db = await get_db()
    try:
        await db.execute(
            """UPDATE orders
               SET status = 'AWAITING_ACTIVATION',
                   activation_identifier = ?,
                   activation_status = 'pending',
                   activation_requested_at = ?
               WHERE id = ?""",
            (identifier, datetime.utcnow().isoformat(), order_id),
        )
        await db.commit()
    finally:
        await db.close()


async def get_stats(days: int = 30, method: str = None) -> dict:
    now = datetime.utcnow().timestamp()
    cache_key = f"{days}_{method}"
    if cache_key in _GET_STATS_CACHE:
        cache_time, cached_data = _GET_STATS_CACHE[cache_key]
        if now - cache_time < _GET_STATS_CACHE_TTL:
            return cached_data
            
    data = await _get_stats_uncached(days, method)
    _GET_STATS_CACHE[cache_key] = (now, data)
    return data

async def _get_stats_uncached(days: int = 30, method: str = None) -> dict:
    """Retourne les statistiques des commandes sur les N derniers jours.

    Retourne un dictionnaire avec :
    - total_orders : nombre total de commandes
    - total_revenue : revenu total (commandes complÃ©tÃ©es + wallet topups - admin debits)
    - completed_orders : nombre de commandes complÃ©tÃ©es
    - pending_orders : nombre de commandes en attente
    - topup_revenue : revenu des wallet topups uniquement
    """
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    db = await get_db()
    
    try:
        # Nombre total de commandes sur la pÃ©riode
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM orders WHERE created_at >= ?", (since,)
        )
        total_orders = (await cursor.fetchone())["cnt"]

        # Revenu total des commandes complÃ©tÃ©es (exclut les achats par portefeuille pour Ã©viter le double comptage avec les recharges)
        # Revenu total des commandes complÃ©tÃ©es (exclut les achats par portefeuille pour Ã©viter le double comptage avec les recharges)
        cursor = await db.execute(
            "SELECT COALESCE(SUM(amount_usd), 0) as total FROM orders WHERE status = 'COMPLETED' AND (payment_method IS NULL OR payment_method != 'wallet') AND created_at >= ?",
            (since,),
        )
        order_revenue = (await cursor.fetchone())["total"]

        # Wallet topup revenue (user-initiated Binance Pay topups only, not admin credits)
        cursor = await db.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM wallet_transactions WHERE type = 'topup' AND description NOT LIKE 'Admin%' AND description NOT LIKE 'Refund%' AND created_at >= ?",
            (since,),
        )
        topup_revenue = (await cursor.fetchone())["total"]

        # Admin deductions (refunds) â€” subtract from revenue
        cursor = await db.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM wallet_transactions WHERE type = 'purchase' AND description LIKE 'Admin debit%' AND created_at >= ?",
            (since,),
        )
        admin_deductions = (await cursor.fetchone())["total"]

        total_revenue = float(order_revenue) + float(topup_revenue) - float(admin_deductions)

        # Nombre de commandes complÃ©tÃ©es
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM orders WHERE status = 'COMPLETED' AND created_at >= ?",
            (since,),
        )
        completed_orders = (await cursor.fetchone())["cnt"]

        # Nombre de commandes en attente
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM orders WHERE status = 'PENDING' AND created_at >= ?",
            (since,),
        )
        pending_orders = (await cursor.fetchone())["cnt"]

        # Breakdown of sales volume by payment method
        cursor = await db.execute(
            "SELECT payment_method, SUM(amount_usd) as total FROM orders WHERE status = 'COMPLETED' AND created_at >= ? GROUP BY payment_method",
            (since,),
        )
        sales_breakdown = await cursor.fetchall()
        
        sales_binance = 0.0
        sales_bep20 = 0.0
        sales_trc20 = 0.0
        sales_wallet = 0.0
        
        for row in sales_breakdown:
            pm = row["payment_method"]
            amount = float(row["total"] or 0.0)
            if not pm or pm.lower() == "binance":
                sales_binance += amount
            elif pm.lower() == "bep20":
                sales_bep20 += amount
            elif pm.lower() == "trc20":
                sales_trc20 += amount
            elif pm.lower() == "wallet":
                sales_wallet += amount

        # Topup count
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM wallet_transactions WHERE type = 'topup' AND description NOT LIKE 'Admin%' AND description NOT LIKE 'Refund%' AND created_at >= ?",
            (since,),
        )
        topup_count = (await cursor.fetchone())["cnt"]

        # Nouveaux utilisateurs sur la période
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE created_at >= ?", (since,)
        )
        new_users = (await cursor.fetchone())["cnt"]

        # Utilisateurs récurrents (avec au moins 2 commandes complétées)
        cursor = await db.execute(
            """SELECT COUNT(*) as cnt FROM (
                SELECT user_telegram_id FROM orders 
                WHERE status = 'COMPLETED' 
                GROUP BY user_telegram_id 
                HAVING COUNT(*) >= 2
            )"""
        )
        returning_users = (await cursor.fetchone())["cnt"]

        return {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "topup_revenue": float(topup_revenue),
            "order_revenue": float(order_revenue),
            "admin_deductions": float(admin_deductions),
            "completed_orders": completed_orders,
            "pending_orders": pending_orders,
            "sales_binance": sales_binance,
            "sales_bep20": sales_bep20,
            "sales_trc20": sales_trc20,
            "sales_wallet": sales_wallet,
            "topup_count": topup_count,
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
            cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (setting_key,))
            set_row = await cursor.fetchone()
            bal = float(set_row["value"]) if set_row else 0.0
            await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (setting_key, str(bal + amount)))

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
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT rk.*, u.username, u.first_name, COALESCE(u.wallet_balance, 0) as wallet_balance,
                      COALESCE(u.is_banned, 0) as is_banned
               FROM reseller_api_keys rk
               JOIN users u ON u.telegram_id = rk.user_telegram_id
               WHERE rk.key_prefix = ? AND rk.is_active = 1
               LIMIT 1""",
            (prefix,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        data = dict(row)
        if not hmac.compare_digest(str(data.get("key_hash") or ""), _hash_reseller_key(raw_key)):
            return None
        if data.get("is_banned"):
            return None
        await _touch_reseller_api_key_last_used(data["id"])
        data.pop("key_hash", None)
        return data
    finally:
        await db.close()


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
                unit_price = float(tier["price_usd"])
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
                activation_requested_at = datetime.utcnow().isoformat()
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
            for item in stock_items:
                cursor = await db.execute(
                    "UPDATE stock_items SET is_sold = 1, sold_to_order_id = ?, sold_at = CURRENT_TIMESTAMP WHERE id = ? AND is_sold = 0",
                    (order_id, item["id"]),
                )
                if cursor.rowcount <= 0:
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
    start_date = (datetime.utcnow() - timedelta(days=days - 1)).date()
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
    """Enregistre un ID de transaction comme utilisÃ©. Retourne False si dÃ©jÃ  utilisÃ©."""
    db = await get_db()
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
                return False
            raise
    finally:
        await db.close()


# â•”â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•—
# â•‘  CODES PROMO                                                     â•‘
# â•šâ•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•â•


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
                return False
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
                return False
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
