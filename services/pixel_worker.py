"""Background submission and reconciliation for Pixel activation tasks.

The worker is intentionally small: it only runs when Pixel is enabled, batches
provider status lookups, and never repeats an ambiguous ``/submit`` request.
"""

from __future__ import annotations

import asyncio
import logging
import os
from urllib.parse import urlparse

from config import PIXEL_RECONCILE_SECONDS
from database.models import (
    apply_pixel_provider_task,
    claim_due_pixel_reconciliations,
    claim_pixel_submissions,
    claim_pixel_task_notification,
    expire_stale_pixel_drafts,
    get_pixel_activation_settings,
    get_pixel_task_submission_payload,
    get_user_lang,
    mark_pixel_submission_pending,
    mark_pixel_submission_unknown,
    release_pixel_submission_claim,
    purge_expired_pixel_credentials,
    refund_pixel_activation_task,
    release_pixel_reconciliation_claims,
)
from services.pixel_api import (
    PixelAPIError,
    get_pixel_balance,
    is_pixel_configured,
    query_pixel_tasks,
    submit_pixel_task,
)
from utils.locales import t


logger = logging.getLogger(__name__)
_PURGE_EVERY_SECONDS = 6 * 60 * 60


def pixel_public_base_url() -> str:
    """Derive an HTTPS public base without accidentally nesting /webhook."""
    value = (
        os.environ.get("PUBLIC_BASE_URL")
        or os.environ.get("RAILWAY_PUBLIC_DOMAIN")
        or os.environ.get("WEBHOOK_URL")
        or ""
    ).strip().rstrip("/")
    if not value:
        return ""
    if not value.startswith(("http://", "https://")):
        value = f"https://{value}"
    parsed = urlparse(value)
    if not parsed.scheme or not parsed.netloc:
        return ""
    path = parsed.path.rstrip("/")
    if path in {"/webhook", "/webhooks"}:
        path = ""
    return f"{parsed.scheme}://{parsed.netloc}{path}".rstrip("/")


def pixel_callback_url(public_id: str, callback_token: str) -> str:
    base = pixel_public_base_url()
    if not base:
        return ""
    return f"{base}/api/pixel/callback/{public_id}/{callback_token}"


