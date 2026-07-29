import unittest
from unittest.mock import AsyncMock

import httpx

import bot
from services import pixel_api


class PixelApiSafetyTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.original_configured = pixel_api.is_pixel_configured
        self.original_client = pixel_api._client
        self.client = AsyncMock()

        async def fake_client():
            return self.client

        pixel_api.is_pixel_configured = lambda: True
        pixel_api._client = fake_client

    async def asyncTearDown(self):
        pixel_api.is_pixel_configured = self.original_configured
        pixel_api._client = self.original_client

    async def test_submit_5xx_is_never_treated_as_safe_to_retry(self):
        self.client.request.return_value = httpx.Response(
            502,
            json={"detail": "temporary supplier failure"},
            request=httpx.Request("POST", "https://pixel.example/submit"),
        )
        with self.assertRaises(pixel_api.PixelAPIError) as caught:
            await pixel_api._request("POST", "/submit", json={})
        self.assertEqual(caught.exception.status_code, 502)
        self.assertTrue(caught.exception.outcome_unknown)
        self.assertTrue(caught.exception.retryable)
        self.assertEqual(self.client.request.await_count, 1)

    async def test_invalid_ids_do_not_make_a_provider_request(self):
        result = await pixel_api.query_pixel_tasks(["bad", 0, -4, None])
        self.assertEqual(result, {})
        self.client.request.assert_not_awaited()

    async def test_malformed_callback_path_is_rejected_before_database_access(self):
        transport = httpx.ASGITransport(app=bot.api)
        async with httpx.AsyncClient(transport=transport, base_url="https://testserver") as client:
            response = await client.post("/api/pixel/callback/short/nope")
        self.assertEqual(response.status_code, 404)


if __name__ == "__main__":
    unittest.main()
