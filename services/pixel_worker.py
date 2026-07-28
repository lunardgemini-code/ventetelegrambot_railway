"""Pixel Gemini Activation Background Worker.

Periodically queries pending/processing tasks on https://pixel.wxie.de/api/v1/query
and notifies Telegram users/admins instantly upon status completion (success / failure).
"""

import asyncio
import logging
import os
from typing import Optional

from telegram import Bot
from database.db import get_db
from services.supplier_registry import _provider_config
from services.supplier_multi_api import _request
from utils.helpers import escape_html

logger = logging.getLogger(__name__)


async def _get_pixel_db():
    """Get DB connection ensuring parent directory exists."""
    db_path = os.environ.get("DB_PATH", "bot_data.db")
    if db_path and db_path != ":memory:":
        try:
            parent = os.path.dirname(os.path.abspath(db_path))
            if parent:
                os.makedirs(parent, exist_ok=True)
        except Exception:
            pass
    try:
        return await get_db()
    except Exception:
        os.environ["DB_PATH"] = ":memory:"
        return await get_db()


async def init_pixel_tasks_table():
    """Ensure the pixel_tasks table exists in the database."""
    try:
        db = await _get_pixel_db()
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS pixel_tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id INTEGER UNIQUE NOT NULL,
                user_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                task_mode TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                result_link TEXT DEFAULT '',
                error_message TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        await db.execute(
            "CREATE INDEX IF NOT EXISTS idx_pixel_tasks_status ON pixel_tasks(status)"
        )
        await db.commit()
    except Exception as exc:
        logger.debug("init_pixel_tasks_table: %s", exc)


async def record_pixel_task(
    task_id: int,
    user_id: int,
    email: str,
    task_mode: str,
):
    """Record a newly submitted Pixel task for status tracking."""
    try:
        await init_pixel_tasks_table()
        db = await _get_pixel_db()
        await db.execute(
            """
            INSERT OR REPLACE INTO pixel_tasks (task_id, user_id, email, task_mode, status, updated_at)
            VALUES (?, ?, ?, ?, 'pending', CURRENT_TIMESTAMP)
            """,
            (int(task_id), int(user_id), str(email), str(task_mode)),
        )
        await db.commit()
    except Exception as exc:
        logger.error("Failed to record pixel task #%s: %s", task_id, exc, exc_info=True)


async def get_active_pixel_tasks() -> list[dict]:
    """Fetch all pixel tasks with pending or processing status."""
    try:
        await init_pixel_tasks_table()
        db = await _get_pixel_db()
        cursor = await db.execute(
            """
            SELECT id, task_id, user_id, email, task_mode, status, result_link, error_message
            FROM pixel_tasks
            WHERE status IN ('pending', 'processing')
            ORDER BY id ASC
            """
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": row[0],
                "task_id": row[1],
                "user_id": row[2],
                "email": row[3],
                "task_mode": row[4],
                "status": row[5],
                "result_link": row[6] or "",
                "error_message": row[7] or "",
            }
            for row in rows
        ]
    except Exception as exc:
        logger.error("Failed to fetch active pixel tasks: %s", exc)
        return []


async def update_pixel_task_db(
    task_id: int,
    status: str,
    result_link: str = "",
    error_message: str = "",
):
    """Update task status, result link, and error message in DB."""
    try:
        db = await _get_pixel_db()
        await db.execute(
            """
            UPDATE pixel_tasks
            SET status = ?, result_link = ?, error_message = ?, updated_at = CURRENT_TIMESTAMP
            WHERE task_id = ?
            """,
            (str(status), str(result_link), str(error_message), int(task_id)),
        )
        await db.commit()
    except Exception as exc:
        logger.error("Failed to update pixel task #%s in DB: %s", task_id, exc)


