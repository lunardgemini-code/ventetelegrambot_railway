import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from handlers.products import _send_product_detail_message
from handlers.start import callback_check_sub, start_command


class CallbackSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_start_sends_persistent_reply_keyboard_only_once_per_session(self):
        message = SimpleNamespace(reply_text=AsyncMock())
        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=1234, username="buyer", first_name="Buyer"),
            message=message,
        )
        context = SimpleNamespace(args=[], user_data={})
        with (
            patch("handlers.start.prepare_user_start", AsyncMock(return_value=({"language": "en"}, 0))),
            patch("handlers.start.is_user_banned", AsyncMock(return_value=False)),
        ):
            await start_command(update, context)
            await start_command(update, context)

        self.assertEqual(message.reply_text.await_count, 3)
        self.assertTrue(context.user_data["_reply_menu_sent"])

    async def test_product_photo_prefers_cached_telegram_file_id(self):
        send_photo = AsyncMock(return_value=SimpleNamespace(photo=[]))
        context = SimpleNamespace(bot=SimpleNamespace(
            send_photo=send_photo,
            send_message=AsyncMock(),
        ))

        await _send_product_detail_message(
            context,
            1234,
            "Product",
            None,
            "https://example.com/product.png",
            telegram_file_id="cached-file-id",
            product_id=1,
        )

        self.assertEqual(send_photo.await_args.kwargs["photo"], "cached-file-id")

    async def test_subscription_callback_is_answered_once_before_network_check(self):
        events = []
        query = SimpleNamespace(
            from_user=SimpleNamespace(id=1234, username="buyer", first_name="Buyer"),
            answer=AsyncMock(side_effect=lambda *args, **kwargs: events.append("answer")),
            message=SimpleNamespace(
                delete=AsyncMock(),
                reply_text=AsyncMock(),
            ),
        )
        bot = SimpleNamespace(
            get_chat_member=AsyncMock(
                side_effect=lambda *args, **kwargs: (
                    events.append("membership")
                    or SimpleNamespace(status="member")
                )
            )
        )
        update = SimpleNamespace(callback_query=query)
        context = SimpleNamespace(bot=bot, user_data={})

        with (
            patch("config.REQUIRED_CHANNEL", "@required"),
            patch(
                "handlers.start.get_or_create_user",
                AsyncMock(return_value={"language": "fr"}),
            ),
        ):
            await callback_check_sub(update, context)

        self.assertEqual(events[:2], ["answer", "membership"])
        query.answer.assert_awaited_once_with()
        query.message.delete.assert_awaited_once_with()
        self.assertEqual(query.message.reply_text.await_count, 2)


if __name__ == "__main__":
    unittest.main()
