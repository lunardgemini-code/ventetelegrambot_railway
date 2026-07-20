import asyncio
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from database import db as db_module
from database import models
from database.db import init_db
from database.suppliers import sync_supplier_products, update_supplier_wallet_snapshot
from services.supplier_ai import (
    _gemini_analyze_batch,
    _gemini_batch_with_heartbeat,
    _merge_ai,
    _run_supplier_ai_job,
    analyze_supplier_catalog,
    list_supplier_product_groups,
    run_supplier_ai_auto_cycle_once,
    search_supplier_catalog,
    supplier_ai_job_worker,
    supplier_ai_pressure_reason,
)
from services.supplier_router import extract_product_signature


class SupplierAISearchTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["DB_PATH"] = os.path.join(self.temp_dir.name, "supplier-ai.db")
        db_module.TURSO_URL = ""
        db_module._sqlite_wal_configured = False
        models.clear_products_cache()
        await init_db()
        self.provider = {
            "code": "canboso",
            "name": "Supplier One",
            "base_url": "https://supplier.invalid",
        }
        await sync_supplier_products(
            [
                {
                    "external_product_id": "grok-month-warranty",
                    "name": "Grok 1 month private account full warranty",
                    "description": "Private ready account with email and password",
                    "base_price": 2.0,
                    "remote_stock": 5,
                    "warranty_days": 25,
                },
                {
                    "external_product_id": "grok-month-no-warranty",
                    "name": "Grok 1 month private account no warranty",
                    "description": "Private ready account",
                    "base_price": 1.0,
                    "remote_stock": 9,
                    "warranty_days": 0,
                },
                {
                    "external_product_id": "grok-month-short-warranty",
                    "name": "Grok 1 month private account warranty",
                    "description": "Private ready account with a 7 day warranty",
                    "base_price": 0.9,
                    "remote_stock": 9,
                    "warranty_days": 7,
                },
                {
                    "external_product_id": "grok-week",
                    "name": "Grok 7 days private account warranty",
                    "description": "Private account",
                    "base_price": 0.5,
                    "remote_stock": 9,
                    "warranty_days": 7,
                },
                {
                    "external_product_id": "chatgpt-month",
                    "name": "ChatGPT 1 month private account warranty",
                    "description": "Private account",
                    "base_price": 0.8,
                    "remote_stock": 9,
                    "warranty_days": 30,
                },
            ],
            "canboso",
        )
        await update_supplier_wallet_snapshot("canboso", {"balance": 5.0})

    async def asyncTearDown(self):
        self.temp_dir.cleanup()

    async def _analyze(self):
        with patch("services.supplier_ai._configured_providers", return_value=[self.provider]):
            return await analyze_supplier_catalog(use_ai=False)

    async def _search(self, payload):
        with patch("services.supplier_ai._configured_providers", return_value=[self.provider]):
            return await search_supplier_catalog(payload)

    def test_auto_cycle_detects_webhook_and_database_pressure(self):
        self.assertEqual(
            supplier_ai_pressure_reason({"queue": {"current": 2}}),
            "webhook_queue",
        )
        self.assertEqual(
            supplier_ai_pressure_reason({"database": {"p95_ms": 800}}),
            "database",
        )
        self.assertEqual(
            supplier_ai_pressure_reason(
                {"database": {"p95_ms": 800}},
                include_historical=False,
            ),
            "",
        )
        self.assertEqual(
            supplier_ai_pressure_reason({
                "queue": {"current": 0, "p95_wait_ms": 20},
                "workers": {"utilization_1m": 0.2},
                "diagnosis": {"bottleneck": "healthy"},
            }),
            "",
        )

    async def test_auto_cycle_waits_while_clients_are_queued(self):
        enqueue = AsyncMock()
        with patch("services.supplier_ai.enqueue_supplier_ai_sync", enqueue):
            result = await run_supplier_ai_auto_cycle_once(
                lambda: {"queue": {"current": 1}}
            )

        self.assertEqual(result, {"status": "deferred", "reason": "webhook_queue"})
        enqueue.assert_not_awaited()

    async def test_auto_cycle_queues_sync_and_records_schedule(self):
        enqueue = AsyncMock(return_value=({"job_id": "auto-sync-1"}, True))
        setting = AsyncMock()
        with patch("services.supplier_ai.enqueue_supplier_ai_sync", enqueue), patch(
            "services.supplier_ai.set_setting", setting
        ):
            result = await run_supplier_ai_auto_cycle_once(
                lambda: {
                    "queue": {"current": 0},
                    "workers": {"utilization_1m": 0.1},
                    "diagnosis": {"bottleneck": "healthy"},
                }
            )

        self.assertEqual(result["status"], "queued")
        enqueue.assert_awaited_once_with(
            use_ai=True,
            automatic=True,
            auto_analyze=True,
        )
        setting.assert_awaited_once()

    async def test_auto_sync_chains_incremental_ai_analysis(self):
        job = {
            "id": "auto-sync-job",
            "payload": {
                "supplier_codes": ["canboso"],
                "automatic": True,
                "auto_analyze": True,
                "use_ai": True,
            },
            "cursor_value": 0,
            "progress_done": 0,
            "progress_failed": 0,
        }
        with patch(
            "services.supplier_ai.sync_supplier_catalog",
            AsyncMock(return_value={"status": "synced", "synced": 5}),
        ), patch(
            "services.supplier_ai.update_background_job_progress", AsyncMock()
        ), patch(
            "services.supplier_ai.complete_background_job", AsyncMock()
        ), patch(
            "services.supplier_ai.set_setting", AsyncMock()
        ), patch(
            "services.supplier_ai.enqueue_supplier_ai_analysis",
            AsyncMock(return_value=({"job_id": "analysis-1"}, True)),
        ) as enqueue_analysis:
            await _run_supplier_ai_job(job)

        enqueue_analysis.assert_awaited_once_with(
            use_ai=True,
            force=False,
            automatic=True,
        )

    async def test_automatic_job_is_requeued_if_pressure_appears(self):
        job = {
            "id": "auto-analysis-job",
            "job_type": "supplier_ai_analyze",
            "payload": {"automatic": True},
        }
        claim = AsyncMock(side_effect=[job, asyncio.CancelledError()])
        defer = AsyncMock(return_value=True)
        with patch("services.supplier_ai.claim_next_background_job", claim), patch(
            "services.supplier_ai.defer_background_job", defer
        ):
            with self.assertRaises(asyncio.CancelledError):
                await supplier_ai_job_worker(
                    lambda: {"queue": {"current": 3}}
                )

        defer.assert_awaited_once_with(
            "auto-analysis-job",
            delay_seconds=300,
            reason="Deferred while bot is under pressure: webhook_queue",
        )

    async def test_strict_search_excludes_wrong_duration_family_and_missing_warranty(self):
        result = await self._analyze()
        self.assertEqual(result["total"], 5)
        response = await self._search({
            "query": "Grok 1 month full warranty private",
            "include_unfunded": False,
        })
        self.assertEqual(response["count"], 1)
        self.assertEqual(response["intent"]["min_warranty_days"], 24)
        self.assertEqual(
            response["results"][0]["external_product_id"],
            "grok-month-warranty",
        )
        self.assertEqual(response["results"][0]["affordable_stock"], 2)
        self.assertIn("fiabilité", response["results"][0]["reason"])
        self.assertIn("unités achetables", response["results"][0]["reason"])

    async def test_wallet_filter_hides_unaffordable_products_but_can_be_overridden(self):
        await self._analyze()
        await update_supplier_wallet_snapshot("canboso", {"balance": 0.0})
        hidden = await self._search({
            "query": "Grok 1 month full warranty",
            "include_unfunded": False,
        })
        self.assertEqual(hidden["count"], 0)
        self.assertEqual(hidden["hidden_unfunded_count"], 1)
        visible = await self._search({
            "query": "Grok 1 month full warranty",
            "include_unfunded": True,
        })
        self.assertEqual(visible["count"], 1)
        self.assertEqual(visible["hidden_unfunded_count"], 0)
        self.assertEqual(visible["results"][0]["affordable_stock"], 0)

    async def test_reanalysis_reuses_unchanged_index_rows(self):
        first = await self._analyze()
        second = await self._analyze()
        self.assertEqual(first["changed"], 5)
        self.assertEqual(second["changed"], 0)
        self.assertEqual(second["reused"], 5)

    async def test_forced_analysis_rebuilds_the_complete_catalog(self):
        await self._analyze()
        with patch("services.supplier_ai._configured_providers", return_value=[self.provider]):
            result = await analyze_supplier_catalog(use_ai=False, force=True)
        self.assertEqual(result["changed"], 5)
        self.assertEqual(result["reused"], 0)
        self.assertTrue(result["forced"])

    async def test_gemini_analysis_falls_back_from_an_unavailable_model(self):
        class FakeResponse:
            def __init__(self, status_code, payload):
                self.status_code = status_code
                self._payload = payload

            def raise_for_status(self):
                if self.status_code >= 400:
                    raise RuntimeError(f"HTTP {self.status_code}")

            def json(self):
                return self._payload

        class FakeClient:
            def __init__(self):
                self.urls = []

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

            async def post(self, url, **_kwargs):
                self.urls.append(url)
                if len(self.urls) == 1:
                    return FakeResponse(404, {"error": {"message": "unavailable"}})
                return FakeResponse(200, {
                    "candidates": [{
                        "content": {"parts": [{"text": '{"products":[{"id":1,"family":"grok","confidence":0.9}]}' }]}
                    }]
                })

        client = FakeClient()
        with patch.dict(os.environ, {
            "GEMINI_API_KEY": "test-key",
            "GEMINI_CATALOG_MODEL": "gemini-2.5-flash",
        }, clear=False), patch(
            "services.supplier_ai.httpx.AsyncClient", return_value=client
        ):
            result = await _gemini_analyze_batch([{
                "id": 1,
                "name": "Grok 1 month",
                "description": "Private account",
            }])
        self.assertEqual(result[1]["family"], "grok")
        self.assertIn("gemini-2.5-flash:generateContent", client.urls[0])
        self.assertIn("gemini-3.1-flash-lite:generateContent", client.urls[1])

    async def test_complete_ai_analysis_reviews_every_product(self):
        reviewed_ids = []

        async def classify(products):
            reviewed_ids.extend(int(product["id"]) for product in products)
            return {
                int(product["id"]): {
                    "id": int(product["id"]),
                    "family": "grok" if "grok" in product["name"].lower() else "chatgpt",
                    "duration_months": 1,
                    "duration_days": None,
                    "delivery_mode": "account",
                    "access_mode": "private",
                    "region": "GLOBAL",
                    "confidence": 0.91,
                }
                for product in products
            }

        with patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"}, clear=False), patch(
            "services.supplier_ai._gemini_analyze_batch", side_effect=classify
        ), patch("services.supplier_ai._configured_providers", return_value=[self.provider]):
            result = await analyze_supplier_catalog(use_ai=True, force=True)

        self.assertEqual(len(reviewed_ids), 5)
        self.assertEqual(len(set(reviewed_ids)), 5)
        self.assertEqual(result["ai_reviewed"], 5)
        self.assertEqual(result["ai_used"], 5)

    async def test_slow_gemini_batch_keeps_the_job_heartbeat_alive(self):
        heartbeat = AsyncMock()

        async def slow_analysis(_products):
            await asyncio.sleep(0.04)
            return {1: {"id": 1, "family": "grok"}}

        with patch("services.supplier_ai._AI_HEARTBEAT_SECONDS", 0.01), patch(
            "services.supplier_ai._gemini_analyze_batch", side_effect=slow_analysis
        ):
            result = await _gemini_batch_with_heartbeat(
                [{"id": 1}], heartbeat=heartbeat, reviewed=20, total=100
            )

        self.assertEqual(result[1]["family"], "grok")
        self.assertGreaterEqual(heartbeat.await_count, 2)
        heartbeat.assert_awaited_with(20, 100)

    async def test_catalog_index_writes_are_split_into_small_turso_batches(self):
        products = [
            {
                "id": product_id,
                "supplier_code": "canboso",
                "name": f"Grok {product_id} month",
                "description": "Private account",
                "warranty_days": 0,
                "indexed_source_hash": "",
            }
            for product_id in range(1, 96)
        ]
        writer = AsyncMock(side_effect=lambda rows: len(rows))
        with patch(
            "services.supplier_ai.list_supplier_products_for_analysis",
            new=AsyncMock(return_value=products),
        ), patch(
            "services.supplier_ai.upsert_supplier_product_analysis",
            new=writer,
        ), patch("services.supplier_ai._configured_providers", return_value=[self.provider]):
            result = await analyze_supplier_catalog(use_ai=False, force=True)

        self.assertEqual(result["indexed"], 95)
        self.assertEqual([len(call.args[0]) for call in writer.await_args_list], [40, 40, 15])

    def test_ai_classification_overrides_deterministic_fields(self):
        deterministic = {
            "family": "chatgpt",
            "duration_months": 12,
            "duration_days": None,
            "delivery_mode": "account",
            "access_mode": "shared",
            "region": "US",
            "confidence": 0.98,
            "analysis_source": "deterministic",
        }
        merged = _merge_ai(deterministic, {
            "family": "grok",
            "duration_months": 1,
            "duration_days": None,
            "delivery_mode": "activation",
            "access_mode": "private",
            "region": "GLOBAL",
            "confidence": 0.87,
        })
        self.assertEqual(merged["family"], "grok")
        self.assertEqual(merged["duration_months"], 1)
        self.assertEqual(merged["delivery_mode"], "activation")
        self.assertEqual(merged["access_mode"], "private")
        self.assertEqual(merged["region"], "GLOBAL")
        self.assertEqual(merged["confidence"], 0.87)
        self.assertEqual(merged["analysis_source"], "gemini")

    async def test_similar_products_are_grouped_with_the_cheapest_offer_first(self):
        second_provider = {
            "code": "nanlux",
            "name": "Supplier Two",
            "base_url": "https://second.invalid",
        }
        await sync_supplier_products(
            [{
                "external_product_id": "grok-cheaper",
                "name": "Grok 1 month private account full warranty",
                "description": "Private ready account with email and password",
                "base_price": 1.5,
                "remote_stock": 4,
                "warranty_days": 30,
            }],
            "nanlux",
        )
        await update_supplier_wallet_snapshot("nanlux", {"balance": 10.0})
        providers = [self.provider, second_provider]
        with patch("services.supplier_ai._configured_providers", return_value=providers):
            await analyze_supplier_catalog(use_ai=False, force=True)
            response = await list_supplier_product_groups()
        group = next(
            item for item in response["groups"]
            if item["family"] == "grok" and item["duration_months"] == 1
        )
        self.assertEqual(group["offer_count"], 4)
        self.assertEqual(group["warranty_kind"], "mixed")
        self.assertEqual(group["warranty_label"], "Garanties variées")
        self.assertIn("1 mois · Garanties variées", group["signature"])
        self.assertEqual(
            [offer["external_product_id"] for offer in group["offers"]],
            [
                "grok-month-short-warranty",
                "grok-month-no-warranty",
                "grok-cheaper",
                "grok-month-warranty",
            ],
        )
        self.assertEqual(group["best_price"], 0.9)

    def test_french_duration_and_product_constraints_are_parsed(self):
        signature = extract_product_signature(
            "Grok 1 mois garantie complete prive",
            "Compte fourni avec mot de passe",
        )
        self.assertEqual(signature["family"], "grok")
        self.assertEqual(signature["duration_months"], 1)
        self.assertEqual(signature["delivery_mode"], "account")
        self.assertEqual(signature["access"], "private")
