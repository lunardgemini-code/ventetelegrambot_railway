import asyncio
import unittest
from unittest.mock import AsyncMock, patch

import bot
from services import product_warm_cache


class SnappyV3PerformanceTests(unittest.IsolatedAsyncioTestCase):
    def test_product_warm_cache_interval_is_at_least_90s(self):
        self.assertGreaterEqual(bot.PRODUCT_WARM_CACHE_SECONDS, 60)
        self.assertEqual(bot.PRODUCT_WARM_CACHE_SECONDS, 90)

    async def test_preload_active_products_uses_bounded_concurrency(self):
        fake_products = [{"id": i, "is_active": 1} for i in range(1, 10)]

        async def fake_get_details(pid):
            await asyncio.sleep(0.001)
            return ({"id": pid}, 1, [], 1)

        with patch("services.product_warm_cache.get_all_products", AsyncMock(return_value=fake_products)), \
             patch("services.product_warm_cache.get_all_stock_counts", AsyncMock(return_value={i: 5 for i in range(1, 10)})), \
             patch("services.product_warm_cache.get_product_full_details", AsyncMock(side_effect=fake_get_details)):
            warmed = await product_warm_cache.preload_active_products(limit=9)
            self.assertEqual(warmed, 9)
            self.assertTrue(product_warm_cache.is_warm_preload_ready())


if __name__ == "__main__":
    unittest.main()
