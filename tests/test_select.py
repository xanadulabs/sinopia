"""A marquee copies its pixels, and New can use that size."""

import os
import unittest

from sinopia.clipboard import clear_system, clipboard_picture, publish_image, system_image
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
            step = window.scale
            window._press(_Click(2 * step, 2 * step))
            window._release(_Click(6 * step, 4 * step))
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
            window._apply_new(copied.width, copied.height, copied)
            self.assertEqual(window.stage.picture.get(0, 0), copied.get(0, 0))
            window._apply_new(20, 8)
            self.assertEqual((window.stage.document.width, window.stage.document.height), (20, 8))
            self.assertEqual(window.stage.picture.get(0, 0), (255, 255, 255, 255))
            self.assertEqual(window.history_list.get(1), "New")
            self.assertIsNone(window.marquee)
        finally:
            clear_copied()
            window.root.destroy()


@unittest.skipUnless(os.environ.get("DISPLAY"), "no display")
class DesktopClipboardTest(unittest.TestCase):
    def test_a_picture_on_the_desktop_clipboard_supplies_the_size(self):
        before = system_image()
        try:
            publish_image(Image(6, 4, (180, 24, 24, 255)))
            found = clipboard_picture()
            self.assertIsNotNone(found)
            assert found is not None
            self.assertEqual((found.width, found.height), (6, 4))
            self.assertEqual(found.get(0, 0), (180, 24, 24, 255))
        finally:
            if before is not None:
                publish_image(before)
            else:
                clear_system()


class _Click:
    def __init__(self, x: int, y: int, state: int = 0):
        self.x = x
        self.y = y
        self.state = state
