"""The clay-tablet mark is the icon, the shortcut file, and the About picture."""

import os
import unittest
from pathlib import Path

from sinopia.image import Image
from sinopia.mark import LINE, LINE_DEEP, SHORTCUT_ZOOM, scaled, tablet
from sinopia.png import read_png

ROOT = Path(__file__).resolve().parents[1]
SHORTCUT = ROOT / "sinopia.png"


class MarkTest(unittest.TestCase):
    def test_the_shard_carries_a_sinopia_drawing(self):
        image = tablet()
        colors = _colors(image)
        self.assertEqual(image.get(0, 0)[3], 0)
        self.assertEqual(image.get(image.width - 1, image.height - 1)[3], 0)
        self.assertIn(LINE, colors)
        self.assertIn(LINE_DEEP, colors)
        self.assertTrue(any(pixel[3] == 255 and pixel[1] > 120 and pixel not in (LINE, LINE_DEEP) for pixel in colors))

    def test_shortcut_file_is_the_same_tablet_zoomed(self):
        saved = read_png(SHORTCUT)
        mark = scaled(tablet(), SHORTCUT_ZOOM)
        self.assertEqual((saved.width, saved.height), (mark.width, mark.height))
        self.assertEqual(saved.get(0, 0), mark.get(0, 0))
        self.assertEqual(saved.get(12 * SHORTCUT_ZOOM, 8 * SHORTCUT_ZOOM), mark.get(12 * SHORTCUT_ZOOM, 8 * SHORTCUT_ZOOM))

    def test_about_puts_the_mark_beside_the_name(self):
        if not os.environ.get("DISPLAY"):
            self.skipTest("no display")
        import tkinter

        from sinopia.proof import proof_document
        from sinopia.stage import Stage
        from sinopia.window import Window

        window = Window(Stage(proof_document()))
        try:
            dialog = window._about()
            window.root.update()
            texts = [widget.cget("text") for widget in _labels(dialog)]
            images = [widget.cget("image") for widget in _labels(dialog)]
            self.assertIn("Copyright 2026 Will Hinds\nApache License 2.0", texts)
            self.assertTrue(any(images))
            self.assertEqual(len(window._icons), 3)
        finally:
            window.root.destroy()


def _colors(image: Image) -> set[tuple[int, int, int, int]]:
    found = set()
    for y in range(image.height):
        for x in range(image.width):
            found.add(image.get(x, y))
    return found


def _labels(widget):
    import tkinter

    found = []
    for child in widget.winfo_children():
        if isinstance(child, tkinter.Label):
            found.append(child)
        found.extend(_labels(child))
    return found


if __name__ == "__main__":
    unittest.main()
