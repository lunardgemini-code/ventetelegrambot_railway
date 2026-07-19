"""Persistent background jobs and durable performance aggregates."""

from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

from database.db import get_db, is_transient_db_connection_error


logger = logging.getLogger(__name__)
T = TypeVar("T")


async def _retry_read(operation: Callable[[bool], Awaitable[T]]) -> T:
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            return await operation(attempt > 0)
        except Exception as exc:
            last_error = exc
            if not is_transient_db_connection_error(exc) or attempt:
                raise
            await asyncio.sleep(0.1)
    raise RuntimeError("Persistent job database unavailable") from last_error


def _decode_job(row: Any) -> dict | None:
    if not row:
        return None
    job = dict(row)
    try:
        payload = json.loads(job.pop("payload_json", "{}") or "{}")
    except (TypeError, ValueError, json.JSONDecodeError):
        payload = {}
    job["payload"] = payload if isinstance(payload, dict) else {}
    return job


async def create_background_job(
    job_id: str,
    job_type: str,
    payload: dict,
    *,
    max_attempts: int = 3,
    progress_total: int = 0,
) -> dict:
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO background_jobs
               (id, job_type, payload_json, max_attempts, progress_total)
               VALUES (?, ?, ?, ?, ?)""",
            (
                str(job_id),
                str(job_type),
                json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                max(1, int(max_attempts)),
                max(0, int(progress_total)),
            ),
        )
        await db.commit()
    finally:
        await db.close()
    job = await get_background_job(job_id)
    if not job:
        raise RuntimeError("Background job was not persisted")
    return job


async def create_background_job_once(
    job_id: str,
    job_type: str,
    payload: dict,
    *,
    max_attempts: int = 3,
) -> tuple[dict, bool]:
    """Create a deterministic job once and return (job, created)."""
    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            "SELECT 1 FROM background_jobs WHERE id = ? LIMIT 1",
            (str(job_id),),
        )
        created = await cursor.fetchone() is None
        if created:
            await db.execute(
                """INSERT INTO background_jobs
                   (id, job_type, payload_json, max_attempts)
                   VALUES (?, ?, ?, ?)""",
                (
                    str(job_id),
                    str(job_type),
                    json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
                    max(1, int(max_attempts)),
                ),
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
    job = await get_background_job(job_id)
    if not job:
        raise RuntimeError("Background job was not persisted")
    return job, created


async def get_background_job(job_id: str) -> dict | None:
    async def read(fresh: bool) -> dict | None:
        db = await get_db(fresh=fresh)
        try:
            cursor = await db.execute(
                "SELECT * FROM background_jobs WHERE id = ?",
                (str(job_id),),
            )
            return _decode_job(await cursor.fetchone())
        finally:
            await db.close()

    return await _retry_read(read)


async def claim_next_background_job() -> dict | None:
    """Atomically claim the oldest runnable job."""
    db = await get_db()
    try:
        await db.execute("BEGIN IMMEDIATE")
        cursor = await db.execute(
            """SELECT id FROM background_jobs
               WHERE status = 'queued'
                 AND available_at <= CURRENT_TIMESTAMP
               ORDER BY created_at ASC, id ASC
               LIMIT 1"""
        )
        candidate = await cursor.fetchone()
        if not candidate:
            await db.commit()
            return None
        job_id = str(candidate["id"])
        cursor = await db.execute(
            """UPDATE background_jobs
               SET status = 'running', attempts = attempts + 1,
                   claimed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP,
                   error = NULL
               WHERE id = ? AND status = 'queued'""",
            (job_id,),
        )
        if cursor.rowcount not in (-1, 1):
            await db.rollback()
            return None
        cursor = await db.execute(
            "SELECT * FROM background_jobs WHERE id = ?",
            (job_id,),
        )
        job = _decode_job(await cursor.fetchone())
        await db.commit()
        return job
    except Exception:
        try:
            await db.rollback()
        except Exception:
            pass
        raise
    finally:
        await db.close()


async def update_background_job_progress(
    job_id: str,
    *,
    done: int,
    failed: int,
    total: int,
    cursor_value: int,
) -> None:
    db = await get_db()
    try:
        await db.execute(
            """UPDATE background_jobs
               SET progress_done = ?, progress_failed = ?, progress_total = ?,
                   cursor_value = ?, claimed_at = CURRENT_TIMESTAMP,
                   updated_at = CURRENT_TIMESTAMP
               WHERE id = ? AND status = 'running'""",
            (
                max(0, int(done)),
                max(0, int(failed)),
                max(0, int(total)),
                max(0, int(cursor_value)),
                str(job_id),
            ),
        )
        await db.commit()
    finally:
        await db.close()


async def complete_background_job(
    job_id: str,
    *,
    done: int,
    failed: int,
    total: int,
    cursor_value: int,
) -> None:
    db = await get_db()
    try:
        await db.execute(
            """UPDATE background_jobs
               SET status = 'completed', progress_done = ?, progress_failed = ?,
                   progress_total = ?, cursor_value = ?, claimed_at = NULL,
                   completed_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP,
                   error = NULL
               WHERE id = ?""",
            (
                max(0, int(done)),
                max(0, int(failed)),
                max(0, int(total)),
                max(0, int(cursor_value)),
                str(job_id),
            ),
        )
        await db.commit()
    finally:
        await db.close()


async def fail_background_job(job_id: str, error: str, *, retry_delay_seconds: int = 15) -> str:
    db = await get_db()
    try:
        modifier = f"+{max(1, int(retry_delay_seconds))} seconds"
        await db.execute(
            """UPDATE background_jobs
               SET status = CASE WHEN attempts >= max_attempts THEN 'failed' ELSE 'queued' END,
                   available_at = CASE WHEN attempts >= max_attempts
                       THEN available_at ELSE datetime('now', ?) END,
                   claimed_at = NULL, error = ?, updated_at = CURRENT_TIMESTAMP,
                   completed_at = CASE WHEN attempts >= max_attempts
                       THEN CURRENT_TIMESTAMP ELSE NULL END
               WHERE id = ?""",
            (modifier, str(error or "Background job failed")[:500], str(job_id)),
        )
        await db.commit()
        cursor = await db.execute(
            "SELECT status FROM background_jobs WHERE id = ?",
            (str(job_id),),
        )
        row = await cursor.fetchone()
        return str(row["status"] if row else "failed")
    finally:
        await db.close()


async def requeue_stale_background_jobs(stale_seconds: int = 180) -> int:
    db = await get_db()
    try:
        modifier = f"-{max(30, int(stale_seconds))} seconds"
        cursor = await db.execute(
            """UPDATE background_jobs
               SET status = 'queued', claimed_at = NULL,
                   available_at = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP,
                   error = COALESCE(error, 'Recovered after interrupted worker')
               WHERE status = 'running'
                 AND claimed_at <= datetime('now', ?)""",
            (modifier,),
        )
        await db.commit()
        return max(0, int(cursor.rowcount)) if cursor.rowcount != -1 else 0
    finally:
        await db.close()


async def cleanup_background_jobs(retention_days: int = 7) -> int:
    db = await get_db()
    try:
        modifier = f"-{max(1, int(retention_days))} days"
        cursor = await db.execute(
            """DELETE FROM background_jobs
               WHERE status IN ('completed', 'failed')
                 AND updated_at < datetime('now', ?)""",
            (modifier,),
        )
        await db.commit()
        return max(0, int(cursor.rowcount)) if cursor.rowcount != -1 else 0
    finally:
        await db.close()


async def get_broadcast_recipient_window() -> dict:
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT COALESCE(MAX(id), 0) AS max_user_id, COUNT(*) AS total
               FROM users WHERE COALESCE(is_banned, 0) = 0"""
        )
        row = await cursor.fetchone()
        return {
            "max_user_id": int(row["max_user_id"] if row else 0),
            "total": int(row["total"] if row else 0),
        }
    finally:
        await db.close()


