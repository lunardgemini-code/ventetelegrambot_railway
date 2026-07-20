"""Database access for the supplier catalog analysis and search index."""

from __future__ import annotations

import json
from typing import Iterable

from database.db import get_db


def _codes(values: Iterable[str]) -> list[str]:
    return sorted({str(value).strip().lower() for value in values if str(value).strip()})


async def list_supplier_products_for_analysis(supplier_codes: Iterable[str]) -> list[dict]:
    codes = _codes(supplier_codes)
    if not codes:
        return []
    placeholders = ",".join("?" for _ in codes)
    db = await get_db()
    try:
        cursor = await db.execute(
            f"""SELECT sp.id, sp.supplier_code, sp.external_product_id,
                       COALESCE(NULLIF(TRIM(sp.custom_name), ''), sp.name) AS name,
                       COALESCE(NULLIF(TRIM(sp.description_en), ''), sp.description, '') AS description,
                       COALESCE(sp.custom_warranty_days, sp.warranty_days, 0) AS warranty_days,
                       sp.base_price, sp.remote_stock, sp.last_synced_at,
                       spa.source_hash AS indexed_source_hash
                FROM supplier_products sp
                LEFT JOIN supplier_product_analysis spa ON spa.supplier_product_id = sp.id
                WHERE sp.supplier_code IN ({placeholders})
                ORDER BY sp.supplier_code, sp.id""",
            codes,
        )
        return [dict(row) for row in await cursor.fetchall()]
    finally:
        await db.close()

async def upsert_supplier_product_analysis(rows: list[dict]) -> int:
    if not rows:
        return 0
    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        await db.executemany(
            """INSERT INTO supplier_product_analysis
               (supplier_product_id, supplier_code, family, duration_months,
                duration_days, delivery_mode, access_mode, region, tokens_json,
                analysis_source, confidence, source_hash, analyzed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(supplier_product_id) DO UPDATE SET
                   supplier_code = excluded.supplier_code,
                   family = excluded.family,
                   duration_months = excluded.duration_months,
                   duration_days = excluded.duration_days,
                   delivery_mode = excluded.delivery_mode,
                   access_mode = excluded.access_mode,
                   region = excluded.region,
                   tokens_json = excluded.tokens_json,
                   analysis_source = excluded.analysis_source,
                   confidence = excluded.confidence,
                   source_hash = excluded.source_hash,
                   analyzed_at = CURRENT_TIMESTAMP""",
            [
                (
                    int(row["supplier_product_id"]),
                    str(row["supplier_code"]),
                    str(row.get("family") or ""),
                    row.get("duration_months"),
                    row.get("duration_days"),
                    str(row.get("delivery_mode") or "unknown"),
                    str(row.get("access_mode") or "unknown"),
                    str(row.get("region") or "")[:40],
                    json.dumps(row.get("tokens") or [], ensure_ascii=False, separators=(",", ":")),
                    str(row.get("analysis_source") or "deterministic"),
                    min(1.0, max(0.0, float(row.get("confidence") or 0))),
                    str(row["source_hash"]),
                )
                for row in rows
            ],
        )
        await db.commit()
        return len(rows)
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()


