"""Regression tests for authentication hardening and engagement buffering.

Covers: v2 admin session tokens (expiry, revocation, tampering), failed-auth
throttling for the admin and reseller paths, the audited login route, the
banned-reseller cache purge, /health caching, and batched product analytics.
"""

import asyncio
import json
import time
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import HTTPException
from starlette.requests import Request

import bot
from database import models


def _request(body=None, *, headers=None, path="/api/stats", method="GET", client_ip="127.0.0.1"):
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
            "client": (client_ip, 12345),
            "server": ("testserver", 443),
        },
        receive,
    )


class AdminSessionTokenV2Tests(unittest.TestCase):
    def test_v2_token_round_trip(self):
        token = bot._new_admin_session_token()
        self.assertTrue(token.startswith("v2."))
        self.assertTrue(bot._valid_admin_session_token(token))

    def test_tampered_and_malformed_tokens_rejected(self):
        token = bot._new_admin_session_token()
        self.assertFalse(bot._valid_admin_session_token(token + "x"))
        self.assertFalse(bot._valid_admin_session_token("not-a-session"))
        self.assertFalse(bot._valid_admin_session_token(""))
        # Tampering with the embedded timestamp must break the signature.
        parts = token.split(".")
        parts[1] = str(int(parts[1]) + 1)
        self.assertFalse(bot._valid_admin_session_token(".".join(parts)))

    def test_legacy_two_part_tokens_are_rejected(self):
        import base64
        import hashlib
        import hmac as hmac_mod
        import secrets as secrets_mod

        payload = base64.urlsafe_b64encode(secrets_mod.token_bytes(32)).decode("ascii").rstrip("=")
        signature = hmac_mod.new(
            bot.ADMIN_SESSION_SECRET.encode("utf-8"), payload.encode("ascii"), hashlib.sha256
        ).hexdigest()
        self.assertFalse(bot._valid_admin_session_token(f"{payload}.{signature}"))

    def test_expired_token_rejected(self):
        stale = bot._new_admin_session_token(
            issued_at=int(time.time()) - bot.ADMIN_SESSION_MAX_AGE - 10
        )
        self.assertFalse(bot._valid_admin_session_token(stale))

    def test_future_dated_token_rejected(self):
        forged = bot._new_admin_session_token(issued_at=int(time.time()) + 3600)
        self.assertFalse(bot._valid_admin_session_token(forged))

    def test_revocation_epoch_invalidates_older_sessions(self):
        token = bot._new_admin_session_token(issued_at=int(time.time()) - 100)
        self.assertTrue(bot._valid_admin_session_token(token))
        with patch.object(bot, "ADMIN_SESSION_REVOKED_BEFORE", int(time.time()) - 50):
            self.assertFalse(bot._valid_admin_session_token(token))


class AuthFailureThrottleTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        bot._auth_fail_buckets.clear()

    def tearDown(self):
        bot._auth_fail_buckets.clear()

    async def test_admin_auth_throttles_after_repeated_failures(self):
        for _ in range(bot.AUTH_FAIL_MAX_ATTEMPTS):
            with self.assertRaises(HTTPException) as raised:
                await bot.verify_api_key(_request(), "wrong-key")
            self.assertEqual(raised.exception.status_code, 401)

        with self.assertRaises(HTTPException) as raised:
            await bot.verify_api_key(_request(), "wrong-key")
        self.assertEqual(raised.exception.status_code, 429)
        self.assertIn("Retry-After", raised.exception.headers)

    async def test_valid_credentials_bypass_the_throttle(self):
        for _ in range(bot.AUTH_FAIL_MAX_ATTEMPTS + 2):
            bot._register_auth_failure("admin", "127.0.0.1")
        result = await bot.verify_api_key(_request(), bot.ADMIN_API_KEY)
        self.assertEqual(result, "api_key")

    async def test_throttle_is_per_ip(self):
        for _ in range(bot.AUTH_FAIL_MAX_ATTEMPTS + 1):
            bot._register_auth_failure("admin", "10.0.0.1")
        with self.assertRaises(HTTPException) as raised:
            await bot.verify_api_key(_request(client_ip="10.0.0.2"), "wrong-key")
        self.assertEqual(raised.exception.status_code, 401)

    async def test_window_expiry_resets_the_bucket(self):
        for _ in range(bot.AUTH_FAIL_MAX_ATTEMPTS + 1):
            bot._register_auth_failure("admin", "127.0.0.1")
        bucket = bot._auth_fail_buckets[("admin", "127.0.0.1")]
        bucket["reset_at"] = time.time() - 1
        self.assertEqual(bot._auth_failure_retry_after("admin", "127.0.0.1"), 0)

    async def test_reseller_throttle_blocks_before_database_lookup(self):
        lookup = AsyncMock(return_value=None)
        with patch("database.models.get_reseller_by_api_key", lookup):
            for _ in range(bot.AUTH_FAIL_MAX_ATTEMPTS):
                with self.assertRaises(HTTPException) as raised:
                    await bot.verify_reseller_key(
                        _request(path="/api/reseller/products"),
                        MagicMock(),
                        "vbr_live_bad_key",
                        None,
                    )
                self.assertEqual(raised.exception.status_code, 401)
            self.assertEqual(lookup.await_count, bot.AUTH_FAIL_MAX_ATTEMPTS)

            with self.assertRaises(HTTPException) as raised:
                await bot.verify_reseller_key(
                    _request(path="/api/reseller/products"),
                    MagicMock(),
                    "vbr_live_bad_key",
                    None,
                )
            self.assertEqual(raised.exception.status_code, 429)
            # The throttled request must never have reached the database.
            self.assertEqual(lookup.await_count, bot.AUTH_FAIL_MAX_ATTEMPTS)

    def test_login_route_is_audited(self):
        request = _request(path="/api/admin/session", method="POST")
        self.assertTrue(bot._should_audit_admin_request(request))
        reseller = _request(path="/api/reseller/orders", method="POST")
        self.assertFalse(bot._should_audit_admin_request(reseller))


