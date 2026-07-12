import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from handlers.start import callback_check_sub


class CallbackSafetyTests(unittest.IsolatedAsyncioTestCase):
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
