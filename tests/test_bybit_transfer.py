import time
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from handlers import payment as payment_handler
from handlers import wallet as wallet_handler
from services import bybit_transfer
from utils.keyboards import payment_method_keyboard, wallet_topup_method_keyboard
from utils.locales import t


class BybitTransferTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        bybit_transfer.reset_bybit_transfer_cache()

    async def asyncTearDown(self):
        bybit_transfer.reset_bybit_transfer_cache()
        await bybit_transfer.close_bybit_transfer_client()

    def _deposit(self, **overrides):
        row = {
            "txID": "77c37e5c-d9fa-41e5-bd13-c9b59d95",
            "amount": "5.00",
            "coin": "USDT",
            "status": 2,
            "createdTime": str(int(time.time())),
            "fromMemberId": "118027304",
        }
        row.update(overrides)
        return row

    async def test_valid_internal_transfer_is_verified(self):
        with (
            patch.object(bybit_transfer, "is_bybit_transfer_configured", return_value=True),
            patch.object(
                bybit_transfer,
                "_get_internal_deposit",
                AsyncMock(return_value=[self._deposit()]),
            ),
        ):
            result = await bybit_transfer.verify_payment(
                "77c37e5c-d9fa-41e5-bd13-c9b59d95", 5
            )

        self.assertTrue(result["verified"])
        self.assertEqual(result["transaction"]["fromMemberId"], "118027304")

    async def test_underpayment_is_rejected(self):
        with (
            patch.object(bybit_transfer, "is_bybit_transfer_configured", return_value=True),
            patch.object(
                bybit_transfer,
                "_get_internal_deposit",
                AsyncMock(return_value=[self._deposit(amount="4.50")]),
            ),
        ):
            result = await bybit_transfer.verify_payment(
                "77c37e5c-d9fa-41e5-bd13-c9b59d95", 5
            )

        self.assertFalse(result["verified"])
        self.assertEqual(result["error_key"], "bybit_transfer_underpaid")

    async def test_old_transfer_is_rejected(self):
        old_time = int(time.time() - bybit_transfer.MAX_PAYMENT_AGE_SECONDS - 1)
        with (
            patch.object(bybit_transfer, "is_bybit_transfer_configured", return_value=True),
            patch.object(
                bybit_transfer,
                "_get_internal_deposit",
                AsyncMock(return_value=[self._deposit(createdTime=str(old_time))]),
            ),
        ):
            result = await bybit_transfer.verify_payment(
                "77c37e5c-d9fa-41e5-bd13-c9b59d95", 5
            )

        self.assertFalse(result["verified"])
        self.assertEqual(result["error_key"], "bybit_transfer_too_old")

    async def test_button_is_available_when_transfer_is_configured(self):
        with (
            patch(
                "services.bybit_transfer.is_bybit_transfer_configured",
                return_value=True,
            ),
            patch("services.nowpayments.is_nowpayments_configured", return_value=True),
            patch("services.crypto_pay.is_crypto_pay_configured", return_value=True),
            patch("database.models.get_setting", AsyncMock(return_value=None)),
        ):
            markup = await payment_method_keyboard(42, "en", 0, allow_bybit=True)

        callbacks = [
            button.callback_data
            for row in markup.inline_keyboard
            for button in row
            if button.callback_data
        ]
        self.assertIn("pay_bybit:42", callbacks)
        payment_callbacks = [
            callback
            for callback in callbacks
            if callback.startswith(
                (
                    "pay_binance:",
                    "pay_bybit:",
                    "pay_nowpayments:",
                    "pay_cryptopay:",
                )
            )
        ]
        self.assertEqual(
            payment_callbacks,
            [
                "pay_binance:42",
                "pay_bybit:42",
                "pay_nowpayments:42",
                "pay_cryptopay:42",
            ],
        )
        bybit_button = next(
            button
            for row in markup.inline_keyboard
            for button in row
            if button.callback_data == "pay_bybit:42"
        )
        self.assertEqual(bybit_button.icon_custom_emoji_id, "5370607602919031217")

    async def test_button_is_hidden_for_regular_users(self):
        with (
            patch(
                "services.bybit_transfer.is_bybit_transfer_configured",
                return_value=True,
            ),
            patch("services.nowpayments.is_nowpayments_configured", return_value=True),
            patch("services.crypto_pay.is_crypto_pay_configured", return_value=True),
            patch("database.models.get_setting", AsyncMock(return_value=None)),
        ):
            markup = await payment_method_keyboard(42, "en", 0)

        callbacks = [
            button.callback_data
            for row in markup.inline_keyboard
            for button in row
            if button.callback_data
        ]
        self.assertNotIn("pay_bybit:42", callbacks)

    async def test_wallet_topup_button_is_admin_only(self):
        with (
            patch(
                "services.bybit_transfer.is_bybit_transfer_configured",
                return_value=True,
            ),
            patch("services.nowpayments.is_nowpayments_configured", return_value=True),
            patch("services.crypto_pay.is_crypto_pay_configured", return_value=True),
            patch("database.models.get_setting", AsyncMock(return_value=None)),
        ):
            admin_markup = await wallet_topup_method_keyboard(
                "en", allow_bybit=True
            )
            customer_markup = await wallet_topup_method_keyboard("en")

        admin_callbacks = [
            button.callback_data
            for row in admin_markup.inline_keyboard
            for button in row
            if button.callback_data
        ]
        customer_callbacks = [
            button.callback_data
            for row in customer_markup.inline_keyboard
            for button in row
            if button.callback_data
        ]
        self.assertIn("topup_bybit", admin_callbacks)
        self.assertNotIn("topup_bybit", customer_callbacks)
        payment_callbacks = [
            callback
            for callback in admin_callbacks
            if callback in {
                "topup_binance",
                "topup_bybit",
                "topup_nowpayments",
                "topup_cryptopay",
            }
        ]
        self.assertEqual(
            payment_callbacks,
            [
                "topup_binance",
                "topup_bybit",
                "topup_nowpayments",
                "topup_cryptopay",
            ],
        )
        bybit_button = next(
            button
            for row in admin_markup.inline_keyboard
            for button in row
            if button.callback_data == "topup_bybit"
        )
        self.assertEqual(bybit_button.icon_custom_emoji_id, "5370607602919031217")

    async def test_direct_callback_is_rejected_for_regular_users(self):
        query = SimpleNamespace(
            data="pay_bybit:42",
            answer=AsyncMock(),
            message=SimpleNamespace(chat_id=123),
        )
        update = SimpleNamespace(
            callback_query=query,
            effective_user=SimpleNamespace(id=123),
        )
        context = SimpleNamespace(user_data={})
        safe_edit = AsyncMock()

        with (
            patch.object(payment_handler, "get_user_lang", AsyncMock(return_value="en")),
            patch.object(
                payment_handler,
                "get_order",
                AsyncMock(return_value={"id": 42, "user_telegram_id": 123}),
            ),
            patch.object(payment_handler, "is_admin", return_value=False),
            patch.object(payment_handler, "safe_edit_message_text", safe_edit),
        ):
            await payment_handler.pay_with_bybit_transfer(update, context)

        safe_edit.assert_awaited_once_with(query, t("access_denied", "en"))
        self.assertEqual(context.user_data, {})

    async def test_wallet_topup_callback_is_rejected_for_regular_users(self):
        query = SimpleNamespace(data="topup_bybit", answer=AsyncMock())
        update = SimpleNamespace(
            callback_query=query,
            effective_user=SimpleNamespace(id=123),
        )
        context = SimpleNamespace(user_data={"wallet_topup_amount": 2})
        safe_edit = AsyncMock()

        with (
            patch.object(wallet_handler, "get_user_lang", AsyncMock(return_value="en")),
            patch.object(wallet_handler, "is_admin", return_value=False),
            patch.object(wallet_handler, "safe_edit_message_text", safe_edit),
        ):
            await wallet_handler.wallet_topup_method_bybit(update, context)

        safe_edit.assert_awaited_once_with(query, t("access_denied", "en"))

    async def test_wallet_topup_credits_verified_received_amount(self):
        message = SimpleNamespace(
            text="01d90e5a-dba0-4156-81ea-59a7c589",
            reply_text=AsyncMock(),
        )
        update = SimpleNamespace(
            message=message,
            effective_user=SimpleNamespace(id=123),
        )
        context = SimpleNamespace(user_data={"wallet_topup_amount": 2})
        credit = AsyncMock(return_value={"credited": True, "balance_after": 22.1})

        with (
            patch.object(wallet_handler, "get_user_lang", AsyncMock(return_value="en")),
            patch.object(wallet_handler, "is_admin", return_value=True),
            patch.object(
                bybit_transfer,
                "verify_payment",
                AsyncMock(return_value={
                    "verified": True,
                    "transaction": {
                        "transactionId": "01d90e5a-dba0-4156-81ea-59a7c589",
                        "amount": 2.1,
                        "fromMemberId": "566919137",
                    },
                }),
            ),
            patch.object(wallet_handler, "credit_wallet_from_bybit_transaction", credit),
        ):
            state = await wallet_handler.wallet_verify_bybit(update, context)

        self.assertEqual(state, wallet_handler.ConversationHandler.END)
        credit.assert_awaited_once_with(
            "01d90e5a-dba0-4156-81ea-59a7c589",
            123,
            2.1,
            "Bybit Transfer: 01d90e5a-dba0-4156-81ea-59a7c589",
            "566919137",
        )
        self.assertNotIn("wallet_topup_amount", context.user_data)


if __name__ == "__main__":
    unittest.main()
