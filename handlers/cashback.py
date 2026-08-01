"""Customer cashback balance and atomic wallet claims."""

import logging

from telegram import Update
from telegram.ext import ContextTypes

from database.models import (
    get_loyalty_summary,
    get_user_lang,
    redeem_loyalty_to_wallet,
)
from utils.keyboards import cashback_keyboard
from utils.locales import t
from utils.telegram import safe_edit_message_text

logger = logging.getLogger(__name__)


def _money(value: float) -> str:
    return f"{float(value):.4f}".rstrip("0").rstrip(".") or "0"


def _cashback_text(summary: dict, lang: str) -> str:
    lines = [
        t("cashback_title", lang),
        "",
        t("cashback_balance", lang).format(points=summary["balance_points"]),
        t("cashback_value", lang).format(amount=_money(summary["redeemable_usd"])),
        "",
        t("cashback_earn_rule", lang).format(
            earn_points=summary["earn_points"],
            earn_spend=_money(summary["earn_spend_usd"]),
        ),
        t("cashback_claim_rule", lang).format(
            minimum=summary["redeem_min_points"],
            block_points=summary["redeem_block_points"],
            block_usd=_money(summary["redeem_block_usd"]),
        ),
        "",
    ]
    if not summary["enabled"]:
        lines.append(t("cashback_disabled", lang))
    elif summary["redeemable_points"] > 0:
        lines.append(t("cashback_ready", lang))
    else:
        remaining = max(
            0, summary["redeem_min_points"] - summary["balance_points"]
        )
        lines.append(t("cashback_progress", lang).format(remaining=remaining))
    return "\n".join(lines)


async def show_cashback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    lang = await get_user_lang(user_id)
    try:
        summary = await get_loyalty_summary(user_id)
        await safe_edit_message_text(
            query,
            _cashback_text(summary, lang),
            parse_mode="HTML",
            reply_markup=cashback_keyboard(
                lang,
                can_claim=bool(summary["enabled"] and summary["redeemable_points"]),
            ),
        )
    except Exception as exc:
        logger.error("show_cashback failed for %s: %s", user_id, exc, exc_info=True)
        await safe_edit_message_text(query, t("cashback_claim_error", lang))


async def claim_cashback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    lang = await get_user_lang(user_id)
    try:
        result = await redeem_loyalty_to_wallet(user_id)
        summary = await get_loyalty_summary(user_id)
        text = t("cashback_claimed", lang).format(
            points=result["redeemed_points"],
            amount=_money(result["wallet_amount_usd"]),
            wallet=_money(result["wallet_balance"]),
        )
        await safe_edit_message_text(
            query,
            f"{text}\n\n{_cashback_text(summary, lang)}",
            parse_mode="HTML",
            reply_markup=cashback_keyboard(lang, can_claim=False),
        )
    except ValueError as exc:
        summary = await get_loyalty_summary(user_id)
        await safe_edit_message_text(
            query,
            _cashback_text(summary, lang),
            parse_mode="HTML",
            reply_markup=cashback_keyboard(
                lang,
                can_claim=bool(summary["enabled"] and summary["redeemable_points"]),
            ),
        )
        logger.info("Cashback claim rejected for %s: %s", user_id, exc)
    except Exception as exc:
        logger.error("claim_cashback failed for %s: %s", user_id, exc, exc_info=True)
        await safe_edit_message_text(
            query,
            t("cashback_claim_error", lang),
            reply_markup=cashback_keyboard(lang),
        )
