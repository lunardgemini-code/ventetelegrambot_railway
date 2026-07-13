"""
Support / ticket handlers with full multi-language (i18n) support.

Uses a ConversationHandler with state WAITING_TICKET_MSG = 210.
"""

import logging

from telegram import Update
from telegram.ext import (
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from database.models import get_user_lang
from utils.keyboards import support_menu_keyboard
from utils.locales import t
from utils.telegram import safe_edit_message_text

logger = logging.getLogger(__name__)

# ── Conversation state ──
WAITING_TICKET_MSG = 210


# ──────────────────────────────────────────────
#  Support menu
# ──────────────────────────────────────────────

async def support_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'menu_support' callback — show support sub-menu."""
    telegram_id = update.effective_user.id
    lang = await get_user_lang(telegram_id)

    if update.callback_query:
        query = update.callback_query
        await query.answer()
        await safe_edit_message_text(query, 
            t("support_title", lang),
            parse_mode="HTML",
            reply_markup=support_menu_keyboard(lang),
        )
    else:
        # Called from reply keyboard text "💬 Support" or equivalent translation
        await update.message.reply_text(
            t("support_title", lang),
            parse_mode="HTML",
            reply_markup=support_menu_keyboard(lang),
        )


async def support_menu_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Wrapper for reply keyboard '💬 Support' button."""
    await support_menu(update, context)


# ──────────────────────────────────────────────
#  New ticket flow
# ──────────────────────────────────────────────

async def new_ticket_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'new_ticket' callback — redirect to support menu."""
    await support_menu(update, context)
    return ConversationHandler.END



async def show_my_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'my_tickets' callback — redirect to support menu."""
    await support_menu(update, context)


async def show_ticket_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'ticket:{id}' callback — redirect to support menu."""
    await support_menu(update, context)


# ──────────────────────────────────────────────
#  Fallback
# ──────────────────────────────────────────────

async def _support_start_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fallback: end conversation and redirect to /start."""
    from handlers.start import start_command
    await start_command(update, context)
    return ConversationHandler.END


# ──────────────────────────────────────────────
#  ConversationHandler factory
# ──────────────────────────────────────────────

def get_support_conversation_handler() -> ConversationHandler:
    """Build and return the support ConversationHandler."""
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(new_ticket_start, pattern=r"^new_ticket$"),
        ],
        states={},
        fallbacks=[
            CallbackQueryHandler(support_menu, pattern=r"^menu_support$"),
            CommandHandler("start", _support_start_fallback),
        ],
        per_message=False,
        allow_reentry=True,
        name="support_conversation",
    )
