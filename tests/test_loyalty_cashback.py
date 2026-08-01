import asyncio
import os
import tempfile
import unittest
from pathlib import Path

from database import db as db_module
from database import models
from database.db import get_db, init_db
from handlers.cashback import _cashback_claim_rejection_text, _cashback_text
from utils.keyboards import cashback_keyboard


ROOT = Path(__file__).resolve().parents[1]


class LoyaltyCashbackTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["DB_PATH"] = os.path.join(self.temp_dir.name, "loyalty.db")
        db_module.TURSO_URL = ""
        db_module._sqlite_wal_configured = False
        models._SETTINGS_CACHE.clear()
        await init_db()
        await models.get_or_create_user(81001, "cashback", "Cashback User")
        category_id = await models.add_category("Cashback tests")
        self.product_id = await models.add_product(
            category_id=category_id,
            name="Cashback product",
            description="",
            price_usd=10,
        )

    async def asyncTearDown(self):
        self.temp_dir.cleanup()

    async def _complete_order(self, amount: float) -> dict:
        order = await models.create_order(81001, self.product_id, amount)
        changed = await models.update_order_status(
            order["id"], "COMPLETED", payment_method="wallet"
        )
        self.assertTrue(changed)
        return order

    async def test_migration_28_creates_idempotent_ledger(self):
        db = await get_db()
        try:
            migration = await (
                await db.execute(
                    "SELECT name FROM schema_migrations WHERE version = 28"
                )
            ).fetchone()
            table = await (
                await db.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' "
                    "AND name='loyalty_transactions'"
                )
            ).fetchone()
        finally:
            await db.close()
        self.assertEqual(migration["name"], "loyalty_cashback_ledger")
        self.assertEqual(table["name"], "loyalty_transactions")

    async def test_completed_order_awards_default_points_once(self):
        order = await self._complete_order(10)
        first = await models.get_loyalty_summary(81001)

        changed = await models.update_order_status(
            order["id"], "COMPLETED", payment_method="wallet"
        )
        second = await models.get_loyalty_summary(81001)

        self.assertEqual(first["balance_points"], 100)
        self.assertFalse(changed)
        self.assertEqual(second["balance_points"], 100)
        self.assertEqual(len(second["history"]), 1)

    async def test_pending_and_cancelled_orders_do_not_earn_points(self):
        pending = await models.create_order(81001, self.product_id, 10)
        await models.update_order_status(pending["id"], "CANCELLED")
        summary = await models.get_loyalty_summary(81001)
        self.assertEqual(summary["balance_points"], 0)

    async def test_claim_requires_minimum_and_credits_wallet(self):
        await self._complete_order(199.90)
        with self.assertRaisesRegex(ValueError, "LOYALTY_MINIMUM_NOT_REACHED"):
            await models.redeem_loyalty_to_wallet(81001)

        await self._complete_order(0.10)
        result = await models.redeem_loyalty_to_wallet(81001)
        summary = await models.get_loyalty_summary(81001)
        user = await models.get_user(81001)

        self.assertEqual(result["redeemed_points"], 2000)
        self.assertAlmostEqual(result["wallet_amount_usd"], 2.0)
        self.assertAlmostEqual(float(user["wallet_balance"]), 2.0)
        self.assertEqual(summary["balance_points"], 0)
        self.assertEqual(summary["redeemed_points"], 2000)

    async def test_concurrent_double_claim_only_credits_once(self):
        await self._complete_order(200)

        results = await asyncio.gather(
            models.redeem_loyalty_to_wallet(81001),
            models.redeem_loyalty_to_wallet(81001),
            return_exceptions=True,
        )
        successes = [result for result in results if isinstance(result, dict)]
        failures = [result for result in results if isinstance(result, Exception)]
        user = await models.get_user(81001)

        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        self.assertAlmostEqual(float(user["wallet_balance"]), 2.0)

    async def test_settings_change_earning_and_cashout_conversion(self):
        saved = await models.set_loyalty_settings({
            "enabled": True,
            "earn_spend_usd": 5,
            "earn_points": 200,
            "redeem_min_points": 500,
            "redeem_block_points": 100,
            "redeem_block_usd": 0.25,
        })
        await self._complete_order(12.50)
        summary = await models.get_loyalty_summary(81001)
        result = await models.redeem_loyalty_to_wallet(81001)

        self.assertEqual(saved["redeem_min_points"], 500)
        self.assertEqual(summary["balance_points"], 500)
        self.assertAlmostEqual(result["wallet_amount_usd"], 1.25)

    async def test_disabled_program_does_not_award_new_orders(self):
        await models.set_loyalty_settings({"enabled": False})
        await self._complete_order(20)
        summary = await models.get_loyalty_summary(81001)
        self.assertFalse(summary["enabled"])
        self.assertEqual(summary["balance_points"], 0)

    async def test_users_list_includes_and_sorts_cashback_points(self):
        await self._complete_order(10)

        users, total = await models.get_users_paginated(
            limit=20,
            offset=0,
            search="81001",
            sort="loyalty_points",
            order="desc",
        )

        self.assertEqual(total, 1)
        self.assertEqual(users[0]["telegram_id"], 81001)
        self.assertEqual(users[0]["loyalty_points"], 100)


class LoyaltyDashboardAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        cls.app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")

    def test_dashboard_exposes_configurable_cashback(self):
        self.assertIn('id="loyalty-settings-form"', self.html)
        self.assertIn("/api/loyalty/settings", self.app)
        self.assertIn("handleSaveLoyaltySettings", self.app)
        self.assertIn("updateLoyaltyPreview", self.app)

    def test_users_table_exposes_cashback_points(self):
        self.assertIn('data-field="loyalty_points"', self.html)
        self.assertIn('data-i18n="th_cashback_points"', self.html)
        self.assertIn("u.loyalty_points||0", self.app)

    def test_all_dashboard_languages_have_cashback_strings(self):
        section = self.app.split("const LOYALTY_TRANSLATIONS = {", 1)[1].split(
            "Object.entries(LOYALTY_TRANSLATIONS)", 1
        )[0]
        for key in (
            "loyalty_settings_title",
            "loyalty_settings_desc",
            "loyalty_minimum",
            "loyalty_save",
            "loyalty_saved",
            "th_cashback_points",
        ):
            self.assertEqual(section.count(f'{key}:"'), 6, key)


class LoyaltyTelegramInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.summary = {
            "enabled": True,
            "balance_points": 100,
            "redeemable_usd": 0,
            "earn_points": 100,
            "earn_spend_usd": 10,
            "redeem_min_points": 2000,
            "redeem_block_points": 100,
            "redeem_block_usd": 0.10,
        }

    def test_cashback_home_hides_minimum_warning(self):
        text = _cashback_text(self.summary, "en")

        self.assertNotIn("You need", text)
        self.assertNotIn("more points", text)
        self.assertNotIn("Claim from", text)
        self.assertNotIn("100 points =", text)

    def test_cashback_keyboard_always_has_claim_and_back(self):
        callbacks = [
            row[0].callback_data for row in cashback_keyboard("en").inline_keyboard
        ]

        self.assertEqual(callbacks, ["cashback_claim", "back_main"])

    def test_claim_click_explains_required_and_current_points(self):
        text = _cashback_claim_rejection_text(
            self.summary, "en", "LOYALTY_MINIMUM_NOT_REACHED"
        )

        self.assertIn("2000 points", text)
        self.assertIn("100 points", text)


if __name__ == "__main__":
    unittest.main()