async def flush_performance_action_hourly(rows: list[dict]) -> None:
    if not rows:
        return
    db = await get_db()
    try:
        await db.executemany(
            """INSERT INTO performance_action_hourly
               (bucket_hour, action, sample_count, error_count, total_duration_ms, max_duration_ms)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(bucket_hour, action) DO UPDATE SET
                   sample_count = sample_count + excluded.sample_count,
                   error_count = error_count + excluded.error_count,
                   total_duration_ms = total_duration_ms + excluded.total_duration_ms,
                   max_duration_ms = MAX(max_duration_ms, excluded.max_duration_ms)""",
            [
                (
                    row["bucket_hour"],
                    row["action"],
                    int(row["sample_count"]),
                    int(row["error_count"]),
                    float(row["total_duration_ms"]),
                    float(row["max_duration_ms"]),
                )
                for row in rows
            ],
        )
        await db.commit()
    finally:
        await db.close()


async def get_performance_action_history(hours: int = 24) -> dict:
    hours = min(168, max(1, int(hours)))

    async def read(fresh: bool) -> dict:
        db = await get_db(fresh=fresh)
        try:
            modifier = f"-{hours} hours"
            cursor = await db.execute(
                """SELECT action,
                          SUM(sample_count) AS sample_count,
                          SUM(error_count) AS error_count,
                          SUM(total_duration_ms) AS total_duration_ms,
                          MAX(max_duration_ms) AS max_duration_ms
                   FROM performance_action_hourly
                   WHERE bucket_hour >= strftime('%Y-%m-%d %H:00:00', 'now', ?)
                   GROUP BY action
                   ORDER BY (SUM(total_duration_ms) / MAX(1, SUM(sample_count))) DESC
                   LIMIT 30""",
                (modifier,),
            )
            actions = []
            for row in await cursor.fetchall():
                count = max(0, int(row["sample_count"] or 0))
                total = float(row["total_duration_ms"] or 0)
                actions.append({
                    "action": row["action"],
                    "count": count,
                    "errors": int(row["error_count"] or 0),
                    "average_ms": round(total / count, 1) if count else 0.0,
                    "max_ms": round(float(row["max_duration_ms"] or 0), 1),
                })
            return {"hours": hours, "actions": actions}
        finally:
            await db.close()

    return await _retry_read(read)


