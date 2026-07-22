import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DashboardV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (ROOT / "dashboard" / "index.html").read_text(encoding="utf-8")
        cls.app = (ROOT / "dashboard" / "app.js").read_text(encoding="utf-8")
        cls.system = (ROOT / "dashboard" / "system.css").read_text(encoding="utf-8")
        cls.shell_translations = cls.app.split(
            "const SHELL_TRANSLATIONS = {", 1
        )[1].split("Object.entries(SHELL_TRANSLATIONS)", 1)[0]

    def test_navigation_preserves_every_existing_operational_view(self):
        expected_tabs = {
            "dashboard-tab", "stats-tab", "finance-tab", "orders-tab",
            "payment-review-tab", "activations-tab", "inventory-tab",
            "users-tab", "wallet-history-tab", "tickets-tab", "resellers-tab",
            "supplier-bots-tab", "ai-bot-tab", "game-tab", "binance-tab",
            "broadcast-tab", "settings-tab",
        }
        menu_tabs = re.findall(r'class="menu-item(?: active)?" data-tab="([^"]+)"', self.html)
        self.assertEqual(set(menu_tabs), expected_tabs)
        self.assertEqual(len(menu_tabs), len(set(menu_tabs)))
        for tab_id in expected_tabs:
            self.assertIn(f'id="{tab_id}"', self.html)

    def test_navigation_groups_follow_the_operational_hierarchy(self):
        keys = [
            "nav_group_overview", "nav_group_sales", "nav_group_catalog",
            "nav_group_clients", "nav_group_resellers", "nav_group_analytics",
            "nav_group_tools",
        ]
        positions = [self.html.index(f'data-i18n="{key}"') for key in keys]
        self.assertEqual(positions, sorted(positions))

    def test_shell_translations_exist_in_all_six_languages(self):
        french = self.shell_translations.split("\nfr: {", 1)[1].split("\n},\nen: {", 1)[0]
        keys = set(re.findall(r"\b([a-z][a-z0-9_]+)\s*:\s*\"", french))
        self.assertGreater(len(keys), 55)
        for key in keys:
            self.assertEqual(
                len(re.findall(rf"\b{re.escape(key)}\s*:\s*\"", self.shell_translations)),
                6,
                f"{key} is not translated in every dashboard language",
            )

    def test_operational_translation_bundles_cover_all_six_languages(self):
        bundles = (
            "DASHBOARD_RUNTIME_TRANSLATIONS",
            "OPERATIONAL_SCREEN_TRANSLATIONS",
            "GENERATED_SCREEN_TRANSLATIONS",
            "EXTENDED_SCREEN_TRANSLATIONS",
            "MODAL_SCREEN_TRANSLATIONS",
            "MISC_UI_TRANSLATIONS",
            "ACTION_FEEDBACK_TRANSLATIONS",
        )
        for bundle in bundles:
            segment = self.app.split(f"const {bundle} = {{", 1)[1].split(
                f"Object.entries({bundle})", 1
            )[0]
            french_match = re.search(r"\bfr\s*:\s*\{(.*?)\}\s*,\s*en\s*:\s*\{", segment, re.S)
            self.assertIsNotNone(french_match, bundle)
            french = french_match.group(1)
            key_pattern = r"(?:\{|,)\s*([a-z][a-z0-9_]+)\s*:\s*\""
            keys = set(re.findall(key_pattern, french))
            self.assertGreater(len(keys), 2, bundle)
            for key in keys:
                self.assertEqual(
                    len(re.findall(rf"(?:\{{|,)\s*{re.escape(key)}\s*:\s*\"", segment)),
                    6,
                    f"{bundle}.{key} is not translated in every language",
                )

    def test_legacy_static_translation_pass_covers_operational_screens(self):
        self.assertIn("function applyLegacyStaticTranslations", self.app)
        self.assertIn("applyLegacyStaticTranslations();", self.app)
        for source in (
            '"Gestion Financière":"finance_title"',
            '"Catalogue externe":"supplier_external_catalog"',
            '"Match Arena":"game_arena"',
            '"Modifier le Produit":"product_edit_title"',
            '"Exporter les Transactions":"export_transactions"',
            '"Optionnel...":"common_optional_placeholder"',
            '"Dynamic Price":"product_dynamic"',
        ):
            self.assertIn(source, self.app)
        self.assertIn('data-i18n="supplier_key_prefix"', self.html)
        self.assertIn('data-i18n="game_api_key_suffix"', self.html)
        self.assertIn('data-i18n="settings_crypto_addresses"', self.html)
        self.assertIn('data-i18n="settings_crypto_help"', self.html)

    def test_accessible_shell_and_feedback_regions_are_present(self):
        self.assertIn('class="skip-link"', self.html)
        self.assertIn('id="dashboard-workspace"', self.html)
        self.assertIn('aria-controls="dashboard-sidebar"', self.html)
        self.assertIn('aria-expanded="false"', self.html)
        self.assertIn('id="page-status-region"', self.html)
        self.assertIn("case 'retry-tab':", self.app)
        self.assertIn("data-i18n-aria-label", self.app)

    def test_tab_cache_does_not_change_explicit_refresh_semantics(self):
        self.assertIn("const TAB_CACHE_TTLS", self.app)
        self.assertIn("options.useCache && !options.force", self.app)
        self.assertIn("refreshData({tabId, useCache:true", self.app)
        self.assertIn("refreshData({force:true})", self.app)
        self.assertIn("tabScrollPositions", self.app)

    def test_duplicate_requests_and_mobile_tables_are_guarded(self):
        self.assertIn("const inFlightApiRequests = new Map()", self.app)
        self.assertIn("inFlightApiRequests.get(requestKey)", self.app)
        self.assertIn("setActionControlBusy(actionControl, true)", self.app)
        self.assertIn("function setupResponsiveTables()", self.app)
        self.assertIn("responsive-table-cards", self.app)

    def test_design_system_covers_required_breakpoints_and_rtl(self):
        for width in (1280, 768, 430, 390, 360):
            self.assertIn(f"@media (max-width: {width}px)", self.system)
        self.assertIn("--ds-control: 44px", self.system)
        self.assertIn('[dir="rtl"] .sidebar', self.system)
        self.assertIn(".data-table.responsive-table-cards", self.system)
        self.assertIn("grid-template-columns: minmax(108px, 36%) minmax(0, 1fr)", self.system)
        self.assertIn("max-height: 94dvh", self.system)

    def test_overview_prioritizes_actions_before_secondary_metrics(self):
        operations = self.system.index("#dashboard-tab .operations-grid { order: 3; }")
        metrics = self.system.index("#dashboard-tab .metrics-grid { order: 4; }")
        performance = self.system.index("#dashboard-tab .bot-performance { order: 7; }")
        self.assertLess(operations, metrics)
        self.assertLess(metrics, performance)


if __name__ == "__main__":
    unittest.main()
