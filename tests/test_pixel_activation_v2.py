import os
import tempfile
import unittest

from cryptography.fernet import Fernet
from telegram.constants import KeyboardButtonStyle

from database import db as db_module
from database import models
from database.db import get_db, init_db
from handlers.pixel_activation import _main_markup, parse_pixel_credentials_message
from utils.keyboards import main_menu_keyboard
from utils.locales import t


PIXEL_2FA_SECRET = "JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"


class PixelActivationV2Tests(unittest.IsolatedAsyncioTestCase):
    def test_activation_menu_has_clear_turnaround_labels_and_safe_styles(self):
        for lang in ("en", "fr", "ar", "zh", "vi", "ru"):
            self.assertNotEqual(t("pixel_mode_fast_button", lang), "pixel_mode_fast_button")
            self.assertNotEqual(t("pixel_mode_normal_button", lang), "pixel_mode_normal_button")

        buttons = [row[0] for row in _main_markup("en").inline_keyboard]
        self.assertEqual(buttons[0].style, KeyboardButtonStyle.PRIMARY)
        self.assertIsNone(buttons[1].style)
        self.assertEqual(buttons[2].style, KeyboardButtonStyle.SUCCESS)
        self.assertTrue(buttons[0].text.startswith("🟢"))
        self.assertIn("min-h", buttons[0].text)
        self.assertIn("24 h", buttons[1].text)
        self.assertIn("email | password | 32-character 2FA secret", t("pixel_credentials_prompt", "en"))

        main_menu = main_menu_keyboard("en", include_pixel=True)
        pixel_button = main_menu.inline_keyboard[1][0]
        self.assertEqual(pixel_button.callback_data, "pixel:menu")
        self.assertEqual(pixel_button.style, KeyboardButtonStyle.PRIMARY)

    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_db_path = os.environ.get("DB_PATH")
        self.previous_key = os.environ.get("CREDENTIAL_ENCRYPTION_KEY")
        self.previous_keys = os.environ.pop("CREDENTIAL_ENCRYPTION_KEYS", None)
        self.previous_turso_url = db_module.TURSO_URL
        os.environ["DB_PATH"] = os.path.join(self.temp_dir.name, "pixel-v2.db")
        os.environ["CREDENTIAL_ENCRYPTION_KEY"] = Fernet.generate_key().decode("ascii")
        db_module.TURSO_URL = ""
        db_module._sqlite_wal_configured = False
        await init_db()
        await models.get_or_create_user(901001, "pixel_test", "Pixel Trace")
        db = await get_db()
        try:
            await db.execute(
                "UPDATE users SET wallet_balance = 50 WHERE telegram_id = ?", (901001,)
            )
            await db.commit()
        finally:
            await db.close()

    async def asyncTearDown(self):
        db_module.TURSO_URL = self.previous_turso_url
        if self.previous_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self.previous_db_path
        if self.previous_key is None:
            os.environ.pop("CREDENTIAL_ENCRYPTION_KEY", None)
        else:
            os.environ["CREDENTIAL_ENCRYPTION_KEY"] = self.previous_key
        if self.previous_keys is not None:
            os.environ["CREDENTIAL_ENCRYPTION_KEYS"] = self.previous_keys
        self.temp_dir.cleanup()

    async def _raw_task(self, public_id: str):
        db = await get_db()
        try:
            return await (await db.execute(
                "SELECT * FROM pixel_activation_tasks WHERE public_id = ?", (public_id,)
            )).fetchone()
        finally:
            await db.close()

    async def test_credentials_are_encrypted_and_dashboard_trace_is_minimized(self):
        draft = await models.create_pixel_activation_draft(
            user_telegram_id=901001,
            user_display_name="Pixel Trace",
            email="trace@example.com",
            password="plain-password",
            twofa_secret=PIXEL_2FA_SECRET,
            channel="normal",
            request_key="pixel-test-draft-1",
        )
        raw = await self._raw_task(draft["public_id"])
        self.assertEqual(raw["email"], "trace@example.com")
        self.assertEqual(raw["user_display_name"], "Pixel Trace")
        self.assertTrue(str(raw["password_encrypted"]).startswith("enc:v1:"))
        self.assertTrue(str(raw["twofa_secret_encrypted"]).startswith("enc:v1:"))
        self.assertNotIn("plain-password", str(raw["password_encrypted"]))
        self.assertNotIn(PIXEL_2FA_SECRET, str(raw["twofa_secret_encrypted"]))

        snapshot = await models.get_pixel_dashboard_snapshot()
        task = next(item for item in snapshot["tasks"] if item["public_id"] == draft["public_id"])
        self.assertEqual(task["email"], "trace@example.com")
        self.assertNotIn("password_encrypted", task)
        self.assertNotIn("twofa_secret_encrypted", task)
        self.assertNotIn("callback_token_encrypted", task)
        self.assertNotIn("result_link", task)
        self.assertNotIn("error_message", task)

    async def test_credit_purchase_and_task_reservation_are_idempotent(self):
        await models.update_pixel_activation_settings({
            "credit_usd_price": 0.25,
            "fast_credits": 8,
            "normal_credits": 5,
            "is_enabled": False,
            "admin_only": True,
            "min_supplier_points": 0,
            "credential_retention_days": 90,
        })
        packs = await models.get_pixel_credit_packs(active_only=True)
        starter = next(pack for pack in packs if pack["credits"] == 10)
        self.assertEqual(starter["price_usd"], 2.5)

        purchase = await models.purchase_pixel_credit_pack(
            901001, starter["id"], reference_key="pixel-pack-test-1"
        )
        repeat = await models.purchase_pixel_credit_pack(
            901001, starter["id"], reference_key="pixel-pack-test-1"
        )
        self.assertFalse(purchase["idempotent"])
        self.assertTrue(repeat["idempotent"])
        self.assertEqual(await models.get_pixel_credit_balance(901001), 10)

        draft = await models.create_pixel_activation_draft(
            user_telegram_id=901001,
            user_display_name="Pixel Trace",
            email="trace@example.com",
            password="plain-password",
            twofa_secret=PIXEL_2FA_SECRET,
            channel="normal",
            request_key="pixel-test-draft-2",
        )
        reserved = await models.reserve_pixel_activation_task(draft["public_id"], 901001)
        repeated = await models.reserve_pixel_activation_task(draft["public_id"], 901001)
        self.assertEqual(reserved["status"], "RESERVED")
        self.assertEqual(repeated["status"], "RESERVED")
        self.assertEqual(await models.get_pixel_credit_balance(901001), 5)

        refunded = await models.refund_pixel_activation_task(
            draft["public_id"], error_message="safe test failure"
        )
        repeated_refund = await models.refund_pixel_activation_task(
            draft["public_id"], error_message="safe test failure"
        )
        self.assertEqual(refunded["status"], "REFUNDED")
        self.assertEqual(repeated_refund["status"], "REFUNDED")
        self.assertEqual(await models.get_pixel_credit_balance(901001), 10)

    async def test_fractional_credits_are_charged_and_refunded_exactly(self):
        settings = await models.update_pixel_activation_settings({
            "credit_usd_price": 0.25,
            "fast_credits": 1.5,
            "normal_credits": 0.5,
            "is_enabled": False,
            "admin_only": True,
            "min_supplier_points": 0,
            "credential_retention_days": 90,
        })
        self.assertEqual(settings["fast_credits"], 1.5)
        self.assertEqual(settings["normal_credits"], 0.5)

        pack = await models.upsert_pixel_credit_pack({
            "label": "Fractional",
            "credits": 1.5,
            "sort_order": 99,
            "is_active": True,
        })
        self.assertEqual(pack["credits"], 1.5)
        self.assertEqual(pack["price_usd"], 0.375)

        purchase = await models.purchase_pixel_credit_pack(
            901001, pack["id"], reference_key="pixel-fractional-credit-test"
        )
        self.assertEqual(purchase["credits_added"], 1.5)
        self.assertEqual(await models.get_pixel_credit_balance(901001), 1.5)

        draft = await models.create_pixel_activation_draft(
            user_telegram_id=901001,
            user_display_name="Pixel Trace",
            email="fractional@example.com",
            password="plain-password",
            twofa_secret=PIXEL_2FA_SECRET,
            channel="normal",
            request_key="pixel-fractional-draft",
        )
        reserved = await models.reserve_pixel_activation_task(draft["public_id"], 901001)
        self.assertEqual(reserved["credits_reserved"], 0.5)
        self.assertEqual(await models.get_pixel_credit_balance(901001), 1.0)

        await models.refund_pixel_activation_task(
            draft["public_id"], error_message="fractional refund test"
        )
        self.assertEqual(await models.get_pixel_credit_balance(901001), 1.5)

        db = await get_db()
        try:
            stored = await (await db.execute(
                "SELECT typeof(balance_credits) AS balance_type FROM pixel_credit_accounts "
                "WHERE user_telegram_id = ?",
                (901001,),
            )).fetchone()
        finally:
            await db.close()
        self.assertEqual(stored["balance_type"], "real")

    async def test_credit_pack_bonus_is_credited_without_changing_pack_price(self):
        await models.update_pixel_activation_settings({
            "credit_usd_price": 0.25,
            "fast_credits": 1.5,
            "normal_credits": 0.5,
            "is_enabled": False,
            "admin_only": True,
            "min_supplier_points": 0,
            "credential_retention_days": 90,
        })
        pack = await models.upsert_pixel_credit_pack({
            "label": "Pro",
            "credits": 10,
            "bonus_credits": 5,
            "sort_order": 50,
            "is_active": True,
        })
        self.assertEqual(pack["credits"], 10)
        self.assertEqual(pack["bonus_credits"], 5)
        self.assertEqual(pack["total_credits"], 15)
        self.assertEqual(pack["price_usd"], 2.5)

        purchase = await models.purchase_pixel_credit_pack(
            901001, pack["id"], reference_key="pixel-bonus-credit-test"
        )
        repeat = await models.purchase_pixel_credit_pack(
            901001, pack["id"], reference_key="pixel-bonus-credit-test"
        )
        self.assertFalse(purchase["idempotent"])
        self.assertEqual(purchase["credits_added"], 15)
        self.assertEqual(purchase["bonus_credits"], 5)
        self.assertTrue(repeat["idempotent"])
        self.assertEqual(repeat["credits_added"], 15)
        self.assertEqual(await models.get_pixel_credit_balance(901001), 15)

    async def test_expired_draft_keeps_trace_identity_but_erases_credentials(self):
        draft = await models.create_pixel_activation_draft(
            user_telegram_id=901001,
            user_display_name="Pixel Trace",
            email="trace@example.com",
            password="plain-password",
            twofa_secret=PIXEL_2FA_SECRET,
            channel="normal",
            request_key="pixel-test-draft-3",
        )
        db = await get_db()
        try:
            await db.execute(
                "UPDATE pixel_activation_tasks SET created_at = datetime('now', '-25 hours') WHERE public_id = ?",
                (draft["public_id"],),
            )
            await db.commit()
        finally:
            await db.close()

        self.assertEqual(await models.expire_stale_pixel_drafts(), 1)
        raw = await self._raw_task(draft["public_id"])
        self.assertEqual(raw["status"], "CANCELLED")
        self.assertEqual(raw["user_display_name"], "Pixel Trace")
        self.assertEqual(raw["email"], "trace@example.com")
        self.assertEqual(raw["password_encrypted"], "")
        self.assertEqual(raw["twofa_secret_encrypted"], "")

    async def test_batch_reservation_is_atomic_and_idempotent(self):
        packs = await models.get_pixel_credit_packs(active_only=True)
        starter = next(pack for pack in packs if pack["credits"] == 10)
        await models.purchase_pixel_credit_pack(
            901001, starter["id"], reference_key="pixel-batch-credit-test"
        )
        created = await models.create_pixel_activation_batch_drafts(
            user_telegram_id=901001,
            user_display_name="Pixel Trace",
            channel="normal",
            request_key="pixel-batch-test-1",
            credentials=[
                {
                    "email": "one@example.com",
                    "password": "password-one",
                    "twofa_secret": PIXEL_2FA_SECRET,
                },
                {
                    "email": "two@example.com",
                    "password": "password-two",
                    "twofa_secret": PIXEL_2FA_SECRET,
                },
            ],
        )
        self.assertFalse(created["idempotent"])
        self.assertEqual(len(created["tasks"]), 2)
        self.assertTrue(created["batch"]["public_id"])

        reserved = await models.reserve_pixel_activation_batch(
            created["batch"]["public_id"], 901001
        )
        repeated = await models.reserve_pixel_activation_batch(
            created["batch"]["public_id"], 901001
        )
        self.assertTrue(reserved["newly_reserved"])
        self.assertFalse(repeated["newly_reserved"])
        self.assertEqual(len(reserved["tasks"]), 2)
        self.assertEqual(await models.get_pixel_credit_balance(901001), 0)
        self.assertEqual(reserved["batch"]["credits_reserved"], 10)

        db = await get_db()
        try:
            raw_tasks = await (await db.execute(
                "SELECT password_encrypted, twofa_secret_encrypted, batch_public_id "
                "FROM pixel_activation_tasks WHERE batch_public_id = ? ORDER BY id",
                (created["batch"]["public_id"],),
            )).fetchall()
        finally:
            await db.close()
        self.assertEqual(len(raw_tasks), 2)
        self.assertTrue(all(row["batch_public_id"] == created["batch"]["public_id"] for row in raw_tasks))
        self.assertTrue(all(str(row["password_encrypted"]).startswith("enc:v1:") for row in raw_tasks))
        self.assertTrue(all(str(row["twofa_secret_encrypted"]).startswith("enc:v1:") for row in raw_tasks))

    async def test_batch_parser_requires_raw_32_character_twofa_secret(self):
        single_entry = parse_pixel_credentials_message(
            "one@example.com | pass-one | JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
        )
        self.assertEqual(len(single_entry), 1)
        self.assertEqual(single_entry[0]["email"], "one@example.com")

        entries = parse_pixel_credentials_message(
            "one@example.com | pass-one | JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP\n"
            "two@example.com | pass-two | JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP"
        )
        self.assertEqual([entry["email"] for entry in entries], ["one@example.com", "two@example.com"])
        self.assertEqual(entries[0]["twofa_secret"], PIXEL_2FA_SECRET)
        with self.assertRaises(ValueError):
            parse_pixel_credentials_message(
                "one@example.com\npass-one\notpauth://totp/example?secret=JBSWY3DPEHPK3PXP"
            )


if __name__ == "__main__":
    unittest.main()