async def list_indexed_supplier_products(supplier_codes: Iterable[str]) -> list[dict]:
    codes = _codes(supplier_codes)
    if not codes:
        return []
    placeholders = ",".join("?" for _ in codes)
    db = await get_db()
    try:
        cursor = await db.execute(
            f"""SELECT sp.id, sp.supplier_code, sp.external_product_id,
                       COALESCE(NULLIF(TRIM(sp.custom_name), ''), sp.name) AS name,
                       COALESCE(NULLIF(TRIM(sp.description_en), ''), sp.description, '') AS description,
                       COALESCE(sp.custom_warranty_days, sp.warranty_days, 0) AS warranty_days,
                       sp.base_price, sp.remote_stock, sp.last_synced_at, sp.enabled,
                       spa.family, spa.duration_months, spa.duration_days,
                       spa.delivery_mode, spa.access_mode, spa.region, spa.tokens_json,
                       spa.analysis_source, spa.confidence, spa.analyzed_at,
                       COALESCE(stats.completed_orders, 0) AS completed_orders,
                       COALESCE(stats.failed_orders, 0) AS failed_orders,
                       COALESCE(stats.unknown_orders, 0) AS unknown_orders
                FROM supplier_products sp
                JOIN supplier_product_analysis spa ON spa.supplier_product_id = sp.id
                LEFT JOIN (
                    SELECT supplier_code, external_product_id,
                           SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) AS completed_orders,
                           SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed_orders,
                           SUM(CASE WHEN status NOT IN ('completed', 'failed', 'pending') THEN 1 ELSE 0 END) AS unknown_orders
                    FROM supplier_orders GROUP BY supplier_code, external_product_id
                ) stats ON stats.supplier_code = sp.supplier_code
                       AND stats.external_product_id = sp.external_product_id
                WHERE sp.supplier_code IN ({placeholders}) AND sp.base_price > 0
                ORDER BY sp.base_price, sp.id""",
            codes,
        )
        result = []
        for raw in await cursor.fetchall():
            row = dict(raw)
            try:
                tokens = json.loads(row.pop("tokens_json", "[]") or "[]")
            except (TypeError, ValueError, json.JSONDecodeError):
                tokens = []
            row["tokens"] = tokens if isinstance(tokens, list) else []
            result.append(row)
        return result
    finally:
        await db.close()


async def get_supplier_wallet_snapshots(supplier_codes: Iterable[str]) -> dict[str, dict]:
    codes = _codes(supplier_codes)
    if not codes:
        return {}
    keys = []
    for code in codes:
        keys.extend((f"supplier_{code}_wallet_balance", f"supplier_{code}_wallet_updated_at"))
    placeholders = ",".join("?" for _ in keys)
    db = await get_db()
    try:
        cursor = await db.execute(
            f"SELECT key, value FROM settings WHERE key IN ({placeholders})",
            keys,
        )
        values = {str(row["key"]): str(row["value"]) for row in await cursor.fetchall()}
        snapshots = {}
        for code in codes:
            try:
                balance = max(0.0, float(values.get(f"supplier_{code}_wallet_balance", "0")))
            except ValueError:
                balance = 0.0
            snapshots[code] = {
                "balance": balance,
                "updated_at": values.get(f"supplier_{code}_wallet_updated_at", ""),
            }
        return snapshots
    finally:
        await db.close()


async def save_supplier_ai_run_summary(summary: dict) -> None:
    db = await get_db()
    try:
        value = json.dumps(summary, ensure_ascii=False, separators=(",", ":"))
        await db.execute(
            "INSERT INTO settings (key, value) VALUES ('supplier_ai_last_result', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (value,),
        )
        await db.execute(
            "INSERT INTO settings (key, value) VALUES ('supplier_ai_last_run', CURRENT_TIMESTAMP) "
            "ON CONFLICT(key) DO UPDATE SET value = CURRENT_TIMESTAMP"
        )
        await db.commit()
    finally:
        await db.close()


async def get_supplier_ai_index_status() -> dict:
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT COUNT(*) AS indexed_products,
                      COUNT(DISTINCT supplier_code) AS indexed_suppliers,
                      MAX(analyzed_at) AS last_analysis
               FROM supplier_product_analysis"""
        )
        row = dict(await cursor.fetchone())
        cursor = await db.execute(
            """SELECT key, value FROM settings WHERE key IN (
                   'supplier_ai_last_run', 'supplier_ai_last_result',
                   'supplier_ai_auto_last_started_at',
                   'supplier_ai_auto_last_completed_at'
               )"""
        )
        values = {str(item["key"]): str(item["value"]) for item in await cursor.fetchall()}
        try:
            summary = json.loads(values.get("supplier_ai_last_result", "{}") or "{}")
        except (TypeError, ValueError, json.JSONDecodeError):
            summary = {}
        return {
            "indexed_products": int(row.get("indexed_products") or 0),
            "indexed_suppliers": int(row.get("indexed_suppliers") or 0),
            "last_analysis": row.get("last_analysis") or values.get("supplier_ai_last_run") or "",
            "last_result": summary if isinstance(summary, dict) else {},
            "auto_last_started_at": values.get("supplier_ai_auto_last_started_at", ""),
            "auto_last_completed_at": values.get("supplier_ai_auto_last_completed_at", ""),
        }
    finally:
        await db.close()
