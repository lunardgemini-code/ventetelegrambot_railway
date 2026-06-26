# database/models.py — Fonctions CRUD asynchrones pour toutes les tables
# Chaque fonction ouvre sa propre connexion, exécute, commit et ferme.

from __future__ import annotations

import uuid
import logging
from datetime import datetime, timedelta

from .db import get_db

logger = logging.getLogger(__name__)


# ── Caches en mémoire pour optimiser la performance (éviter les appels réseau Turso répétitifs) ──
_USER_LANG_CACHE: dict[int, str] = {}
_USER_BANNED_CACHE: dict[int, bool] = {}
_CATEGORIES_CACHE: list[dict] | None = None
_PRODUCTS_CACHE: list[dict] | None = None
_PRODUCT_BY_ID_CACHE: dict[int, dict | None] = {}
_TIERS_CACHE: dict[int, list[dict]] = {}


# ╔══════════════════════════════════════════════════════════════════╗
# ║  UTILISATEURS                                                    ║
# ╚══════════════════════════════════════════════════════════════════╝


async def get_or_create_user(
    telegram_id: int,
    username: str | None,
    first_name: str,
    referred_by: int | None = None,
) -> dict:
    """Récupère un utilisateur existant ou en crée un nouveau, en enregistrant le parrain si applicable."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        )
        row = await cursor.fetchone()
        if row:
            # Mettre à jour le nom d'utilisateur et le prénom s'ils ont changé
            await db.execute(
                "UPDATE users SET username = ?, first_name = ? WHERE telegram_id = ?",
                (username, first_name, telegram_id),
            )
            await db.commit()
            cursor = await db.execute(
                "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
            )
            row = await cursor.fetchone()
            user_dict = dict(row)
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
    """Récupère un utilisateur par son identifiant Telegram."""
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
    """Retourne la liste de tous les utilisateurs enregistrés avec leur nombre de filleuls."""
    db = await get_db()
    try:
        cursor = await db.execute("""
            SELECT u.*, 
                   (SELECT COUNT(*) FROM users f WHERE f.referred_by = u.telegram_id) as referrals_count 
            FROM users u 
            ORDER BY u.created_at DESC
        """)
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_users_paginated(limit: int = 20, offset: int = 0, search: str = "") -> tuple[list[dict], int]:
    """Retourne la liste des utilisateurs paginée et filtrée avec le nombre total."""
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
            SELECT u.*, 
                   (SELECT COUNT(*) FROM users f WHERE f.referred_by = u.telegram_id) as referrals_count 
            FROM users u
            {where_clause}
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


async def get_user_lang(telegram_id: int) -> str:
    """Retourne la langue préférée de l'utilisateur (par défaut 'fr')."""
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
    """Définit la langue préférée de l'utilisateur."""
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


