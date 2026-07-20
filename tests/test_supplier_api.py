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
    get_supplier_stats,
    supplier_stock_counts,
    sync_supplier_products,
    update_supplier_product,
    update_supplier_product_descriptions,
    update_supplier_detected_identity,
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
from services.supplier_sync import (
    refresh_supplier_product_stock,
    reset_supplier_sync_state,
    sync_supplier_catalog,
)


class SupplierAPITests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        reset_supplier_sync_state()
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
        reset_supplier_sync_state()
        self.temp_dir.cleanup()

    async def test_live_catalog_sync_deduplicates_concurrent_clients(self):
        catalog = [{**self.remote_product, "remote_stock": 5}]
        list_products = AsyncMock(return_value=catalog)
        persist_catalog = AsyncMock(
            return_value={"supplier_code": "canboso", "synced": 1, "selected": 1}
        )
        with (
            patch(
                "services.supplier_sync.is_supplier_configured",
                return_value=True,
            ),
            patch(
                "services.supplier_sync.get_supplier_units_per_usd",
                AsyncMock(return_value=1.0),
            ),
            patch(
                "services.supplier_sync.list_supplier_products", list_products
            ),
            patch(
                "services.supplier_sync.sync_supplier_products", persist_catalog
            ),
        ):
            results = await asyncio.gather(*(
                sync_supplier_catalog("canboso", min_interval_seconds=30)
                for _ in range(5)
            ))

        self.assertTrue(all(result["synced"] == 1 for result in results))
        list_products.assert_awaited_once()
        persist_catalog.assert_awaited_once_with(catalog, "canboso")

    async def test_empty_live_catalog_does_not_erase_cached_stock(self):
        persist_catalog = AsyncMock()
        with (
            patch(
                "services.supplier_sync.is_supplier_configured",
                return_value=True,
            ),
            patch(
                "services.supplier_sync.get_supplier_units_per_usd",
                AsyncMock(return_value=1.0),
            ),
            patch(
                "services.supplier_sync.list_supplier_products",
                AsyncMock(return_value=[]),
            ),
            patch(
                "services.supplier_sync.sync_supplier_products", persist_catalog
            ),
        ):
            with self.assertRaises(SupplierAPIError):
                await sync_supplier_catalog("canboso")

        persist_catalog.assert_not_awaited()

    async def test_unchanged_catalog_avoids_supplier_product_rewrites(self):
        result = await sync_supplier_products([self.remote_product])

        self.assertEqual(result["scope"], "full")
        self.assertEqual(result["compared"], 1)
        self.assertEqual(result["changed"], 0)
        self.assertEqual(result["inserted"], 0)
        self.assertEqual(result["unchanged"], 1)
        self.assertEqual(result["selected"], 1)

    async def test_raw_supplier_metadata_does_not_trigger_a_rewrite(self):
        result = await sync_supplier_products([{
            **self.remote_product,
            "raw_payload": {
                "id": "remote-10",
                "volatile_request_id": "different-on-every-call",
            },
        }])

        self.assertEqual(result["changed"], 0)
        self.assertEqual(result["unchanged"], 1)

    async def test_unchanged_active_sync_performs_no_database_write(self):
        result = await sync_supplier_products(
            [self.remote_product],
            refresh_disabled=False,
        )

        self.assertEqual(result["scope"], "active")
        self.assertEqual(result["changed"], 0)
        self.assertFalse(result["wrote"])
        self.assertEqual(result["transaction_ms"], 0.0)

    async def test_active_sync_skips_disabled_products(self):
        disabled = {
            **self.remote_product,
            "external_product_id": "remote-disabled",
            "name": "Disabled supplier product",
            "remote_stock": 12,
            "raw_payload": {"id": "remote-disabled"},
        }
        await sync_supplier_products([self.remote_product, disabled])

        result = await sync_supplier_products(
            [
                {**self.remote_product, "remote_stock": 3},
                {**disabled, "remote_stock": 2},
            ],
            refresh_disabled=False,
        )
        dashboard = await get_supplier_dashboard()
        by_external_id = {
            product["external_product_id"]: product
            for product in dashboard["products"]
        }

        self.assertEqual(result["scope"], "active")
        self.assertEqual(result["compared"], 1)
        self.assertEqual(result["changed"], 1)
        self.assertEqual(result["skipped_disabled"], 1)
        self.assertEqual(by_external_id["remote-10"]["remote_stock"], 3)
        self.assertEqual(by_external_id["remote-disabled"]["remote_stock"], 12)

    async def test_active_sync_zeroes_missing_selected_product_only(self):
        disabled = {
            **self.remote_product,
            "external_product_id": "remote-disabled",
            "name": "Disabled supplier product",
            "remote_stock": 12,
            "raw_payload": {"id": "remote-disabled"},
        }
        await sync_supplier_products([self.remote_product, disabled])

        result = await sync_supplier_products(
            [disabled],
            refresh_disabled=False,
        )
        dashboard = await get_supplier_dashboard()
        by_external_id = {
            product["external_product_id"]: product
            for product in dashboard["products"]
        }

        self.assertEqual(result["zeroed"], 1)
        self.assertEqual(by_external_id["remote-10"]["remote_stock"], 0)
        self.assertEqual(by_external_id["remote-disabled"]["remote_stock"], 12)

    async def test_active_catalog_sync_uses_selective_persistence(self):
        catalog = [{**self.remote_product, "remote_stock": 5}]
        persist_catalog = AsyncMock(
            return_value={
                "supplier_code": "canboso",
                "scope": "active",
                "synced": 1,
                "changed": 1,
            }
        )
        with (
            patch(
                "services.supplier_sync.is_supplier_configured",
                return_value=True,
            ),
            patch(
                "services.supplier_sync.get_supplier_units_per_usd",
                AsyncMock(return_value=1.0),
            ),
            patch(
                "services.supplier_sync.list_supplier_products",
                AsyncMock(return_value=catalog),
            ),
            patch(
                "services.supplier_sync.sync_supplier_products",
                persist_catalog,
            ),
        ):
            result = await sync_supplier_catalog(
                "canboso",
                refresh_disabled=False,
            )

        self.assertEqual(result["scope"], "active")
        persist_catalog.assert_awaited_once_with(
            catalog,
            "canboso",
            refresh_disabled=False,
        )

    async def test_enabling_supplier_product_refreshes_it_first(self):
        from bot import api_update_supplier_product

        await update_supplier_product(
            self.mapping_id,
            enabled=False,
            margin_type="fixed",
            margin_value=1,
        )
        refresh = AsyncMock(return_value={
            "status": "synced",
            "scope": "full",
            "synced": 1,
        })
        with patch("services.supplier_sync.sync_supplier_catalog", refresh):
            result = await api_update_supplier_product(
                "canboso",
                self.mapping_id,
                {
                    "enabled": True,
                    "margin_type": "fixed",
                    "margin_value": 1,
                },
            )

        refresh.assert_awaited_once_with(
            "canboso",
            min_interval_seconds=0,
            refresh_disabled=True,
        )
        self.assertEqual(result["status"], "updated")
        self.assertTrue(result["dashboard"]["products"][0]["enabled"])

    async def test_saving_active_supplier_product_does_not_force_full_sync(self):
        from bot import api_update_supplier_product

        refresh = AsyncMock()
        with patch("services.supplier_sync.sync_supplier_catalog", refresh):
            result = await api_update_supplier_product(
                "canboso",
                self.mapping_id,
                {
                    "enabled": True,
                    "margin_type": "fixed",
                    "margin_value": 2,
                },
            )

        refresh.assert_not_awaited()
        self.assertEqual(result["status"], "updated")

    async def test_blocked_restock_subscriber_is_retired(self):
        from telegram.error import Forbidden
        from handlers.products import notify_restock_subscribers

        bot = AsyncMock()
        bot.send_message.side_effect = Forbidden("bot was blocked by the user")
        mark_notified = AsyncMock()
        with (
            patch(
                "handlers.products.get_product",
                AsyncMock(return_value={
                    "id": self.local_product_id,
                    "name": "Remote account",
                    "emoji": "📦",
                }),
            ),
            patch(
                "handlers.products.get_stock_count",
                AsyncMock(return_value=3),
            ),
            patch(
                "database.models.get_pending_stock_alerts",
                AsyncMock(return_value=[{
                    "user_telegram_id": 9999,
                    "language": "en",
                }]),
            ),
            patch(
                "database.models.mark_stock_alerts_notified",
                mark_notified,
            ),
        ):
            sent = await notify_restock_subscribers(bot, self.local_product_id)

        self.assertEqual(sent, 0)
        mark_notified.assert_awaited_once_with(self.local_product_id, [9999])

    async def test_fresh_supplier_stock_respects_earlier_checkout_reservations(self):
        await models.get_or_create_user(3002, "earlier_buyer", "Earlier Buyer")
        first = await models.create_order(
            3002, self.local_product_id, 7.0, quantity=2
        )
        current = await models.create_order(
            3001, self.local_product_id, 3.5, quantity=1
        )
        with (
            patch(
                "services.supplier_sync.sync_supplier_catalog",
                AsyncMock(return_value={"status": "synced", "synced": 1}),
            ),
            patch(
                "services.supplier_sync.supplier_available_stock",
                AsyncMock(return_value=5),
            ),
        ):
            current_stock = await refresh_supplier_product_stock(
                self.local_product_id,
                reservation_order_id=current["id"],
            )
            unreserved_stock = await refresh_supplier_product_stock(
                self.local_product_id,
            )

        self.assertLess(first["id"], current["id"])
        self.assertEqual(current_stock, 3)
        self.assertEqual(unreserved_stock, 2)

    async def test_supplier_checkout_is_cancelled_before_payment_when_stock_is_zero(self):
        from handlers import payment as payment_handler

        query = object()
        order = {
            "id": 91,
            "product_id": self.local_product_id,
            "quantity": 1,
        }
        update_status = AsyncMock(return_value=True)
        edit_message = AsyncMock()
        with (
            patch.object(
                payment_handler,
                "get_product",
                AsyncMock(return_value={
                    "id": self.local_product_id,
                    "delivery_type": "supplier_api",
                }),
            ),
            patch.object(
                payment_handler,
                "_get_current_purchase_stock",
                AsyncMock(return_value=0),
            ),
            patch.object(payment_handler, "update_order_status", update_status),
            patch.object(payment_handler, "safe_edit_message_text", edit_message),
        ):
            allowed = await payment_handler._ensure_supplier_stock_for_order(
                query, order, "en"
            )

        self.assertFalse(allowed)
        update_status.assert_awaited_once_with(
            91,
            "CANCELLED",
            expected_statuses=("PENDING", "AWAITING_PAYMENT"),
        )
        edit_message.assert_awaited_once()

    async def test_supplier_checkout_fails_closed_when_live_check_is_unavailable(self):
        from handlers import payment as payment_handler

        query = object()
        order = {
            "id": 92,
            "product_id": self.local_product_id,
            "quantity": 1,
        }
        update_status = AsyncMock()
        edit_message = AsyncMock()
        with (
            patch.object(
                payment_handler,
                "get_product",
                AsyncMock(return_value={
                    "id": self.local_product_id,
                    "delivery_type": "supplier_api",
                }),
            ),
            patch.object(
                payment_handler,
                "_get_current_purchase_stock",
                AsyncMock(side_effect=SupplierAPIError("supplier offline")),
            ),
            patch.object(payment_handler, "update_order_status", update_status),
            patch.object(payment_handler, "safe_edit_message_text", edit_message),
        ):
            allowed = await payment_handler._ensure_supplier_stock_for_order(
                query, order, "en"
            )

        self.assertFalse(allowed)
        update_status.assert_not_awaited()
        edit_message.assert_awaited_once()

    async def test_supplier_stock_balance_timeout_keeps_catalog_responsive(self):
        async def never_returns(*_args, **_kwargs):
            await asyncio.sleep(10)

        loop = asyncio.get_running_loop()
        started = loop.time()
        with (
            patch("services.supplier_registry.get_supplier_balance", side_effect=never_returns),
            patch("database.suppliers.SUPPLIER_STOCK_BALANCE_TIMEOUT_SECONDS", 0.01),
        ):
            counts = await supplier_stock_counts()
        elapsed = loop.time() - started

        self.assertEqual(counts[self.local_product_id], 0)
        self.assertLess(elapsed, 0.25)

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
            "botSource": "Gemini Store Bot",
            "requester": {"name": "Rayan"},
        })
        self.assertEqual(balance["currency"], "USD")
        self.assertEqual(balance["balance"], 2.5)
        self.assertEqual(balance["balance_text"], "$2.50")
        self.assertEqual(balance["provider_name"], "Gemini Store Bot")
        self.assertEqual(balance["account_name"], "Rayan")

    async def test_detected_supplier_name_is_persisted_for_dashboard(self):
        changed = await update_supplier_detected_identity("canboso", {
            "provider_name": "Gemini Store Bot",
            "bot_source": "Gemini Store Bot",
            "account_name": "Rayan",
        })
        dashboard = await get_supplier_dashboard("canboso")

        self.assertTrue(changed)
        self.assertEqual(dashboard["detected_name"], "Gemini Store Bot")
        self.assertFalse(await update_supplier_detected_identity("canboso", {
            "provider_name": "Gemini Store Bot",
            "bot_source": "Gemini Store Bot",
            "account_name": "Rayan",
        }))

    async def test_supplier_display_name_can_be_customized(self):
        await update_supplier_settings(
            supplier_code="canboso",
            enabled=True,
            margin_type="fixed",
            margin_value=1,
            display_name="My Supplier Bot",
        )
        dashboard = await get_supplier_dashboard("canboso")
        self.assertEqual(dashboard["display_name"], "My Supplier Bot")

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

    async def test_supplier_custom_image_survives_resync_and_clears_media_cache(self):
        first_image = "https://example.com/custom-first.png"
        second_image = "https://example.com/custom-second.png"
        supplier_image = "https://supplier.example.com/source.png"

        await update_supplier_product_descriptions(
            self.mapping_id,
            {},
            custom_image_url=first_image,
        )
        await models.cache_product_telegram_file_id(
            self.local_product_id,
            first_image,
            "cached-telegram-photo",
        )

        await update_supplier_product_descriptions(
            self.mapping_id,
            {},
            custom_image_url=second_image,
        )
        product = await models.get_product(self.local_product_id)
        dashboard = await get_supplier_dashboard()
        self.assertEqual(product["image_url"], second_image)
        self.assertIsNone(product["telegram_file_id"])
        self.assertEqual(dashboard["products"][0]["custom_image_url"], second_image)
        self.assertEqual(dashboard["products"][0]["display_image_url"], second_image)

        await sync_supplier_products(
            [{**self.remote_product, "image_url": supplier_image}]
        )
        product = await models.get_product(self.local_product_id)
        self.assertEqual(product["image_url"], second_image)

        await update_supplier_product_descriptions(
            self.mapping_id,
            {},
            custom_image_url="",
        )
        product = await models.get_product(self.local_product_id)
        dashboard = await get_supplier_dashboard()
        self.assertEqual(product["image_url"], supplier_image)
        self.assertEqual(dashboard["products"][0]["custom_image_url"], "")
        self.assertEqual(dashboard["products"][0]["display_image_url"], supplier_image)

    async def test_regular_product_editor_cannot_convert_supplier_product_to_stock(self):
        from bot import api_update_product

        await api_update_product(
            self.local_product_id,
            {
                "delivery_type": "stock",
                "name": "Edited from Products tab",
                "emoji": "🌟",
                "custom_emoji_id": "5375312095346704820",
                "description": "Custom English from Products tab",
                "description_fr": "Traduction depuis Produits",
                "warranty_days": 30,
                "image_url": "https://example.com/products-editor.png",
                "price_usd": 3.5,
            },
        )
        product = await models.get_product(self.local_product_id)
        dashboard = await get_supplier_dashboard()
        mapping = dashboard["products"][0]
        self.assertEqual(product["delivery_type"], "supplier_api")
        self.assertEqual(product["name"], "Edited from Products tab")
        self.assertEqual(product["description_fr"], "Traduction depuis Produits")
        self.assertEqual(int(product["warranty_days"]), 30)
        self.assertEqual(mapping["custom_name"], "Edited from Products tab")
        self.assertEqual(mapping["description_fr"], "Traduction depuis Produits")
        self.assertEqual(int(mapping["custom_warranty_days"]), 30)
        self.assertEqual(
            mapping["custom_image_url"],
            "https://example.com/products-editor.png",
        )

        await sync_supplier_products(
            [{**self.remote_product, "name": "Supplier source name"}]
        )
        product = await models.get_product(self.local_product_id)
        self.assertEqual(product["delivery_type"], "supplier_api")
        self.assertEqual(product["name"], "Edited from Products tab")
        self.assertEqual(product["description_fr"], "Traduction depuis Produits")
        self.assertEqual(int(product["warranty_days"]), 30)
        self.assertEqual(
            product["image_url"],
            "https://example.com/products-editor.png",
        )

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
            self.assertTrue({"custom_name", "custom_emoji", "custom_emoji_id", "custom_warranty_days", "custom_image_url"} <= columns)
            self.assertEqual(mapping["description_en"], "Edited English")
            self.assertEqual(mapping["description_fr"], "Français existant")
            self.assertEqual(mapping["description_ar"], "عربي موجود")
            self.assertEqual(int(version["version"]), 16)
        finally:
            os.environ["DB_PATH"] = current_path
            db_module._sqlite_wal_configured = False
            models.clear_products_cache()

    async def test_v8_migration_preserves_existing_local_custom_image(self):
        current_path = os.environ["DB_PATH"]
        legacy_path = os.path.join(self.temp_dir.name, "supplier-v7-image.db")
        try:
            os.environ["DB_PATH"] = legacy_path
            db_module._sqlite_wal_configured = False
            db = await db_module.get_db()
            try:
                await db.execute(
                    "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
                )
                await db.execute(
                    "INSERT INTO schema_migrations (version, name) VALUES (7, 'supplier_custom_warranty')"
                )
                await db.execute(
                    "CREATE TABLE products (id INTEGER PRIMARY KEY, image_url TEXT)"
                )
                await db.execute(
                    """CREATE TABLE supplier_products (
                        id INTEGER PRIMARY KEY, local_product_id INTEGER,
                        image_url TEXT DEFAULT ''
                    )"""
                )
                await db.execute(
                    "INSERT INTO products (id, image_url) VALUES (7, 'https://example.com/existing-custom.png')"
                )
                await db.execute(
                    "INSERT INTO supplier_products (id, local_product_id, image_url) VALUES (9, 7, 'https://supplier.example.com/source.png')"
                )
                await db.commit()
            finally:
                await db.close()

            await init_db()
            db = await db_module.get_db()
            try:
                mapping = await (
                    await db.execute(
                        "SELECT custom_image_url FROM supplier_products WHERE id = 9"
                    )
                ).fetchone()
                version = await (
                    await db.execute("SELECT MAX(version) AS version FROM schema_migrations")
                ).fetchone()
            finally:
                await db.close()

            self.assertEqual(
                mapping["custom_image_url"],
                "https://example.com/existing-custom.png",
            )
            self.assertEqual(int(version["version"]), 16)
        finally:
            os.environ["DB_PATH"] = current_path
            db_module._sqlite_wal_configured = False
            models.clear_products_cache()

    async def test_v9_migration_backfills_historical_supplier_financials(self):
        current_path = os.environ["DB_PATH"]
        legacy_path = os.path.join(self.temp_dir.name, "supplier-v8-finance.db")
        try:
            os.environ["DB_PATH"] = legacy_path
            db_module._sqlite_wal_configured = False
            db = await db_module.get_db()
            try:
                await db.execute(
                    "CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
                )
                await db.execute(
                    "INSERT INTO schema_migrations (version, name) VALUES (8, 'supplier_custom_image')"
                )
                await db.execute(
                    "CREATE TABLE orders (id INTEGER PRIMARY KEY, amount_usd REAL)"
                )
                await db.execute(
                    """CREATE TABLE supplier_products (
                        supplier_code TEXT, external_product_id TEXT,
                        base_price REAL
                    )"""
                )
                await db.execute(
                    """CREATE TABLE supplier_orders (
                        id INTEGER PRIMARY KEY, order_id INTEGER,
                        supplier_code TEXT, external_product_id TEXT,
                        quantity INTEGER, status TEXT
                    )"""
                )
                await db.execute("INSERT INTO orders VALUES (7, 4.5)")
                await db.execute(
                    "INSERT INTO supplier_products VALUES ('canboso', 'remote-9', 1.5)"
                )
                await db.execute(
                    "INSERT INTO supplier_orders VALUES (9, 7, 'canboso', 'remote-9', 2, 'completed')"
                )
                await db.commit()
            finally:
                await db.close()

            await init_db()
            db = await db_module.get_db()
            try:
                row = await (
                    await db.execute(
                        "SELECT cost_usd, revenue_usd, cost_estimated FROM supplier_orders WHERE id = 9"
                    )
                ).fetchone()
                version = await (
                    await db.execute("SELECT MAX(version) AS version FROM schema_migrations")
                ).fetchone()
            finally:
                await db.close()

            self.assertEqual(float(row["cost_usd"]), 3.0)
            self.assertEqual(float(row["revenue_usd"]), 4.5)
            self.assertEqual(int(row["cost_estimated"]), 1)
            self.assertEqual(int(version["version"]), 16)
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

    async def test_supplier_delivery_is_available_from_purchase_history(self):
        order = await models.create_order(
            3001, self.local_product_id, 3.5, quantity=1
        )
        supplier_purchase = AsyncMock(return_value={
            "external_order_id": "history-1",
            "items": [{"account_data": "supplier-login:secret"}],
            "raw_payload": {"success": True},
        })

        with patch(
            "services.supplier_api.purchase_canboso_product", supplier_purchase
        ):
            delivered = await deliver_order(order["id"], self.local_product_id)

        await models.update_order_status(
            order["id"], "COMPLETED", expected_statuses=("PENDING",)
        )
        stored = await models.get_stock_items_for_order(order["id"])

        self.assertEqual(delivered, [{"account_data": "supplier-login:secret"}])
        self.assertEqual(
            [item["account_data"] for item in stored],
            [item["account_data"] for item in delivered],
        )
        self.assertIsInstance(stored[0]["id"], int)

    async def test_reseller_supplier_purchase_returns_delivery_and_is_idempotent(self):
        await models.topup_wallet(3001, 10, "test")
        supplier_purchase = AsyncMock(return_value={
            "external_order_id": "reseller-1",
            "items": [{"account_data": "reseller-login:secret"}],
            "raw_payload": {"success": True},
        })

        stock_count = AsyncMock(return_value=8)
        with (
            patch(
                "services.supplier_sync.refresh_supplier_product_stock",
                stock_count,
            ),
            patch(
                "services.supplier_api.purchase_canboso_product",
                supplier_purchase,
            ),
        ):
            first = await models.create_reseller_order(
                3001,
                self.local_product_id,
                quantity=1,
                idempotency_key="supplier-reseller-1",
            )
            replay = await models.create_reseller_order(
                3001,
                self.local_product_id,
                quantity=1,
                idempotency_key="supplier-reseller-1",
            )

        self.assertFalse(first["idempotent"])
        self.assertTrue(replay["idempotent"])
        self.assertEqual(first["order"]["status"], "COMPLETED")
        self.assertEqual(
            [item["account_data"] for item in first["order"]["items"]],
            ["reseller-login:secret"],
        )
        self.assertEqual(replay["order"]["items"], first["order"]["items"])
        supplier_purchase.assert_awaited_once()
        stock_count.assert_awaited_once_with(self.local_product_id)

        db = await db_module.get_db()
        try:
            user = await (
                await db.execute(
                    "SELECT wallet_balance FROM users WHERE telegram_id = 3001"
                )
            ).fetchone()
            transactions = await (
                await db.execute(
                    "SELECT COUNT(*) AS cnt FROM wallet_transactions "
                    "WHERE description LIKE 'Reseller API order #%'")
            ).fetchone()
        finally:
            await db.close()

        self.assertAlmostEqual(float(user["wallet_balance"]), 6.5)
        self.assertEqual(int(transactions["cnt"]), 1)

    async def test_supplier_stats_use_order_time_cost_and_revenue_snapshots(self):
        purchase = AsyncMock(
            side_effect=[
                {
                    "external_order_id": "stats-1",
                    "items": [{"account_data": "first"}],
                    "raw_payload": {"success": True},
                },
                {
                    "external_order_id": "stats-2",
                    "items": [
                        {"account_data": "second"},
                        {"account_data": "third"},
                    ],
                    "raw_payload": {"success": True},
                },
            ]
        )
        first = await models.create_order(3001, self.local_product_id, 3.5, quantity=1)
        second = await models.create_order(3001, self.local_product_id, 7.0, quantity=2)
        with patch("services.supplier_api.purchase_canboso_product", purchase):
            await deliver_order(first["id"], self.local_product_id)
            await deliver_order(second["id"], self.local_product_id)

        stats = await get_supplier_stats(days=30)
        summary = stats["summary"]
        self.assertEqual(summary["orders"], 2)
        self.assertEqual(summary["items_sold"], 3)
        self.assertEqual(summary["revenue"], 10.5)
        self.assertEqual(summary["cost"], 7.5)
        self.assertEqual(summary["profit"], 3.0)
        self.assertEqual(summary["average_order"], 5.25)
        self.assertAlmostEqual(summary["margin_percent"], 28.57, places=2)
        self.assertEqual(summary["success_rate"], 100.0)
        self.assertEqual(stats["data_quality"]["estimated_cost_orders"], 0)
        self.assertEqual(stats["data_quality"]["missing_cost_orders"], 0)
        self.assertEqual(len(stats["daily"]), 30)
        self.assertEqual(stats["daily"][-1]["items_sold"], 3)

        product = stats["products"][0]
        self.assertEqual(product["name"], "Remote account")
        self.assertEqual(product["items_sold"], 3)
        self.assertEqual(product["revenue"], 10.5)
        self.assertEqual(product["cost"], 7.5)
        self.assertEqual(product["profit"], 3.0)

        from bot import api_get_supplier_stats

        api_stats = await api_get_supplier_stats("canboso", days=7)
        self.assertEqual(api_stats["days"], 7)
        self.assertEqual(len(api_stats["daily"]), 7)
        self.assertEqual(api_stats["summary"]["profit"], 3.0)

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

    def test_supplier_order_messages_are_neutral_in_every_language(self):
        from utils.locales import t

        expected = {
            "en": (
                "⏳ <b>Your order is being processed...</b>",
                "⏳ <b>Your order #42 is being processed.</b>",
            ),
            "fr": (
                "⏳ <b>Votre commande est en cours...</b>",
                "⏳ <b>Votre commande #42 est en cours.</b>",
            ),
            "ar": (
                "⏳ <b>طلبك قيد المعالجة...</b>",
                "⏳ <b>طلبك رقم #42 قيد المعالجة.</b>",
            ),
            "zh": (
                "⏳ <b>您的订单正在处理中...</b>",
                "⏳ <b>您的订单 #42 正在处理中。</b>",
            ),
            "vi": (
                "⏳ <b>Đơn hàng của bạn đang được xử lý...</b>",
                "⏳ <b>Đơn hàng #42 của bạn đang được xử lý.</b>",
            ),
            "ru": (
                "⏳ <b>Ваш заказ обрабатывается...</b>",
                "⏳ <b>Ваш заказ #42 обрабатывается.</b>",
            ),
        }
        for lang, (processing, pending) in expected.items():
            self.assertEqual(t("supplier_delivery_processing", lang), processing)
            self.assertEqual(
                t("supplier_paid_pending", lang).format(order_id=42), pending
            )

            client_text = f"{processing} {pending}".lower()
            for provider_name in ("supplier", "fournisseur", "canboso", "nanlux"):
                self.assertNotIn(provider_name, client_text)


if __name__ == "__main__":
    unittest.main()
