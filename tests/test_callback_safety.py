import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from telegram.error import BadRequest
from telegram.constants import KeyboardButtonStyle

from handlers.profile import view_referrals_list
from handlers.products import _send_product_detail_message
from handlers.start import callback_check_sub, start_command
from utils.keyboards import main_menu_keyboard
from utils.locales import LANGUAGES, t
from utils.telegram import safe_edit_message_text


class CallbackSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def test_safe_edit_ignores_an_unchanged_message(self):
        query = SimpleNamespace(
            edit_message_text=AsyncMock(side_effect=BadRequest("Message is not modified")),
            message=SimpleNamespace(reply_text=AsyncMock()),
        )

        result = await safe_edit_message_text(query, "Same text")

        self.assertIsNone(result)
        query.message.reply_text.assert_not_awaited()

    async def test_safe_edit_falls_back_when_the_original_message_is_gone(self):
        query = SimpleNamespace(
            edit_message_text=AsyncMock(side_effect=BadRequest("Message to edit not found")),
            message=SimpleNamespace(reply_text=AsyncMock(return_value="sent")),
        )

        result = await safe_edit_message_text(query, "Fresh text", parse_mode="HTML")

        self.assertEqual(result, "sent")
        query.message.reply_text.assert_awaited_once_with(
            "Fresh text",
            parse_mode="HTML",
        )

    async def test_referrals_list_uses_database_language_lookup(self):
        query = SimpleNamespace(answer=AsyncMock(), edit_message_text=AsyncMock())
        update = SimpleNamespace(
            callback_query=query,
            effective_user=SimpleNamespace(id=1234),
        )

        with (
            patch("handlers.profile.get_user_lang", AsyncMock(return_value="en")),
            patch("database.models.get_referred_users_list", AsyncMock(return_value=[])),
        ):
            await view_referrals_list(update, SimpleNamespace())

        query.answer.assert_awaited_once_with()
        query.edit_message_text.assert_awaited_once()

    async def test_main_menu_channel_button_is_translated_and_uses_configured_channel(self):
        for language in LANGUAGES:
            with self.subTest(language=language):
                with patch("utils.keyboards.REQUIRED_CHANNEL", "@required_channel"):
                    markup = main_menu_keyboard(language)
                channel_button = next(
                    button
                    for row in markup.inline_keyboard
                    for button in row
                    if button.url == "https://t.me/required_channel"
                )
                self.assertEqual(channel_button.text, t("btn_channel", language))
                self.assertNotEqual(channel_button.text, "btn_channel")

    async def test_game_button_is_directly_below_wallet_with_custom_emoji(self):
        markup = main_menu_keyboard("en")
        wallet_button = markup.inline_keyboard[1][0]
        game_button = markup.inline_keyboard[2][0]

        self.assertEqual(wallet_button.callback_data, "menu_wallet")
        self.assertEqual(game_button.callback_data, "menu_game")
        self.assertEqual(game_button.icon_custom_emoji_id, "5375312095346704820")
        self.assertEqual(game_button.text, "Game · Who Wins?")
        self.assertEqual(game_button.style, KeyboardButtonStyle.DANGER)

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
