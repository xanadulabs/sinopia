"""A marquee copies its pixels, and New can use that size."""

import os
import unittest

from sinopia.image import Image
from sinopia.proof import proof_document
from sinopia.select import clear_copied, copied_image, copy_pixels, crop, marquee_box
from sinopia.stage import Stage


class MarqueeTest(unittest.TestCase):
    def test_a_drag_includes_both_corners_and_shift_keeps_a_square(self):
        self.assertIsNone(marquee_box((2, 2), (2, 2), False, 96, 96))
        self.assertEqual(marquee_box((2, 2), (6, 4), False, 96, 96), (2, 2, 7, 5))
        self.assertEqual(marquee_box((0, 0), (2, 5), True, 96, 96), (0, 0, 6, 6))

    def test_crop_keeps_only_the_rectangle(self):
        image = Image(4, 3, (180, 24, 24, 255))
        image.set(1, 1, (32, 140, 64, 255))
        piece = crop(image, (1, 1, 3, 2))
        self.assertEqual((piece.width, piece.height), (2, 1))
        self.assertEqual(piece.get(0, 0), (32, 140, 64, 255))


@unittest.skipUnless(os.environ.get("DISPLAY"), "no display")
class SelectWindowTest(unittest.TestCase):
    def test_copy_then_new_uses_the_clipboard_size_or_a_typed_size(self):
        from sinopia.picker import SizeDialog
        from sinopia.window import Window

        window = Window(Stage(proof_document()))
        try:
            window.root.update()
            window.set_tool("select")
            window._press(_Click(16, 16))
            window._release(_Click(48, 32))
            self.assertEqual(window.marquee, (2, 2, 7, 5))
            window._copy()
            copied = copied_image()
            self.assertIsNotNone(copied)
            assert copied is not None
            self.assertEqual((copied.width, copied.height), (5, 3))
            dialog = SizeDialog(window.root, (96, 96), (copied.width, copied.height))
            window.root.update()
            self.assertEqual(dialog.width_var.get(), "5")
            self.assertEqual(dialog.height_var.get(), "3")
            self.assertIn("Clipboard", dialog.note.cget("text"))
            dialog.width_var.set("20")
            dialog.height_var.set("8")
            dialog._accept()
            self.assertEqual(dialog.chosen, (20, 8))
            window._apply_new(20, 8)
            self.assertEqual((window.stage.document.width, window.stage.document.height), (20, 8))
            self.assertEqual(window.stage.picture.get(0, 0), (255, 255, 255, 255))
            self.assertEqual(window.history_list.get(1), "New")
            self.assertIsNone(window.marquee)
        finally:
            clear_copied()
            window.root.destroy()


class _Click:
    def __init__(self, x: int, y: int, state: int = 0):
        self.x = x
        self.y = y
        self.state = state
