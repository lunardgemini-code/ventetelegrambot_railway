"""Regression tests for the second performance pass.

Covers: batched supplier catalogue upserts, probe-before-write in the expiry
and maintenance workers, pooled (non-fresh) connections on hot paths,
snapshot-backed stock counts, post-commit cache invalidation, the O(1) webhook
dedupe sweep, HTTP keep-alive limits, and the dashboard frontend changes.
"""

import asyncio
import pathlib
import time
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import bot
from database import audit as audit_db
from database import jobs as jobs_db
from database import models

DASHBOARD = pathlib.Path(__file__).resolve().parents[1] / "dashboard"


def _cursor(rows=None, one=None, rowcount=0):
    return SimpleNamespace(
        fetchall=AsyncMock(return_value=rows if rows is not None else []),
        fetchone=AsyncMock(return_value=one),
        rowcount=rowcount,
        lastrowid=1,
    )


class PooledConnectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_order_status_first_attempt_uses_the_pool(self):
        once = AsyncMock(return_value=True)
        with patch("database.models._update_order_status_once", once):
            await models.update_order_status(1, "COMPLETED")
        self.assertFalse(once.await_args_list[0].kwargs["fresh_connection"])

    async def test_audit_flush_uses_the_pool(self):
        fake_db = SimpleNamespace(
            executemany=AsyncMock(), commit=AsyncMock(), close=AsyncMock()
        )
        get_db = AsyncMock(return_value=fake_db)
        with patch("database.audit.get_db", get_db):
            await audit_db.insert_admin_audit_events(
                [{"event_uid": "a", "method": "POST", "path": "/api/x", "status_code": 200}]
            )
        self.assertEqual(get_db.await_args.kwargs, {})


class ProbeBeforeWriteTests(unittest.IsolatedAsyncioTestCase):
    async def test_stale_order_expiry_skips_writer_lock_when_nothing_is_stale(self):
        probe_db = SimpleNamespace(
            execute=AsyncMock(return_value=_cursor(one=None)), close=AsyncMock()
        )
        get_db = AsyncMock(return_value=probe_db)
        with patch("database.models.get_db", get_db):
            result = await models.expire_stale_orders()
        self.assertEqual(result, [])
        # Exactly one pooled probe: no fresh connection, no BEGIN IMMEDIATE.
        self.assertEqual(get_db.await_count, 1)
        self.assertNotIn(
            "BEGIN", str(probe_db.execute.await_args_list[0].args[0]).upper()
        )

    async def test_cryptopay_expiry_skips_writer_lock_when_nothing_is_stale(self):
        probe_db = SimpleNamespace(
            execute=AsyncMock(return_value=_cursor(one=None)), close=AsyncMock()
        )
        get_db = AsyncMock(return_value=probe_db)
        with patch("database.models.get_db", get_db):
            result = await models.expire_stale_cryptopay_invoices()
        self.assertEqual(result, [])
        self.assertEqual(get_db.await_count, 1)

    async def test_nowpayments_expiry_skips_writer_lock_when_nothing_is_stale(self):
        probe_db = SimpleNamespace(
            execute=AsyncMock(return_value=_cursor(one=None)), close=AsyncMock()
        )
        get_db = AsyncMock(return_value=probe_db)
        with patch("database.models.get_db", get_db):
            result = await models._expire_stale_nowpayments_payments_once()
        self.assertEqual(result, [])
        self.assertEqual(get_db.await_count, 1)

    async def test_requeue_stale_jobs_probes_before_updating(self):
        fake_db = SimpleNamespace(
            execute=AsyncMock(return_value=_cursor(one=None)),
            commit=AsyncMock(),
            close=AsyncMock(),
        )
        with patch("database.jobs.get_db", AsyncMock(return_value=fake_db)):
            recovered = await jobs_db.requeue_stale_background_jobs()
        self.assertEqual(recovered, 0)
        self.assertEqual(fake_db.execute.await_count, 1)
        self.assertIn("SELECT", str(fake_db.execute.await_args.args[0]).upper())
        fake_db.commit.assert_not_awaited()


class StockCountSnapshotTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_stock_count_reads_the_shared_snapshot(self):
        snapshot = AsyncMock(return_value={7: 5})
        with patch("database.models.get_all_stock_counts", snapshot):
            self.assertEqual(await models.get_stock_count(7), 5)
            self.assertEqual(await models.get_stock_count(999), 0)
        self.assertEqual(snapshot.await_count, 2)

    async def test_negative_or_missing_counts_clamp_to_zero(self):
        with patch("database.models.get_all_stock_counts", AsyncMock(return_value={7: -3})):
            self.assertEqual(await models.get_stock_count(7), 0)


class CacheInvalidationOrderTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_op_status_update_keeps_catalogue_caches_warm(self):
        order = {"id": 1, "status": "COMPLETED", "payment_method": "wallet"}
        fake_db = SimpleNamespace(
            execute=AsyncMock(return_value=_cursor(one=order)),
            commit=AsyncMock(),
            rollback=AsyncMock(),
            close=AsyncMock(),
        )
        before = models.get_catalog_cache_generation()
        with patch("database.models.get_db", AsyncMock(return_value=fake_db)):
            transitioned = await models._update_order_status_once(1, "COMPLETED")
        self.assertFalse(transitioned)
        # A no-op update must not evict every user's warm catalogue view.
        self.assertEqual(models.get_catalog_cache_generation(), before)

    async def test_real_transition_invalidates_the_catalogue(self):
        order = {"id": 1, "status": "PENDING", "payment_method": "wallet"}
        fake_db = SimpleNamespace(
            execute=AsyncMock(return_value=_cursor(one=order)),
            commit=AsyncMock(),
            rollback=AsyncMock(),
            close=AsyncMock(),
        )
        before = models.get_catalog_cache_generation()
        with patch("database.models.get_db", AsyncMock(return_value=fake_db)):
            transitioned = await models._update_order_status_once(1, "AWAITING_PAYMENT")
        self.assertTrue(transitioned)
        self.assertNotEqual(models.get_catalog_cache_generation(), before)


