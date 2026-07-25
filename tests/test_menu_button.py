"""Tests for native Telegram blue Menu button configuration and command handlers."""

import unittest
from unittest.mock import AsyncMock, patch

from telegram import BotCommand, MenuButtonCommands

from bot import setup_telegram_bot_commands
from handlers.start import (
    game_command,
    history_command,
    products_command,
    profile_command,
    support_command,
    wallet_command,
)


class MenuButtonTests(unittest.IsolatedAsyncioTestCase):

    async def test_setup_telegram_bot_commands_registers_commands_and_menu_button(self):
        mock_bot = AsyncMock()

        await setup_telegram_bot_commands(mock_bot)

        self.assertGreaterEqual(mock_bot.set_my_commands.await_count, 1)
        mock_bot.set_chat_menu_button.assert_awaited_once()

        # Check default commands set
        first_call_args = mock_bot.set_my_commands.await_args_list[0][0][0]
        cmd_names = [cmd.command for cmd in first_call_args]
        self.assertIn("start", cmd_names)
        self.assertIn("products", cmd_names)
        self.assertIn("wallet", cmd_names)
        self.assertIn("profile", cmd_names)
        self.assertIn("history", cmd_names)
        self.assertIn("support", cmd_names)
        self.assertIn("game", cmd_names)

    async def test_menu_command_wrappers_delegate_to_respective_menus(self):
        update = AsyncMock()
        context = AsyncMock()

        with patch("handlers.products.show_products_list", AsyncMock()) as mock_show:
            await products_command(update, context)
            mock_show.assert_awaited_once_with(update, context)

        with patch("handlers.wallet.wallet_menu", AsyncMock()) as mock_wallet:
            await wallet_command(update, context)
            mock_wallet.assert_awaited_once_with(update, context)

        with patch("handlers.profile.show_profile", AsyncMock()) as mock_profile:
            await profile_command(update, context)
            mock_profile.assert_awaited_once_with(update, context)

        with patch("handlers.history.show_history", AsyncMock()) as mock_hist:
            await history_command(update, context)
            mock_hist.assert_awaited_once_with(update, context)

        with patch("handlers.support.support_menu", AsyncMock()) as mock_supp:
            await support_command(update, context)
            mock_supp.assert_awaited_once_with(update, context)

        with patch("handlers.game.show_game_menu", AsyncMock()) as mock_game:
            await game_command(update, context)
            mock_game.assert_awaited_once_with(update, context)


if __name__ == "__main__":
    unittest.main()
