import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from database import db as db_module
from database.db import init_db
from database import models


class ProductAutoHideTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_db_path = os.environ.get("DB_PATH")
        self.original_turso_url = db_module.TURSO_URL
        os.environ["DB_PATH"] = os.path.join(
            self.temp_dir.name,
            "auto-hide.db",
        )
        db_module.TURSO_URL = ""
        db_module._sqlite_wal_configured = False
        models.clear_products_cache()
        models._clear_stock_cache()
        await init_db()
        self.category_id = await models.add_category("Products", "📦", "")

    async def asyncTearDown(self):
        models.clear_products_cache()
        models._clear_stock_cache()
        db_module.TURSO_URL = self.original_turso_url
        if self.original_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self.original_db_path
        self.temp_dir.cleanup()

    async def _create_product(
        self,
        *,
        enabled: bool = True,
        delivery_type: str = "stock",
    ) -> int:
        return await models.add_product(
            self.category_id,
            "Auto-hide product",
            "",
            1.0,
            delivery_type=delivery_type,
            auto_hide_out_of_stock=enabled,
            auto_hide_delay_minutes=60,
        )

    async def _set_out_since(self, product_id: int, value: datetime) -> None:
        db = await db_module.get_db()
        try:
            await db.execute(
                "UPDATE products SET out_of_stock_since = ? WHERE id = ?",
                (value.isoformat(sep=" "), product_id),
            )
            await db.commit()
        finally:
            await db.close()
        models.clear_products_cache()

    @staticmethod
    def _utcnow() -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    async def test_product_hides_after_delay_but_admin_always_sees_it(self):
        product_id = await self._create_product()
        await self._set_out_since(
            product_id,
            self._utcnow() - timedelta(minutes=61),
        )
        product = await models.get_product(product_id)

        status = models.product_auto_hide_status(product, 0)

        self.assertEqual(status["auto_hide_status"], "hidden")
        self.assertFalse(
            models.product_is_customer_visible(product, 0)
        )
        self.assertTrue(
            models.product_is_customer_visible(product, 0, is_admin=True)
        )

    async def test_restock_unhides_and_records_hidden_duration(self):
        product_id = await self._create_product()
        await self._set_out_since(
            product_id,
            self._utcnow() - timedelta(minutes=120),
        )

        await models.add_stock_items(product_id, ["account-one"])
        product = await models.get_product(product_id)

        self.assertIsNone(product["out_of_stock_since"])
        self.assertIsNotNone(product["last_restocked_at"])
        self.assertGreaterEqual(
            int(product["auto_hidden_total_seconds"]),
            3500,
        )
        self.assertEqual(
            models.product_auto_hide_status(product, 1)["auto_hide_status"],
            "in_stock",
        )

    async def test_stock_removal_starts_timer_and_reset_restarts_it(self):
        product_id = await self._create_product()
        await models.add_stock_items(product_id, ["account-one"])
        db = await db_module.get_db()
        try:
            row = await (
                await db.execute(
                    "SELECT id FROM stock_items WHERE product_id = ?",
                    (product_id,),
                )
            ).fetchone()
        finally:
            await db.close()

        await models.delete_stock_item(int(row["id"]))
        product = await models.get_product(product_id)
        self.assertIsNotNone(product["out_of_stock_since"])
        self.assertEqual(
            models.product_auto_hide_status(product, 0)["auto_hide_status"],
            "grace",
        )

        await self._set_out_since(
            product_id,
            self._utcnow() - timedelta(minutes=90),
        )
        await models.reset_product_auto_hide_timer(product_id)
        reset_product = await models.get_product(product_id)
        reset_status = models.product_auto_hide_status(reset_product, 0)
        self.assertEqual(reset_status["auto_hide_status"], "grace")
        self.assertGreater(reset_status["auto_hide_remaining_seconds"], 3500)

    async def test_activation_products_never_enable_auto_hide(self):
        product_id = await self._create_product(
            enabled=True,
            delivery_type="activation",
        )
        product = await models.get_product(product_id)

        self.assertEqual(int(product["auto_hide_out_of_stock"]), 0)
        status = models.product_auto_hide_status(product, 0)
        self.assertEqual(status["auto_hide_status"], "not_applicable")
        self.assertTrue(status["auto_hide_customer_visible"])

    async def test_steady_state_reconciliation_does_not_write(self):
        product_id = await self._create_product()
        first = await models.reconcile_product_availability_states(
            [product_id],
            stock_counts={product_id: 0},
        )
        second = await models.reconcile_product_availability_states(
            [product_id],
            stock_counts={product_id: 0},
        )

        self.assertEqual(first, 0)
        self.assertEqual(second, 0)

    async def test_disabling_auto_hide_keeps_out_of_stock_product_visible(self):
        product_id = await self._create_product()
        updated = await models.set_product_auto_hide_settings(
            product_id,
            enabled=False,
            delay_minutes=60,
        )

        self.assertEqual(int(updated["auto_hide_out_of_stock"]), 0)
        self.assertIsNone(updated["out_of_stock_since"])
        self.assertTrue(
            models.product_auto_hide_status(
                updated,
                0,
            )["auto_hide_customer_visible"]
        )

    async def test_dashboard_api_updates_auto_hide_without_other_product_fields(self):
        from bot import api_get_products, api_update_product

        product_id = await self._create_product(enabled=False)
        response = await api_update_product(
            product_id,
            {
                "auto_hide_out_of_stock": True,
                "auto_hide_delay_minutes": 90,
            },
        )
        products = await api_get_products()
        product = next(
            item for item in products if int(item["id"]) == product_id
        )

        self.assertEqual(response["status"], "updated")
        self.assertEqual(int(product["auto_hide_out_of_stock"]), 1)
        self.assertEqual(int(product["auto_hide_delay_minutes"]), 90)
        self.assertEqual(product["auto_hide_status"], "grace")
        self.assertIn("stock_alert_subscribers", product)

    async def test_reseller_catalog_uses_customer_visibility_policy(self):
        from bot import _build_reseller_catalog

        hidden_id = await self._create_product(enabled=True)
        await self._set_out_since(
            hidden_id,
            self._utcnow() - timedelta(minutes=61),
        )
        visible_id = await self._create_product(enabled=False)

        payload = await _build_reseller_catalog("en")
        product_ids = {
            int(product["id"])
            for product in payload["products"]
            if product.get("id") != "test_product"
        }

        self.assertNotIn(hidden_id, product_ids)
        self.assertIn(visible_id, product_ids)


if __name__ == "__main__":
    unittest.main()
