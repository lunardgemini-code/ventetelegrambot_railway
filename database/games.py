"""Database operations for the lightweight virtual match prediction game."""

from __future__ import annotations

import json
import math
import time
from datetime import datetime, timedelta, timezone

from config import (
    GAME_DAILY_CLAIM,
    GAME_DEFAULT_FEE_BPS,
    GAME_DEFAULT_MAX_STAKE,
    GAME_DEFAULT_MIN_STAKE,
)
from database.db import get_db


FINAL_PROVIDER_STATUSES = {"FINISHED", "CANCELLED", "AWARDED"}
VALID_MARKETS = {"qualified", "regulation"}
VALID_OUTCOMES = {"home", "draw", "away"}
_OPEN_MATCH_CACHE_TTL = 20.0
_open_match_cache: tuple[float, list[dict]] | None = None


class GameError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_time(value) -> datetime | None:
    if not value:
        return None
    text = str(value).strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _db_time(value: datetime | str) -> str:
    parsed = value if isinstance(value, datetime) else _parse_time(value)
    if parsed is None:
        raise GameError("invalid_date", "Invalid match date")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def _dict(row) -> dict | None:
    return dict(row) if row is not None else None


def _effective_status(match: dict, *, now: datetime | None = None) -> str:
    status = str(match.get("status") or "DRAFT").upper()
    lock_at = _parse_time(match.get("lock_at"))
    if status == "OPEN" and lock_at and lock_at <= (now or _utc_now()):
        return "LOCKED"
    return status


def _invalidate_open_match_cache() -> None:
    global _open_match_cache
    _open_match_cache = None


def public_game_match(match: dict | None) -> dict | None:
    if not match:
        return None
    result = dict(match)
    result["status"] = _effective_status(result)
    for key in ("raw_payload",):
        result.pop(key, None)
    for key in (
        "bet_count",
        "total_pool",
        "home_pool",
        "draw_pool",
        "away_pool",
    ):
        result[key] = int(result.get(key) or 0)
    result["min_stake"] = int(result.get("min_stake") or GAME_DEFAULT_MIN_STAKE)
    result["max_stake"] = int(result.get("max_stake") or GAME_DEFAULT_MAX_STAKE)
    result["fee_bps"] = int(result.get("fee_bps") or 0)
    return result


async def selected_external_match_ids() -> set[str]:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT external_match_id FROM game_matches"
        )
        return {str(row["external_match_id"]) for row in await cursor.fetchall()}
    finally:
        await db.close()


