import json
import os
import tempfile
import unittest
from unittest.mock import patch

import httpx

from database import db as db_module
from database.db import init_db
from database import models
from services import nowpayments


class NowPaymentsTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["DB_PATH"] = os.path.join(self.temp_dir.name, "nowpayments.db")
        db_module.TURSO_URL = ""
        db_module._sqlite_wal_configured = False
        models.clear_products_cache()
        await init_db()
        await models.get_or_create_user(2001, "np_buyer", "NP Buyer")
        category_id = await models.add_category("Products")
        self.product_id = await models.add_product(
            category_id=category_id,
            name="NOWPayments product",
            description="",
            price_usd=5,
        )
        await models.add_stock_items(self.product_id, ["np-account"])
        self.order = await models.create_order(2001, self.product_id, 5, quantity=1)
        attempt = await models.prepare_nowpayments_attempt(self.order["id"], 5)
        self.payment_id = "np-webhook-1"
        await models.attach_nowpayments_payment(attempt["request_key"], {
            "payment_id": self.payment_id,
            "payment_status": "waiting",
            "pay_amount": 5,
            "pay_currency": "usdtbsc",
            "pay_address": "0x1111111111111111111111111111111111111111",
        })

    async def asyncTearDown(self):
        self.temp_dir.cleanup()

    def test_ipn_signature_is_order_independent_and_tamper_evident(self):
        secret = "test-ipn-secret"
        first = {"payment_status": "finished", "nested": {"z": 2, "a": 1}, "payment_id": 7}
        second = {"payment_id": 7, "nested": {"a": 1, "z": 2}, "payment_status": "finished"}
        signature = nowpayments.calculate_ipn_signature(first, secret=secret)

        with patch.object(nowpayments, "NOWPAYMENTS_IPN_SECRET", secret):
            self.assertTrue(nowpayments.verify_ipn_signature(second, signature))
            second["payment_status"] = "waiting"
            self.assertFalse(nowpayments.verify_ipn_signature(second, signature))

    async def test_notification_claim_prevents_duplicate_messages(self):
        self.assertTrue(await models.claim_nowpayments_notification(self.payment_id))
        self.assertFalse(await models.claim_nowpayments_notification(self.payment_id))
        await models.release_nowpayments_notification(self.payment_id)
        self.assertTrue(await models.claim_nowpayments_notification(self.payment_id))
        await models.mark_nowpayments_notified(self.payment_id)
        self.assertFalse(await models.claim_nowpayments_notification(self.payment_id))

    async def test_payment_button_and_translations_exist_for_every_language(self):
        from utils.keyboards import payment_method_keyboard
        from utils.locales import LANGUAGES, t

        with (
            patch.object(nowpayments, "NOWPAYMENTS_ENABLED", True),
            patch.object(nowpayments, "NOWPAYMENTS_API_KEY", "test-api-key"),
            patch.object(nowpayments, "NOWPAYMENTS_IPN_SECRET", "test-ipn-secret"),
        ):
            markup = await payment_method_keyboard(self.order["id"], "en")

        callbacks = [button.callback_data for row in markup.inline_keyboard for button in row]
        self.assertIn(f"pay_nowpayments:{self.order['id']}", callbacks)
        for language in LANGUAGES:
            with self.subTest(language=language):
                self.assertNotEqual(t("btn_pay_nowpayments", language), "btn_pay_nowpayments")
                self.assertNotEqual(t("nowpayments_partial", language), "nowpayments_partial")

    async def test_webhook_rejects_bad_signature_and_accepts_valid_update(self):
        import bot

        payload = {
            "payment_id": self.payment_id,
            "payment_status": "finished",
            "order_id": str(self.order["id"]),
            "pay_amount": 5,
            "actually_paid": 5,
            "pay_currency": "usdtbsc",
        }
        secret = "test-ipn-secret"
        signature = nowpayments.calculate_ipn_signature(payload, secret=secret)
        transport = httpx.ASGITransport(app=bot.api)

        with (
            patch.object(nowpayments, "NOWPAYMENTS_ENABLED", True),
            patch.object(nowpayments, "NOWPAYMENTS_API_KEY", "test-api-key"),
            patch.object(nowpayments, "NOWPAYMENTS_IPN_SECRET", secret),
            patch.object(bot, "tg_app", None),
        ):
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                invalid = await client.post(
                    "/webhooks/nowpayments",
                    content=json.dumps(payload),
                    headers={"Content-Type": "application/json", "x-nowpayments-sig": "bad"},
                )
                accepted = await client.post(
                    "/webhooks/nowpayments",
                    content=json.dumps(payload),
                    headers={"Content-Type": "application/json", "x-nowpayments-sig": signature},
                )

        self.assertEqual(invalid.status_code, 401)
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.json()["status"], "accepted")
        saved = await models.get_nowpayments_payment(self.payment_id)
        self.assertEqual(saved["provider_status"], "finished")
        self.assertAlmostEqual(float(saved["actually_paid"]), 5.0)
        self.assertAlmostEqual(float(saved["actually_paid"]), 5.0)

        await models.save_nowpayments_update({
            "payment_id": self.payment_id,
            "payment_status": "waiting",
            "order_id": str(self.order["id"]),
            "pay_amount": 5,
            "actually_paid": 0,
            "pay_currency": "usdtbsc",
        })
        saved = await models.get_nowpayments_payment(self.payment_id)
        self.assertEqual(saved["provider_status"], "finished")


if __name__ == "__main__":
    unittest.main()
