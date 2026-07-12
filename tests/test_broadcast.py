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
        delivery = AsyncMock(return_value=(2, 1, 3))
        bot_module._broadcast_jobs.clear()
        bot_module._broadcast_tasks.clear()

        with (
            patch.object(bot_module, "tg_app", SimpleNamespace(bot=telegram_bot)),
            patch("services.broadcast.execute_broadcast", delivery),
        ):
            queued = await bot_module.api_broadcast({"message": "Hello"})
            self.assertEqual(queued["status"], "queued")
            self.assertTrue(queued["job_id"])
            await asyncio.gather(*list(bot_module._broadcast_tasks))
            completed = await bot_module.api_broadcast_status(queued["job_id"])

        self.assertEqual(completed["status"], "completed")
        self.assertEqual((completed["sent"], completed["failed"], completed["total"]), (2, 1, 3))
        delivery.assert_awaited_once()


if __name__ == "__main__":
    unittest.main()