async def get_game_match(match_id: int) -> dict | None:
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT gm.*,
                      COUNT(gb.id) AS bet_count,
                      COALESCE(SUM(CASE WHEN gb.status = 'ACTIVE' THEN gb.stake ELSE 0 END), 0) AS total_pool,
                      COALESCE(SUM(CASE WHEN gb.status = 'ACTIVE' AND gb.outcome = 'home' THEN gb.stake ELSE 0 END), 0) AS home_pool,
                      COALESCE(SUM(CASE WHEN gb.status = 'ACTIVE' AND gb.outcome = 'draw' THEN gb.stake ELSE 0 END), 0) AS draw_pool,
                      COALESCE(SUM(CASE WHEN gb.status = 'ACTIVE' AND gb.outcome = 'away' THEN gb.stake ELSE 0 END), 0) AS away_pool
               FROM game_matches gm
               LEFT JOIN game_bets gb ON gb.match_id = gm.id
               WHERE gm.id = ?
               GROUP BY gm.id""",
            (int(match_id),),
        )
        return public_game_match(_dict(await cursor.fetchone()))
    finally:
        await db.close()


async def list_game_matches(*, include_cancelled: bool = False, limit: int = 250) -> list[dict]:
    db = await get_db()
    try:
        where = "" if include_cancelled else "WHERE gm.status != 'CANCELLED'"
        cursor = await db.execute(
            f"""SELECT gm.*,
                       COUNT(gb.id) AS bet_count,
                       COALESCE(SUM(CASE WHEN gb.status = 'ACTIVE' THEN gb.stake ELSE 0 END), 0) AS total_pool,
                       COALESCE(SUM(CASE WHEN gb.status = 'ACTIVE' AND gb.outcome = 'home' THEN gb.stake ELSE 0 END), 0) AS home_pool,
                       COALESCE(SUM(CASE WHEN gb.status = 'ACTIVE' AND gb.outcome = 'draw' THEN gb.stake ELSE 0 END), 0) AS draw_pool,
                       COALESCE(SUM(CASE WHEN gb.status = 'ACTIVE' AND gb.outcome = 'away' THEN gb.stake ELSE 0 END), 0) AS away_pool
                FROM game_matches gm
                LEFT JOIN game_bets gb ON gb.match_id = gm.id
                {where}
                GROUP BY gm.id
                ORDER BY gm.utc_date DESC
                LIMIT ?""",
            (max(1, min(1000, int(limit))),),
        )
        return [public_game_match(dict(row)) for row in await cursor.fetchall()]
    finally:
        await db.close()


async def list_open_game_matches(limit: int = 12) -> list[dict]:
    global _open_match_cache
    now_monotonic = time.monotonic()
    if _open_match_cache and now_monotonic - _open_match_cache[0] < _OPEN_MATCH_CACHE_TTL:
        return [dict(item) for item in _open_match_cache[1][:max(1, min(30, int(limit)))]]

    matches = await list_game_matches(limit=200)
    now = _utc_now()
    open_matches = [
        match for match in matches
        if _effective_status(match, now=now) == "OPEN" and _parse_time(match.get("utc_date"))
    ]
    open_matches.sort(key=lambda item: _parse_time(item["utc_date"]) or now)
    _open_match_cache = (now_monotonic, [dict(item) for item in open_matches])
    return [dict(item) for item in open_matches[:max(1, min(30, int(limit)))]]


async def import_game_match(
    provider_match: dict,
    *,
    market_type: str = "qualified",
    lock_minutes: int = 10,
    min_stake: int = GAME_DEFAULT_MIN_STAKE,
    max_stake: int = GAME_DEFAULT_MAX_STAKE,
    fee_bps: int = GAME_DEFAULT_FEE_BPS,
    publish: bool = True,
) -> dict:
    market = str(market_type or "qualified").lower()
    if market not in VALID_MARKETS:
        raise GameError("invalid_market", "Unsupported market type")
    minimum = max(1, int(min_stake))
    maximum = max(minimum, int(max_stake))
    fee = min(2500, max(0, int(fee_bps)))
    starts_at = _parse_time(provider_match.get("utc_date"))
    if starts_at is None:
        raise GameError("invalid_date", "The provider match has no valid date")
    lock_at = starts_at - timedelta(minutes=max(0, min(1440, int(lock_minutes))))
    provider_status = str(provider_match.get("provider_status") or "SCHEDULED").upper()
    if publish and provider_status not in {"SCHEDULED", "TIMED"}:
        raise GameError("invalid_provider_status", "Only scheduled matches can be published")
    if publish and lock_at <= _utc_now():
        raise GameError("match_started", "Predictions would already be closed for this match")
    now_text = _db_time(_utc_now())
    status = "OPEN" if publish else "DRAFT"
    raw_payload = json.dumps(provider_match.get("raw_payload") or {}, ensure_ascii=False, separators=(",", ":"))

    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO game_matches (
                   provider, external_match_id, competition_code, competition_name,
                   competition_emblem, stage, home_external_id, home_name, home_code,
                   home_crest, away_external_id, away_name, away_code, away_crest,
                   utc_date, provider_status, provider_winner, score_home, score_away,
                   regular_score_home, regular_score_away, market_type, status, lock_at,
                   min_stake, max_stake, fee_bps, raw_payload, last_synced_at,
                   next_sync_at, published_at, updated_at
               ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(provider, external_match_id) DO UPDATE SET
                   competition_code = excluded.competition_code,
                   competition_name = excluded.competition_name,
                   competition_emblem = excluded.competition_emblem,
                   stage = excluded.stage,
                   home_name = excluded.home_name,
                   home_code = excluded.home_code,
                   home_crest = excluded.home_crest,
                   away_name = excluded.away_name,
                   away_code = excluded.away_code,
                   away_crest = excluded.away_crest,
                   utc_date = excluded.utc_date,
                   provider_status = excluded.provider_status,
                   provider_winner = excluded.provider_winner,
                   score_home = excluded.score_home,
                   score_away = excluded.score_away,
                   regular_score_home = excluded.regular_score_home,
                   regular_score_away = excluded.regular_score_away,
                   raw_payload = excluded.raw_payload,
                   last_synced_at = excluded.last_synced_at,
                   next_sync_at = excluded.next_sync_at,
                   updated_at = excluded.updated_at""",
            (
                provider_match.get("provider") or "football-data",
                str(provider_match["external_match_id"]),
                provider_match.get("competition_code") or "",
                provider_match.get("competition_name") or "Football",
                provider_match.get("competition_emblem") or "",
                provider_match.get("stage") or "",
                provider_match.get("home_external_id") or "",
                provider_match.get("home_name") or "Home",
                provider_match.get("home_code") or "",
                provider_match.get("home_crest") or "",
                provider_match.get("away_external_id") or "",
                provider_match.get("away_name") or "Away",
                provider_match.get("away_code") or "",
                provider_match.get("away_crest") or "",
                _db_time(starts_at),
                provider_status,
                provider_match.get("provider_winner"),
                provider_match.get("score_home"),
                provider_match.get("score_away"),
                provider_match.get("regular_score_home"),
                provider_match.get("regular_score_away"),
                market,
                status,
                _db_time(lock_at),
                minimum,
                maximum,
                fee,
                raw_payload,
                now_text,
                now_text,
                now_text if publish else None,
                now_text,
            ),
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT id FROM game_matches WHERE provider = ? AND external_match_id = ?",
            (provider_match.get("provider") or "football-data", str(provider_match["external_match_id"])),
        )
        row = await cursor.fetchone()
    finally:
        await db.close()
    _invalidate_open_match_cache()
    return await get_game_match(int(row["id"]))