async def cleanup_performance_history(retention_days: int = 8) -> int:
    db = await get_db()
    try:
        modifier = f"-{max(1, int(retention_days))} days"
        cursor = await db.execute(
            "DELETE FROM performance_action_hourly WHERE bucket_hour < datetime('now', ?)",
            (modifier,),
        )
        await db.commit()
        return max(0, int(cursor.rowcount)) if cursor.rowcount != -1 else 0
    finally:
        await db.close()


async def get_webhook_autoscale_settings() -> dict:
    async def read(fresh: bool) -> dict:
        db = await get_db(fresh=fresh)
        try:
            cursor = await db.execute(
                "SELECT * FROM webhook_autoscale_settings WHERE id = 1"
            )
            row = await cursor.fetchone()
            return dict(row) if row else {
                "mode": "auto",
                "observe_only": 1,
                "min_workers": 6,
                "max_workers": 20,
                "manual_workers": 8,
            }
        finally:
            await db.close()

    return await _retry_read(read)


async def update_webhook_autoscale_settings(
    *,
    mode: str,
    observe_only: bool,
    min_workers: int,
    max_workers: int,
    manual_workers: int,
) -> dict:
    normalized_mode = str(mode).lower()
    if normalized_mode not in {"auto", "manual", "off"}:
        raise ValueError("mode must be auto, manual, or off")
    minimum = max(1, int(min_workers))
    maximum = max(minimum, int(max_workers))
    manual = min(maximum, max(minimum, int(manual_workers)))
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO webhook_autoscale_settings
               (id, mode, observe_only, min_workers, max_workers, manual_workers, updated_at)
               VALUES (1, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
               ON CONFLICT(id) DO UPDATE SET
                   mode = excluded.mode,
                   observe_only = excluded.observe_only,
                   min_workers = excluded.min_workers,
                   max_workers = excluded.max_workers,
                   manual_workers = excluded.manual_workers,
                   updated_at = CURRENT_TIMESTAMP""",
            (normalized_mode, int(bool(observe_only)), minimum, maximum, manual),
        )
        await db.commit()
    finally:
        await db.close()
    return await get_webhook_autoscale_settings()


async def save_webhook_autoscale_decision(decision: dict) -> None:
    metrics = decision.get("metrics") if isinstance(decision.get("metrics"), dict) else {}
    # Persist only the bounded fields needed to explain a decision. The live
    # endpoint remains the source for full high-frequency metrics.
    compact_metrics = {
        "workers": metrics.get("workers") or {},
        "queue": metrics.get("queue") or {},
        "traffic": metrics.get("traffic") or {},
        "database": metrics.get("database") or {},
        "external_apis": metrics.get("external_apis") or {},
        "event_loop": metrics.get("event_loop") or {},
        "memory": metrics.get("memory") or {},
    }
    db = await get_db()
    try:
        await db.execute(
            """INSERT INTO webhook_autoscale_decisions
               (state, bottleneck, workers_before, workers_after,
                proposed_workers, reason, observe_only,
                next_analysis_seconds, metrics_json)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                str(decision.get("state") or "CALM")[:20],
                str(decision.get("bottleneck") or "healthy")[:40],
                max(0, int(decision.get("workers_before") or 0)),
                max(0, int(decision.get("workers_after") or 0)),
                max(0, int(decision.get("proposed_workers") or 0)),
                str(decision.get("reason") or "")[:500],
                int(bool(decision.get("observe_only"))),
                max(1, int(decision.get("next_analysis_seconds") or 60)),
                json.dumps(compact_metrics, ensure_ascii=True, separators=(",", ":")),
            ),
        )
        await db.commit()
    finally:
        await db.close()


async def list_webhook_autoscale_decisions(limit: int = 30) -> list[dict]:
    bounded_limit = min(100, max(1, int(limit)))

    async def read(fresh: bool) -> list[dict]:
        db = await get_db(fresh=fresh)
        try:
            cursor = await db.execute(
                """SELECT id, state, bottleneck, workers_before, workers_after,
                          proposed_workers, reason, observe_only,
                          next_analysis_seconds, created_at
                   FROM webhook_autoscale_decisions
                   ORDER BY id DESC LIMIT ?""",
                (bounded_limit,),
            )
            return [dict(row) for row in await cursor.fetchall()]
        finally:
            await db.close()

    return await _retry_read(read)


async def get_recent_webhook_autoscale_decision(max_age_seconds: int = 300) -> dict | None:
    age = max(30, int(max_age_seconds))

    async def read(fresh: bool) -> dict | None:
        db = await get_db(fresh=fresh)
        try:
            cursor = await db.execute(
                """SELECT * FROM webhook_autoscale_decisions
                   WHERE created_at >= datetime('now', ?)
                   ORDER BY id DESC LIMIT 1""",
                (f"-{age} seconds",),
            )
            row = await cursor.fetchone()
            return dict(row) if row else None
        finally:
            await db.close()

    return await _retry_read(read)
