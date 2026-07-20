import unittest
from unittest.mock import AsyncMock, patch

import httpx

from services.supplier_multi_api import (
    _request,
    _normalize_akunding_products,
    _normalize_pixverify_products,
    _normalize_tunvn_products,
)
from services.supplier_api import SupplierAPIError
from services.supplier_registry import list_supplier_providers
from services.supplier_router import (
    compatibility_score,
    extract_product_signature,
    rank_supplier_candidates,
)


class SupplierRouterUnitTests(unittest.TestCase):
    def test_public_registry_never_exposes_api_keys(self):
        self.assertTrue(list_supplier_providers())
        self.assertTrue(all("api_key" not in provider for provider in list_supplier_providers()))

    def test_matching_rejects_different_durations(self):
        left = {"name": "Gemini AI Pro 18 months", "description": "activation on your account"}
        right = {"name": "Gemini AI Pro 12 months", "description": "activation on your account"}
        score, compatible, reason = compatibility_score(left, right)
        self.assertFalse(compatible)
        self.assertEqual(score, 0)
        self.assertIn("duration", reason)

    def test_matching_rejects_account_activation_mismatch(self):
        left = {"name": "ChatGPT Plus 1 month account", "description": "email password"}
        right = {"name": "ChatGPT Plus 1 month activation", "description": "activate on your account"}
        self.assertFalse(compatibility_score(left, right)[1])

    def test_ranker_prefers_lower_cost_reliable_offer(self):
        ranked = rank_supplier_candidates([
            {"supplier_code": "slow", "base_price": 1.20, "completed_orders": 10, "failed_orders": 4},
            {"supplier_code": "best", "base_price": 0.90, "completed_orders": 20, "failed_orders": 0},
            {"supplier_code": "loss", "base_price": 2.10, "completed_orders": 100},
        ], 2.0)
        self.assertEqual([row["supplier_code"] for row in ranked], ["best", "slow"])

    def test_tunvn_catalog_normalization(self):
        rows = _normalize_tunvn_products({"products": [{
            "id": 37, "name": "Capcut", "price_vnd": 42000,
            "price_usdt": 1.6, "stock": 101, "description": "Team",
        }]}, {})
        self.assertEqual(rows[0]["external_product_id"], "37")
        self.assertEqual(rows[0]["base_price"], 1.6)
        self.assertEqual(rows[0]["source_currency"], "VND")

    def test_akunding_and_pixverify_catalog_normalization(self):
        akunding = _normalize_akunding_products([{
            "id": 27, "name": "Gemini", "base_price": 0.65,
            "stock": 192, "description": "Link", "features": "18 months",
        }], {})
        pix = _normalize_pixverify_products({"categories": [{
            "id": 22, "name": "Coursera", "discounted_price": 2,
            "price_per_unit": 3, "stock": {"available": 12},
        }]}, {})
        self.assertEqual(akunding[0]["remote_stock"], 192)
        self.assertIn("18 months", akunding[0]["description"])
        self.assertEqual(pix[0]["base_price"], 2)
        self.assertEqual(pix[0]["remote_stock"], 12)

    def test_signature_never_contains_credentials(self):
        signature = extract_product_signature("Gemini 18 months", "private activation")
        self.assertEqual(signature["family"], "gemini")
        self.assertEqual(signature["duration_months"], 18)


class SupplierRouterHTTPTests(unittest.IsolatedAsyncioTestCase):
    async def test_post_server_error_has_unknown_outcome(self):
        response = httpx.Response(
            500,
            json={"error": "temporary"},
            request=httpx.Request("POST", "https://supplier.example/api/order"),
        )
        client = AsyncMock()
        client.request.return_value = response
        provider = {
            "code": "test", "name": "Test", "base_url": "https://supplier.example",
            "api_key": "secret", "auth_mode": "header", "auth_header": "X-API-Key",
        }
        with patch("services.supplier_multi_api._client", AsyncMock(return_value=client)):
            with self.assertRaises(SupplierAPIError) as raised:
                await _request(provider, "POST", "/api/order", json={"product_id": 1})
        self.assertTrue(raised.exception.outcome_unknown)


if __name__ == "__main__":
    unittest.main()
