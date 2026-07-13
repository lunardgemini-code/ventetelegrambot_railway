"""Durable jobs that resume after a Railway process restart."""

from __future__ import annotations

import asyncio
import logging
import secrets
import time
from typing import Any

from telegram import InlineKeyboardMarkup

from database.jobs import (
    claim_next_background_job,
    cleanup_background_jobs,
    complete_background_job,
    create_background_job,
    fail_background_job,
    get_background_job,
    get_broadcast_recipient_window,
    requeue_stale_background_jobs,
    update_background_job_progress,
)
from services.broadcast import execute_broadcast


logger = logging.getLogger(__name__)
_JOB_POLL_SECONDS = 2.0
_STALE_JOB_SECONDS = 180


def _serialize_markup(reply_markup) -> dict | None:
    if reply_markup is None:
        return None
    try:
        return reply_markup.to_dict()
    except Exception:
        logger.warning("Could not serialize broadcast reply markup", exc_info=True)
        return None


def _deserialize_markup(payload: dict, bot) -> InlineKeyboardMarkup | None:
    raw = payload.get("reply_markup")
    if not isinstance(raw, dict):
        return None
    try:
        return InlineKeyboardMarkup.de_json(raw, bot)
    except Exception:
        logger.warning("Could not restore broadcast reply markup", exc_info=True)
        return None


def public_background_job(job: dict | None) -> dict | None:
    if not job:
        return None
    return {
        "job_id": job.get("id"),
        "job_type": job.get("job_type"),
        "status": job.get("status"),
        "sent": int(job.get("progress_done") or 0),
        "failed": int(job.get("progress_failed") or 0),
        "total": int(job.get("progress_total") or 0),
        "attempts": int(job.get("attempts") or 0),
        "error": job.get("error"),
        "created_at": job.get("created_at"),
        "updated_at": job.get("updated_at"),
        "completed_at": job.get("completed_at"),
    }


async def get_public_background_job(job_id: str) -> dict | None:
    return public_background_job(await get_background_job(job_id))


async def enqueue_broadcast_job(
    text: str,
    *,
    photo: str | None = None,
    reply_markup=None,
    source: str = "dashboard",
    status_chat_id: int | None = None,
    status_message_id: int | None = None,
) -> dict:
    window = await get_broadcast_recipient_window()
    payload = {
        "text": str(text or ""),
        "photo": str(photo or "").strip() or None,
        "reply_markup": _serialize_markup(reply_markup),
        "source": str(source or "dashboard")[:40],
        "max_user_id": int(window["max_user_id"]),
        "status_chat_id": int(status_chat_id) if status_chat_id is not None else None,
        "status_message_id": int(status_message_id) if status_message_id is not None else None,
    }
    job = await create_background_job(
        secrets.token_urlsafe(12),
        "broadcast",
        payload,
        max_attempts=3,
        progress_total=int(window["total"]),
    )
    return public_background_job(job) or {}


async def enqueue_restock_notification(product_id: int) -> dict:
    job = await create_background_job(
        secrets.token_urlsafe(12),
        "restock_notification",
        {"product_id": int(product_id)},
        max_attempts=3,
    )
    return public_background_job(job) or {}


async def _edit_admin_status(bot, payload: dict, text: str, *, final: bool = False) -> None:
    chat_id = payload.get("status_chat_id")
    message_id = payload.get("status_message_id")
    if chat_id is None or message_id is None:
        return
    try:
        kwargs: dict[str, Any] = {
            "chat_id": int(chat_id),
            "message_id": int(message_id),
            "text": text,
        }
        if final:
            from utils.keyboards import admin_menu_keyboard

            kwargs["parse_mode"] = "HTML"
            kwargs["reply_markup"] = admin_menu_keyboard()
        await bot.edit_message_text(**kwargs)
    except Exception:
        logger.debug("Could not update persistent broadcast status message", exc_info=True)


async def _run_broadcast_job(job: dict, bot) -> None:
    payload = job.get("payload") or {}
    job_id = str(job["id"])
    last_status_edit = 0.0

    async def checkpoint(sent: int, failed: int, total: int, cursor_value: int) -> None:
        nonlocal last_status_edit
        await update_background_job_progress(
            job_id,
            done=sent,
            failed=failed,
            total=total,
            cursor_value=cursor_value,
        )
        now = time.monotonic()
        if now - last_status_edit >= 2.0 or sent + failed >= total:
            last_status_edit = now
            await _edit_admin_status(
                bot,
                payload,
                f"Broadcast en cours...\n\nEnvoye : {sent}/{total}\nEchoue : {failed}",
            )

    sent, failed, total = await execute_broadcast(
        bot,
        str(payload.get("text") or ""),
        photo=payload.get("photo"),
        reply_markup=_deserialize_markup(payload, bot),
        checkpoint=checkpoint,
        start_offset=int(job.get("cursor_value") or 0),
        max_user_id=int(payload.get("max_user_id") or 0),
        initial_sent=int(job.get("progress_done") or 0),
        initial_failed=int(job.get("progress_failed") or 0),
    )
    await complete_background_job(
        job_id,
        done=sent,
        failed=failed,
        total=total,
        cursor_value=total,
    )
    await _edit_admin_status(
        bot,
        payload,
        f"<b>Broadcast termine</b>\n\nEnvoye : {sent}/{total}\nEchoue : {failed}",
        final=True,
    )


async def _run_restock_job(job: dict, bot) -> None:
    from handlers.products import notify_restock_subscribers

    product_id = int((job.get("payload") or {}).get("product_id") or 0)
    if product_id <= 0:
        raise ValueError("Invalid restock product ID")
    sent = await notify_restock_subscribers(bot, product_id)
    await complete_background_job(
        str(job["id"]),
        done=sent,
        failed=0,
        total=sent,
        cursor_value=sent,
    )


async def _process_job(job: dict, bot) -> None:
    job_type = str(job.get("job_type") or "")
    if job_type == "broadcast":
        await _run_broadcast_job(job, bot)
        return
    if job_type == "restock_notification":
        await _run_restock_job(job, bot)
        return
    raise ValueError(f"Unsupported background job type: {job_type}")


async def background_job_worker(bot) -> None:
    """Claim and execute persisted jobs until application shutdown."""
    last_maintenance = 0.0
    while True:
        try:
            now = time.monotonic()
            if now - last_maintenance >= 60.0:
                recovered = await requeue_stale_background_jobs(_STALE_JOB_SECONDS)
                if recovered:
                    logger.warning("Recovered %d interrupted background job(s)", recovered)
                await cleanup_background_jobs(retention_days=7)
                last_maintenance = now

            job = await claim_next_background_job()
            if not job:
                await asyncio.sleep(_JOB_POLL_SECONDS)
                continue
            try:
                await _process_job(job, bot)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                status = await fail_background_job(
                    str(job["id"]),
                    str(exc),
                    retry_delay_seconds=min(120, 10 * max(1, int(job.get("attempts") or 1))),
                )
                logger.error(
                    "Background job %s (%s) failed; status=%s: %s",
                    job.get("id"),
                    job.get("job_type"),
                    status,
                    exc,
                    exc_info=True,
                )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Background job worker cycle failed: %s", exc)
            await asyncio.sleep(5.0)
