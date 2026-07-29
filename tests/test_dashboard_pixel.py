import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"


class DashboardPixelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        cls.app = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        cls.css = (DASHBOARD / "operations.css").read_text(encoding="utf-8")

    def test_pixel_tab_and_secure_trace_are_present(self):
        self.assertIn('data-tab="pixel-tab"', self.html)
        self.assertIn('id="pixel-tab"', self.html)
        self.assertIn("function renderPixelActivation", self.app)
        self.assertIn("/api/pixel", self.app)
        self.assertIn("credential_encryption_ready", self.app)
        self.assertNotIn("password_encrypted", self.app)
        self.assertNotIn("twofa_secret_encrypted", self.app)
        self.assertIn(".pixel-layout", self.css)

    def test_pixel_labels_exist_in_all_dashboard_languages(self):
        block = self.app.split("const PIXEL_DASHBOARD_TRANSLATIONS = {", 1)[1].split(
            "Object.entries(PIXEL_DASHBOARD_TRANSLATIONS)", 1
        )[0]
        for key in ("nav_pixel", "pixel_title", "pixel_security_note", "pixel_tasks_title"):
            self.assertEqual(block.count(f"{key}:"), 6, key)


if __name__ == "__main__":
    unittest.main()
