"""
VenteBot — Main entry point.

Wires all handlers together and starts the bot using python-telegram-bot v21+ async API.
Includes a FastAPI REST API with health-check for Railway deployment.
"""

import warnings
from telegram.warnings import PTBUserWarning
warnings.filterwarnings("ignore", category=PTBUserWarning)

import hmac
import logging
import os
import threading
from fastapi import FastAPI, Header, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import uvicorn
import httpx

from telegram import Update
from telegram.ext import (
    Application,
    ApplicationHandlerStop,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    TypeHandler,
    filters,
)

from config import BOT_TOKEN, ADMIN_IDS
from database import init_db
from handlers.admin import get_admin_conversation_handler
from handlers.history import show_history, show_order_detail
from handlers.payment import (
    get_payment_conversation_handler,
    initiate_purchase,
    download_txt_delivery,
)
from handlers.products import (
    refresh_products,
    show_product_detail,
    show_products_list,
)
from handlers.profile import show_profile, show_referrals
from handlers.start import change_language, main_menu_callback, set_language, start_command, callback_check_sub
from handlers.support import (
    get_support_conversation_handler,
    show_my_tickets,
    show_ticket_detail,
    support_menu,
    support_menu_text,
)
from handlers.wallet import wallet_conversation_handler, wallet_menu, wallet_history, wallet_noop

from utils.helpers import escape_html

# ── Logging ──
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────
#  Secure REST API Server (FastAPI + uvicorn)
# ──────────────────────────────────────────────

api = FastAPI(title="VenteBot Admin API", version="1.0.0")

# Enable CORS for browser access — restrict origins in production
_cors_origins = os.environ.get("CORS_ORIGINS", "*").split(",")
api.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in _cors_origins],
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["X-API-Key", "Content-Type"],
    expose_headers=[],
)

# ── Serve dashboard static files directly from Railway ──
import pathlib
_dashboard_dir = pathlib.Path(__file__).parent / "dashboard"
if _dashboard_dir.is_dir():
    @api.get("/dashboard")
    @api.get("/dashboard/")
    async def serve_dashboard_index():
        return FileResponse(str(_dashboard_dir / "index.html"), media_type="text/html")
    api.mount("/dashboard", StaticFiles(directory=str(_dashboard_dir)), name="dashboard")

ADMIN_API_KEY = os.environ.get("ADMIN_API_KEY", "")
if not ADMIN_API_KEY:
    import secrets
    ADMIN_API_KEY = secrets.token_urlsafe(32)
    logger.critical("⚠️ ADMIN_API_KEY not set! Generated temporary key. Set ADMIN_API_KEY env var in production! (Key starts with %s)", ADMIN_API_KEY[:4])

async def verify_api_key(x_api_key: str = Header(None)):
    """Dependency to check the custom X-API-Key header using constant-time comparison."""
    if not x_api_key or not hmac.compare_digest(x_api_key, ADMIN_API_KEY):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Key"
        )
    return x_api_key


@api.get("/health")
async def health_check():
    """Anonymous endpoint for Railway health check."""
    return {"status": "ok", "bot": "running"}

@api.get("/api/finance", dependencies=[Depends(verify_api_key)])
async def api_get_finance(method: str = None):
    from database.models import get_stats, get_setting
    try:
        stats_1 = await get_stats(days=1)
        stats_7 = await get_stats(days=7)
        stats_30 = await get_stats(days=30)
        
        balance = 0.0
        if method and method != "all":
            # Get balance for specific method
            balance_str = await get_setting(f"finance_bot_balance_{method}")
            balance = float(balance_str) if balance_str else 0.0
        else:
            # Sum all balances
            methods = ["binance", "bep20", "trc20", "wallet"]
            for m in methods:
                b_str = await get_setting(f"finance_bot_balance_{m}")
                if b_str:
                    balance += float(b_str)
        
        return {
            "daily_revenue": stats_1.get("total_revenue", 0),
            "weekly_revenue": stats_7.get("total_revenue", 0),
            "monthly_revenue": stats_30.get("total_revenue", 0),
            "bot_balance": balance,
            "sales_binance_30d": stats_30.get("sales_binance", 0),
            "sales_bep20_30d": stats_30.get("sales_bep20", 0),
            "sales_trc20_30d": stats_30.get("sales_trc20", 0),
            "sales_wallet_30d": stats_30.get("sales_wallet", 0),
            "topup_count_30d": stats_30.get("topup_count", 0),
            "topup_revenue_30d": stats_30.get("topup_revenue", 0)
        }
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@api.post("/api/finance/adjust", dependencies=[Depends(verify_api_key)])
async def api_adjust_finance(data: dict):
    from database.models import get_setting, set_setting
    try:
        amount = float(data.get("amount", 0))
        method = data.get("method")
        
        if not method or method == "all":
            raise HTTPException(status_code=400, detail="Veuillez sélectionner une méthode spécifique (Binance, BEP20, etc.) pour ajuster le solde.")
            
        setting_key = f"finance_bot_balance_{method}"
        balance_str = await get_setting(setting_key)
        balance = float(balance_str) if balance_str else 0.0
        
        new_balance = balance + amount
        if new_balance < 0:
            new_balance = 0.0
            
        await set_setting(setting_key, str(new_balance))
        return {"status": "success", "new_balance": new_balance}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/stats", dependencies=[Depends(verify_api_key)])
