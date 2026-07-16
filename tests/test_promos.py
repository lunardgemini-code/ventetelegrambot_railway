import unittest

from utils.promos import calculate_promo_price, parse_applicable_product_ids


class PromoPricingTests(unittest.TestCase):
    def test_product_price_is_applied_per_unit(self):
        discount, total = calculate_promo_price(2.85, 3, "product_price", 0.47)

        self.assertAlmostEqual(discount, 1.44)
        self.assertAlmostEqual(total, 1.41)

    def test_product_price_never_increases_a_lower_order_total(self):
        discount, total = calculate_promo_price(0.45, 1, "product_price", 0.47)

        self.assertEqual(discount, 0.0)
        self.assertEqual(total, 0.45)

    def test_existing_percent_and_fixed_discounts_are_unchanged(self):
        percent_discount, percent_total = calculate_promo_price(10, 1, "percent", 20)
        fixed_discount, fixed_total = calculate_promo_price(10, 1, "fixed", 1.5)

        self.assertEqual((percent_discount, percent_total), (2.0, 8.0))
        self.assertEqual((fixed_discount, fixed_total), (1.5, 8.5))

    def test_discount_is_clamped_to_the_order_total(self):
        discount, total = calculate_promo_price(1, 1, "fixed", 5)

        self.assertEqual(discount, 1.0)
        self.assertEqual(total, 0.0)

    def test_product_ids_are_normalized_and_deduplicated(self):
        self.assertEqual(parse_applicable_product_ids("16, 4,16,bad,0"), [16, 4])

    def test_unknown_discount_type_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_promo_price(10, 1, "mystery", 2)

    def test_non_finite_value_is_rejected(self):
        with self.assertRaises(ValueError):
            calculate_promo_price(10, 1, "product_price", float("nan"))


if __name__ == "__main__":
    unittest.main()