# ╔══════════════════════════════════════════════════════════════════╗
# ║  CATÉGORIES                                                      ║
# ╚══════════════════════════════════════════════════════════════════╝


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
    """Récupère une catégorie par son identifiant."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM categories WHERE id = ?", (category_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def add_category(
    name: str,
    emoji: str = "📂",
    description: str = "",
) -> int:
    """Ajoute une nouvelle catégorie et retourne son identifiant."""
    global _CATEGORIES_CACHE
    _CATEGORIES_CACHE = None
    db = await get_db()
    try:
        cursor = await db.execute(
            "INSERT INTO categories (name, emoji, description) VALUES (?, ?, ?)",
            (name, emoji, description),
        )
        await db.commit()
        return cursor.lastrowid  # type: ignore[return-value]
    finally:
        await db.close()


ALLOWED_CATEGORY_COLUMNS = {"name", "emoji", "description", "is_active", "sort_order"}


async def update_category(category_id: int, **kwargs) -> None:
    """Met à jour une catégorie avec les champs fournis en kwargs."""
    global _CATEGORIES_CACHE
    _CATEGORIES_CACHE = None
    safe_kwargs = {k: v for k, v in kwargs.items() if k in ALLOWED_CATEGORY_COLUMNS}
    if not safe_kwargs:
        return
    columns = ", ".join(f"{k} = ?" for k in safe_kwargs)
    values = list(safe_kwargs.values()) + [category_id]
    db = await get_db()
    try:
        await db.execute(
            f"UPDATE categories SET {columns} WHERE id = ?", values
        )
        await db.commit()
    finally:
        await db.close()


async def delete_category(category_id: int) -> None:
    """Marque une catégorie comme supprimée, ainsi que ses produits, et supprime leur stock non vendu."""
    global _CATEGORIES_CACHE, _PRODUCTS_CACHE, _PRODUCT_BY_ID_CACHE
    _CATEGORIES_CACHE = None
    _PRODUCTS_CACHE = None
    _PRODUCT_BY_ID_CACHE.clear()
    db = await get_db()
    try:
        # Ne pas toucher aux commandes.
        # Supprimer uniquement le stock non vendu pour les produits de cette catégorie
        await db.execute(
            "DELETE FROM stock_items WHERE product_id IN (SELECT id FROM products WHERE category_id = ?) AND is_sold = 0",
            (category_id,),
        )
        # Soft delete les produits associés (is_deleted = 1, is_active = 0)
        await db.execute("UPDATE products SET is_deleted = 1, is_active = 0 WHERE category_id = ?", (category_id,))
        # Soft delete la catégorie (is_deleted = 1, is_active = 0)
        await db.execute("UPDATE categories SET is_deleted = 1, is_active = 0 WHERE id = ?", (category_id,))
        await db.commit()
    finally:
        await db.close()


# ╔══════════════════════════════════════════════════════════════════╗
# ║  PRODUITS                                                        ║
# ╚══════════════════════════════════════════════════════════════════╝


async def get_products_by_category(category_id: int) -> list[dict]:
    """Retourne les produits actifs d'une catégorie donnée."""
    db = await get_db()
    try:
        try:
            cursor = await db.execute(
                "SELECT * FROM products WHERE category_id = ? AND is_active = 1 AND is_deleted = 0 ORDER BY id ASC",
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
            cursor = await db.execute("SELECT * FROM products WHERE is_deleted = 0 ORDER BY category_id, id")
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
    emoji: str = "📦",
    custom_emoji_id: str | None = None,
    image_url: str | None = None,
    binance_account_id: int | None = None,
) -> int:
    """Ajoute un nouveau produit et retourne son identifiant."""
    global _PRODUCTS_CACHE
    _PRODUCTS_CACHE = None
    _PRODUCT_BY_ID_CACHE.clear()
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO products
               (category_id, name, description, price_usd, warranty_days, emoji, custom_emoji_id, image_url, binance_account_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (category_id, name, description, price_usd, warranty_days, emoji, custom_emoji_id, image_url, binance_account_id),
        )
        await db.commit()
        return cursor.lastrowid  # type: ignore[return-value]
    finally:
        await db.close()


ALLOWED_PRODUCT_COLUMNS = {"category_id", "name", "description", "price_usd", "warranty_days", "emoji", "custom_emoji_id", "image_url", "is_active", "binance_account_id"}


async def update_product(product_id: int, **kwargs) -> None:
    """Met à jour un produit avec les champs fournis en kwargs."""
    global _PRODUCTS_CACHE
    _PRODUCTS_CACHE = None
    _PRODUCT_BY_ID_CACHE.clear()
    safe_kwargs = {k: v for k, v in kwargs.items() if k in ALLOWED_PRODUCT_COLUMNS}
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


# ── Binance Accounts ──────────────────────────────────────────────


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
            return dict(row) if row else None
        finally:
            await db.close()
    except Exception as exc:
        logger.error("Error in get_default_binance_account: %s", exc, exc_info=True)
        return None


async def add_binance_account(label: str, uid: str, api_key: str = "", api_secret: str = "", is_default: int = 0) -> int:
    """Add a new Binance account. If is_default=1, unset other defaults first."""
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
    db = await get_db()
    try:
        await db.execute("DELETE FROM binance_accounts WHERE id = ?", (account_id,))
        await db.execute("UPDATE products SET binance_account_id = NULL WHERE binance_account_id = ?", (account_id,))
        await db.commit()
    finally:
        await db.close()


