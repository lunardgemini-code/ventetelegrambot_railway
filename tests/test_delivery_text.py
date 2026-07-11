import unittest

from handlers.payment import _build_txt_delivery


class DeliveryTextTests(unittest.TestCase):
    def test_accounts_are_separated_by_one_blank_line_without_labels(self):
        content = _build_txt_delivery([
            {"account_data": "first@example.com:password-1"},
            {"account_data": "second@example.com:password-2"},
            {"account_data": "third@example.com:password-3"},
        ])

        self.assertEqual(
            content,
            "first@example.com:password-1\n\n"
            "second@example.com:password-2\n\n"
            "third@example.com:password-3\n",
        )
        self.assertNotIn("Product", content)
        self.assertNotIn("---", content)

    def test_multiline_account_data_keeps_its_internal_lines(self):
        content = _build_txt_delivery([
            {"account_data": "login: first\npassword: secret"},
            {"account_data": "login: second\npassword: other"},
        ])

        self.assertEqual(
            content,
            "login: first\npassword: secret\n\n"
            "login: second\npassword: other\n",
        )


if __name__ == "__main__":
    unittest.main()
