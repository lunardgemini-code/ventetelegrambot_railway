import unittest
import sys
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from database import db as db_module
from database import models
from handlers.payment import _start_redirect


class DatabaseResilienceTests(unittest.IsolatedAsyncioTestCase):
    async def test_unchanged_user_does_not_issue_redundant_update(self):
        cursor = SimpleNamespace(fetchone=AsyncMock(return_value={
            "telegram_id": 42,
            "username": "buyer",
            "first_name": "Buyer",
            "language": "fr",
            "is_banned": 0,
        }))
        db = SimpleNamespace(
            execute=AsyncMock(return_value=cursor),
            commit=AsyncMock(),
            close=AsyncMock(),
        )
        get_db_mock = AsyncMock(return_value=db)
        with patch("database.models.get_db", get_db_mock):
            result = await models._get_or_create_user_once(42, "buyer", "Buyer")

        self.assertEqual(result["username"], "buyer")
        get_db_mock.assert_awaited_once_with(fresh=False)
        db.execute.assert_awaited_once()
        db.commit.assert_not_awaited()
        db.close.assert_awaited_once()

    async def test_get_or_create_user_retries_stale_hrana_stream(self):
        expected = {
            "telegram_id": 42,
            "username": "buyer",
            "first_name": "Buyer",
            "language": "fr",
        }
        operation = AsyncMock(side_effect=[
            ValueError('Hrana: status=404 body={"error":"stream not found"}'),
            expected,
        ])
        with patch("database.models._get_or_create_user_once", operation):
            result = await models.get_or_create_user(42, "buyer", "Buyer")

        self.assertEqual(result, expected)
        self.assertEqual(operation.await_count, 2)
        self.assertFalse(operation.await_args_list[0].kwargs["fresh_connection"])
        self.assertTrue(operation.await_args_list[1].kwargs["fresh_connection"])

    async def test_turso_connection_skips_remote_busy_timeout_and_is_reused(self):
        class FakeCursor:
            description = None

        class FakeConnection:
            def __init__(self):
                self.statements = []
                self.closed = False

            def execute(self, sql, params=None):
                self.statements.append(sql)
                return FakeCursor()

            def close(self):
                self.closed = True

        connection = FakeConnection()
        connect = Mock(return_value=connection)
        fake_libsql = SimpleNamespace(connect=connect)
        db_module._libsql_pool.clear()
        db_module._pool_lock = None

        with patch.object(db_module, "TURSO_URL", "libsql://test.turso.io"):
            with patch.object(db_module, "TURSO_TOKEN", "test-token"):
                with patch.dict(sys.modules, {"libsql_experimental": fake_libsql}):
                    first = await db_module.get_db()
                    await first.close()
                    second = await db_module.get_db()
                    await second.close()

        self.assertEqual(connect.call_count, 1)
        self.assertIn("PRAGMA foreign_keys = ON", connection.statements)
        self.assertIn("SELECT 1", connection.statements)
        self.assertFalse(any("busy_timeout" in sql for sql in connection.statements))
        db_module._libsql_pool.clear()
        db_module._pool_lock = None

    async def test_get_or_create_user_does_not_retry_business_error(self):
        operation = AsyncMock(side_effect=ValueError("invalid user data"))
        with patch("database.models._get_or_create_user_once", operation):
            with self.assertRaisesRegex(ValueError, "invalid user data"):
                await models.get_or_create_user(42, "buyer", "Buyer")

        operation.assert_awaited_once()

    async def test_nowpayments_finalization_retries_stale_hrana_stream(self):
        expected = {"action": "completed", "items": []}
        operation = AsyncMock(side_effect=[
            ValueError('Hrana: status=404 body={"error":"stream not found"}'),
            expected,
        ])
        with patch("database.models._finalize_nowpayments_payment_once", operation):
            with patch("database.models.asyncio.sleep", AsyncMock()):
                result = await models.finalize_nowpayments_payment("payment-42")

        self.assertEqual(result, expected)
        self.assertEqual(operation.await_count, 2)

    async def test_pending_order_cancellation_retries_stale_hrana_stream(self):
        operation = AsyncMock(side_effect=[
            ValueError('Hrana: status=404 body={"error":"stream not found"}'),
            1,
        ])
        with patch("database.models._cancel_all_pending_orders_once", operation):
            with patch("database.models.asyncio.sleep", AsyncMock()):
                result = await models.cancel_all_pending_orders(42)

        self.assertEqual(result, 1)
        self.assertEqual(operation.await_count, 2)

    async def test_nowpayments_status_update_retries_stale_hrana_stream(self):
        expected = {"payment_id": "payment-42", "provider_status": "finished"}
        operation = AsyncMock(side_effect=[
            ValueError('Hrana: status=404 body={"error":"stream not found"}'),
            expected,
        ])
        with patch("database.models._save_nowpayments_update_once", operation):
            with patch("database.models.asyncio.sleep", AsyncMock()):
                result = await models.save_nowpayments_update({"payment_id": "payment-42"})

        self.assertEqual(result, expected)
        self.assertEqual(operation.await_count, 2)

    async def test_nowpayments_queue_read_retries_stale_hrana_stream(self):
        expected = [{"payment_id": "payment-42"}]
        operation = AsyncMock(side_effect=[
            ValueError('Hrana: status=404 body={"error":"stream not found"}'),
            expected,
        ])
        with patch("database.models._list_nowpayments_to_poll_once", operation):
            with patch("database.models.asyncio.sleep", AsyncMock()):
                result = await models.list_nowpayments_to_poll(limit=5)

        self.assertEqual(result, expected)
        operation.assert_awaited_with(5)
        self.assertEqual(operation.await_count, 2)

    async def test_order_status_update_retries_stale_hrana_stream(self):
        operation = AsyncMock(side_effect=[
            ValueError('Hrana: status=404 body={"error":"stream not found"}'),
            True,
        ])
        with patch("database.models._update_order_status_once", operation):
            with patch("database.models.asyncio.sleep", AsyncMock()):
                result = await models.update_order_status(
                    5159,
                    "COMPLETED",
                    expected_statuses=("PENDING",),
                    payment_method="binance",
                )

        self.assertTrue(result)
        self.assertEqual(operation.await_count, 2)

    async def test_stock_reservation_retries_stale_hrana_stream(self):
        expected = [{"id": 1, "account_data": "account"}]
        operation = AsyncMock(side_effect=[
            ValueError('Hrana: status=404 body={"error":"stream not found"}'),
            expected,
        ])
        with patch("database.models._reserve_stock_items_for_order_once", operation):
            with patch("database.models.asyncio.sleep", AsyncMock()):
                result = await models.reserve_stock_items_for_order(5159, 16)

        self.assertEqual(result, expected)
        self.assertEqual(operation.await_count, 2)

    async def test_binance_transaction_record_retries_stale_hrana_stream(self):
        operation = AsyncMock(side_effect=[
            ValueError('Hrana: status=404 body={"error":"stream not found"}'),
            True,
        ])
        with patch("database.models._record_used_transaction_once", operation):
            with patch("database.models.asyncio.sleep", AsyncMock()):
                result = await models.record_used_transaction("tx-42", 5159, 42, 4.5)

        self.assertTrue(result)
        self.assertEqual(operation.await_count, 2)

    async def test_payment_start_fallback_only_ends_conversation(self):
        context = SimpleNamespace(user_data={
            "paying_order_id": 1,
            "paying_amount": 5,
            "paying_product_id": 9,
            "unrelated": "keep",
        })
        result = await _start_redirect(SimpleNamespace(), context)

        self.assertEqual(result, -1)
        self.assertEqual(context.user_data, {"unrelated": "keep"})


if __name__ == "__main__":
    unittest.main()
