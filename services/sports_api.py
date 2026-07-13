"""Lightweight football-data.org client used by the virtual match game."""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import date, datetime, timezone
from typing import Any

import httpx

from config import FOOTBALL_DATA_API_KEY, FOOTBALL_DATA_BASE_URL


logger = logging.getLogger(__name__)
_CLIENT: httpx.AsyncClient | None = None
_CATALOG_CACHE: dict[tuple[str, str, str], tuple[float, list[dict]]] = {}
_CACHE_LOCK = asyncio.Lock()
_CACHE_SECONDS = 300
_LAST_QUOTA: dict[str, str] = {}


class SportsAPIError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.retryable = retryable


def is_sports_api_configured() -> bool:
    return bool(
        FOOTBALL_DATA_API_KEY
        and FOOTBALL_DATA_BASE_URL.startswith("https://")
    )


async def _client() -> httpx.AsyncClient:
    global _CLIENT
    if _CLIENT is None or _CLIENT.is_closed:
        _CLIENT = httpx.AsyncClient(
            base_url=FOOTBALL_DATA_BASE_URL,
            timeout=httpx.Timeout(15.0, connect=6.0),
            headers={
                "X-Auth-Token": FOOTBALL_DATA_API_KEY,
                "Accept": "application/json",
            },
        )
    return _CLIENT


async def close_sports_client() -> None:
    global _CLIENT
    if _CLIENT is not None and not _CLIENT.is_closed:
        await _CLIENT.aclose()
    _CLIENT = None
    _CATALOG_CACHE.clear()


def _provider_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
        if isinstance(payload, dict):
            return str(payload.get("message") or payload.get("error") or response.text)
    except Exception:
        pass
    return response.text.strip() or f"Sports API HTTP {response.status_code}"


def _record_quota(response: httpx.Response) -> None:
    for key in (
        "x-requests-available-minute",
        "x-requestcounter-reset",
        "x-ratelimit-remaining",
    ):
        if response.headers.get(key) is not None:
            _LAST_QUOTA[key] = response.headers[key]


async def _request(path: str, *, params: dict | None = None) -> Any:
    if not is_sports_api_configured():
        raise SportsAPIError("FOOTBALL_DATA_API_KEY is not configured")
    for attempt in range(2):
        try:
            response = await (await _client()).get(path, params=params)
            _record_quota(response)
            if response.status_code >= 400:
                retryable = response.status_code == 429 or response.status_code >= 500
                if retryable and attempt == 0:
                    await asyncio.sleep(1)
                    continue
                raise SportsAPIError(
                    _provider_error(response),
                    status_code=response.status_code,
                    retryable=retryable,
                )
            payload = response.json()
            if not isinstance(payload, (dict, list)):
                raise SportsAPIError("Sports provider returned invalid JSON")
            return payload
        except SportsAPIError:
            raise
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            if attempt == 0:
                await asyncio.sleep(1)
                continue
            raise SportsAPIError("Sports provider is temporarily unreachable", retryable=True) from exc
        except ValueError as exc:
            raise SportsAPIError("Sports provider returned invalid JSON") from exc
    raise SportsAPIError("Sports provider request failed", retryable=True)


