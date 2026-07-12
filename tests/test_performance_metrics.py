import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from telegram import Bot as TelegramBot

import bot
from database import db as db_module


class PerformanceMetricsTests(unittest.TestCase):
    def setUp(self):
        bot._webhook_samples.clear()
        bot._webhook_queue_samples.clear()
        bot._webhook_handler_error_times.clear()
        bot._webhook_deduplicated_times.clear()

    def tearDown(self):
        bot._webhook_samples.clear()
        bot._webhook_queue_samples.clear()
        bot._webhook_handler_error_times.clear()
        db_module._DB_CONNECTION_ERROR_TIMES.clear()

    def test_recommends_more_workers_when_queue_wait_is_high(self):
        for _ in range(30):
            bot._webhook_samples.append((999.0, 0.8, 0.0, 0.1, True))
        bot._webhook_queue_samples.append((999.0, 12))
        db_metrics = {
            "operations": 100,
            "errors": 0,
            "connection_errors": 0,
            "average_ms": 50,
            "p95_ms": 100,
            "slow_operations": 0,
            "connections": {},
        }
        with patch.object(bot.time, "monotonic", return_value=1000.0):
            with patch.object(db_module, "get_db_performance_snapshot", return_value=db_metrics):
                result = bot._webhook_performance_snapshot()

        self.assertEqual(result["diagnosis"]["bottleneck"], "workers")
        self.assertGreater(result["workers"]["recommended"], bot.WEBHOOK_WORKERS)

    def test_database_errors_take_priority_over_worker_recommendation(self):
        for _ in range(30):
            bot._webhook_samples.append((999.0, 0.8, 0.0, 1.0, True))
        db_metrics = {
            "operations": 100,
            "errors": 1,
            "connection_errors": 1,
            "average_ms": 200,
            "p95_ms": 900,
            "slow_operations": 2,
            "connections": {},
        }
        with patch.object(bot.time, "monotonic", return_value=1000.0):
            with patch.object(db_module, "get_db_performance_snapshot", return_value=db_metrics):
                result = bot._webhook_performance_snapshot()

        self.assertEqual(result["diagnosis"]["bottleneck"], "database")
        self.assertEqual(result["workers"]["recommended"], bot.WEBHOOK_WORKERS)

    def test_database_error_is_reported_even_with_few_webhook_samples(self):
        bot._webhook_samples.append((999.0, 0.0, 0.0, 0.1, True))
        db_metrics = {
            "operations": 5,
            "errors": 1,
            "connection_errors": 1,
            "average_ms": 100,
            "p95_ms": 200,
            "slow_operations": 0,
            "connections": {},
        }
        with patch.object(bot.time, "monotonic", return_value=1000.0):
            with patch.object(db_module, "get_db_performance_snapshot", return_value=db_metrics):
                result = bot._webhook_performance_snapshot()

        self.assertEqual(result["diagnosis"]["bottleneck"], "database")

    def test_db_export_groups_connection_errors_without_sensitive_details(self):
        db_module._DB_CONNECTION_ERROR_TIMES.clear()
        db_module._record_db_connection_error(
            ValueError('Hrana: {"error":"stream not found: private-stream-id"}'),
            "commit",
        )
        snapshot = db_module.get_db_performance_snapshot(300)

        self.assertEqual(snapshot["connection_errors"], 1)
        self.assertEqual(snapshot["connection_error_categories"], {"stream_not_found": 1})
        self.assertEqual(snapshot["connection_error_operations"], {"commit": 1})
        self.assertNotIn("private-stream-id", str(snapshot))

    def test_unchanged_waiting_nowpayment_skips_expensive_finalization(self):
        self.assertFalse(bot._should_process_polled_nowpayment({
            "payment_id": "np-1",
            "provider_status": "waiting",
            "status_changed": False,
            "notified_at": None,
        }))
        self.assertTrue(bot._should_process_polled_nowpayment({
            "payment_id": "np-1",
            "provider_status": "finished",
            "status_changed": True,
            "notified_at": None,
        }))


class PerformanceEndpointTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        bot._webhook_active_workers = 0
        bot._webhook_peak_active_workers = 0
        bot._webhook_enqueued_at.clear()
        bot._webhook_dequeued_at.clear()
        bot._webhook_pending_by_key.clear()
        bot._webhook_active_keys.clear()
        bot._webhook_active_dedupe_signatures.clear()
        bot._webhook_dedupe_by_update.clear()
        bot._webhook_samples.clear()
        bot._webhook_queue_samples.clear()

    async def test_webhook_worker_records_queue_and_processing_latency(self):
        original_queue = bot.webhook_update_queue
        bot.webhook_update_queue = asyncio.Queue()
        bot._webhook_samples.clear()
        bot._webhook_queue_samples.clear()
        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=42),
            effective_chat=None,
            update_id=7,
        )
        bot._webhook_enqueued_at[id(update)] = bot.time.monotonic() - 0.01
        await bot.webhook_update_queue.put(update)
        application = SimpleNamespace(process_update=AsyncMock())
        worker = asyncio.create_task(bot._webhook_update_worker(application, 1))
        try:
            await asyncio.wait_for(bot.webhook_update_queue.join(), timeout=1)
        finally:
            worker.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await worker
            bot.webhook_update_queue = original_queue

        application.process_update.assert_awaited_once_with(update)
        self.assertEqual(len(bot._webhook_samples), 1)
        self.assertGreaterEqual(bot._webhook_samples[0][1], 0.0)
        self.assertGreaterEqual(bot._webhook_samples[0][2], 0.0)
        self.assertGreaterEqual(bot._webhook_samples[0][3], 0.0)

    async def test_identical_start_is_deduplicated_before_queueing(self):
        original_queue = bot.webhook_update_queue
        original_app = bot.tg_app
        bot.webhook_update_queue = asyncio.Queue()
        bot.tg_app = SimpleNamespace(bot=TelegramBot("123456:TEST_TOKEN"))
        payload = {
            "update_id": 100,
            "message": {
                "message_id": 10,
                "date": 0,
                "chat": {"id": 42, "type": "private"},
                "from": {"id": 42, "is_bot": False, "first_name": "Buyer"},
                "text": "/start",
            },
        }
        transport = httpx.ASGITransport(app=bot.api)
        try:
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                first = await client.post("/webhook", json=payload)
                second = await client.post("/webhook", json={**payload, "update_id": 101})

            self.assertEqual(first.status_code, 200)
            self.assertEqual(second.status_code, 200)
            self.assertTrue(second.json().get("deduplicated"))
            self.assertEqual(bot.webhook_update_queue.qsize(), 1)
        finally:
            while not bot.webhook_update_queue.empty():
                queued = bot.webhook_update_queue.get_nowait()
                bot.webhook_update_queue.task_done()
                bot._webhook_enqueued_at.pop(id(queued), None)
                bot._release_webhook_dedupe(queued)
            bot.webhook_update_queue = original_queue
            bot.tg_app = original_app

    async def test_one_user_backlog_does_not_occupy_multiple_workers(self):
        original_queue = bot.webhook_update_queue
        bot.webhook_update_queue = asyncio.Queue()
        release_first = asyncio.Event()
        first_started = asyncio.Event()
        second_started = asyncio.Event()
        other_user_started = asyncio.Event()
        user_42_calls = 0

        async def process(update):
            nonlocal user_42_calls
            if update.effective_user.id == 42:
                user_42_calls += 1
                if user_42_calls == 1:
                    first_started.set()
                    await release_first.wait()
                else:
                    second_started.set()
            else:
                other_user_started.set()

        updates = [
            SimpleNamespace(effective_user=SimpleNamespace(id=42), effective_chat=None, update_id=1),
            SimpleNamespace(effective_user=SimpleNamespace(id=42), effective_chat=None, update_id=2),
            SimpleNamespace(effective_user=SimpleNamespace(id=99), effective_chat=None, update_id=3),
        ]
        for update in updates:
            bot._webhook_enqueued_at[id(update)] = bot.time.monotonic()
            await bot.webhook_update_queue.put(update)

        application = SimpleNamespace(process_update=AsyncMock(side_effect=process))
        workers = [
            asyncio.create_task(bot._webhook_update_worker(application, worker_id))
            for worker_id in (1, 2)
        ]
        try:
            await asyncio.wait_for(first_started.wait(), timeout=1)
            await asyncio.wait_for(other_user_started.wait(), timeout=1)
            self.assertFalse(second_started.is_set())
            release_first.set()
            await asyncio.wait_for(bot.webhook_update_queue.join(), timeout=1)
        finally:
            for worker in workers:
                worker.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
            bot.webhook_update_queue = original_queue

        self.assertTrue(second_started.is_set())
        self.assertEqual(application.process_update.await_count, 3)
        self.assertLessEqual(bot._webhook_peak_active_workers, 2)

    async def test_performance_endpoint_requires_admin_key_and_returns_metrics(self):
        transport = httpx.ASGITransport(app=bot.api)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            denied = await client.get("/api/performance")
            allowed = await client.get(
                "/api/performance",
                headers={"X-API-Key": bot.ADMIN_API_KEY},
            )

        self.assertEqual(denied.status_code, 401)
        self.assertEqual(allowed.status_code, 200)
        payload = allowed.json()
        self.assertIn("workers", payload)
        self.assertIn("queue", payload)
        self.assertIn("database", payload)
        self.assertEqual(len(payload["timeline_30s"]), 10)
        self.assertIn("diagnosis", payload)


if __name__ == "__main__":
    unittest.main()
