"""Persistence and idempotency for external supplier products and orders."""

from __future__ import annotations

import json

from database.db import get_db


SUPPLIER_CODE = "canboso"


def calculate_supplier_price(base_price: float, margin_type: str, margin_value: float) -> float:
    base = max(0.0, float(base_price or 0))
    value = max(0.0, float(margin_value or 0))
    return round(base * (1.0 + value / 100.0), 2) if margin_type == "percent" else round(base + value, 2)


async def _setting(db, key: str, default: str) -> str:
    cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = await cursor.fetchone()
    return str(row["value"]) if row and row["value"] is not None else default


async def _global_margin(db) -> tuple[str, float]:
    margin_type = await _setting(db, "supplier_canboso_margin_type", "fixed")
    if margin_type not in ("fixed", "percent"):
        margin_type = "fixed"
    try:
        margin_value = max(0.0, float(await _setting(db, "supplier_canboso_margin_value", "1")))
    except ValueError:
        margin_value = 1.0
    return margin_type, margin_value


async def _category_id(db) -> int:
    cursor = await db.execute("SELECT id FROM categories WHERE COALESCE(is_deleted, 0) = 0 ORDER BY id LIMIT 1")
    row = await cursor.fetchone()
    if row:
        return int(row["id"])
    cursor = await db.execute(
        "INSERT INTO categories (name, emoji, description, is_active) VALUES ('API Catalog', '🔌', 'External supplier products', 1)"
    )
    return int(cursor.lastrowid)


async def _effective_margin(db, row: dict) -> tuple[str, float]:
    global_type, global_value = await _global_margin(db)
    row_type = str(row.get("margin_type") or "inherit")
    if row_type in ("fixed", "percent"):
        return row_type, max(0.0, float(row.get("margin_value") or 0))
    return global_type, global_value


async def _upsert_local_product(db, row: dict) -> int:
    margin_type, margin_value = await _effective_margin(db, row)
    final_price = calculate_supplier_price(row["base_price"], margin_type, margin_value)
    supplier_enabled = (await _setting(db, "supplier_canboso_enabled", "1")) != "0"
    is_active = 1 if row.get("enabled") and supplier_enabled else 0
    local_id = row.get("local_product_id")
    if local_id:
        await db.execute(
            """UPDATE products SET name = ?, description = ?, price_usd = ?, warranty_days = ?,
                      emoji = ?, image_url = ?, delivery_type = 'supplier_api', is_active = ?, is_deleted = 0
               WHERE id = ?""",
            (row["name"], row.get("description") or "", final_price, int(row.get("warranty_days") or 0),
             row.get("emoji") or "📦", row.get("image_url") or None, is_active, int(local_id)),
        )
        return int(local_id)
    category_id = await _category_id(db)
    cursor = await db.execute(
        """INSERT INTO products
           (category_id, name, description, price_usd, warranty_days, emoji, image_url,
            delivery_type, is_active, is_deleted)
           VALUES (?, ?, ?, ?, ?, ?, ?, 'supplier_api', ?, 0)""",
        (category_id, row["name"], row.get("description") or "", final_price,
         int(row.get("warranty_days") or 0), row.get("emoji") or "📦",
         row.get("image_url") or None, is_active),
    )
    local_id = int(cursor.lastrowid)
    await db.execute("UPDATE supplier_products SET local_product_id = ? WHERE id = ?", (local_id, int(row["id"])))
    return local_id


