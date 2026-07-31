import time
import unittest
from unittest.mock import AsyncMock, patch

from services import bybit_transfer
from utils.keyboards import payment_method_keyboard


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
            markup = await payment_method_keyboard(42, "en", 0)

        callbacks = [
            button.callback_data
            for row in markup.inline_keyboard
            for button in row
            if button.callback_data
        ]
        self.assertIn("pay_bybit:42", callbacks)


if __name__ == "__main__":
    unittest.main()
