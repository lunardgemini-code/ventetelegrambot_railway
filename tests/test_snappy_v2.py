"""Tests for Snappy V2 performance optimizations."""

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from services.runtime_metrics import (
    get_runtime_snapshot,
    reset_runtime_metrics_for_tests,
)
from services.supplier_multi_api import get_all_supplier_balances_parallel
from utils.keyboards import (
    back_keyboard,
    clear_keyboard_cache,
    language_keyboard,
    main_menu_keyboard,
    reply_menu_keyboard,
)


class TestSnappyV2Optimizations(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        reset_runtime_metrics_for_tests()
        clear_keyboard_cache()

    def test_keyboard_caching(self):
        # First calls -> cache miss
        kb1 = main_menu_keyboard("fr")
        kb2 = language_keyboard()
        kb3 = reply_menu_keyboard("en")
        kb4 = back_keyboard("back_main", "fr")

        # Second calls -> cache hit
        kb1_cached = main_menu_keyboard("fr")
        kb2_cached = language_keyboard()
        kb3_cached = reply_menu_keyboard("en")
        kb4_cached = back_keyboard("back_main", "fr")

        self.assertIs(kb1, kb1_cached)
        self.assertIs(kb2, kb2_cached)
        self.assertIs(kb3, kb3_cached)
        self.assertIs(kb4, kb4_cached)

        snapshot = get_runtime_snapshot(window_seconds=60)
        cache_stats = snapshot.get("cache", {})
        self.assertGreaterEqual(cache_stats.get("hits"), 4)

        # Clear cache
        clear_keyboard_cache()
        kb1_new = main_menu_keyboard("fr")
        self.assertIsNot(kb1_cached, kb1_new)

    async def test_parallel_supplier_balances(self):
        mock_provider1 = {"code": "sup1", "adapter": "canboso", "base_url": "http://mock1", "api_key": "k1"}
        mock_provider2 = {"code": "sup2", "adapter": "tunvn", "base_url": "http://mock2", "api_key": "k2"}

        with patch("services.supplier_multi_api.get_balance", side_effect=[
            {"balance": 150.0, "currency": "USD"},
            {"balance": 320.0, "currency": "VND"},
        ]):
            results = await get_all_supplier_balances_parallel(
                [mock_provider1, mock_provider2],
                units_per_usd_map={"sup1": 1.0, "sup2": 25000.0},
                force=True,
                timeout=1.0,
            )
            self.assertIn("sup1", results)
            self.assertIn("sup2", results)
            self.assertEqual(results["sup1"]["balance"], 150.0)


if __name__ == "__main__":
    unittest.main()
