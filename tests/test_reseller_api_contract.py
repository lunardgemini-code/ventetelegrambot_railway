import os
import unittest
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

from starlette.requests import Request


if not os.environ.get("BOT_TOKEN"):
    os.environ["BOT_TOKEN"] = "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk"

import bot
from bot import _reseller_openapi_schema


class ResellerApiContractTests(unittest.TestCase):
    def setUp(self):
        self.schema = _reseller_openapi_schema()

    def test_every_operation_documents_shared_responses_and_rate_headers(self):
        expected_responses = {"200", "401", "429", "500", "503"}
        expected_rate_headers = {
            "X-RateLimit-Limit",
            "X-RateLimit-Remaining",
            "X-RateLimit-Reset",
        }

        for path, path_item in self.schema["paths"].items():
            for method, operation in path_item.items():
                with self.subTest(path=path, method=method):
                    self.assertTrue(expected_responses.issubset(operation["responses"]))
                    self.assertTrue(
                        expected_rate_headers.issubset(
                            operation["responses"]["200"]["headers"]
                        )
                    )
                    self.assertIn("Retry-After", operation["responses"]["429"]["headers"])
                    self.assertIn("Retry-After", operation["responses"]["503"]["headers"])

    def test_catalog_and_quote_match_the_runtime_contract(self):
        product_operation = self.schema["paths"]["/api/reseller/products"]["get"]
        self.assertEqual(
            product_operation["parameters"][0]["schema"]["enum"],
            ["en", "fr", "ar", "zh", "vi", "ru"],
        )

        quote = self.schema["components"]["schemas"]["QuoteResponse"]["properties"]["quote"]
        self.assertIn("stock", quote["properties"])
        self.assertIn("pricing_type", quote["properties"])
        self.assertIn("standard_unit_price", quote["properties"])
        self.assertTrue(quote["properties"]["stock"]["nullable"])
        product = self.schema["components"]["schemas"]["Product"]
        self.assertIn("pricing_type", product["properties"])
        self.assertIn("standard_price_usd", product["properties"])
        self.assertIn("304", product_operation["responses"])
        self.assertIn("ETag", product_operation["responses"]["200"]["headers"])

    def test_order_and_wallet_edge_cases_are_documented(self):
        order_response = self.schema["paths"]["/api/reseller/orders"]["post"]["responses"]["200"]
        order_properties = order_response["content"]["application/json"]["schema"]["properties"]
        for field in ("balance_after", "unit_price", "total"):
            self.assertTrue(order_properties[field]["nullable"])

        activation_responses = self.schema["paths"][
            "/api/reseller/orders/{order_id}/activation-identifier"
        ]["post"]["responses"]
        self.assertIn("409", activation_responses)

        wallet_operation = self.schema["paths"]["/api/reseller/wallet/transactions"]["get"]
        self.assertEqual(wallet_operation["parameters"][0]["schema"]["maximum"], 100)
        wallet_items = wallet_operation["responses"]["200"]["content"]["application/json"][
            "schema"
        ]["properties"]["transactions"]["items"]
        self.assertEqual(wallet_items["$ref"], "#/components/schemas/WalletTransaction")

    def test_jit_deposit_security_and_api_test_product_are_documented(self):
        self.assertEqual(self.schema["info"]["version"], "1.2.0")
        self.assertIn("/api/reseller/wallet/deposit-methods", self.schema["paths"])
        self.assertIn("/api/reseller/wallet/deposits", self.schema["paths"])
        self.assertIn("/api/reseller/wallet/deposits/{deposit_id}", self.schema["paths"])
        self.assertIn("/api/reseller/security", self.schema["paths"])
        product = self.schema["components"]["schemas"]["Product"]
        self.assertIn("api_test", product["properties"]["delivery_type"]["enum"])
        self.assertIn("api_test", product["properties"])

    def test_english_guide_covers_languages_and_temporary_failures(self):
        guide = (Path(__file__).parents[1] / "docs" / "reseller_api.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("`vi`, and `ru`", guide)
        self.assertIn("`503`", guide)
        self.assertIn("reuse it for every retry", guide)
        self.assertIn("If-None-Match", guide)
        self.assertIn("Just-in-time BEP20 Wallet Funding", guide)
        self.assertIn("Low-cost API test product", guide)
        self.assertIn("X-Vente-Signature", guide)


class ResellerCatalogCacheTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        bot._reseller_catalog_cache.clear()
        bot._reseller_catalog_lock = None
        bot._reseller_catalog_lock_loop = None

    def request(self, **headers):
        raw_headers = [
            (name.lower().replace("_", "-").encode(), value.encode())
            for name, value in headers.items()
        ]
        return Request({
            "type": "http",
            "method": "GET",
            "path": "/api/reseller/products",
            "query_string": b"",
            "headers": raw_headers,
        })

    async def test_catalog_cache_uses_etag_without_rebuilding(self):
        payload = {"success": True, "products": [{"id": 1}]}
        builder = AsyncMock(return_value=payload)
        reseller = {
            "user_telegram_id": 42,
            "_rate_headers": {"X-RateLimit-Remaining": "58"},
        }
        with (
            patch("bot._build_reseller_catalog", builder),
            patch("database.models.get_catalog_cache_generation", return_value=7),
            patch(
                "database.models.apply_reseller_special_prices_to_catalog",
                AsyncMock(side_effect=lambda payload, _user_id: payload),
            ),
        ):
            first = await bot.api_reseller_products(
                self.request(), lang="en", reseller=reseller
            )
            etag = first.headers["etag"]
            second = await bot.api_reseller_products(
                self.request(if_none_match=etag), lang="en", reseller=reseller
            )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(json.loads(first.body), payload)
        self.assertEqual(first.headers["x-ratelimit-remaining"], "58")
        self.assertEqual(second.status_code, 304)
        self.assertEqual(second.headers["x-ratelimit-remaining"], "58")
        builder.assert_awaited_once_with("en")

    async def test_catalog_uses_stale_snapshot_when_refresh_fails(self):
        bot._reseller_catalog_cache["en"] = {
            "payload": {"success": True, "products": [{"id": 9}]},
            "etag": '"old"',
            "generation": 1,
            "created_at": 0.0,
        }
        with (
            patch("bot.RESELLER_CATALOG_CACHE_SECONDS", 1),
            patch("bot.time.monotonic", return_value=100.0),
            patch("database.models.get_catalog_cache_generation", return_value=1),
            patch("bot._build_reseller_catalog", AsyncMock(side_effect=RuntimeError("offline"))),
            patch(
                "database.models.apply_reseller_special_prices_to_catalog",
                AsyncMock(side_effect=lambda payload, _user_id: payload),
            ),
        ):
            response = await bot.api_reseller_products(
                self.request(), lang="en", reseller={"user_telegram_id": 42}
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["x-catalog-stale"], "true")
        self.assertEqual(json.loads(response.body)["products"][0]["id"], 9)


if __name__ == "__main__":
    unittest.main()
