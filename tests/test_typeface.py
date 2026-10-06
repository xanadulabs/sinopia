"""Font, size, italic, strike, kerning, and stroke. The built-in face stays exact at 7px."""

import os
import unittest

from sinopia.brush import BLACK
from sinopia.glyphs import ADVANCE
from sinopia.image import Image
from sinopia.lettering import place
from sinopia.typeface import TextStyle, font_families, place_text

GREEN = (32, 140, 64, 255)
RED = (180, 24, 24, 255)


def _ink(image: Image, color: tuple[int, int, int, int] | None = None) -> list[tuple[int, int]]:
    found = []
    for y in range(image.height):
        for x in range(image.width):
            pixel = image.get(x, y)
            if color is None and pixel != GREEN:
                found.append((x, y))
            elif color is not None and pixel[:3] == color[:3]:
                found.append((x, y))
    return found


class BitmapStyleTest(unittest.TestCase):
    def test_default_style_matches_the_five_by_seven_face(self):
        image = Image(12, 7, GREEN)
        place(image, 0, 0, "H", BLACK)
        self.assertEqual(image.get(0, 0), BLACK)
        self.assertEqual(image.get(1, 0), GREEN)

    def test_points_scale_the_face_at_96_dpi(self):
        image = Image(24, 20, GREEN)
        place_text(image, 0, 0, "H", BLACK, TextStyle(size=12, unit="pt"))
        self.assertEqual(image.get(0, 0), BLACK)
        self.assertEqual(image.get(0, 13), BLACK)
        self.assertEqual(image.get(0, 14), GREEN)

    def test_italic_shears_the_top_and_strike_crosses_the_gap(self):
        image = Image(16, 16, GREEN)
        place_text(image, 0, 0, "H", BLACK, TextStyle(italic=True, strikethrough=True))
        self.assertEqual(image.get(0, 0), GREEN)
        self.assertEqual(image.get(3, 0), BLACK)
        self.assertEqual(image.get(5, 3), BLACK)

    def test_kerning_opens_a_gap_and_stroke_outlines_the_fill(self):
        image = Image(24, 12, GREEN)
        place_text(image, 0, 2, "HI", BLACK, TextStyle(kerning=3))
        self.assertEqual(image.get(ADVANCE + 1, 2), GREEN)
        self.assertEqual(image.get(ADVANCE + 3 + 1, 2), BLACK)
        outlined = Image(12, 12, GREEN)
        place_text(outlined, 2, 2, "H", RED, TextStyle(stroke=1))
        self.assertEqual(outlined.get(2, 2), RED)
        self.assertEqual(outlined.get(3, 2), BLACK)

    def test_a_system_face_kerns_and_accepts_italic(self):
        if "DejaVu Sans" not in font_families():
            self.skipTest("DejaVu Sans is not installed")
        plain = Image(80, 40, GREEN)
        loose = Image(80, 40, GREEN)
        place_text(plain, 0, 0, "HI", BLACK, TextStyle(family="DejaVu Sans", size=16))
        place_text(loose, 0, 0, "HI", BLACK, TextStyle(family="DejaVu Sans", size=16, kerning=8, italic=True))
        plain_right = max(x for x, _y in _ink(plain))
        loose_right = max(x for x, _y in _ink(loose))
        self.assertGreater(loose_right, plain_right)


@unittest.skipUnless(os.environ.get("DISPLAY"), "no display")
class TypeBarTest(unittest.TestCase):
    def test_the_bar_follows_the_tool(self):
        from sinopia.proof import proof_document
        from sinopia.stage import Stage
        from sinopia.window import Window

        stage = Stage(proof_document())
        window = Window(stage)
        try:
            window.root.update()
            self.assertEqual(window.options.winfo_children()[0].cget("text"), "Move")
            window.set_tool("brush")
            window._radius_var.set(5)
            window._apply_brush()
            self.assertEqual(stage.radius, 5)
            window.set_tool("type")
            window._size_var.set(14)
            window._italic_var.set(1)
            window._kerning_var.set(2)
            window._stroke_var.set(1)
            window._apply_type()
            self.assertEqual(stage.lettering.style.size, 14)
            self.assertTrue(stage.lettering.style.italic)
            self.assertEqual(stage.lettering.style.kerning, 2)
            self.assertEqual(stage.lettering.style.stroke, 1)
            self.assertIn("DejaVu Sans", font_families())
        finally:
            window.root.destroy()
