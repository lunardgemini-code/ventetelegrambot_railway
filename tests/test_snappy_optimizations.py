"""Tests for Snappy V1 performance optimizations."""

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from database.jobs import create_background_job
from services.background_jobs import notify_background_job_enqueued
from services.http_pool import close_http_pools, get_shared_http_client
from services.product_warm_cache import preload_active_products
from services.runtime_metrics import (
    get_runtime_snapshot,
    record_cache_access,
    reset_runtime_metrics_for_tests,
)


class TestSnappyOptimizations(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        reset_runtime_metrics_for_tests()

    async def asyncTearDown(self):
        await close_http_pools()

    def test_cache_metrics_recording(self):
        record_cache_access("product_details", hit=True)
        record_cache_access("product_details", hit=True, stale=True)
        record_cache_access("product_details", hit=False)

        snapshot = get_runtime_snapshot(window_seconds=60)
        cache_stats = snapshot.get("cache", {})

        self.assertEqual(cache_stats.get("hits"), 1)
        self.assertEqual(cache_stats.get("stale_hits"), 1)
        self.assertEqual(cache_stats.get("misses"), 1)
        self.assertAlmostEqual(cache_stats.get("hit_ratio_percent"), 66.7, places=1)

    async def test_persistent_http_client(self):
        client1 = await get_shared_http_client()
        client2 = await get_shared_http_client()
        self.assertIs(client1, client2)
        self.assertFalse(client1.is_closed)

        await close_http_pools()
        self.assertTrue(client1.is_closed)

    async def test_job_enqueued_notification(self):
        # Verify notify_background_job_enqueued runs safely without throwing
        notify_background_job_enqueued()

    async def test_product_warm_preload(self):
        warmed = await preload_active_products(limit=5)
        self.assertIsInstance(warmed, int)
        self.assertGreaterEqual(warmed, 0)


if __name__ == "__main__":
    unittest.main()
