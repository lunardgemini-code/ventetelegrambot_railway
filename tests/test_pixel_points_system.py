import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, Update, User
from database import models
from services import pixel_payment
from handlers import pixel_activation


import os
import tempfile
from database import db as db_module

class PixelPointsSystemTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.db_path = os.path.join(self.temp_dir.name, "test_pixel.db")
        os.environ["DB_PATH"] = self.db_path
        db_module.TURSO_URL = ""
        db_module._sqlite_wal_configured = False
        await db_module.init_db()

    async def asyncTearDown(self):
        try:
            await db_module.close_db()
        except Exception:
            pass
        self.temp_dir.cleanup()

    async def test_pixel_points_db_operations(self):
        user_id = 777123

        # Test initial points
        pts = await models.get_user_pixel_points(user_id)
        self.assertEqual(pts, 0.0)

        # Test add points
        new_pts = await models.add_user_pixel_points(user_id, 10.0, 9.5, "topup_test", "ref1")
        self.assertEqual(new_pts, 10.0)

        # Test deduct points (success)
        ok = await models.deduct_user_pixel_points(user_id, 4.0, "ref2")
        self.assertTrue(ok)
        self.assertEqual(await models.get_user_pixel_points(user_id), 6.0)

        # Test deduct points (insufficient balance)
        ok_fail = await models.deduct_user_pixel_points(user_id, 100.0, "ref3")
        self.assertFalse(ok_fail)
        self.assertEqual(await models.get_user_pixel_points(user_id), 6.0)

    async def test_pixel_point_packs_management(self):
        packs = await models.get_pixel_point_packs()
        self.assertTrue(len(packs) >= 4)

        # Add custom pack
        new_pack = await models.save_pixel_point_pack(None, 100, 70.0, 30.0, 1)
        self.assertIsNotNone(new_pack.get("id"))

        updated_packs = await models.get_pixel_point_packs()
        found = any(p["points"] == 100 for p in updated_packs)
        self.assertTrue(found)

        # Delete custom pack
        await models.delete_pixel_point_pack(new_pack["id"])
        final_packs = await models.get_pixel_point_packs()
        self.assertFalse(any(p["id"] == new_pack["id"] for p in final_packs))

    async def test_topup_via_wallet_flow(self):
        user_id = 999888
        db = await models.get_db()
        # Set up user with $20 wallet balance
        await db.execute("INSERT OR REPLACE INTO users (telegram_id, wallet_balance) VALUES (?, 20.0)", (user_id,))
        await db.commit()

        packs = await models.get_pixel_point_packs()
        pack = packs[0]

        # Topup
        res = await pixel_payment.topup_pixel_points_via_wallet(user_id, pack["id"])
        self.assertTrue(res["success"])
        self.assertEqual(res["points_added"], pack["points"])

        # Verify wallet balance deducted
        cursor = await db.execute("SELECT wallet_balance FROM users WHERE telegram_id = ?", (user_id,))
        row = await cursor.fetchone()
        self.assertAlmostEqual(float(row[0]), 20.0 - pack["price_usd"])

    async def test_insufficient_points_handler_block(self):
        update = MagicMock(spec=Update)
        update.effective_user = User(id=9999, is_bot=False, first_name="Admin")
        query = MagicMock(spec=CallbackQuery)
        query.answer = AsyncMock()
        query.data = "pixel_mode:extract_link_fast"
        update.callback_query = query

        context = MagicMock()
        context.user_data = {}

        with patch("handlers.pixel_activation.is_admin", return_value=True), \
             patch("handlers.pixel_activation.get_user_pixel_points", AsyncMock(return_value=0.0)), \
             patch("handlers.pixel_activation.safe_edit_message_text", AsyncMock()) as mock_edit:
            await pixel_activation.pixel_mode_selected(update, context)
            mock_edit.assert_called_once()
            args, _ = mock_edit.call_args
            self.assertIn("insuffisants", args[1].lower())


if __name__ == "__main__":
    unittest.main()
