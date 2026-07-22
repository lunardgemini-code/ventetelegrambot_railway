import os
import tempfile
import unittest

from database import db as db_module
from database import models
from database.audit import (
    get_order_timeline,
    insert_admin_audit_events,
    list_admin_audit_events,
)
from database.db import get_db, init_db
from services.reconciliation import (
    get_latest_financial_reconciliation,
    reset_reconciliation_state,
    run_financial_reconciliation,
)


class OperationalAuditTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_db_path = os.environ.get("DB_PATH")
        self.previous_turso_url = db_module.TURSO_URL
        os.environ["DB_PATH"] = os.path.join(self.temp_dir.name, "audit.db")
        db_module.TURSO_URL = ""
        db_module._sqlite_wal_configured = False
        models._SETTINGS_CACHE.clear()
        models.clear_products_cache()
        reset_reconciliation_state()
        await init_db()

        await models.get_or_create_user(7001, "audit-user", "Audit User")
        category_id = await models.add_category("Audit")
        self.product_id = await models.add_product(
            category_id=category_id,
            name="Audit product",
            description="",
            price_usd=1.0,
        )

    async def asyncTearDown(self):
        reset_reconciliation_state()
        models._SETTINGS_CACHE.clear()
        db_module.TURSO_URL = self.previous_turso_url
        if self.previous_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self.previous_db_path
        self.temp_dir.cleanup()

    async def test_reconciliation_is_read_only_and_persists_latest_report(self):
        order = await models.create_order(7001, self.product_id, 1.0)
        db = await get_db()
        try:
            await db.execute(
                "UPDATE users SET wallet_balance = -1 WHERE telegram_id = 7001"
            )
            await db.execute(
                "UPDATE orders SET status = 'PROCESSING', "
                "created_at = datetime('now', '-30 minutes') WHERE id = ?",
                (order["id"],),
            )
            await db.commit()
        finally:
            await db.close()

        report = await run_financial_reconciliation()
        latest = await get_latest_financial_reconciliation()

        checks = {check["key"]: check for check in report["checks"]}
        self.assertEqual(report["status"], "critical")
        self.assertEqual(checks["negative_wallets"]["count"], 1)
        self.assertEqual(checks["stuck_paid_orders"]["count"], 1)
        self.assertTrue(report["read_only"])
        self.assertEqual(latest["generated_at"], report["generated_at"])

        unchanged = await models.get_order(order["id"])
        self.assertEqual(unchanged["status"], "PROCESSING")

    async def test_order_timeline_contains_payment_and_delivery_without_secrets(self):
        await models.add_stock_items(self.product_id, ["secret-account-data"])
        order = await models.create_order(7001, self.product_id, 1.0)
        await models.reserve_stock_items_for_order(order["id"], self.product_id)
        await models.update_order_status(
            order["id"],
            "COMPLETED",
            expected_statuses=("PENDING",),
            payment_method="wallet",
        )

        timeline = await get_order_timeline(order["id"])
        event_types = {event["type"] for event in timeline["events"]}

        self.assertIn("order.created", event_types)
        self.assertIn("payment.confirmed", event_types)
        self.assertIn("stock.reserved", event_types)
        self.assertNotIn("secret-account-data", str(timeline))

    async def test_admin_audit_batch_is_idempotent(self):
        event = {
            "event_uid": "same-event",
            "method": "POST",
            "path": "/api/users/7001/wallet/topup",
            "status_code": 200,
            "duration_ms": 12.5,
            "auth_kind": "session",
            "source_hash": "abc123",
        }
        await insert_admin_audit_events([event, event])
        result = await list_admin_audit_events()

        self.assertEqual(result["total"], 1)
        self.assertEqual(result["events"][0]["path"], event["path"])


if __name__ == "__main__":
    unittest.main()
