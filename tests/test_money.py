import unittest

from utils.money import usd_decimal, usd_float


class MoneyBoundaryTests(unittest.TestCase):
    def test_uses_decimal_half_up_rounding(self):
        self.assertEqual(usd_float("1.005", places=2), 1.01)
        self.assertEqual(str(usd_decimal("0.10495", places=4)), "0.1050")

    def test_rejects_non_finite_negative_and_zero_when_required(self):
        for value in ("NaN", "Infinity", -0.01):
            with self.assertRaises(ValueError):
                usd_float(value)
        with self.assertRaises(ValueError):
            usd_float(0, allow_zero=False)


if __name__ == "__main__":
    unittest.main()
