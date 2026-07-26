"""Regression tests for targeted broadcasts (message specific people).

Covers recipient parsing/resolution, the API contract, job payload plumbing,
delivery to an explicit audience, resume-after-restart, and the dashboard UI
including the six-language requirement.
"""

import pathlib
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx

import bot
from database import models
from services import background_jobs, broadcast

DASHBOARD = pathlib.Path(__file__).resolve().parents[1] / "dashboard"

USERS = [
    {"telegram_id": 111, "username": "alice", "first_name": "Alice", "is_banned": 0},
    {"telegram_id": 222, "username": "Bob", "first_name": "Bob", "is_banned": 0},
    {"telegram_id": 333, "username": "carol", "first_name": "Carol", "is_banned": 1},
]


def _users_db(rows):
    """Fake connection that honours the resolver's WHERE clauses.

    A mock returning every row regardless of the query would hide filtering
    bugs, so this one matches on the bound parameters like SQLite would.
    """

    async def execute(sql, params=None):
        values = list(params or [])
        if "telegram_id IN" in sql:
            wanted = {int(value) for value in values}
            matched = [row for row in rows if int(row["telegram_id"]) in wanted]
        elif "LOWER(username) IN" in sql:
            wanted = {str(value).lower() for value in values}
            matched = [
                row for row in rows
                if str(row.get("username") or "").lower() in wanted
            ]
        else:
            matched = list(rows)
        return SimpleNamespace(fetchall=AsyncMock(return_value=matched))

    return SimpleNamespace(execute=AsyncMock(side_effect=execute), close=AsyncMock())


class RecipientParsingTests(unittest.TestCase):
    def test_separators_and_at_prefix(self):
        parsed = models.parse_broadcast_recipient_entries("111, @bob\n222;333 @carol")
        self.assertEqual(parsed, ["111", "bob", "222", "333", "carol"])

    def test_deduplicates_case_insensitively(self):
        self.assertEqual(
            models.parse_broadcast_recipient_entries("@Bob\nbob\nBOB"), ["Bob"]
        )

    def test_accepts_a_list_and_ignores_blanks(self):
        self.assertEqual(
            models.parse_broadcast_recipient_entries(["@a", "", "  ", "b"]), ["a", "b"]
        )

    def test_empty_input(self):
        for value in ("", None, [], "   ,  ;  "):
            self.assertEqual(models.parse_broadcast_recipient_entries(value), [])


class RecipientResolutionTests(unittest.IsolatedAsyncioTestCase):
    async def test_resolves_ids_and_usernames_and_reports_unknown(self):
        db = _users_db(USERS)
        with patch("database.models.get_db", AsyncMock(return_value=db)):
            resolved = await models.resolve_broadcast_recipients("111 @bob @ghost 999")
        ids = [item["telegram_id"] for item in resolved["recipients"]]
        self.assertEqual(ids, [111, 222])
        self.assertCountEqual(resolved["unknown"], ["ghost", "999"])
        self.assertEqual(resolved["requested"], 4)

    async def test_recipients_are_sorted_for_a_stable_resume_cursor(self):
        db = _users_db(list(reversed(USERS)))
        with patch("database.models.get_db", AsyncMock(return_value=db)):
            resolved = await models.resolve_broadcast_recipients("333 111 222")
        self.assertEqual([item["telegram_id"] for item in resolved["recipients"]], [111, 222, 333])

    async def test_banned_flag_is_surfaced(self):
        db = _users_db(USERS)
        with patch("database.models.get_db", AsyncMock(return_value=db)):
            resolved = await models.resolve_broadcast_recipients("@carol")
        self.assertTrue(resolved["recipients"][0]["is_banned"])

    async def test_empty_input_never_touches_the_database(self):
        get_db = AsyncMock()
        with patch("database.models.get_db", get_db):
            resolved = await models.resolve_broadcast_recipients("")
        self.assertEqual(resolved["recipients"], [])
        get_db.assert_not_awaited()

    async def test_recipient_cap_is_enforced(self):
        entries = "\n".join(str(value) for value in range(models.BROADCAST_RECIPIENT_MAX + 1))
        with self.assertRaises(ValueError) as raised:
            await models.resolve_broadcast_recipients(entries)
        self.assertEqual(str(raised.exception), "TOO_MANY_RECIPIENTS")


