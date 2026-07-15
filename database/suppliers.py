"""Persistence and idempotency for external supplier products and orders."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from database.db import get_db


DEFAULT_SUPPLIER_CODE = "canboso"
# Backwards-compatible export used by older integrations.
SUPPLIER_CODE = DEFAULT_SUPPLIER_CODE
SUPPLIER_DESCRIPTION_LANGUAGES = ("en", "fr", "ar", "zh", "vi", "ru")
MAX_SUPPLIER_DESCRIPTION_LENGTH = 3000
MAX_SUPPLIER_NAME_LENGTH = 160
MAX_SUPPLIER_EMOJI_LENGTH = 16
MAX_SUPPLIER_IMAGE_URL_LENGTH = 2048


def _provider(supplier_code: str) -> dict:
    from services.supplier_registry import get_supplier_provider

    return get_supplier_provider(supplier_code)


def _settings_prefix(supplier_code: str) -> str:
    return f"supplier_{_provider(supplier_code)['code']}"


def calculate_supplier_price(
    base_price: float, margin_type: str, margin_value: float
) -> float:
    base = max(0.0, float(base_price or 0))
    value = max(0.0, float(margin_value or 0))
    if margin_type == "sale_price":
        return round(value, 2)
    if margin_type == "percent":
        return round(base * (1.0 + value / 100.0), 2)
    return round(base + value, 2)


def supplier_price_is_safe(
    base_price: float, margin_type: str, margin_value: float
) -> bool:
    """Fixed sale prices must stay strictly above the supplier cost."""
    if margin_type != "sale_price":
        return True
    return float(margin_value or 0) > float(base_price or 0)


async def _setting(db, key: str, default: str) -> str:
    cursor = await db.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = await cursor.fetchone()
    return str(row["value"]) if row and row["value"] is not None else default


async def _global_margin(db, supplier_code: str) -> tuple[str, float]:
    prefix = _settings_prefix(supplier_code)
    margin_type = await _setting(db, f"{prefix}_margin_type", "fixed")
    if margin_type not in ("fixed", "percent"):
        margin_type = "fixed"
    try:
        margin_value = max(
            0.0, float(await _setting(db, f"{prefix}_margin_value", "1"))
        )
    except ValueError:
        margin_value = 1.0
    return margin_type, margin_value


async def _supplier_config(db, supplier_code: str) -> dict:
    """Load all provider settings in one indexed database round trip."""
    provider = _provider(supplier_code)
    prefix = _settings_prefix(supplier_code)
    keys = {
        "enabled": f"{prefix}_enabled",
        "margin_type": f"{prefix}_margin_type",
        "margin_value": f"{prefix}_margin_value",
        "units_per_usd": f"{prefix}_units_per_usd",
        "last_sync": f"{prefix}_last_sync",
    }
    placeholders = ",".join("?" for _ in keys)
    cursor = await db.execute(
        f"SELECT key, value FROM settings WHERE key IN ({placeholders})",
        list(keys.values()),
    )
    values = {str(row["key"]): str(row["value"]) for row in await cursor.fetchall()}
    margin_type = values.get(keys["margin_type"], "fixed")
    if margin_type not in ("fixed", "percent"):
        margin_type = "fixed"
    try:
        margin_value = max(0.0, float(values.get(keys["margin_value"], "1")))
    except ValueError:
        margin_value = 1.0
    try:
        units_per_usd = max(
            1.0,
            float(
                values.get(
                    keys["units_per_usd"],
                    str(provider["default_units_per_usd"]),
                )
            ),
        )
    except ValueError:
        units_per_usd = max(1.0, float(provider["default_units_per_usd"]))
    enabled_default = "1" if supplier_code == DEFAULT_SUPPLIER_CODE else "0"
    return {
        "enabled": values.get(keys["enabled"], enabled_default) != "0",
        "margin_type": margin_type,
        "margin_value": margin_value,
        "units_per_usd": units_per_usd,
        "last_sync": values.get(keys["last_sync"], ""),
    }


async def _units_per_usd(db, supplier_code: str) -> float:
    provider = _provider(supplier_code)
    default = float(provider["default_units_per_usd"])
    try:
        return max(
            1.0,
            float(
                await _setting(
                    db,
                    f"{_settings_prefix(supplier_code)}_units_per_usd",
                    str(default),
                )
            ),
        )
    except ValueError:
        return max(1.0, default)


async def get_supplier_units_per_usd(
    supplier_code: str = DEFAULT_SUPPLIER_CODE,
) -> float:
    supplier_code = _provider(supplier_code)["code"]
    db = await get_db()
    try:
        return await _units_per_usd(db, supplier_code)
    finally:
        await db.close()


async def _category_id(db) -> int:
    cursor = await db.execute(
        "SELECT id FROM categories WHERE COALESCE(is_deleted, 0) = 0 ORDER BY id LIMIT 1"
    )
    row = await cursor.fetchone()
    if row:
        return int(row["id"])
    cursor = await db.execute(
        "INSERT INTO categories (name, emoji, description, is_active) "
        "VALUES ('API Catalog', '🔌', 'External supplier products', 1)"
    )
    return int(cursor.lastrowid)


async def _effective_margin(db, row: dict) -> tuple[str, float]:
    global_type, global_value = await _global_margin(db, row["supplier_code"])
    row_type = str(row.get("margin_type") or "inherit")
    if row_type in ("fixed", "percent", "sale_price"):
        return row_type, max(0.0, float(row.get("margin_value") or 0))
    return global_type, global_value


def _effective_margin_from_global(
    row: dict, global_type: str, global_value: float
) -> tuple[str, float]:
    row_type = str(row.get("margin_type") or "inherit")
    if row_type in ("fixed", "percent", "sale_price"):
        return row_type, max(0.0, float(row.get("margin_value") or 0))
    return global_type, global_value


def _clean_description(value) -> str:
    return str(value or "").strip()[:MAX_SUPPLIER_DESCRIPTION_LENGTH]


def _product_descriptions(row: dict) -> dict[str, str]:
    custom_english = _clean_description(row.get("description_en"))
    return {
        "en": custom_english or _clean_description(row.get("description")),
        "fr": _clean_description(row.get("description_fr")),
        "ar": _clean_description(row.get("description_ar")),
        "zh": _clean_description(row.get("description_zh")),
        "vi": _clean_description(row.get("description_vi")),
        "ru": _clean_description(row.get("description_ru")),
    }


def _display_name(row: dict) -> str:
    return (
        str(row.get("custom_name") or "").strip()[:MAX_SUPPLIER_NAME_LENGTH]
        or str(row.get("name") or "Product").strip()[:MAX_SUPPLIER_NAME_LENGTH]
    )


def _display_emoji(row: dict) -> str:
    return (
        str(row.get("custom_emoji") or "").strip()[:MAX_SUPPLIER_EMOJI_LENGTH]
        or str(row.get("emoji") or "📦").strip()[:MAX_SUPPLIER_EMOJI_LENGTH]
    )


def _display_warranty_days(row: dict) -> int:
    custom_value = row.get("custom_warranty_days")
    if custom_value is not None:
        return max(0, min(int(custom_value), 36500))
    return max(0, min(int(row.get("warranty_days") or 0), 36500))


def _display_image_url(row: dict) -> str:
    return (
        str(row.get("custom_image_url") or "").strip()[
            :MAX_SUPPLIER_IMAGE_URL_LENGTH
        ]
        or str(row.get("image_url") or "").strip()[:MAX_SUPPLIER_IMAGE_URL_LENGTH]
    )


async def _supplier_enabled(db, supplier_code: str) -> bool:
    # Preserve the established Canboso behavior. New providers remain hidden
    # until explicitly enabled by the administrator.
    default = "1" if supplier_code == DEFAULT_SUPPLIER_CODE else "0"
    return (
        await _setting(
            db, f"{_settings_prefix(supplier_code)}_enabled", default
        )
    ) != "0"


async def _upsert_local_product(
    db,
    row: dict,
    *,
    global_margin: tuple[str, float] | None = None,
    supplier_enabled: bool | None = None,
) -> int:
    if global_margin is None:
        margin_type, margin_value = await _effective_margin(db, row)
    else:
        margin_type, margin_value = _effective_margin_from_global(
            row, global_margin[0], global_margin[1]
        )
    final_price = calculate_supplier_price(
        row["base_price"], margin_type, margin_value
    )
    price_safe = supplier_price_is_safe(
        row["base_price"], margin_type, margin_value
    )
    descriptions = _product_descriptions(row)
    display_name = _display_name(row)
    display_emoji = _display_emoji(row)
    display_image_url = _display_image_url(row)
    custom_emoji_id = str(row.get("custom_emoji_id") or "").strip()
    if supplier_enabled is None:
        supplier_enabled = await _supplier_enabled(db, row["supplier_code"])
    is_active = 1 if row.get("enabled") and supplier_enabled and price_safe else 0
    local_id = row.get("local_product_id")
    if local_id:
        await db.execute(
            """UPDATE products SET name = ?, description = ?, description_fr = ?, description_ar = ?,
                      description_zh = ?, description_vi = ?, description_ru = ?,
                      price_usd = ?, warranty_days = ?, emoji = ?, custom_emoji_id = ?,
                      telegram_file_id = CASE
                          WHEN COALESCE(image_url, '') <> ? THEN NULL
                          ELSE telegram_file_id END,
                      image_url = ?,
                      delivery_type = 'supplier_api', is_active = ?, is_deleted = 0
               WHERE id = ?""",
            (
                display_name,
                descriptions["en"],
                descriptions["fr"],
                descriptions["ar"],
                descriptions["zh"],
                descriptions["vi"],
                descriptions["ru"],
                final_price,
                _display_warranty_days(row),
                display_emoji,
                custom_emoji_id or None,
                display_image_url,
                display_image_url or None,
                is_active,
                int(local_id),
            ),
        )
        return int(local_id)
    category_id = await _category_id(db)
    cursor = await db.execute(
        """INSERT INTO products
           (category_id, name, description, description_fr, description_ar,
            description_zh, description_vi, description_ru, price_usd,
            warranty_days, emoji, custom_emoji_id, image_url, delivery_type, is_active, is_deleted)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'supplier_api', ?, 0)""",
        (
            category_id,
            display_name,
            descriptions["en"],
            descriptions["fr"],
            descriptions["ar"],
            descriptions["zh"],
            descriptions["vi"],
            descriptions["ru"],
            final_price,
            _display_warranty_days(row),
            display_emoji,
            custom_emoji_id or None,
            display_image_url or None,
            is_active,
        ),
    )
    local_id = int(cursor.lastrowid)
    await db.execute(
        "UPDATE supplier_products SET local_product_id = ? WHERE id = ?",
        (local_id, int(row["id"])),
    )
    return local_id


async def sync_supplier_products(
    products: list[dict], supplier_code: str = DEFAULT_SUPPLIER_CODE
) -> dict:
    from database.models import _clear_stock_cache, clear_products_cache

    provider = _provider(supplier_code)
    supplier_code = provider["code"]
    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        for product in products:
            source_price = float(
                product.get("source_price", product.get("base_price") or 0)
            )
            source_currency = str(
                product.get("source_currency")
                or provider["source_currency"]
            ).upper()
            await db.execute(
                """INSERT INTO supplier_products
                   (supplier_code, external_product_id, name, description,
                    base_price, source_price, source_currency, remote_stock,
                    warranty_days, image_url, emoji, raw_payload, last_synced_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                   ON CONFLICT(supplier_code, external_product_id) DO UPDATE SET
                    name = excluded.name, description = excluded.description,
                    base_price = excluded.base_price,
                    source_price = excluded.source_price,
                    source_currency = excluded.source_currency,
                    remote_stock = excluded.remote_stock,
                    warranty_days = excluded.warranty_days,
                    image_url = excluded.image_url, emoji = excluded.emoji,
                    raw_payload = excluded.raw_payload,
                    last_synced_at = CURRENT_TIMESTAMP""",
                (
                    supplier_code,
                    str(product["external_product_id"]),
                    product["name"],
                    product.get("description") or "",
                    float(product["base_price"]),
                    source_price,
                    source_currency,
                    int(product.get("remote_stock") or 0),
                    int(product.get("warranty_days") or 0),
                    product.get("image_url") or "",
                    product.get("emoji") or "📦",
                    json.dumps(
                        product.get("raw_payload") or {},
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                ),
            )
        external_ids = [str(product["external_product_id"]) for product in products]
        if external_ids:
            placeholders = ",".join("?" for _ in external_ids)
            await db.execute(
                f"UPDATE supplier_products SET remote_stock = 0 "
                f"WHERE supplier_code = ? AND external_product_id NOT IN ({placeholders})",
                [supplier_code, *external_ids],
            )
        else:
            await db.execute(
                "UPDATE supplier_products SET remote_stock = 0 WHERE supplier_code = ?",
                (supplier_code,),
            )
        config = await _supplier_config(db, supplier_code)
        cursor = await db.execute(
            "SELECT * FROM supplier_products WHERE supplier_code = ? AND enabled = 1",
            (supplier_code,),
        )
        selected = [dict(row) for row in await cursor.fetchall()]
        for row in selected:
            await _upsert_local_product(
                db,
                row,
                global_margin=(config["margin_type"], config["margin_value"]),
                supplier_enabled=config["enabled"],
            )
        key = f"{_settings_prefix(supplier_code)}_last_sync"
        await db.execute(
            """INSERT INTO settings (key, value) VALUES (?, CURRENT_TIMESTAMP)
               ON CONFLICT(key) DO UPDATE SET value = CURRENT_TIMESTAMP""",
            (key,),
        )
        await db.commit()
        clear_products_cache()
        _clear_stock_cache()
        return {
            "supplier_code": supplier_code,
            "synced": len(products),
            "selected": len(selected),
        }
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()


async def get_supplier_dashboard(
    supplier_code: str = DEFAULT_SUPPLIER_CODE,
) -> dict:
    supplier_code = _provider(supplier_code)["code"]
    db = await get_db()
    try:
        config = await _supplier_config(db, supplier_code)
        global_type = config["margin_type"]
        global_value = config["margin_value"]
        cursor = await db.execute(
            "SELECT * FROM supplier_products WHERE supplier_code = ? "
            "ORDER BY enabled DESC, name COLLATE NOCASE",
            (supplier_code,),
        )
        products = []
        for raw_row in await cursor.fetchall():
            row = dict(raw_row)
            margin_type, margin_value = _effective_margin_from_global(
                row, global_type, global_value
            )
            row.update(
                display_name=_display_name(row),
                display_emoji=_display_emoji(row),
                display_image_url=_display_image_url(row),
                display_warranty_days=_display_warranty_days(row),
                effective_margin_type=margin_type,
                effective_margin_value=margin_value,
                final_price=calculate_supplier_price(
                    row["base_price"], margin_type, margin_value
                ),
                price_safe=supplier_price_is_safe(
                    row["base_price"], margin_type, margin_value
                ),
                enabled=bool(row.get("enabled")),
            )
            row.pop("raw_payload", None)
            products.append(row)
        cursor = await db.execute(
            "SELECT status, COUNT(*) AS count FROM supplier_orders "
            "WHERE supplier_code = ? GROUP BY status",
            (supplier_code,),
        )
        return {
            "supplier_code": supplier_code,
            "enabled": config["enabled"],
            "margin_type": global_type,
            "margin_value": global_value,
            "units_per_usd": config["units_per_usd"],
            "last_sync": config["last_sync"],
            "products": products,
            "order_counts": {
                row["status"]: int(row["count"])
                for row in await cursor.fetchall()
            },
        }
    finally:
        await db.close()


async def get_supplier_stats(
    supplier_code: str = DEFAULT_SUPPLIER_CODE,
    *,
    days: int = 30,
) -> dict:
    """Return lightweight financial and sales analytics for one supplier."""
    supplier_code = _provider(supplier_code)["code"]
    days = max(1, min(int(days), 365))
    today = datetime.now(timezone.utc).date()
    start_day = today - timedelta(days=days - 1)
    start_date = start_day.isoformat()
    completed_date = "DATE(COALESCE(so.completed_at, so.updated_at, so.created_at))"

    db = await get_db()
    try:
        cursor = await db.execute(
            f"""SELECT
                    COUNT(*) AS order_count,
                    COALESCE(SUM(so.quantity), 0) AS items_sold,
                    COALESCE(SUM(COALESCE(so.revenue_usd, o.amount_usd, 0)), 0) AS revenue,
                    COALESCE(SUM(COALESCE(so.cost_usd, 0)), 0) AS cost,
                    COALESCE(SUM(CASE WHEN so.cost_estimated = 1 THEN 1 ELSE 0 END), 0) AS estimated_orders,
                    COALESCE(SUM(CASE WHEN so.cost_usd IS NULL THEN 1 ELSE 0 END), 0) AS missing_cost_orders
                FROM supplier_orders so
                LEFT JOIN orders o ON o.id = so.order_id
                WHERE so.supplier_code = ? AND so.status = 'completed'
                  AND {completed_date} >= ?""",
            (supplier_code, start_date),
        )
        total = dict(await cursor.fetchone())

        cursor = await db.execute(
            """SELECT status, COUNT(*) AS count
               FROM supplier_orders
               WHERE supplier_code = ? AND DATE(created_at) >= ?
               GROUP BY status""",
            (supplier_code, start_date),
        )
        status_counts = {
            str(row["status"]): int(row["count"])
            for row in await cursor.fetchall()
        }

        cursor = await db.execute(
            f"""SELECT
                    so.external_product_id,
                    MAX(COALESCE(NULLIF(TRIM(sp.custom_name), ''), sp.name, so.external_product_id)) AS name,
                    MAX(COALESCE(NULLIF(TRIM(sp.custom_emoji), ''), sp.emoji, '📦')) AS emoji,
                    COUNT(*) AS order_count,
                    COALESCE(SUM(so.quantity), 0) AS items_sold,
                    COALESCE(SUM(COALESCE(so.revenue_usd, o.amount_usd, 0)), 0) AS revenue,
                    COALESCE(SUM(COALESCE(so.cost_usd, 0)), 0) AS cost,
                    COALESCE(SUM(CASE WHEN so.cost_estimated = 1 THEN 1 ELSE 0 END), 0) AS estimated_orders,
                    COALESCE(SUM(CASE WHEN so.cost_usd IS NULL THEN 1 ELSE 0 END), 0) AS missing_cost_orders
                FROM supplier_orders so
                LEFT JOIN orders o ON o.id = so.order_id
                LEFT JOIN supplier_products sp
                  ON sp.supplier_code = so.supplier_code
                 AND sp.external_product_id = so.external_product_id
                WHERE so.supplier_code = ? AND so.status = 'completed'
                  AND {completed_date} >= ?
                GROUP BY so.external_product_id
                ORDER BY items_sold DESC, revenue DESC""",
            (supplier_code, start_date),
        )
        products = []
        for raw in await cursor.fetchall():
            row = dict(raw)
            revenue = float(row.get("revenue") or 0)
            cost = float(row.get("cost") or 0)
            profit = revenue - cost
            products.append(
                {
                    "external_product_id": str(row["external_product_id"]),
                    "name": str(row.get("name") or row["external_product_id"]),
                    "emoji": str(row.get("emoji") or "📦"),
                    "orders": int(row.get("order_count") or 0),
                    "items_sold": int(row.get("items_sold") or 0),
                    "revenue": round(revenue, 2),
                    "cost": round(cost, 2),
                    "profit": round(profit, 2),
                    "margin_percent": round((profit / revenue * 100) if revenue else 0, 2),
                    "estimated_cost_orders": int(row.get("estimated_orders") or 0),
                    "missing_cost_orders": int(row.get("missing_cost_orders") or 0),
                }
            )

        cursor = await db.execute(
            f"""SELECT
                    {completed_date} AS day,
                    COUNT(*) AS order_count,
                    COALESCE(SUM(so.quantity), 0) AS items_sold,
                    COALESCE(SUM(COALESCE(so.revenue_usd, o.amount_usd, 0)), 0) AS revenue,
                    COALESCE(SUM(COALESCE(so.cost_usd, 0)), 0) AS cost
                FROM supplier_orders so
                LEFT JOIN orders o ON o.id = so.order_id
                WHERE so.supplier_code = ? AND so.status = 'completed'
                  AND {completed_date} >= ?
                GROUP BY day ORDER BY day""",
            (supplier_code, start_date),
        )
        daily_by_date = {str(row["day"]): dict(row) for row in await cursor.fetchall()}
        daily = []
        for offset in range(days):
            day = (start_day + timedelta(days=offset)).isoformat()
            row = daily_by_date.get(day, {})
            revenue = float(row.get("revenue") or 0)
            cost = float(row.get("cost") or 0)
            daily.append(
                {
                    "day": day,
                    "orders": int(row.get("order_count") or 0),
                    "items_sold": int(row.get("items_sold") or 0),
                    "revenue": round(revenue, 2),
                    "cost": round(cost, 2),
                    "profit": round(revenue - cost, 2),
                }
            )

        revenue = float(total.get("revenue") or 0)
        cost = float(total.get("cost") or 0)
        profit = revenue - cost
        completed_orders = int(total.get("order_count") or 0)
        attempted_orders = sum(status_counts.values())
        completed_attempts = int(status_counts.get("completed", 0))
        return {
            "supplier_code": supplier_code,
            "days": days,
            "start_date": start_date,
            "end_date": today.isoformat(),
            "summary": {
                "revenue": round(revenue, 2),
                "cost": round(cost, 2),
                "profit": round(profit, 2),
                "margin_percent": round((profit / revenue * 100) if revenue else 0, 2),
                "items_sold": int(total.get("items_sold") or 0),
                "orders": completed_orders,
                "average_order": round((revenue / completed_orders) if completed_orders else 0, 2),
                "success_rate": round((completed_attempts / attempted_orders * 100) if attempted_orders else 0, 2),
            },
            "status_counts": status_counts,
            "data_quality": {
                "estimated_cost_orders": int(total.get("estimated_orders") or 0),
                "missing_cost_orders": int(total.get("missing_cost_orders") or 0),
            },
            "products": products,
            "daily": daily,
        }
    finally:
        await db.close()


async def update_supplier_settings(
    *,
    enabled: bool,
    margin_type: str,
    margin_value: float,
    supplier_code: str = DEFAULT_SUPPLIER_CODE,
    units_per_usd: float | None = None,
) -> None:
    from database.models import _clear_stock_cache, clear_products_cache

    provider = _provider(supplier_code)
    supplier_code = provider["code"]
    if margin_type not in ("fixed", "percent"):
        raise ValueError("INVALID_MARGIN_TYPE")
    margin_value = max(0.0, min(float(margin_value), 100000.0))
    if units_per_usd is not None:
        units_per_usd = max(1.0, min(float(units_per_usd), 1000000000.0))
    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        prefix = _settings_prefix(supplier_code)
        settings = [
            (f"{prefix}_enabled", "1" if enabled else "0"),
            (f"{prefix}_margin_type", margin_type),
            (f"{prefix}_margin_value", str(margin_value)),
        ]
        if units_per_usd is not None:
            settings.append((f"{prefix}_units_per_usd", str(units_per_usd)))
        for key, value in settings:
            await db.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (key, value),
            )
        if units_per_usd is not None:
            await db.execute(
                """UPDATE supplier_products
                   SET base_price = CASE
                       WHEN source_currency = 'USD' THEN source_price
                       ELSE source_price / ? END
                   WHERE supplier_code = ?""",
                (units_per_usd, supplier_code),
            )
        cursor = await db.execute(
            "SELECT * FROM supplier_products WHERE supplier_code = ? AND enabled = 1",
            (supplier_code,),
        )
        for raw_row in await cursor.fetchall():
            row = dict(raw_row)
            if enabled:
                await _upsert_local_product(
                    db,
                    row,
                    global_margin=(margin_type, margin_value),
                    supplier_enabled=True,
                )
            elif row.get("local_product_id"):
                await db.execute(
                    "UPDATE products SET is_active = 0 WHERE id = ?",
                    (int(row["local_product_id"]),),
                )
        await db.commit()
        clear_products_cache()
        _clear_stock_cache()
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()


async def update_supplier_product(
    mapping_id: int,
    *,
    enabled: bool,
    margin_type: str,
    margin_value: float | None,
    supplier_code: str = DEFAULT_SUPPLIER_CODE,
) -> dict:
    from database.models import _clear_stock_cache, clear_products_cache

    supplier_code = _provider(supplier_code)["code"]
    if margin_type not in ("inherit", "fixed", "percent", "sale_price"):
        raise ValueError("INVALID_MARGIN_TYPE")
    value = (
        None
        if margin_type == "inherit"
        else max(0.0, min(float(margin_value or 0), 100000.0))
    )
    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "UPDATE supplier_products SET enabled = ?, margin_type = ?, "
            "margin_value = ? WHERE id = ? AND supplier_code = ?",
            (
                1 if enabled else 0,
                margin_type,
                value,
                int(mapping_id),
                supplier_code,
            ),
        )
        cursor = await db.execute(
            "SELECT * FROM supplier_products WHERE id = ? AND supplier_code = ?",
            (int(mapping_id), supplier_code),
        )
        raw = await cursor.fetchone()
        if not raw:
            await db.rollback()
            raise ValueError("SUPPLIER_PRODUCT_NOT_FOUND")
        row = dict(raw)
        config = await _supplier_config(db, supplier_code)
        row["local_product_id"] = await _upsert_local_product(
            db,
            row,
            global_margin=(config["margin_type"], config["margin_value"]),
            supplier_enabled=config["enabled"],
        )
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


async def update_supplier_product_descriptions(
    mapping_id: int,
    descriptions: dict,
    supplier_code: str = DEFAULT_SUPPLIER_CODE,
    *,
    custom_name: str | None = None,
    custom_emoji: str | None = None,
    custom_emoji_id: str | None = None,
    custom_warranty_days: int | None = None,
    custom_image_url: str | None = None,
) -> dict:
    """Save content overrides and update the linked Telegram product."""
    from database.models import clear_products_cache

    supplier_code = _provider(supplier_code)["code"]
    if not isinstance(descriptions, dict):
        raise ValueError("INVALID_DESCRIPTIONS")
    supplied_descriptions = {
        language: _clean_description(descriptions[language])
        for language in SUPPLIER_DESCRIPTION_LANGUAGES
        if language in descriptions
    }
    supplied_fields = {
        f"description_{language}": value
        for language, value in supplied_descriptions.items()
    }
    if custom_name is not None:
        supplied_fields["custom_name"] = str(custom_name).strip()[
            :MAX_SUPPLIER_NAME_LENGTH
        ]
    if custom_emoji is not None:
        supplied_fields["custom_emoji"] = str(custom_emoji).strip()[
            :MAX_SUPPLIER_EMOJI_LENGTH
        ]
    if custom_emoji_id is not None:
        emoji_id = str(custom_emoji_id).strip()
        if emoji_id and (not emoji_id.isdigit() or len(emoji_id) > 32):
            raise ValueError("INVALID_CUSTOM_EMOJI_ID")
        supplied_fields["custom_emoji_id"] = emoji_id
    if custom_warranty_days is not None:
        supplied_fields["custom_warranty_days"] = max(
            0, min(int(custom_warranty_days), 36500)
        )
    if custom_image_url is not None:
        image_url = str(custom_image_url).strip()[:MAX_SUPPLIER_IMAGE_URL_LENGTH]
        if image_url and not image_url.lower().startswith(("https://", "http://")):
            raise ValueError("INVALID_IMAGE_URL")
        supplied_fields["custom_image_url"] = image_url
    if not supplied_fields:
        raise ValueError("NO_PRODUCT_CUSTOMIZATIONS")
    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        set_parts = [f"{column} = ?" for column in supplied_fields]
        await db.execute(
            f"UPDATE supplier_products SET {', '.join(set_parts)} "
            "WHERE id = ? AND supplier_code = ?",
            [*supplied_fields.values(), int(mapping_id), supplier_code],
        )
        cursor = await db.execute(
            "SELECT * FROM supplier_products WHERE id = ? AND supplier_code = ?",
            (int(mapping_id), supplier_code),
        )
        raw = await cursor.fetchone()
        if not raw:
            await db.rollback()
            raise ValueError("SUPPLIER_PRODUCT_NOT_FOUND")
        row = dict(raw)
        if row.get("enabled") or row.get("local_product_id"):
            config = await _supplier_config(db, supplier_code)
            row["local_product_id"] = await _upsert_local_product(
                db,
                row,
                global_margin=(config["margin_type"], config["margin_value"]),
                supplier_enabled=config["enabled"],
            )
        await db.commit()
        clear_products_cache()
        return row
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()


async def get_supplier_product_by_local_product(
    local_product_id: int,
) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM supplier_products WHERE local_product_id = ? "
            "AND enabled = 1 LIMIT 1",
            (int(local_product_id),),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def get_supplier_mapping_by_local_product(
    local_product_id: int,
) -> dict | None:
    """Return a supplier mapping even when its storefront toggle is disabled."""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM supplier_products WHERE local_product_id = ? LIMIT 1",
            (int(local_product_id),),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None
    finally:
        await db.close()


async def supplier_stock_counts() -> dict[int, int]:
    from services.supplier_api import SupplierAPIError, calculate_affordable_stock
    from services.supplier_registry import get_supplier_balance

    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT local_product_id, supplier_code, remote_stock, base_price, "
            "margin_type, margin_value "
            "FROM supplier_products WHERE enabled = 1 "
            "AND local_product_id IS NOT NULL"
        )
        rows = [dict(row) for row in await cursor.fetchall()]
        rates = {
            code: await _units_per_usd(db, code)
            for code in {row["supplier_code"] for row in rows}
        }
    finally:
        await db.close()
    balances: dict[str, float] = {}
    for code, rate in rates.items():
        try:
            wallet = await get_supplier_balance(code, units_per_usd=rate)
            balances[code] = float(wallet.get("balance") or 0)
        except (SupplierAPIError, ValueError):
            balances[code] = 0.0
    return {
        int(row["local_product_id"]): (
            calculate_affordable_stock(
                row.get("remote_stock"),
                row.get("base_price"),
                balances.get(row["supplier_code"], 0.0),
            )
            if supplier_price_is_safe(
                row.get("base_price"),
                str(row.get("margin_type") or "inherit"),
                row.get("margin_value") or 0,
            )
            else 0
        )
        for row in rows
    }


async def get_supplier_available_stock(local_product_id: int) -> int:
    mapping = await get_supplier_product_by_local_product(local_product_id)
    if not mapping:
        return 0
    return await supplier_available_stock(mapping)


async def supplier_available_stock(mapping: dict) -> int:
    from services.supplier_api import SupplierAPIError, calculate_affordable_stock
    from services.supplier_registry import get_supplier_balance

    supplier_code = str(mapping.get("supplier_code") or DEFAULT_SUPPLIER_CODE)
    if not supplier_price_is_safe(
        mapping.get("base_price"),
        str(mapping.get("margin_type") or "inherit"),
        mapping.get("margin_value") or 0,
    ):
        return 0
    try:
        units_per_usd = await get_supplier_units_per_usd(supplier_code)
        wallet = await get_supplier_balance(
            supplier_code, units_per_usd=units_per_usd
        )
        balance = float(wallet.get("balance") or 0)
    except (SupplierAPIError, ValueError):
        return 0
    return calculate_affordable_stock(
        mapping.get("remote_stock"), mapping.get("base_price"), balance
    )


async def claim_supplier_order(
    order_id: int, mapping: dict, quantity: int
) -> dict:
    supplier_code = _provider(
        str(mapping.get("supplier_code") or DEFAULT_SUPPLIER_CODE)
    )["code"]
    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        quantity = max(1, int(quantity))
        cost_usd = round(
            max(0.0, float(mapping.get("base_price") or 0)) * quantity,
            6,
        )
        order_cursor = await db.execute(
            "SELECT amount_usd FROM orders WHERE id = ?",
            (int(order_id),),
        )
        order_row = await order_cursor.fetchone()
        revenue_usd = (
            round(max(0.0, float(order_row["amount_usd"])), 6)
            if order_row and order_row["amount_usd"] is not None
            else None
        )
        cursor = await db.execute(
            "SELECT * FROM supplier_orders WHERE order_id = ?", (int(order_id),)
        )
        existing = await cursor.fetchone()
        if existing:
            row = dict(existing)
            if row["status"] in ("completed", "purchasing", "unknown"):
                await db.commit()
                return {**row, "claimed": False}
            await db.execute(
                "UPDATE supplier_orders SET status = 'purchasing', "
                "attempts = attempts + 1, error = NULL, "
                "cost_usd = COALESCE(cost_usd, ?), "
                "revenue_usd = COALESCE(revenue_usd, ?), "
                "cost_estimated = CASE WHEN cost_usd IS NULL THEN 0 ELSE cost_estimated END, "
                "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (cost_usd, revenue_usd, int(row["id"])),
            )
            await db.commit()
            return {**row, "status": "purchasing", "claimed": True}
        cursor = await db.execute(
            """INSERT INTO supplier_orders
               (order_id, supplier_code, external_product_id, quantity,
                status, attempts, cost_usd, revenue_usd, cost_estimated)
               VALUES (?, ?, ?, ?, 'purchasing', 1, ?, ?, 0)""",
            (
                int(order_id),
                supplier_code,
                str(mapping["external_product_id"]),
                quantity,
                cost_usd,
                revenue_usd,
            ),
        )
        await db.commit()
        return {
            "id": int(cursor.lastrowid),
            "order_id": int(order_id),
            "supplier_code": supplier_code,
            "status": "purchasing",
            "claimed": True,
        }
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()


async def finish_supplier_order(
    supplier_order_id: int, result: dict
) -> list[dict]:
    items = result.get("items") or []
    db = await get_db()
    try:
        await db.execute(
            """UPDATE supplier_orders SET status = 'completed',
                      external_order_id = ?, delivered_items = ?, raw_payload = ?,
                      error = NULL, completed_at = CURRENT_TIMESTAMP,
                      updated_at = CURRENT_TIMESTAMP WHERE id = ?""",
            (
                result.get("external_order_id") or None,
                json.dumps(items, ensure_ascii=False, separators=(",", ":")),
                json.dumps(
                    result.get("raw_payload") or {},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                int(supplier_order_id),
            ),
        )
        await db.commit()
        return items
    finally:
        await db.close()


async def fail_supplier_order(
    supplier_order_id: int, error: str, *, unknown: bool
) -> None:
    db = await get_db()
    try:
        await db.execute(
            "UPDATE supplier_orders SET status = ?, error = ?, "
            "updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (
                "unknown" if unknown else "failed",
                str(error)[:1000],
                int(supplier_order_id),
            ),
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