async def api_get_stats():
    from database.models import get_stats, get_all_users, get_all_products, get_all_stock_counts
    try:
        stats_30 = await get_stats(days=30)
        users = await get_all_users()
        products = await get_all_products()
        stock_counts = await get_all_stock_counts()

        stock_summary = [{
            "id": p["id"],
            "name": p["name"],
            "emoji": p["emoji"],
            "stock": stock_counts.get(p["id"], 0)
        } for p in products]

        return {
            "total_users": len(users),
            "total_orders": stats_30.get("total_orders", 0),
            "completed_orders": stats_30.get("completed_orders", 0),
            "total_revenue": stats_30.get("total_revenue", 0),
            "stock_summary": stock_summary
        }
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/products", dependencies=[Depends(verify_api_key)])
async def api_get_products():
    from database.models import get_all_products, get_all_stock_counts
    try:
        products = await get_all_products()
        stock_counts = await get_all_stock_counts()
        result = []
        for p in products:
            item = dict(p)
            item["stock"] = stock_counts.get(p["id"], 0)
            result.append(item)
        return result
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/products", dependencies=[Depends(verify_api_key)])
async def api_create_product(data: dict):
    from database.models import add_product, get_categories, add_category
    try:
        if "price_usd" not in data or "name" not in data:
            raise HTTPException(status_code=400, detail="Missing required fields: name, price_usd")
            
        # Auto-create a default category if none exists (categories hidden from UI)
        cats = await get_categories()
        if not cats:
            cat_id = await add_category(name="Produits", emoji="📦", description="Catégorie par défaut")
        else:
            cat_id = cats[0]["id"]

        price = float(data["price_usd"])
        if price <= 0:
            raise HTTPException(status_code=400, detail="Price must be positive")
        warranty = int(data.get("warranty_days", 0))
        if warranty < 0:
            raise HTTPException(status_code=400, detail="Warranty days cannot be negative")

        prod_id = await add_product(
            category_id=cat_id,
            name=data["name"],
            description=data.get("description", ""),
            price_usd=price,
            warranty_days=warranty,
            emoji=data.get("emoji", "📦"),
            custom_emoji_id=data.get("custom_emoji_id"),
            image_url=data.get("image_url"),
            binance_account_id=data.get("binance_account_id")
        )
        return {"id": prod_id, "status": "created"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/products/{product_id}/tiers", dependencies=[Depends(verify_api_key)])
async def api_get_product_tiers(product_id: int):
    from database.models import get_price_tiers
    try:
        tiers = await get_price_tiers(product_id)
        return tiers
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.put("/api/products/{product_id}/tiers", dependencies=[Depends(verify_api_key)])
async def api_set_product_tiers(product_id: int, data: dict):
    from database.models import set_price_tiers
    try:
        tiers = data.get("tiers", [])
        await set_price_tiers(product_id, tiers)
        return {"status": "updated", "count": len(tiers)}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")



@api.post("/api/products/update-sort", dependencies=[Depends(verify_api_key)])
async def api_reorder_products(request: Request):
    from database.db import get_db
    from database.models import clear_products_cache
    try:
        data = await request.json()
        orders = data.get("orders", [])
        if not orders:
            return {"status": "ok"}
            
        db = await get_db()
        for item in orders:
            prod_id = item.get("id")
            sort_order = item.get("sort_order")
            if prod_id is not None and sort_order is not None:
                await db.execute("UPDATE products SET sort_order = ? WHERE id = ?", (sort_order, prod_id))
        await db.commit()
        clear_products_cache()
        return {"status": "reordered"}
    except Exception as exc:
        logger.error("API error reorder products: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@api.put("/api/products/{product_id}", dependencies=[Depends(verify_api_key)])
async def api_update_product(product_id: int, data: dict):
    from database.models import update_product
    try:
        allowed = {"name", "price_usd", "emoji", "custom_emoji_id", "warranty_days", "description", "is_active", "binance_account_id", "image_url"}
        updates = {k: v for k, v in data.items() if k in allowed}
        if not updates:
            raise HTTPException(status_code=400, detail="No valid fields to update")
        if "price_usd" in updates:
            updates["price_usd"] = float(updates["price_usd"])
        if "warranty_days" in updates:
            updates["warranty_days"] = int(updates["warranty_days"])
        await update_product(product_id, **updates)
        return {"status": "updated"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.delete("/api/products/{product_id}", dependencies=[Depends(verify_api_key)])
async def api_delete_product(product_id: int):
    from database.models import delete_product
    try:
        await delete_product(product_id)
        return {"status": "deleted"}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ── Binance Accounts Endpoints ──

@api.get("/api/binance-accounts", dependencies=[Depends(verify_api_key)])
async def api_get_binance_accounts():
    from database.models import get_binance_accounts
    try:
        accounts = await get_binance_accounts()
        return accounts
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@api.post("/api/binance-accounts", dependencies=[Depends(verify_api_key)])
async def api_create_binance_account(data: dict):
    from database.models import add_binance_account
    try:
        if "label" not in data or "uid" not in data:
            raise HTTPException(status_code=400, detail="label and uid are required")
        acc_id = await add_binance_account(
            label=data["label"],
            uid=data["uid"],
            api_key=data.get("api_key", ""),
            api_secret=data.get("api_secret", ""),
            is_default=data.get("is_default", 0)
        )
        return {"id": acc_id, "status": "created"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@api.put("/api/binance-accounts/{account_id}", dependencies=[Depends(verify_api_key)])
async def api_update_binance_account(account_id: int, data: dict):
    from database.models import update_binance_account
    try:
        allowed_keys = {"label", "uid", "api_key", "api_secret", "is_default"}
        safe_data = {k: v for k, v in data.items() if k in allowed_keys}
        await update_binance_account(account_id, **safe_data)
        return {"status": "updated"}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@api.delete("/api/binance-accounts/{account_id}", dependencies=[Depends(verify_api_key)])
async def api_delete_binance_account(account_id: int):
    from database.models import delete_binance_account
    try:
        await delete_binance_account(account_id)
        return {"status": "deleted"}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/categories", dependencies=[Depends(verify_api_key)])
async def api_get_categories():
    from database.models import get_categories
    try:
        categories = await get_categories()
        return [dict(c) for c in categories]
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/categories", dependencies=[Depends(verify_api_key)])
async def api_create_category(data: dict):
    from database.models import add_category
    try:
        cat_id = await add_category(
            name=data["name"],
            emoji=data.get("emoji", "📂"),
            description=data.get("description", "")
        )
        return {"id": cat_id, "status": "created"}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.delete("/api/categories/{category_id}", dependencies=[Depends(verify_api_key)])
async def api_delete_category(category_id: int):
    from database.models import delete_category
    try:
        await delete_category(category_id)
        return {"status": "deleted"}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/orders", dependencies=[Depends(verify_api_key)])
async def api_get_orders():
    from database.models import get_pending_orders
    try:
        orders = await get_pending_orders()
        return [dict(o) for o in orders]
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/orders/{order_id}/confirm", dependencies=[Depends(verify_api_key)])
async def api_confirm_order(order_id: int):
    from database.models import get_order, update_order_status, get_product, get_user_lang
    from services.delivery import deliver_order
    try:
        order = await get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
            
        await update_order_status(order_id, "COMPLETED")
        delivered = await deliver_order(order_id, order.get("product_id"))
        
        if delivered:
            product = await get_product(order.get("product_id"))
            warranty_days = product.get("warranty_days", 0) if product else 0
            
            # Notify user
            try:
                from utils.locales import t
                user_lang = await get_user_lang(order["user_telegram_id"])
                accounts_text = "\n".join(f"🔑 <code>{escape_html(item['account_data'])}</code>" for item in delivered)
                
                global tg_app
                if tg_app:
                    await tg_app.bot.send_message(
                        chat_id=order["user_telegram_id"],
                        text=f"{t('payment_confirmed', user_lang)}\n\n"
                             f"{t('your_account', user_lang)}\n"
                             f"{accounts_text}\n\n"
                             f"{t('warranty_lbl', user_lang).format(days=warranty_days)}\n"
                             f"{t('save_info', user_lang)}\n\n"
                             f"{t('thank_you', user_lang)}",
                        parse_mode="HTML"
                    )
            except Exception as notify_exc:
                logger.warning("Failed to notify user via API: %s", notify_exc)
                
            return {"status": "confirmed_and_delivered"}
        else:
            return {"status": "confirmed_but_no_stock"}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/tickets", dependencies=[Depends(verify_api_key)])
async def api_get_tickets():
    from database.models import get_open_tickets
    try:
        tickets = await get_open_tickets()
        return [dict(t_item) for t_item in tickets]
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/tickets/{ticket_id}/reply", dependencies=[Depends(verify_api_key)])
async def api_reply_ticket(ticket_id: int, data: dict):
    from database.models import get_ticket, reply_ticket, get_user_lang
    try:
        ticket = await get_ticket(ticket_id)
        if not ticket:
            raise HTTPException(status_code=404, detail="Ticket not found")
            
        reply_text = data["reply_text"]
        await reply_ticket(ticket_id, reply_text)
        
        # Notify user
        try:
            from utils.locales import t
            user_lang = await get_user_lang(ticket["user_telegram_id"])
            global tg_app
            if tg_app:
                await tg_app.bot.send_message(
                    chat_id=ticket["user_telegram_id"],
                    text=f"{t('ticket_replied', user_lang).format(id=ticket_id)}\n\n{escape_html(reply_text)}",
                    parse_mode="HTML"
                )
        except Exception as notify_exc:
            logger.warning("Failed to notify user reply via API: %s", notify_exc)
            
        return {"status": "replied"}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/products/{product_id}/stock", dependencies=[Depends(verify_api_key)])
async def api_get_product_stock(product_id: int):
    from database.models import get_stock_items_for_product
    try:
        items = await get_stock_items_for_product(product_id)
        return items
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/products/{product_id}/stock", dependencies=[Depends(verify_api_key)])
async def api_add_product_stock(product_id: int, data: dict):
    from database.models import add_stock_items
    try:
        items = data.get("items", [])
        if not items:
            raise HTTPException(status_code=400, detail="No items provided")
        count = await add_stock_items(product_id, items)
        
        broadcast = data.get("broadcast_restock", False)
        if broadcast:
            from database.models import get_product
            product = await get_product(product_id)
            if product:
                from utils.helpers import format_price
                broadcast_text = (
                    "🔔 <b>Product Restocked!</b>\n\n"
                    f"{product['emoji']} <b>{product['name']}</b> is back in stock!\n"
                    f"💰 Price: <b>{format_price(product['price_usd'])}</b>\n\n"
                    f"{product.get('description', '')}"
                )
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                markup = InlineKeyboardMarkup([[
                    InlineKeyboardButton("🛒 Buy now", callback_data=f"buy:{product_id}")
                ]])
                from handlers.admin import _execute_broadcast
                global tg_app
                if tg_app and tg_app.bot:
                    # Run in background tasks to not block API response
                    import asyncio
                    asyncio.create_task(_execute_broadcast(tg_app.bot, broadcast_text, reply_markup=markup))

        return {"status": "added", "count": count}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.delete("/api/stock/{stock_id}", dependencies=[Depends(verify_api_key)])
async def api_delete_stock_item(stock_id: int):
    from database.models import delete_stock_item
    try:
        await delete_stock_item(stock_id)
        return {"status": "deleted"}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


from fastapi import Query as _Q

@api.get("/api/orders/all", dependencies=[Depends(verify_api_key)])
async def api_get_all_orders(order_status: str = _Q(None, alias="status"), limit: int = 50, offset: int = 0):
    from database.models import get_all_orders_filtered, get_all_topups_filtered
    try:
        # Validate & bound inputs
        VALID_STATUSES = {"PENDING", "COMPLETED", "CANCELLED", "AWAITING_PAYMENT", "TOPUP"}
        if order_status and order_status.upper() not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail=f"Invalid status. Valid: {', '.join(VALID_STATUSES)}")
        limit = max(1, min(limit, 200))  # Cap between 1-200
        offset = max(0, offset)

        # TOPUP filter returns wallet top-up transactions instead of orders
        if order_status and order_status.upper() == "TOPUP":
            topups, total = await get_all_topups_filtered(limit=limit, offset=offset)
            return {"orders": topups, "total": total}

        orders, total = await get_all_orders_filtered(status=order_status, limit=limit, offset=offset)
        return {"orders": orders, "total": total}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/orders/{order_id}/items", dependencies=[Depends(verify_api_key)])
async def api_get_order_items(order_id: int):
    from database.models import get_stock_items_for_order, get_order
    try:
        order = await get_order(order_id)
        if not order:
            raise HTTPException(status_code=404, detail="Order not found")
        items = await get_stock_items_for_order(order_id)
        return {"order_id": order_id, "status": order["status"], "items": items}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/orders/{order_id}/cancel", dependencies=[Depends(verify_api_key)])
async def api_cancel_order(order_id: int):
    from database.models import update_order_status
    try:
        await update_order_status(order_id, "CANCELLED")
        return {"status": "cancelled"}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/orders/cleanup", dependencies=[Depends(verify_api_key)])
async def api_cleanup_stale_orders():
    """Auto-cancel all PENDING/AWAITING_PAYMENT orders older than 5 minutes and notify users."""
    from database.db import get_db
    try:
        db = await get_db()
        try:
            cursor = await db.execute(
                """SELECT id, user_telegram_id FROM orders 
                   WHERE status IN ('PENDING', 'AWAITING_PAYMENT')
                     AND created_at <= datetime('now', '-5 minutes')"""
            )
            stale_orders = await cursor.fetchall()
            count = 0
            
            if stale_orders:
                stale_ids = [str(o["id"]) for o in stale_orders]
                placeholders = ",".join(["?"] * len(stale_ids))
                await db.execute(
                    f"UPDATE orders SET status = 'CANCELLED' WHERE id IN ({placeholders})",
                    stale_ids
                )
                await db.commit()
                count = len(stale_ids)
                
                from database.models import get_user_lang
                from utils.locales import t
                
                if tg_app and tg_app.bot:
                    for order in stale_orders:
                        try:
                            lang = await get_user_lang(order["user_telegram_id"])
                            msg = t("order_expired_notification", lang).format(order_id=order["id"])
                            await tg_app.bot.send_message(
                                chat_id=order["user_telegram_id"],
                                text=msg,
                                parse_mode="HTML"
                            )
                        except Exception as e:
                            logger.error(f"Failed to notify user {order['user_telegram_id']} of expired order {order['id']}: {e}")
                            
            return {"status": "ok", "cancelled": count}
        finally:
            await db.close()
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/stats/daily", dependencies=[Depends(verify_api_key)])
async def api_get_daily_stats(days: int = 30):
    from database.models import get_daily_stats
    try:
        days = max(1, min(days, 365))  # Cap between 1-365
        data = await get_daily_stats(days=days)
        return data
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/broadcast", dependencies=[Depends(verify_api_key)])
async def api_broadcast(data: dict):
    from database.models import get_all_users
    try:
        message = data.get("message", "").strip()
        photo_url = data.get("photo_url", "").strip()
        btn_type = data.get("btn_type", "none")
        btn_prod_id = data.get("btn_prod_id")
        btn_text = data.get("btn_text", "").strip()
        btn_url = data.get("btn_url", "").strip()

        if not message and not photo_url:
            raise HTTPException(status_code=400, detail="Empty message and photo_url")

        users = await get_all_users()
        sent = 0
        failed = 0

        # Construct reply markup if button requested
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        reply_markup = None
        if btn_type == "buy" and btn_prod_id:
            reply_markup = InlineKeyboardMarkup([[
                InlineKeyboardButton("🛒 Acheter maintenant", callback_data=f"buy:{btn_prod_id}")
            ]])
        elif btn_type == "url" and btn_text and btn_url:
            if not btn_url.startswith(("http://", "https://")):
                btn_url = "https://" + btn_url
            reply_markup = InlineKeyboardMarkup([[
                InlineKeyboardButton(btn_text, url=btn_url)
            ]])

        if tg_app and tg_app.bot:
            for user in users:
                if user.get("is_banned"):
                    continue
                try:
                    if photo_url:
                        await tg_app.bot.send_photo(
                            chat_id=user["telegram_id"],
                            photo=photo_url,
                            caption=message or None,
                            parse_mode="HTML" if message else None,
                            reply_markup=reply_markup
                        )
                    else:
                        await tg_app.bot.send_message(
                            chat_id=user["telegram_id"],
                            text=message,
                            parse_mode="HTML",
                            reply_markup=reply_markup
                        )
                    sent += 1
                except Exception as e:
                    logger.debug("Failed sending broadcast to %s: %s", user["telegram_id"], e)
                    failed += 1
        else:
            raise HTTPException(status_code=503, detail="Bot not initialized")

        return {"sent": sent, "failed": failed, "total": len(users)}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/promos", dependencies=[Depends(verify_api_key)])
async def api_get_promos():
    from database.models import get_all_promos
    try:
        return await get_all_promos()
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/promos", dependencies=[Depends(verify_api_key)])
async def api_create_promo(data: dict):
    from database.models import create_promo
    try:
        discount_type = data.get("discount_type", "percent")
        if discount_type not in ("percent", "fixed"):
            raise HTTPException(status_code=400, detail="discount_type must be 'percent' or 'fixed'")
        discount_value = float(data["discount_value"])
        if discount_value <= 0:
            raise HTTPException(status_code=400, detail="discount_value must be positive")
        if discount_type == "percent" and discount_value > 100:
            raise HTTPException(status_code=400, detail="Percent discount cannot exceed 100")

        promo_id = await create_promo(
            code=data["code"],
            discount_type=discount_type,
            discount_value=discount_value,
            max_uses=int(data.get("max_uses", 0)),
            max_uses_per_user=int(data.get("max_uses_per_user", 0)),
            applicable_product_ids=data.get("applicable_product_ids"),
            max_qty_per_order=int(data.get("max_qty_per_order", 0)),
            expires_at=data.get("expires_at"),
        )
        return {"id": promo_id, "status": "created"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.delete("/api/promos/{promo_id}", dependencies=[Depends(verify_api_key)])
async def api_delete_promo(promo_id: int):
    from database.models import delete_promo
    try:
        await delete_promo(promo_id)
        return {"status": "deleted"}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/users", dependencies=[Depends(verify_api_key)])
async def api_get_users(limit: int = 20, offset: int = 0, search: str = ""):
    from database.models import get_users_paginated
    try:
        users, total = await get_users_paginated(limit, offset, search)
        return {"users": users, "total": total}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/users/{telegram_id}/ban", dependencies=[Depends(verify_api_key)])
async def api_ban_user(telegram_id: int, notify: bool = False):
    from database.models import ban_user, get_user_lang
    try:
        await ban_user(telegram_id)
        if notify:
            lang = "fr"
            try:
                lang = await get_user_lang(telegram_id)
            except Exception:
                pass
            
            ban_msg = {
                "fr": "🚫 Vous avez été banni du bot.",
                "en": "🚫 You have been banned from the bot.",
                "ar": "🚫 لقد تم حظرك من البوت."
            }
            text = ban_msg.get(lang, ban_msg["fr"])
            
            global tg_app
            if tg_app and tg_app.bot:
                try:
                    await tg_app.bot.send_message(chat_id=telegram_id, text=text, parse_mode="HTML")
                except Exception as e:
                    logger.error("Failed to send ban notification to user %s: %s", telegram_id, e)
                    
        return {"status": "banned"}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/users/{telegram_id}/unban", dependencies=[Depends(verify_api_key)])
async def api_unban_user(telegram_id: int):
    from database.models import unban_user
    try:
        await unban_user(telegram_id)
        return {"status": "unbanned"}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/users/{telegram_id}/wallet/topup", dependencies=[Depends(verify_api_key)])
async def api_wallet_topup(telegram_id: int, data: dict):
    from database.models import topup_wallet
    try:
        amount = float(data.get("amount", 0))
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be > 0")
        new_balance = await topup_wallet(telegram_id, amount, "Admin credit")
        return {"status": "credited", "new_balance": new_balance}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/users/{telegram_id}/wallet/deduct", dependencies=[Depends(verify_api_key)])
async def api_wallet_deduct(telegram_id: int, data: dict):
    from database.models import deduct_wallet
    try:
        amount = float(data.get("amount", 0))
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Amount must be > 0")
        new_balance = await deduct_wallet(telegram_id, amount, "Admin debit")
        return {"status": "debited", "new_balance": new_balance}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/wallet/history", dependencies=[Depends(verify_api_key)])
async def api_wallet_history(limit: int = 50, offset: int = 0, tx_type: str = None):
    """Return all wallet transactions across all users (admin view)."""
    from database.models import get_all_wallet_transactions
    try:
        limit = max(1, min(limit, 200))
        offset = max(0, offset)
        txs, total = await get_all_wallet_transactions(limit=limit, offset=offset, tx_type=tx_type or None)
        return {"transactions": txs, "total": total}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/api/settings/payment", dependencies=[Depends(verify_api_key)])
async def api_get_payment_settings():
    from database.models import get_setting
    try:
        bep20_address = await get_setting("bep20_address") or ""
        trc20_address = await get_setting("trc20_address") or ""
        return {"bep20_address": bep20_address, "trc20_address": trc20_address}
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.post("/api/settings/payment", dependencies=[Depends(verify_api_key)])
async def api_set_payment_settings(data: dict):
    from database.models import set_setting
    try:
        bep20_address = data.get("bep20_address", "").strip()
        trc20_address = data.get("trc20_address", "").strip()
        
        if bep20_address and (not bep20_address.startswith("0x") or len(bep20_address) != 42):
            raise HTTPException(status_code=400, detail="Invalid BEP20 address. Must start with 0x and be 42 characters.")
            
        if trc20_address and (not trc20_address.startswith("T") or len(trc20_address) != 34):
            raise HTTPException(status_code=400, detail="Invalid TRC20 address. Must start with T and be 34 characters.")
            
        await set_setting("bep20_address", bep20_address)
        await set_setting("trc20_address", trc20_address)
        return {"status": "saved"}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ── Admin notifications utility ──
async def notify_admins(text: str):
    """Send a notification message to all admin Telegram IDs."""
    if not tg_app or not tg_app.bot:
        return
    for admin_id in ADMIN_IDS:
        try:
            await tg_app.bot.send_message(chat_id=admin_id, text=text, parse_mode="HTML")
        except Exception:
            pass


# ──────────────────────────────────────────────
#  Vente DZ — Public API routes (no auth)
# ──────────────────────────────────────────────

@api.get("/dz/api/products")
async def dz_get_products():
    """Public: list all visible DZ products with stock count, categories, and settings."""
    from database.models import get_visible_dz_products, get_dz_settings, get_categories
    try:
        products = await get_visible_dz_products()
        settings = await get_dz_settings()
        categories = await get_categories()

        usd_to_dzd = float(settings.get("dz_usd_to_dzd", 250))
        profit_per_usd = float(settings.get("dz_profit_per_usd", 100))

        product_list = []
        for p in products:
            price_usd = float(p["price_usd"])
            price_dzd = int(price_usd * (usd_to_dzd + profit_per_usd))
            product_list.append({
                "id": p["id"],
                "name": p["name"],
                "description": p.get("description", ""),
                "dz_description": p.get("dz_description", ""),
                "price_usd": price_usd,
                "price_dzd": price_dzd,
                "image_url": p.get("dz_image_url") or p.get("image_url") or "",
                "emoji": p.get("emoji", "📦"),
                "category_id": p.get("category_id"),
                "stock_count": p.get("stock_count", 0),
                "warranty_days": p.get("warranty_days", 0),
            })

        return {
            "products": product_list,
            "categories": [{"id": c["id"], "name": c["name"], "emoji": c.get("emoji", "📂")} for c in categories],
            "settings": {
                "usd_to_dzd": usd_to_dzd,
                "profit_per_usd": profit_per_usd,
            }
        }
    except Exception as exc:
        logger.error("DZ API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@api.get("/dz/api/products/{product_id}")
async def dz_get_product(product_id: int):
    """Public: get single product detail with stock count."""
    from database.models import get_visible_dz_product, get_dz_settings
    try:
        product = await get_visible_dz_product(product_id)
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        settings = await get_dz_settings()
        usd_to_dzd = float(settings.get("dz_usd_to_dzd", 250))
        profit_per_usd = float(settings.get("dz_profit_per_usd", 100))
        price_usd = float(product["price_usd"])
        price_dzd = int(price_usd * (usd_to_dzd + profit_per_usd))

        return {
            "id": product["id"],
            "name": product["name"],
            "description": product.get("description", ""),
            "dz_description": product.get("dz_description", ""),
            "price_usd": price_usd,
            "price_dzd": price_dzd,
            "image_url": product.get("dz_image_url") or product.get("image_url") or "",
            "emoji": product.get("emoji", "📦"),
            "category_id": product.get("category_id"),
            "stock_count": product.get("stock_count", 0),
            "warranty_days": product.get("warranty_days", 0),
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("DZ API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
tg_app = None


# ──────────────────────────────────────────────
#  Post-init hook: database setup
# ──────────────────────────────────────────────

async def post_init(application: Application) -> None:
    """Called after the Application has been initialised — set up the database."""
    await init_db()
    logger.info("✅ Database initialized")

    # Auto-cancel stale PENDING/AWAITING_PAYMENT orders older than 5 minutes
    # This handles orders that were left hanging after a bot restart
    try:
        from database.db import get_db
        db = await get_db()
        try:
            cursor = await db.execute(
                """UPDATE orders SET status = 'CANCELLED'
                   WHERE status IN ('PENDING', 'AWAITING_PAYMENT')
                     AND created_at <= datetime('now', '-5 minutes')"""
            )
            await db.commit()
            count = cursor.rowcount if cursor.rowcount > 0 else 0
            if count:
                logger.info("🧹 Auto-cancelled %d stale PENDING/AWAITING_PAYMENT orders on startup", count)
        finally:
            await db.close()
    except Exception as exc:
        logger.warning("Could not clean stale orders: %s", exc)


# ──────────────────────────────────────────────
#  Webhook endpoint for Telegram updates
# ──────────────────────────────────────────────

WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

from starlette.requests import Request as StarletteRequest
from fastapi import BackgroundTasks

@api.post("/webhook")
async def telegram_webhook(request: StarletteRequest, background_tasks: BackgroundTasks):
    """Receive Telegram updates via webhook — zero polling, zero wasted CPU."""
    try:
        # Verify webhook secret if configured
        if WEBHOOK_SECRET:
            token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
            if not hmac.compare_digest(token, WEBHOOK_SECRET):
                logger.warning("⚠️ Webhook secret mismatch — rejecting update")
                raise HTTPException(status_code=403, detail="Forbidden")

        data = await request.json()
        logger.info("📨 Webhook received update: %s", data.get("update_id", "?"))
        if tg_app:
            update = Update.de_json(data, tg_app.bot)
            background_tasks.add_task(tg_app.process_update, update)
        else:
            logger.error("❌ tg_app is None — cannot process update")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("❌ Webhook error: %s", exc, exc_info=True)
        return {"ok": False}


async def get_emoji_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only command to get the HTML code of any custom emoji sent with the message."""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Access denied.")
        return

    message = update.message
    if not message:
        return

    custom_emojis = [
        e for e in (message.entities or []) if e.type == "custom_emoji"
    ]
    
    if not custom_emojis:
        await message.reply_text(
            "Veuillez envoyer cette commande suivie d'un emoji premium.\n"
            "Exemple: `/getemoji` 🔥 (avec un emoji premium animé)",
            parse_mode="Markdown"
        )
        return

    response = "Voici le(s) code(s) HTML pour vos emojis custom :\n\n"
    for entity in custom_emojis:
        emoji_char = message.text[entity.offset:entity.offset+entity.length]
        emoji_id = entity.custom_emoji_id
        html_code = f"<code>&lt;tg-emoji emoji-id=\"{emoji_id}\"&gt;{emoji_char}&lt;/tg-emoji&gt;</code>"
        response += f"Emoji {emoji_char} (ID: <code>{emoji_id}</code>) :\n{html_code}\n\n"

    await message.reply_text(response, parse_mode="HTML")


async def run_migrations_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin-only command to manually force run database migrations and print output."""
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("🚫 Access denied.")
        return
        
    try:
        from database.db import get_db
        db = await get_db()
        # count promo usages table
        c = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='promo_code_usages'")
        table_exists = await c.fetchone() is not None
        
        c = await db.execute("SELECT * FROM promo_codes ORDER BY id DESC LIMIT 1")
        last_row = await c.fetchone()
        last_promo = dict(last_row) if last_row else None
        
        usage_count = 0
        if last_promo and table_exists:
            c = await db.execute("SELECT COUNT(*) as c FROM promo_code_usages WHERE promo_code_id = ?", (last_promo["id"],))
            res = await c.fetchone()
            usage_count = res["c"] if res else 0

        await update.message.reply_text(
            f"Table usages existe: {table_exists}\n"
            f"Dernier promo max_per_user: {last_promo.get('max_uses_per_user') if last_promo else 'None'}\n"
            f"Usages dans la table: {usage_count}"
        )
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")
    
    await update.message.reply_text("🔄 Starting manual database migrations...")
    
    from database.db import get_db
    logs = []
    
    queries = [
        ("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)", "Table 'settings'"),
        ("CREATE TABLE IF NOT EXISTS used_bep20_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, tx_hash TEXT UNIQUE NOT NULL, order_id INTEGER, user_telegram_id INTEGER, amount REAL, used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)", "Table 'used_bep20_transactions'"),
        ("CREATE TABLE IF NOT EXISTS used_trc20_transactions (id INTEGER PRIMARY KEY AUTOINCREMENT, tx_hash TEXT UNIQUE NOT NULL, order_id INTEGER, user_telegram_id INTEGER, amount REAL, used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)", "Table 'used_trc20_transactions'"),
        ("ALTER TABLE orders ADD COLUMN quantity INTEGER DEFAULT 1", "Column 'orders.quantity'"),
        ("ALTER TABLE orders ADD COLUMN payment_method TEXT DEFAULT 'binance'", "Column 'orders.payment_method'"),
        ("ALTER TABLE orders ADD COLUMN promo_code_id INTEGER", "Column 'orders.promo_code_id'"),
        ("ALTER TABLE orders ADD COLUMN promo_discount REAL DEFAULT 0.0", "Column 'orders.promo_discount'"),
        ("ALTER TABLE users ADD COLUMN referred_by INTEGER", "Column 'users.referred_by'"),
        ("ALTER TABLE users ADD COLUMN referral_earnings REAL DEFAULT 0", "Column 'users.referral_earnings'"),
        ("ALTER TABLE users ADD COLUMN referral_commission_paid REAL DEFAULT 0", "Column 'users.referral_commission_paid'"),
        ("ALTER TABLE categories ADD COLUMN is_deleted INTEGER DEFAULT 0", "Column 'categories.is_deleted'"),
        ("ALTER TABLE products ADD COLUMN is_deleted INTEGER DEFAULT 0", "Column 'products.is_deleted'"),
        ("ALTER TABLE products ADD COLUMN binance_account_id INTEGER DEFAULT NULL", "Column 'products.binance_account_id'"),
        ("ALTER TABLE products ADD COLUMN image_url TEXT DEFAULT NULL", "Column 'products.image_url'"),
        ("ALTER TABLE products ADD COLUMN custom_emoji_id TEXT DEFAULT NULL", "Column 'products.custom_emoji_id'"),
        ("ALTER TABLE products ADD COLUMN sort_order INTEGER DEFAULT 0", "Column 'products.sort_order'"),
        ("CREATE TABLE IF NOT EXISTS binance_accounts (id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT NOT NULL, uid TEXT NOT NULL, api_key TEXT DEFAULT '', api_secret TEXT DEFAULT '', is_default INTEGER DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)", "Table 'binance_accounts'"),
        ("UPDATE orders SET binance_order_id = (SELECT transaction_id FROM used_binance_transactions WHERE used_binance_transactions.order_id = orders.id) WHERE binance_order_id IS NULL AND id IN (SELECT order_id FROM used_binance_transactions WHERE order_id IS NOT NULL)", "Retroactive Binance Pay IDs"),
        ("UPDATE orders SET binance_order_id = (SELECT tx_hash FROM used_bep20_transactions WHERE used_bep20_transactions.order_id = orders.id) WHERE binance_order_id IS NULL AND id IN (SELECT order_id FROM used_bep20_transactions WHERE order_id IS NOT NULL)", "Retroactive BEP20 Tx Hashes"),
        ("UPDATE orders SET binance_order_id = (SELECT tx_hash FROM used_trc20_transactions WHERE used_trc20_transactions.order_id = orders.id) WHERE binance_order_id IS NULL AND id IN (SELECT order_id FROM used_trc20_transactions WHERE order_id IS NOT NULL)", "Retroactive TRC20 Tx Hashes"),
        ("ALTER TABLE promo_codes ADD COLUMN max_uses_per_user INTEGER DEFAULT 0", "Column 'promo_codes.max_uses_per_user'"),
        ("CREATE TABLE IF NOT EXISTS promo_code_usages (id INTEGER PRIMARY KEY AUTOINCREMENT, promo_code_id INTEGER NOT NULL, user_telegram_id INTEGER NOT NULL, usage_count INTEGER DEFAULT 0, last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(promo_code_id, user_telegram_id))", "Table 'promo_code_usages'"),
        ("ALTER TABLE promo_codes ADD COLUMN applicable_product_ids TEXT DEFAULT NULL", "Column 'promo_codes.applicable_product_ids'"),
        ("ALTER TABLE promo_codes ADD COLUMN max_qty_per_order INTEGER DEFAULT 0", "Column 'promo_codes.max_qty_per_order'"),
    ]
    
    for sql, name in queries:
        try:
            mig_db = await get_db()
            await mig_db.execute(sql)
            await mig_db.commit()
            logs.append(f"✅ {name} added/verified.")
        except Exception as e:
            logs.append(f"⚠️ {name} skipped: {e}")
        finally:
            try:
                await mig_db.close()
            except Exception:
                pass
                
    # ── Mises à jour rétroactives des Order IDs Binance (18 chiffres) ──
    # 1. Nettoyage des formats avec slash (ex: 'P_... / 18_chiffres') pour ne garder que la partie à 18 chiffres
    try:
        mig_db = None
        mig_db = await get_db()
        cursor = await mig_db.execute("SELECT id, binance_order_id FROM orders WHERE binance_order_id LIKE '%/%'")
        rows = await cursor.fetchall()
        cleaned_count = 0
        for r in rows:
            parts = [p.strip() for p in r["binance_order_id"].split("/")]
            numeric_part = next((p for p in parts if p.isdigit() and len(p) >= 15), None)
            if numeric_part:
                await mig_db.execute("UPDATE orders SET binance_order_id = ? WHERE id = ?", (numeric_part, r["id"]))
                cleaned_count += 1
        if cleaned_count > 0:
            await mig_db.commit()
            logs.append(f"✅ Nettoyage de {cleaned_count} commande(s) au format slash.")
    except Exception as e:
        logs.append(f"⚠️ Échec du nettoyage des formats slash : {e}")
    finally:
        if mig_db: await mig_db.close()

    # 3. Interrogation de l'API SAPI pour les autres commandes contenant uniquement un Prepay ID (commençant par 'P_')
    try:
        mig_db = None
        from services.binance_verify import verify_payment
        mig_db = await get_db()
        cursor = await mig_db.execute(
            "SELECT id, product_id, binance_order_id, amount_usd FROM orders WHERE status = 'COMPLETED' AND binance_order_id LIKE 'P_%'"
        )
        orders_to_update = await cursor.fetchall()
        updated_count = 0
        
        for o in orders_to_update:
            p_id = o["product_id"]
            prepay_id = o["binance_order_id"]
            amount = float(o["amount_usd"])
            
            # Récupération des clés API associées au produit
            api_key_to_use = None
            api_secret_to_use = None
            if p_id:
                from database.models import get_product
                product = await get_product(p_id)
                if product and product.get("binance_account_id"):
                    from database.models import get_binance_account
                    acc = await get_binance_account(product["binance_account_id"])
                    if acc:
                        api_key_to_use = acc.get("api_key")
                        api_secret_to_use = acc.get("api_secret")
            
            # Requête API Binance SAPI pour récupérer le véritable orderId
            result = await verify_payment(prepay_id, amount, api_key=api_key_to_use, api_secret=api_secret_to_use)
            if result.get("verified") and result.get("transaction"):
                tx = result["transaction"]
                order_id_18 = tx.get("orderId", "")
                if order_id_18 and order_id_18.isdigit():
                    await mig_db.execute("UPDATE orders SET binance_order_id = ? WHERE id = ?", (order_id_18, o["id"]))
                    updated_count += 1
                    
        if updated_count > 0:
            await mig_db.commit()
            logs.append(f"✅ Mise à jour de {updated_count} commande(s) passée(s) avec leur Order ID SAPI.")
    except Exception as e:
        logs.append(f"⚠️ Échec de la récupération des Order IDs via SAPI : {e}")
    finally:
        if mig_db: await mig_db.close()

    try:
        await update.message.reply_text("\n".join(logs))
    except Exception as exc:
        await update.message.reply_text(f"❌ Completed with some errors, check logs.")



# ── Serve Vente DZ static files ──
_ventedz_dir = pathlib.Path(__file__).parent / "ventedz"
if _ventedz_dir.is_dir():
    api.mount("/dz", StaticFiles(directory=str(_ventedz_dir), html=True), name="ventedz")


# ──────────────────────────────────────────────
#  Main
# ──────────────────────────────────────────────

def main() -> None:
    """Build the Application, register handlers, and start in webhook or polling mode."""
    global tg_app

    webhook_url = os.environ.get("WEBHOOK_URL", "").strip()

    # In webhook mode, disable the built-in Updater (we handle updates via FastAPI)
    builder = Application.builder().token(BOT_TOKEN).connect_timeout(30.0).read_timeout(30.0).write_timeout(30.0).pool_timeout(30.0).post_init(post_init)
    if webhook_url:
        builder = builder.updater(None)
    app = builder.build()

    tg_app = app

    # ── Global Error Handler ─────────────
    from telegram.error import BadRequest

    async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log the error and handle specific harmless errors."""
        if isinstance(context.error, BadRequest):
            if "Message is not modified" in str(context.error):
                # Harmless error caused by users spamming inline buttons that don't change the message content
                return
        
        logger.error("Exception while handling an update:", exc_info=context.error)

    app.add_error_handler(global_error_handler)

    # ── Anti-spam middleware (runs before everything) ─────────────
    from utils.antispam import is_spam, should_warn, get_cooldown_remaining, SPAM_MESSAGES, WARN_MESSAGES, check_and_mark_cooldown_warned

    async def _antispam_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Global anti-spam pre-check. Blocks spamming users."""
        user = update.effective_user
        if not user:
            return
        user_id = user.id

        # Global Ban Check
        try:
            from database.models import is_user_banned
            if await is_user_banned(user_id):
                try:
                    if update.callback_query:
                        await update.callback_query.answer()
                except Exception:
                    pass
                raise ApplicationHandlerStop()
        except ApplicationHandlerStop:
            raise
        except Exception:
            pass

        # Check if they clicked a referral link and store it in context.user_data
        if update.message and update.message.text:
            text = update.message.text
            if text.startswith("/start ref_"):
                try:
                    ref_id = int(text.split("_")[1])
                    if context.user_data is not None:
                        context.user_data["referred_by"] = ref_id
                except (ValueError, IndexError):
                    pass

        # Forced Channel Subscription Check
        import time
        from config import REQUIRED_CHANNEL, ADMIN_IDS
        if REQUIRED_CHANNEL and user_id not in ADMIN_IDS:
            is_sub_callback = False
            if update.callback_query and update.callback_query.data == "check_sub":
                is_sub_callback = True

            if not is_sub_callback:
                now = time.time()
                cached_time = context.user_data.get("sub_verified_at", 0) if context.user_data else 0
                if (now - cached_time) < 900:
                    is_subscribed = True
                else:
                    is_subscribed = False
                    try:
                        member = await context.bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
                        if member.status in ["creator", "administrator", "member", "restricted"]:
                            is_subscribed = True
                            if context.user_data is not None:
                                context.user_data["sub_verified_at"] = now
                    except Exception as e:
                        err_msg = str(e).lower()
                        if "chat not found" in err_msg or "not enough rights" in err_msg or "admin" in err_msg:
                            is_subscribed = True
                            if context.user_data is not None:
                                context.user_data["sub_verified_at"] = now

                if not is_subscribed:
                    lang = "fr"
                    try:
                        from database.models import get_user_lang
                        lang = await get_user_lang(user_id)
                    except Exception:
                        pass

                    sub_msg = {
                        "fr": (
                            "📢 <b>Abonnement requis</b>\n\n"
                            "Pour utiliser ce bot, vous devez d'abord rejoindre notre canal Telegram.\n\n"
                            "Rejoignez-nous ici : https://t.me/Batmanstore2\n\n"
                            "Une fois rejoint, cliquez sur le bouton ci-dessous pour valider."
                        ),
                        "en": (
                            "📢 <b>Subscription Required</b>\n\n"
                            "To use this bot, you must first join our Telegram channel.\n\n"
                            "Join here: https://t.me/Batmanstore2\n\n"
                            "Once joined, click the button below to verify."
                        ),
                        "ar": (
                            "📢 <b>الاشتراك مطلوب</b>\n\n"
                            "لاستخدام هذا البوت، يجب عليك أولاً الانضمام إلى قناتنا على Telegram.\n\n"
                            "انضم هنا: https://t.me/Batmanstore2\n\n"
                            "بمجرد الانضمام، انقر فوق الزر أدناه للتحقق."
                        )
                    }

                    btn_text = {
                        "fr": "✅ Vérifier mon abonnement",
                        "en": "✅ Verify my subscription",
                        "ar": "✅ التحقق من الاشتراك"
                    }

                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    markup = InlineKeyboardMarkup([
                        [InlineKeyboardButton("📢 Rejoindre le Canal", url="https://t.me/Batmanstore2")],
                        [InlineKeyboardButton(btn_text.get(lang, btn_text["fr"]), callback_data="check_sub")]
                    ])

                    try:
                        if update.callback_query:
                            await update.callback_query.answer()
                            await update.callback_query.message.reply_text(sub_msg.get(lang, sub_msg["fr"]), reply_markup=markup, parse_mode="HTML")
                        elif update.message:
                            await update.message.reply_text(sub_msg.get(lang, sub_msg["fr"]), reply_markup=markup, parse_mode="HTML")
                    except Exception:
                        pass
                    raise ApplicationHandlerStop()

        if is_spam(user_id):
            if not check_and_mark_cooldown_warned(user_id):
                remaining = get_cooldown_remaining(user_id)
                lang = "fr"
                try:
                    from database.models import get_user_lang
                    lang = await get_user_lang(user_id)
                except Exception:
                    pass
                msg = SPAM_MESSAGES.get(lang, SPAM_MESSAGES["fr"]).format(sec=remaining)

                try:
                    if update.callback_query:
                        await update.callback_query.answer(msg, show_alert=True)
                    elif update.message:
                        await update.message.reply_text(msg)
                except Exception:
                    pass
            else:
                try:
                    if update.callback_query:
                        await update.callback_query.answer()
                except Exception:
                    pass
            raise ApplicationHandlerStop()

        if should_warn(user_id):
            lang = "fr"
            try:
                from database.models import get_user_lang
                lang = await get_user_lang(user_id)
            except Exception:
                pass
            warn = WARN_MESSAGES.get(lang, WARN_MESSAGES["fr"])
            try:
                if update.callback_query:
                    await update.callback_query.answer(warn, show_alert=False)
                elif update.message:
                    await update.message.reply_text(warn)
            except Exception:
                pass

    app.add_handler(TypeHandler(Update, _antispam_check), group=-1)

    # ── Conversation handlers (added first for priority) ─────────────
    app.add_handler(get_admin_conversation_handler(), group=0)
    app.add_handler(get_payment_conversation_handler(), group=1)
    app.add_handler(get_support_conversation_handler(), group=2)
    app.add_handler(wallet_conversation_handler(), group=3)

    # ── Command handlers ─────────────────────────────────────────
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("run_migrations", run_migrations_command))
    app.add_handler(CommandHandler("getemoji", get_emoji_command))

    # ── Callback query handlers ──────────────────────────────────
    app.add_handler(CallbackQueryHandler(callback_check_sub, pattern=r"^check_sub$"))
    app.add_handler(CallbackQueryHandler(download_txt_delivery, pattern=r"^dl_txt:"))
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern=r"^back_main$"))
    app.add_handler(CallbackQueryHandler(change_language, pattern=r"^change_lang$"))
    app.add_handler(CallbackQueryHandler(set_language, pattern=r"^lang:"))
    app.add_handler(CallbackQueryHandler(show_products_list, pattern=r"^menu_buy$"))
    app.add_handler(CallbackQueryHandler(show_products_list, pattern=r"^back_products$"))
    app.add_handler(CallbackQueryHandler(show_product_detail, pattern=r"^prod:"))
    app.add_handler(CallbackQueryHandler(show_profile, pattern=r"^menu_profile$"))
    app.add_handler(CallbackQueryHandler(show_referrals, pattern=r"^show_referrals$"))
    app.add_handler(CallbackQueryHandler(show_history, pattern=r"^menu_history$"))
    app.add_handler(CallbackQueryHandler(show_history, pattern=r"^hist_page:"))
    app.add_handler(CallbackQueryHandler(show_order_detail, pattern=r"^order:"))
    app.add_handler(CallbackQueryHandler(refresh_products, pattern=r"^refresh_prods$"))
    app.add_handler(CallbackQueryHandler(support_menu, pattern=r"^menu_support$"))
    app.add_handler(CallbackQueryHandler(show_my_tickets, pattern=r"^my_tickets$"))
    app.add_handler(CallbackQueryHandler(show_ticket_detail, pattern=r"^ticket:"))
    app.add_handler(CallbackQueryHandler(wallet_menu, pattern=r"^menu_wallet$"))
    app.add_handler(CallbackQueryHandler(wallet_menu, pattern=r"^back_wallet$"))
    app.add_handler(CallbackQueryHandler(wallet_history, pattern=r"^wallet_history$"))
    app.add_handler(CallbackQueryHandler(wallet_noop, pattern=r"^wallet_noop$"))

    # ── Reply keyboard text handlers ─────────────────────────────
    app.add_handler(MessageHandler(filters.Regex(r"^(🛍️ Produits|🛍️ Products|🛍️ المنتجات)$"), show_products_list))
    app.add_handler(MessageHandler(filters.Regex(r"^(💬 Support|💬 الدعم)$"), support_menu_text))
    app.add_handler(MessageHandler(filters.Regex(r"^(🚀 Commencer|🚀 Start|🚀 ابدأ)$"), start_command))
    app.add_handler(MessageHandler(filters.Regex(r"^(🌐 Langue|🌐 Language|🌐 اللغة)$"), change_language))

    # ── Decide: Webhook (production) or Polling (local dev) ──────
    port = int(os.environ.get("PORT", 8000))

    if webhook_url:
        # ── WEBHOOK MODE (Railway production) ────────────────────
        import asyncio

        async def _setup_and_run():
            """Initialize the bot, set webhook, and run FastAPI."""
            await app.initialize()
            await app.start()

            wh = f"{webhook_url}/webhook"
            await app.bot.set_webhook(
                url=wh,
                secret_token=WEBHOOK_SECRET or None,
                drop_pending_updates=False,
            )
            logger.info("🔗 Webhook set: %s", wh)

            config = uvicorn.Config(api, host="0.0.0.0", port=port, log_level="warning")
            server = uvicorn.Server(config)
            try:
                await server.serve()
            finally:
                # Do NOT delete the webhook on shutdown. In a rolling deployment,
                # the old container shutting down would delete the webhook set by the new container.
                await app.stop()
                await app.shutdown()

        logger.info("🚀 Bot starting in WEBHOOK mode (zero polling, saves credits)…")
        asyncio.run(_setup_and_run())
    else:
        # ── POLLING MODE (local development) ─────────────────────
        def _start_api_bg():
            def run_server():
                logger.info("🌐 REST API server starting on port %s", port)
                uvicorn.run(api, host="0.0.0.0", port=port, log_level="warning")
            thread = threading.Thread(target=run_server, daemon=True)
            thread.start()

        _start_api_bg()
        logger.info("🚀 Bot starting in POLLING mode (local dev)…")
        logger.info("💡 Set WEBHOOK_URL env var for production webhook mode")
        app.run_polling(drop_pending_updates=True)


@api.get("/api/export/transactions", dependencies=[Depends(verify_api_key)])
async def api_export_transactions(start_date: str, end_date: str):
    from database.models import get_transactions_for_export
    try:
        transactions = await get_transactions_for_export(start_date, end_date)
        return transactions
    except Exception as exc:
        logger.error("API error: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    main()




