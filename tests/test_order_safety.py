import asyncio
import os
import tempfile
import unittest

from database import db as db_module
from database.db import get_db, init_db
from database import models


class OrderSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test.db")
        os.environ["DB_PATH"] = self.db_path
        db_module.TURSO_URL = ""
        db_module._sqlite_wal_configured = False
        models._SETTINGS_CACHE.clear()
        models._USER_LANG_CACHE.clear()
        models._USER_BANNED_CACHE.clear()
        models.clear_products_cache()
        await init_db()

        await models.get_or_create_user(1001, "buyer", "Buyer")
        db = await get_db()
        try:
            await db.execute(
                "UPDATE users SET wallet_balance = 20 WHERE telegram_id = 1001"
            )
            await db.commit()
        finally:
            await db.close()

        category_id = await models.add_category("Products")
        self.product_id = await models.add_product(
            category_id=category_id,
            name="Test product",
            description="",
            price_usd=5,
        )
        await models.add_stock_items(self.product_id, ["account-1", "account-2"])

    async def asyncTearDown(self):
        self.temp_dir.cleanup()

    async def test_wallet_double_click_debits_and_delivers_once(self):
        order = await models.create_order(1001, self.product_id, 5, quantity=1)
        results = await asyncio.gather(
            models.purchase_order_with_wallet(order["id"], 1001),
            models.purchase_order_with_wallet(order["id"], 1001),
            return_exceptions=True,
        )

        successes = [result for result in results if isinstance(result, dict)]
        failures = [result for result in results if isinstance(result, Exception)]
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)

        db = await get_db()
        try:
            user = await (await db.execute(
                "SELECT wallet_balance, total_orders, total_spent FROM users WHERE telegram_id = 1001"
            )).fetchone()
            tx_count = await (await db.execute(
                "SELECT COUNT(*) AS cnt FROM wallet_transactions WHERE description = ?",
                (f"Order #{order['id']}",),
            )).fetchone()
            sold_count = await (await db.execute(
                "SELECT COUNT(*) AS cnt FROM stock_items WHERE sold_to_order_id = ?",
                (order["id"],),
            )).fetchone()
            stored_order = await (await db.execute(
                "SELECT status FROM orders WHERE id = ?", (order["id"],)
            )).fetchone()
        finally:
            await db.close()

        self.assertAlmostEqual(float(user["wallet_balance"]), 15.0)
        self.assertEqual(int(user["total_orders"]), 1)
        self.assertAlmostEqual(float(user["total_spent"]), 5.0)
        self.assertEqual(int(tx_count["cnt"]), 1)
        self.assertEqual(int(sold_count["cnt"]), 1)
        self.assertEqual(stored_order["status"], "COMPLETED")

    async def test_concurrent_completion_counts_finance_once(self):
        order = await models.create_order(1001, self.product_id, 5, quantity=1)
        results = await asyncio.gather(
            models.update_order_status(
                order["id"], "COMPLETED", expected_statuses=("PENDING",)
            ),
            models.update_order_status(
                order["id"], "COMPLETED", expected_statuses=("PENDING",)
            ),
        )
        self.assertEqual(sum(bool(value) for value in results), 1)

        db = await get_db()
        try:
            user = await (await db.execute(
                "SELECT total_orders, total_spent FROM users WHERE telegram_id = 1001"
            )).fetchone()
            finance = await (await db.execute(
                "SELECT value FROM settings WHERE key = 'finance_bot_balance_binance'"
            )).fetchone()
        finally:
            await db.close()

        self.assertEqual(int(user["total_orders"]), 1)
        self.assertAlmostEqual(float(user["total_spent"]), 5.0)
        self.assertAlmostEqual(float(finance["value"]), 5.0)

    async def test_cancelled_order_cannot_reserve_stock(self):
        order = await models.create_order(1001, self.product_id, 5, quantity=1)
        cancelled = await models.cancel_order_if_allowed(order["id"])
        self.assertEqual(cancelled["status"], "CANCELLED")

        delivered = await models.reserve_stock_items_for_order(
            order["id"], self.product_id
        )
        self.assertIsNone(delivered)
        self.assertEqual(await models.get_stock_count(self.product_id), 2)

    async def test_crypto_transaction_retry_is_only_idempotent_for_same_order(self):
        first = await models.create_order(1001, self.product_id, 5, quantity=1)
        self.assertTrue(await models.record_used_transaction("tx-1", first["id"], 1001, 5))
        self.assertTrue(await models.record_used_transaction("tx-1", first["id"], 1001, 5))

        second = await models.create_order(1001, self.product_id, 5, quantity=1)
        self.assertFalse(await models.record_used_transaction("tx-1", second["id"], 1001, 5))

    async def test_timeout_cannot_cancel_a_completed_order(self):
        order = await models.create_order(1001, self.product_id, 5, quantity=1)
        completed = await models.update_order_status(
            order["id"], "COMPLETED", expected_statuses=("PENDING",)
        )
        cancelled = await models.update_order_status(
            order["id"],
            "CANCELLED",
            expected_statuses=("PENDING", "AWAITING_PAYMENT"),
        )
        stored = await models.get_order(order["id"])
        self.assertTrue(completed)
        self.assertFalse(cancelled)
        self.assertEqual(stored["status"], "COMPLETED")

    async def test_activation_identifier_cannot_reopen_completed_order(self):
        order = await models.create_order(1001, self.product_id, 5, quantity=1)
        await models.update_order_status(
            order["id"],
            "AWAITING_ACTIVATION_INFO",
            expected_statuses=("PENDING",),
        )
        self.assertTrue(await models.submit_activation_identifier(order["id"], "client-id"))
        self.assertTrue(await models.update_order_status(
            order["id"],
            "COMPLETED",
            expected_statuses=("AWAITING_ACTIVATION",),
        ))
        self.assertFalse(await models.submit_activation_identifier(order["id"], "new-id"))
        stored = await models.get_order(order["id"])
        self.assertEqual(stored["status"], "COMPLETED")
        self.assertEqual(stored["activation_identifier"], "client-id")

    async def test_product_views_are_deduplicated(self):
        await models.record_product_view(self.product_id, 1001)
        await models.record_product_view(self.product_id, 1001)
        db = await get_db()
        try:
            row = await (await db.execute(
                "SELECT COUNT(*) AS cnt FROM product_views WHERE product_id = ? AND user_telegram_id = ?",
                (self.product_id, 1001),
            )).fetchone()
        finally:
            await db.close()
        self.assertEqual(int(row["cnt"]), 1)

    async def test_reseller_idempotency_does_not_double_debit(self):
        first = await models.create_reseller_order(
            1001,
            self.product_id,
            quantity=1,
            idempotency_key="reseller-order-1",
        )
        second = await models.create_reseller_order(
            1001,
            self.product_id,
            quantity=1,
            idempotency_key="reseller-order-1",
        )
        self.assertFalse(first["idempotent"])
        self.assertTrue(second["idempotent"])
        self.assertEqual(first["order"]["id"], second["order"]["id"])

        db = await get_db()
        try:
            user = await (await db.execute(
                "SELECT wallet_balance, total_orders FROM users WHERE telegram_id = 1001"
            )).fetchone()
            transactions = await (await db.execute(
                "SELECT COUNT(*) AS cnt FROM wallet_transactions WHERE description LIKE 'Reseller API order #%'")
            ).fetchone()
        finally:
            await db.close()
        self.assertAlmostEqual(float(user["wallet_balance"]), 15.0)
        self.assertEqual(int(user["total_orders"]), 1)
        self.assertEqual(int(transactions["cnt"]), 1)


if __name__ == "__main__":
    unittest.main()
