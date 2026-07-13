"""Pure helpers for the game's live pari-mutuel odds."""

from __future__ import annotations

import math


def _market_outcomes(match: dict) -> tuple[str, ...]:
    if str(match.get("market_type") or "qualified").lower() == "regulation":
        return ("home", "draw", "away")
    return ("home", "away")


def _pool_value(match: dict, outcome: str) -> int:
    return max(0, int(match.get(f"{outcome}_pool") or 0))


def _distributable_pool(total_pool: int, fee_bps: int) -> int:
    fee = min(2500, max(0, int(fee_bps)))
    return math.floor(max(0, int(total_pool)) * (10000 - fee) / 10000)


def calculate_match_odds(match: dict) -> dict[str, float | None]:
    """Return the current payout multiplier for each valid outcome."""
    outcomes = _market_outcomes(match)
    pools = {outcome: _pool_value(match, outcome) for outcome in outcomes}
    total_pool = sum(pools.values())
    distributable = _distributable_pool(total_pool, int(match.get("fee_bps") or 0))
    return {
        outcome: (distributable / pool if pool > 0 and distributable > 0 else None)
        for outcome, pool in pools.items()
    }


def estimate_bet_return(match: dict, outcome: str, stake: int) -> dict[str, int | float | None]:
    """Estimate payout after adding a prospective stake to the current pools."""
    chosen = str(outcome or "").lower()
    amount = max(0, int(stake))
    outcomes = _market_outcomes(match)
    if chosen not in outcomes or amount <= 0:
        return {"payout": 0, "odds": None}

    pools = {item: _pool_value(match, item) for item in outcomes}
    pools[chosen] += amount
    total_pool = sum(pools.values())
    distributable = _distributable_pool(total_pool, int(match.get("fee_bps") or 0))
    payout = math.floor(distributable * amount / pools[chosen]) if pools[chosen] else 0
    return {
        "payout": payout,
        "odds": payout / amount if payout > 0 else None,
    }


def format_game_odd(value: float | None) -> str:
    """Format a multiplier compactly for Telegram buttons and messages."""
    return "—" if value is None else f"x{value:.2f}"
