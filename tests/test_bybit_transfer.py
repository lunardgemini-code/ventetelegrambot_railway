import time
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from handlers import payment as payment_handler
from services import bybit_transfer
from utils.keyboards import payment_method_keyboard
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

    async def test_button_is_hidden_for_regular_users(self):
        with (
            patch(
                "services.bybit_transfer.is_bybit_transfer_configured",
                return_value=True,
            ),
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


if __name__ == "__main__":
    unittest.main()
