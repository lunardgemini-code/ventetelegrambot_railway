import os
import unittest
from pathlib import Path


if not os.environ.get("BOT_TOKEN"):
    os.environ["BOT_TOKEN"] = "123456:ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijk"

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
                    self.assertEqual(
                        set(operation["responses"]["200"]["headers"]),
                        expected_rate_headers,
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
        self.assertTrue(quote["properties"]["stock"]["nullable"])

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

    def test_english_guide_covers_languages_and_temporary_failures(self):
        guide = (Path(__file__).parents[1] / "docs" / "reseller_api.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("`vi`, and `ru`", guide)
        self.assertIn("`503`", guide)
        self.assertIn("reuse it for every retry", guide)


if __name__ == "__main__":
    unittest.main()