async def pixel_task_worker(bot: Optional[Bot] = None, interval_seconds: float = 30.0):
    """Worker loop that periodically queries active Pixel tasks and notifies users."""
    logger.info("Starting Pixel Gemini task background worker (every %ds)", interval_seconds)
    try:
        await init_pixel_tasks_table()
    except Exception as e:
        logger.warning("Could not init pixel_tasks table: %s", e)

    while True:
        try:
            active_tasks = await get_active_pixel_tasks()
            if active_tasks:
                provider = _provider_config("pixel")
                for task in active_tasks:
                    tid = task["task_id"]
                    try:
                        resp = await _request(
                            provider,
                            "POST",
                            "/api/v1/query",
                            json={"task_id": int(tid)},
                        )

                        task_info = resp.get("task") or {}
                        if not task_info and isinstance(resp.get("tasks"), list) and resp["tasks"]:
                            task_info = resp["tasks"][0].get("task") or {}

                        new_status = str(task_info.get("status") or "pending").lower()
                        result_link = str(task_info.get("result_link") or "")
                        error_msg = str(task_info.get("error_message") or "")
                        old_status = task["status"]

                        if new_status != old_status or result_link != task["result_link"] or error_msg != task["error_message"]:
                            await update_pixel_task_db(tid, new_status, result_link, error_msg)

                            # Send Telegram Notification if completed or failed
                            if bot and task["user_id"] and new_status in ("success", "failed", "error"):
                                user_id = task["user_id"]
                                email = task["email"]
                                mode = task["task_mode"]

                                if new_status == "success":
                                    msg_text = (
                                        f"🎉 <b>Votre Activation Pixel Gemini est Terminée !</b>\n\n"
                                        f"⚡ <b>Tâche :</b> <code>#{tid}</code>\n"
                                        f"📧 <b>Compte :</b> <code>{escape_html(email)}</code>\n"
                                        f"⚙️ <b>Mode :</b> <code>{escape_html(mode)}</code>\n\n"
                                        f"🔗 <b>Lien d'activation :</b>\n"
                                        f"<code>{escape_html(result_link)}</code>\n\n"
                                        f"<i>Merci pour votre confiance !</i>"
                                    )
                                else:
                                    msg_text = (
                                        f"❌ <b>Échec de l'Activation Pixel Gemini</b>\n\n"
                                        f"⚡ <b>Tâche :</b> <code>#{tid}</code>\n"
                                        f"📧 <b>Compte :</b> <code>{escape_html(email)}</code>\n"
                                        f"⚠️ <b>Raison :</b> <code>{escape_html(error_msg or 'Erreur lors du traitement')}</code>"
                                    )

                                try:
                                    await bot.send_message(chat_id=user_id, text=msg_text, parse_mode="HTML")
                                    logger.info("Sent Pixel completion notification to user %s for task #%s", user_id, tid)
                                except Exception as send_err:
                                    logger.warning("Could not send Telegram message for task #%s: %s", tid, send_err)
                    except Exception as task_err:
                        logger.warning("Error querying Pixel task #%s: %s", tid, task_err)

        except asyncio.CancelledError:
            logger.info("Pixel task worker cancelled")
            break
        except Exception as exc:
            logger.error("Error in pixel_task_worker loop: %s", exc, exc_info=True)

        await asyncio.sleep(interval_seconds)

async def get_user_pixel_tasks(user_id: int) -> list[dict]:
    """Fetch recent/active pixel tasks for a specific user."""
    try:
        await init_pixel_tasks_table()
        db = await _get_pixel_db()
        cursor = await db.execute(
            """
            SELECT id, task_id, user_id, email, task_mode, status, result_link, error_message, created_at, updated_at
            FROM pixel_tasks
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT 10
            """,
            (int(user_id),)
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": row[0],
                "task_id": row[1],
                "user_id": row[2],
                "email": row[3],
                "task_mode": row[4],
                "status": row[5],
                "result_link": row[6] or "",
                "error_message": row[7] or "",
                "created_at": row[8],
                "updated_at": row[9],
            }
            for row in rows
        ]
    except Exception as exc:
        logger.error("Failed to fetch user pixel tasks for %s: %s", user_id, exc)
        return []
