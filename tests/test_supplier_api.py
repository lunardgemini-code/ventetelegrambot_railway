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
    update_supplier_settings,
)
from services.delivery import deliver_order
from services.supplier_api import SupplierAPIError, normalize_products


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

    def test_fixed_and_percent_margins(self):
        self.assertEqual(calculate_supplier_price(2.5, "fixed", 1), 3.5)
        self.assertEqual(calculate_supplier_price(2.5, "percent", 20), 3.0)

    async def test_selected_product_uses_remote_stock_and_margin(self):
        product = await models.get_product(self.local_product_id)
        self.assertEqual(product["delivery_type"], "supplier_api")
        self.assertAlmostEqual(float(product["price_usd"]), 3.5)
        self.assertEqual(await models.get_stock_count(self.local_product_id), 8)

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


if __name__ == "__main__":
    unittest.main()
