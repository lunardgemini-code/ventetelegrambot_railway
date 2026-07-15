import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from telegram.ext import ConversationHandler

from handlers import payment


class ActivationHandlerTests(unittest.IsolatedAsyncioTestCase):
    async def test_unrelated_text_does_not_read_user_language(self):
        update = SimpleNamespace(
            message=SimpleNamespace(text="hello"),
            effective_user=SimpleNamespace(id=42),
        )
        context = SimpleNamespace(user_data={})

        with (
            patch.object(
                payment,
                "get_pending_activation_order_for_user",
                AsyncMock(return_value=None),
            ) as pending_order,
            patch.object(payment, "get_user_lang", AsyncMock()) as get_language,
        ):
            result = await payment.receive_activation_identifier(update, context)

        self.assertEqual(result, ConversationHandler.END)
        pending_order.assert_awaited_once_with(42)
        get_language.assert_not_awaited()

    async def test_short_unrelated_text_avoids_database_reads(self):
        update = SimpleNamespace(
            message=SimpleNamespace(text="x"),
            effective_user=SimpleNamespace(id=42),
        )
        context = SimpleNamespace(user_data={})

        with (
            patch.object(
                payment,
                "get_pending_activation_order_for_user",
                AsyncMock(),
            ) as pending_order,
            patch.object(payment, "get_user_lang", AsyncMock()) as get_language,
        ):
            result = await payment.receive_activation_identifier(update, context)

        self.assertEqual(result, ConversationHandler.END)
        pending_order.assert_not_awaited()
        get_language.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
