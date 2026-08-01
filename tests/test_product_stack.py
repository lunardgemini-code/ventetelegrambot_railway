"""Tests for Product Stack feature with stable sorting and visual separators."""

import unittest
from unittest.mock import AsyncMock, patch

from database.models import get_product_stack_mode, set_product_stack_mode
from utils.keyboards import products_keyboard, sort_products_out_of_stock_first


class ProductStackTests(unittest.IsolatedAsyncioTestCase):

    async def test_product_stack_mode_setter_getter(self):
        with patch("database.models.get_setting", AsyncMock(return_value="stack")):
            mode = await get_product_stack_mode()
            self.assertEqual(mode, "stack")

        with patch("database.models.set_setting", AsyncMock()) as mock_set:
            res = await set_product_stack_mode("hide")
            self.assertEqual(res, "hide")
            mock_set.assert_awaited_once_with("product_stack_mode", "hide")

    def test_products_keyboard_stable_sorting_and_separator(self):
        products = [
            {"id": 1, "name": "IPTV 1M", "price_usd": 10.0, "delivery_type": "stock"},
            {"id": 2, "name": "Netflix 4K", "price_usd": 15.0, "delivery_type": "stock"},
            {"id": 3, "name": "Spotify 1Y", "price_usd": 8.0, "delivery_type": "stock"},
            {"id": 4, "name": "Disney+", "price_usd": 12.0, "delivery_type": "stock"},
        ]
        stock_counts = {1: 10, 2: 0, 3: 5, 4: 0}

        sorted_prods = sort_products_out_of_stock_first(products, stock_counts)

        # Unavailable products are grouped first; each group keeps manual order.
        self.assertEqual([p["id"] for p in sorted_prods], [2, 4, 1, 3])

        # Test products_keyboard with show_stack_separator=True
        keyboard = products_keyboard(sorted_prods, stock_counts, lang="fr", show_stack_separator=True)
        inline_rows = keyboard.inline_keyboard

        # Find row containing the visual separator
        separator_row = [r for r in inline_rows if len(r) == 1 and "EN RUPTURE DE STOCK" in r[0].text]
        self.assertEqual(len(separator_row), 1)
        self.assertEqual(separator_row[0][0].callback_data, "noop")

        # A restocked product automatically returns to its manual position in
        # the available group; no database sort_order update is needed.
        stock_counts[2] = 2
        restocked_prods = sort_products_out_of_stock_first(products, stock_counts)
        self.assertEqual([p["id"] for p in restocked_prods], [4, 1, 2, 3])

    def test_products_keyboard_without_stack_separator(self):
        products = [
            {"id": 1, "name": "IPTV 1M", "price_usd": 10.0, "delivery_type": "stock"},
            {"id": 2, "name": "Netflix 4K", "price_usd": 15.0, "delivery_type": "stock"},
        ]
        stock_counts = {1: 10, 2: 0}

        keyboard = products_keyboard(products, stock_counts, lang="fr", show_stack_separator=False)
        inline_rows = keyboard.inline_keyboard

        separator_row = [r for r in inline_rows if len(r) == 1 and "EN RUPTURE DE STOCK" in r[0].text]
        self.assertEqual(len(separator_row), 0)


if __name__ == "__main__":
    unittest.main()
