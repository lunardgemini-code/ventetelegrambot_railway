import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DASHBOARD = ROOT / "dashboard"


class DashboardAppearanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (DASHBOARD / "index.html").read_text(encoding="utf-8")
        cls.app = (DASHBOARD / "app.js").read_text(encoding="utf-8")
        cls.bootstrap = (DASHBOARD / "theme-bootstrap.js").read_text(encoding="utf-8")
        cls.liquid = (DASHBOARD / "liquid-glass.css").read_text(encoding="utf-8")

    def test_liquid_glass_is_bootstrapped_before_styles_and_is_the_default(self):
        bootstrap_position = self.html.index('src="theme-bootstrap.js')
        first_dashboard_style = self.html.index('href="style.css')
        self.assertLess(bootstrap_position, first_dashboard_style)
        self.assertIn("validAppearances.has(savedAppearance) ? savedAppearance : 'liquid'", self.bootstrap)
        self.assertIn("root.dataset.appearance = appearance", self.bootstrap)

    def test_existing_theme_and_new_local_preferences_are_preserved(self):
        for key in (
            "vb_theme",
            "ventebot_appearance",
            "ventebot_reduce_transparency",
        ):
            self.assertIn(key, self.bootstrap)
            self.assertIn(key, self.app)
        appearance_section = self.app.split(
            "const APPEARANCE_STORAGE_KEY", 1
        )[1].split("AUTO-REFRESH", 1)[0]
        self.assertNotIn("apiCall(", appearance_section)
        self.assertNotIn("fetch(", appearance_section)

    def test_settings_expose_all_modes_and_accessibility_switch(self):
        for value in ("liquid", "standard", "auto"):
            self.assertIn(
                f'name="appearance-mode" value="{value}"',
                self.html,
            )
        self.assertIn('id="reduce-transparency"', self.html)
        self.assertIn('role="radiogroup"', self.html)

    def test_automatic_mode_tracks_system_color_changes(self):
        self.assertIn("matchMedia('(prefers-color-scheme: light)')", self.app)
        self.assertIn("systemColorScheme.addEventListener('change'", self.app)
        self.assertIn("selected === 'auto'", self.app)

    def test_appearance_strings_are_translated_in_all_languages(self):
        segment = self.app.split(
            "const APPEARANCE_TRANSLATIONS = {", 1
        )[1].split("Object.entries(APPEARANCE_TRANSLATIONS)", 1)[0]
        keys = (
            "settings_appearance_title",
            "settings_appearance_description",
            "appearance_liquid",
            "appearance_liquid_description",
            "appearance_standard",
            "appearance_standard_description",
            "appearance_auto",
            "appearance_auto_description",
            "reduce_transparency",
            "reduce_transparency_description",
        )
        for key in keys:
            self.assertEqual(
                len(re.findall(rf"\b{re.escape(key)}\s*:", segment)),
                6,
                key,
            )

    def test_liquid_css_has_performance_and_accessibility_fallbacks(self):
        self.assertIn("backdrop-filter:", self.liquid)
        self.assertIn("@supports not", self.liquid)
        self.assertIn('[data-reduce-transparency="true"]', self.liquid)
        self.assertIn("@media (prefers-reduced-motion: reduce)", self.liquid)
        for width in (1440, 768, 431):
            self.assertIn(f"@media (max-width: {width}px)", self.liquid)
        self.assertIn("--lg-blur-shell: 6px", self.liquid)
        self.assertIn("--lg-panel-dense", self.liquid)


if __name__ == "__main__":
    unittest.main()
