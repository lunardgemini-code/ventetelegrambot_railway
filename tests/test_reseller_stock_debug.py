from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

import bot
from bot import verify_reseller_key


class ResellerStockDebugTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = TestClient(bot.api)

    async def test_reseller_product_stock_check_endpoint(self):
        fake_product = {
            "id": 12,
            "name": "Gemini Account",
            "delivery_type": "stock",
            "is_active": 1,
            "is_deleted": 0,
        }
        cursor = SimpleNamespace(
            fetchone=AsyncMock(return_value={"total": 5, "unsold": 3})
        )
        fake_db = SimpleNamespace(
            execute=AsyncMock(return_value=cursor),
            close=AsyncMock(),
        )
        reseller_key = {
            "id": 1,
            "user_telegram_id": 999,
            "key_hash": "test",
            "is_active": 1,
            "wallet_balance": 100.0,
        }
        bot.api.dependency_overrides[verify_reseller_key] = lambda: reseller_key
        try:
            with patch("database.models.get_product", AsyncMock(return_value=fake_product)), \
                 patch("database.models.get_db", AsyncMock(return_value=fake_db)), \
                 patch("database.models.get_all_stock_counts", AsyncMock(return_value={12: 3})):
                response = self.client.get("/api/reseller/products/12/stock", headers={"X-API-Key": "test"})
                self.assertEqual(response.status_code, 200)
                data = response.json()
                self.assertEqual(data["product_id"], 12)
                self.assertEqual(data["delivery_type"], "stock")
                self.assertEqual(data["unsold_stock_items"], 3)
                self.assertEqual(data["available_stock"], 3)
        finally:
            bot.api.dependency_overrides.clear()


if __name__ == "__main__":
    unittest.main()
