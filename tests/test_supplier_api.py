import asyncio
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from database import db as db_module
from database.db import init_db
from database import models
from database.suppliers import (
    calculate_supplier_price,
    get_supplier_dashboard,
    sync_supplier_products,
    update_supplier_product,
    update_supplier_product_descriptions,
    update_supplier_settings,
)
from services.delivery import deliver_order
from services.supplier_api import (
    SupplierAPIError,
    calculate_affordable_stock,
    normalize_balance,
    normalize_products,
    normalize_purchase,
)
from services import supplier_api
from services import nanlux_api
from services.nanlux_api import (
    normalize_nanlux_balance,
    normalize_nanlux_products,
    normalize_nanlux_purchase,
)


class SupplierAPITests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["DB_PATH"] = os.path.join(self.temp_dir.name, "supplier.db")
        db_module.TURSO_URL = ""
        db_module._sqlite_wal_configured = False
        models.clear_products_cache()
        await init_db()
        await models.get_or_create_user(3001, "supplier_buyer", "Supplier Buyer")
        await models.add_category("Products")
        self.remote_product = {
            "external_product_id": "remote-10",
            "name": "Remote account",
            "description": "Delivered by API",
            "base_price": 2.5,
            "remote_stock": 8,
            "warranty_days": 7,
            "image_url": "",
            "emoji": "📦",
            "raw_payload": {"id": "remote-10"},
        }
        await sync_supplier_products([self.remote_product])
        dashboard = await get_supplier_dashboard()
        self.mapping_id = int(dashboard["products"][0]["id"])
        mapping = await update_supplier_product(
            self.mapping_id,
            enabled=True,
            margin_type="fixed",
            margin_value=1,
        )
        self.local_product_id = int(mapping["local_product_id"])

    async def asyncTearDown(self):
        self.temp_dir.cleanup()

    def test_catalog_normalization_accepts_common_envelopes(self):
        products = normalize_products({
            "data": {
                "products": [
                    {"product_id": 7, "title": "Account", "unit_price": "1.25", "available_stock": "4"}
                ]
            }
        })
        self.assertEqual(products[0]["external_product_id"], "7")
        self.assertEqual(products[0]["name"], "Account")
        self.assertEqual(products[0]["base_price"], 1.25)
        self.assertEqual(products[0]["remote_stock"], 4)

    def test_catalog_normalization_matches_canboso_live_contract(self):
        products = normalize_products({
            "success": True,
            "walletCurrency": "USD",
            "products": [{
                "_id": "6a2cf7d94a0ce56b9db8228d",
                "product_name": "Test API",
                "emoji": "tele",
                "usdPricing": 0.01,
                "walletPricing": 0.01,
                "description": "API connection test",
                "descriptionImage": "/uploads/test.png",
                "warrantyDays": 2,
                "stats": {"total": 170, "sold": 74, "available": 96},
            }],
        })
        self.assertEqual(len(products), 1)
        self.assertEqual(products[0]["external_product_id"], "6a2cf7d94a0ce56b9db8228d")
        self.assertEqual(products[0]["base_price"], 0.01)
        self.assertEqual(products[0]["remote_stock"], 96)
        self.assertEqual(products[0]["warranty_days"], 2)
        self.assertEqual(products[0]["emoji"], "📦")
        self.assertTrue(products[0]["image_url"].endswith("/uploads/test.png"))

    def test_fixed_and_percent_margins(self):
        self.assertEqual(calculate_supplier_price(2.5, "fixed", 1), 3.5)
        self.assertEqual(calculate_supplier_price(2.5, "percent", 20), 3.0)
        self.assertEqual(calculate_supplier_price(2.5, "sale_price", 4), 4.0)

    async def test_fixed_sale_price_hides_product_when_supplier_cost_reaches_it(self):
        mapping = await update_supplier_product(
            self.mapping_id,
            enabled=True,
            margin_type="sale_price",
            margin_value=3.0,
        )
        product = await models.get_product(int(mapping["local_product_id"]))
        self.assertEqual(float(product["price_usd"]), 3.0)
        self.assertEqual(int(product["is_active"]), 1)

        await sync_supplier_products(
            [{**self.remote_product, "base_price": 3.0}]
        )
        product = await models.get_product(int(mapping["local_product_id"]))
        dashboard = await get_supplier_dashboard()
        self.assertEqual(int(product["is_active"]), 0)
        self.assertFalse(dashboard["products"][0]["price_safe"])
        with patch(
            "services.supplier_api.get_canboso_balance",
            AsyncMock(return_value={"balance": 100.0}),
        ):
            self.assertEqual(
                await models.get_stock_count(int(mapping["local_product_id"])),
                0,
            )

    def test_affordable_stock_is_capped_by_supplier_wallet(self):
        self.assertEqual(calculate_affordable_stock(20, 4, 0), 0)
        self.assertEqual(calculate_affordable_stock(20, 4, 5), 1)
        self.assertEqual(calculate_affordable_stock(2, 4, 100), 2)

    def test_purchase_normalization_matches_canboso_contract(self):
        purchase = normalize_purchase({
            "success": True,
            "orderCode": "ORDER1A2B3C4D5E",
            "deliveredAccounts": [{
                "productItemId": "item-1",
                "user": "buyer@example.com",
                "password": "secret",
                "verifyEmail": "backup@example.com",
            }],
        })
        self.assertEqual(purchase["external_order_id"], "ORDER1A2B3C4D5E")
        self.assertEqual(
            purchase["items"][0]["account_data"],
            "buyer@example.com | secret | backup@example.com",
        )

    def test_balance_normalization_matches_canboso_contract(self):
        balance = normalize_balance({
            "success": True,
            "walletCurrency": "USD",
            "balance": 2.5,
            "balanceUsd": 2.5,
            "balanceText": "$2.50",
            "updatedAt": None,
        })
        self.assertEqual(balance["currency"], "USD")
        self.assertEqual(balance["balance"], 2.5)
        self.assertEqual(balance["balance_text"], "$2.50")

    def test_nanlux_catalog_converts_vnd_cost_price_to_usd(self):
        products = normalize_nanlux_products(
            {
                "success": True,
                "data": {
                    "products": [
                        {
                            "id": 17,
                            "name": "Vietnam account",
                            "price": 30000,
                            "cost_price": 25000,
                            "stock": 6,
                            "description": "Delivered by dealer API",
                            "is_maintenance": False,
                        },
                        {
                            "id": 18,
                            "name": "Maintenance product",
                            "cost_price": 50000,
                            "stock": 20,
                            "is_maintenance": True,
                        },
                    ]
                },
            },
            25000,
        )
        self.assertEqual(products[0]["base_price"], 1.0)
        self.assertEqual(products[0]["source_price"], 25000)
        self.assertEqual(products[0]["source_currency"], "VND")
        self.assertEqual(products[0]["remote_stock"], 6)
        self.assertEqual(products[1]["remote_stock"], 0)

    def test_nanlux_balance_keeps_source_and_normalized_values(self):
        balance = normalize_nanlux_balance(
            {
                "success": True,
                "data": {
                    "name": "Rayan",
                    "balance": 50000,
                    "discount_percent": 3,
                },
            },
            25000,
        )
        self.assertEqual(balance["source_balance"], 50000)
        self.assertEqual(balance["balance"], 2.0)
        self.assertEqual(balance["dealer_name"], "Rayan")
        self.assertIn("VND", balance["balance_text"])

    def test_nanlux_purchase_normalization(self):
        purchase = normalize_nanlux_purchase(
            {
                "success": True,
                "data": {
                    "order_id": 991,
                    "items": ["login:password", {"content": "second item"}],
                },
            }
        )
        self.assertEqual(purchase["external_order_id"], "991")
        self.assertEqual(
            [item["account_data"] for item in purchase["items"]],
            ["login:password", "second item"],
        )

    async def test_nanlux_purchase_uses_dealer_contract(self):
        request = AsyncMock(
            return_value={
                "success": True,
                "data": {"order_id": 992, "items": ["delivered"]},
            }
        )
        with patch("services.nanlux_api._request", request):
            result = await nanlux_api.purchase_nanlux_product(
                "17", 1, buyer_info="VenteBot order #20"
            )
        request.assert_awaited_once_with(
            "POST",
            "/api/dealer/buy",
            json={
                "product_id": 17,
                "quantity": 1,
                "buyer_info": "VenteBot order #20",
            },
        )
        self.assertEqual(result["items"][0]["account_data"], "delivered")

    async def test_concurrent_balance_reads_share_one_supplier_request(self):
        supplier_api._BALANCE_CACHE = None
        request = AsyncMock(return_value={
            "success": True,
            "walletCurrency": "USD",
            "balance": 5.0,
        })
        with patch("services.supplier_api._request", request):
            results = await asyncio.gather(*(
                supplier_api.get_canboso_balance() for _ in range(5)
            ))

        self.assertEqual(request.await_count, 1)
        self.assertTrue(all(result["balance"] == 5.0 for result in results))
        supplier_api._BALANCE_CACHE = None

    async def test_stale_supplier_balance_is_served_during_outage(self):
        supplier_api._BALANCE_CACHE = (0.0, {"balance": 7.5, "currency": "USD"})
        with (
            patch("services.supplier_api.time.monotonic", return_value=1000.0),
            patch(
                "services.supplier_api._request",
                AsyncMock(side_effect=SupplierAPIError("supplier offline")),
            ),
        ):
            result = await supplier_api.get_canboso_balance(force=True)

        self.assertEqual(result["balance"], 7.5)
        self.assertTrue(result["stale"])
        supplier_api._BALANCE_CACHE = None

    async def test_selected_product_uses_remote_stock_and_margin(self):
        product = await models.get_product(self.local_product_id)
        self.assertEqual(product["delivery_type"], "supplier_api")
        self.assertAlmostEqual(float(product["price_usd"]), 3.5)
        with patch("services.supplier_api.get_canboso_balance", AsyncMock(return_value={"balance": 5.0})):
            self.assertEqual(await models.get_stock_count(self.local_product_id), 2)

    async def test_global_margin_and_master_switch_update_local_product(self):
        await update_supplier_product(
            self.mapping_id,
            enabled=True,
            margin_type="inherit",
            margin_value=None,
        )
        await update_supplier_settings(enabled=True, margin_type="percent", margin_value=20)
        product = await models.get_product(self.local_product_id)
        self.assertAlmostEqual(float(product["price_usd"]), 3.0)
        self.assertEqual(int(product["is_active"]), 1)

        await update_supplier_settings(enabled=False, margin_type="percent", margin_value=20)
        product = await models.get_product(self.local_product_id)
        self.assertEqual(int(product["is_active"]), 0)

    async def test_multilingual_descriptions_survive_supplier_resync(self):
        descriptions = {
            "en": "Custom English description",
            "fr": "Description personnalisée en français",
            "ar": "وصف عربي مخصص",
            "zh": "自定义中文描述",
            "vi": "Mô tả tiếng Việt tùy chỉnh",
            "ru": "Пользовательское описание",
        }
        await update_supplier_product_descriptions(self.mapping_id, descriptions)

        product = await models.get_product(self.local_product_id)
        self.assertEqual(product["description"], descriptions["en"])
        for language in ("fr", "ar", "zh", "vi", "ru"):
            self.assertEqual(product[f"description_{language}"], descriptions[language])

        refreshed = {**self.remote_product, "description": "Updated supplier description"}
        await sync_supplier_products([refreshed])
        product = await models.get_product(self.local_product_id)
        self.assertEqual(product["description"], descriptions["en"])
        self.assertEqual(product["description_fr"], descriptions["fr"])

        dashboard = await get_supplier_dashboard()
        mapping = dashboard["products"][0]
        self.assertEqual(mapping["description"], "Updated supplier description")
        self.assertEqual(mapping["description_en"], descriptions["en"])

        await update_supplier_product_descriptions(self.mapping_id, {"en": ""})
        product = await models.get_product(self.local_product_id)
        self.assertEqual(product["description"], "Updated supplier description")

    async def test_supplier_name_and_custom_emoji_survive_resync(self):
        await update_supplier_product_descriptions(
            self.mapping_id,
            {},
            custom_name="My premium account",
            custom_emoji="⭐",
            custom_emoji_id="5375312095346704820",
        )
        product = await models.get_product(self.local_product_id)
        self.assertEqual(product["name"], "My premium account")
        self.assertEqual(product["emoji"], "⭐")
        self.assertEqual(product["custom_emoji_id"], "5375312095346704820")

        await sync_supplier_products(
            [{**self.remote_product, "name": "Supplier renamed this product"}]
        )
        product = await models.get_product(self.local_product_id)
        dashboard = await get_supplier_dashboard()
        self.assertEqual(product["name"], "My premium account")
        self.assertEqual(product["custom_emoji_id"], "5375312095346704820")
        self.assertEqual(dashboard["products"][0]["name"], "Supplier renamed this product")
        self.assertEqual(dashboard["products"][0]["display_name"], "My premium account")

    async def test_supplier_custom_emoji_id_must_be_numeric(self):
        with self.assertRaisesRegex(ValueError, "INVALID_CUSTOM_EMOJI_ID"):
            await update_supplier_product_descriptions(
                self.mapping_id,
                {},
                custom_emoji_id="not-an-id",
            )

    async def test_supplier_product_ids_are_isolated_by_provider(self):
        nanlux_product = {
            **self.remote_product,
            "name": "NanLux product with same external id",
            "base_price": 1.0,
            "source_price": 25000,
            "source_currency": "VND",
        }
        await sync_supplier_products([nanlux_product], "nanlux")
        canboso = await get_supplier_dashboard("canboso")
        nanlux = await get_supplier_dashboard("nanlux")
        self.assertEqual(len(canboso["products"]), 1)
        self.assertEqual(len(nanlux["products"]), 1)
        self.assertNotEqual(canboso["products"][0]["id"], nanlux["products"][0]["id"])
        self.assertEqual(nanlux["products"][0]["source_currency"], "VND")
        self.assertFalse(nanlux["enabled"])

    async def test_v3_migration_preserves_existing_local_descriptions(self):
        current_path = os.environ["DB_PATH"]
        legacy_path = os.path.join(self.temp_dir.name, "supplier-v3.db")
        try:
            os.environ["DB_PATH"] = legacy_path
            db_module._sqlite_wal_configured = False
            db = await db_module.get_db()
            try:
                await db.execute(
                    "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
                )
                await db.execute(
                    "INSERT INTO schema_migrations (version, name) VALUES (3, 'virtual_match_game')"
                )
                await db.execute(
                    """CREATE TABLE products (
                        id INTEGER PRIMARY KEY,
                        description TEXT DEFAULT '', description_fr TEXT DEFAULT '',
                        description_ar TEXT DEFAULT '', description_zh TEXT DEFAULT '',
                        description_vi TEXT DEFAULT '', description_ru TEXT DEFAULT ''
                    )"""
                )
                await db.execute(
                    """CREATE TABLE supplier_products (
                        id INTEGER PRIMARY KEY, supplier_code TEXT NOT NULL,
                        external_product_id TEXT NOT NULL, local_product_id INTEGER,
                        name TEXT NOT NULL, description TEXT DEFAULT ''
                    )"""
                )
                await db.execute(
                    "INSERT INTO products (id, description, description_fr, description_ar) VALUES (7, 'Edited English', 'Français existant', 'عربي موجود')"
                )
                await db.execute(
                    "INSERT INTO supplier_products (id, supplier_code, external_product_id, local_product_id, name, description) VALUES (9, 'canboso', 'remote-9', 7, 'Legacy product', 'Remote English')"
                )
                await db.commit()
            finally:
                await db.close()

            await init_db()
            db = await db_module.get_db()
            try:
                columns = {
                    row["name"]
                    for row in await (await db.execute("PRAGMA table_info(supplier_products)")).fetchall()
                }
                mapping = await (
                    await db.execute("SELECT * FROM supplier_products WHERE id = 9")
                ).fetchone()
                version = await (
                    await db.execute("SELECT MAX(version) AS version FROM schema_migrations")
                ).fetchone()
            finally:
                await db.close()

            self.assertTrue({f"description_{lang}" for lang in ("en", "fr", "ar", "zh", "vi", "ru")} <= columns)
            self.assertTrue({"custom_name", "custom_emoji", "custom_emoji_id"} <= columns)
            self.assertEqual(mapping["description_en"], "Edited English")
            self.assertEqual(mapping["description_fr"], "Français existant")
            self.assertEqual(mapping["description_ar"], "عربي موجود")
            self.assertEqual(int(version["version"]), 6)
        finally:
            os.environ["DB_PATH"] = current_path
            db_module._sqlite_wal_configured = False
            models.clear_products_cache()

    async def test_wallet_supplier_order_is_paid_pending_before_external_delivery(self):
        await models.topup_wallet(3001, 10, "test")
        order = await models.create_order(3001, self.local_product_id, 3.5, quantity=1)
        purchase = await models.purchase_order_with_wallet(order["id"], 3001)
        saved = await models.get_order(order["id"])
        self.assertEqual(purchase["delivery_type"], "supplier_api")
        self.assertEqual(saved["status"], "PAID_PENDING_DELIVERY")
        self.assertEqual(purchase["items"], [])
        self.assertAlmostEqual(float(purchase["balance_after"]), 6.5)

    async def test_completed_supplier_delivery_replays_without_second_purchase(self):
        order = await models.create_order(3001, self.local_product_id, 3.5, quantity=1)
        purchase = AsyncMock(return_value={
            "external_order_id": "friend-900",
            "items": [{"account_data": "user@example.com:password"}],
            "raw_payload": {"success": True},
        })
        with patch("services.supplier_api.purchase_canboso_product", purchase):
            first = await deliver_order(order["id"], self.local_product_id)
            second = await deliver_order(order["id"], self.local_product_id)
        self.assertEqual(first, second)
        self.assertEqual(first[0]["account_data"], "user@example.com:password")
        purchase.assert_awaited_once()

    async def test_unknown_purchase_outcome_is_not_retried_automatically(self):
        order = await models.create_order(3001, self.local_product_id, 3.5, quantity=1)
        purchase = AsyncMock(side_effect=SupplierAPIError(
            "timeout after POST",
            retryable=True,
            outcome_unknown=True,
        ))
        with patch("services.supplier_api.purchase_canboso_product", purchase):
            self.assertIsNone(await deliver_order(order["id"], self.local_product_id))
            self.assertIsNone(await deliver_order(order["id"], self.local_product_id))
        purchase.assert_awaited_once()

    async def test_nanlux_delivery_dispatches_to_nanlux_only(self):
        product = {
            **self.remote_product,
            "external_product_id": "17",
            "name": "NanLux delivery",
            "base_price": 1.0,
            "source_price": 25000,
            "source_currency": "VND",
        }
        await sync_supplier_products([product], "nanlux")
        dashboard = await get_supplier_dashboard("nanlux")
        mapping = await update_supplier_product(
            int(dashboard["products"][0]["id"]),
            enabled=True,
            margin_type="fixed",
            margin_value=0.5,
            supplier_code="nanlux",
        )
        order = await models.create_order(
            3001, int(mapping["local_product_id"]), 1.5, quantity=1
        )
        nanlux_purchase = AsyncMock(
            return_value={
                "external_order_id": "nanlux-100",
                "items": [{"account_data": "nanlux-login"}],
                "raw_payload": {"success": True},
            }
        )
        canboso_purchase = AsyncMock()
        with (
            patch(
                "services.nanlux_api.purchase_nanlux_product", nanlux_purchase
            ),
            patch(
                "services.supplier_api.purchase_canboso_product", canboso_purchase
            ),
        ):
            delivered = await deliver_order(
                order["id"], int(mapping["local_product_id"])
            )
        self.assertEqual(delivered[0]["account_data"], "nanlux-login")
        nanlux_purchase.assert_awaited_once()
        canboso_purchase.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
