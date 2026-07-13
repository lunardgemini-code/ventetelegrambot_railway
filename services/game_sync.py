"""Adaptive background synchronization for published virtual-game matches."""

from __future__ import annotations

import asyncio
import logging
import os
from collections import defaultdict

from database.games import (
    defer_game_match_sync,
    list_due_game_matches,
    update_game_match_from_provider,
)
from services.sports_api import is_sports_api_configured, list_football_matches


logger = logging.getLogger(__name__)
GAME_SYNC_WORKER_SECONDS = max(60, int(os.environ.get("GAME_SYNC_WORKER_SECONDS", "120")))


async def sync_due_game_matches_once(limit: int = 30) -> dict:
    if not is_sports_api_configured():
        return {"configured": False, "due": 0, "updated": 0, "failed": 0}

    due_matches = await list_due_game_matches(limit=limit)
    if not due_matches:
        return {"configured": True, "due": 0, "updated": 0, "failed": 0}

    by_date: dict[str, list[dict]] = defaultdict(list)
    for match in due_matches:
        match_date = str(match.get("utc_date") or "")[:10]
        if match_date:
            by_date[match_date].append(match)

    updated = 0
    failed = 0
    for match_date, saved_matches in by_date.items():
        try:
            provider_matches = await list_football_matches(
                match_date,
                match_date,
                force=True,
            )
            provider_by_id = {
                str(item["external_match_id"]): item for item in provider_matches
            }
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Game match synchronization failed for %s: %s", match_date, exc)
            failed += len(saved_matches)
            for saved in saved_matches:
                await defer_game_match_sync(int(saved["id"]), minutes=10)
            continue

        for saved in saved_matches:
            provider_match = provider_by_id.get(str(saved["external_match_id"]))
            try:
                if provider_match is None:
                    await defer_game_match_sync(int(saved["id"]), minutes=30)
                    failed += 1
                    continue
                await update_game_match_from_provider(int(saved["id"]), provider_match)
                updated += 1
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                failed += 1
                logger.warning("Could not update game match %s: %s", saved.get("id"), exc)
                await defer_game_match_sync(int(saved["id"]), minutes=10)

    return {
        "configured": True,
        "due": len(due_matches),
        "updated": updated,
        "failed": failed,
    }


async def game_sync_worker() -> None:
    while True:
        try:
            result = await sync_due_game_matches_once()
            if result.get("updated") or result.get("failed"):
                logger.info("Game match sync: %s", result)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Game match synchronization cycle failed: %s", exc)
        await asyncio.sleep(GAME_SYNC_WORKER_SECONDS)
