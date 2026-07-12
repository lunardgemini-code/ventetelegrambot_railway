import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from database import models
from handlers.payment import _start_redirect


class DatabaseResilienceTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_or_create_user_retries_stale_hrana_stream(self):
        expected = {
            "telegram_id": 42,
            "username": "buyer",
            "first_name": "Buyer",
            "language": "fr",
        }
        operation = AsyncMock(side_effect=[
            ValueError('Hrana: status=404 body={"error":"stream not found"}'),
            expected,
        ])
        with patch("database.models._get_or_create_user_once", operation):
            result = await models.get_or_create_user(42, "buyer", "Buyer")

        self.assertEqual(result, expected)
        self.assertEqual(operation.await_count, 2)

    async def test_get_or_create_user_does_not_retry_business_error(self):
        operation = AsyncMock(side_effect=ValueError("invalid user data"))
        with patch("database.models._get_or_create_user_once", operation):
            with self.assertRaisesRegex(ValueError, "invalid user data"):
                await models.get_or_create_user(42, "buyer", "Buyer")

        operation.assert_awaited_once()

    async def test_payment_start_fallback_only_ends_conversation(self):
        context = SimpleNamespace(user_data={
            "paying_order_id": 1,
            "paying_amount": 5,
            "paying_product_id": 9,
            "unrelated": "keep",
        })
        result = await _start_redirect(SimpleNamespace(), context)

        self.assertEqual(result, -1)
        self.assertEqual(context.user_data, {"unrelated": "keep"})


if __name__ == "__main__":
    unittest.main()
