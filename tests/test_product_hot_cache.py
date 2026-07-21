import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from database import models
from handlers import products as product_handlers
from services.singleflight import AsyncSingleFlight
from utils.locales import LANGUAGES


class AsyncSingleFlightTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_callers_share_one_loader(self):
        singleflight = AsyncSingleFlight()
        started = asyncio.Event()
        release = asyncio.Event()
        calls = 0

        async def loader():
            nonlocal calls
            calls += 1
            started.set()
            await release.wait()
            return {"value": 7}

        tasks = [
            asyncio.create_task(singleflight.run("catalog", loader))
            for _ in range(12)
        ]
        await started.wait()
        await asyncio.sleep(0)
        release.set()
        results = await asyncio.gather(*tasks)

        self.assertEqual(calls, 1)
        self.assertEqual(results, [{"value": 7}] * 12)
        self.assertEqual(len(singleflight), 0)

    async def test_cancelling_one_waiter_does_not_cancel_shared_loader(self):
        singleflight = AsyncSingleFlight()
        started = asyncio.Event()
        release = asyncio.Event()

        async def loader():
            started.set()
            await release.wait()
            return 9

        cancelled = asyncio.create_task(singleflight.run("stock", loader))
        survivor = asyncio.create_task(singleflight.run("stock", loader))
        await started.wait()
        cancelled.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await cancelled
        release.set()

        self.assertEqual(await survivor, 9)


class ProductDataCacheTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        models._PRODUCT_DETAILS_CACHE.clear()
        models._PRODUCT_READ_SINGLEFLIGHT.clear()
        models._STOCK_COUNTS_CACHE = None
        models.clear_products_cache()

    async def test_product_details_are_coalesced_cached_and_copied(self):
        started = asyncio.Event()
        release = asyncio.Event()

        async def load(_product_id):
            started.set()
            await release.wait()
            return ({"id": 4, "name": "Gemini"}, 8, [{"min_qty": 1}], 3)

        loader = AsyncMock(side_effect=load)
        with patch(
            "database.models._get_product_full_details_uncached",
            loader,
        ):
            tasks = [
                asyncio.create_task(models.get_product_full_details(4))
                for _ in range(10)
            ]
            await started.wait()
            await asyncio.sleep(0)
            release.set()
            results = await asyncio.gather(*tasks)
            results[0][0]["name"] = "Changed by caller"
            cached = await models.get_product_full_details(4)

        self.assertEqual(loader.await_count, 1)
        self.assertTrue(all(result[1] == 8 for result in results))
        self.assertEqual(cached[0]["name"], "Gemini")

    async def test_stock_invalidation_clears_product_detail_snapshots(self):
        models._PRODUCT_DETAILS_CACHE[4] = (
            10.0,
            models.get_catalog_cache_generation(),
            ({"id": 4}, 8, [], 3),
        )

        models._clear_stock_cache()

        self.assertEqual(models._PRODUCT_DETAILS_CACHE, {})

    async def test_stock_refresh_is_singleflight(self):
        started = asyncio.Event()
        release = asyncio.Event()
        calls = 0

        class Cursor:
            def __init__(self, rows):
                self._rows = rows

            async def fetchall(self):
                return list(self._rows)

        async def execute(sql, _params=None):
            if "FROM stock_items" in sql:
                return Cursor([{"product_id": 4, "cnt": 8}])
            return Cursor([])

        async def get_db():
            nonlocal calls
            calls += 1
            started.set()
            await release.wait()
            return SimpleNamespace(
                execute=AsyncMock(side_effect=execute),
                close=AsyncMock(),
            )

        with patch("database.models.get_db", side_effect=get_db), patch(
            "database.suppliers.supplier_stock_counts",
            AsyncMock(return_value={}),
        ):
            tasks = [
                asyncio.create_task(models.get_all_stock_counts())
                for _ in range(10)
            ]
            await started.wait()
            await asyncio.sleep(0)
            release.set()
            results = await asyncio.gather(*tasks)

        self.assertEqual(calls, 1)
        self.assertEqual(results, [{4: 8}] * 10)


class ProductViewCacheTests(unittest.TestCase):
    def setUp(self):
        product_handlers._PRODUCT_LIST_VIEW_CACHE.clear()
        product_handlers._PRODUCT_DETAIL_VIEW_CACHE.clear()
        product_handlers._PRODUCT_VIEW_CACHE_GENERATION = -1
        self.product = {
            "id": 4,
            "name": "Gemini",
            "emoji": "G",
            "price_usd": 0.55,
            "delivery_type": "stock",
            "warranty_days": 30,
            "description": "Private account",
        }

    def test_product_list_precomputes_all_languages_once(self):
        keyboard = Mock(side_effect=lambda _p, _s, language: language)
        with patch(
            "handlers.products.get_catalog_cache_generation",
            return_value=12,
        ), patch("handlers.products.products_keyboard", keyboard):
            first = product_handlers._precomputed_product_list_view(
                [self.product], {4: 8}, "en", None
            )
            second = product_handlers._precomputed_product_list_view(
                [self.product], {4: 8}, "fr", None
            )

        self.assertEqual(keyboard.call_count, len(LANGUAGES))
        self.assertEqual(first[1], "en")
        self.assertEqual(second[1], "fr")

    def test_generation_change_rebuilds_precomputed_details(self):
        generation = {"value": 20}
        text_builder = Mock(
            side_effect=lambda _p, _s, _t, _sold, language, **_kwargs: language
        )
        keyboard = Mock(side_effect=lambda _id, language, **_kwargs: language)
        with patch(
            "handlers.products.get_catalog_cache_generation",
            side_effect=lambda: generation["value"],
        ), patch(
            "handlers.products._build_product_detail_text",
            text_builder,
        ), patch("handlers.products.product_detail_keyboard", keyboard):
            product_handlers._precomputed_product_detail_view(
                self.product, 8, [], 3, "en"
            )
            product_handlers._precomputed_product_detail_view(
                self.product, 8, [], 3, "fr"
            )
            generation["value"] += 1
            product_handlers._precomputed_product_detail_view(
                self.product, 8, [], 3, "en"
            )

        self.assertEqual(text_builder.call_count, len(LANGUAGES) * 2)
        self.assertEqual(keyboard.call_count, len(LANGUAGES) * 2)


if __name__ == "__main__":
    unittest.main()
