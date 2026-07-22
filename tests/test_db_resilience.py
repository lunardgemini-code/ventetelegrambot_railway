import asyncio
import unittest
import sys
import threading
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from database import db as db_module
from database import models
from handlers.payment import _start_redirect


class _FakeCursor:
    description = None


class _FakeLibsqlConnection:
    def __init__(self):
        self.statements = []
        self.commit_count = 0
        self.rollback_count = 0
        self.closed = False

    def execute(self, sql, params=None):
        self.statements.append(sql)
        return _FakeCursor()

    def executemany(self, sql, params_list):
        self.statements.append(sql)

    def executescript(self, sql):
        self.statements.append(sql)

    def commit(self):
        self.commit_count += 1

    def rollback(self):
        self.rollback_count += 1

    def close(self):
        self.closed = True


class DatabaseResilienceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        db_module._turso_writer_lock = None
        db_module._turso_writer_lock_loop = None
        db_module._DB_WRITE_WAITERS = 0
        db_module._DB_WRITE_LOCK_SAMPLES.clear()
        db_module._turso_connect_semaphore = None
        db_module._turso_connect_semaphore_loop = None

    async def asyncTearDown(self):
        db_module._turso_writer_lock = None
        db_module._turso_writer_lock_loop = None
        db_module._DB_WRITE_WAITERS = 0
        db_module._turso_connect_semaphore = None
        db_module._turso_connect_semaphore_loop = None

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

    async def test_start_fast_path_does_not_open_write_transaction(self):
        cursor = SimpleNamespace(fetchone=AsyncMock(return_value={
            "telegram_id": 42,
            "username": "buyer",
            "first_name": "Buyer",
            "language": "fr",
            "is_banned": 0,
            "has_cancellable_order": 0,
        }))
        db = SimpleNamespace(
            execute=AsyncMock(return_value=cursor),
            commit=AsyncMock(),
            rollback=AsyncMock(),
            close=AsyncMock(),
        )
        with patch("database.models.get_db", AsyncMock(return_value=db)):
            user, cancelled = await models._prepare_user_start_once(
                42, "buyer", "Buyer"
            )

        self.assertEqual(cancelled, 0)
        self.assertNotIn("has_cancellable_order", user)
        db.execute.assert_awaited_once()
        self.assertNotIn("BEGIN IMMEDIATE", db.execute.await_args.args[0])
        db.commit.assert_not_awaited()

    async def test_stale_stock_snapshot_is_served_during_turso_failure(self):
        original_cache = models._STOCK_COUNTS_CACHE
        models._STOCK_COUNTS_CACHE = (0.0, {7: 3})
        try:
            with (
                patch("database.models.time.monotonic", return_value=1000.0),
                patch("database.models.get_db", AsyncMock(side_effect=RuntimeError("offline"))),
            ):
                result = await models.get_all_stock_counts()
        finally:
            models._STOCK_COUNTS_CACHE = original_cache

        self.assertEqual(result, {7: 3})

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
        db_module._pool_lock_loop = None

        with patch.object(db_module, "TURSO_URL", "libsql://test.turso.io"):
            with patch.object(db_module, "TURSO_TOKEN", "test-token"):
                with patch.dict(sys.modules, {"libsql": fake_libsql}):
                    first = await db_module.get_db()
                    await first.close()
                    second = await db_module.get_db()
                    await second.close()

        self.assertEqual(connect.call_count, 1)
        self.assertIn("PRAGMA foreign_keys = ON", connection.statements)
        self.assertNotIn("SELECT 1", connection.statements)
        self.assertFalse(any("busy_timeout" in sql for sql in connection.statements))
        db_module._libsql_pool.clear()
        db_module._pool_lock = None
        db_module._pool_lock_loop = None

    async def test_expired_pool_connection_closes_outside_pool_lock(self):
        connection = _FakeLibsqlConnection()
        db_module._libsql_pool.clear()
        db_module._pool_lock = None
        db_module._pool_lock_loop = None
        expired_at = time.monotonic() - 100
        db_module._libsql_pool.append((connection, expired_at, expired_at))
        lock_states = []

        async def run_call(func, *args, **kwargs):
            lock_states.append(db_module.get_pool_lock().locked())
            return func()

        with patch("database.db._run_turso_call", side_effect=run_call):
            selected, created_at, returned_at = await db_module._take_pooled_turso_connection()

        self.assertIsNone(selected)
        self.assertIsNone(created_at)
        self.assertIsNone(returned_at)
        self.assertEqual(lock_states, [False])
        self.assertTrue(connection.closed)

    async def test_turso_connection_creation_has_bounded_concurrency(self):
        active = 0
        peak = 0
        state_lock = threading.Lock()

        def connect(*_args, **_kwargs):
            nonlocal active, peak
            with state_lock:
                active += 1
                peak = max(peak, active)
            try:
                time.sleep(0.05)
                return _FakeLibsqlConnection()
            finally:
                with state_lock:
                    active -= 1

        fake_libsql = SimpleNamespace(connect=connect)
        db_module._libsql_pool.clear()
        db_module._turso_connect_semaphore = None
        db_module._turso_connect_semaphore_loop = None
        with (
            patch.object(db_module, "TURSO_URL", "libsql://test.turso.io"),
            patch.object(db_module, "TURSO_TOKEN", "test-token"),
            patch.object(db_module, "_TURSO_CONNECT_CONCURRENCY", 2),
            patch.dict(sys.modules, {"libsql": fake_libsql}),
        ):
            connections = await asyncio.gather(*(
                db_module.get_db(fresh=True) for _ in range(8)
            ))
            await asyncio.gather(*(connection.close() for connection in connections))

        self.assertLessEqual(peak, 2)
        self.assertGreaterEqual(peak, 1)

    async def test_turso_writes_are_serialized_before_reaching_the_sdk(self):
        first_connection = _FakeLibsqlConnection()
        second_connection = _FakeLibsqlConnection()
        first = db_module._PooledAsyncDB(first_connection, return_to_pool=False)
        second = db_module._PooledAsyncDB(second_connection, return_to_pool=False)

        await first.execute("UPDATE users SET first_name = ? WHERE id = ?", ("A", 1))
        second_write = asyncio.create_task(
            second.execute("UPDATE users SET first_name = ? WHERE id = ?", ("B", 2))
        )
        await asyncio.sleep(0.05)

        self.assertEqual(len(first_connection.statements), 1)
        self.assertEqual(second_connection.statements, [])
        self.assertFalse(second_write.done())

        await first.commit()
        await asyncio.wait_for(second_write, timeout=1)
        self.assertEqual(len(second_connection.statements), 1)

        await second.rollback()
        await first.close()
        await second.close()

    async def test_turso_read_is_not_blocked_by_an_active_writer(self):
        writer_connection = _FakeLibsqlConnection()
        reader_connection = _FakeLibsqlConnection()
        writer = db_module._PooledAsyncDB(writer_connection, return_to_pool=False)
        reader = db_module._PooledAsyncDB(reader_connection, return_to_pool=False)

        await writer.execute("BEGIN IMMEDIATE")
        await asyncio.wait_for(reader.execute("SELECT 1"), timeout=1)

        self.assertEqual(reader_connection.statements, ["SELECT 1"])
        await writer.rollback()
        await writer.close()
        await reader.close()

    async def test_uncommitted_write_is_rolled_back_and_unlocks_on_close(self):
        connection = _FakeLibsqlConnection()
        db = db_module._PooledAsyncDB(connection, return_to_pool=False)

        await db.execute("INSERT INTO users (telegram_id) VALUES (?)", (42,))
        self.assertTrue(db_module.get_turso_writer_lock().locked())

        await db.close()

        self.assertEqual(connection.rollback_count, 1)
        self.assertTrue(connection.closed)
        self.assertFalse(db_module.get_turso_writer_lock().locked())

    async def test_turso_write_queue_timeout_is_bounded(self):
        first = db_module._PooledAsyncDB(
            _FakeLibsqlConnection(), return_to_pool=False
        )
        second = db_module._PooledAsyncDB(
            _FakeLibsqlConnection(), return_to_pool=False
        )
        await first.execute("BEGIN IMMEDIATE")

        with patch.object(db_module, "_TURSO_WRITE_LOCK_TIMEOUT_SECONDS", 0.02):
            with self.assertRaisesRegex(TimeoutError, "Turso write queue"):
                await second.execute("BEGIN IMMEDIATE")

        snapshot = db_module.get_db_performance_snapshot()
        self.assertEqual(snapshot["write_serialization"]["timeouts"], 1)
        await first.rollback()
        await first.close()
        await second.close()

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
        self.assertTrue(operation.await_args_list[0].kwargs["fresh_connection"])
        self.assertTrue(operation.await_args_list[1].kwargs["fresh_connection"])

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
        self.assertTrue(operation.await_args_list[0].kwargs["fresh_connection"])
        self.assertTrue(operation.await_args_list[1].kwargs["fresh_connection"])

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
        self.assertTrue(operation.await_args_list[0].kwargs["fresh_connection"])
        self.assertTrue(operation.await_args_list[1].kwargs["fresh_connection"])

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
        self.assertTrue(operation.await_args_list[0].kwargs["fresh_connection"])
        self.assertTrue(operation.await_args_list[1].kwargs["fresh_connection"])

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