async def _notify_final_task(bot, task: dict) -> None:
    claimed = await claim_pixel_task_notification(str(task["public_id"]))
    if not claimed:
        return
    try:
        lang = await get_user_lang(int(claimed["user_telegram_id"])) or "fr"
        status = str(claimed.get("status") or "")
        if status == "SUCCESS":
            message = t("pixel_task_success", lang).format(
                task_id=claimed["public_id"],
                result_link=claimed.get("result_link") or "-",
            )
        elif status == "REFUNDED":
            message = t("pixel_task_refunded", lang).format(
                task_id=claimed["public_id"],
                error=claimed.get("error_message") or "-",
            )
        else:
            message = t("pixel_task_manual_review", lang).format(
                task_id=claimed["public_id"],
            )
        await bot.send_message(
            chat_id=int(claimed["user_telegram_id"]),
            text=message,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.warning("Could not notify Pixel task %s: %s", task.get("public_id"), exc)


async def submit_pixel_activation_task(public_id: str, bot) -> None:
    """Submit an already-reserved task once, then persist its provider ID."""
    payload = await get_pixel_task_submission_payload(public_id)
    if not payload:
        return
    settings = await get_pixel_activation_settings()
    minimum_points = float(settings.get("min_supplier_points") or 0)
    if minimum_points > 0:
        try:
            balance = await get_pixel_balance()
        except PixelAPIError as exc:
            # No POST was attempted, so retrying later is safe.
            await release_pixel_submission_claim(public_id)
            logger.warning("Pixel balance preflight deferred task %s: %s", public_id, exc)
            return
        if float(balance.get("balance_points") or 0) < minimum_points:
            task = await refund_pixel_activation_task(
                public_id,
                error_message="Pixel supplier balance is below the configured safety minimum",
                supplier_status="supplier_low_balance",
            )
            if task:
                await _notify_final_task(bot, task)
            return
    callback_url = pixel_callback_url(payload["public_id"], payload["callback_token"])
    if not callback_url:
        task = await refund_pixel_activation_task(
            public_id,
            error_message="Pixel callback URL is not configured",
            supplier_status="configuration_error",
        )
        if task:
            await _notify_final_task(bot, task)
        return

    try:
        response = await submit_pixel_task(
            email=payload["email"],
            password=payload["password"],
            twofa_secret=payload["twofa_secret"],
            task_mode=payload["task_mode"],
            channel=payload["channel"],
            callback_url=callback_url,
        )
    except PixelAPIError as exc:
        if exc.outcome_unknown:
            await mark_pixel_submission_unknown(public_id, str(exc))
            task = {"public_id": public_id}
            await _notify_final_task(bot, task)
            return
        task = await refund_pixel_activation_task(
            public_id,
            error_message=str(exc),
            supplier_status=f"http_{exc.status_code}" if exc.status_code else "submit_error",
        )
        if task:
            await _notify_final_task(bot, task)
        return
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        # Treat unexpected client errors conservatively. We have not received
        # a provider task ID, so a retry must never create a second activation.
        await mark_pixel_submission_unknown(public_id, f"Unexpected submission error: {exc}")
        await _notify_final_task(bot, {"public_id": public_id})
        logger.exception("Pixel submission failed with an unexpected error")
        return

    task = await mark_pixel_submission_pending(public_id, response["task"])
    if not task:
        logger.warning("Pixel provider task submitted but local task %s disappeared", public_id)
        return
    provider_status = str(response["task"].get("status") or "pending").lower()
    if provider_status in {"success", "failed", "error", "cancelled", "canceled", "rejected"}:
        final = await apply_pixel_provider_task(public_id, response["task"])
        if final and final.get("status") in {"SUCCESS", "REFUNDED"}:
            await _notify_final_task(bot, final)


async def process_pixel_activation_cycle(bot, *, busy: bool = False) -> dict[str, int]:
    """Perform a bounded cycle. It is callable from a webhook callback too."""
    stats = {"submitted": 0, "reconciled": 0, "purged": 0}
    if busy or not is_pixel_configured():
        return stats
    settings = await get_pixel_activation_settings()
    if not settings.get("is_enabled"):
        return stats

    for claim in await claim_pixel_submissions(limit=3):
        await submit_pixel_activation_task(str(claim["public_id"]), bot)
        stats["submitted"] += 1

    claimed = await claim_due_pixel_reconciliations(limit=12)
    if not claimed:
        return stats
    task_ids = [int(task["supplier_task_id"]) for task in claimed]
    public_by_supplier_id = {
        int(task["supplier_task_id"]): str(task["public_id"]) for task in claimed
    }
    try:
        provider_tasks = await query_pixel_tasks(task_ids)
    except PixelAPIError as exc:
        await release_pixel_reconciliation_claims(
            [str(task["public_id"]) for task in claimed],
            retry_after_seconds=180 if exc.retryable else 600,
        )
        logger.warning("Pixel reconciliation failed: %s", exc)
        return stats

    missing_public_ids: list[str] = []
    for task_id, public_id in public_by_supplier_id.items():
        provider_task = provider_tasks.get(task_id)
        if not provider_task:
            missing_public_ids.append(public_id)
            continue
        updated = await apply_pixel_provider_task(public_id, provider_task)
        if updated and updated.get("status") in {"SUCCESS", "REFUNDED"}:
            await _notify_final_task(bot, updated)
        stats["reconciled"] += 1
    if missing_public_ids:
        await release_pixel_reconciliation_claims(missing_public_ids, retry_after_seconds=300)
    return stats


async def pixel_activation_worker(bot, *, busy_check=None) -> None:
    """Low-priority loop; it yields completely when live webhook traffic is busy."""
    next_purge_at = 0.0
    while True:
        try:
            busy = bool(busy_check and busy_check())
            await process_pixel_activation_cycle(bot, busy=busy)
            now = asyncio.get_running_loop().time()
            if now >= next_purge_at:
                next_purge_at = now + _PURGE_EVERY_SECONDS
                await purge_expired_pixel_credentials()
                await expire_stale_pixel_drafts()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Pixel activation worker cycle failed: %s", exc)
        await asyncio.sleep(PIXEL_RECONCILE_SECONDS)