async def sync_supplier_products(products: list[dict]) -> dict:
    from database.models import clear_products_cache, _clear_stock_cache

    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        for product in products:
            await db.execute(
                """INSERT INTO supplier_products
                   (supplier_code, external_product_id, name, description, base_price, remote_stock,
                    warranty_days, image_url, emoji, raw_payload, last_synced_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(supplier_code, external_product_id) DO UPDATE SET
                    name = excluded.name, description = excluded.description,
                    base_price = excluded.base_price, remote_stock = excluded.remote_stock,
                    warranty_days = excluded.warranty_days, image_url = excluded.image_url,
                    emoji = excluded.emoji, raw_payload = excluded.raw_payload,
                    last_synced_at = CURRENT_TIMESTAMP""",
                (SUPPLIER_CODE, str(product["external_product_id"]), product["name"], product.get("description") or "",
                 float(product["base_price"]), int(product.get("remote_stock") or 0),
                 int(product.get("warranty_days") or 0), product.get("image_url") or "",
                 product.get("emoji") or "📦",
                 json.dumps(product.get("raw_payload") or {}, ensure_ascii=False, separators=(",", ":"))),
            )
        external_ids = [str(product["external_product_id"]) for product in products]
        if external_ids:
            placeholders = ",".join("?" for _ in external_ids)
            await db.execute(
                f"UPDATE supplier_products SET remote_stock = 0 WHERE supplier_code = ? AND external_product_id NOT IN ({placeholders})",
                [SUPPLIER_CODE, *external_ids],
            )
        else:
            await db.execute("UPDATE supplier_products SET remote_stock = 0 WHERE supplier_code = ?", (SUPPLIER_CODE,))
        cursor = await db.execute("SELECT * FROM supplier_products WHERE supplier_code = ? AND enabled = 1", (SUPPLIER_CODE,))
        selected = [dict(row) for row in await cursor.fetchall()]
        for row in selected:
            await _upsert_local_product(db, row)
        await db.execute(
            """INSERT INTO settings (key, value) VALUES ('supplier_canboso_last_sync', CURRENT_TIMESTAMP)
               ON CONFLICT(key) DO UPDATE SET value = CURRENT_TIMESTAMP"""
        )
        await db.commit()
        clear_products_cache()
        _clear_stock_cache()
        return {"synced": len(products), "selected": len(selected)}
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()


async def get_supplier_dashboard() -> dict:
    db = await get_db()
    try:
        global_type, global_value = await _global_margin(db)
        enabled = (await _setting(db, "supplier_canboso_enabled", "1")) != "0"
        last_sync = await _setting(db, "supplier_canboso_last_sync", "")
        cursor = await db.execute(
            "SELECT * FROM supplier_products WHERE supplier_code = ? ORDER BY enabled DESC, name COLLATE NOCASE",
            (SUPPLIER_CODE,),
        )
        products = []
        for raw_row in await cursor.fetchall():
            row = dict(raw_row)
            margin_type, margin_value = await _effective_margin(db, row)
            row.update(
                effective_margin_type=margin_type,
                effective_margin_value=margin_value,
                final_price=calculate_supplier_price(row["base_price"], margin_type, margin_value),
                enabled=bool(row.get("enabled")),
            )
            row.pop("raw_payload", None)
            products.append(row)
        cursor = await db.execute(
            "SELECT status, COUNT(*) AS count FROM supplier_orders WHERE supplier_code = ? GROUP BY status",
            (SUPPLIER_CODE,),
        )
        return {
            "enabled": enabled,
            "margin_type": global_type,
            "margin_value": global_value,
            "last_sync": last_sync,
            "products": products,
            "order_counts": {row["status"]: int(row["count"]) for row in await cursor.fetchall()},
        }
    finally:
        await db.close()


async def update_supplier_settings(*, enabled: bool, margin_type: str, margin_value: float) -> None:
    from database.models import clear_products_cache

    if margin_type not in ("fixed", "percent"):
        raise ValueError("INVALID_MARGIN_TYPE")
    margin_value = max(0.0, min(float(margin_value), 100000.0))
    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        for key, value in (("supplier_canboso_enabled", "1" if enabled else "0"),
                           ("supplier_canboso_margin_type", margin_type),
                           ("supplier_canboso_margin_value", str(margin_value))):
            await db.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
        cursor = await db.execute("SELECT * FROM supplier_products WHERE supplier_code = ? AND enabled = 1", (SUPPLIER_CODE,))
        for raw_row in await cursor.fetchall():
            row = dict(raw_row)
            if enabled:
                await _upsert_local_product(db, row)
            elif row.get("local_product_id"):
                await db.execute("UPDATE products SET is_active = 0 WHERE id = ?", (int(row["local_product_id"]),))
        await db.commit()
        clear_products_cache()
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()