async def toggle_product(product_id: int) -> None:
    """Inverse l'état actif/inactif d'un produit."""
    global _PRODUCTS_CACHE
    _PRODUCTS_CACHE = None
    _PRODUCT_BY_ID_CACHE.clear()
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
    """Marque un produit comme supprimé et supprime uniquement son stock non vendu."""
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


# ╔══════════════════════════════════════════════════════════════════╗
# ║  PRIX PAR PALIERS (BATCH PRICING)                                ║
# ╚══════════════════════════════════════════════════════════════════╝


async def get_price_tiers(product_id: int) -> list[dict]:
    """Retourne les paliers de prix pour un produit, triés par min_qty."""
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
    """Retourne le prix unitaire effectif pour une quantité donnée.

    Cherche le palier correspondant à la quantité.
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


# ╔══════════════════════════════════════════════════════════════════╗
# ║  STOCK                                                           ║
# ╚══════════════════════════════════════════════════════════════════╝


async def get_all_stock_counts() -> dict[int, int]:
    """Retourne le nombre d'articles non vendus et non réservés pour TOUS les produits en une seule requête.

    Returns:
        Dictionnaire {product_id: count}
    """
    db = await get_db()
    try:
        # 1. Obtenir le stock total non vendu pour chaque produit
        cursor = await db.execute(
            "SELECT product_id, COUNT(*) as cnt FROM stock_items WHERE is_sold = 0 GROUP BY product_id"
        )
        rows = await cursor.fetchall()
        stocks = {r["product_id"]: r["cnt"] for r in rows}

        # 2. Obtenir les réservations actives (créées dans les dernières 300 secondes / 5 minutes)
        cursor = await db.execute(
            """SELECT product_id, COALESCE(SUM(quantity), 0) as reserved 
               FROM orders 
               WHERE status IN ('PENDING', 'AWAITING_PAYMENT') 
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

        # Stock réservé (dernières 5 minutes)
        cursor = await db.execute(
            "SELECT COALESCE(SUM(quantity), 0) as reserved FROM orders WHERE product_id = ? AND status IN ('PENDING', 'AWAITING_PAYMENT') AND created_at >= datetime('now', '-300 seconds')",
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
    """Retourne le nombre d'articles en stock non vendus et non réservés pour un produit."""
    db = await get_db()
    try:
        # 1. Stock total non vendu en base
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM stock_items WHERE product_id = ? AND is_sold = 0",
            (product_id,),
        )
        row = await cursor.fetchone()
        total_unsold = row["cnt"] if row else 0

        # 2. Stock réservé (commandes PENDING ou AWAITING_PAYMENT créées il y a moins de 300 secondes / 5 minutes)
        cursor = await db.execute(
            """SELECT COALESCE(SUM(quantity), 0) as reserved 
               FROM orders 
               WHERE product_id = ? 
                 AND status IN ('PENDING', 'AWAITING_PAYMENT') 
                 AND created_at >= datetime('now', '-300 seconds')""",
            (product_id,),
        )
        row = await cursor.fetchone()
        reserved = row["reserved"] if row else 0

        return max(0, total_unsold - reserved)
    finally:
        await db.close()


