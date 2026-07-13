"""Telegram callbacks for the lightweight virtual match prediction game."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from database.games import (
    GameError,
    claim_daily_coins,
    get_game_leaderboard,
    get_game_match,
    get_game_wallet,
    list_open_game_matches,
    list_user_game_bets,
    place_game_bet,
)
from database.models import get_user_lang
from utils.helpers import escape_html
from utils.keyboards import (
    game_confirm_keyboard,
    game_home_keyboard,
    game_match_keyboard,
    game_simple_back_keyboard,
    game_stake_keyboard,
)
from utils.locales import t
from utils.telegram import safe_edit_message_text


logger = logging.getLogger(__name__)


async def _answer(query, text: str | None = None, *, alert: bool = False) -> None:
    try:
        await query.answer(text=text, show_alert=alert)
    except BadRequest as exc:
        logger.debug("Game callback answer expired: %s", exc)


def _format_time(value) -> str:
    text = str(value or "").strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        try:
            parsed = datetime.strptime(text, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return str(value or "-")
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")


def _outcome_label(match: dict, outcome: str, lang: str) -> str:
    if outcome == "home":
        return str(match.get("home_name") or "Home")
    if outcome == "away":
        return str(match.get("away_name") or "Away")
    return t("game_draw_button", lang)


async def _render_game_home(query, user_id: int, lang: str, notice: str = "") -> None:
    wallet = await get_game_wallet(user_id)
    matches = await list_open_game_matches()
    lines = [
        t("game_title", lang),
        "",
        t("game_balance", lang).format(balance=wallet["balance"]),
        t("game_daily_available" if wallet["claim_available"] else "game_daily_claimed", lang),
        t("game_disclaimer", lang),
    ]
    if notice:
        lines.extend(["", notice])
    lines.extend(["", t("game_matches_heading", lang)])
    if not matches:
        lines.append(t("game_no_matches", lang))
    await safe_edit_message_text(
        query,
        "\n".join(lines),
        parse_mode="HTML",
        reply_markup=game_home_keyboard(matches, wallet, lang),
    )


async def show_game_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await _answer(query)
    user_id = update.effective_user.id
    lang = await get_user_lang(user_id)
    try:
        await _render_game_home(query, user_id, lang)
    except Exception as exc:
        logger.error("show_game_menu: %s", exc, exc_info=True)
        await safe_edit_message_text(query, t("game_error", lang))


async def claim_game_coins(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await _answer(query)
    user_id = update.effective_user.id
    lang = await get_user_lang(user_id)
    try:
        result = await claim_daily_coins(user_id)
        key = "game_claim_success" if result.get("claimed") else "game_claim_already"
        notice = t(key, lang).format(amount=result.get("daily_claim", 300))
        await _render_game_home(query, user_id, lang, notice)
    except Exception as exc:
        logger.error("claim_game_coins: %s", exc, exc_info=True)
        await safe_edit_message_text(
            query,
            t("game_error", lang),
            reply_markup=game_simple_back_keyboard("menu_game", lang),
        )


async def show_game_match(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await _answer(query)
    lang = await get_user_lang(update.effective_user.id)
    try:
        match_id = int(query.data.split(":", 1)[1])
        match = await get_game_match(match_id)
        if not match or match.get("status") != "OPEN":
            await _answer(query, t("game_closed", lang), alert=True)
            await _render_game_home(query, update.effective_user.id, lang)
            return
        market_key = "game_market_qualified" if match["market_type"] == "qualified" else "game_market_regulation"
        text = (
            f"⚽ <b>{escape_html(match['home_name'])} - {escape_html(match['away_name'])}</b>\n"
            f"{escape_html(match.get('competition_name') or '')}\n\n"
            f"🎯 <b>{escape_html(t(market_key, lang))}</b>\n"
            f"{escape_html(t('game_starts', lang).format(date=_format_time(match['utc_date'])))}\n"
            f"{escape_html(t('game_locks', lang).format(date=_format_time(match['lock_at'])))}\n"
            f"{t('game_total_pool', lang).format(pool=match['total_pool'])}\n\n"
            f"{escape_html(t('game_choose', lang))}"
        )
        await safe_edit_message_text(
            query,
            text,
            parse_mode="HTML",
            reply_markup=game_match_keyboard(match, lang),
        )
    except Exception as exc:
        logger.error("show_game_match: %s", exc, exc_info=True)
        await safe_edit_message_text(query, t("game_error", lang), reply_markup=game_simple_back_keyboard("menu_game", lang))


async def choose_game_outcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await _answer(query)
    user_id = update.effective_user.id
    lang = await get_user_lang(user_id)
    try:
        _, match_id_text, outcome = query.data.split(":", 2)
        match = await get_game_match(int(match_id_text))
        wallet = await get_game_wallet(user_id)
        if not match or match.get("status") != "OPEN":
            raise GameError("closed", t("game_closed", lang))
        label = _outcome_label(match, outcome, lang)
        text = (
            f"⚽ <b>{escape_html(match['home_name'])} - {escape_html(match['away_name'])}</b>\n\n"
            f"{t('game_choose_stake', lang).format(outcome=escape_html(label))}\n"
            f"{t('game_balance_line', lang).format(balance=wallet['balance'])}\n"
            f"{t('game_stake_limits', lang).format(min=match['min_stake'], max=match['max_stake'])}"
        )
        await safe_edit_message_text(
            query,
            text,
            parse_mode="HTML",
            reply_markup=game_stake_keyboard(match, outcome, wallet["balance"], lang),
        )
    except GameError as exc:
        await safe_edit_message_text(
            query,
            escape_html(str(exc)),
            parse_mode="HTML",
            reply_markup=game_simple_back_keyboard("menu_game", lang),
        )
    except Exception as exc:
        logger.error("choose_game_outcome: %s", exc, exc_info=True)
        await safe_edit_message_text(query, t("game_error", lang), reply_markup=game_simple_back_keyboard("menu_game", lang))


async def choose_game_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await _answer(query)
    lang = await get_user_lang(update.effective_user.id)
    try:
        _, match_id_text, outcome, amount_text = query.data.split(":", 3)
        match = await get_game_match(int(match_id_text))
        if not match or match.get("status") != "OPEN":
            raise GameError("closed", t("game_closed", lang))
        amount = int(amount_text)
        label = _outcome_label(match, outcome, lang)
        text = (
            f"⚽ <b>{escape_html(match['home_name'])} - {escape_html(match['away_name'])}</b>\n\n"
            f"{t('game_selected', lang).format(outcome=escape_html(label))}\n"
            f"{t('game_confirm_prompt', lang).format(amount=amount, outcome=escape_html(label))}"
        )
        await safe_edit_message_text(
            query,
            text,
            parse_mode="HTML",
            reply_markup=game_confirm_keyboard(int(match_id_text), outcome, amount, lang),
        )
    except GameError as exc:
        await safe_edit_message_text(
            query,
            escape_html(str(exc)),
            parse_mode="HTML",
            reply_markup=game_simple_back_keyboard("menu_game", lang),
        )
    except Exception as exc:
        logger.error("choose_game_amount: %s", exc, exc_info=True)
        await safe_edit_message_text(query, t("game_error", lang), reply_markup=game_simple_back_keyboard("menu_game", lang))


async def confirm_game_bet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await _answer(query)
    user_id = update.effective_user.id
    lang = await get_user_lang(user_id)
    try:
        _, match_id_text, outcome, amount_text = query.data.split(":", 3)
        match = await get_game_match(int(match_id_text))
        if not match:
            raise GameError("closed", t("game_closed", lang))
        result = await place_game_bet(user_id, int(match_id_text), outcome, int(amount_text))
        label = _outcome_label(match, outcome, lang)
        text = t("game_bet_success", lang).format(
            amount=result["stake"],
            outcome=escape_html(label),
            balance=result["balance"],
        )
        await safe_edit_message_text(
            query,
            text,
            parse_mode="HTML",
            reply_markup=game_simple_back_keyboard("menu_game", lang),
        )
    except GameError as exc:
        key = {
            "insufficient_balance": "game_insufficient",
            "closed": "game_closed",
            "already_bet": "game_already_bet",
        }.get(exc.code)
        await safe_edit_message_text(
            query,
            t(key, lang) if key else escape_html(str(exc)),
            parse_mode="HTML",
            reply_markup=game_simple_back_keyboard("menu_game", lang),
        )
    except Exception as exc:
        logger.error("confirm_game_bet: %s", exc, exc_info=True)
        await safe_edit_message_text(query, t("game_error", lang), reply_markup=game_simple_back_keyboard("menu_game", lang))


async def show_my_game_bets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await _answer(query)
    user_id = update.effective_user.id
    lang = await get_user_lang(user_id)
    try:
        bets = await list_user_game_bets(user_id)
        lines = [t("game_my_bets_title", lang), ""]
        if not bets:
            lines.append(t("game_no_bets", lang))
        for bet in bets:
            label = _outcome_label(bet, str(bet["outcome"]), lang)
            status_icon = {"ACTIVE": "⏳", "WON": "✅", "LOST": "❌", "REFUNDED": "↩️"}.get(str(bet["status"]), "•")
            stake_label = t("game_coin_amount", lang).format(amount=int(bet["stake"]))
            payout = (
                f" → {t('game_coin_amount', lang).format(amount=int(bet['payout']))}"
                if int(bet.get("payout") or 0) else ""
            )
            lines.append(
                f"{status_icon} <b>{escape_html(bet['home_name'])} - {escape_html(bet['away_name'])}</b>\n"
                f"{escape_html(label)} · {escape_html(stake_label)}{escape_html(payout)}"
            )
        await safe_edit_message_text(
            query,
            "\n\n".join(lines),
            parse_mode="HTML",
            reply_markup=game_simple_back_keyboard("menu_game", lang),
        )
    except Exception as exc:
        logger.error("show_my_game_bets: %s", exc, exc_info=True)
        await safe_edit_message_text(query, t("game_error", lang), reply_markup=game_simple_back_keyboard("menu_game", lang))


async def show_game_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await _answer(query)
    lang = await get_user_lang(update.effective_user.id)
    try:
        leaders = await get_game_leaderboard()
        lines = [t("game_leaderboard_title", lang), ""]
        if not leaders:
            lines.append(t("game_no_leaderboard", lang))
        medals = ["🥇", "🥈", "🥉"]
        for index, leader in enumerate(leaders):
            name = leader.get("first_name") or leader.get("username") or str(leader["user_telegram_id"])
            prefix = medals[index] if index < len(medals) else f"{index + 1}."
            amount = escape_html(t("game_coin_amount", lang).format(amount=int(leader["balance"])))
            lines.append(f"{prefix} {escape_html(str(name))} — <b>{amount}</b>")
        await safe_edit_message_text(
            query,
            "\n".join(lines),
            parse_mode="HTML",
            reply_markup=game_simple_back_keyboard("menu_game", lang),
        )
    except Exception as exc:
        logger.error("show_game_leaderboard: %s", exc, exc_info=True)
        await safe_edit_message_text(query, t("game_error", lang), reply_markup=game_simple_back_keyboard("menu_game", lang))
