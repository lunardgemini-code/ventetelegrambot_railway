import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, User, Message, CallbackQuery
from utils import keyboards
from handlers import pixel_activation


class PixelActivationFlowTests(unittest.IsolatedAsyncioTestCase):
    def test_main_menu_keyboard_admin_visibility(self):
        with patch("utils.helpers.is_admin", side_effect=lambda uid: uid == 9999):
            admin_kbd = keyboards.main_menu_keyboard("fr", user_id=9999)
            user_kbd = keyboards.main_menu_keyboard("fr", user_id=1234)

            admin_callbacks = [btn.callback_data for row in admin_kbd.inline_keyboard for btn in row if btn.callback_data]
            user_callbacks = [btn.callback_data for row in user_kbd.inline_keyboard for btn in row if btn.callback_data]

            self.assertIn("pixel_activation_start", admin_callbacks)
            self.assertNotIn("pixel_activation_start", user_callbacks)

    async def test_pixel_activation_start_admin_only(self):
        update = MagicMock(spec=Update)
        update.effective_user = User(id=9999, is_bot=False, first_name="Admin")
        query = MagicMock(spec=CallbackQuery)
        query.answer = AsyncMock()
        update.callback_query = query

        context = MagicMock()
        context.user_data = {}

        with patch("handlers.pixel_activation.is_admin", return_value=True), \
             patch("handlers.pixel_activation.safe_edit_message_text", AsyncMock()) as mock_edit:
            await pixel_activation.pixel_activation_start(update, context)
            mock_edit.assert_called_once()
            args, kwargs = mock_edit.call_args
            self.assertIn("Pixel Gemini", args[1])

    async def test_receive_pixel_credentials_submits_to_pixel(self):
        update = MagicMock(spec=Update)
        update.effective_user = User(id=9999, is_bot=False, first_name="Admin")
        msg = MagicMock(spec=Message)
        msg.text = "testuser@gmail.com|pass123|SECRET2FA32CHARS"
        loading_msg = MagicMock(spec=Message)
        loading_msg.edit_text = AsyncMock()
        msg.reply_text = AsyncMock(return_value=loading_msg)
        update.message = msg

        context = MagicMock()
        context.user_data = {
            "pixel_awaiting_creds": True,
            "pixel_selected_mode": "extract_link_fast",
        }

        fake_result = {"order_id": "888", "items": []}

        with patch("handlers.pixel_activation.is_admin", return_value=True), \
             patch("handlers.pixel_activation.deduct_user_pixel_points", AsyncMock(return_value=True)), \
             patch("handlers.pixel_activation.purchase_supplier_product", AsyncMock(return_value=fake_result)) as mock_purchase:
            handled = await pixel_activation.receive_pixel_credentials(update, context)
            self.assertTrue(handled)
            mock_purchase.assert_called_once_with(
                "pixel",
                "extract_link_fast",
                1,
                buyer_info="testuser@gmail.com|pass123|SECRET2FA32CHARS",
            )
            loading_msg.edit_text.assert_called_once()
            self.assertIn("#888", loading_msg.edit_text.call_args[0][0])

    async def test_pixel_my_activations_renders_user_tasks(self):
        update = MagicMock(spec=Update)
        update.effective_user = User(id=9999, is_bot=False, first_name="Admin")
        query = MagicMock(spec=CallbackQuery)
        query.answer = AsyncMock()
        update.callback_query = query

        context = MagicMock()
        context.user_data = {}

        fake_tasks = [
            {
                "task_id": 999,
                "email": "user@gmail.com",
                "task_mode": "extract_link_fast",
                "status": "pending",
                "result_link": "",
                "error_message": "",
            }
        ]

        with patch("handlers.pixel_activation.is_admin", return_value=True), \
             patch("handlers.pixel_activation.get_user_pixel_tasks", AsyncMock(return_value=fake_tasks)), \
             patch("handlers.pixel_activation.safe_edit_message_text", AsyncMock()) as mock_edit:
            await pixel_activation.pixel_my_activations(update, context)
            mock_edit.assert_called_once()
            self.assertIn("#999", mock_edit.call_args[0][1])


if __name__ == "__main__":
    unittest.main()

