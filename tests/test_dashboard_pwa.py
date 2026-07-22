import json
import struct
import unittest
from pathlib import Path

import httpx

import bot


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"


def png_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise AssertionError(f"{path.name} is not a PNG file")
    return struct.unpack(">II", data[16:24])


class DashboardPwaTests(unittest.IsolatedAsyncioTestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        cls.app = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        cls.worker = (DASHBOARD / "service-worker.js").read_text(encoding="utf-8")
        cls.manifest = json.loads(
            (DASHBOARD / "manifest.webmanifest").read_text(encoding="utf-8")
        )

    def test_manifest_is_installable_and_scoped_to_dashboard(self):
        self.assertEqual(self.manifest["start_url"], "./")
        self.assertEqual(self.manifest["scope"], "./")
        self.assertEqual(self.manifest["display"], "standalone")
        self.assertEqual(self.manifest["id"], "./")
        self.assertIn('rel="manifest"', self.html)
        self.assertIn('apple-mobile-web-app-capable" content="yes"', self.html)
        self.assertIn('viewport-fit=cover', self.html)

    def test_manifest_icons_exist_with_declared_sizes(self):
        for icon in self.manifest["icons"]:
            path = DASHBOARD / icon["src"]
            self.assertTrue(path.is_file(), icon["src"])
            expected = tuple(int(value) for value in icon["sizes"].split("x"))
            self.assertEqual(png_dimensions(path), expected)
        apple_icon = DASHBOARD / "icons" / "ventebot-apple-touch-180.png"
        self.assertEqual(png_dimensions(apple_icon), (180, 180))

    def test_service_worker_never_intercepts_api_or_mutating_requests(self):
        self.assertIn("request.method !== 'GET'", self.worker)
        self.assertIn("url.pathname.startsWith('/api/')", self.worker)
        self.assertIn("request.headers.has('authorization')", self.worker)
        self.assertIn("url.origin !== self.location.origin", self.worker)
        self.assertNotIn("skipWaiting", self.worker)
        self.assertIn("networkFirst(request)", self.worker)

    def test_installation_and_updates_are_wired_without_forced_reload(self):
        self.assertIn('id="btn-install-app"', self.html)
        self.assertIn("beforeinstallprompt", self.app)
        self.assertIn("navigator.serviceWorker.register", self.app)
        self.assertIn("updateViaCache:'none'", self.app)
        self.assertIn("pwa_update_ready", self.app)
        self.assertNotIn("window.location.reload()", self.app)

    def test_pwa_strings_are_available_in_all_dashboard_languages(self):
        shell = self.app.split("const SHELL_TRANSLATIONS = {", 1)[1].split(
            "Object.entries(SHELL_TRANSLATIONS)", 1
        )[0]
        for key in (
            "install_app",
            "app_installed",
            "pwa_install_success",
            "pwa_install_unavailable",
            "pwa_ios_instructions",
            "pwa_update_ready",
        ):
            self.assertEqual(shell.count(f'{key}:"'), 6, key)

    async def test_manifest_and_worker_are_revalidated_instead_of_stale_cached(self):
        transport = httpx.ASGITransport(app=bot.api)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="https://testserver",
        ) as client:
            manifest = await client.get("/dashboard/manifest.webmanifest")
            worker = await client.get("/dashboard/service-worker.js")
            icon = await client.get("/dashboard/icons/ventebot-icon-192.png")

        self.assertEqual(manifest.status_code, 200)
        self.assertEqual(worker.status_code, 200)
        self.assertIn("application/manifest+json", manifest.headers["content-type"])
        self.assertIn("javascript", worker.headers["content-type"])
        self.assertEqual(manifest.headers["cache-control"], "no-cache, must-revalidate")
        self.assertEqual(worker.headers["cache-control"], "no-cache, must-revalidate")
        self.assertEqual(worker.headers["service-worker-allowed"], "/dashboard/")
        self.assertIn("public", icon.headers["cache-control"])


if __name__ == "__main__":
    unittest.main()
