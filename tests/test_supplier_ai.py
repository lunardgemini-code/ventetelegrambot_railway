import os
import tempfile
import unittest
from unittest.mock import patch

from database import db as db_module
from database import models
from database.db import init_db
from database.suppliers import sync_supplier_products, update_supplier_wallet_snapshot
from services.supplier_ai import (
    analyze_supplier_catalog,
    list_supplier_product_groups,
    search_supplier_catalog,
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
            if item["family"] == "grok"
            and item["duration_months"] == 1
            and item["warranty_kind"] == "full"
        )
        self.assertEqual(group["offer_count"], 2)
        self.assertEqual(
            [offer["external_product_id"] for offer in group["offers"]],
            ["grok-cheaper", "grok-month-warranty"],
        )
        self.assertEqual(group["best_price"], 1.5)

    def test_french_duration_and_product_constraints_are_parsed(self):
        signature = extract_product_signature(
            "Grok 1 mois garantie complete prive",
            "Compte fourni avec mot de passe",
        )
        self.assertEqual(signature["family"], "grok")
        self.assertEqual(signature["duration_months"], 1)
        self.assertEqual(signature["delivery_mode"], "account")
        self.assertEqual(signature["access"], "private")