class BannedResellerCachePurgeTests(unittest.IsolatedAsyncioTestCase):
    async def test_ban_user_clears_reseller_auth_cache(self):
        models._RESELLER_AUTH_CACHE["digest"] = (time.time(), {"id": 1})
        fake_db = SimpleNamespace(
            execute=AsyncMock(),
            commit=AsyncMock(),
            close=AsyncMock(),
        )
        with patch("database.models.get_db", AsyncMock(return_value=fake_db)):
            await models.ban_user(4242)
        self.assertEqual(models._RESELLER_AUTH_CACHE, {})
        self.assertTrue(models._USER_BANNED_CACHE.get(4242))
        models._USER_BANNED_CACHE.pop(4242, None)


class HealthEndpointCacheTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        bot._health_check_cache.update({"time": 0.0, "status": 200, "payload": None})
        self._previous_app = bot.tg_app
        bot.tg_app = SimpleNamespace(running=True)

    def tearDown(self):
        bot._health_check_cache.update({"time": 0.0, "status": 200, "payload": None})
        bot.tg_app = self._previous_app

    async def test_health_serves_cached_payload_within_ttl(self):
        cursor = SimpleNamespace(fetchone=AsyncMock(return_value={"ok": 1}))
        fake_db = SimpleNamespace(
            execute=AsyncMock(return_value=cursor),
            close=AsyncMock(),
        )
        get_db = AsyncMock(return_value=fake_db)
        with patch("database.db.get_db", get_db):
            first = await bot.health_check()
            second = await bot.health_check()
        self.assertEqual(first["status"], "ok")
        self.assertIs(second, first)
        self.assertEqual(get_db.await_count, 1)


class ProductEngagementBufferTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._clear_buffers()

    def tearDown(self):
        self._clear_buffers()

    @staticmethod
    def _clear_buffers():
        models._PRODUCT_VIEW_BUFFER.clear()
        models._PRODUCT_CLICK_BUFFER.clear()
        models._PRODUCT_VIEW_RECENT.clear()
        models._PRODUCT_CLICK_RECENT.clear()

    def test_queue_deduplicates_within_window(self):
        models.queue_product_view(7, 1001)
        models.queue_product_view(7, 1001)
        models.queue_product_view(7, 1002)
        self.assertEqual(len(models._PRODUCT_VIEW_BUFFER), 2)

        models.queue_product_buy_click(7, 1001)
        models.queue_product_buy_click(7, 1001)
        self.assertEqual(len(models._PRODUCT_CLICK_BUFFER), 1)

    async def test_flush_writes_batch_in_one_transaction(self):
        models.queue_product_view(7, 1001)
        models.queue_product_view(8, 1001)
        models.queue_product_buy_click(7, 1001)
        fake_db = SimpleNamespace(
            execute=AsyncMock(),
            commit=AsyncMock(),
            close=AsyncMock(),
        )
        with patch("database.models.get_db", AsyncMock(return_value=fake_db)):
            written = await models.flush_product_engagement()
        self.assertEqual(written, 3)
        self.assertEqual(fake_db.execute.await_count, 3)
        self.assertEqual(fake_db.commit.await_count, 1)
        self.assertEqual(models._PRODUCT_VIEW_BUFFER, {})
        self.assertEqual(models._PRODUCT_CLICK_BUFFER, {})

    async def test_flush_requeues_batch_on_failure(self):
        models.queue_product_view(7, 1001)
        fake_db = SimpleNamespace(
            execute=AsyncMock(side_effect=RuntimeError("stream not found")),
            commit=AsyncMock(),
            close=AsyncMock(),
        )
        with patch("database.models.get_db", AsyncMock(return_value=fake_db)):
            written = await models.flush_product_engagement()
        self.assertEqual(written, 0)
        self.assertEqual(len(models._PRODUCT_VIEW_BUFFER), 1)

    async def test_flush_is_a_noop_when_buffers_are_empty(self):
        get_db = AsyncMock()
        with patch("database.models.get_db", get_db):
            written = await models.flush_product_engagement()
        self.assertEqual(written, 0)
        get_db.assert_not_awaited()


class BroadcastRecipientQueryTests(unittest.IsolatedAsyncioTestCase):
    async def test_recipient_query_is_lean_and_unsorted(self):
        rows = [
            {"id": 1, "telegram_id": 111, "is_banned": 0},
            {"id": 2, "telegram_id": 222, "is_banned": 1},
        ]
        cursor = SimpleNamespace(fetchall=AsyncMock(return_value=rows))
        fake_db = SimpleNamespace(
            execute=AsyncMock(return_value=cursor),
            close=AsyncMock(),
        )
        with patch("database.models.get_db", AsyncMock(return_value=fake_db)):
            users = await models._get_all_users_once()
        self.assertEqual(len(users), 2)
        sql = fake_db.execute.await_args.args[0]
        self.assertNotIn("JOIN", sql.upper())
        self.assertNotIn("ORDER BY", sql.upper())
        for field in ("id", "telegram_id", "is_banned"):
            self.assertIn(field, sql)


if __name__ == "__main__":
    unittest.main()
