"""The clay-tablet mark is the icon, the shortcut file, and the About picture."""

import os
import unittest
from pathlib import Path

from sinopia.image import Image
from sinopia.mark import SHORTCUT_ZOOM, tablet
from sinopia.png import read_png
from sinopia.mark import scaled

ROOT = Path(__file__).resolve().parents[1]
SHORTCUT = ROOT / "sinopia.png"
SINOPIA = (176, 52, 34, 255)
GREEN = (32, 132, 62, 255)


class MarkTest(unittest.TestCase):
    def test_the_tablet_is_broken_and_carries_the_proof(self):
        image = tablet()
        self.assertEqual(image.get(0, 0)[3], 0)
        self.assertEqual(image.get(image.width - 1, image.height - 1)[3], 0)
        self.assertIn(SINOPIA, _colors(image))
        self.assertIn(GREEN, _colors(image))
        self.assertTrue(any(pixel[3] == 255 and pixel[0] > 180 and pixel[1] > 140 for pixel in _colors(image)))

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
            self.assertIn("Will Hinds, 2026", texts)
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
