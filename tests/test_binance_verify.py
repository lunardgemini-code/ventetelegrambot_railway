import asyncio
import time
import unittest
from unittest.mock import AsyncMock, patch
from urllib.parse import parse_qs, urlparse

from services import binance_verify


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code
        self.text = str(payload)

    def json(self):
        return self._payload


class BinanceVerifyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        binance_verify.reset_binance_verification_cache()

    async def asyncTearDown(self):
        binance_verify.reset_binance_verification_cache()

    async def test_uses_supported_time_parameters_and_accepts_overpayment(self):
        client = AsyncMock()
        transaction = {
            "transactionId": "P_TEST",
            "orderId": "442882137117253632",
            "amount": "5.04",
            "currency": "USDT",
            "orderType": "C2C",
        }
        client.get.return_value = _FakeResponse({"code": "000000", "data": [transaction]})

        with (
            patch.object(binance_verify, "_get_http_client", AsyncMock(return_value=client)),
            patch.object(binance_verify.time, "time", return_value=1_800_000_000),
        ):
            result = await binance_verify.verify_payment(
                "442882137117253632",
                5.00,
                api_key="key",
                api_secret="secret",
            )

        self.assertTrue(result["verified"])
        params = parse_qs(urlparse(client.get.await_args.args[0]).query)
        self.assertIn("startTime", params)
        self.assertIn("endTime", params)
        self.assertEqual(params["limit"], [str(binance_verify.PAY_API_LIMIT)])
        self.assertNotIn("startTimestamp", params)
        self.assertNotIn("endTimestamp", params)

    async def test_searches_older_windows_up_to_48_hours(self):
        client = AsyncMock()
        target = {
            "transactionId": "P_OLD",
            "orderId": "OLD_ORDER",
            "amount": "7.00",
            "orderType": "PAY",
        }

        async def fake_get(url, **_kwargs):
            params = parse_qs(urlparse(url).query)
            end_ms = int(params["endTime"][0])
            now_ms = 1_800_000_000 * 1000
            rows = [target] if end_ms <= now_ms - 46 * 60 * 60 * 1000 else []
            return _FakeResponse({"code": "000000", "data": rows})

        client.get.side_effect = fake_get
        with (
            patch.object(binance_verify, "_get_http_client", AsyncMock(return_value=client)),
            patch.object(binance_verify.time, "time", return_value=1_800_000_000),
        ):
            result = await binance_verify.verify_payment(
                "OLD_ORDER",
                7.00,
                api_key="key",
                api_secret="secret",
            )

        self.assertTrue(result["verified"])
        self.assertGreater(client.get.await_count, 1)
        self.assertLessEqual(client.get.await_count, binance_verify.PAY_MAX_API_REQUESTS)

    async def test_splits_a_full_binance_response(self):
        client = AsyncMock()
        target = {
            "transactionId": "P_SPLIT",
            "orderId": "SPLIT_ORDER",
            "amount": "3.00",
            "orderType": "C2C",
        }
        unrelated = [
            {
                "transactionId": f"P_{index}",
                "orderId": f"ORDER_{index}",
                "amount": "3.00",
                "orderType": "C2C",
            }
            for index in range(binance_verify.PAY_API_LIMIT)
        ]

        async def fake_get(url, **_kwargs):
            params = parse_qs(urlparse(url).query)
            start_ms = int(params["startTime"][0])
            end_ms = int(params["endTime"][0])
            if end_ms - start_ms == binance_verify.PAY_INITIAL_WINDOW_MS:
                rows = unrelated
            else:
                rows = [target]
            return _FakeResponse({"code": "000000", "data": rows})

        client.get.side_effect = fake_get
        with (
            patch.object(binance_verify, "_get_http_client", AsyncMock(return_value=client)),
            patch.object(binance_verify.time, "time", return_value=1_800_000_000),
        ):
            result = await binance_verify.verify_payment(
                "SPLIT_ORDER",
                3.00,
                api_key="key",
                api_secret="secret",
            )

        self.assertTrue(result["verified"])
        self.assertEqual(client.get.await_count, 2)

    async def test_rejects_underpayment(self):
        client = AsyncMock()
        transaction = {
            "transactionId": "P_UNDER",
            "orderId": "UNDER_ORDER",
            "amount": "4.98",
            "orderType": "C2C",
        }
        client.get.return_value = _FakeResponse({"code": "000000", "data": [transaction]})

        with (
            patch.object(binance_verify, "_get_http_client", AsyncMock(return_value=client)),
            patch.object(binance_verify.time, "time", return_value=1_800_000_000),
        ):
            result = await binance_verify.verify_payment(
                "UNDER_ORDER",
                5.00,
                api_key="key",
                api_secret="secret",
            )

        self.assertFalse(result["verified"])
        self.assertIsNone(result["transaction"])
        self.assertLessEqual(client.get.await_count, binance_verify.PAY_MAX_API_REQUESTS)

    async def test_concurrent_identical_checks_share_one_scan(self):
        client = AsyncMock()

        async def delayed_empty(*_args, **_kwargs):
            await asyncio.sleep(0.01)
            return _FakeResponse({"code": "000000", "data": []})

        client.get.side_effect = delayed_empty
        with patch.object(
            binance_verify, "_get_http_client", AsyncMock(return_value=client)
        ):
            first, second = await asyncio.gather(
                binance_verify.verify_payment(
                    "MISSING", 1.0, api_key="key", api_secret="secret"
                ),
                binance_verify.verify_payment(
                    "MISSING", 1.0, api_key="key", api_secret="secret"
                ),
            )

        self.assertFalse(first["verified"])
        self.assertEqual(first, second)
        self.assertEqual(
            client.get.await_count, len(binance_verify._payment_search_ranges(int(time.time() * 1000)))
        )


if __name__ == "__main__":
    unittest.main()
