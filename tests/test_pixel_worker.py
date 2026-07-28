import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import Bot
from services import pixel_worker


class PixelWorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_record_and_get_active_pixel_tasks(self):
        await pixel_worker.init_pixel_tasks_table()
        await pixel_worker.record_pixel_task(
            task_id=99101,
            user_id=123456,
            email="test@gmail.com",
            task_mode="extract_link_fast",
        )

        active = await pixel_worker.get_active_pixel_tasks()
        task_ids = [t["task_id"] for t in active]
        self.assertIn(99101, task_ids)

        task = next(t for t in active if t["task_id"] == 99101)
        self.assertEqual(task["email"], "test@gmail.com")
        self.assertEqual(task["status"], "pending")

        await pixel_worker.update_pixel_task_db(99101, "success", result_link="https://activate.me/abc")
        active_after = await pixel_worker.get_active_pixel_tasks()
        task_ids_after = [t["task_id"] for t in active_after]
        self.assertNotIn(99101, task_ids_after)

    async def test_pixel_task_worker_notifies_telegram(self):
        bot = MagicMock(spec=Bot)
        bot.send_message = AsyncMock()

        await pixel_worker.record_pixel_task(
            task_id=99202,
            user_id=8888,
            email="notify@gmail.com",
            task_mode="extract_link_fast",
        )

        query_resp = {
            "task": {
                "status": "success",
                "result_link": "https://pixel.wxie.de/result/99202",
            }
        }

        with patch("services.pixel_worker._request", AsyncMock(return_value=query_resp)):
            # Run one cycle of worker logic
            tasks = await pixel_worker.get_active_pixel_tasks()
            self.assertTrue(any(t["task_id"] == 99202 for t in tasks))

            provider = {"code": "pixel", "base_url": "https://pixel.wxie.de"}
            with patch("services.pixel_worker._provider_config", return_value=provider):
                # Trigger single worker pass
                worker_task = asyncio.create_task(pixel_worker.pixel_task_worker(bot, interval_seconds=0.1))
                await asyncio.sleep(0.2)
                worker_task.cancel()
                try:
                    await worker_task
                except asyncio.CancelledError:
                    pass

            bot.send_message.assert_called()
            call_kwargs = bot.send_message.call_args[1]
            self.assertEqual(call_kwargs["chat_id"], 8888)
            self.assertIn("https://pixel.wxie.de/result/99202", call_kwargs["text"])


if __name__ == "__main__":
    unittest.main()
