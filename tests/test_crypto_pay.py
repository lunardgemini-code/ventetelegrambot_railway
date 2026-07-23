import json
import os
import tempfile
import time
import unittest
from unittest.mock import patch

import httpx

import bot
from database import db as db_module
from database import models
from database.db import init_db
from services import crypto_pay
from utils.keyboards import payment_method_keyboard, wallet_topup_method_keyboard
from utils.locales import t


class CryptoPayTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_db_path = os.environ.get("DB_PATH")
        self.previous_turso_url = db_module.TURSO_URL
        os.environ["DB_PATH"] = os.path.join(
            self.temp_dir.name,
            "cryptopay.db",
        )
        db_module.TURSO_URL = ""
        db_module._sqlite_wal_configured = False
        models.clear_products_cache()
        await init_db()

        await models.get_or_create_user(4101, "crypto_buyer", "Crypto Buyer")
        category_id = await models.add_category("Crypto products")
        self.product_id = await models.add_product(
            category_id=category_id,
            name="Crypto Pay product",
            description="",
            price_usd=5,
        )
        await models.add_stock_items(self.product_id, ["crypto-account"])
        self.order = await models.create_order(
            4101,
            self.product_id,
            5,
            quantity=1,
        )
        self.provider_amount = crypto_pay.calculate_invoice_amount(5, 3)
        self.attempt = await models.prepare_cryptopay_invoice(
            "order",
            4101,
            5,
            order_id=self.order["id"],
            provider_amount_usd=self.provider_amount,
            fee_percent=3,
        )
        self.invoice_id = "810001"
        self.invoice = await models.attach_cryptopay_invoice(
            self.attempt["request_key"],
            self._provider_invoice("active"),
        )

    async def asyncTearDown(self):
        db_module.TURSO_URL = self.previous_turso_url
        if self.previous_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self.previous_db_path
        self.temp_dir.cleanup()

    def _provider_invoice(self, status: str) -> dict:
        return {
            "invoice_id": self.invoice_id,
            "status": status,
            "currency_type": "fiat",
            "fiat": "USD",
            "amount": f"{self.provider_amount:.2f}",
            "asset": "USDT" if status == "paid" else None,
            "paid_amount": (
                f"{self.provider_amount:.2f}" if status == "paid" else None
            ),
            "paid_usd_rate": "1.00" if status == "paid" else None,
            "payload": self.attempt["provider_payload"],
            "bot_invoice_url": f"https://t.me/CryptoBot?start=invoice-{self.invoice_id}",
            "expiration_date": "2030-01-01T00:00:00Z",
        }

    def test_signature_is_raw_body_bound_and_tamper_evident(self):
        token = "test-crypto-pay-token"
        body = b'{"update_id":1,"update_type":"invoice_paid"}'
        signature = crypto_pay.calculate_webhook_signature(body, token=token)
        with patch.object(crypto_pay, "CRYPTO_PAY_API_TOKEN", token):
            self.assertTrue(
                crypto_pay.verify_webhook_signature(body, signature)
            )
            self.assertFalse(
                crypto_pay.verify_webhook_signature(body + b" ", signature)
            )

    def test_request_date_freshness_rejects_replay(self):
        self.assertTrue(crypto_pay.request_date_is_fresh(int(time.time())))
        self.assertFalse(
            crypto_pay.request_date_is_fresh(int(time.time()) - 3600)
        )
        self.assertFalse(crypto_pay.request_date_is_fresh("not-a-date"))

    def test_three_percent_fee_is_grossed_up_and_labelled(self):
        self.assertEqual(crypto_pay.calculate_invoice_amount(0.50, 3), 0.52)
        self.assertEqual(crypto_pay.calculate_invoice_amount(2.50, 3), 2.58)
        self.assertEqual(crypto_pay.calculate_invoice_amount(100, 3), 103.10)
        label = t("btn_pay_cryptopay", "en").format(fee="3")
        self.assertEqual(label, "CryptoBot (3%)")

    async def test_cryptopay_buttons_use_the_configured_custom_emoji(self):
        with (
            patch.object(crypto_pay, "CRYPTO_PAY_ENABLED", True),
            patch.object(crypto_pay, "CRYPTO_PAY_API_TOKEN", "test-token"),
            patch.object(
                crypto_pay,
                "CRYPTO_PAY_WEBHOOK_SECRET",
                "test-webhook-secret",
            ),
        ):
            purchase_markup = await payment_method_keyboard(
                self.order["id"],
                "en",
                0,
            )
            topup_markup = await wallet_topup_method_keyboard("en")

        purchase_button = next(
            button
            for row in purchase_markup.inline_keyboard
            for button in row
            if str(button.callback_data or "").startswith("pay_cryptopay:")
        )
        topup_button = next(
            button
            for row in topup_markup.inline_keyboard
            for button in row
            if button.callback_data == "topup_cryptopay"
        )
        expected_emoji_id = "5373118582534228948"
        self.assertEqual(purchase_button.icon_custom_emoji_id, expected_emoji_id)
        self.assertEqual(topup_button.icon_custom_emoji_id, expected_emoji_id)

    async def test_paid_order_is_delivered_exactly_once(self):
        await models.update_order_status(
            self.order["id"],
            "AWAITING_PAYMENT",
            expected_statuses=("PENDING",),
            payment_method="cryptopay",
        )
        await models.save_cryptopay_update(self._provider_invoice("paid"))

        first = await models.finalize_cryptopay_invoice(self.invoice_id)
        second = await models.finalize_cryptopay_invoice(self.invoice_id)
        order = await models.get_order(self.order["id"])
        user = await models.get_user(4101)
        items = await models.get_stock_items_for_order(self.order["id"])

        self.assertEqual(first["action"], "completed")
        self.assertEqual(second["action"], "completed")
        self.assertTrue(second["already_processed"])
        self.assertEqual(order["status"], "COMPLETED")
        self.assertEqual(order["payment_method"], "cryptopay")
        self.assertEqual(len(items), 1)
        self.assertEqual(user["total_orders"], 1)
        self.assertAlmostEqual(float(user["total_spent"]), 5.0)
        self.assertAlmostEqual(
            float(first["invoice"]["provider_amount_usd"]),
            self.provider_amount,
        )
        self.assertAlmostEqual(float(first["invoice"]["amount_usd"]), 5.0)

    async def test_wallet_topup_is_credited_exactly_once(self):
        provider_amount = crypto_pay.calculate_invoice_amount(3.25, 3)
        attempt = await models.prepare_cryptopay_invoice(
            "wallet_topup",
            4101,
            3.25,
            wallet_amount=3.25,
            provider_amount_usd=provider_amount,
            fee_percent=3,
        )
        invoice_id = "810002"
        payload = {
            "invoice_id": invoice_id,
            "status": "active",
            "amount": f"{provider_amount:.2f}",
            "currency_type": "fiat",
            "fiat": "USD",
            "payload": attempt["provider_payload"],
            "bot_invoice_url": "https://t.me/CryptoBot?start=invoice-810002",
        }
        await models.attach_cryptopay_invoice(attempt["request_key"], payload)
        payload.update(
            {
                "status": "paid",
                "asset": "USDT",
                "paid_amount": f"{provider_amount:.2f}",
                "paid_usd_rate": "1.00",
            }
        )
        await models.save_cryptopay_update(payload)

        first = await models.finalize_cryptopay_invoice(invoice_id)
        second = await models.finalize_cryptopay_invoice(invoice_id)
        balance = await models.get_wallet_balance(4101)
        transactions = await models.get_wallet_transactions(4101, limit=10)

        self.assertEqual(first["action"], "wallet_credited")
        self.assertEqual(second["action"], "wallet_credited")
        self.assertTrue(second["already_processed"])
        self.assertAlmostEqual(balance, 3.25)
        matching = [
            tx
            for tx in transactions
            if "Crypto Pay" in str(tx.get("description") or "")
        ]
        self.assertEqual(len(matching), 1)

    async def test_provider_amount_mismatch_is_rejected_before_payment(self):
        attempt = await models.prepare_cryptopay_invoice(
            "wallet_topup",
            4101,
            4.00,
            wallet_amount=4.00,
            provider_amount_usd=4.13,
            fee_percent=3,
        )
        with self.assertRaisesRegex(
            ValueError,
            "CRYPTOPAY_INVOICE_AMOUNT_MISMATCH",
        ):
            await models.attach_cryptopay_invoice(
                attempt["request_key"],
                {
                    "invoice_id": "810003",
                    "status": "active",
                    "amount": "4.00",
                    "payload": attempt["provider_payload"],
                    "bot_invoice_url": (
                        "https://t.me/CryptoBot?start=invoice-810003"
                    ),
                },
            )

    async def test_expiration_cancels_order_and_stops_polling(self):
        await models.update_order_status(
            self.order["id"],
            "AWAITING_PAYMENT",
            expected_statuses=("PENDING",),
            payment_method="cryptopay",
        )
        db = await db_module.get_db()
        try:
            await db.execute(
                """UPDATE cryptopay_invoices
                   SET created_at = datetime('now', '-6 minutes')
                   WHERE invoice_id = ?""",
                (self.invoice_id,),
            )
            await db.commit()
        finally:
            await db.close()

        expired = await models.expire_stale_cryptopay_invoices(
            timeout_seconds=300
        )
        order = await models.get_order(self.order["id"])
        invoice = await models.get_cryptopay_invoice(self.invoice_id)
        pollable = await models.list_cryptopay_invoices_to_poll()

        self.assertEqual(expired, [self.invoice_id])
        self.assertEqual(order["status"], "CANCELLED")
        self.assertEqual(invoice["provider_status"], "expired")
        self.assertNotIn(
            self.invoice_id,
            {str(item["invoice_id"]) for item in pollable},
        )

    async def test_late_payment_after_cancellation_requires_review(self):
        await models.update_order_status(
            self.order["id"],
            "CANCELLED",
            expected_statuses=("PENDING",),
        )
        await models.cancel_cryptopay_order_invoice(self.order["id"])
        await models.save_cryptopay_update(self._provider_invoice("paid"))

        result = await models.finalize_cryptopay_invoice(self.invoice_id)
        order = await models.get_order(self.order["id"])
        items = await models.get_stock_items_for_order(self.order["id"])

        self.assertEqual(result["action"], "review_required")
        self.assertEqual(order["status"], "CANCELLED")
        self.assertEqual(items, [])

    async def test_signed_webhook_persists_paid_status(self):
        webhook_secret = "test-webhook-path-secret"
        token = "test-webhook-token"
        body = json.dumps(
            {
                "update_id": 77,
                "update_type": "invoice_paid",
                "request_date": int(time.time()),
                "payload": self._provider_invoice("paid"),
            },
            separators=(",", ":"),
        ).encode("utf-8")
        signature = crypto_pay.calculate_webhook_signature(body, token=token)

        transport = httpx.ASGITransport(app=bot.api)
        with (
            patch.object(crypto_pay, "CRYPTO_PAY_ENABLED", True),
            patch.object(crypto_pay, "CRYPTO_PAY_API_TOKEN", token),
            patch.object(
                crypto_pay,
                "CRYPTO_PAY_WEBHOOK_SECRET",
                webhook_secret,
            ),
            patch.object(bot, "tg_app", None),
        ):
            async with httpx.AsyncClient(
                transport=transport,
                base_url="http://test",
            ) as client:
                response = await client.post(
                    f"/webhooks/cryptopay/{webhook_secret}",
                    content=body,
                    headers={"crypto-pay-api-signature": signature},
                )
                invalid = await client.post(
                    f"/webhooks/cryptopay/{webhook_secret}",
                    content=body,
                    headers={"crypto-pay-api-signature": "invalid"},
                )

        invoice = await models.get_cryptopay_invoice(self.invoice_id)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "accepted")
        self.assertEqual(invalid.status_code, 401)
        self.assertEqual(invoice["provider_status"], "paid")

    async def test_notification_claim_is_single_consumer(self):
        self.assertTrue(
            await models.claim_cryptopay_notification(self.invoice_id)
        )
        self.assertFalse(
            await models.claim_cryptopay_notification(self.invoice_id)
        )


if __name__ == "__main__":
    unittest.main()
