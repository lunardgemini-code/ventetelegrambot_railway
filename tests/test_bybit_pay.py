import base64
import hashlib
import hmac
import json
import os
import tempfile
import time
import unittest
from unittest.mock import patch

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa

import bot
import config
from database import db as db_module
from database import models
from database.db import init_db
from services import bybit_pay
from utils.keyboards import payment_method_keyboard


class BybitPayTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_db_path = os.environ.get("DB_PATH")
        self.previous_turso_url = db_module.TURSO_URL
        os.environ["DB_PATH"] = os.path.join(self.temp_dir.name, "bybitpay.db")
        db_module.TURSO_URL = ""
        db_module._sqlite_wal_configured = False
        models.clear_products_cache()
        await init_db()

        await models.get_or_create_user(5101, "bybit_buyer", "Bybit Buyer")
        category_id = await models.add_category("Bybit products")
        self.product_id = await models.add_product(
            category_id=category_id,
            name="Bybit Pay product",
            description="",
            price_usd=5,
        )
        await models.add_stock_items(self.product_id, ["bybit-account"])
        self.order = await models.create_order(5101, self.product_id, 5, quantity=1)
        self.attempt = await models.prepare_cryptopay_invoice(
            "order",
            5101,
            5,
            order_id=self.order["id"],
            provider="bybitpay",
        )
        self.pay_id = "01TESTBYBITPAY"
        self.invoice = await models.attach_cryptopay_invoice(
            self.attempt["request_key"],
            self._normalized("INIT"),
        )

    async def asyncTearDown(self):
        await bybit_pay.close_bybit_pay_client()
        db_module.TURSO_URL = self.previous_turso_url
        if self.previous_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self.previous_db_path
        self.temp_dir.cleanup()

    def _provider_payload(self, status: str) -> dict:
        return {
            "paymentType": "E_COMMERCE",
            "merchantId": "merchant-1",
            "merchantTradeNo": self.attempt["provider_payload"],
            "payId": self.pay_id,
            "status": status,
            "amount": "5.00",
            "currency": "USDT",
            "currencyType": "crypto",
            "createTime": int(time.time()),
            "paymentTime": int(time.time()) if status == "PAY_SUCCESS" else 0,
            "finishTime": int(time.time()) if status != "INIT" else 0,
        }

    def _normalized(self, status: str) -> dict:
        result = bybit_pay.normalize_payment(self._provider_payload(status))
        result["web_app_invoice_url"] = "https://www.bybit.com/pay/test"
        return result

    async def test_button_is_hidden_until_all_credentials_are_configured(self):
        with patch.object(bybit_pay, "BYBIT_PAY_ENABLED", False):
            hidden = await payment_method_keyboard(self.order["id"], "en", 0)
        self.assertFalse(any(
            str(button.callback_data or "").startswith("pay_bybitpay:")
            for row in hidden.inline_keyboard for button in row
        ))

        with (
            patch.object(bybit_pay, "BYBIT_PAY_ENABLED", True),
            patch.object(bybit_pay, "BYBIT_PAY_API_KEY", "key"),
            patch.object(bybit_pay, "BYBIT_PAY_API_SECRET", "secret"),
            patch.object(bybit_pay, "BYBIT_PAY_MERCHANT_ID", "merchant"),
            patch.object(bybit_pay, "BYBIT_PAY_WEBHOOK_PUBLIC_KEY", "public-key"),
        ):
            visible = await payment_method_keyboard(self.order["id"], "en", 0)
        self.assertTrue(any(
            str(button.callback_data or "").startswith("pay_bybitpay:")
            for row in visible.inline_keyboard for button in row
        ))

    def test_checkout_allowlist_accepts_only_bybit_targets(self):
        self.assertTrue(bybit_pay.is_safe_checkout_url("bybitapp://open/route?x=1"))
        self.assertTrue(bybit_pay.is_safe_checkout_url("https://www.bybit.com/pay/test"))
        self.assertFalse(bybit_pay.is_safe_checkout_url("https://bybit.com.evil.test/pay"))
        self.assertFalse(bybit_pay.is_safe_checkout_url("javascript:alert(1)"))

    async def test_https_bridge_redirects_only_saved_bybit_checkout(self):
        transport = httpx.ASGITransport(app=bot.api)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
            follow_redirects=False,
        ) as client:
            response = await client.get(
                f"/payments/bybit/{self.attempt['request_key']}"
            )
            malformed = await client.get("/payments/bybit/not-a-payment")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["location"], "https://www.bybit.com/pay/test")
        self.assertEqual(response.headers["cache-control"], "no-store")
        self.assertEqual(malformed.status_code, 404)

    async def test_api_request_uses_bybit_hmac_contract(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            body = request.content.decode("utf-8")
            timestamp = request.headers["X-BAPI-TIMESTAMP"]
            expected = hmac.new(
                b"secret",
                f"{timestamp}key5000{body}".encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            captured["valid_signature"] = hmac.compare_digest(
                expected, request.headers["X-BAPI-SIGN"]
            )
            captured["payload"] = json.loads(body)
            return httpx.Response(200, json={
                "retCode": 100000,
                "retMsg": "success",
                "result": {
                    "payId": self.pay_id,
                    "checkoutLink": "https://www.bybit.com/pay/test",
                    "expireTime": int(time.time()) + 300,
                    "order": self._provider_payload("INIT"),
                },
            })

        transport = httpx.MockTransport(handler)
        bybit_pay._HTTP_CLIENT = httpx.AsyncClient(
            transport=transport,
            base_url="https://api.bybit.test",
        )
        with (
            patch.object(bybit_pay, "BYBIT_PAY_ENABLED", True),
            patch.object(bybit_pay, "BYBIT_PAY_API_KEY", "key"),
            patch.object(bybit_pay, "BYBIT_PAY_API_SECRET", "secret"),
            patch.object(bybit_pay, "BYBIT_PAY_MERCHANT_ID", "merchant-1"),
            patch.object(bybit_pay, "BYBIT_PAY_WEBHOOK_PUBLIC_KEY", "public-key"),
        ):
            result = await bybit_pay.create_payment(
                amount_usd=5,
                merchant_trade_no=self.attempt["provider_payload"],
                goods_name="Product",
                callback_url="https://shop.test/webhooks/bybitpay",
                success_url="https://shop.test/health/live",
                expires_in=300,
                user_telegram_id=5101,
            )

        self.assertTrue(captured["valid_signature"])
        self.assertEqual(captured["payload"]["orderAmount"], "5.00")
        self.assertEqual(captured["payload"]["paymentType"], "E_COMMERCE")
        self.assertEqual(result["payId"], self.pay_id)

    async def test_signed_webhook_is_raw_body_bound(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public_pem = private_key.public_key().public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("ascii")
        body = json.dumps(
            self._provider_payload("PAY_SUCCESS"),
            separators=(",", ":"),
        ).encode("utf-8")
        timestamp = str(int(time.time()))
        signature = base64.b64encode(private_key.sign(
            timestamp.encode("ascii") + body,
            padding.PKCS1v15(),
            hashes.SHA256(),
        )).decode("ascii")

        transport = httpx.ASGITransport(app=bot.api)
        with (
            patch.object(bybit_pay, "BYBIT_PAY_ENABLED", True),
            patch.object(bybit_pay, "BYBIT_PAY_API_KEY", "key"),
            patch.object(bybit_pay, "BYBIT_PAY_API_SECRET", "secret"),
            patch.object(bybit_pay, "BYBIT_PAY_MERCHANT_ID", "merchant-1"),
            patch.object(bybit_pay, "BYBIT_PAY_WEBHOOK_PUBLIC_KEY", public_pem),
            patch.object(config, "BYBIT_PAY_MERCHANT_ID", "merchant-1"),
            patch.object(bot, "tg_app", None),
        ):
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                accepted = await client.post(
                    "/webhooks/bybitpay",
                    content=body,
                    headers={"timestamp": timestamp, "signature": signature},
                )
                rejected = await client.post(
                    "/webhooks/bybitpay",
                    content=body + b" ",
                    headers={"timestamp": timestamp, "signature": signature},
                )

        invoice = await models.get_cryptopay_invoice(self.pay_id)
        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(rejected.status_code, 401)
        self.assertEqual(invoice["provider_status"], "paid")

    async def test_paid_order_is_delivered_once_with_bybit_method(self):
        await models.update_order_status(
            self.order["id"],
            "AWAITING_PAYMENT",
            expected_statuses=("PENDING",),
            payment_method="bybitpay",
        )
        await models.save_cryptopay_update(self._normalized("PAY_SUCCESS"))
        first = await models.finalize_cryptopay_invoice(self.pay_id)
        second = await models.finalize_cryptopay_invoice(self.pay_id)
        order = await models.get_order(self.order["id"])
        items = await models.get_stock_items_for_order(self.order["id"])

        self.assertEqual(first["action"], "completed")
        self.assertTrue(second["already_processed"])
        self.assertEqual(order["payment_method"], "bybitpay")
        self.assertEqual(len(items), 1)

    async def test_provider_timeout_cancels_unpaid_order(self):
        await models.update_order_status(
            self.order["id"],
            "AWAITING_PAYMENT",
            expected_statuses=("PENDING",),
            payment_method="bybitpay",
        )
        await models.save_cryptopay_update(self._normalized("TIMEOUT"))
        result = await models.finalize_cryptopay_invoice(self.pay_id)
        order = await models.get_order(self.order["id"])

        self.assertEqual(result["action"], "expired")
        self.assertEqual(order["status"], "CANCELLED")

    async def test_provider_scoped_expiration_does_not_touch_cryptopay(self):
        crypto_order = await models.create_order(5101, self.product_id, 5, quantity=1)
        crypto_attempt = await models.prepare_cryptopay_invoice(
            "order", 5101, 5, order_id=crypto_order["id"]
        )
        await models.attach_cryptopay_invoice(crypto_attempt["request_key"], {
            "invoice_id": "crypto-other",
            "status": "active",
            "amount": "5.00",
            "payload": crypto_attempt["provider_payload"],
            "bot_invoice_url": "https://t.me/CryptoBot?start=test",
        })
        db = await db_module.get_db()
        try:
            await db.execute(
                "UPDATE cryptopay_invoices SET created_at = datetime('now', '-10 minutes')"
            )
            await db.commit()
        finally:
            await db.close()

        expired = await models.expire_stale_cryptopay_invoices(
            timeout_seconds=300,
            provider="bybitpay",
        )
        crypto_invoice = await models.get_cryptopay_invoice("crypto-other")
        self.assertEqual(expired, [self.pay_id])
        self.assertEqual(crypto_invoice["provider_status"], "active")


if __name__ == "__main__":
    unittest.main()