async def update_game_match_configuration(
    match_id: int,
    *,
    market_type: str,
    lock_minutes: int,
    min_stake: int,
    max_stake: int,
    fee_bps: int,
) -> dict:
    match = await get_game_match(match_id)
    if not match:
        raise GameError("not_found", "Match not found")
    if int(match.get("bet_count") or 0) > 0:
        raise GameError("bets_exist", "Configuration is locked after the first prediction")
    market = str(market_type or "").lower()
    if market not in VALID_MARKETS:
        raise GameError("invalid_market", "Unsupported market type")
    starts_at = _parse_time(match.get("utc_date"))
    lock_at = starts_at - timedelta(minutes=max(0, min(1440, int(lock_minutes))))
    minimum = max(1, int(min_stake))
    maximum = max(minimum, int(max_stake))
    fee = min(2500, max(0, int(fee_bps)))
    db = await get_db()
    try:
        await db.execute(
            """UPDATE game_matches
               SET market_type = ?, lock_at = ?, min_stake = ?, max_stake = ?,
                   fee_bps = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ? AND status NOT IN ('SETTLED', 'CANCELLED')""",
            (market, _db_time(lock_at), minimum, maximum, fee, int(match_id)),
        )
        await db.commit()
    finally:
        await db.close()
    _invalidate_open_match_cache()
    return await get_game_match(match_id)


