"""Read-only financial consistency checks with a low-frequency scheduler."""

from __future__ import annotations

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Callable

from database.db import get_db
from database.models import get_setting, set_setting


logger = logging.getLogger(__name__)

_LATEST_SETTING_KEY = "financial_reconciliation_latest"
_reconciliation_lock: asyncio.Lock | None = None
_reconciliation_lock_loop = None


def _env_seconds(name: str, default: int, minimum: int) -> int:
    try:
        return max(minimum, int(os.environ.get(name, str(default))))
    except (TypeError, ValueError):
        return default


def _get_lock() -> asyncio.Lock:
    global _reconciliation_lock, _reconciliation_lock_loop
    loop = asyncio.get_running_loop()
    if _reconciliation_lock is None or _reconciliation_lock_loop is not loop:
        _reconciliation_lock = asyncio.Lock()
        _reconciliation_lock_loop = loop
    return _reconciliation_lock


async def _check(
    db,
    *,
    key: str,
    severity: str,
    title: str,
    count_sql: str,
    sample_sql: str,
) -> dict[str, Any]:
    count_row = await (await db.execute(count_sql)).fetchone()
    count = int(count_row["count"] if count_row else 0)
    samples = []
    if count:
        rows = await (await db.execute(sample_sql)).fetchall()
        samples = [dict(row) for row in rows]
    return {
        "key": key,
        "severity": severity,
        "title": title,
        "count": count,
        "ok": count == 0,
        "samples": samples,
    }


async def run_financial_reconciliation() -> dict[str, Any]:
    """Inspect financial invariants without changing orders, balances, or stock."""
    async with _get_lock():
        db = await get_db()
        try:
            checks = [
                await _check(
                    db,
                    key="negative_wallets",
                    severity="critical",
                    title="Wallet balances below zero",
                    count_sql=(
                        "SELECT COUNT(*) AS count FROM users "
                        "WHERE COALESCE(wallet_balance, 0) < -0.0001"
                    ),
                    sample_sql=(
                        "SELECT telegram_id, wallet_balance FROM users "
                        "WHERE COALESCE(wallet_balance, 0) < -0.0001 "
                        "ORDER BY wallet_balance ASC LIMIT 20"
                    ),
                ),
                await _check(
                    db,
                    key="stuck_paid_orders",
                    severity="warning",
                    title="Paid orders waiting for delivery for over 15 minutes",
                    count_sql=(
                        "SELECT COUNT(*) AS count FROM orders "
                        "WHERE status IN ('PROCESSING', 'PAID_PENDING_DELIVERY') "
                        "AND COALESCE(paid_at, created_at) < datetime('now', '-15 minutes')"
                    ),
                    sample_sql=(
                        "SELECT id, user_telegram_id, status, payment_method, "
                        "amount_usd, COALESCE(paid_at, created_at) AS waiting_since "
                        "FROM orders "
                        "WHERE status IN ('PROCESSING', 'PAID_PENDING_DELIVERY') "
                        "AND COALESCE(paid_at, created_at) < datetime('now', '-15 minutes') "
                        "ORDER BY waiting_since ASC LIMIT 20"
                    ),
                ),
                await _check(
                    db,
                    key="unknown_supplier_outcomes",
                    severity="warning",
                    title="Supplier purchases with an unknown outcome",
                    count_sql=(
                        "SELECT COUNT(*) AS count FROM supplier_orders "
                        "WHERE status = 'unknown'"
                    ),
                    sample_sql=(
                        "SELECT order_id, supplier_code, external_order_id, attempts, "
                        "updated_at FROM supplier_orders WHERE status = 'unknown' "
                        "ORDER BY updated_at ASC LIMIT 20"
                    ),
                ),
                await _check(
                    db,
                    key="unprofitable_supplier_orders",
                    severity="critical",
                    title="Completed supplier orders with cost at or above revenue",
                    count_sql=(
                        "SELECT COUNT(*) AS count FROM supplier_orders "
                        "WHERE status = 'completed' AND cost_usd IS NOT NULL "
                        "AND revenue_usd IS NOT NULL AND cost_usd >= revenue_usd"
                    ),
                    sample_sql=(
                        "SELECT order_id, supplier_code, cost_usd, revenue_usd, "
                        "completed_at FROM supplier_orders "
                        "WHERE status = 'completed' AND cost_usd IS NOT NULL "
                        "AND revenue_usd IS NOT NULL AND cost_usd >= revenue_usd "
                        "ORDER BY completed_at DESC LIMIT 20"
                    ),
                ),
                await _check(
                    db,
                    key="completed_without_delivery",
                    severity="critical",
                    title="Completed stock orders without persisted delivery",
                    count_sql=(
                        "SELECT COUNT(*) AS count FROM orders o "
                        "JOIN products p ON p.id = o.product_id "
                        "WHERE o.status = 'COMPLETED' "
                        "AND COALESCE(p.delivery_type, 'stock') = 'stock' "
                        "AND NOT EXISTS (SELECT 1 FROM stock_items si "
                        "                WHERE si.sold_to_order_id = o.id AND si.is_sold = 1) "
                        "AND NOT EXISTS (SELECT 1 FROM supplier_orders so "
                        "                WHERE so.order_id = o.id AND so.status = 'completed')"
                    ),
                    sample_sql=(
                        "SELECT o.id, o.user_telegram_id, o.product_id, o.payment_method, "
                        "o.amount_usd, o.created_at FROM orders o "
                        "JOIN products p ON p.id = o.product_id "
                        "WHERE o.status = 'COMPLETED' "
                        "AND COALESCE(p.delivery_type, 'stock') = 'stock' "
                        "AND NOT EXISTS (SELECT 1 FROM stock_items si "
                        "                WHERE si.sold_to_order_id = o.id AND si.is_sold = 1) "
                        "AND NOT EXISTS (SELECT 1 FROM supplier_orders so "
                        "                WHERE so.order_id = o.id AND so.status = 'completed') "
                        "ORDER BY o.created_at DESC LIMIT 20"
                    ),
                ),
                await _check(
                    db,
                    key="finished_provider_payments_unresolved",
                    severity="warning",
                    title="Finished provider payments not reflected in the order",
                    count_sql=(
                        "SELECT COUNT(*) AS count FROM nowpayments_payments np "
                        "JOIN orders o ON o.id = np.order_id "
                        "WHERE LOWER(COALESCE(np.provider_status, '')) = 'finished' "
                        "AND o.status IN ('PENDING', 'AWAITING_PAYMENT', 'CANCELLED')"
                    ),
                    sample_sql=(
                        "SELECT o.id AS order_id, np.payment_id, o.status AS order_status, "
                        "np.actually_paid, np.updated_at FROM nowpayments_payments np "
                        "JOIN orders o ON o.id = np.order_id "
                        "WHERE LOWER(COALESCE(np.provider_status, '')) = 'finished' "
                        "AND o.status IN ('PENDING', 'AWAITING_PAYMENT', 'CANCELLED') "
                        "ORDER BY np.updated_at ASC LIMIT 20"
                    ),
                ),
            ]
        finally:
            await db.close()

        critical = sum(
            check["count"] for check in checks if check["severity"] == "critical"
        )
        warnings = sum(
            check["count"] for check in checks if check["severity"] == "warning"
        )
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "status": "critical" if critical else "warning" if warnings else "healthy",
            "critical_count": critical,
            "warning_count": warnings,
            "checks": checks,
            "read_only": True,
        }
        await set_setting(
            _LATEST_SETTING_KEY,
            json.dumps(report, ensure_ascii=True, separators=(",", ":")),
        )
        return report


