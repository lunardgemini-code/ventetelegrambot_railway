import asyncio
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
from telegram import Bot as TelegramBot

import bot
from database import db as db_module
from services.runtime_metrics import reset_runtime_metrics_for_tests


class PerformanceMetricsTests(unittest.TestCase):
    def test_railway_deployment_uses_process_liveness_probe(self):
        config_path = Path(__file__).resolve().parents[1] / "railway.json"
        config = json.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(config["deploy"]["healthcheckPath"], "/health/live")

    def setUp(self):
        bot._webhook_samples.clear()
        bot._webhook_queue_samples.clear()
        bot._webhook_handler_error_times.clear()
        bot._webhook_deduplicated_times.clear()
        bot._webhook_action_samples.clear()
        bot._webhook_pending_hourly.clear()
        bot._webhook_recent_start_signatures.clear()
        bot._webhook_worker_activity_samples.clear()
        bot._webhook_queued_by_key.clear()
        reset_runtime_metrics_for_tests()

    def tearDown(self):
        bot._webhook_samples.clear()
        bot._webhook_queue_samples.clear()
        bot._webhook_handler_error_times.clear()
        bot._webhook_action_samples.clear()
        bot._webhook_pending_hourly.clear()
        bot._webhook_recent_start_signatures.clear()
        bot._webhook_worker_activity_samples.clear()
        bot._webhook_queued_by_key.clear()
        reset_runtime_metrics_for_tests()
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

    def test_write_queue_timeout_is_reported_as_database_bottleneck(self):
        db_metrics = {
            "operations": 5,
            "errors": 0,
            "connection_errors": 0,
            "average_ms": 50,
            "p95_ms": 100,
            "slow_operations": 0,
            "connections": {},
            "write_serialization": {
                "timeouts": 1,
                "p95_wait_ms": 800,
            },
        }
        with patch.object(bot.time, "monotonic", return_value=1000.0):
            with patch.object(db_module, "get_db_performance_snapshot", return_value=db_metrics):
                result = bot._webhook_performance_snapshot()

        self.assertEqual(result["diagnosis"]["bottleneck"], "database")

    def test_event_loop_pressure_is_reported_even_with_few_samples(self):
        from services import runtime_metrics

        bot._webhook_samples.append((999.0, 0.0, 0.0, 0.1, True))
        runtime_metrics._LOOP_LAG_SAMPLES.append((999.0, 0.5))
        db_metrics = {
            "operations": 1,
            "errors": 0,
            "connection_errors": 0,
            "average_ms": 10,
            "p95_ms": 10,
            "slow_operations": 0,
            "connections": {},
        }
        with patch.object(bot.time, "monotonic", return_value=1000.0):
            with patch.object(db_module, "get_db_performance_snapshot", return_value=db_metrics):
                result = bot._webhook_performance_snapshot()

        self.assertEqual(result["diagnosis"]["bottleneck"], "event_loop")

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

    def test_performance_snapshot_groups_latency_by_action(self):
        bot._webhook_samples.append((999.0, 0.0, 0.0, 1.2, True))
        bot._webhook_action_samples.extend([
            (999.0, "command:/start", 1.2, True),
            (999.0, "command:/start", 0.8, True),
            (999.0, "callback:prod", 0.2, True),
        ])
        db_metrics = {
            "operations": 3,
            "errors": 0,
            "connection_errors": 0,
            "average_ms": 20,
            "p95_ms": 30,
            "slow_operations": 0,
            "connections": {},
        }
        with patch.object(bot.time, "monotonic", return_value=1000.0):
            with patch.object(db_module, "get_db_performance_snapshot", return_value=db_metrics):
                result = bot._webhook_performance_snapshot()

        self.assertEqual(result["actions_5m"][0]["action"], "command:/start")
        self.assertEqual(result["actions_5m"][0]["count"], 2)
        self.assertEqual(result["actions_5m"][0]["max_ms"], 1200.0)

    def test_free_text_actions_are_classified_without_storing_user_content(self):
        def update(text):
            return SimpleNamespace(
                callback_query=None,
                effective_message=SimpleNamespace(text=text, photo=None),
            )

        self.assertEqual(bot._webhook_action_name(update("42.5")), "message:number")
        self.assertEqual(
            bot._webhook_action_name(update("0x" + "a" * 64)),
            "message:evm_tx_hash",
        )
        self.assertEqual(
            bot._webhook_action_name(update("customer.name")),
            "message:identifier",
        )
        self.assertEqual(
            bot._webhook_action_name(update("a private support message with spaces")),
            "message:short_text",
        )


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
        bot._webhook_action_samples.clear()
        bot._webhook_pending_hourly.clear()
        bot._webhook_recent_start_signatures.clear()
        bot._webhook_worker_activity_samples.clear()
        bot._webhook_queued_by_key.clear()
        reset_runtime_metrics_for_tests()

    async def test_deployment_readiness_only_opens_after_startup(self):
        original_ready = bot._service_ready
        transport = httpx.ASGITransport(app=bot.api)
        try:
            async with httpx.AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                bot._service_ready = False
                starting = await client.get("/health/ready")
                bot._service_ready = True
                ready = await client.get("/health/ready")
        finally:
            bot._service_ready = original_ready

        self.assertEqual(starting.status_code, 503)
        self.assertEqual(starting.json()["status"], "not_ready")
        self.assertEqual(ready.status_code, 200)
        self.assertEqual(ready.json()["status"], "ok")

    async def test_webhook_is_retryable_until_telegram_workers_are_ready(self):
        original_queue = bot.webhook_update_queue
        original_app = bot.tg_app
        bot.webhook_update_queue = None
        bot.tg_app = SimpleNamespace(bot=TelegramBot("123456:TEST_TOKEN"))
        transport = httpx.ASGITransport(app=bot.api)
        try:
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.post("/webhook", json={"update_id": 1})
        finally:
            bot.webhook_update_queue = original_queue
            bot.tg_app = original_app

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.headers["retry-after"], "2")
        self.assertEqual(response.json()["detail"], "Telegram workers are starting")

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
        self.assertEqual(bot._webhook_action_samples[0][1], "update:other")

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

    async def test_recently_completed_start_is_debounced(self):
        original_queue = bot.webhook_update_queue
        original_app = bot.tg_app
        bot.webhook_update_queue = asyncio.Queue()
        bot.tg_app = SimpleNamespace(bot=TelegramBot("123456:TEST_TOKEN"))
        payload = {
            "update_id": 110,
            "message": {
                "message_id": 11,
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
                queued = bot.webhook_update_queue.get_nowait()
                bot.webhook_update_queue.task_done()
                bot._webhook_enqueued_at.pop(id(queued), None)
                bot._release_webhook_dedupe(queued, completed=True)
                second = await client.post(
                    "/webhook", json={**payload, "update_id": 111}
                )

            self.assertEqual(first.status_code, 200)
            self.assertTrue(second.json().get("deduplicated"))
            self.assertEqual(bot.webhook_update_queue.qsize(), 0)
        finally:
            bot.webhook_update_queue = original_queue
            bot.tg_app = original_app

    async def test_dashboard_shell_revalidates_and_assets_are_compressed(self):
        transport = httpx.ASGITransport(app=bot.api)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            shell = await client.get("/dashboard/")
            asset = await client.get(
                "/dashboard/app.js?v=test",
                headers={"Accept-Encoding": "gzip"},
            )

        self.assertEqual(shell.status_code, 200)
        self.assertEqual(shell.headers["cache-control"], "no-cache, must-revalidate")
        self.assertEqual(asset.status_code, 200)
        self.assertIn("max-age=3600", asset.headers["cache-control"])
        self.assertEqual(asset.headers.get("content-encoding"), "gzip")
        script = (Path(__file__).resolve().parents[1] / "dashboard" / "app.js").read_text(
            encoding="utf-8"
        )
        self.assertEqual(
            script.count("apiCall('/api/performance/autoscaling', 'POST'"),
            3,
        )
        self.assertNotIn("formatDate(item.created_at)", script)

    async def test_identical_callback_is_deduplicated_before_queueing(self):
        original_queue = bot.webhook_update_queue
        original_app = bot.tg_app
        bot.webhook_update_queue = asyncio.Queue()
        bot.tg_app = SimpleNamespace(bot=TelegramBot("123456:TEST_TOKEN"))
        payload = {
            "update_id": 200,
            "callback_query": {
                "id": "callback-1",
                "from": {"id": 42, "is_bot": False, "first_name": "Buyer"},
                "chat_instance": "instance-1",
                "data": "menu_products",
                "message": {
                    "message_id": 10,
                    "date": 0,
                    "chat": {"id": 42, "type": "private"},
                    "text": "Menu",
                },
            },
        }
        second_payload = json.loads(json.dumps(payload))
        second_payload["update_id"] = 201
        second_payload["callback_query"]["id"] = "callback-2"
        transport = httpx.ASGITransport(app=bot.api)
        try:
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                first = await client.post("/webhook", json=payload)
                second = await client.post("/webhook", json=second_payload)

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

    async def test_per_user_queue_limit_contains_callback_spam(self):
        original_queue = bot.webhook_update_queue
        original_app = bot.tg_app
        original_limit = bot.WEBHOOK_USER_QUEUE_MAX
        bot.webhook_update_queue = asyncio.Queue()
        bot.tg_app = SimpleNamespace(bot=TelegramBot("123456:TEST_TOKEN"))
        bot.WEBHOOK_USER_QUEUE_MAX = 3
        transport = httpx.ASGITransport(app=bot.api)
        responses = []
        try:
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                for index in range(4):
                    responses.append(await client.post("/webhook", json={
                        "update_id": 300 + index,
                        "callback_query": {
                            "id": f"callback-spam-{index}",
                            "from": {"id": 42, "is_bot": False, "first_name": "Buyer"},
                            "chat_instance": "instance-spam",
                            "data": f"menu_product:{index}",
                            "message": {
                                "message_id": 30 + index,
                                "date": 0,
                                "chat": {"id": 42, "type": "private"},
                                "text": "Menu",
                            },
                        },
                    }))

            self.assertEqual(bot.webhook_update_queue.qsize(), 3)
            self.assertTrue(responses[-1].json().get("rate_limited"))
        finally:
            while not bot.webhook_update_queue.empty():
                queued = bot.webhook_update_queue.get_nowait()
                bot.webhook_update_queue.task_done()
                bot._webhook_enqueued_at.pop(id(queued), None)
                bot._release_webhook_dedupe(queued, completed=False)
            bot._webhook_queued_by_key.clear()
            bot.WEBHOOK_USER_QUEUE_MAX = original_limit
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
        self.assertIn("actions_5m", payload)
        self.assertEqual(len(payload["timeline_30s"]), 10)
        self.assertIn("diagnosis", payload)

    async def test_autoscaling_configuration_endpoint_updates_live_manager(self):
        original_manager = bot.webhook_worker_manager
        manager = SimpleNamespace(
            status=lambda: {
                "mode": "auto",
                "observe_only": True,
                "min_workers": 8,
                "max_workers": 20,
                "current_workers": 8,
            },
            configure=AsyncMock(return_value={
                "mode": "auto",
                "observe_only": True,
                "min_workers": 8,
                "max_workers": 12,
                "current_workers": 8,
            }),
        )
        bot.webhook_worker_manager = manager
        transport = httpx.ASGITransport(app=bot.api)
        try:
            with (
                patch("database.jobs.update_webhook_autoscale_settings", AsyncMock()),
                patch("database.jobs.list_webhook_autoscale_decisions", AsyncMock(return_value=[])),
            ):
                async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                    response = await client.post(
                        "/api/performance/autoscaling",
                        headers={"X-API-Key": bot.ADMIN_API_KEY},
                        json={
                            "mode": "auto",
                            "observe_only": True,
                            "min_workers": 8,
                            "max_workers": 12,
                        },
                    )
        finally:
            bot.webhook_worker_manager = original_manager

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["mode"], "auto")
        manager.configure.assert_awaited_once_with(
            mode="auto",
            min_workers=8,
            max_workers=12,
            target_workers=None,
            observe_only=True,
        )

    async def test_admin_validation_preserves_client_error_statuses(self):
        transport = httpx.ASGITransport(app=bot.api)
        headers = {"X-API-Key": bot.ADMIN_API_KEY}
        with patch("database.models.get_ticket", AsyncMock(return_value=None)):
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                finance = await client.post(
                    "/api/finance/adjust",
                    headers=headers,
                    json={"amount": 1, "method": "all"},
                )
                missing_ticket = await client.post(
                    "/api/tickets/999/reply",
                    headers=headers,
                    json={"reply_text": "Hello"},
                )
                invalid_payload = await client.post(
                    "/api/tickets/999/reply",
                    headers=headers,
                    json={},
                )

        self.assertEqual(finance.status_code, 400)
        self.assertEqual(missing_ticket.status_code, 404)
        self.assertEqual(invalid_payload.status_code, 422)

    async def test_stats_bundle_returns_all_statistics_sections(self):
        transport = httpx.ASGITransport(app=bot.api)
        with (
            patch.object(bot, "api_get_stats", AsyncMock(return_value={"total_users": 1})),
            patch.object(bot, "api_get_daily_stats", AsyncMock(return_value=[{"day": "2026-07-12"}])),
            patch.object(bot, "api_get_products_stats", AsyncMock(return_value=[])),
            patch.object(bot, "api_get_products_momentum", AsyncMock(return_value={"days": [], "products": []})),
            patch.object(bot, "api_get_dead_product_alerts", AsyncMock(return_value={"alerts": []})),
            patch.object(bot, "api_get_conversion_funnel", AsyncMock(return_value={"summary": {}, "products": []})),
        ):
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                response = await client.get(
                    "/api/stats/bundle?days=30",
                    headers={"X-API-Key": bot.ADMIN_API_KEY},
                )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.json()),
            {"stats", "daily", "products", "momentum", "dead_alerts", "conversion"},
        )


if __name__ == "__main__":
    unittest.main()