async def publish_game_match(match_id: int) -> dict:
    existing = await get_game_match(match_id)
    if not existing:
        raise GameError("not_found", "Match not found")
    if str(existing.get("provider_status") or "").upper() not in {"SCHEDULED", "TIMED"}:
        raise GameError("invalid_provider_status", "Only scheduled matches can be published")
    if (_parse_time(existing.get("lock_at")) or _utc_now()) <= _utc_now():
        raise GameError("match_started", "Predictions would already be closed for this match")
    db = await get_db()
    try:
        await db.execute(
            """UPDATE game_matches
               SET status = 'OPEN', published_at = COALESCE(published_at, CURRENT_TIMESTAMP),
                   next_sync_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
               WHERE id = ? AND status = 'DRAFT'""",
            (int(match_id),),
        )
        await db.commit()
    finally:
        await db.close()
    _invalidate_open_match_cache()
    match = await get_game_match(match_id)
    if not match:
        raise GameError("not_found", "Match not found")
    return match


async def get_game_wallet(user_telegram_id: int) -> dict:
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT * FROM game_wallets WHERE user_telegram_id = ?",
            (int(user_telegram_id),),
        )
        row = _dict(await cursor.fetchone()) or {
            "user_telegram_id": int(user_telegram_id),
            "balance": 0,
            "last_claim_date": None,
            "lifetime_earned": 0,
            "lifetime_spent": 0,
        }
        row["balance"] = int(row.get("balance") or 0)
        row["claim_available"] = str(row.get("last_claim_date") or "") < _utc_now().date().isoformat()
        row["daily_claim"] = GAME_DAILY_CLAIM
        return row
    finally:
        await db.close()


async def claim_daily_coins(user_telegram_id: int) -> dict:
    user_id = int(user_telegram_id)
    today = _utc_now().date().isoformat()
    idempotency_key = f"daily:{user_id}:{today}"
    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "INSERT OR IGNORE INTO game_wallets (user_telegram_id) VALUES (?)",
            (user_id,),
        )
        cursor = await db.execute(
            "SELECT balance, last_claim_date FROM game_wallets WHERE user_telegram_id = ?",
            (user_id,),
        )
        wallet = _dict(await cursor.fetchone())
        if wallet and str(wallet.get("last_claim_date") or "") >= today:
            await db.rollback()
            result = await get_game_wallet(user_id)
            result["claimed"] = False
            return result

        new_balance = int((wallet or {}).get("balance") or 0) + GAME_DAILY_CLAIM
        await db.execute(
            """UPDATE game_wallets
               SET balance = ?, last_claim_date = ?, lifetime_earned = lifetime_earned + ?,
                   updated_at = CURRENT_TIMESTAMP
               WHERE user_telegram_id = ?""",
            (new_balance, today, GAME_DAILY_CLAIM, user_id),
        )
        await db.execute(
            """INSERT OR IGNORE INTO game_ledger
               (user_telegram_id, amount, balance_after, event_type, reference_type,
                reference_id, idempotency_key)
               VALUES (?, ?, ?, 'DAILY_CLAIM', 'day', ?, ?)""",
            (user_id, GAME_DAILY_CLAIM, new_balance, today, idempotency_key),
        )
        await db.commit()
        return {
            "user_telegram_id": user_id,
            "balance": new_balance,
            "last_claim_date": today,
            "claim_available": False,
            "daily_claim": GAME_DAILY_CLAIM,
            "claimed": True,
        }
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()


def _valid_outcomes_for_market(market_type: str) -> set[str]:
    return {"home", "away"} if market_type == "qualified" else VALID_OUTCOMES


