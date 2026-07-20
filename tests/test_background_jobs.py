import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from database import db as db_module
from database.db import init_db
from database.jobs import (
    claim_next_background_job,
    complete_background_job,
    create_background_job,
    get_background_job,
    get_performance_action_history,
    get_webhook_autoscale_settings,
    list_webhook_autoscale_decisions,
    requeue_stale_background_jobs,
    save_webhook_autoscale_decision,
    flush_performance_action_hourly,
    update_webhook_autoscale_settings,
    update_background_job_progress,
)
from services import background_jobs


class PersistentBackgroundJobTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = os.environ.get("DB_PATH")
        self.original_turso_url = db_module.TURSO_URL
        os.environ["DB_PATH"] = os.path.join(self.temp_dir.name, "jobs.db")
        db_module.TURSO_URL = ""
        db_module._sqlite_wal_configured = False
        await init_db()

    async def asyncTearDown(self):
        db_module.TURSO_URL = self.original_turso_url
        if self.original_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self.original_db_path
        self.temp_dir.cleanup()

    async def test_schema_migrations_are_versioned_and_idempotent(self):
        await init_db()
        db = await db_module.get_db()
        try:
            cursor = await db.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            )
            versions = [int(row["version"]) for row in await cursor.fetchall()]
            cursor = await db.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name IN "
                "('background_jobs', 'performance_action_hourly', "
                "'webhook_autoscale_settings', 'webhook_autoscale_decisions') ORDER BY name"
            )
            tables = [row["name"] for row in await cursor.fetchall()]
        finally:
            await db.close()

        self.assertEqual(versions, list(range(1, 13)))
        self.assertEqual(tables, [
            "background_jobs",
            "performance_action_hourly",
            "webhook_autoscale_decisions",
            "webhook_autoscale_settings",
        ])

    async def test_webhook_autoscale_settings_and_decisions_are_persistent(self):
        settings = await update_webhook_autoscale_settings(
            mode="manual",
            observe_only=False,
            min_workers=6,
            max_workers=14,
            manual_workers=11,
        )
        self.assertEqual(settings["mode"], "manual")
        self.assertEqual(int(settings["observe_only"]), 0)
        self.assertEqual(int(settings["manual_workers"]), 11)

        await save_webhook_autoscale_decision({
            "state": "PRESSURE",
            "bottleneck": "workers",
            "workers_before": 8,
            "workers_after": 10,
            "proposed_workers": 10,
            "reason": "queue pressure",
            "observe_only": False,
            "next_analysis_seconds": 15,
            "metrics": {"queue": {"p95_wait_ms": 800}},
        })
        decisions = await list_webhook_autoscale_decisions(5)
        reloaded = await get_webhook_autoscale_settings()

        self.assertEqual(reloaded["mode"], "manual")
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]["state"], "PRESSURE")
        self.assertEqual(decisions[0]["workers_after"], 10)

    async def test_interrupted_job_is_requeued_and_resumes_from_checkpoint(self):
        await create_background_job(
            "job-1",
            "broadcast",
            {"text": "Hello", "max_user_id": 50},
            progress_total=10,
        )
        claimed = await claim_next_background_job()
        self.assertEqual(claimed["status"], "running")
        self.assertEqual(claimed["attempts"], 1)

        await update_background_job_progress(
            "job-1", done=5, failed=1, total=10, cursor_value=6
        )
        db = await db_module.get_db()
        try:
            await db.execute(
                "UPDATE background_jobs SET claimed_at = datetime('now', '-10 minutes') WHERE id = ?",
                ("job-1",),
            )
            await db.commit()
        finally:
            await db.close()

        self.assertEqual(await requeue_stale_background_jobs(180), 1)
        resumed = await claim_next_background_job()
        self.assertEqual(resumed["cursor_value"], 6)
        self.assertEqual(resumed["progress_done"], 5)
        self.assertEqual(resumed["progress_failed"], 1)
        self.assertEqual(resumed["attempts"], 2)

        await complete_background_job(
            "job-1", done=9, failed=1, total=10, cursor_value=10
        )
        completed = await get_background_job("job-1")
        self.assertEqual(completed["status"], "completed")

    async def test_broadcast_worker_forwards_saved_progress(self):
        checkpoint_update = AsyncMock()
        completed_update = AsyncMock()

        async def delivery(_bot, _text, **kwargs):
            await kwargs["checkpoint"](4, 1, 5, 5)
            return 4, 1, 5

        job = {
            "id": "job-2",
            "payload": {"text": "Resume", "max_user_id": 99},
            "cursor_value": 3,
            "progress_done": 2,
            "progress_failed": 1,
        }
        with (
            patch("services.background_jobs.execute_broadcast", side_effect=delivery) as execute,
            patch("services.background_jobs.update_background_job_progress", checkpoint_update),
            patch("services.background_jobs.complete_background_job", completed_update),
        ):
            await background_jobs._run_broadcast_job(job, SimpleNamespace())

        kwargs = execute.await_args.kwargs
        self.assertEqual(kwargs["start_offset"], 3)
        self.assertEqual(kwargs["initial_sent"], 2)
        self.assertEqual(kwargs["initial_failed"], 1)
        checkpoint_update.assert_awaited_once_with(
            "job-2", done=4, failed=1, total=5, cursor_value=5
        )
        completed_update.assert_awaited_once_with(
            "job-2", done=4, failed=1, total=5, cursor_value=5
        )

    async def test_inline_keyboard_survives_serialization(self):
        markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Open", url="https://example.com")]]
        )
        payload = {"reply_markup": background_jobs._serialize_markup(markup)}
        restored = background_jobs._deserialize_markup(payload, SimpleNamespace())

        self.assertIsNotNone(restored)
        self.assertEqual(restored.inline_keyboard[0][0].text, "Open")
        self.assertEqual(restored.inline_keyboard[0][0].url, "https://example.com")

    async def test_performance_aggregates_survive_process_memory(self):
        rows = [
            {
                "bucket_hour": "2099-01-01 10:00:00",
                "action": "command:/start",
                "sample_count": 2,
                "error_count": 1,
                "total_duration_ms": 600.0,
                "max_duration_ms": 400.0,
            }
        ]
        await flush_performance_action_hourly(rows)
        await flush_performance_action_hourly(rows)

        history = await get_performance_action_history(168)
        action = next(item for item in history["actions"] if item["action"] == "command:/start")
        self.assertEqual(action["count"], 4)
        self.assertEqual(action["errors"], 2)
        self.assertEqual(action["average_ms"], 300.0)
        self.assertEqual(action["max_ms"], 400.0)


if __name__ == "__main__":
    unittest.main()
