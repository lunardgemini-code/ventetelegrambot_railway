import asyncio
import os
import tempfile
import time
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
        models._RESELLER_AUTH_CACHE.clear()
        models._RESELLER_LAST_USED_TOUCH_CACHE.clear()
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

    async def test_product_price_promo_round_trips_through_database(self):
        promo_id = await models.create_promo(
            code="GEMINI47",
            discount_type="product_price",
            discount_value=0.47,
            applicable_product_ids=str(self.product_id),
        )

        promo = await models.get_promo_by_code("gemini47")

        self.assertEqual(promo["id"], promo_id)
        self.assertEqual(promo["discount_type"], "product_price")
        self.assertAlmostEqual(float(promo["discount_value"]), 0.47)
        self.assertEqual(promo["applicable_product_ids"], str(self.product_id))

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

    async def test_dashboard_user_purchase_history_is_paginated(self):
        completed = await models.create_order(
            1001, self.product_id, 5, quantity=1
        )
        self.assertTrue(await models.update_order_status(
            completed["id"], "COMPLETED", expected_statuses=("PENDING",),
            payment_method="wallet",
        ))
        pending = await models.create_order(
            1001, self.product_id, 10, quantity=2
        )

        first_page = await models.get_user_purchase_history(1001, limit=1, offset=0)
        second_page = await models.get_user_purchase_history(1001, limit=1, offset=1)
        empty_page = await models.get_user_purchase_history(1001, limit=1, offset=99)

        self.assertEqual(first_page["total"], 2)
        self.assertEqual(first_page["user"]["telegram_id"], 1001)
        self.assertEqual(first_page["orders"][0]["id"], pending["id"])
        self.assertEqual(first_page["orders"][0]["product_name"], "Test product")
        self.assertEqual(second_page["orders"][0]["id"], completed["id"])
        self.assertEqual(second_page["orders"][0]["payment_method"], "wallet")
        self.assertEqual(empty_page["total"], 2)
        self.assertEqual(empty_page["orders"], [])
        self.assertIsNone(
            await models.get_user_purchase_history(999999, limit=10, offset=0)
        )

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

    async def test_prepare_user_start_cancels_and_loads_user_atomically(self):
        order = await models.create_order(1001, self.product_id, 5, quantity=1)

        user, cancelled = await models.prepare_user_start(
            1001,
            "buyer_updated",
            "Buyer Updated",
        )
        stored_order = await models.get_order(order["id"])

        self.assertEqual(cancelled, 1)
        self.assertEqual(user["username"], "buyer_updated")
        self.assertEqual(user["first_name"], "Buyer Updated")
        self.assertEqual(stored_order["status"], "CANCELLED")

    async def test_telegram_media_cache_is_cleared_when_image_changes(self):
        await models.update_product(self.product_id, image_url="https://example.com/first.png")
        await models.cache_product_telegram_file_id(
            self.product_id,
            "https://example.com/first.png",
            "telegram-file-1",
        )
        cached = await models.get_product(self.product_id)
        self.assertEqual(cached["telegram_file_id"], "telegram-file-1")

        await models.update_product(self.product_id, image_url="https://example.com/second.png")
        updated = await models.get_product(self.product_id)
        self.assertIsNone(updated["telegram_file_id"])

    async def test_reserved_stock_prevents_every_pending_cancellation_path(self):
        order = await models.create_order(1001, self.product_id, 5, quantity=1)
        reserved = await models.reserve_stock_items_for_order(order["id"], self.product_id)
        self.assertEqual(len(reserved), 1)

        transitioned = await models.update_order_status(
            order["id"],
            "CANCELLED",
            expected_statuses=("PENDING", "AWAITING_PAYMENT"),
        )
        with self.assertRaisesRegex(ValueError, "reserved or delivered stock"):
            await models.cancel_order_if_allowed(order["id"])
        cancelled_count = await models.cancel_all_pending_orders(1001)
        stored = await models.get_order(order["id"])
        linked_stock = await models.get_stock_items_for_order(order["id"])

        self.assertFalse(transitioned)
        self.assertEqual(cancelled_count, 0)
        self.assertEqual(stored["status"], "PENDING")
        self.assertEqual(len(linked_stock), 1)

    async def test_stock_history_page_has_exact_counts_and_bounded_rows(self):
        first = await models.get_stock_items_page_for_product(self.product_id, limit=1)
        second = await models.get_stock_items_page_for_product(
            self.product_id,
            limit=1,
            offset=1,
        )

        self.assertEqual(first["total"], 2)
        self.assertEqual(first["available"], 2)
        self.assertEqual(first["sold"], 0)
        self.assertEqual(len(first["items"]), 1)
        self.assertEqual(len(second["items"]), 1)
        self.assertNotEqual(first["items"][0]["id"], second["items"][0]["id"])

    async def test_binance_transaction_claim_rejects_every_duplicate(self):
        first = await models.create_order(1001, self.product_id, 5, quantity=1)
        self.assertTrue(await models.record_used_transaction("tx-1", first["id"], 1001, 5))
        self.assertFalse(await models.record_used_transaction("tx-1", first["id"], 1001, 5))

        second = await models.create_order(1001, self.product_id, 5, quantity=1)
        self.assertFalse(await models.record_used_transaction("tx-1", second["id"], 1001, 5))

    async def test_concurrent_binance_order_claim_has_one_winner(self):
        order = await models.create_order(1001, self.product_id, 5, quantity=1)

        results = await asyncio.gather(*(
            models.claim_binance_order_payment(
                "binance-order-race",
                order["id"],
                1001,
                5,
                "442882137117253632",
            )
            for _ in range(3)
        ))

        self.assertEqual(sum(bool(result["claimed"]) for result in results), 1)
        self.assertEqual(
            sum(result["reason"] == "already_claimed" for result in results),
            2,
        )
        stored = await models.get_order(order["id"])
        self.assertEqual(stored["status"], "PAID_PENDING_DELIVERY")
        self.assertEqual(stored["payment_method"], "binance")
        self.assertEqual(stored["binance_order_id"], "442882137117253632")

        db = await get_db()
        try:
            row = await (await db.execute(
                "SELECT COUNT(*) AS cnt FROM used_binance_transactions WHERE transaction_id = ?",
                ("binance-order-race",),
            )).fetchone()
        finally:
            await db.close()
        self.assertEqual(int(row["cnt"]), 1)

    async def test_concurrent_binance_wallet_credit_happens_once(self):
        results = await asyncio.gather(*(
            models.credit_wallet_from_binance_transaction(
                "binance-wallet-race",
                1001,
                5,
                "Binance Pay: test-order",
            )
            for _ in range(3)
        ))

        self.assertEqual(sum(bool(result["credited"]) for result in results), 1)
        self.assertEqual(await models.get_wallet_balance(1001), 25.0)

        db = await get_db()
        try:
            used = await (await db.execute(
                "SELECT COUNT(*) AS cnt FROM used_binance_transactions WHERE transaction_id = ?",
                ("binance-wallet-race",),
            )).fetchone()
            credits = await (await db.execute(
                "SELECT COUNT(*) AS cnt FROM wallet_transactions WHERE tx_hash = ?",
                ("binance-wallet-race",),
            )).fetchone()
        finally:
            await db.close()
        self.assertEqual(int(used["cnt"]), 1)
        self.assertEqual(int(credits["cnt"]), 1)

    async def test_failed_binance_order_claim_does_not_consume_transaction(self):
        result = await models.claim_binance_order_payment(
            "binance-missing-order",
            999999,
            1001,
            5,
            "missing-order",
        )

        self.assertFalse(result["claimed"])
        self.assertEqual(result["reason"], "order_not_found")
        self.assertFalse(await models.is_transaction_used("binance-missing-order"))

    async def test_binance_activation_claim_is_immediately_recoverable(self):
        await models.update_product(self.product_id, delivery_type="activation")
        order = await models.create_order(1001, self.product_id, 5, quantity=1)

        result = await models.claim_binance_order_payment(
            "binance-activation",
            order["id"],
            1001,
            5,
            "activation-payment",
        )

        self.assertTrue(result["claimed"])
        self.assertEqual(result["order_status"], "AWAITING_ACTIVATION_INFO")
        self.assertEqual(
            (await models.get_order(order["id"]))["status"],
            "AWAITING_ACTIVATION_INFO",
        )

    async def test_failed_binance_wallet_credit_rolls_back_transaction_claim(self):
        with self.assertRaisesRegex(ValueError, "WALLET_USER_NOT_FOUND"):
            await models.credit_wallet_from_binance_transaction(
                "binance-missing-wallet",
                999999,
                5,
                "Binance Pay: missing-user",
            )

        self.assertFalse(await models.is_transaction_used("binance-missing-wallet"))

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

    async def test_periodic_expiration_cancels_only_stale_unpaid_orders(self):
        stale = await models.create_order(1001, self.product_id, 5, quantity=1)
        await models.get_or_create_user(1002, "recent", "Recent")
        recent = await models.create_order(1002, self.product_id, 5, quantity=1)
        db = await get_db()
        try:
            await db.execute(
                "UPDATE orders SET created_at = datetime('now', '-10 minutes') WHERE id = ?",
                (stale["id"],),
            )
            await db.commit()
        finally:
            await db.close()

        expired = await models.expire_stale_orders(timeout_seconds=300)

        self.assertEqual([row["id"] for row in expired], [stale["id"]])
        self.assertEqual((await models.get_order(stale["id"]))["status"], "CANCELLED")
        self.assertEqual((await models.get_order(recent["id"]))["status"], "PENDING")

    async def test_cancelled_nowpayment_is_removed_from_polling_queue(self):
        order = await models.create_order(1001, self.product_id, 5, quantity=1)
        attempt = await models.prepare_nowpayments_attempt(order["id"], 5)
        await models.attach_nowpayments_payment(attempt["request_key"], {
            "payment_id": "np-cancelled-poll",
            "payment_status": "waiting",
            "pay_amount": 5,
            "pay_currency": "usdtbsc",
            "pay_address": "0x1111111111111111111111111111111111111111",
        })
        db = await get_db()
        try:
            await db.execute(
                "UPDATE nowpayments_payments SET updated_at = datetime('now', '-2 minutes') WHERE payment_id = ?",
                ("np-cancelled-poll",),
            )
            await db.commit()
        finally:
            await db.close()

        self.assertEqual(
            [row["payment_id"] for row in await models.list_nowpayments_to_poll()],
            ["np-cancelled-poll"],
        )
        self.assertTrue(await models.update_order_status(
            order["id"],
            "CANCELLED",
            expected_statuses=("PENDING", "AWAITING_PAYMENT"),
        ))
        self.assertEqual(await models.list_nowpayments_to_poll(), [])

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

    async def test_conversion_funnel_deduplicates_buy_clicks_and_counts_paid_orders(self):
        await models.record_product_view(self.product_id, 1001)
        await models.record_product_buy_click(self.product_id, 1001)
        await models.record_product_buy_click(self.product_id, 1001)
        order = await models.create_order(1001, self.product_id, 5, quantity=1)
        db = await get_db()
        try:
            await db.execute(
                "UPDATE orders SET status = 'COMPLETED', paid_at = CURRENT_TIMESTAMP WHERE id = ?",
                (order["id"],),
            )
            await db.commit()
            click_count = await (await db.execute(
                "SELECT COUNT(*) AS cnt FROM product_buy_clicks WHERE product_id = ?",
                (self.product_id,),
            )).fetchone()
        finally:
            await db.close()

        funnel = await models.get_conversion_funnel(days=30)
        product = next(item for item in funnel["products"] if item["product_id"] == self.product_id)
        self.assertEqual(int(click_count["cnt"]), 1)
        self.assertEqual(product["views"], 1)
        self.assertEqual(product["buy_clicks"], 1)
        self.assertEqual(product["payments_created"], 1)
        self.assertEqual(product["payments_completed"], 1)
        self.assertEqual(product["overall_conversion_rate"], 1.0)

    async def test_conversion_funnel_excludes_events_before_exact_tracking_start(self):
        await models.record_product_view(self.product_id, 1001)
        await models.record_product_buy_click(self.product_id, 1001)
        order = await models.create_order(1001, self.product_id, 5, quantity=1)
        db = await get_db()
        try:
            await db.execute(
                "UPDATE product_views SET viewed_at = datetime('now', '-2 hours') WHERE product_id = ?",
                (self.product_id,),
            )
            await db.execute(
                "UPDATE product_buy_clicks SET clicked_at = datetime('now', '-1 hour') WHERE product_id = ?",
                (self.product_id,),
            )
            await db.execute(
                "UPDATE orders SET created_at = datetime('now', '-90 minutes') WHERE id = ?",
                (order["id"],),
            )
            await db.commit()
        finally:
            await db.close()

        funnel = await models.get_conversion_funnel(days=30)
        product = next(item for item in funnel["products"] if item["product_id"] == self.product_id)
        self.assertEqual(product["views"], 0)
        self.assertEqual(product["buy_clicks"], 1)
        self.assertEqual(product["payments_created"], 0)

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

    async def test_reseller_auth_retries_a_broken_connection(self):
        generated = await models.create_reseller_api_key(1001, "Retry test")
        models._RESELLER_LAST_USED_TOUCH_CACHE[int(generated["id"])] = time.time()
        original_get_db = models.get_db
        attempts = 0

        async def flaky_get_db():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise RuntimeError("Hrana: stream not found")
            return await original_get_db()

        with patch.object(models, "get_db", side_effect=flaky_get_db):
            reseller = await models.get_reseller_by_api_key(generated["api_key"])

        self.assertEqual(int(reseller["user_telegram_id"]), 1001)
        self.assertEqual(attempts, 2)

    async def test_reseller_auth_cache_avoids_repeated_database_reads(self):
        generated = await models.create_reseller_api_key(1001, "Cache test")
        models._RESELLER_LAST_USED_TOUCH_CACHE[int(generated["id"])] = time.time()
        first = await models.get_reseller_by_api_key(generated["api_key"])

        with patch.object(models, "get_db", side_effect=AssertionError("cache miss")):
            second = await models.get_reseller_by_api_key(generated["api_key"])

        self.assertEqual(first["id"], second["id"])

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

    async def test_dynamic_price_preview_is_idempotent_and_applies_once(self):
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
            dynamic_cooldown_hours=1,
            dynamic_sensitivity="normal",
        )

        first = (await models.recalculate_dynamic_prices(
            product_id=self.product_id, force=True, apply_automatic=False
        ))[0]
        second = (await models.recalculate_dynamic_prices(
            product_id=self.product_id, force=True, apply_automatic=False
        ))[0]
        before_apply = await models.get_product(self.product_id)
        history_before = await models.get_dynamic_price_history(self.product_id)

        self.assertEqual(first["status"], "recommended")
        self.assertEqual(second["status"], "unchanged")
        self.assertTrue(second["idempotent"])
        self.assertEqual(first["suggested_price"], second["suggested_price"])
        self.assertEqual(float(before_apply["price_usd"]), 5.0)
        self.assertEqual(len(history_before), 1)

        applied = await models.apply_dynamic_price_suggestion(self.product_id)
        applied_again = await models.apply_dynamic_price_suggestion(self.product_id)
        after_apply = await models.get_product(self.product_id)
        history_after = await models.get_dynamic_price_history(self.product_id)

        self.assertEqual(applied["status"], "applied")
        self.assertEqual(applied_again["status"], "unchanged")
        self.assertEqual(float(after_apply["price_usd"]), float(first["suggested_price"]))
        self.assertEqual(len(history_after), 1)
        self.assertEqual(int(history_after[0]["applied"]), 1)

    async def test_dynamic_price_force_does_not_compound_same_data(self):
        await self._seed_dynamic_sales(3)
        await models.update_product(
            self.product_id,
            dynamic_pricing_enabled=1,
            dynamic_pricing_mode="automatic",
            dynamic_min_price=4.0,
            dynamic_max_price=6.0,
            dynamic_target_daily_sales=0.1,
            dynamic_max_change_pct=5.0,
            dynamic_cooldown_hours=1,
            dynamic_sensitivity="aggressive",
        )
        first = (await models.recalculate_dynamic_prices(
            product_id=self.product_id, force=True
        ))[0]
        first_price = float((await models.get_product(self.product_id))["price_usd"])
        second = (await models.recalculate_dynamic_prices(
            product_id=self.product_id, force=True
        ))[0]
        second_price = float((await models.get_product(self.product_id))["price_usd"])

        self.assertEqual(first["status"], "updated")
        self.assertEqual(second["status"], "unchanged")
        self.assertEqual(first_price, second_price)

    async def test_dynamic_price_worker_applies_existing_preview_after_cooldown(self):
        await self._seed_dynamic_sales(3)
        await models.update_product(
            self.product_id,
            dynamic_pricing_enabled=1,
            dynamic_pricing_mode="automatic",
            dynamic_min_price=4.0,
            dynamic_max_price=6.0,
            dynamic_target_daily_sales=0.1,
            dynamic_max_change_pct=5.0,
            dynamic_cooldown_hours=1,
        )
        preview = (await models.recalculate_dynamic_prices(
            product_id=self.product_id, force=True, apply_automatic=False
        ))[0]
        db = await get_db()
        try:
            await db.execute(
                "UPDATE products SET dynamic_last_calculated_at = datetime('now', '-2 hours') WHERE id = ?",
                (self.product_id,),
            )
            await db.commit()
        finally:
            await db.close()
        models.clear_products_cache()

        applied = (await models.recalculate_dynamic_prices(
            product_id=self.product_id, force=False, apply_automatic=True
        ))[0]
        product = await models.get_product(self.product_id)
        history = await models.get_dynamic_price_history(self.product_id)

        self.assertEqual(applied["status"], "updated")
        self.assertTrue(applied["idempotent"])
        self.assertEqual(float(product["price_usd"]), float(preview["suggested_price"]))
        self.assertEqual(len(history), 1)
        self.assertEqual(int(history[0]["applied"]), 1)

    async def test_dynamic_price_respects_daily_cumulative_cap(self):
        await self._seed_dynamic_sales(3)
        await models.update_product(
            self.product_id,
            price_usd=5.10,
            dynamic_pricing_enabled=1,
            dynamic_pricing_mode="automatic",
            dynamic_min_price=4.0,
            dynamic_max_price=8.0,
            dynamic_target_daily_sales=0.1,
            dynamic_max_change_pct=20.0,
            dynamic_daily_cap_pct=2.0,
            dynamic_weekly_cap_pct=10.0,
            dynamic_sensitivity="aggressive",
        )
        db = await get_db()
        try:
            await db.execute(
                """INSERT INTO dynamic_price_history
                   (product_id, old_price, new_price, suggested_price, mode, applied)
                   VALUES (?, 5.0, 5.1, 5.1, 'automatic', 1)""",
                (self.product_id,),
            )
            await db.commit()
        finally:
            await db.close()

        result = (await models.recalculate_dynamic_prices(
            product_id=self.product_id, force=True
        ))[0]
        product = await models.get_product(self.product_id)

        self.assertLessEqual(float(result["suggested_price"]), 5.10)
        self.assertLessEqual(float(product["price_usd"]), 5.10)

    async def test_dynamic_price_suspends_when_stock_is_zero(self):
        await self._seed_dynamic_sales(3)
        db = await get_db()
        try:
            await db.execute("UPDATE stock_items SET is_sold = 1 WHERE product_id = ?", (self.product_id,))
            await db.commit()
        finally:
            await db.close()
        await models.update_product(
            self.product_id,
            dynamic_pricing_enabled=1,
            dynamic_pricing_mode="automatic",
            dynamic_min_price=4.0,
            dynamic_max_price=6.0,
            dynamic_target_daily_sales=0.1,
        )

        result = (await models.recalculate_dynamic_prices(
            product_id=self.product_id, force=True
        ))[0]
        product = await models.get_product(self.product_id)

        self.assertEqual(result["status"], "out_of_stock")
        self.assertEqual(float(product["price_usd"]), 5.0)

    async def test_dynamic_price_simulation_never_writes(self):
        await self._seed_dynamic_sales(3)
        await models.update_product(
            self.product_id,
            dynamic_pricing_enabled=1,
            dynamic_pricing_mode="automatic",
            dynamic_min_price=4.0,
            dynamic_max_price=6.0,
            dynamic_target_daily_sales=0.1,
        )
        before = await models.get_product(self.product_id)
        history_before = await models.get_dynamic_price_history(self.product_id)

        simulation = await models.simulate_dynamic_pricing(self.product_id, days=30)

        models.clear_products_cache()
        after = await models.get_product(self.product_id)
        history_after = await models.get_dynamic_price_history(self.product_id)
        self.assertEqual(len(simulation["points"]), 30)
        self.assertEqual(float(before["price_usd"]), float(after["price_usd"]))
        self.assertEqual(len(history_before), len(history_after))

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

    async def _finished_nowpayments_payment(self, order_id: int, payment_id: str, amount: float = 5.0):
        attempt = await models.prepare_nowpayments_attempt(order_id, amount)
        await models.attach_nowpayments_payment(attempt["request_key"], {
            "payment_id": payment_id,
            "payment_status": "waiting",
            "pay_amount": amount,
            "pay_currency": "usdtbsc",
            "pay_address": "0x1111111111111111111111111111111111111111",
            "network": "bsc",
        })
        await models.save_nowpayments_update({
            "payment_id": payment_id,
            "payment_status": "finished",
            "order_id": str(order_id),
            "pay_amount": amount,
            "actually_paid": amount,
            "pay_currency": "usdtbsc",
        })

    async def test_nowpayments_double_callback_delivers_and_counts_once(self):
        order = await models.create_order(1001, self.product_id, 5, quantity=1)
        await self._finished_nowpayments_payment(order["id"], "np-double-1")

        first, second = await asyncio.gather(
            models.finalize_nowpayments_payment("np-double-1"),
            models.finalize_nowpayments_payment("np-double-1"),
        )
        self.assertEqual(first["action"], "completed")
        self.assertEqual(second["action"], "completed")

        db = await get_db()
        try:
            saved_order = await (await db.execute(
                "SELECT status, payment_method, binance_order_id FROM orders WHERE id = ?",
                (order["id"],),
            )).fetchone()
            sold = await (await db.execute(
                "SELECT COUNT(*) AS cnt FROM stock_items WHERE sold_to_order_id = ?",
                (order["id"],),
            )).fetchone()
            user = await (await db.execute(
                "SELECT total_orders, total_spent FROM users WHERE telegram_id = 1001"
            )).fetchone()
            finance = await (await db.execute(
                "SELECT value FROM settings WHERE key = 'finance_bot_balance_bep20'"
            )).fetchone()
        finally:
            await db.close()

        self.assertEqual(saved_order["status"], "COMPLETED")
        self.assertEqual(saved_order["payment_method"], "nowpayments_bep20")
        self.assertEqual(saved_order["binance_order_id"], "np-double-1")
        self.assertEqual(int(sold["cnt"]), 1)
        self.assertEqual(int(user["total_orders"]), 1)
        self.assertAlmostEqual(float(user["total_spent"]), 5.0)
        self.assertAlmostEqual(float(finance["value"]), 5.0)

    async def test_nowpayments_underpayment_requires_review(self):
        order = await models.create_order(1001, self.product_id, 5, quantity=1)
        attempt = await models.prepare_nowpayments_attempt(order["id"], 5)
        await models.attach_nowpayments_payment(attempt["request_key"], {
            "payment_id": "np-underpaid-1",
            "payment_status": "waiting",
            "pay_amount": 5,
            "pay_currency": "usdtbsc",
            "pay_address": "0x1111111111111111111111111111111111111111",
        })
        await models.save_nowpayments_update({
            "payment_id": "np-underpaid-1",
            "payment_status": "finished",
            "order_id": str(order["id"]),
            "pay_amount": 5,
            "actually_paid": 4,
            "pay_currency": "usdtbsc",
        })

        result = await models.finalize_nowpayments_payment("np-underpaid-1")
        saved = await models.get_order(order["id"])
        self.assertEqual(result["action"], "review_required")
        self.assertNotEqual(saved["status"], "COMPLETED")
        self.assertIn("Insufficient provider amount", result["payment"]["processing_error"])

        accepted = await models.finalize_nowpayments_payment(
            "np-underpaid-1",
            allow_underpayment=True,
        )
        saved = await models.get_order(order["id"])
        self.assertEqual(accepted["action"], "completed")
        self.assertEqual(saved["status"], "COMPLETED")

    async def test_nowpayments_activation_waits_for_identifier(self):
        category_id = await models.add_category("Activation")
        product_id = await models.add_product(
            category_id=category_id,
            name="Activation product",
            description="",
            price_usd=5,
            delivery_type="activation",
        )
        order = await models.create_order(1001, product_id, 5, quantity=1)
        await self._finished_nowpayments_payment(order["id"], "np-activation-1")

        result = await models.finalize_nowpayments_payment("np-activation-1")
        saved = await models.get_order(order["id"])
        self.assertEqual(result["action"], "activation")
        self.assertEqual(saved["status"], "AWAITING_ACTIVATION_INFO")
        self.assertEqual(saved["payment_method"], "nowpayments_bep20")


if __name__ == "__main__":
    unittest.main()
