import asyncio
import json
import unittest
from unittest.mock import AsyncMock, patch

from services import supplier_registry, supplier_multi_api


class PixelGeminiSupplierTests(unittest.IsolatedAsyncioTestCase):
    def test_provider_registration(self):
        provider = supplier_registry.get_supplier_provider("pixel")
        self.assertEqual(provider["code"], "pixel")
        self.assertEqual(provider["name"], "Pixel Gemini")
        self.assertEqual(provider["base_url"], "https://pixel.wxie.de")
        self.assertEqual(provider["adapter"], "pixel")

    async def test_get_balance_normalizes_balance_points(self):
        fake_response = {
            "generated_at": "2026-07-28T14:00:00Z",
            "user_id": 12345,
            "balance": {
                "balance_points": 137.0,
                "total_success_count": 12,
            }
        }
        with patch("services.supplier_multi_api._request", AsyncMock(return_value=fake_response)):
            bal = await supplier_registry.get_supplier_balance("pixel", units_per_usd=1.0, force=True)
            self.assertEqual(bal["balance"], 137.0)
            self.assertEqual(bal["currency"], "PTS")
            self.assertIn("137.0 PTS", bal["balance_text"])

    async def test_list_products_returns_pixel_task_modes(self):
        prods = await supplier_registry.list_supplier_products("pixel", units_per_usd=1.0)
        self.assertEqual(len(prods), 2)
        ids = [p["id"] for p in prods]
        self.assertIn("extract_link_fast", ids)
        self.assertIn("extract_link_normal", ids)

    async def test_purchase_submits_task_payload(self):
        fake_submit_resp = {
            "task": {
                "id": 987,
                "display_id": "⚡#987",
                "task_mode": "extract_link",
                "channel": "fast",
                "status": "pending",
            }
        }
        with patch("services.supplier_multi_api._request", AsyncMock(return_value=fake_submit_resp)) as mock_req:
            res = await supplier_registry.purchase_supplier_product(
                "pixel",
                "extract_link_fast",
                1,
                buyer_info="test@gmail.com|password123|SECRET2FA32CHARS",
            )
            self.assertEqual(res["order_id"], "987")
            self.assertEqual(len(res["items"]), 1)
            mock_req.assert_called_once()
            args, kwargs = mock_req.call_args
            self.assertEqual(args[1], "POST")
            self.assertEqual(args[2], "/api/v1/submit")
            self.assertEqual(kwargs["json"]["email"], "test@gmail.com")
            self.assertEqual(kwargs["json"]["password"], "password123")
            self.assertEqual(kwargs["json"]["twofa_url"], "SECRET2FA32CHARS")
            self.assertEqual(kwargs["json"]["task_mode"], "extract_link")
            self.assertEqual(kwargs["json"]["channel"], "fast")


if __name__ == "__main__":
    unittest.main()