async def get_latest_financial_reconciliation() -> dict[str, Any] | None:
    raw = await get_setting(_LATEST_SETTING_KEY)
    if not raw:
        return None
    try:
        value = json.loads(raw)
    except (TypeError, ValueError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _runtime_is_busy(snapshot_provider: Callable[[], dict] | None) -> bool:
    if snapshot_provider is None:
        return False
    try:
        snapshot = snapshot_provider() or {}
    except Exception:
        return True
    queue = snapshot.get("queue") or {}
    database = snapshot.get("database") or {}
    event_loop = snapshot.get("event_loop") or {}
    return (
        int(queue.get("current") or 0) > 0
        or float(queue.get("p95_wait_ms") or 0) >= 500
        or int(database.get("connection_errors") or 0) > 0
        or float(database.get("p95_ms") or 0) >= 750
        or float(event_loop.get("p95_lag_ms") or 0) >= 250
    )


async def financial_reconciliation_worker(
    snapshot_provider: Callable[[], dict] | None = None,
) -> None:
    interval = _env_seconds("FINANCIAL_RECONCILE_SECONDS", 24 * 60 * 60, 60 * 60)
    retry_delay = _env_seconds("FINANCIAL_RECONCILE_BUSY_RETRY_SECONDS", 10 * 60, 60)
    initial_delay = _env_seconds("FINANCIAL_RECONCILE_INITIAL_DELAY_SECONDS", 5 * 60, 30)

    latest = await get_latest_financial_reconciliation()
    if latest and latest.get("generated_at"):
        try:
            generated = datetime.fromisoformat(
                str(latest["generated_at"]).replace("Z", "+00:00")
            )
            age = max(0.0, (datetime.now(timezone.utc) - generated).total_seconds())
            initial_delay = max(initial_delay, int(interval - age))
        except (TypeError, ValueError):
            pass

    await asyncio.sleep(initial_delay)
    while True:
        if _runtime_is_busy(snapshot_provider):
            logger.info("Deferring financial reconciliation while the bot is busy")
            await asyncio.sleep(retry_delay)
            continue
        try:
            report = await run_financial_reconciliation()
            logger.info(
                "Financial reconciliation completed: status=%s critical=%d warnings=%d",
                report["status"],
                report["critical_count"],
                report["warning_count"],
            )
            await asyncio.sleep(interval)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Financial reconciliation failed: %s", exc)
            await asyncio.sleep(retry_delay)


def reset_reconciliation_state() -> None:
    global _reconciliation_lock, _reconciliation_lock_loop
    _reconciliation_lock = None
    _reconciliation_lock_loop = None