async def add_stock_items(product_id: int, items: list[str]) -> int:
    """Ajoute plusieurs articles en stock et retourne le nombre ajouté."""
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
    """Marque un article comme vendu de manière atomique.
    
    Utilise WHERE is_sold = 0 pour éviter la double-livraison en cas de requêtes concurrentes.
    Retourne True si l'article a été marqué, False s'il était déjà vendu.
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
    """Relâche un article (annule la vente). Utilisé en cas de livraison partielle échouée."""
    db = await get_db()
    try:
        await db.execute(
            "UPDATE stock_items SET is_sold = 0, sold_to_order_id = NULL, sold_at = NULL WHERE id = ?",
            (stock_id,),
        )
        await db.commit()
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
    """Retourne les articles livrés pour une commande spécifique."""
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


# ╔══════════════════════════════════════════════════════════════════╗
# ║  COMMANDES                                                       ║
# ╚══════════════════════════════════════════════════════════════════╝


async def create_order(
    user_telegram_id: int,
    product_id: int,
    amount_usd: float,
    quantity: int = 1,
) -> dict:
    """Crée une nouvelle commande avec un merchant_trade_no unique et une quantité."""
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
    """Récupère une commande par son identifiant."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT * FROM orders WHERE id = ?", (order_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def get_order_by_merchant_id(merchant_trade_no: str) -> dict | None:
    """Récupère une commande par son numéro de transaction marchand."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM orders WHERE merchant_trade_no = ?", (merchant_trade_no,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
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
}


async def update_order_status(order_id: int, status: str, **kwargs) -> None:
    """Met à jour le statut d'une commande avec des champs optionnels."""
    # Get current order state to detect status transitions
    current_order = await get_order(order_id)

    set_parts = ["status = ?"]
    values: list = [status]
    safe_kwargs = {k: v for k, v in kwargs.items() if k in ALLOWED_ORDER_COLUMNS}
    for key, val in safe_kwargs.items():
        set_parts.append(f"{key} = ?")
        values.append(val)
    values.append(order_id)
    db = await get_db()
    try:
        await db.execute(
            f"UPDATE orders SET {', '.join(set_parts)} WHERE id = ?", values
        )
        
        # If the order is transitioning to COMPLETED, update bot balance
        if status == "COMPLETED" and current_order and current_order.get("status") != "COMPLETED":
            # Increment finance_bot_balance if paid externally
            pay_method = kwargs.get("payment_method") or current_order.get("payment_method")
            if pay_method != "wallet":
                cursor = await db.execute("SELECT value FROM settings WHERE key = 'finance_bot_balance'")
                row = await cursor.fetchone()
                bal = float(row["value"]) if row else 0.0
                await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ("finance_bot_balance", str(bal + float(current_order.get("amount_usd", 0)))))

        await db.commit()
    finally:
        await db.close()

    # Trigger referral payout and promo usage outside the DB connection (they open their own)
    if status == "COMPLETED" and current_order and current_order.get("status") != "COMPLETED":
        promo_id = current_order.get("promo_code_id")
        if promo_id:
            await increment_promo_usage(promo_id)
        # Trigger referral payout
        await process_referral_payout(order_id)


