import json
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

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
        nowpayments_button = next(
            button
            for row in markup.inline_keyboard
            for button in row
            if button.callback_data == f"pay_nowpayments:{self.order['id']}"
        )
        self.assertEqual(nowpayments_button.text, "BEP20")
        self.assertEqual(nowpayments_button.icon_custom_emoji_id, "5359437015752401733")
        for language in LANGUAGES:
            with self.subTest(language=language):
                self.assertNotEqual(t("btn_pay_nowpayments", language), "btn_pay_nowpayments")
                self.assertEqual(t("btn_pay_nowpayments", language), "BEP20")
                self.assertEqual(t("nowpayments_title", language), "<b>BEP20</b>")
                self.assertNotEqual(t("nowpayments_partial", language), "nowpayments_partial")
                self.assertNotEqual(
                    t("btn_copy_nowpayments_amount", language),
                    "btn_copy_nowpayments_amount",
                )
                self.assertNotEqual(
                    t("nowpayments_fee_warning", language),
                    "nowpayments_fee_warning",
                )
                self.assertNotIn("0.04", t("nowpayments_fee_warning", language))
                self.assertNotIn("0,04", t("nowpayments_fee_warning", language))
                self.assertNotEqual(
                    t("nowpayments_checking", language),
                    "nowpayments_checking",
                )
                self.assertNotEqual(
                    t("nowpayments_checking_short", language),
                    "nowpayments_checking_short",
                )

    def test_copy_button_uses_exact_provider_amount_without_surcharge(self):
        from handlers.payment import _format_crypto_amount
        from utils.keyboards import nowpayments_payment_keyboard

        amount = _format_crypto_amount("0.64936553")
        self.assertEqual(amount, "0.64936553")

        markup = nowpayments_payment_keyboard(self.order["id"], amount, "en")
        copy_button = markup.inline_keyboard[0][0]
        self.assertEqual(copy_button.copy_text.text, amount)

    def test_checkout_price_adds_four_cent_bep20_fee(self):
        self.assertEqual(nowpayments.calculate_checkout_price(0.50), 0.54)
        self.assertEqual(nowpayments.calculate_checkout_price(5), 5.04)

    def test_callback_url_falls_back_to_railway_public_domain(self):
        from handlers.payment import _nowpayments_callback_url

        clean_env = {
            "NOWPAYMENTS_CALLBACK_URL": "",
            "PUBLIC_BASE_URL": "",
            "WEBHOOK_URL": "",
            "RAILWAY_PUBLIC_DOMAIN": "shop-example.up.railway.app",
        }
        with patch.dict(os.environ, clean_env):
            self.assertEqual(
                _nowpayments_callback_url(),
                "https://shop-example.up.railway.app/webhooks/nowpayments",
            )

    def test_explicit_callback_url_has_priority(self):
        from handlers.payment import _nowpayments_callback_url

        with patch.dict(os.environ, {
            "NOWPAYMENTS_CALLBACK_URL": "https://payments.example.com/ipn/",
            "PUBLIC_BASE_URL": "https://ignored.example.com",
            "WEBHOOK_URL": "https://ignored-too.example.com",
            "RAILWAY_PUBLIC_DOMAIN": "ignored.up.railway.app",
        }):
            self.assertEqual(
                _nowpayments_callback_url(),
                "https://payments.example.com/ipn",
            )

    async def test_customer_paid_fees_force_fixed_rate(self):
        request = AsyncMock(return_value={"payment_id": "np-fixed"})
        with patch.object(nowpayments, "_request", request):
            await nowpayments.create_payment(
                price_amount=1,
                order_id=self.order["id"],
                order_description="Test",
                callback_url="https://example.com/webhooks/nowpayments",
                is_fixed_rate=False,
                is_fee_paid_by_user=True,
            )
        payload = request.await_args.kwargs["json"]
        self.assertTrue(payload["is_fixed_rate"])
        self.assertTrue(payload["is_fee_paid_by_user"])

    async def test_default_checkout_uses_floating_rate_without_customer_fees(self):
        request = AsyncMock(return_value={"payment_id": "np-floating"})
        with (
            patch.object(nowpayments, "_request", request),
            patch.object(nowpayments, "NOWPAYMENTS_FIXED_RATE", False),
            patch.object(nowpayments, "NOWPAYMENTS_FEE_PAID_BY_USER", False),
        ):
            await nowpayments.create_payment(
                price_amount=1,
                order_id=self.order["id"],
                order_description="Test",
                callback_url="https://example.com/webhooks/nowpayments",
            )
        payload = request.await_args.kwargs["json"]
        self.assertFalse(payload["is_fixed_rate"])
        self.assertFalse(payload["is_fee_paid_by_user"])

    async def test_minimum_check_uses_the_same_floating_mode(self):
        request = AsyncMock(return_value={"min_amount": 1, "fiat_equivalent": 1})
        with (
            patch.object(nowpayments, "_request", request),
            patch.object(nowpayments, "NOWPAYMENTS_FIXED_RATE", False),
            patch.object(nowpayments, "NOWPAYMENTS_FEE_PAID_BY_USER", False),
        ):
            nowpayments._MINIMUM_CACHE = None
            await nowpayments.get_minimum_amount()
        params = request.await_args.kwargs["params"]
        self.assertEqual(params["is_fixed_rate"], "false")
        self.assertEqual(params["is_fee_paid_by_user"], "false")

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
