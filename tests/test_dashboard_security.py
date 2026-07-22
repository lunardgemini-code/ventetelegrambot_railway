import re
import unittest
from pathlib import Path

import httpx

import bot


ROOT = Path(__file__).resolve().parents[1]


class DashboardSecurityTests(unittest.IsolatedAsyncioTestCase):
    async def test_dashboard_response_has_browser_security_headers(self):
        transport = httpx.ASGITransport(app=bot.api)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="https://testserver",
        ) as client:
            response = await client.get("/dashboard/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["x-content-type-options"], "nosniff")
        self.assertEqual(response.headers["x-frame-options"], "DENY")
        policy = response.headers["content-security-policy"]
        self.assertIn("object-src 'none'", policy)
        self.assertNotIn("'unsafe-eval'", policy)
        self.assertNotIn("script-src 'self' 'unsafe-inline'", policy)

    async def test_admin_key_is_exchanged_for_http_only_cookie(self):
        transport = httpx.ASGITransport(app=bot.api)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="https://testserver",
        ) as client:
            login = await client.post(
                "/api/admin/session",
                headers={"X-API-Key": bot.ADMIN_API_KEY},
            )
            authenticated = await client.get("/api/admin/session")

        self.assertEqual(login.status_code, 200)
        cookie = login.headers.get("set-cookie", "")
        self.assertIn("HttpOnly", cookie)
        self.assertIn("Secure", cookie)
        self.assertIn("SameSite=lax", cookie)
        self.assertEqual(authenticated.status_code, 200)

    def test_dashboard_has_no_inline_script_handlers(self):
        html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        inline_handler = re.compile(
            r"\bon(?:click|change|submit|input|error|load)\s*=",
            re.IGNORECASE,
        )
        self.assertIsNone(inline_handler.search(html))
        self.assertIsNone(inline_handler.search(script))
        self.assertNotRegex(html, r"<script(?![^>]*\bsrc=)")

    def test_external_dashboard_assets_are_integrity_pinned(self):
        html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        external_assets = re.findall(
            r"<(?:script|link)\b[^>]*(?:src|href)=\"https://[^\"]+\"[^>]*>",
            html,
            flags=re.IGNORECASE,
        )
        self.assertGreater(len(external_assets), 0)
        for asset in external_assets:
            with self.subTest(asset=asset):
                self.assertIn('integrity="sha384-', asset)
                self.assertIn('crossorigin="anonymous"', asset)

    def test_admin_key_is_not_persisted_in_local_storage(self):
        script = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        self.assertNotIn("localStorage.setItem('ventebot_key'", script)
        self.assertIn("sessionStorage.setItem('ventebot_key'", script)
        self.assertIn("/api/admin/session", script)

    def test_operational_views_are_wired_and_translated(self):
        html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        script = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        translations = script.split(
            "const OPERATIONS_TRANSLATIONS = {", 1
        )[1].split("Object.entries(OPERATIONS_TRANSLATIONS)", 1)[0]
        french = translations.split("\nfr: {", 1)[1].split("\n},\nen: {", 1)[0]
        keys = set(re.findall(r"\b(?:ops_|order_)[a-z0-9_]+\s*:", french))

        self.assertGreater(len(keys), 30)
        for raw_key in keys:
            key = raw_key.rstrip(":").strip()
            self.assertEqual(
                len(re.findall(rf"\b{re.escape(key)}\s*:", translations)),
                6,
                f"{key} is not translated in every language",
            )
        self.assertIn('id="finance-reconcile-checks"', html)
        self.assertIn('data-action="run-financial-reconciliation"', html)
        self.assertIn('id="order-timeline-list"', html)
        self.assertIn("/api/finance/reconciliation/run", script)
        self.assertIn("/api/orders/${orderId}/timeline", script)


if __name__ == "__main__":
    unittest.main()