async def place_game_bet(user_telegram_id: int, match_id: int, outcome: str, stake: int) -> dict:
    user_id = int(user_telegram_id)
    match_id = int(match_id)
    amount = int(stake)
    chosen = str(outcome or "").lower()
    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute("SELECT * FROM game_matches WHERE id = ?", (match_id,))
        match = _dict(await cursor.fetchone())
        if not match:
            raise GameError("not_found", "Match not found")
        if _effective_status(match) != "OPEN":
            raise GameError("closed", "Predictions are closed for this match")
        if chosen not in _valid_outcomes_for_market(str(match.get("market_type") or "qualified")):
            raise GameError("invalid_outcome", "Invalid prediction")
        minimum = int(match.get("min_stake") or GAME_DEFAULT_MIN_STAKE)
        maximum = int(match.get("max_stake") or GAME_DEFAULT_MAX_STAKE)
        if amount < minimum or amount > maximum:
            raise GameError("invalid_stake", f"Stake must be between {minimum} and {maximum}")

        cursor = await db.execute(
            "SELECT id, outcome, stake FROM game_bets WHERE match_id = ? AND user_telegram_id = ?",
            (match_id, user_id),
        )
        existing = _dict(await cursor.fetchone())
        if existing:
            raise GameError("already_bet", "You already predicted this match")

        await db.execute(
            "INSERT OR IGNORE INTO game_wallets (user_telegram_id) VALUES (?)",
            (user_id,),
        )
        cursor = await db.execute(
            "SELECT balance FROM game_wallets WHERE user_telegram_id = ?",
            (user_id,),
        )
        wallet = _dict(await cursor.fetchone())
        balance = int((wallet or {}).get("balance") or 0)
        if balance < amount:
            raise GameError("insufficient_balance", "Not enough game coins")

        await db.execute(
            "INSERT INTO game_bets (match_id, user_telegram_id, outcome, stake) VALUES (?, ?, ?, ?)",
            (match_id, user_id, chosen, amount),
        )
        cursor = await db.execute(
            "SELECT id FROM game_bets WHERE match_id = ? AND user_telegram_id = ?",
            (match_id, user_id),
        )
        bet_id = int((await cursor.fetchone())["id"])
        new_balance = balance - amount
        await db.execute(
            """UPDATE game_wallets
               SET balance = ?, lifetime_spent = lifetime_spent + ?, updated_at = CURRENT_TIMESTAMP
               WHERE user_telegram_id = ?""",
            (new_balance, amount, user_id),
        )
        await db.execute(
            """INSERT INTO game_ledger
               (user_telegram_id, amount, balance_after, event_type, reference_type,
                reference_id, idempotency_key)
               VALUES (?, ?, ?, 'BET', 'bet', ?, ?)""",
            (user_id, -amount, new_balance, str(bet_id), f"bet:{bet_id}"),
        )
        await db.commit()
        _invalidate_open_match_cache()
        return {
            "id": bet_id,
            "match_id": match_id,
            "outcome": chosen,
            "stake": amount,
            "balance": new_balance,
        }
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()


async def list_user_game_bets(user_telegram_id: int, limit: int = 10) -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT gb.*, gm.home_name, gm.away_name, gm.utc_date, gm.market_type,
                      gm.status AS match_status, gm.result_outcome
               FROM game_bets gb
               JOIN game_matches gm ON gm.id = gb.match_id
               WHERE gb.user_telegram_id = ?
               ORDER BY gb.created_at DESC
               LIMIT ?""",
            (int(user_telegram_id), max(1, min(50, int(limit)))),
        )
        return [dict(row) for row in await cursor.fetchall()]
    finally:
        await db.close()


async def get_game_leaderboard(limit: int = 10) -> list[dict]:
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT gw.user_telegram_id, gw.balance, gw.lifetime_earned,
                      u.username, u.first_name
               FROM game_wallets gw
               LEFT JOIN users u ON u.telegram_id = gw.user_telegram_id
               ORDER BY gw.balance DESC, gw.lifetime_earned DESC
               LIMIT ?""",
            (max(1, min(50, int(limit))),),
        )
        return [dict(row) for row in await cursor.fetchall()]
    finally:
        await db.close()


