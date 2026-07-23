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

    def test_pwa_cache_uses_the_mobile_product_asset_version(self):
        version = "20260723-mobile-products-v2"
        self.assertIn(f"operations.css?v={version}", self.html)
        self.assertIn(f"app.js?v={version}", self.html)
        self.assertIn(f"ventebot-dashboard-shell-{version}", self.worker)
        self.assertIn(f"operations.css?v={version}", self.worker)
        self.assertIn(f"app.js?v={version}", self.worker)


if __name__ == "__main__":
    unittest.main()
