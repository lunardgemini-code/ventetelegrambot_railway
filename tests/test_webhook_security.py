import asyncio
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request

import bot


def _request(body=None, *, headers=None, path="/webhook", method="POST"):
    raw_body = body if isinstance(body, bytes) else json.dumps(body or {}).encode("utf-8")
    header_items = [
        (str(name).lower().encode("latin-1"), str(value).encode("latin-1"))
        for name, value in (headers or {}).items()
    ]
    sent = False

    async def receive():
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": raw_body, "more_body": False}

    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": method,
            "scheme": "https",
            "path": path,
            "raw_path": path.encode("ascii"),
            "query_string": b"",
            "headers": header_items,
            "client": ("127.0.0.1", 12345),
            "server": ("testserver", 443),
        },
        receive,
    )


class WebhookSecurityTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.previous_app = bot.tg_app
        self.previous_queue = bot.webhook_update_queue
        bot.tg_app = SimpleNamespace(bot=None)
        bot.webhook_update_queue = asyncio.Queue(maxsize=8)
        bot._webhook_active_update_ids.clear()
        bot._webhook_recent_update_ids.clear()
        bot._webhook_update_id_by_object.clear()
        bot._webhook_enqueued_at.clear()
        bot._webhook_queued_by_key.clear()
        bot._webhook_active_dedupe_signatures.clear()
        bot._webhook_dedupe_by_update.clear()

    async def asyncTearDown(self):
        bot.tg_app = self.previous_app
        bot.webhook_update_queue = self.previous_queue

    async def test_webhook_rejects_missing_or_wrong_secret(self):
        with patch.object(bot, "WEBHOOK_SECRET", "s" * 32):
            for supplied in (None, "wrong"):
                headers = {}
                if supplied is not None:
                    headers["X-Telegram-Bot-Api-Secret-Token"] = supplied
                with self.subTest(supplied=supplied):
                    with self.assertRaises(HTTPException) as raised:
                        await bot.telegram_webhook(_request({"update_id": 1}, headers=headers))
                    self.assertEqual(raised.exception.status_code, 403)

    async def test_webhook_rejects_oversized_body_before_json_decode(self):
        headers = {
            "X-Telegram-Bot-Api-Secret-Token": "s" * 32,
            "Content-Length": str(bot.WEBHOOK_MAX_BODY_BYTES + 1),
        }
        with patch.object(bot, "WEBHOOK_SECRET", "s" * 32):
            with self.assertRaises(HTTPException) as raised:
                await bot.telegram_webhook(_request(b"{}", headers=headers))
        self.assertEqual(raised.exception.status_code, 413)

    async def test_webhook_deduplicates_an_active_telegram_update_id(self):
        headers = {"X-Telegram-Bot-Api-Secret-Token": "s" * 32}
        payload = {"update_id": 4242}
        with patch.object(bot, "WEBHOOK_SECRET", "s" * 32):
            first = await bot.telegram_webhook(_request(payload, headers=headers))
            second = await bot.telegram_webhook(_request(payload, headers=headers))

        self.assertEqual(first, {"ok": True})
        self.assertEqual(second, {"ok": True, "deduplicated": True})
        self.assertEqual(bot.webhook_update_queue.qsize(), 1)

    async def test_failed_enqueue_preparation_releases_update_dedupe_claim(self):
        headers = {"X-Telegram-Bot-Api-Secret-Token": "s" * 32}
        payload = {"update_id": 5151}
        with (
            patch.object(bot, "WEBHOOK_SECRET", "s" * 32),
            patch.object(bot, "_webhook_lock_key", side_effect=RuntimeError("boom")),
        ):
            with self.assertRaises(HTTPException) as raised:
                await bot.telegram_webhook(_request(payload, headers=headers))

        self.assertEqual(raised.exception.status_code, 500)
        self.assertNotIn(5151, bot._webhook_active_update_ids)
        self.assertEqual(bot._webhook_update_id_by_object, {})

    def test_production_runtime_requires_explicit_secrets(self):
        production = {
            "RAILWAY_ENVIRONMENT_NAME": "production",
            "ADMIN_API_KEY": "admin-key",
        }
        with (
            patch.dict(os.environ, production, clear=False),
            patch.object(bot, "WEBHOOK_SECRET", ""),
        ):
            with self.assertRaisesRegex(RuntimeError, "WEBHOOK_SECRET"):
                bot._validate_runtime_security("https://example.up.railway.app")


class AdminSessionSecurityTests(unittest.IsolatedAsyncioTestCase):
    def test_admin_session_token_is_signed_and_tamper_evident(self):
        token = bot._new_admin_session_token()
        self.assertTrue(bot._valid_admin_session_token(token))
        self.assertFalse(bot._valid_admin_session_token(token + "x"))
        self.assertFalse(bot._valid_admin_session_token("not-a-session"))

    async def test_verify_api_key_accepts_header_or_session_cookie(self):
        header_request = _request(path="/api/stats")
        self.assertEqual(
            await bot.verify_api_key(header_request, bot.ADMIN_API_KEY),
            "api_key",
        )

        token = bot._new_admin_session_token()
        cookie_request = _request(
            path="/api/stats",
            headers={"Cookie": f"{bot.ADMIN_SESSION_COOKIE}={token}"},
        )
        self.assertEqual(await bot.verify_api_key(cookie_request, None), "session")

        with self.assertRaises(HTTPException) as raised:
            await bot.verify_api_key(_request(path="/api/stats"), None)
        self.assertEqual(raised.exception.status_code, 401)


if __name__ == "__main__":
    unittest.main()