async def settle_game_match(match_id: int, result_outcome: str) -> dict:
    match_id = int(match_id)
    outcome = str(result_outcome or "").lower()
    if outcome not in VALID_OUTCOMES:
        raise GameError("invalid_outcome", "Invalid result")
    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute("SELECT * FROM game_matches WHERE id = ?", (match_id,))
        match = _dict(await cursor.fetchone())
        if not match:
            raise GameError("not_found", "Match not found")
        if match.get("status") == "SETTLED":
            await db.rollback()
            return await get_game_match(match_id)
        if match.get("status") in {"DRAFT", "CANCELLED"}:
            raise GameError("invalid_status", "This match cannot be settled")
        if outcome not in _valid_outcomes_for_market(str(match.get("market_type") or "qualified")):
            raise GameError("invalid_outcome", "This result is not valid for the selected market")

        await db.execute(
            "UPDATE game_matches SET status = 'SETTLING', result_outcome = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (outcome, match_id),
        )
        cursor = await db.execute(
            "SELECT * FROM game_bets WHERE match_id = ? AND status = 'ACTIVE' ORDER BY id",
            (match_id,),
        )
        bets = [dict(row) for row in await cursor.fetchall()]
        total_pool = sum(int(bet["stake"]) for bet in bets)
        winners = [bet for bet in bets if bet["outcome"] == outcome]
        winning_pool = sum(int(bet["stake"]) for bet in winners)
        fee_bps = int(match.get("fee_bps") or 0)
        distributable = math.floor(total_pool * (10000 - fee_bps) / 10000)

        wallet_updates: list[tuple[int, int, int]] = []
        bet_updates: list[tuple[str, int, int]] = []
        ledger_rows: list[tuple] = []
        if bets and not winners:
            for bet in bets:
                payout = int(bet["stake"])
                wallet_updates.append((payout, 0, int(bet["user_telegram_id"])))
                bet_updates.append(("REFUNDED", payout, int(bet["id"])))
        else:
            for bet in bets:
                if bet["outcome"] == outcome and winning_pool > 0:
                    payout = math.floor(distributable * int(bet["stake"]) / winning_pool)
                    wallet_updates.append((payout, payout, int(bet["user_telegram_id"])))
                    bet_updates.append(("WON", payout, int(bet["id"])))
                else:
                    bet_updates.append(("LOST", 0, int(bet["id"])))

        if wallet_updates:
            await db.executemany(
                """UPDATE game_wallets
                   SET balance = balance + ?, lifetime_earned = lifetime_earned + ?,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE user_telegram_id = ?""",
                wallet_updates,
            )
        if bet_updates:
            await db.executemany(
                "UPDATE game_bets SET status = ?, payout = ?, settled_at = CURRENT_TIMESTAMP WHERE id = ?",
                bet_updates,
            )
        balances_after: dict[int, int] = {}
        payout_user_ids = sorted({user_id for amount, _earned, user_id in wallet_updates if amount > 0})
        if payout_user_ids:
            placeholders = ",".join("?" for _ in payout_user_ids)
            cursor = await db.execute(
                f"SELECT user_telegram_id, balance FROM game_wallets WHERE user_telegram_id IN ({placeholders})",
                tuple(payout_user_ids),
            )
            balances_after = {
                int(row["user_telegram_id"]): int(row["balance"])
                for row in await cursor.fetchall()
            }
        bets_by_id = {int(item["id"]): item for item in bets}
        for status_value, payout, bet_id in bet_updates:
            if payout <= 0:
                continue
            bet = bets_by_id[bet_id]
            user_id = int(bet["user_telegram_id"])
            balance_after = balances_after[user_id]
            ledger_rows.append((
                user_id, payout, balance_after,
                "BET_REFUND" if status_value == "REFUNDED" else "BET_PAYOUT",
                "bet", str(bet_id), f"settle:{match_id}:{bet_id}",
            ))
        if ledger_rows:
            await db.executemany(
                """INSERT OR IGNORE INTO game_ledger
                   (user_telegram_id, amount, balance_after, event_type, reference_type,
                    reference_id, idempotency_key)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ledger_rows,
            )
        await db.execute(
            """UPDATE game_matches
               SET status = 'SETTLED', result_outcome = ?, settled_at = CURRENT_TIMESTAMP,
                   next_sync_at = NULL, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (outcome, match_id),
        )
        await db.commit()
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()
    _invalidate_open_match_cache()
    result = await get_game_match(match_id)
    result["distributed"] = sum(amount for amount, _earned, _user_id in wallet_updates)
    result["winner_count"] = len(winners)
    return result