def _integer_or_none(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _outcome_from_winner(winner: Any) -> str | None:
    return {
        "HOME_TEAM": "home",
        "AWAY_TEAM": "away",
        "DRAW": "draw",
    }.get(str(winner or "").upper())


def normalize_match(raw: dict) -> dict | None:
    """Normalize one football-data match into VenteBot's stable contract."""
    external_id = raw.get("id")
    utc_date = str(raw.get("utcDate") or "").strip()
    home = raw.get("homeTeam") if isinstance(raw.get("homeTeam"), dict) else {}
    away = raw.get("awayTeam") if isinstance(raw.get("awayTeam"), dict) else {}
    competition = raw.get("competition") if isinstance(raw.get("competition"), dict) else {}
    if external_id is None or not utc_date or not home.get("name") or not away.get("name"):
        return None

    score = raw.get("score") if isinstance(raw.get("score"), dict) else {}
    full_time = score.get("fullTime") if isinstance(score.get("fullTime"), dict) else {}
    regular_time = score.get("regularTime") if isinstance(score.get("regularTime"), dict) else {}
    full_home = _integer_or_none(full_time.get("home"))
    full_away = _integer_or_none(full_time.get("away"))
    regular_home = _integer_or_none(regular_time.get("home"))
    regular_away = _integer_or_none(regular_time.get("away"))
    if regular_home is None and str(score.get("duration") or "").upper() == "REGULAR":
        regular_home = full_home
        regular_away = full_away

    regulation_outcome = None
    if regular_home is not None and regular_away is not None:
        regulation_outcome = "home" if regular_home > regular_away else "away" if regular_away > regular_home else "draw"

    return {
        "provider": "football-data",
        "external_match_id": str(external_id),
        "competition_code": str(competition.get("code") or ""),
        "competition_name": str(competition.get("name") or "Football"),
        "competition_emblem": str(competition.get("emblem") or ""),
        "stage": str(raw.get("stage") or raw.get("group") or ""),
        "home_external_id": str(home.get("id") or ""),
        "home_name": str(home.get("name") or ""),
        "home_code": str(home.get("tla") or home.get("shortName") or ""),
        "home_crest": str(home.get("crest") or ""),
        "away_external_id": str(away.get("id") or ""),
        "away_name": str(away.get("name") or ""),
        "away_code": str(away.get("tla") or away.get("shortName") or ""),
        "away_crest": str(away.get("crest") or ""),
        "utc_date": utc_date,
        "provider_status": str(raw.get("status") or "SCHEDULED").upper(),
        "provider_winner": _outcome_from_winner(score.get("winner")),
        "regulation_outcome": regulation_outcome,
        "score_home": full_home,
        "score_away": full_away,
        "regular_score_home": regular_home,
        "regular_score_away": regular_away,
        "raw_payload": raw,
    }


async def list_football_matches(
    date_from: date | str,
    date_to: date | str,
    *,
    competition: str = "",
    force: bool = False,
) -> list[dict]:
    start = date_from.isoformat() if isinstance(date_from, date) else str(date_from)
    end = date_to.isoformat() if isinstance(date_to, date) else str(date_to)
    competition_code = str(competition or "").strip().upper()
    cache_key = (start, end, competition_code)
    now = time.monotonic()
    cached = _CATALOG_CACHE.get(cache_key)
    if not force and cached and now - cached[0] < _CACHE_SECONDS:
        return [dict(item) for item in cached[1]]

    async with _CACHE_LOCK:
        now = time.monotonic()
        cached = _CATALOG_CACHE.get(cache_key)
        if not force and cached and now - cached[0] < _CACHE_SECONDS:
            return [dict(item) for item in cached[1]]
        params = {"dateFrom": start, "dateTo": end}
        if competition_code:
            params["competitions"] = competition_code
        payload = await _request("/matches", params=params)
        raw_matches = payload.get("matches", []) if isinstance(payload, dict) else []
        matches = [item for raw in raw_matches if isinstance(raw, dict) if (item := normalize_match(raw))]
        _CATALOG_CACHE[cache_key] = (time.monotonic(), matches)
        if len(_CATALOG_CACHE) > 40:
            oldest = sorted(_CATALOG_CACHE, key=lambda key: _CATALOG_CACHE[key][0])[:10]
            for key in oldest:
                _CATALOG_CACHE.pop(key, None)
        return [dict(item) for item in matches]


async def get_football_match(external_match_id: str) -> dict:
    payload = await _request(f"/matches/{str(external_match_id).strip()}")
    if not isinstance(payload, dict):
        raise SportsAPIError("Sports provider returned an invalid match")
    match = normalize_match(payload)
    if not match:
        raise SportsAPIError("Sports provider returned an incomplete match")
    return match


def sports_provider_status() -> dict:
    return {
        "provider": "football-data",
        "configured": is_sports_api_configured(),
        "base_url": FOOTBALL_DATA_BASE_URL,
        "catalog_cache_entries": len(_CATALOG_CACHE),
        "quota": dict(_LAST_QUOTA),
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