class WebhookDedupeSweepTests(unittest.TestCase):
    def setUp(self):
        bot._webhook_recent_update_ids.clear()

    def tearDown(self):
        bot._webhook_recent_update_ids.clear()

    def test_sweep_evicts_only_expired_entries_from_the_front(self):
        now = time.monotonic()
        for update_id in range(6000):
            bot._webhook_recent_update_ids[update_id] = now - 700
        fresh_id = 999999
        bot._webhook_recent_update_ids[fresh_id] = now
        cutoff = now - bot.WEBHOOK_UPDATE_DEDUPE_SECONDS
        while bot._webhook_recent_update_ids:
            oldest = next(iter(bot._webhook_recent_update_ids))
            if bot._webhook_recent_update_ids[oldest] >= cutoff:
                break
            bot._webhook_recent_update_ids.pop(oldest, None)
        self.assertEqual(list(bot._webhook_recent_update_ids), [fresh_id])

    def test_completion_reinsert_keeps_the_map_ordered(self):
        bot._webhook_recent_update_ids[1] = 100.0
        bot._webhook_recent_update_ids[2] = 101.0
        bot._webhook_recent_update_ids.pop(1, None)
        bot._webhook_recent_update_ids[1] = 102.0
        self.assertEqual(list(bot._webhook_recent_update_ids), [2, 1])


class HttpKeepAliveTests(unittest.TestCase):
    def test_periodic_clients_declare_a_keepalive_window(self):
        root = pathlib.Path(__file__).resolve().parents[1] / "services"
        for name in (
            "nowpayments.py",
            "crypto_pay.py",
            "supplier_api.py",
            "supplier_multi_api.py",
            "sports_api.py",
            "binance_verify.py",
            "blockchain_verify.py",
        ):
            source = (root / name).read_text(encoding="utf-8")
            self.assertIn("keepalive_expiry", source, f"{name} rebuilds TLS per poll")


class SupplierSyncBatchTests(unittest.TestCase):
    def test_catalogue_upserts_are_batched(self):
        source = (
            pathlib.Path(__file__).resolve().parents[1] / "database" / "suppliers.py"
        ).read_text(encoding="utf-8")
        marker = source.index("upsert_params")
        batched = source.index("await db.executemany(", marker)
        self.assertGreater(batched, marker)
        # The old per-product execute inside the changes loop must be gone.
        loop_start = source.index("for existing, incoming, changed_fields in changes:")
        loop_end = source.index("if upsert_params:", loop_start)
        self.assertNotIn("await db.execute(", source[loop_start:loop_end])


class DashboardFrontendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_js = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        cls.index = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        cls.worker = (DASHBOARD / "service-worker.js").read_text(encoding="utf-8")

    def test_arabic_inherits_the_english_base(self):
        # LANG.ar was spreading itself (undefined), silently falling back to French.
        self.assertIn("LANG.ar = {...LANG.en,", self.app_js)
        self.assertNotIn("LANG.ar = {...LANG.ar,", self.app_js)

    def test_every_locale_inherits_a_base(self):
        for locale in ("zh", "vi", "ru", "ar"):
            self.assertIn(f"LANG.{locale} = {{...LANG.en,", self.app_js)

    def test_export_libraries_are_not_eagerly_loaded(self):
        for library in ("xlsx.full.min.js", "jspdf.umd.min.js", "jspdf.plugin.autotable"):
            self.assertNotIn(library, self.index, f"{library} still blocks page load")
        self.assertIn("loadExportLibraries", self.app_js)
        # SRI must survive the move to dynamic injection.
        self.assertIn("script.integrity = integrity;", self.app_js)
        self.assertIn("sha384-vtjasyidUo0kW94K5MXDXntzOJpQgBKXmE7e2Ga4LG0skTTLeBi97eFAXsqewJjw", self.app_js)

    def test_chart_and_sortable_stay_eager(self):
        self.assertIn("chart.umd.min.js", self.index)
        self.assertIn("Sortable.min.js", self.index)

    def test_recent_orders_are_rendered_once(self):
        self.assertEqual(self.app_js.count("DOM.recentOrdersList.innerHTML"), 0)
        operations = (DASHBOARD / "operations.js").read_text(encoding="utf-8")
        self.assertEqual(operations.count("DOM.recentOrdersList.innerHTML"), 1)

    def test_poll_renders_are_diffed(self):
        self.assertIn("function renderPayloadUnchanged(", self.app_js)
        self.assertIn("renderPayloadUnchanged('payment-review', data)", self.app_js)
        # A language switch must force a re-render despite an identical payload.
        self.assertIn("invalidateRenderSignatures();", self.app_js)

    def test_service_worker_shell_matches_the_shipped_versions(self):
        for asset in ("app.js?v=20260802-same-time-comparison-v1", "operations.js?v=20260726-targeted-broadcast-v1"):
            self.assertIn(asset, self.index)
            self.assertIn(asset, self.worker)
        self.assertIn("ventebot-dashboard-shell-20260802-same-time-comparison-v1", self.worker)


if __name__ == "__main__":
    unittest.main()
