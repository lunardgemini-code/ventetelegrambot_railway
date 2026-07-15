import unittest
import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from telegram.error import BadRequest

from database import models
from services.broadcast import execute_broadcast


class BroadcastTests(unittest.IsolatedAsyncioTestCase):
    async def test_invalid_html_retries_as_plain_text(self):
        bot = SimpleNamespace(
            send_message=AsyncMock(side_effect=[
                BadRequest("Can't parse entities: unsupported start tag"),
                object(),
            ]),
            send_photo=AsyncMock(),
        )
        users = [
            {"telegram_id": 1, "is_banned": 0},
            {"telegram_id": 2, "is_banned": 1},
        ]

        with patch("services.broadcast.get_all_users", AsyncMock(return_value=users)):
            sent, failed, total = await execute_broadcast(bot, "<broken>Message")

        self.assertEqual((sent, failed, total), (1, 0, 1))
        self.assertEqual(bot.send_message.await_count, 2)
        self.assertEqual(bot.send_message.await_args_list[0].kwargs["parse_mode"], "HTML")
        self.assertIsNone(bot.send_message.await_args_list[1].kwargs["parse_mode"])

    async def test_long_photo_caption_is_sent_as_photo_then_message(self):
        bot = SimpleNamespace(send_message=AsyncMock(), send_photo=AsyncMock())
        users = [{"telegram_id": 1, "is_banned": 0}]
        text = "A" * 1100

        with patch("services.broadcast.get_all_users", AsyncMock(return_value=users)):
            sent, failed, total = await execute_broadcast(
                bot,
                text,
                photo="https://example.com/photo.jpg",
            )

        self.assertEqual((sent, failed, total), (1, 0, 1))
        bot.send_photo.assert_awaited_once_with(
            chat_id=1,
            photo="https://example.com/photo.jpg",
        )
        bot.send_message.assert_awaited_once()
        self.assertEqual(bot.send_message.await_args.kwargs["text"], text)

    async def test_recipient_read_retries_stale_turso_stream(self):
        operation = AsyncMock(side_effect=[
            ValueError('Hrana: status=404 body={"error":"stream not found"}'),
            [{"telegram_id": 1}],
        ])
        with patch("database.models._get_all_users_once", operation):
            users = await models.get_all_users()

        self.assertEqual(users, [{"telegram_id": 1}])
        self.assertEqual(operation.await_count, 2)

    async def test_dashboard_broadcast_runs_as_tracked_background_job(self):
        import bot as bot_module

        telegram_bot = SimpleNamespace()
        enqueue = AsyncMock(return_value={
            "job_id": "job-1",
            "job_type": "broadcast",
            "status": "queued",
            "sent": 0,
            "failed": 0,
            "total": 3,
        })
        status = AsyncMock(return_value={
            "job_id": "job-1",
            "job_type": "broadcast",
            "status": "completed",
            "sent": 2,
            "failed": 1,
            "total": 3,
        })

        with (
            patch.object(bot_module, "tg_app", SimpleNamespace(bot=telegram_bot)),
            patch("services.background_jobs.enqueue_broadcast_job", enqueue),
            patch("services.background_jobs.get_public_background_job", status),
        ):
            queued = await bot_module.api_broadcast({"message": "Hello"})
            self.assertEqual(queued["status"], "queued")
            self.assertEqual(queued["job_id"], "job-1")
            completed = await bot_module.api_broadcast_status(queued["job_id"])

        self.assertEqual(completed["status"], "completed")
        self.assertEqual((completed["sent"], completed["failed"], completed["total"]), (2, 1, 3))
        enqueue.assert_awaited_once()
        status.assert_awaited_once_with("job-1")

    async def test_admin_broadcast_updates_status_after_handler_returns(self):
        from handlers import admin

        status_message = SimpleNamespace(
            chat_id=42,
            message_id=99,
            edit_text=AsyncMock(),
        )
        enqueue = AsyncMock(return_value={
            "job_id": "job-admin",
            "job_type": "broadcast",
            "status": "queued",
            "sent": 0,
            "failed": 0,
            "total": 4,
        })
        admin._admin_broadcast_tasks.clear()

        with patch("services.background_jobs.enqueue_broadcast_job", enqueue):
            admin._queue_admin_broadcast(
                SimpleNamespace(),
                status_message,
                "Hello",
            )
            self.assertEqual(len(admin._admin_broadcast_tasks), 1)
            await asyncio.gather(*list(admin._admin_broadcast_tasks))

        enqueue.assert_awaited_once_with(
            "Hello",
            photo=None,
            reply_markup=None,
            source="telegram_admin",
            status_chat_id=42,
            status_message_id=99,
        )
        self.assertIn("file persistante", status_message.edit_text.await_args.args[0])

    async def test_broadcast_resume_starts_after_last_checkpoint(self):
        bot = SimpleNamespace(send_message=AsyncMock(), send_photo=AsyncMock())
        users = [
            {"id": 1, "telegram_id": 101, "is_banned": 0},
            {"id": 2, "telegram_id": 102, "is_banned": 0},
            {"id": 3, "telegram_id": 103, "is_banned": 0},
        ]
        checkpoint = AsyncMock()

        with patch("services.broadcast.get_all_users", AsyncMock(return_value=users)):
            sent, failed, total = await execute_broadcast(
                bot,
                "Resume",
                start_offset=2,
                max_user_id=3,
                initial_sent=2,
                initial_failed=0,
                checkpoint=checkpoint,
            )

        self.assertEqual((sent, failed, total), (3, 0, 3))
        bot.send_message.assert_awaited_once()
        self.assertEqual(bot.send_message.await_args.kwargs["chat_id"], 103)
        checkpoint.assert_awaited_once_with(3, 0, 3, 3)


if __name__ == "__main__":
    unittest.main()