async def update_supplier_product(mapping_id: int, *, enabled: bool, margin_type: str, margin_value: float | None) -> dict:
    from database.models import clear_products_cache, _clear_stock_cache

    if margin_type not in ("inherit", "fixed", "percent"):
        raise ValueError("INVALID_MARGIN_TYPE")
    value = None if margin_type == "inherit" else max(0.0, min(float(margin_value or 0), 100000.0))
    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "UPDATE supplier_products SET enabled = ?, margin_type = ?, margin_value = ? WHERE id = ? AND supplier_code = ?",
            (1 if enabled else 0, margin_type, value, int(mapping_id), SUPPLIER_CODE),
        )
        cursor = await db.execute("SELECT * FROM supplier_products WHERE id = ? AND supplier_code = ?", (int(mapping_id), SUPPLIER_CODE))
        raw = await cursor.fetchone()
        if not raw:
            await db.rollback()
            raise ValueError("SUPPLIER_PRODUCT_NOT_FOUND")
        row = dict(raw)
        row["local_product_id"] = await _upsert_local_product(db, row)
        await db.commit()
        clear_products_cache()
        _clear_stock_cache()
        return row
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()


async def get_supplier_product_by_local_product(local_product_id: int) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM supplier_products WHERE local_product_id = ? AND enabled = 1 LIMIT 1",
            (int(local_product_id),),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def supplier_stock_counts() -> dict[int, int]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT local_product_id, remote_stock FROM supplier_products WHERE enabled = 1 AND local_product_id IS NOT NULL"
        )
        return {int(row["local_product_id"]): max(0, int(row["remote_stock"] or 0)) for row in await cursor.fetchall()}
    finally:
        await db.close()


async def claim_supplier_order(order_id: int, mapping: dict, quantity: int) -> dict:
    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute("SELECT * FROM supplier_orders WHERE order_id = ?", (int(order_id),))
        existing = await cursor.fetchone()
        if existing:
            row = dict(existing)
            if row["status"] in ("completed", "purchasing", "unknown"):
                await db.commit()
                return {**row, "claimed": False}
            await db.execute(
                "UPDATE supplier_orders SET status = 'purchasing', attempts = attempts + 1, error = NULL, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (int(row["id"]),),
            )
            await db.commit()
            return {**row, "status": "purchasing", "claimed": True}
        cursor = await db.execute(
            """INSERT INTO supplier_orders (order_id, supplier_code, external_product_id, quantity, status, attempts)
               VALUES (?, ?, ?, ?, 'purchasing', 1)""",
            (int(order_id), SUPPLIER_CODE, str(mapping["external_product_id"]), max(1, int(quantity))),
        )
        await db.commit()
        return {"id": int(cursor.lastrowid), "order_id": int(order_id), "status": "purchasing", "claimed": True}
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()


async def finish_supplier_order(supplier_order_id: int, result: dict) -> list[dict]:
    items = result.get("items") or []
    db = await get_db()
    try:
        await db.execute(
            """UPDATE supplier_orders SET status = 'completed', external_order_id = ?, delivered_items = ?,
                      raw_payload = ?, error = NULL, completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (result.get("external_order_id") or None,
             json.dumps(items, ensure_ascii=False, separators=(",", ":")),
             json.dumps(result.get("raw_payload") or {}, ensure_ascii=False, separators=(",", ":")),
             int(supplier_order_id)),
        )
        await db.commit()
        return items
    finally:
        await db.close()


async def fail_supplier_order(supplier_order_id: int, error: str, *, unknown: bool) -> None:
    db = await get_db()
    try:
        await db.execute(
            "UPDATE supplier_orders SET status = ?, error = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            ("unknown" if unknown else "failed", str(error)[:1000], int(supplier_order_id)),
        )
        await db.commit()
    finally:
        await db.close()


def decoded_supplier_items(row: dict) -> list[dict]:
    try:
        items = json.loads(row.get("delivered_items") or "[]")
        return items if isinstance(items, list) else []
    except (TypeError, ValueError):
        return []