class TargetedDeliveryTests(unittest.IsolatedAsyncioTestCase):
    async def test_only_the_listed_recipients_receive_the_message(self):
        sent_to = []

        async def fake_send(bot_obj, user_id, text, photo, markup):
            sent_to.append(user_id)
            return True

        get_all_users = AsyncMock(return_value=[{"telegram_id": 999}])
        with (
            patch("services.broadcast._send_one", fake_send),
            patch("services.broadcast.get_all_users", get_all_users),
        ):
            sent, failed, total = await broadcast.execute_broadcast(
                SimpleNamespace(token=""), "hello", recipient_ids=[222, 111]
            )
        self.assertEqual(sorted(sent_to), [111, 222])
        self.assertEqual((sent, failed, total), (2, 0, 2))
        # The all-users read must be skipped entirely in targeted mode.
        get_all_users.assert_not_awaited()

    async def test_max_user_id_snapshot_is_ignored_when_targeting(self):
        sent_to = []

        async def fake_send(bot_obj, user_id, text, photo, markup):
            sent_to.append(user_id)
            return True

        with patch("services.broadcast._send_one", fake_send):
            # max_user_id=0 would wipe an all-users audience; targeted must ignore it.
            sent, _, total = await broadcast.execute_broadcast(
                SimpleNamespace(token=""), "hi", recipient_ids=[555], max_user_id=0
            )
        self.assertEqual(sent_to, [555])
        self.assertEqual((sent, total), (1, 1))

    async def test_resume_skips_already_delivered_recipients(self):
        sent_to = []

        async def fake_send(bot_obj, user_id, text, photo, markup):
            sent_to.append(user_id)
            return True

        with patch("services.broadcast._send_one", fake_send):
            sent, failed, total = await broadcast.execute_broadcast(
                SimpleNamespace(token=""),
                "hi",
                recipient_ids=[111, 222, 333],
                start_offset=2,
                initial_sent=2,
            )
        self.assertEqual(sent_to, [333])
        self.assertEqual((sent, failed, total), (3, 0, 3))

    async def test_untargeted_broadcast_still_reads_every_user(self):
        async def fake_send(bot_obj, user_id, text, photo, markup):
            return True

        get_all_users = AsyncMock(return_value=[{"telegram_id": 1, "id": 1}])
        with (
            patch("services.broadcast._send_one", fake_send),
            patch("services.broadcast.get_all_users", get_all_users),
        ):
            sent, _, total = await broadcast.execute_broadcast(SimpleNamespace(token=""), "hi")
        self.assertEqual((sent, total), (1, 1))
        get_all_users.assert_awaited()


class TargetedJobPayloadTests(unittest.IsolatedAsyncioTestCase):
    async def test_payload_carries_sorted_unique_recipients(self):
        created = {}

        async def fake_create(job_uid, job_type, payload, **kwargs):
            created.update({"payload": payload, "kwargs": kwargs})
            return {"id": job_uid, "job_type": job_type, "status": "queued", **kwargs}

        window = AsyncMock()
        with (
            patch("services.background_jobs.create_background_job", fake_create),
            patch("services.background_jobs.get_broadcast_recipient_window", window),
        ):
            await background_jobs.enqueue_broadcast_job("hi", recipient_ids=[333, 111, 111])
        self.assertEqual(created["payload"]["recipient_ids"], [111, 333])
        self.assertEqual(created["kwargs"]["progress_total"], 2)
        # A fixed audience needs no recipient window query.
        window.assert_not_awaited()

    async def test_untargeted_payload_keeps_the_snapshot(self):
        created = {}

        async def fake_create(job_uid, job_type, payload, **kwargs):
            created.update({"payload": payload, "kwargs": kwargs})
            return {"id": job_uid, "job_type": job_type, "status": "queued", **kwargs}

        with (
            patch("services.background_jobs.create_background_job", fake_create),
            patch(
                "services.background_jobs.get_broadcast_recipient_window",
                AsyncMock(return_value={"max_user_id": 42, "total": 7}),
            ),
        ):
            await background_jobs.enqueue_broadcast_job("hi")
        self.assertIsNone(created["payload"]["recipient_ids"])
        self.assertEqual(created["payload"]["max_user_id"], 42)
        self.assertEqual(created["kwargs"]["progress_total"], 7)

    async def test_empty_targeted_list_is_rejected(self):
        with self.assertRaises(ValueError):
            await background_jobs.enqueue_broadcast_job("hi", recipient_ids=[])


class TargetedBroadcastApiTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self._previous_app = bot.tg_app
        bot.tg_app = SimpleNamespace(bot=SimpleNamespace())
        bot._auth_fail_buckets.clear()

    def tearDown(self):
        bot.tg_app = self._previous_app
        bot._auth_fail_buckets.clear()

    async def _client(self):
        transport = httpx.ASGITransport(app=bot.api)
        return httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"X-API-Key": bot.ADMIN_API_KEY},
        )

    async def test_preview_endpoint_reports_matched_banned_and_unknown(self):
        db = _users_db(USERS)
        async with await self._client() as client:
            with patch("database.models.get_db", AsyncMock(return_value=db)):
                response = await client.post(
                    "/api/broadcast/recipients", json={"recipients": "111 @bob @carol @ghost"}
                )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["matched"], 3)
        self.assertEqual(body["banned"], 1)
        self.assertEqual(body["unknown"], ["ghost"])

    async def test_preview_requires_authentication(self):
        transport = httpx.ASGITransport(app=bot.api)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post("/api/broadcast/recipients", json={"recipients": "111"})
        self.assertEqual(response.status_code, 401)

    async def test_send_excludes_banned_recipients_by_default(self):
        db = _users_db(USERS)
        enqueue = AsyncMock(return_value={"job_id": "j1", "status": "queued"})
        async with await self._client() as client:
            with (
                patch("database.models.get_db", AsyncMock(return_value=db)),
                patch("services.background_jobs.enqueue_broadcast_job", enqueue),
            ):
                response = await client.post(
                    "/api/broadcast",
                    json={"message": "hi", "recipients": "111 @bob @carol"},
                )
        self.assertEqual(response.status_code, 202)
        body = response.json()
        self.assertEqual(body["matched"], 2)
        self.assertEqual(body["skipped_banned"], 1)
        self.assertEqual(enqueue.await_args.kwargs["recipient_ids"], [111, 222])

    async def test_send_can_include_banned_recipients_on_request(self):
        db = _users_db(USERS)
        enqueue = AsyncMock(return_value={"job_id": "j1", "status": "queued"})
        async with await self._client() as client:
            with (
                patch("database.models.get_db", AsyncMock(return_value=db)),
                patch("services.background_jobs.enqueue_broadcast_job", enqueue),
            ):
                response = await client.post(
                    "/api/broadcast",
                    json={"message": "hi", "recipients": "@carol", "include_banned": True},
                )
        self.assertEqual(response.status_code, 202)
        self.assertEqual(enqueue.await_args.kwargs["recipient_ids"], [333])

    async def test_send_rejects_a_list_that_matches_nobody(self):
        db = _users_db([])
        enqueue = AsyncMock()
        async with await self._client() as client:
            with (
                patch("database.models.get_db", AsyncMock(return_value=db)),
                patch("services.background_jobs.enqueue_broadcast_job", enqueue),
            ):
                response = await client.post(
                    "/api/broadcast", json={"message": "hi", "recipients": "@ghost"}
                )
        self.assertEqual(response.status_code, 400)
        enqueue.assert_not_awaited()

    async def test_omitting_recipients_keeps_the_all_users_broadcast(self):
        enqueue = AsyncMock(return_value={"job_id": "j1", "status": "queued"})
        async with await self._client() as client:
            with patch("services.background_jobs.enqueue_broadcast_job", enqueue):
                response = await client.post("/api/broadcast", json={"message": "hi"})
        self.assertEqual(response.status_code, 202)
        self.assertNotIn("recipient_ids", enqueue.await_args.kwargs)
        self.assertFalse(response.json().get("targeted"))

    async def test_empty_message_is_still_rejected_in_targeted_mode(self):
        async with await self._client() as client:
            response = await client.post(
                "/api/broadcast", json={"message": "", "recipients": "111"}
            )
        self.assertEqual(response.status_code, 400)


class TargetedBroadcastDashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_js = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        cls.index = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        cls.worker = (DASHBOARD / "service-worker.js").read_text(encoding="utf-8")

    def test_targeting_controls_exist(self):
        for element_id in (
            "broadcast-audience",
            "broadcast-recipients",
            "broadcast-recipients-group",
            "broadcast-include-banned",
            "btn-check-recipients",
        ):
            self.assertIn(f'id="{element_id}"', self.index)

    def test_recipients_are_sent_to_the_api(self):
        self.assertIn("payload.recipients = recipientsRaw;", self.app_js)
        self.assertIn("'/api/broadcast/recipients'", self.app_js)

    def test_every_new_string_is_translated_in_all_six_languages(self):
        keys = [
            "broadcast_audience_label",
            "broadcast_audience_all",
            "broadcast_audience_targeted",
            "broadcast_recipients_label",
            "broadcast_check_recipients",
            "broadcast_include_banned",
            "broadcast_recipients_matched",
            "broadcast_recipients_banned",
            "broadcast_recipients_unknown",
            "broadcast_recipients_required",
            "broadcast_confirm_all",
            "broadcast_confirm_targeted",
            "btn_send_broadcast_targeted",
        ]
        block = self.app_js.split("const TARGETED_BROADCAST_TRANSLATIONS = {", 1)[1]
        block = block.split("Object.entries(TARGETED_BROADCAST_TRANSLATIONS)", 1)[0]
        for language in ("fr", "en", "ar", "zh", "vi", "ru"):
            section = block.split(f"{language}: {{", 1)[1].split("},", 1)[0]
            for key in keys:
                self.assertIn(f"{key}:", section, f"{key} missing for {language}")

    def test_no_hardcoded_french_confirm_remains(self):
        self.assertNotIn("Envoyer ce message à tous les utilisateurs ?`", self.app_js)

    def test_assets_are_versioned_for_installed_dashboards(self):
        for asset in (
            "app.js?v=20260726-targeted-broadcast-v1",
            "operations.js?v=20260726-targeted-broadcast-v1",
        ):
            self.assertIn(asset, self.index)
            self.assertIn(asset, self.worker)
        self.assertIn("ventebot-dashboard-shell-20260726-targeted-broadcast-v1", self.worker)


if __name__ == "__main__":
    unittest.main()