async def cancel_game_match(match_id: int) -> dict:
    match_id = int(match_id)
    db = await get_db()
    refunded = 0
    try:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute("SELECT status FROM game_matches WHERE id = ?", (match_id,))
        match = _dict(await cursor.fetchone())
        if not match:
            raise GameError("not_found", "Match not found")
        if match["status"] == "SETTLED":
            raise GameError("already_settled", "A settled match cannot be cancelled")
        if match["status"] == "CANCELLED":
            await db.rollback()
            return await get_game_match(match_id)
        cursor = await db.execute(
            "SELECT * FROM game_bets WHERE match_id = ? AND status = 'ACTIVE'",
            (match_id,),
        )
        bets = [dict(row) for row in await cursor.fetchall()]
        if bets:
            await db.executemany(
                """UPDATE game_wallets
                   SET balance = balance + ?, lifetime_earned = lifetime_earned + ?,
                       updated_at = CURRENT_TIMESTAMP
                   WHERE user_telegram_id = ?""",
                [(int(bet["stake"]), 0, int(bet["user_telegram_id"])) for bet in bets],
            )
            await db.executemany(
                "UPDATE game_bets SET status = 'REFUNDED', payout = stake, settled_at = CURRENT_TIMESTAMP WHERE id = ?",
                [(int(bet["id"]),) for bet in bets],
            )
            user_ids = sorted({int(bet["user_telegram_id"]) for bet in bets})
            placeholders = ",".join("?" for _ in user_ids)
            cursor = await db.execute(
                f"SELECT user_telegram_id, balance FROM game_wallets WHERE user_telegram_id IN ({placeholders})",
                tuple(user_ids),
            )
            balances_after = {
                int(row["user_telegram_id"]): int(row["balance"])
                for row in await cursor.fetchall()
            }
            ledger_rows = []
            for bet in bets:
                user_id = int(bet["user_telegram_id"])
                balance_after = balances_after[user_id]
                ledger_rows.append((
                    user_id, int(bet["stake"]), balance_after,
                    "BET_REFUND", "bet", str(bet["id"]), f"cancel:{match_id}:{bet['id']}",
                ))
                refunded += int(bet["stake"])
            await db.executemany(
                """INSERT OR IGNORE INTO game_ledger
                   (user_telegram_id, amount, balance_after, event_type, reference_type,
                    reference_id, idempotency_key)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ledger_rows,
            )
        await db.execute(
            """UPDATE game_matches
               SET status = 'CANCELLED', cancelled_at = CURRENT_TIMESTAMP,
                   next_sync_at = NULL, updated_at = CURRENT_TIMESTAMP
               WHERE id = ?""",
            (match_id,),
        )
        await db.commit()
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()
    _invalidate_open_match_cache()
    result = await get_game_match(match_id)
    result["refunded"] = refunded
    return result


async def list_due_game_matches(limit: int = 30) -> list[dict]:
    now_text = _db_time(_utc_now())
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT * FROM game_matches
               WHERE status IN ('OPEN', 'LOCKED')
                 AND (next_sync_at IS NULL OR next_sync_at <= ?)
               ORDER BY utc_date ASC
               LIMIT ?""",
            (now_text, max(1, min(100, int(limit)))),
        )
        return [dict(row) for row in await cursor.fetchall()]
    finally:
        await db.close()


