"""Unit tests for brand character SVG."""

import unittest

from components.brand_character import render_celebration_scene, render_character_svg


class TestBrandCharacter(unittest.TestCase):
    def test_default_variant(self):
        svg = render_character_svg("default", 92)
        self.assertIn('width="92"', svg)
        self.assertIn('viewBox="0 0 120 120"', svg)
        self.assertIn('cx="50" cy="55"', svg)
        self.assertIn('M35 59 Q42 71 52 72', svg)
        self.assertNotIn('M46 55 Q50 51 54 55', svg)

    def test_custom_bg(self):
        svg = render_character_svg("default", 92, bg="#ffffff")
        self.assertIn('fill="#ffffff"', svg)

    def test_listening_variant(self):
        svg = render_character_svg("listening", 84)
        self.assertIn('width="84"', svg)
        self.assertIn('M46 55 Q50 51 54 55', svg)
        self.assertIn('cx="87" cy="53"', svg)
        self.assertNotIn('M35 59 Q42 71 52 72', svg)

    def test_celebration_scene(self):
        svg = render_celebration_scene(240)
        self.assertIn('viewBox="0 0 240 120"', svg)
        self.assertIn('cx="120" cy="62" r="52"', svg)
        self.assertIn('M110 63 Q120 74 130 63 Z', svg)
        self.assertIn('fill="#534AB7"', svg)
        self.assertIn('transform="rotate(18 22 57.5)"', svg)

    def test_sorry_variant(self):
        svg = render_character_svg("sorry", 96, bg="#ffffff")
        self.assertIn('width="96"', svg)
        self.assertIn('fill="#ffffff"', svg)
        self.assertIn('M44 47 Q49 44 54 47', svg)
        self.assertIn('r="2.8"', svg)
        self.assertIn('M91 40 Q97 48 91 52 Q85 48 91 40 Z', svg)
        self.assertIn('opacity="0.7"', svg)


if __name__ == "__main__":
    unittest.main()
