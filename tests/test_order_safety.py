import asyncio
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

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

    async def test_dynamic_price_history_retries_stale_turso_stream(self):
        stale_db = AsyncMock()
        stale_db.execute.side_effect = RuntimeError(
            'Hrana: status=404 body={"error":"stream not found"}'
        )
        fresh_cursor = AsyncMock()
        fresh_cursor.fetchall.return_value = [
            {"id": 1, "product_id": self.product_id, "old_price": 5, "new_price": 5.5}
        ]
        fresh_db = AsyncMock()
        fresh_db.execute.return_value = fresh_cursor

        with patch.object(models, "get_db", side_effect=[stale_db, fresh_db]):
            history = await models.get_dynamic_price_history(self.product_id, limit=8)

        self.assertEqual(history[0]["new_price"], 5.5)
        stale_db.close.assert_awaited_once()
        fresh_db.close.assert_awaited_once()

    async def test_dynamic_price_without_data_recommends_current_price(self):
        await models.update_product(
            self.product_id,
            dynamic_pricing_enabled=1,
            dynamic_pricing_mode="automatic",
            dynamic_min_price=4.0,
            dynamic_max_price=6.0,
            dynamic_target_daily_sales=20,
            dynamic_max_change_pct=5,
            dynamic_cooldown_hours=6,
            dynamic_sensitivity="normal",
        )

        result = (await models.recalculate_dynamic_prices(
            product_id=self.product_id,
            force=True,
        ))[0]
        product = await models.get_product(self.product_id)

        self.assertEqual(result["status"], "insufficient_data")
        self.assertEqual(float(result["suggested_price"]), 5.0)
        self.assertEqual(float(product["price_usd"]), 5.0)
        self.assertEqual(float(product["dynamic_suggested_price"]), 5.0)

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

    async def test_dashboard_overview_groups_operational_work(self):
        completed = await models.create_order(1001, self.product_id, 5, quantity=1)
        self.assertTrue(await models.update_order_status(
            completed["id"], "COMPLETED", expected_statuses=("PENDING",)
        ))

        await models.get_or_create_user(1002, "pending", "Pending")
        await models.get_or_create_user(1003, "activation", "Activation")
        await models.get_or_create_user(1004, "delivery", "Delivery")
        await models.create_order(1002, self.product_id, 5, quantity=1)
        activation = await models.create_order(1003, self.product_id, 5, quantity=1)
        self.assertTrue(await models.update_order_status(
            activation["id"], "AWAITING_ACTIVATION", expected_statuses=("PENDING",)
        ))
        delivery = await models.create_order(1004, self.product_id, 5, quantity=1)
        self.assertTrue(await models.update_order_status(
            delivery["id"], "PAID_PENDING_DELIVERY", expected_statuses=("PENDING",)
        ))
        await models.create_ticket(1001, "Please help")

        overview = await models.get_dashboard_overview()
        self.assertEqual(overview["today"]["orders"], 1)
        self.assertAlmostEqual(overview["today"]["revenue"], 5.0)
        self.assertEqual(overview["actions"]["pending_payments"], 1)
        self.assertEqual(overview["actions"]["pending_activations"], 1)
        self.assertEqual(overview["actions"]["delivery_issues"], 1)
        self.assertEqual(overview["actions"]["open_tickets"], 1)
        self.assertGreaterEqual(len(overview["recent_orders"]), 4)

    async def _seed_dynamic_sales(self, count=3):
        for index in range(count):
            user_id = 2000 + index
            await models.get_or_create_user(user_id, f"buyer{index}", f"Buyer {index}")
            order = await models.create_order(user_id, self.product_id, 5, quantity=1)
            self.assertTrue(await models.update_order_status(
                order["id"], "COMPLETED", expected_statuses=("PENDING",)
            ))

    async def test_dynamic_price_automatic_increases_with_demand_but_is_capped(self):
        await self._seed_dynamic_sales(3)
        await models.update_product(
            self.product_id,
            dynamic_pricing_enabled=1,
            dynamic_pricing_mode="automatic",
            dynamic_min_price=4.0,
            dynamic_max_price=6.0,
            dynamic_base_price=5.0,
            dynamic_target_daily_sales=0.1,
            dynamic_max_change_pct=5.0,
            dynamic_cooldown_hours=6,
            dynamic_sensitivity="normal",
        )

        result = (await models.recalculate_dynamic_prices(
            product_id=self.product_id, force=True
        ))[0]
        product = await models.get_product(self.product_id)
        history = await models.get_dynamic_price_history(self.product_id)

        self.assertEqual(result["status"], "updated")
        self.assertGreater(float(product["price_usd"]), 5.0)
        self.assertLessEqual(float(product["price_usd"]), 5.25)
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["mode"], "automatic")
        self.assertEqual(await models.recalculate_dynamic_prices(
            product_id=self.product_id, force=False
        ), [])

    async def test_dynamic_price_suggestion_waits_for_manual_apply(self):
        await self._seed_dynamic_sales(3)
        await models.update_product(
            self.product_id,
            dynamic_pricing_enabled=1,
            dynamic_pricing_mode="suggestion",
            dynamic_min_price=4.0,
            dynamic_max_price=6.0,
            dynamic_base_price=5.0,
            dynamic_target_daily_sales=0.1,
            dynamic_max_change_pct=5.0,
            dynamic_cooldown_hours=6,
            dynamic_sensitivity="normal",
        )

        result = (await models.recalculate_dynamic_prices(
            product_id=self.product_id, force=True
        ))[0]
        before_apply = await models.get_product(self.product_id)
        self.assertEqual(float(before_apply["price_usd"]), 5.0)
        self.assertGreater(float(result["suggested_price"]), 5.0)

        applied = await models.apply_dynamic_price_suggestion(self.product_id)
        after_apply = await models.get_product(self.product_id)
        self.assertEqual(float(after_apply["price_usd"]), float(applied["new_price"]))
        self.assertGreater(float(after_apply["price_usd"]), 5.0)

    async def test_dynamic_price_scales_quantity_tiers(self):
        await models.set_price_tiers(self.product_id, [
            {"min_qty": 2, "max_qty": 10, "price_usd": 4.0}
        ])
        await models.update_product(
            self.product_id,
            price_usd=5.5,
            dynamic_pricing_enabled=1,
            dynamic_base_price=5.0,
            dynamic_min_price=4.0,
            dynamic_max_price=6.0,
        )
        self.assertAlmostEqual(await models.get_effective_price(self.product_id, 2), 4.4)


if __name__ == "__main__":
    unittest.main()
