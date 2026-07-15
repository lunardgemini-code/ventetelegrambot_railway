import os
import asyncio
import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from database import db as db_module
from database.db import get_db, init_db
from database.games import (
    _next_sync_time,
    GameError,
    cancel_game_match,
    claim_daily_coins,
    get_game_match,
    get_game_wallet,
    import_game_match,
    place_game_bet,
    settle_game_match,
)
from database.models import get_or_create_user
from handlers.game import _format_leaderboard_entries
from services.sports_api import normalize_match
from services.game_sync import sync_due_game_matches_once
from utils.country_flags import country_flag, format_match_teams, format_team_name
from utils.game_locales import GAME_TRANSLATIONS
from utils.game_odds import calculate_match_odds, estimate_bet_return, format_game_odd
from utils.keyboards import game_home_keyboard, game_match_keyboard


class VirtualMatchGameTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["DB_PATH"] = os.path.join(self.temp_dir.name, "game.db")
        db_module.TURSO_URL = ""
        db_module._sqlite_wal_configured = False
        await init_db()
        await get_or_create_user(7001, "home_player", "Home Player")
        await get_or_create_user(7002, "away_player", "Away Player")
        self.provider_match = {
            "provider": "football-data",
            "external_match_id": "99001",
            "competition_code": "WC",
            "competition_name": "World Cup",
            "competition_emblem": "",
            "stage": "SEMI_FINALS",
            "home_external_id": "1",
            "home_name": "France",
            "home_code": "FRA",
            "home_crest": "",
            "away_external_id": "2",
            "away_name": "Spain",
            "away_code": "ESP",
            "away_crest": "",
            "utc_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "provider_status": "SCHEDULED",
            "provider_winner": None,
            "score_home": None,
            "score_away": None,
            "regular_score_home": None,
            "regular_score_away": None,
            "raw_payload": {"id": 99001},
        }

    async def asyncTearDown(self):
        self.temp_dir.cleanup()

    async def test_schema_migration_creates_game_tables(self):
        db = await get_db()
        try:
            cursor = await db.execute("SELECT version FROM schema_migrations ORDER BY version")
            versions = [int(row["version"]) for row in await cursor.fetchall()]
            self.assertIn(3, versions)
            cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'game_%'")
            tables = {row["name"] for row in await cursor.fetchall()}
            self.assertEqual(tables, {"game_matches", "game_wallets", "game_bets", "game_ledger"})
        finally:
            await db.close()

    async def test_daily_claim_is_idempotent(self):
        first = await claim_daily_coins(7001)
        second = await claim_daily_coins(7001)
        self.assertTrue(first["claimed"])
        self.assertFalse(second["claimed"])
        self.assertEqual((await get_game_wallet(7001))["balance"], 300)
        db = await get_db()
        try:
            cursor = await db.execute("SELECT COUNT(*) AS count FROM game_ledger WHERE user_telegram_id = 7001")
            self.assertEqual(int((await cursor.fetchone())["count"]), 1)
        finally:
            await db.close()

    async def test_bet_debit_and_settlement_are_atomic(self):
        match = await import_game_match(self.provider_match, publish=True)
        await claim_daily_coins(7001)
        await claim_daily_coins(7002)
        home_bet = await place_game_bet(7001, match["id"], "home", 100)
        await place_game_bet(7002, match["id"], "away", 100)
        self.assertEqual(home_bet["balance"], 200)
        with self.assertRaises(GameError) as duplicate:
            await place_game_bet(7001, match["id"], "home", 100)
        self.assertEqual(duplicate.exception.code, "already_bet")

        result = await settle_game_match(match["id"], "home")
        self.assertEqual(result["status"], "SETTLED")
        self.assertEqual(result["distributed"], 190)
        winner_wallet = await get_game_wallet(7001)
        self.assertEqual(winner_wallet["balance"], 390)
        self.assertEqual(winner_wallet["lifetime_earned"], 490)
        self.assertEqual((await get_game_wallet(7002))["balance"], 200)

        replay = await settle_game_match(match["id"], "home")
        self.assertEqual(replay["status"], "SETTLED")
        self.assertEqual((await get_game_wallet(7001))["balance"], 390)

    async def test_cancel_refunds_active_bets_once(self):
        self.provider_match["external_match_id"] = "99002"
        match = await import_game_match(self.provider_match, publish=True)
        await claim_daily_coins(7001)
        await place_game_bet(7001, match["id"], "away", 125)
        cancelled = await cancel_game_match(match["id"])
        self.assertEqual(cancelled["status"], "CANCELLED")
        self.assertEqual(cancelled["refunded"], 125)
        wallet = await get_game_wallet(7001)
        self.assertEqual(wallet["balance"], 300)
        self.assertEqual(wallet["lifetime_earned"], 300)
        await cancel_game_match(match["id"])
        self.assertEqual((await get_game_wallet(7001))["balance"], 300)

    async def test_simultaneous_duplicate_bet_only_debits_once(self):
        self.provider_match["external_match_id"] = "99003"
        match = await import_game_match(self.provider_match, publish=True)
        await claim_daily_coins(7001)

        attempts = await asyncio.gather(
            place_game_bet(7001, match["id"], "home", 100),
            place_game_bet(7001, match["id"], "home", 100),
            return_exceptions=True,
        )
        successes = [item for item in attempts if isinstance(item, dict)]
        failures = [item for item in attempts if isinstance(item, Exception)]
        self.assertEqual(len(successes), 1)
        self.assertEqual(len(failures), 1)
        self.assertEqual((await get_game_wallet(7001))["balance"], 200)

    async def test_publishing_rejects_terminal_or_already_locked_matches(self):
        terminal = dict(self.provider_match)
        terminal["external_match_id"] = "99004"
        terminal["provider_status"] = "FINISHED"
        with self.assertRaises(GameError) as terminal_error:
            await import_game_match(terminal, publish=True)
        self.assertEqual(terminal_error.exception.code, "invalid_provider_status")

        too_close = dict(self.provider_match)
        too_close["external_match_id"] = "99005"
        too_close["utc_date"] = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
        with self.assertRaises(GameError) as locked_error:
            await import_game_match(too_close, publish=True, lock_minutes=10)
        self.assertEqual(locked_error.exception.code, "match_started")

    def test_provider_normalization_keeps_regulation_and_final_scores(self):
        normalized = normalize_match({
            "id": 55,
            "utcDate": "2026-07-14T20:00:00Z",
            "status": "FINISHED",
            "competition": {"code": "WC", "name": "World Cup"},
            "homeTeam": {"id": 1, "name": "France", "tla": "FRA"},
            "awayTeam": {"id": 2, "name": "Spain", "tla": "ESP"},
            "score": {
                "winner": "HOME_TEAM",
                "duration": "EXTRA_TIME",
                "regularTime": {"home": 1, "away": 1},
                "fullTime": {"home": 2, "away": 1},
            },
        })
        self.assertEqual(normalized["provider_winner"], "home")
        self.assertEqual(normalized["regulation_outcome"], "draw")
        self.assertEqual(normalized["score_home"], 2)
        self.assertEqual(normalized["regular_score_home"], 1)

    def test_interrupted_matches_keep_syncing_and_final_matches_stop(self):
        future = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        self.assertIsNotNone(_next_sync_time({"provider_status": "POSTPONED", "utc_date": future}))
        self.assertIsNotNone(_next_sync_time({"provider_status": "SUSPENDED", "utc_date": future}))
        self.assertIsNone(_next_sync_time({"provider_status": "FINISHED", "utc_date": future}))

    async def test_sync_falls_back_to_individual_match_when_catalog_omits_it(self):
        saved = {
            "id": 1,
            "external_match_id": "537387",
            "utc_date": "2026-07-14 19:00:00",
        }
        final_match = {
            **self.provider_match,
            "external_match_id": "537387",
            "provider_status": "FINISHED",
            "provider_winner": "away",
            "score_home": 0,
            "score_away": 2,
        }
        individual = AsyncMock(return_value=final_match)
        update = AsyncMock(return_value=final_match)
        with (
            patch("services.game_sync.is_sports_api_configured", return_value=True),
            patch("services.game_sync.list_due_game_matches", AsyncMock(return_value=[saved])),
            patch("services.game_sync.list_football_matches", AsyncMock(return_value=[])),
            patch("services.game_sync.get_football_match", individual),
            patch("services.game_sync.update_game_match_from_provider", update),
        ):
            result = await sync_due_game_matches_once()

        self.assertEqual(result, {"configured": True, "due": 1, "updated": 1, "failed": 0})
        individual.assert_awaited_once_with("537387")
        update.assert_awaited_once_with(1, final_match)

    def test_dashboard_exposes_manual_result_refresh(self):
        source = (
            Path(__file__).resolve().parents[1] / "dashboard" / "app.js"
        ).read_text(encoding="utf-8")

        self.assertIn('data-game-action="sync"', source)
        self.assertIn("/sync`, 'POST'", source)

    def test_country_flags_are_added_for_national_teams_only(self):
        self.assertEqual(country_flag("France", "FRA"), "🇫🇷")
        self.assertEqual(country_flag("Spain", "ESP"), "🇪🇸")
        self.assertEqual(format_team_name("France", "FRA"), "🇫🇷 France")
        self.assertEqual(format_team_name("Real Madrid CF", "RMA"), "Real Madrid CF")
        self.assertEqual(
            format_match_teams(self.provider_match),
            "🇫🇷 France - 🇪🇸 Spain",
        )

    def test_game_keyboards_show_country_flags(self):
        match = {
            **self.provider_match,
            "id": 99,
            "market_type": "regulation",
            "home_pool": 100,
            "draw_pool": 50,
            "away_pool": 100,
            "fee_bps": 500,
        }
        home_keyboard = game_home_keyboard([match], {"claim_available": False}, "en")
        self.assertEqual(home_keyboard.inline_keyboard[0][0].text, "⚽ 🇫🇷 France - 🇪🇸 Spain")

        match_keyboard = game_match_keyboard(match, "en")
        self.assertEqual(match_keyboard.inline_keyboard[0][0].text, "🇫🇷 France · x2.37")
        self.assertEqual(match_keyboard.inline_keyboard[0][1].text, "🇪🇸 Spain · x2.37")
        self.assertEqual(match_keyboard.inline_keyboard[1][0].text, "Draw · x4.74")

    def test_live_odds_match_the_settlement_formula(self):
        match = {
            "market_type": "qualified",
            "home_pool": 100,
            "away_pool": 100,
            "fee_bps": 500,
        }
        odds = calculate_match_odds(match)
        self.assertEqual(format_game_odd(odds["home"]), "x1.90")
        self.assertEqual(format_game_odd(odds["away"]), "x1.90")

        estimate = estimate_bet_return(match, "home", 100)
        self.assertEqual(estimate["payout"], 142)
        self.assertEqual(format_game_odd(estimate["odds"]), "x1.42")

    def test_game_translations_are_complete_and_use_the_coin_brand(self):
        english_keys = set(GAME_TRANSLATIONS["en"])
        for values in GAME_TRANSLATIONS.values():
            self.assertEqual(set(values), english_keys)
            self.assertIn("Batman Coins", values["game_balance"])

    def test_leaderboard_layout_is_stable_for_long_and_rtl_names(self):
        entries = _format_leaderboard_entries([
            {"user_telegram_id": 1, "first_name": "Mohsen", "balance": 834},
            {"user_telegram_id": 2, "first_name": "كرار", "balance": 300},
            {
                "user_telegram_id": 3,
                "first_name": "A very long leaderboard player name that must be shortened",
                "balance": 289,
            },
            {"user_telegram_id": 4, "first_name": "Fourth", "balance": 278},
        ], "en")

        self.assertEqual(len(entries), 4)
        self.assertTrue(entries[0].startswith("🥇"))
        self.assertIn("\u2068كرار\u2069", entries[1])
        self.assertIn("\n└ 💰 <b>300 Batman Coins</b>", entries[1])
        self.assertIn("...", entries[2])
        self.assertTrue(entries[3].startswith("<b>#4</b>"))
        for entry in entries:
            self.assertEqual(entry.count("Batman Coins"), 1)


if __name__ == "__main__":
    unittest.main()
