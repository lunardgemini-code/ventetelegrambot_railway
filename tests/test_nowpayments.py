import asyncio
import json
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

import httpx

import bot
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

    async def test_payment_review_can_be_audited_and_dismissed(self):
        await models.save_nowpayments_update({
            "payment_id": self.payment_id,
            "payment_status": "finished",
            "order_id": str(self.order["id"]),
            "pay_amount": 5,
            "actually_paid": 4,
            "pay_currency": "usdtbsc",
        })
        result = await models.finalize_nowpayments_payment(self.payment_id)
        self.assertEqual(result["action"], "review_required")

        review = await models.get_payment_review_items(category="underpaid")
        self.assertEqual(review["summary"]["underpaid"], 1)
        self.assertEqual(review["items"][0]["payment_id"], self.payment_id)

        await models.record_payment_review_action(
            "order",
            self.payment_id,
            "dismiss",
            note="Customer abandoned the balance",
            actor="test-admin",
        )
        unresolved = await models.get_payment_review_items(category="underpaid")
        resolved = await models.get_payment_review_items(category="underpaid", include_resolved=True)
        self.assertEqual(unresolved["summary"]["all"], 0)
        self.assertEqual(unresolved["items"], [])
        self.assertEqual(len(resolved["items"]), 1)
        self.assertTrue(resolved["items"][0]["resolved"])

    async def test_payment_review_accept_requires_exact_payment_confirmation(self):
        transport = httpx.ASGITransport(app=bot.api)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                f"/api/payments/review/order/{self.payment_id}/action",
                headers={"X-API-Key": bot.ADMIN_API_KEY},
                json={"action": "accept", "confirmation": "ACCEPT"},
            )
        self.assertEqual(response.status_code, 409)
        self.assertIn(self.payment_id, response.json()["detail"])

    async def test_manual_accept_is_audited_archived_and_cannot_run_twice(self):
        provider_payload = {
            "payment_id": self.payment_id,
            "payment_status": "finished",
            "order_id": str(self.order["id"]),
            "pay_amount": 5,
            "actually_paid": 4,
            "pay_currency": "usdtbsc",
        }
        await models.save_nowpayments_update(provider_payload)
        result = await models.finalize_nowpayments_payment(self.payment_id)
        self.assertEqual(result["action"], "review_required")

        transport = httpx.ASGITransport(app=bot.api)
        headers = {
            "X-API-Key": bot.ADMIN_API_KEY,
            "X-Admin-Actor": "spoofed-browser-identity",
        }
        payload = {
            "action": "accept",
            "confirmation": f"ACCEPT order {self.payment_id}",
            "note": "Approved after checking the received amount",
        }
        with (
            patch("services.nowpayments.get_payment_status", AsyncMock(return_value=provider_payload)),
            patch.object(bot, "tg_app", None),
        ):
            async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
                accepted = await client.post(
                    f"/api/payments/review/order/{self.payment_id}/action",
                    headers=headers,
                    json=payload,
                )
                duplicate = await client.post(
                    f"/api/payments/review/order/{self.payment_id}/action",
                    headers=headers,
                    json=payload,
                )
                reopen = await client.post(
                    f"/api/payments/review/order/{self.payment_id}/action",
                    headers=headers,
                    json={"action": "reopen", "note": "Should be refused"},
                )

        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(duplicate.status_code, 409)
        self.assertIn("already", duplicate.json()["detail"].lower())
        self.assertEqual(reopen.status_code, 409)

        unresolved = await models.get_payment_review_items()
        archived = await models.get_payment_review_items(
            category="accepted",
            include_resolved=True,
        )
        self.assertEqual(unresolved["summary"]["all"], 0)
        self.assertEqual(len(archived["items"]), 1)
        self.assertTrue(archived["items"][0]["resolved"])
        self.assertEqual(archived["items"][0]["last_action"], "accept")

        db = await db_module.get_db()
        try:
            rows = await (await db.execute(
                """SELECT action, actor FROM payment_review_actions
                   WHERE payment_kind = 'order' AND payment_id = ? ORDER BY id""",
                (self.payment_id,),
            )).fetchall()
        finally:
            await db.close()
        self.assertEqual([row["action"] for row in rows], ["accept_requested", "accept"])
        self.assertTrue(all(row["actor"] == "dashboard-admin" for row in rows))

    async def test_unpaid_payment_expires_after_five_minutes(self):
        await models.update_order_status(
            self.order["id"],
            "AWAITING_PAYMENT",
            expected_statuses=("PENDING",),
            payment_method="nowpayments_bep20",
        )
        db = await db_module.get_db()
        try:
            await db.execute(
                "UPDATE nowpayments_payments SET created_at = datetime('now', '-6 minutes') WHERE payment_id = ?",
                (self.payment_id,),
            )
            await db.commit()
        finally:
            await db.close()

        expired = await models.expire_stale_nowpayments_payments(timeout_seconds=300)
        order = await models.get_order(self.order["id"])
        payment = await models.get_nowpayments_payment(self.payment_id)

        self.assertEqual(expired, [self.payment_id])
        self.assertEqual(order["status"], "CANCELLED")
        self.assertEqual(payment["provider_status"], "expired")

    async def test_recent_unpaid_payment_is_not_expired(self):
        expired = await models.expire_stale_nowpayments_payments(timeout_seconds=300)
        order = await models.get_order(self.order["id"])

        self.assertEqual(expired, [])
        self.assertEqual(order["status"], "PENDING")

    async def test_active_timeout_reports_remaining_time_for_restart_recovery(self):
        db = await db_module.get_db()
        try:
            await db.execute(
                "UPDATE nowpayments_payments SET created_at = datetime('now', '-4 minutes') WHERE payment_id = ?",
                (self.payment_id,),
            )
            await db.commit()
        finally:
            await db.close()

        active = await models.list_active_nowpayments_timeouts(timeout_seconds=300)

        self.assertEqual(len(active), 1)
        self.assertEqual(int(active[0]["order_id"]), int(self.order["id"]))
        self.assertGreaterEqual(int(active[0]["remaining_seconds"]), 55)
        self.assertLessEqual(int(active[0]["remaining_seconds"]), 60)

    async def test_late_finished_payment_requires_review_before_recovery(self):
        await models.update_order_status(
            self.order["id"],
            "AWAITING_PAYMENT",
            expected_statuses=("PENDING",),
            payment_method="nowpayments_bep20",
        )
        db = await db_module.get_db()
        try:
            await db.execute(
                "UPDATE nowpayments_payments SET created_at = datetime('now', '-6 minutes') WHERE payment_id = ?",
                (self.payment_id,),
            )
            await db.commit()
        finally:
            await db.close()
        await models.expire_stale_nowpayments_payments(timeout_seconds=300)

        await models.save_nowpayments_update({
            "payment_id": self.payment_id,
            "payment_status": "finished",
            "order_id": str(self.order["id"]),
            "pay_amount": 5,
            "actually_paid": 5,
            "pay_currency": "usdtbsc",
        })
        result = await models.finalize_nowpayments_payment(self.payment_id)
        order = await models.get_order(self.order["id"])

        self.assertEqual(result["action"], "review_required")
        self.assertEqual(order["status"], "CANCELLED")
        self.assertIn("local order cancellation", result["payment"]["processing_error"])

        result = await models.finalize_nowpayments_payment(
            self.payment_id,
            allow_cancelled=True,
        )
        order = await models.get_order(self.order["id"])
        self.assertEqual(result["action"], "completed")
        self.assertEqual(order["status"], "COMPLETED")
        self.assertEqual(len(result["items"]), 1)
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

    async def test_wallet_topup_menu_shows_automated_bep20(self):
        from utils.keyboards import wallet_topup_method_keyboard

        with (
            patch.object(nowpayments, "NOWPAYMENTS_ENABLED", True),
            patch.object(nowpayments, "NOWPAYMENTS_API_KEY", "test-api-key"),
            patch.object(nowpayments, "NOWPAYMENTS_IPN_SECRET", "test-ipn-secret"),
        ):
            markup = await wallet_topup_method_keyboard("en")

        button = next(
            button
            for row in markup.inline_keyboard
            for button in row
            if button.callback_data == "topup_nowpayments"
        )
        self.assertEqual(button.text, "BEP20")
        self.assertEqual(button.icon_custom_emoji_id, "5359437015752401733")

    async def test_wallet_topup_finished_payment_credits_exactly_once(self):
        wallet_amount = 5.0
        checkout_price = nowpayments.calculate_checkout_price(wallet_amount)
        attempt = await models.prepare_nowpayments_wallet_topup(
            2001,
            wallet_amount,
            checkout_price,
        )
        payment_id = "np-wallet-double-1"
        await models.attach_nowpayments_wallet_topup(attempt["request_key"], {
            "payment_id": payment_id,
            "payment_status": "waiting",
            "pay_amount": checkout_price,
            "pay_currency": "usdtbsc",
            "pay_address": "0x2222222222222222222222222222222222222222",
        })
        saved = await models.save_nowpayments_update({
            "payment_id": payment_id,
            "payment_status": "finished",
            "order_id": attempt["request_key"],
            "pay_amount": checkout_price,
            "actually_paid": checkout_price,
            "pay_currency": "usdtbsc",
        })
        self.assertEqual(saved["payment_kind"], "wallet_topup")

        first, second = await asyncio.gather(
            models.finalize_nowpayments_wallet_topup(payment_id),
            models.finalize_nowpayments_wallet_topup(payment_id),
        )

        self.assertEqual(first["action"], "wallet_credited")
        self.assertEqual(second["action"], "wallet_credited")
        self.assertAlmostEqual(await models.get_wallet_balance(2001), wallet_amount)
        db = await db_module.get_db()
        try:
            cursor = await db.execute(
                "SELECT COUNT(*) AS count FROM wallet_transactions WHERE tx_hash = ?",
                (payment_id,),
            )
            self.assertEqual(int((await cursor.fetchone())["count"]), 1)
        finally:
            await db.close()

    async def test_wallet_topup_expires_and_reports_restart_timeout(self):
        attempt = await models.prepare_nowpayments_wallet_topup(2001, 2, 2.04)
        payment_id = "np-wallet-expire-1"
        topup = await models.attach_nowpayments_wallet_topup(attempt["request_key"], {
            "payment_id": payment_id,
            "payment_status": "waiting",
            "pay_amount": 2.04,
            "pay_currency": "usdtbsc",
            "pay_address": "0x3333333333333333333333333333333333333333",
        })
        db = await db_module.get_db()
        try:
            await db.execute(
                "UPDATE nowpayments_wallet_topups SET created_at = datetime('now', '-4 minutes') WHERE id = ?",
                (topup["id"],),
            )
            await db.commit()
        finally:
            await db.close()

        active = await models.list_active_nowpayments_wallet_topup_timeouts(timeout_seconds=300)
        self.assertEqual(len(active), 1)
        self.assertEqual(int(active[0]["topup_id"]), int(topup["id"]))
        self.assertGreaterEqual(int(active[0]["remaining_seconds"]), 55)
        self.assertLessEqual(int(active[0]["remaining_seconds"]), 60)

        db = await db_module.get_db()
        try:
            await db.execute(
                "UPDATE nowpayments_wallet_topups SET created_at = datetime('now', '-6 minutes') WHERE id = ?",
                (topup["id"],),
            )
            await db.commit()
        finally:
            await db.close()
        expired = await models.expire_stale_nowpayments_wallet_topups(timeout_seconds=300)
        saved_topup = await models.get_nowpayments_wallet_topup(topup["id"])
        self.assertEqual(expired, [payment_id])
        self.assertEqual(saved_topup["provider_status"], "expired")
        self.assertAlmostEqual(await models.get_wallet_balance(2001), 0.0)

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
