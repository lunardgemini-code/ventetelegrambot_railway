"""Tests for direct quantity selection from product details."""

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from handlers import payment
from utils.keyboards import product_detail_keyboard


class QuickQuantityTests(unittest.IsolatedAsyncioTestCase):
    def test_product_keyboard_exposes_quick_and_custom_quantities(self):
        markup = product_detail_keyboard(17, "en", can_buy=True)
        callbacks = [
            button.callback_data
            for row in markup.inline_keyboard
            for button in row
            if button.callback_data
        ]

        self.assertEqual(
            callbacks[:4],
            ["buy:17:1", "buy:17:2", "buy:17:3", "buy:17:custom"],
        )
        custom_button = next(
            button
            for row in markup.inline_keyboard
            for button in row
            if button.callback_data == "buy:17:custom"
        )
        self.assertEqual(custom_button.text, "Custom")

    async def test_quick_quantity_skips_the_quantity_prompt(self):
        query = SimpleNamespace(
            data="buy:17:2",
            answer=AsyncMock(),
            message=SimpleNamespace(chat_id=9001),
        )
        update = SimpleNamespace(
            callback_query=query,
            effective_user=SimpleNamespace(id=9001),
        )
        context = SimpleNamespace(user_data={}, bot=Mock())
        product = {
            "id": 17,
            "name": "Test product",
            "emoji": "",
            "price_usd": 2.0,
            "delivery_type": "stock",
        }

        with (
            patch.object(payment, "get_user_lang", AsyncMock(return_value="en")),
            patch.object(payment, "get_product", AsyncMock(return_value=product)),
            patch.object(
                payment,
                "_get_current_purchase_stock",
                AsyncMock(return_value=8),
            ),
            patch.object(payment, "queue_product_buy_click"),
            patch.object(
                payment,
                "_process_quantity",
                AsyncMock(return_value=payment.WAITING_PAYMENT_METHOD),
            ) as process_quantity,
        ):
            state = await payment.initiate_purchase(update, context)

        self.assertEqual(state, payment.WAITING_PAYMENT_METHOD)
        process_quantity.assert_awaited_once_with(
            update,
            context,
            17,
            2,
            "en",
            is_callback=True,
        )
        self.assertEqual(context.user_data["buying_product_id"], 17)

    async def test_custom_quantity_opens_the_text_prompt(self):
        query = SimpleNamespace(
            data="buy:17:custom",
            answer=AsyncMock(),
            message=SimpleNamespace(chat_id=9001),
        )
        update = SimpleNamespace(
            callback_query=query,
            effective_user=SimpleNamespace(id=9001),
        )
        context = SimpleNamespace(user_data={}, bot=Mock())
        product = {
            "id": 17,
            "name": "Test product",
            "emoji": "",
            "price_usd": 2.0,
            "delivery_type": "stock",
        }

        with (
            patch.object(payment, "get_user_lang", AsyncMock(return_value="en")),
            patch.object(payment, "get_product", AsyncMock(return_value=product)),
            patch.object(
                payment,
                "_get_current_purchase_stock",
                AsyncMock(return_value=8),
            ),
            patch.object(payment, "queue_product_buy_click"),
            patch.object(
                payment,
                "safe_edit_message_text",
                AsyncMock(),
            ) as edit_message,
            patch.object(payment, "_process_quantity", AsyncMock()) as process_quantity,
        ):
            state = await payment.initiate_purchase(update, context)

        self.assertEqual(state, payment.WAITING_QUANTITY)
        process_quantity.assert_not_awaited()
        edit_message.assert_awaited_once()
        self.assertEqual(context.user_data["buying_product_id"], 17)


if __name__ == "__main__":
    unittest.main()
