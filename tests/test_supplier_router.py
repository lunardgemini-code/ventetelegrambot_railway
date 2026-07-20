import unittest
from unittest.mock import AsyncMock, patch

import httpx

from services.supplier_multi_api import (
    _request,
    _normalize_akunding_products,
    _normalize_cat_products,
    _normalize_goldfish_products,
    _normalize_pixverify_products,
    _normalize_robotic_product,
    _normalize_tunvn_products,
    _normalize_zoom_products,
    _delivery_values,
    _purchase_idempotency_key,
    purchase,
)
from services.supplier_api import SupplierAPIError
from services.supplier_identity import extract_supplier_identity
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

    def test_zoom_catalog_normalization(self):
        rows = _normalize_zoom_products({"products": [{
            "id": "002", "name": "Gemini", "price": 0.72,
            "stock": 9, "currency": "USDT",
        }]}, 1)
        self.assertEqual(rows[0]["external_product_id"], "002")
        self.assertEqual(rows[0]["base_price"], 0.72)
        self.assertEqual(rows[0]["remote_stock"], 9)

    def test_vnd_catalogs_are_converted_and_input_products_are_filtered(self):
        cat = _normalize_cat_products({"data": [{
            "id": 7, "name": "CapCut", "price": 25000, "stock": 4,
        }]}, 25000)
        goldfish = _normalize_goldfish_products([
            {"id": "stock", "name": "Stock", "price": 50000, "quantity": 2},
            {"id": "activation", "name": "Activation", "price": 50000,
             "quantity": None, "requires_input": True},
        ], 25000)
        self.assertEqual(cat[0]["base_price"], 1.0)
        self.assertEqual(goldfish[0]["base_price"], 2.0)
        self.assertEqual([row["external_product_id"] for row in goldfish], ["stock"])

    def test_robotic_variants_are_flattened_into_purchasable_products(self):
        rows = _normalize_robotic_product({"data": {
            "id": "parent", "title": "ChatGPT", "description": "Account",
            "variants": [{
                "id": "variant-1", "title": "Plus 30D",
                "prices": {"usd": 0.77, "vnd": 20000},
                "in_stock": True, "available_quantity": 5,
            }],
        }}, 25000)
        self.assertEqual(rows[0]["external_product_id"], "variant-1")
        self.assertEqual(rows[0]["name"], "ChatGPT - Plus 30D")
        self.assertEqual(rows[0]["base_price"], 0.77)

    def test_purchase_idempotency_is_stable_per_internal_order(self):
        provider = {"code": "zoom"}
        left = _purchase_idempotency_key(provider, "002", 1, "VenteBot order #42")
        right = _purchase_idempotency_key(provider, "002", 1, "VenteBot order #42")
        other = _purchase_idempotency_key(provider, "002", 1, "VenteBot order #43")
        self.assertEqual(left, right)
        self.assertNotEqual(left, other)

    def test_delivery_normalizer_skips_empty_alias_before_populated_alias(self):
        values = _delivery_values({
            "data": {
                "deliveredAccount": [],
                "delivered_accounts": [{"account": "user", "password": "pass"}],
            }
        })
        self.assertEqual(len(values), 1)

    def test_signature_never_contains_credentials(self):
        signature = extract_product_signature("Gemini 18 months", "private activation")
        self.assertEqual(signature["family"], "gemini")
        self.assertEqual(signature["duration_months"], 18)

    def test_supplier_identity_only_copies_whitelisted_names(self):
        identity = extract_supplier_identity({
            "botSource": "Store One",
            "requester": {"name": "Rayan", "api_key": "never-copy-this"},
            "api_key": "also-never-copy-this",
        })
        self.assertEqual(identity["provider_name"], "Store One")
        self.assertEqual(identity["account_name"], "Rayan")
        self.assertNotIn("api_key", identity)

    def test_generic_payment_source_is_not_used_as_bot_name(self):
        identity = extract_supplier_identity({
            "botSource": "binance",
            "requester": {"name": "RayanKL"},
        })
        self.assertEqual(identity["provider_name"], "RayanKL")
        self.assertEqual(identity["bot_source"], "binance")


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

    async def test_zoom_purchase_sends_idempotency_header_and_delivers_codes(self):
        provider = {
            "code": "zoom", "name": "Zoom", "adapter": "zoom",
            "base_url": "https://supplier.example", "api_key": "secret",
        }
        request = AsyncMock(return_value={
            "success": True, "order_id": "remote-1", "codes": ["a", "b"],
        })
        with patch("services.supplier_multi_api._request", request):
            result = await purchase(
                provider, "002", 2, buyer_info="VenteBot order #88"
            )
        self.assertEqual(
            [item["account_data"] for item in result["items"]], ["a", "b"]
        )
        kwargs = request.await_args.kwargs
        self.assertTrue(kwargs["headers"]["Idempotency-Key"].startswith("ventebot-"))


if __name__ == "__main__":
    unittest.main()
