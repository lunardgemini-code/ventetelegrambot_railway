import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DashboardAiI18nTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        cls.html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        cls.styles = (ROOT / "dashboard" / "style.css").read_text(encoding="utf-8")
        cls.translation_block = cls.app.split(
            "const AI_TRANSLATIONS = {", 1
        )[1].split("Object.entries(AI_TRANSLATIONS)", 1)[0]
        cls.french_block = cls.translation_block.split(
            "\nfr: {", 1
        )[1].split("\n},\nen: {", 1)[0]

    def test_every_ai_translation_exists_in_all_six_languages(self):
        french_keys = set(re.findall(r"\b(?:ai_[a-z0-9_]+|nav_ai_bot)\s*:", self.french_block))
        self.assertGreater(len(french_keys), 90)
        for raw_key in french_keys:
            key = raw_key.rstrip(":").strip()
            occurrences = len(re.findall(rf"\b{re.escape(key)}\s*:", self.translation_block))
            self.assertEqual(occurrences, 6, f"{key} is not translated in every language")

    def test_every_ai_html_key_is_in_the_translation_dictionary(self):
        ai_section = self.html.split('<section id="ai-bot-tab"', 1)[1].split("</section>", 1)[0]
        html_keys = set(re.findall(r'data-i18n(?:-placeholder|-title)?="(ai_[a-z0-9_]+|nav_ai_bot)"', ai_section))
        french_keys = set(re.findall(r"\b(ai_[a-z0-9_]+|nav_ai_bot)\s*:", self.french_block))
        self.assertFalse(html_keys - french_keys)

    def test_dynamic_results_do_not_render_backend_french_or_raw_modes(self):
        ai_code = self.app.split("function aiSupplierErrorMessage", 1)[1].split(
            "async function loadWalletHistory", 1
        )[0]
        referenced_keys = set(re.findall(r"['\"](ai_[a-z0-9_]+)['\"]", ai_code))
        french_keys = set(re.findall(r"\b(ai_[a-z0-9_]+)\s*:", self.french_block))
        self.assertFalse(referenced_keys - french_keys)
        self.assertNotIn("result.reason", ai_code)
        self.assertNotIn("group.signature", ai_code)
        self.assertNotIn("result.delivery_mode || 'unknown'", ai_code)
        self.assertNotIn("result.access_mode || 'unknown'", ai_code)

    def test_dashboard_assets_use_the_i18n_cache_version(self):
        self.assertIn('app.js?v=20260723-mobile-products-v2', self.html)
        self.assertIn('operations.js?v=20260723-ops-v2', self.html)
        self.assertIn('style.css?v=20260720-reseller-telegram-prices', self.html)
        self.assertIn('system.css?v=20260723-pwa-v8', self.html)

    def test_reseller_special_price_controls_are_wired_and_responsive(self):
        self.assertIn('id="reseller-special-prices-modal"', self.html)
        self.assertIn('id="reseller-special-prices-form"', self.html)
        self.assertIn('data-action="reseller-special"', self.app)
        self.assertIn("case 'reseller-special':", self.app)
        self.assertIn("/special-prices", self.app)
        self.assertIn('id="reseller-special-telegram"', self.html)
        self.assertIn('apply_to_telegram: DOM.resellerSpecialTelegram.checked', self.app)
        self.assertIn('.reseller-special-prices-form', self.styles)
        self.assertIn('@media (max-width: 720px)', self.styles)

    def test_ai_results_have_responsive_card_metadata(self):
        ai_code = self.app.split("function renderAiSupplierGroups", 1)[1].split(
            "async function loadWalletHistory", 1
        )[0]
        self.assertIn('class="ai-result-row"', ai_code)
        self.assertIn('class="ai-group-row"', ai_code)
        self.assertIn('data-label="${escapeHtml(t(\'ai_col_price\'))}"', ai_code)
        self.assertIn('class="ai-mobile-action-label"', ai_code)

    def test_ai_mobile_layout_does_not_force_wide_tables(self):
        responsive = self.styles.split("@media (max-width: 820px)", 1)[1]
        self.assertIn(".ai-results-table, .ai-groups-table", responsive)
        self.assertIn("min-width:0", responsive)
        self.assertIn('"rank price"', responsive)
        self.assertIn('"title best"', responsive)
        self.assertNotIn(".ai-results-table { min-width:980px; }", responsive)


if __name__ == "__main__":
    unittest.main()
