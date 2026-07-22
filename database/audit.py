"""Low-volume operational audit and order timeline queries."""

from __future__ import annotations

from typing import Any

from database.db import get_db


async def insert_admin_audit_events(events: list[dict[str, Any]]) -> None:
    if not events:
        return
    db = await get_db(fresh=True)
    try:
        await db.executemany(
            """INSERT OR IGNORE INTO admin_audit_events
               (event_uid, method, path, status_code, duration_ms, auth_kind, source_hash)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    str(event.get("event_uid") or "")[:64],
                    str(event.get("method") or "")[:12],
                    str(event.get("path") or "")[:500],
                    int(event.get("status_code") or 0),
                    max(0.0, float(event.get("duration_ms") or 0)),
                    str(event.get("auth_kind") or "unknown")[:32],
                    str(event.get("source_hash") or "")[:64],
                )
                for event in events
            ],
        )
        await db.commit()
    finally:
        await db.close()


async def list_admin_audit_events(
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))
    db = await get_db()
    try:
        total_row = await (
            await db.execute("SELECT COUNT(*) AS count FROM admin_audit_events")
        ).fetchone()
        rows = await (
            await db.execute(
                """SELECT id, event_uid, method, path, status_code, duration_ms,
                          auth_kind, source_hash, created_at
                   FROM admin_audit_events
                   ORDER BY id DESC LIMIT ? OFFSET ?""",
                (limit, offset),
            )
        ).fetchall()
        return {
            "events": [dict(row) for row in rows],
            "total": int(total_row["count"] if total_row else 0),
        }
    finally:
        await db.close()


def _append_event(
    events: list[dict[str, Any]],
    occurred_at: Any,
    event_type: str,
    label: str,
    **details: Any,
) -> None:
    if occurred_at:
        events.append(
            {
                "occurred_at": str(occurred_at),
                "type": event_type,
                "label": label,
                "details": details,
            }
        )


async def get_order_timeline(order_id: int) -> dict[str, Any] | None:
    """Build a read-only timeline from durable order/payment/delivery timestamps."""
    db = await get_db()
    try:
        order_row = await (
            await db.execute(
                """SELECT o.id, o.user_telegram_id, o.product_id, o.amount_usd,
                          o.quantity, o.status, o.payment_method, o.binance_order_id,
                          o.created_at, o.paid_at, o.activation_requested_at,
                          o.activated_at, p.name AS product_name
                   FROM orders o
                   LEFT JOIN products p ON p.id = o.product_id
                   WHERE o.id = ?""",
                (int(order_id),),
            )
        ).fetchone()
        if not order_row:
            return None
        order = dict(order_row)
        events: list[dict[str, Any]] = []
        _append_event(
            events,
            order.get("created_at"),
            "order.created",
            "Order created",
            status=order.get("status"),
            amount_usd=order.get("amount_usd"),
            quantity=order.get("quantity"),
        )
        _append_event(
            events,
            order.get("paid_at"),
            "payment.confirmed",
            "Payment confirmed",
            method=order.get("payment_method"),
            transaction_id=order.get("binance_order_id"),
        )
        _append_event(
            events,
            order.get("activation_requested_at"),
            "activation.requested",
            "Activation identifier received",
        )
        _append_event(
            events,
            order.get("activated_at"),
            "activation.completed",
            "Activation completed",
        )

        payment_rows = await (
            await db.execute(
                """SELECT payment_id, provider_status, actually_paid, created_at,
                          updated_at, processed_at, processing_error
                   FROM nowpayments_payments WHERE order_id = ? ORDER BY id""",
                (int(order_id),),
            )
        ).fetchall()
        payment_ids: list[str] = []
        for raw_payment in payment_rows:
            payment = dict(raw_payment)
            payment_id = str(payment.get("payment_id") or "")
            if payment_id:
                payment_ids.append(payment_id)
            _append_event(
                events,
                payment.get("created_at"),
                "provider_payment.created",
                "Provider payment created",
                payment_id=payment_id,
            )
            _append_event(
                events,
                payment.get("updated_at"),
                "provider_payment.status",
                "Provider payment status updated",
                payment_id=payment_id,
                provider_status=payment.get("provider_status"),
                actually_paid=payment.get("actually_paid"),
                processing_error=payment.get("processing_error") or None,
            )
            _append_event(
                events,
                payment.get("processed_at"),
                "provider_payment.processed",
                "Provider payment processed",
                payment_id=payment_id,
            )

        supplier_row = await (
            await db.execute(
                """SELECT supplier_code, external_product_id, status, attempts,
                          cost_usd, revenue_usd, external_order_id, error,
                          created_at, updated_at, completed_at
                   FROM supplier_orders WHERE order_id = ?""",
                (int(order_id),),
            )
        ).fetchone()
        if supplier_row:
            supplier = dict(supplier_row)
            _append_event(
                events,
                supplier.get("created_at"),
                "supplier.started",
                "Supplier fulfillment started",
                supplier=supplier.get("supplier_code"),
                external_product_id=supplier.get("external_product_id"),
                cost_usd=supplier.get("cost_usd"),
                revenue_usd=supplier.get("revenue_usd"),
            )
            _append_event(
                events,
                supplier.get("updated_at"),
                "supplier.status",
                "Supplier fulfillment status updated",
                status=supplier.get("status"),
                attempts=supplier.get("attempts"),
                error=supplier.get("error") or None,
            )
            _append_event(
                events,
                supplier.get("completed_at"),
                "supplier.completed",
                "Supplier fulfillment completed",
                external_order_id=supplier.get("external_order_id"),
            )

        stock_row = await (
            await db.execute(
                """SELECT COUNT(*) AS item_count, MIN(sold_at) AS first_sold_at,
                          MAX(sold_at) AS last_sold_at
                   FROM stock_items WHERE sold_to_order_id = ? AND is_sold = 1""",
                (int(order_id),),
            )
        ).fetchone()
        if stock_row and int(stock_row["item_count"] or 0) > 0:
            _append_event(
                events,
                stock_row["last_sold_at"] or stock_row["first_sold_at"],
                "stock.reserved",
                "Stock reserved for delivery",
                item_count=int(stock_row["item_count"]),
            )

        if payment_ids:
            placeholders = ",".join("?" for _ in payment_ids)
            review_rows = await (
                await db.execute(
                    f"""SELECT payment_id, action, actor, result_action, created_at
                         FROM payment_review_actions
                         WHERE payment_kind = 'order'
                           AND payment_id IN ({placeholders})
                         ORDER BY id""",
                    payment_ids,
                )
            ).fetchall()
            for raw_review in review_rows:
                review = dict(raw_review)
                _append_event(
                    events,
                    review.get("created_at"),
                    "payment_review.action",
                    "Manual payment review action",
                    payment_id=review.get("payment_id"),
                    action=review.get("action"),
                    actor=review.get("actor"),
                    result=review.get("result_action") or None,
                )

        events.sort(key=lambda event: (event["occurred_at"], event["type"]))
        return {"order": order, "events": events}
    finally:
        await db.close()
