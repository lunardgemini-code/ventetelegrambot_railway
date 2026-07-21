import unittest
import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from telegram.error import BadRequest

from database import models
from services import broadcast as broadcast_service
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

    async def test_broadcast_uses_a_dedicated_telegram_transport(self):
        main_bot = SimpleNamespace(
            token="123456:TEST_TOKEN",
            send_message=AsyncMock(),
            send_photo=AsyncMock(),
        )
        dedicated_bot = SimpleNamespace(
            initialize=AsyncMock(),
            shutdown=AsyncMock(),
            send_message=AsyncMock(),
            send_photo=AsyncMock(),
        )
        users = [{"telegram_id": 1, "is_banned": 0}]

        with (
            patch("services.broadcast.get_all_users", AsyncMock(return_value=users)),
            patch(
                "services.broadcast._build_isolated_broadcast_bot",
                return_value=dedicated_bot,
            ),
        ):
            result = await execute_broadcast(main_bot, "Isolated")

        self.assertEqual(result, (1, 0, 1))
        dedicated_bot.initialize.assert_awaited_once()
        dedicated_bot.send_message.assert_awaited_once()
        dedicated_bot.shutdown.assert_awaited_once()
        main_bot.send_message.assert_not_awaited()

    async def test_dedicated_pool_is_distinct_and_hard_bounded(self):
        main_request = object()
        dedicated_request = object()
        main_bot = SimpleNamespace(
            token="123456:TEST_TOKEN",
            request=main_request,
        )
        dedicated_bot = object()

        with (
            patch.dict(
                os.environ,
                {"BROADCAST_CONNECTION_POOL_SIZE": "999"},
            ),
            patch(
                "services.broadcast.HTTPXRequest",
                return_value=dedicated_request,
            ) as request_factory,
            patch(
                "services.broadcast.Bot",
                return_value=dedicated_bot,
            ) as bot_factory,
        ):
            result = broadcast_service._build_isolated_broadcast_bot(main_bot)

        self.assertIs(result, dedicated_bot)
        self.assertIsNot(dedicated_request, main_request)
        self.assertEqual(
            request_factory.call_args.kwargs["connection_pool_size"],
            12,
        )
        self.assertIs(bot_factory.call_args.kwargs["request"], dedicated_request)

    async def test_broadcast_concurrency_is_capped_at_ten(self):
        bot = SimpleNamespace(send_message=AsyncMock(), send_photo=AsyncMock())
        users = [
            {"telegram_id": user_id, "is_banned": 0}
            for user_id in range(1, 12)
        ]
        active = 0
        peak = 0

        async def tracked_send(*_args, **_kwargs):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0)
            active -= 1
            return True

        with (
            patch("services.broadcast.get_all_users", AsyncMock(return_value=users)),
            patch("services.broadcast._send_one", side_effect=tracked_send),
            patch.dict(os.environ, {
                "BROADCAST_BATCH_SIZE": "99",
                "BROADCAST_CONNECTION_POOL_SIZE": "12",
            }),
        ):
            result = await execute_broadcast(bot, "Capped")

        self.assertEqual(result, (11, 0, 11))
        self.assertEqual(peak, 10)

    async def test_broadcast_batch_never_exceeds_dedicated_pool(self):
        bot = SimpleNamespace(send_message=AsyncMock(), send_photo=AsyncMock())
        users = [
            {"telegram_id": user_id, "is_banned": 0}
            for user_id in range(1, 7)
        ]
        active = 0
        peak = 0

        async def tracked_send(*_args, **_kwargs):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0)
            active -= 1
            return True

        with (
            patch("services.broadcast.get_all_users", AsyncMock(return_value=users)),
            patch("services.broadcast._send_one", side_effect=tracked_send),
            patch.dict(os.environ, {
                "BROADCAST_BATCH_SIZE": "10",
                "BROADCAST_CONNECTION_POOL_SIZE": "3",
            }),
        ):
            result = await execute_broadcast(bot, "Pool bounded")

        self.assertEqual(result, (6, 0, 6))
        self.assertEqual(peak, 3)

    async def test_initialization_failure_still_closes_dedicated_transport(self):
        main_bot = SimpleNamespace(token="123456:TEST_TOKEN")
        dedicated_bot = SimpleNamespace(
            initialize=AsyncMock(side_effect=RuntimeError("network failed")),
            shutdown=AsyncMock(),
        )
        users = [{"telegram_id": 1, "is_banned": 0}]

        with (
            patch("services.broadcast.get_all_users", AsyncMock(return_value=users)),
            patch(
                "services.broadcast._build_isolated_broadcast_bot",
                return_value=dedicated_bot,
            ),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "Dedicated broadcast transport initialization failed",
            ):
                await execute_broadcast(main_bot, "Initialize")

        dedicated_bot.shutdown.assert_awaited_once()

    async def test_shutdown_failure_does_not_reclassify_delivered_messages(self):
        main_bot = SimpleNamespace(token="123456:TEST_TOKEN")
        dedicated_bot = SimpleNamespace(
            initialize=AsyncMock(),
            shutdown=AsyncMock(side_effect=RuntimeError("close failed")),
            send_message=AsyncMock(),
            send_photo=AsyncMock(),
        )
        users = [{"telegram_id": 1, "is_banned": 0}]

        with (
            patch("services.broadcast.get_all_users", AsyncMock(return_value=users)),
            patch(
                "services.broadcast._build_isolated_broadcast_bot",
                return_value=dedicated_bot,
            ),
        ):
            result = await execute_broadcast(main_bot, "Delivered")

        self.assertEqual(result, (1, 0, 1))
        dedicated_bot.shutdown.assert_awaited_once()

    async def test_cancellation_closes_dedicated_transport(self):
        main_bot = SimpleNamespace(token="123456:TEST_TOKEN")
        dedicated_bot = SimpleNamespace(
            initialize=AsyncMock(),
            shutdown=AsyncMock(),
        )
        users = [{"telegram_id": 1, "is_banned": 0}]
        started = asyncio.Event()
        never = asyncio.Event()

        async def blocked_send(*_args, **_kwargs):
            started.set()
            await never.wait()
            return True

        with (
            patch("services.broadcast.get_all_users", AsyncMock(return_value=users)),
            patch(
                "services.broadcast._build_isolated_broadcast_bot",
                return_value=dedicated_bot,
            ),
            patch("services.broadcast._send_one", side_effect=blocked_send),
        ):
            task = asyncio.create_task(execute_broadcast(main_bot, "Cancel"))
            await started.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task

        dedicated_bot.shutdown.assert_awaited_once()

    async def test_completed_resume_does_not_open_telegram_transport(self):
        bot = SimpleNamespace(token="123456:TEST_TOKEN")
        users = [{"id": 1, "telegram_id": 101, "is_banned": 0}]
        with (
            patch(
                "services.broadcast.get_all_users",
                AsyncMock(return_value=users),
            ),
            patch(
                "services.broadcast._build_isolated_broadcast_bot"
            ) as build,
        ):
            result = await execute_broadcast(
                bot,
                "Already complete",
                start_offset=1,
                initial_sent=1,
            )

        self.assertEqual(result, (1, 0, 1))
        build.assert_not_called()

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
