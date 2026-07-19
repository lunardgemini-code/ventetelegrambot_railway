import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import httpx

import bot

from database import db as db_module
from database import models
from database.db import init_db
from services.reseller_security import (
    canonical_webhook_body,
    ip_is_allowed,
    normalize_ip_allowlist,
    sign_webhook_body,
    validate_webhook_url,
)


class ResellerFundingTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = os.environ.get("DB_PATH")
        self.original_turso_url = db_module.TURSO_URL
        os.environ["DB_PATH"] = os.path.join(self.temp_dir.name, "reseller-funding.db")
        db_module.TURSO_URL = ""
        db_module._sqlite_wal_configured = False
        models._RESELLER_AUTH_CACHE.clear()
        await init_db()
        await models.get_or_create_user(7001, "reseller", "Reseller")
        await models.topup_wallet(7001, 1.0, "Admin test credit")
        self.key = await models.create_reseller_api_key(7001, "Test bot")

    async def asyncTearDown(self):
        models._RESELLER_AUTH_CACHE.clear()
        db_module.TURSO_URL = self.original_turso_url
        if self.original_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self.original_db_path
        self.temp_dir.cleanup()

    async def test_deposit_idempotency_and_credit_are_exactly_once(self):
        prepared = await models.prepare_reseller_deposit(
            self.key["id"], 7001, 5.0, "BEP20", "deposit-001", "checkout-1"
        )
        self.assertTrue(prepared["created"])
        replay = await models.prepare_reseller_deposit(
            self.key["id"], 7001, 5.0, "BEP20", "deposit-001", "checkout-1"
        )
        self.assertFalse(replay["created"])
        self.assertEqual(
            replay["deposit"]["public_id"], prepared["deposit"]["public_id"]
        )
        with self.assertRaisesRegex(ValueError, "Idempotency key"):
            await models.prepare_reseller_deposit(
                self.key["id"], 7001, 6.0, "BEP20", "deposit-001", "checkout-1"
            )

        request_key = prepared["deposit"]["request_key"]
        await models.attach_nowpayments_wallet_topup(request_key, {
            "payment_id": "reseller-deposit-payment-1",
            "payment_status": "waiting",
            "pay_amount": 5.01,
            "pay_currency": "usdtbsc",
            "pay_address": "0x1111111111111111111111111111111111111111",
        })
        await models.save_nowpayments_update({
            "payment_id": "reseller-deposit-payment-1",
            "payment_status": "finished",
            "order_id": request_key,
            "pay_amount": 5.01,
            "actually_paid": 5.01,
            "pay_currency": "usdtbsc",
        })
        first = await models.finalize_nowpayments_wallet_topup(
            "reseller-deposit-payment-1"
        )
        second = await models.finalize_nowpayments_wallet_topup(
            "reseller-deposit-payment-1"
        )
        self.assertEqual(first["action"], "wallet_credited")
        self.assertTrue(second["already_processed"])
        self.assertAlmostEqual(await models.get_wallet_balance(7001), 6.0)
        deposit = await models.get_reseller_deposit(
            7001, prepared["deposit"]["public_id"]
        )
        self.assertEqual(models.public_reseller_deposit(deposit)["status"], "CREDITED")

    async def test_api_test_product_is_virtual_idempotent_and_debits_wallet(self):
        product = models.get_reseller_test_product()
        self.assertIsNotNone(product)
        normal_products = await models.get_all_products()
        self.assertNotIn(product["id"], [item["id"] for item in normal_products])

        result = await models.create_reseller_order(
            reseller_user_telegram_id=7001,
            reseller_api_key_id=self.key["id"],
            product_id=product["id"],
            quantity=1,
            customer_reference="customer-1",
            idempotency_key="test-order-001",
        )
        replay = await models.create_reseller_order(
            reseller_user_telegram_id=7001,
            reseller_api_key_id=self.key["id"],
            product_id=product["id"],
            quantity=1,
            customer_reference="customer-1",
            idempotency_key="test-order-001",
        )
        self.assertLess(result["order"]["id"], 0)
        self.assertEqual(result["order"]["delivery_type"], "api_test")
        self.assertEqual(
            result["order"]["items"][0]["account_data"],
            "VENTEBOT_API_TEST_DELIVERY_OK",
        )
        self.assertTrue(replay["idempotent"])
        self.assertAlmostEqual(await models.get_wallet_balance(7001), 0.99)
        with self.assertRaisesRegex(ValueError, "Idempotency key"):
            await models.create_reseller_order(
                reseller_user_telegram_id=7001,
                reseller_api_key_id=self.key["id"],
                product_id=product["id"],
                quantity=1,
                customer_reference="different-customer",
                idempotency_key="test-order-001",
            )

    async def test_api_test_product_has_no_hourly_purchase_cap(self):
        product = models.get_reseller_test_product()
        self.assertIsNotNone(product)

        order_ids = []
        for index in range(7):
            result = await models.create_reseller_order(
                reseller_user_telegram_id=7001,
                reseller_api_key_id=self.key["id"],
                product_id=product["id"],
                quantity=1,
                customer_reference=f"unlimited-test-{index}",
                idempotency_key=f"unlimited-test-order-{index}",
            )
            order_ids.append(result["order"]["id"])

        self.assertEqual(len(set(order_ids)), 7)
        self.assertAlmostEqual(await models.get_wallet_balance(7001), 0.93)

    async def test_api_test_product_is_authenticated_tenant_scoped_and_balance_safe(
        self,
    ):
        product = models.get_reseller_test_product()
        self.assertIsNotNone(product)
        await models.get_or_create_user(7002, "other-reseller", "Other")
        other_key = await models.create_reseller_api_key(7002, "Other bot")

        with self.assertRaisesRegex(ValueError, "Product unavailable"):
            await models.create_reseller_order(
                reseller_user_telegram_id=7001,
                product_id=product["id"],
                quantity=1,
                idempotency_key="missing-api-identity",
            )
        with self.assertRaisesRegex(ValueError, "Insufficient wallet balance"):
            await models.create_reseller_order(
                reseller_user_telegram_id=7002,
                reseller_api_key_id=other_key["id"],
                product_id=product["id"],
                quantity=1,
                idempotency_key="no-balance-test",
            )
        self.assertAlmostEqual(await models.get_wallet_balance(7002), 0.0)

        result = await models.create_reseller_order(
            reseller_user_telegram_id=7001,
            reseller_api_key_id=self.key["id"],
            product_id=product["id"],
            quantity=1,
            idempotency_key="tenant-owner-test",
        )
        self.assertIsNone(await models.get_reseller_order(7002, result["order"]["id"]))

        transport = httpx.ASGITransport(app=bot.api)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/api/reseller/products")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "MISSING_API_KEY")

    async def test_webhook_url_rejects_local_network_targets(self):
        with self.assertRaisesRegex(ValueError, "public IP"):
            await validate_webhook_url("https://127.0.0.1/webhook")
        with self.assertRaisesRegex(ValueError, "HTTPS"):
            await validate_webhook_url("http://example.com/webhook")

    async def test_security_settings_are_persisted_without_exposing_key_hash(self):
        updated = await models.update_reseller_api_security(
            self.key["id"],
            user_telegram_id=7001,
            ip_allowlist=["203.0.113.10/32"],
            webhook_url="https://example.com/webhook",
            webhook_enabled=True,
            rotate_webhook_secret=True,
        )
        self.assertEqual(updated["ip_allowlist"], ["203.0.113.10/32"])
        listed = await models.list_reseller_api_keys()
        self.assertEqual(listed[0]["ip_allowlist"], ["203.0.113.10/32"])
        self.assertNotIn("key_hash", listed[0])
        self.assertNotIn("webhook_secret_salt", listed[0])

    async def test_authenticated_api_catalog_and_deposit_flow(self):
        provider_payment = {
            "payment_id": "api-deposit-payment-1",
            "payment_status": "waiting",
            "pay_amount": 2.01,
            "pay_currency": "usdtbsc",
            "pay_address": "0x2222222222222222222222222222222222222222",
        }
        transport = httpx.ASGITransport(app=bot.api)
        headers = {"X-Reseller-Key": self.key["api_key"]}
        with (
            patch("services.nowpayments.is_nowpayments_configured", return_value=True),
            patch("services.nowpayments.get_minimum_amount", AsyncMock(return_value={"min_amount": 0.1})),
            patch("services.nowpayments.create_payment", AsyncMock(return_value=provider_payment)),
            patch("handlers.payment._nowpayments_callback_url", return_value="https://example.com/webhooks/nowpayments"),
        ):
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                catalog_response = await client.get("/api/reseller/products", headers=headers)
                deposit_response = await client.post(
                    "/api/reseller/wallet/deposits",
                    headers=headers,
                    json={
                        "amount_usd": 2,
                        "network": "BEP20",
                        "idempotency_key": "api-deposit-001",
                        "reference": "checkout-api",
                    },
                )
                deposit_id = deposit_response.json()["deposit"]["deposit_id"]
                status_response = await client.get(
                    f"/api/reseller/wallet/deposits/{deposit_id}?refresh=false",
                    headers=headers,
                )

        self.assertEqual(catalog_response.status_code, 200)
        api_products = [
            product for product in catalog_response.json()["products"]
            if product.get("api_test")
        ]
        self.assertEqual(len(api_products), 1)
        self.assertEqual(deposit_response.status_code, 201)
        self.assertEqual(deposit_response.json()["deposit"]["status"], "WAITING")
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.json()["deposit"]["deposit_id"], deposit_id)


class ResellerSecurityHelperTests(unittest.TestCase):
    def test_ip_rules_and_webhook_signature(self):
        rules = normalize_ip_allowlist(["203.0.113.10", "2001:db8::/64"])
        self.assertEqual(rules[0], "203.0.113.10/32")
        self.assertTrue(ip_is_allowed("203.0.113.10", rules))
        self.assertFalse(ip_is_allowed("203.0.113.11", rules))
        body = canonical_webhook_body({"event_type": "deposit.credited", "value": 1})
        first = sign_webhook_body("secret", 1234, body)
        second = sign_webhook_body("secret", 1234, body)
        self.assertEqual(first, second)
        self.assertTrue(first.startswith("v1="))


if __name__ == "__main__":
    unittest.main()