def _next_sync_time(match_data: dict) -> str | None:
    provider_status = str(match_data.get("provider_status") or "").upper()
    if provider_status in FINAL_PROVIDER_STATUSES:
        return None
    now = _utc_now()
    starts_at = _parse_time(match_data.get("utc_date")) or now
    until_start = starts_at - now
    if until_start > timedelta(hours=24):
        delay = timedelta(hours=6)
    elif until_start > timedelta(hours=2):
        delay = timedelta(minutes=30)
    else:
        delay = timedelta(minutes=10)
    return _db_time(now + delay)


async def update_game_match_from_provider(match_id: int, provider_match: dict) -> dict:
    now = _utc_now()
    match = await get_game_match(match_id)
    if not match:
        raise GameError("not_found", "Match not found")
    next_status = match["status"]
    lock_at = _parse_time(match.get("lock_at"))
    if next_status == "OPEN" and lock_at is not None and lock_at <= now:
        next_status = "LOCKED"
    raw_payload = json.dumps(provider_match.get("raw_payload") or {}, ensure_ascii=False, separators=(",", ":"))
    db = await get_db()
    try:
        await db.execute(
            """UPDATE game_matches SET
                   competition_code = ?, competition_name = ?, competition_emblem = ?,
                   stage = ?, home_name = ?, home_code = ?, home_crest = ?,
                   away_name = ?, away_code = ?, away_crest = ?, utc_date = ?,
                   provider_status = ?, provider_winner = ?, score_home = ?, score_away = ?,
                   regular_score_home = ?, regular_score_away = ?, raw_payload = ?,
                   status = ?, last_synced_at = ?, next_sync_at = ?, updated_at = CURRENT_TIMESTAMP
               WHERE id = ? AND status NOT IN ('SETTLED', 'CANCELLED')""",
            (
                provider_match.get("competition_code") or "",
                provider_match.get("competition_name") or "Football",
                provider_match.get("competition_emblem") or "",
                provider_match.get("stage") or "",
                provider_match.get("home_name") or match["home_name"],
                provider_match.get("home_code") or "",
                provider_match.get("home_crest") or "",
                provider_match.get("away_name") or match["away_name"],
                provider_match.get("away_code") or "",
                provider_match.get("away_crest") or "",
                _db_time(provider_match.get("utc_date") or match["utc_date"]),
                provider_match.get("provider_status") or "SCHEDULED",
                provider_match.get("provider_winner"),
                provider_match.get("score_home"),
                provider_match.get("score_away"),
                provider_match.get("regular_score_home"),
                provider_match.get("regular_score_away"),
                raw_payload,
                next_status,
                _db_time(now),
                _next_sync_time(provider_match),
                int(match_id),
            ),
        )
        await db.commit()
    finally:
        await db.close()
    _invalidate_open_match_cache()
    return await get_game_match(match_id)


async def defer_game_match_sync(match_id: int, minutes: int = 10) -> None:
    db = await get_db()
    try:
        await db.execute(
            "UPDATE game_matches SET next_sync_at = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (_db_time(_utc_now() + timedelta(minutes=max(1, int(minutes)))), int(match_id)),
        )
        await db.commit()
    finally:
        await db.close()


def summarize_game_matches(matches: list[dict]) -> dict:
    return {
        "open": sum(1 for item in matches if item["status"] == "OPEN"),
        "locked": sum(1 for item in matches if item["status"] == "LOCKED"),
        "settled": sum(1 for item in matches if item["status"] == "SETTLED"),
        "cancelled": sum(1 for item in matches if item["status"] == "CANCELLED"),
        "bets": sum(int(item.get("bet_count") or 0) for item in matches),
        "coins_staked": sum(int(item.get("total_pool") or 0) for item in matches),
    }


async def game_dashboard_summary() -> dict:
    return summarize_game_matches(
        await list_game_matches(include_cancelled=True, limit=1000)
    )
