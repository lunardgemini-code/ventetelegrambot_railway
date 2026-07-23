"""Local dashboard visual-QA server with representative read-only API data."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


DASHBOARD_DIR = Path(__file__).resolve().parents[1] / "dashboard"


def _daily_points(days: int = 30) -> list[dict[str, object]]:
    today = datetime.now(timezone.utc).date()
    return [
        {
            "day": (today - timedelta(days=offset)).isoformat(),
            "revenue": round(54 + (offset % 6) * 7.4, 2),
            "orders": 13 + offset % 9,
        }
        for offset in range(days - 1, -1, -1)
    ]


MOCK_RESPONSES: dict[str, object] = {
    "/api/admin/session": {"authenticated": True},
    "/api/stats": {
        "total_revenue": 2846.2,
        "order_revenue": 2698.2,
        "topup_revenue": 166.0,
        "admin_deductions": 18.0,
        "completed_orders": 691,
        "pending_orders": 4,
        "total_users": 3248,
        "new_users": 186,
        "returning_users": 524,
        "stock_summary": [
            {"name": "Gemini 18 months", "emoji": "⚡", "stock": 126, "days_left": 12.4, "avg_daily_sales_7d": 10.2},
            {"name": "ChatGPT Plus", "emoji": "🎒", "stock": 18, "days_left": 2.1, "avg_daily_sales_7d": 8.5, "stock_risk": "soon"},
            {"name": "Grok 1 month", "emoji": "📦", "stock": 4, "days_left": 0.8, "avg_daily_sales_7d": 5.0, "stock_risk": "soon"},
        ],
    },
    "/api/dashboard/overview": {
        "today": {"revenue": 184.7, "orders": 42},
        "yesterday": {"revenue": 156.5, "orders": 38},
        "actions": {"delivery_issues": 2, "pending_activations": 7, "pending_payments": 4, "open_tickets": 3},
        "economics": {"known_profit_30d": 418.62, "known_profit_orders_30d": 233},
        "recent_orders": [
            {"id": 4821, "product_name": "Gemini 18 months", "product_emoji": "⚡", "username": "customer", "status": "COMPLETED", "amount_usd": 0.55, "created_at": "2026-07-22 14:20:00"},
            {"id": 4820, "product_name": "ChatGPT Plus", "product_emoji": "🎒", "username": "reseller", "status": "PENDING", "amount_usd": 2.4, "created_at": "2026-07-22 14:18:00"},
            {"id": 4819, "product_name": "Grok 1 month", "product_emoji": "📦", "user_first_name": "Sam", "status": "COMPLETED", "amount_usd": 1.15, "created_at": "2026-07-22 14:15:00"},
        ],
    },
    "/api/products": [
        {
            "id": 16,
            "name": "Gemini 18 months",
            "emoji": "⚡",
            "price_usd": 0.55,
            "warranty_days": 30,
            "delivery_type": "stock",
            "stock": 126,
            "is_active": 1,
            "total_sold": 412,
            "sort_order": 1,
        },
        {
            "id": 22,
            "name": "ChatGPT Plus activation",
            "emoji": "🎒",
            "price_usd": 2.4,
            "warranty_days": 7,
            "delivery_type": "activation",
            "stock": 0,
            "is_active": 1,
            "total_sold": 188,
            "sort_order": 2,
        },
        {
            "id": 31,
            "name": "Grok 1 month API",
            "emoji": "📦",
            "price_usd": 1.15,
            "warranty_days": 0,
            "delivery_type": "supplier_api",
            "stock": 38,
            "is_active": 1,
            "total_sold": 91,
            "sort_order": 3,
        },
    ],
    "/api/orders/all": {
        "total": 3,
        "orders": [
            {
                "id": 4821,
                "merchant_trade_no": "VB-4821-2026",
                "binance_order_id": "442882137117253632",
                "user_telegram_id": 100000001,
                "username": "customer",
                "product_id": 16,
                "product_name": "Gemini 18 months",
                "product_emoji": "⚡",
                "amount_usd": 0.55,
                "quantity": 1,
                "payment_method": "binance",
                "status": "COMPLETED",
                "created_at": "2026-07-22 14:20:00",
            },
            {
                "id": 4820,
                "merchant_trade_no": "VB-4820-2026",
                "binance_order_id": None,
                "user_telegram_id": 100000002,
                "username": "reseller",
                "product_id": 22,
                "product_name": "ChatGPT Plus activation",
                "product_emoji": "🎒",
                "amount_usd": 2.4,
                "quantity": 1,
                "payment_method": "wallet",
                "status": "AWAITING_ACTIVATION",
                "activation_identifier": "@customer_account",
                "created_at": "2026-07-22 14:18:00",
            },
            {
                "id": 4819,
                "merchant_trade_no": "VB-4819-2026",
                "binance_order_id": None,
                "user_telegram_id": 100000003,
                "user_first_name": "Sam",
                "product_id": 31,
                "product_name": "Grok 1 month API",
                "product_emoji": "📦",
                "amount_usd": 1.15,
                "quantity": 1,
                "payment_method": "wallet",
                "status": "PAID_PENDING_DELIVERY",
                "created_at": "2026-07-22 14:15:00",
            },
        ],
    },
    "/api/performance": {
        "workers": {"active": 8, "configured": 8, "recommended": 8},
        "queue": {"current": 0, "peak_5m": 3, "p95_wait_ms": 18},
        "traffic": {"throughput_per_minute": 18.4},
        "latency": {"p95_processing_ms": 142, "p95_user_wait_ms": 22},
        "database": {"p95_ms": 74, "connection_errors": 0, "write_serialization": {"p95_wait_ms": 38, "timeouts": 0}},
        "diagnosis": {"bottleneck": "healthy"},
        "actions_5m": [{"action": "products", "p95_ms": 312, "count": 18}],
        "history_24h": {"actions": [{"action": "products", "average_ms": 118, "count": 244}]},
        "autoscaling": {"mode": "auto", "observe_only": True, "state": "CALM", "current_workers": 8, "proposed_workers": 8, "min_workers": 6, "max_workers": 20, "next_analysis_at": 4102444800, "timeline": [], "decisions": []},
    },
    "/api/payments/review": {
        "summary": {"all": 2, "underpaid": 2, "confirming": 0, "late_after_cancel": 0, "expired": 0},
        "items": [
            {
                "category": "underpaid",
                "payment_id": "NP-8801",
                "product_name": "ChatGPT Plus",
                "actually_paid": 2.35,
                "resolved": False,
                "updated_at": "2026-07-22 14:22:00",
            }
        ],
    },
    "/api/binance-accounts": [],
    "/api/orders/activations": {"total": 0, "orders": []},
    "/api/resellers": {"resellers": []},
    "/api/game/provider": {"configured": False, "summary": {}},
    "/api/game/matches": {"matches": [], "summary": {}},
    "/api/supplier-bots": {
        "providers": [
            {"code": "preview", "name": "Preview Supplier", "configured": True, "enabled": True, "selected_count": 0}
        ]
    },
    "/api/supplier-bots/preview": {
        "supplier": "Preview Supplier",
        "configured": True,
        "enabled": True,
        "display_name": "Preview Supplier",
        "credential_env": "PREVIEW_API_KEY",
        "source_currency": "USD",
        "margin_type": "fixed",
        "margin_value": 0.5,
        "wallet": {"balance": 25.0, "balance_text": "$25.00"},
        "last_sync": "2026-07-22 14:00:00",
        "products": [],
        "order_counts": {},
    },
    "/api/supplier-bots/preview/stats": {
        "summary": {}, "data_quality": {}, "products": [], "daily": []
    },
    "/api/supplier-router/routes": {"routes": []},
    "/api/ai-supplier/status": {
        "configured_suppliers": 1,
        "indexed_products": 3,
        "last_analysis": "2026-07-22 14:00:00",
        "job": None,
    },
    "/api/ai-supplier/groups": {
        "groups": [], "available_products": 3, "comparison_groups": 0
    },
    "/api/wallet/history": {"transactions": [], "total": 0},
    "/api/tickets": [],
    "/api/users": {"users": [], "total": 0},
    "/api/promos": [],
    "/api/settings/payment": {"bep20_address": "", "trc20_address": ""},
    "/api/finance": {
        "daily_revenue": 184.7,
        "weekly_revenue": 1062.5,
        "monthly_revenue": 2846.2,
        "bot_balance": 325.4,
        "sales_binance_30d": 820.0,
        "sales_bep20_30d": 742.0,
        "sales_trc20_30d": 314.0,
        "sales_wallet_30d": 822.2,
        "topup_count_30d": 48,
        "topup_revenue_30d": 166.0,
    },
    "/api/finance/reconciliation": {"available": False},
}


def _product_insights(product_id: int) -> dict[str, object]:
    product = next(
        (
            item
            for item in MOCK_RESPONSES["/api/products"]
            if int(item["id"]) == int(product_id)
        ),
        MOCK_RESPONSES["/api/products"][0],
    )
    days = [
        (datetime.now(timezone.utc).date() - timedelta(days=offset)).isoformat()
        for offset in range(29, -1, -1)
    ]
    quantity = [0, 1, 0, 2, 1, 3, 2, 4, 3, 5] * 3
    revenue = [round(value * float(product["price_usd"]), 2) for value in quantity]
    sale_price = float(product["price_usd"])
    return {
        "product": product,
        "sales": {
            "days": days,
            "quantity_series": quantity,
            "revenue_series": revenue,
            "today": quantity[-1],
            "sales_7d": sum(quantity[-7:]),
            "revenue_7d": round(sum(revenue[-7:]), 2),
            "sales_30d": sum(quantity),
            "revenue_30d": round(sum(revenue), 2),
        },
        "conversion": {
            "views": 820,
            "buy_clicks": 412,
            "payments_created": 330,
            "payments_completed": 304,
            "overall_rate": 0.3707,
        },
        "stock": {
            "current": product.get("stock", 0),
            "daily_velocity_7d": 3.1,
            "days_left": 5.8,
        },
        "economics": {"known_profit_30d": 81.42},
        "price_history": [
            {"new_price": round(sale_price * 0.92, 2), "created_at": "2026-07-10 10:00:00"},
            {"new_price": round(sale_price * 0.96, 2), "created_at": "2026-07-16 10:00:00"},
            {"new_price": sale_price, "created_at": "2026-07-22 10:00:00"},
        ],
        "supplier_comparison": [
            {
                "supplier_code": "preview",
                "supplier_name": "Preview Supplier",
                "external_product_id": "PREVIEW-01",
                "name": product["name"],
                "provider_enabled": True,
                "cost": round(max(0.1, sale_price - 0.18), 2),
                "sale_price": sale_price,
                "margin": 0.18,
                "remote_stock": 120,
                "affordable_stock": 45,
                "wallet_balance": 25.0,
                "warranty_days": 30,
                "delivery_mode": "instant",
                "access_mode": "private",
                "reliability": 0.97,
                "freshness_hours": 0.4,
                "recommended": True,
            },
            {
                "supplier_code": "backup",
                "supplier_name": "Backup Market",
                "external_product_id": "BACKUP-14",
                "name": product["name"],
                "provider_enabled": True,
                "cost": round(max(0.1, sale_price - 0.11), 2),
                "sale_price": sale_price,
                "margin": 0.11,
                "remote_stock": 80,
                "affordable_stock": 12,
                "wallet_balance": 8.0,
                "warranty_days": 7,
                "delivery_mode": "instant",
                "access_mode": "shared",
                "reliability": 0.91,
                "freshness_hours": 2.2,
                "recommended": False,
            },
        ],
    }


def _stats_bundle() -> dict[str, object]:
    products = [
        {"id": 16, "name": "Gemini 18 months", "emoji": "⚡", "price_usd": 0.55, "total_sold": 412, "total_revenue": 226.6, "stock": 126, "delivery_type": "stock", "is_active": 1},
        {"id": 22, "name": "ChatGPT Plus activation", "emoji": "🎒", "price_usd": 2.4, "total_sold": 188, "total_revenue": 451.2, "stock": 0, "delivery_type": "activation", "is_active": 1},
        {"id": 31, "name": "Grok 1 month API", "emoji": "📦", "price_usd": 1.15, "total_sold": 91, "total_revenue": 104.65, "stock": 38, "delivery_type": "supplier_api", "is_active": 1},
    ]
    days = _daily_points()
    labels = [point["day"] for point in days]
    momentum_products = []
    for index, product in enumerate(products):
        series = [0] * 30
        for offset in range(30 - (8 + index * 2), 30):
            series[offset] = max(0, (offset + index) % (6 - index))
        momentum_products.append(
            {
                "id": product["id"],
                "name": product["name"],
                "emoji": product["emoji"],
                "series": series,
                "revenue_series": [round(value * float(product["price_usd"]), 2) for value in series],
                "total_sold": sum(series),
                "total_revenue": round(sum(series) * float(product["price_usd"]), 2),
                "yesterday_sold": series[-2],
            }
        )
    return {
        "stats": MOCK_RESPONSES["/api/stats"],
        "daily": days,
        "products": products,
        "momentum": {"days": labels, "products": momentum_products},
        "dead_alerts": {"alerts": []},
        "conversion": {
            "tracking_since": "2026-07-01 00:00:00",
            "summary": {"views": 1240, "buy_clicks": 506, "payments_created": 418, "payments_completed": 372, "view_to_buy_rate": 0.408, "buy_to_payment_rate": 0.826, "payment_completion_rate": 0.89, "overall_conversion_rate": 0.30},
            "products": [],
        },
    }


class PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DASHBOARD_DIR), **kwargs)

    def _json(self, payload: object, status: int = 200) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/admin/session":
            self._json(MOCK_RESPONSES[path])
            return
        self._json({"detail": "Preview endpoint not implemented"}, 404)

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/api/dashboard/search":
            query = parse_qs(parsed.query).get("q", [""])[0]
            self._json(
                {
                    "query": query,
                    "results": [
                        {
                            "entity_type": "product",
                            "entity_id": "16",
                            "title": "Gemini 18 months",
                            "subtitle": "$0.55",
                            "status": "active",
                            "amount": 0.55,
                            "related_id": 16,
                        },
                        {
                            "entity_type": "order",
                            "entity_id": "4821",
                            "title": "#4821",
                            "subtitle": "Gemini 18 months - @customer",
                            "status": "COMPLETED",
                            "amount": 0.55,
                            "related_id": 16,
                        },
                        {
                            "entity_type": "user",
                            "entity_id": "100000001",
                            "title": "@customer",
                            "subtitle": "ID 100000001",
                            "status": "active",
                            "amount": 12.4,
                            "related_id": 100000001,
                        },
                    ],
                }
            )
            return
        if parsed.path.startswith("/api/products/") and parsed.path.endswith("/insights"):
            try:
                product_id = int(parsed.path.split("/")[3])
            except (ValueError, IndexError):
                self._json({"detail": "Product not found"}, 404)
                return
            self._json(_product_insights(product_id))
            return
        if parsed.path.startswith("/api/orders/") and parsed.path.endswith("/items"):
            self._json(
                {
                    "status": "COMPLETED",
                    "items": [{"account_data": "preview-account@example.com | preview-password"}],
                }
            )
            return
        if parsed.path.startswith("/api/orders/") and parsed.path.endswith("/timeline"):
            self._json(
                {
                    "events": [
                        {"type": "order.created", "occurred_at": "2026-07-22 14:18:00", "details": {}},
                        {"type": "payment.confirmed", "occurred_at": "2026-07-22 14:19:00", "details": {"status": "confirmed"}},
                        {"type": "stock.reserved", "occurred_at": "2026-07-22 14:19:02", "details": {}},
                    ]
                }
            )
            return
        if parsed.path.startswith("/api/users/") and parsed.path.endswith("/orders"):
            self._json(
                {
                    "user": {
                        "telegram_id": 100000001,
                        "username": "customer",
                        "language": "en",
                        "wallet_balance": 12.4,
                        "total_spent": 18.75,
                        "total_orders": 14,
                    },
                    "total": 2,
                    "orders": MOCK_RESPONSES["/api/orders/all"]["orders"][:2],
                }
            )
            return
        if parsed.path == "/api/stats/daily":
            self._json(_daily_points())
            return
        if parsed.path == "/api/stats/bundle":
            self._json(_stats_bundle())
            return
        if parsed.path == "/api/payments/review":
            self._json(MOCK_RESPONSES["/api/payments/review"])
            return
        if parsed.path in MOCK_RESPONSES:
            self._json(MOCK_RESPONSES[parsed.path])
            return
        super().do_GET()


if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", 8766), PreviewHandler).serve_forever()
