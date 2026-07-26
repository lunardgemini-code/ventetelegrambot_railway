import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"


class DashboardMobileProductTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        cls.css = (DASHBOARD / "operations.css").read_text(encoding="utf-8")
        cls.html = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        cls.worker = (DASHBOARD / "service-worker.js").read_text(encoding="utf-8")

    def test_product_rows_are_enhanced_as_an_accessible_accordion(self):
        self.assertIn("function enhanceMobileProductRows(products)", self.app)
        self.assertIn("toggle.dataset.action = 'toggle-mobile-product-details'", self.app)
        self.assertIn("toggle.setAttribute('aria-expanded', 'false')", self.app)
        self.assertIn("function setMobileProductRowExpanded(row, expanded)", self.app)
        self.assertIn("tr.product-list-row.is-mobile-expanded", self.app)

    def test_only_expanded_product_details_are_visible_on_mobile(self):
        self.assertIn("#inventory-tab #products-table-body .product-detail-cell", self.css)
        self.assertIn(
            "tr.product-list-row.is-mobile-expanded .product-detail-cell:not(.product-actions-cell)",
            self.css,
        )
        self.assertIn(
            "tr.product-list-row.is-mobile-expanded .product-actions-cell",
            self.css,
        )
        self.assertIn(".mobile-product-toggle", self.css)

    def test_mobile_product_labels_cover_every_dashboard_language(self):
        for language in ("fr", "en", "ar", "zh", "vi", "ru"):
            self.assertIn(f"{language}: {{", self.app)
        self.assertEqual(self.app.count("product_expand_details:"), 6)
        self.assertEqual(self.app.count("product_collapse_details:"), 6)
        self.assertEqual(self.app.count("product_reorder:"), 6)

    def test_mobile_product_accordion_uses_liquid_glass_tokens(self):
        selector = (
            'html:is([data-appearance="liquid"], [data-appearance="auto"]) '
            "#inventory-tab #products-table-body tr.product-list-row"
        )
        self.assertIn(selector, self.css)
        self.assertIn("var(--lg-panel-raised)", self.css)
        self.assertIn("var(--lg-highlight-strong)", self.css)
        self.assertIn(
            'html[data-reduce-transparency="true"]:is([data-appearance="liquid"], '
            '[data-appearance="auto"]) #inventory-tab',
            self.css,
        )

    def test_pwa_cache_uses_the_auto_hide_asset_version(self):
        # operations.css still carries the auto-hide version; app.js was
        # rebumped by the performance pass. The SW cache tag advances
        # independently of individual asset versions.
        self.assertIn("operations.css?v=20260725-auto-hide-v2", self.html)
        self.assertIn("app.js?v=20260726-targeted-broadcast-v1", self.html)
        self.assertIn("ventebot-dashboard-shell-20260726-targeted-broadcast-v1", self.worker)
        self.assertIn("operations.css?v=20260725-auto-hide-v2", self.worker)
        self.assertIn("app.js?v=20260726-targeted-broadcast-v1", self.worker)

    def test_auto_hide_controls_are_responsive_and_fully_translated(self):
        self.assertIn('id="product-auto-hide-filter"', self.html)
        self.assertIn('id="prod-auto-hide-enabled"', self.html)
        self.assertIn('id="edit-prod-auto-hide-enabled"', self.html)
        self.assertIn("function applyProductAutoHideFilter()", self.app)
        self.assertIn("function resetProductAutoHide(productId)", self.app)
        self.assertIn(".auto-hide-panel", self.css)
        self.assertIn("@media (max-width: 700px)", self.css)
        self.assertEqual(self.app.count("auto_hide_filter_label:"), 6)
        self.assertEqual(self.app.count("auto_hide_status_hidden:"), 6)


if __name__ == "__main__":
    unittest.main()
