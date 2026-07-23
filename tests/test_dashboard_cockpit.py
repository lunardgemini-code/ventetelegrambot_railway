import os
import re
import tempfile
import unittest

import httpx

import bot
from database import db as db_module
from database import models
from database.db import init_db


ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DASHBOARD = os.path.join(ROOT, "dashboard")


class DashboardCockpitStaticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with open(os.path.join(DASHBOARD, "index.html"), encoding="utf-8") as handle:
            cls.html = handle.read()
        with open(os.path.join(DASHBOARD, "operations.js"), encoding="utf-8") as handle:
            cls.operations = handle.read()
        with open(os.path.join(DASHBOARD, "operations.css"), encoding="utf-8") as handle:
            cls.styles = handle.read()
        with open(os.path.join(DASHBOARD, "service-worker.js"), encoding="utf-8") as handle:
            cls.worker = handle.read()

    def test_operational_shell_components_are_wired(self):
        for element_id in (
            "btn-command-palette",
            "btn-customize-cockpit",
            "ops-alert-strip",
            "ops-mobile-nav",
            "command-palette",
            "ops-context-drawer",
        ):
            self.assertIn(f'id="{element_id}"', self.html)
        for module in (
            "alerts",
            "operations",
            "today",
            "metrics",
            "charts",
            "stock",
            "performance",
        ):
            self.assertIn(f'data-cockpit-module="{module}"', self.html)

    def test_cockpit_preferences_stay_local_and_do_not_poll(self):
        self.assertIn("ventebot_cockpit_layout_v1", self.operations)
        self.assertIn("ventebot_cockpit_hidden_v1", self.operations)
        self.assertIn("localStorage.setItem(LAYOUT_KEY", self.operations)
        self.assertNotIn("setInterval(", self.operations)
        self.assertIn("document.hidden", self.operations)
        self.assertIn("120000", self.operations)

    def test_command_search_is_bounded_debounced_and_cancellable(self):
        self.assertIn("/api/dashboard/search", self.operations)
        self.assertIn("new AbortController()", self.operations)
        self.assertIn("setTimeout(() => runCommandSearch", self.operations)
        self.assertIn("260", self.operations)
        self.assertIn("limit=14", self.operations)
        self.assertIn("30000", self.operations)

    def test_supplier_comparison_is_explanatory_and_filterable(self):
        self.assertIn('data-ops-filter="supplier-unavailable"', self.operations)
        self.assertIn("aiDeliveryLabel(candidate.delivery_mode)", self.operations)
        self.assertIn("ai_reason_affordable", self.operations)
        self.assertIn("showUnavailableSuppliers", self.operations)

    def test_new_strings_exist_in_all_dashboard_languages(self):
        segment = self.operations.split(
            "const COCKPIT_TRANSLATIONS = {", 1
        )[1].split("Object.entries(COCKPIT_TRANSLATIONS)", 1)[0]
        french = segment.split("\nfr: {", 1)[1].split("\n},\nen: {", 1)[0]
        keys = set(re.findall(r"\b(ops_[a-z0-9_]+)\s*:", french))
        self.assertGreater(len(keys), 70)
        for key in keys:
            self.assertEqual(
                len(re.findall(rf"\b{re.escape(key)}\s*:", segment)),
                6,
                f"{key} is not translated in every language",
            )

    def test_mobile_breakpoints_rtl_and_reduced_motion_are_explicit(self):
        for width in (1440, 1280, 768, 430, 390, 360):
            self.assertIn(f"@media (max-width: {width}px)", self.styles)
        self.assertIn('[dir="rtl"]', self.styles)
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.styles)
        self.assertIn("@supports not", self.styles)
        self.assertIn("env(safe-area-inset-bottom", self.styles)

    def test_pwa_shell_versions_every_new_asset(self):
        for asset in (
            "operations.css?v=20260723-mobile-products-v2",
            "app.js?v=20260723-mobile-products-v2",
            "operations.js?v=20260723-ops-v2",
        ):
            self.assertIn(asset, self.html)
            self.assertIn(asset, self.worker)
        self.assertIn("ventebot-dashboard-shell-20260723-mobile-products-v2", self.worker)


class DashboardCockpitDataTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_db_path = os.environ.get("DB_PATH")
        self.previous_turso_url = db_module.TURSO_URL
        os.environ["DB_PATH"] = os.path.join(self.temp_dir.name, "cockpit.db")
        db_module.TURSO_URL = ""
        db_module._sqlite_wal_configured = False
        models.clear_products_cache()
        models._GET_STATS_CACHE.clear()
        bot._stats_cache.clear()
        await init_db()

        await models.get_or_create_user(91001, "cockpit_client", "Cockpit Client")
        category_id = await models.add_category("Cockpit")
        self.product_id = await models.add_product(
            category_id=category_id,
            name="Cockpit Product",
            description="Operational test product",
            price_usd=1.0,
            warranty_days=7,
        )
        await models.add_stock_items(
            self.product_id,
            ["account-one", "account-two", "account-three"],
        )
        self.order = await models.create_order(
            91001,
            self.product_id,
            2.0,
            quantity=2,
        )

        db = await db_module.get_db()
        try:
            await db.execute(
                "UPDATE orders SET status = 'COMPLETED', paid_at = CURRENT_TIMESTAMP "
                "WHERE id = ?",
                (self.order["id"],),
            )
            await db.execute(
                "INSERT INTO product_views (product_id, user_telegram_id) VALUES (?, ?)",
                (self.product_id, 91001),
            )
            await db.execute(
                "INSERT INTO product_buy_clicks (product_id, user_telegram_id) "
                "VALUES (?, ?)",
                (self.product_id, 91001),
            )
            await db.execute(
                """INSERT INTO dynamic_price_history
                   (product_id, old_price, new_price, suggested_price, mode, applied)
                   VALUES (?, 0.90, 1.00, 1.00, 'auto', 1)""",
                (self.product_id,),
            )
            await db.execute(
                """INSERT INTO supplier_orders
                   (order_id, supplier_code, external_product_id, quantity,
                    status, cost_usd, revenue_usd, completed_at)
                   VALUES (?, 'cockpit', 'remote-product', 2,
                           'completed', 1.25, 2.00, CURRENT_TIMESTAMP)""",
                (self.order["id"],),
            )
            await db.commit()
        finally:
            await db.close()

    async def asyncTearDown(self):
        models.clear_products_cache()
        models._GET_STATS_CACHE.clear()
        bot._stats_cache.clear()
        db_module.TURSO_URL = self.previous_turso_url
        if self.previous_db_path is None:
            os.environ.pop("DB_PATH", None)
        else:
            os.environ["DB_PATH"] = self.previous_db_path
        self.temp_dir.cleanup()

    async def test_bounded_search_finds_products_users_and_orders(self):
        product_results = await models.search_dashboard_entities("Cockpit", limit=3)
        user_results = await models.search_dashboard_entities("91001", limit=3)
        order_results = await models.search_dashboard_entities(
            str(self.order["id"]),
            limit=3,
        )
        escaped_wildcard = await models.search_dashboard_entities("%", limit=3)
        oversized_number = await models.search_dashboard_entities("9" * 80, limit=3)

        self.assertTrue(any(row["entity_type"] == "product" for row in product_results))
        self.assertTrue(any(row["entity_type"] == "user" for row in user_results))
        self.assertTrue(any(row["entity_type"] == "order" for row in order_results))
        self.assertEqual(escaped_wildcard, [])
        self.assertEqual(oversized_number, [])
        self.assertLessEqual(len(product_results), 3)

    async def test_product_insights_are_zero_filled_and_economic_data_is_known(self):
        insights = await models.get_product_operational_insights(
            self.product_id,
            days=30,
        )

        self.assertIsNotNone(insights)
        self.assertEqual(len(insights["sales"]["days"]), 30)
        self.assertEqual(len(insights["sales"]["quantity_series"]), 30)
        self.assertEqual(insights["sales"]["sales_7d"], 2)
        self.assertEqual(insights["conversion"]["views"], 1)
        self.assertEqual(insights["conversion"]["payments_completed"], 1)
        self.assertEqual(insights["stock"]["current"], 3)
        self.assertEqual(insights["economics"]["known_profit_30d"], 0.75)
        self.assertEqual(len(insights["price_history"]), 1)

    async def test_overview_exposes_known_profit_without_estimating_local_stock(self):
        overview = await models.get_dashboard_overview()

        self.assertEqual(overview["economics"]["known_profit_orders_30d"], 1)
        self.assertEqual(overview["economics"]["known_profit_30d"], 0.75)
        self.assertEqual(overview["today"]["orders"], 1)

    async def test_authenticated_endpoints_return_bounded_contracts(self):
        transport = httpx.ASGITransport(app=bot.api)
        headers = {"X-API-Key": bot.ADMIN_API_KEY}
        async with httpx.AsyncClient(
            transport=transport,
            base_url="https://testserver",
            headers=headers,
        ) as client:
            search = await client.get("/api/dashboard/search", params={"q": "Cockpit"})
            insights = await client.get(
                f"/api/products/{self.product_id}/insights"
            )
            missing = await client.get("/api/products/999999/insights")

        self.assertEqual(search.status_code, 200)
        self.assertLessEqual(len(search.json()["results"]), 12)
        self.assertEqual(insights.status_code, 200)
        self.assertIn("supplier_comparison", insights.json())
        self.assertEqual(missing.status_code, 404)


if __name__ == "__main__":
    unittest.main()