async def cancel_all_pending_orders(user_telegram_id: int) -> int:
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
    """Associe un article en stock à une commande."""
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
    """Retourne les commandes d'un utilisateur avec pagination."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM orders WHERE user_telegram_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
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
            "SELECT * FROM orders WHERE status = 'PENDING' ORDER BY created_at ASC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        await db.close()


async def get_stats(days: int = 30, method: str = None) -> dict:
    """Retourne les statistiques des commandes sur les N derniers jours.

    Retourne un dictionnaire avec :
    - total_orders : nombre total de commandes
    - total_revenue : revenu total (commandes complétées + wallet topups - admin debits)
    - completed_orders : nombre de commandes complétées
    - pending_orders : nombre de commandes en attente
    - topup_revenue : revenu des wallet topups uniquement
    """
    since = (datetime.utcnow() - timedelta(days=days)).isoformat()
    db = await get_db()
    
    try:
        # Nombre total de commandes sur la période
        cursor = await db.execute(
            "SELECT COUNT(*) as cnt FROM orders WHERE created_at >= ?", (since,)
        )
        total_orders = (await cursor.fetchone())["cnt"]

        # Revenu total des commandes complétées (exclut les achats par portefeuille pour éviter le double comptage avec les recharges)
        # Revenu total des commandes complétées (exclut les achats par portefeuille pour éviter le double comptage avec les recharges)
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

        # Admin deductions (refunds) — subtract from revenue
        cursor = await db.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM wallet_transactions WHERE type = 'purchase' AND description LIKE 'Admin debit%' AND created_at >= ?",
            (since,),
        )
        admin_deductions = (await cursor.fetchone())["total"]

        total_revenue = float(order_revenue) + float(topup_revenue) - float(admin_deductions)

        # Nombre de commandes complétées
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
        }
    finally:
        await db.close()


async def get_all_orders_filtered(
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """Retourne les commandes avec filtre optionnel sur le statut + count total + username."""
    db = await get_db()
    try:
        if status:
            where = "WHERE o.status = ?"
            params: list = [status]
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


# ╔══════════════════════════════════════════════════════════════════╗
# ║  WALLET                                                          ║
# ╚══════════════════════════════════════════════════════════════════╝


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


async def topup_wallet(telegram_id: int, amount: float, description: str = "") -> float:
    """Crédite le wallet et enregistre la transaction. Retourne le nouveau solde."""
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
            "INSERT INTO wallet_transactions (user_telegram_id, type, amount, balance_after, description) VALUES (?, 'topup', ?, ?, ?)",
            (telegram_id, amount, new_balance, description),
        )
        # Increment finance_bot_balance if it's a real topup
        if not description.startswith("Admin") and not description.startswith("Refund"):
            cursor = await db.execute("SELECT value FROM settings WHERE key = 'finance_bot_balance'")
            set_row = await cursor.fetchone()
            bal = float(set_row["value"]) if set_row else 0.0
            await db.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", ("finance_bot_balance", str(bal + amount)))

        await db.commit()
        return new_balance
    finally:
        await db.close()


async def deduct_wallet(telegram_id: int, amount: float, description: str = "") -> float:
    """Débite le wallet. Lève ValueError si solde insuffisant. Retourne le nouveau solde."""
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
    """Retourne les dernières transactions du wallet."""
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


# ╔══════════════════════════════════════════════════════════════════╗
# ║  TICKETS DE SUPPORT                                              ║
# ╚══════════════════════════════════════════════════════════════════╝


async def create_ticket(telegram_id: int, message: str) -> int:
    """Crée un ticket de support et retourne son identifiant."""
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
    """Récupère un ticket de support par son identifiant."""
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
    """Retourne tous les tickets ouverts (en attente de réponse admin)."""
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
    """Enregistre la réponse d'un administrateur sur un ticket."""
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


# ╔══════════════════════════════════════════════════════════════════╗
# ║  STATISTIQUES JOURNALIÈRES                                      ║
# ╚══════════════════════════════════════════════════════════════════╝


async def get_daily_stats(days: int = 30) -> list[dict]:
    """Retourne les revenus et commandes par jour sur les N derniers jours.
    Revenue includes completed orders + wallet topups - admin deductions."""
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    db = await get_db()
    try:
        # Order stats per day
        cursor = await db.execute(
            """SELECT DATE(created_at) as day,
                      COUNT(*) as orders,
                      COALESCE(SUM(CASE WHEN status='COMPLETED' AND (payment_method IS NULL OR payment_method != 'wallet') THEN amount_usd ELSE 0 END), 0) as revenue,
                      SUM(CASE WHEN status='COMPLETED' THEN 1 ELSE 0 END) as completed
               FROM orders
               WHERE DATE(created_at) >= ?
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
                 AND DATE(created_at) >= ?
               GROUP BY DATE(created_at)""",
            (since,),
        )
        topup_rows = {r["day"]: float(r["topup_rev"]) for r in await cursor.fetchall()}

        # Merge all days
        all_days = sorted(set(list(order_rows.keys()) + list(topup_rows.keys())))
        result = []
        for day in all_days:
            od = order_rows.get(day, {"day": day, "orders": 0, "revenue": 0, "completed": 0})
            od["revenue"] = float(od["revenue"]) + topup_rows.get(day, 0)
            result.append(od)
        return result
    finally:
        await db.close()


# ╔══════════════════════════════════════════════════════════════════╗
# ║  GESTION UTILISATEURS (BAN)                                     ║
# ╚══════════════════════════════════════════════════════════════════╝


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
    """Débannit un utilisateur."""
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
    """Vérifie si un utilisateur est banni."""
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


# ╔══════════════════════════════════════════════════════════════════╗
# ║  PROTECTION ANTI-REPLAY TRANSACTIONS                             ║
# ╚══════════════════════════════════════════════════════════════════╝


async def is_transaction_used(transaction_id: str) -> bool:
    """Vérifie si un ID de transaction Binance a déjà été utilisé."""
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
    """Enregistre un ID de transaction comme utilisé. Retourne False si déjà utilisé."""
    db = await get_db()
    try:
        try:
            await db.execute(
                "INSERT INTO used_binance_transactions (transaction_id, order_id, user_telegram_id, amount) VALUES (?, ?, ?, ?)",
                (transaction_id, order_id, user_telegram_id, amount),
            )
            await db.commit()
            return True
        except Exception:
            # UNIQUE constraint violation = already used
            return False
    finally:
        await db.close()


# ╔══════════════════════════════════════════════════════════════════╗
# ║  CODES PROMO                                                     ║
# ╚══════════════════════════════════════════════════════════════════╝


async def create_promo(
    code: str,
    discount_type: str = "percent",
    discount_value: float = 10,
    max_uses: int = 0,
    expires_at: str | None = None,
) -> int:
    """Crée un code promo et retourne son identifiant."""
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT INTO promo_codes (code, discount_type, discount_value, max_uses, expires_at)
               VALUES (?, ?, ?, ?, ?)""",
            (code.upper(), discount_type, discount_value, max_uses, expires_at),
        )
        await db.commit()
        return cursor.lastrowid
    finally:
        await db.close()


async def get_promo_by_code(code: str) -> dict | None:
    """Récupère un code promo par son code texte."""
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
        # Vérifier expiration
        if promo.get("expires_at"):
            from datetime import datetime as dt, timezone
            try:
                exp = dt.fromisoformat(promo["expires_at"])
                now = dt.now(timezone.utc) if exp.tzinfo is not None else dt.utcnow()
                if now > exp:
                    return None
            except (ValueError, TypeError):
                pass
        # Vérifier max uses
        if promo["max_uses"] > 0 and promo["used_count"] >= promo["max_uses"]:
            return None
        return promo
    finally:
        await db.close()


async def increment_promo_usage(promo_id: int) -> None:
    """Incrémente le compteur d'utilisation d'un code promo."""
    db = await get_db()
    try:
        await db.execute(
            "UPDATE promo_codes SET used_count = used_count + 1 WHERE id = ?",
            (promo_id,),
        )
        await db.commit()
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
    """Retourne le nombre d'utilisateurs parrainés par cet utilisateur."""
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
    # 1. Get the completed order details
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
    """Vérifie si un Tx Hash BEP20 a déjà été utilisé."""
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
    """Enregistre un Tx Hash BEP20 comme utilisé. Retourne False si déjà utilisé."""
    db = await get_db()
    try:
        try:
            await db.execute(
                "INSERT INTO used_bep20_transactions (tx_hash, order_id, user_telegram_id, amount) VALUES (?, ?, ?, ?)",
                (tx_hash.strip().lower(), order_id, user_telegram_id, amount),
            )
            await db.commit()
            return True
        except Exception:
            # UNIQUE constraint violation = already used
            return False
    finally:
        await db.close()


# ── settings CRUD ──────────────────────────────────────────────

async def get_setting(key: str) -> str | None:
    """Retourne la valeur d'un paramètre ou None."""
    db = await get_db()
    try:
        cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cursor.fetchone()
        return row["value"] if row else None
    finally:
        await db.close()


async def set_setting(key: str, value: str) -> None:
    """Enregistre ou met à jour un paramètre."""
    db = await get_db()
    try:
        await db.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value.strip()),
        )
        await db.commit()
    finally:
        await db.close()


# ── TRC20 Transactions ──────────────────────────────────────────

async def is_trc20_transaction_used(tx_hash: str) -> bool:
    """Vérifie si un Tx Hash TRC20 a déjà été utilisé."""
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
    """Enregistre un Tx Hash TRC20 comme utilisé. Retourne False si déjà utilisé."""
    db = await get_db()
    try:
        try:
            await db.execute(
                "INSERT INTO used_trc20_transactions (tx_hash, order_id, user_telegram_id, amount) VALUES (?, ?, ?, ?)",
                (tx_hash.strip().lower(), order_id, user_telegram_id, amount),
            )
            await db.commit()
            return True
        except Exception:
            return False
    finally:
        await db.close()
