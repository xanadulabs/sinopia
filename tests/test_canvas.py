"""Canvas Size adds empty pixels on the sides you choose."""

import os
import unittest

from sinopia.canvas import placement, resize_canvas
from sinopia.document import Document, Layer
from sinopia.image import Image

RED = (180, 24, 24, 255)


class PlacementTest(unittest.TestCase):
    def test_the_picture_stays_on_the_selected_square(self):
        self.assertEqual(placement(4, 2, "nw"), (0, 4, 0, 2))
        self.assertEqual(placement(4, 2, "w"), (0, 4, 1, 1))
        self.assertEqual(placement(4, 0, "e"), (4, 0, 0, 0))
        self.assertEqual(placement(5, 1, "c"), (2, 3, 0, 1))
        self.assertEqual(placement(3, 4, "se"), (3, 0, 4, 0))


class ResizeCanvasTest(unittest.TestCase):
    def test_growth_to_the_right_keeps_the_old_pixel_and_leaves_the_new_one_empty(self):
        image = Image(2, 2, RED)
        mask = bytearray(b"\xff\xff\xff\xff")
        document = Document(2, 2, [Layer("red", image, mask)])
        resize_canvas(document, 2, 0, "w")
        self.assertEqual((document.width, document.height), (4, 2))
        layer = document.layers[0]
        self.assertEqual(layer.image.get(0, 0), RED)
        self.assertEqual(layer.image.get(3, 0), (0, 0, 0, 0))
        self.assertEqual(layer.mask[0], 255)
        self.assertEqual(layer.mask[-1], 0)


@unittest.skipUnless(os.environ.get("DISPLAY"), "no display")
class CanvasDialogTest(unittest.TestCase):
    def test_the_dialog_reports_the_added_pixels_and_the_square(self):
        from sinopia.picker import CanvasDialog
        from sinopia.proof import proof_document
        from sinopia.stage import Stage
        from sinopia.window import Window

        window = Window(Stage(proof_document()))
        try:
            dialog = CanvasDialog(window.root, 96, 64)
            window.root.update()
            self.assertEqual(dialog.note.cget("text"), "New size 96 × 64")
            dialog.width_var.set("10")
            dialog._pick("e")
            self.assertEqual(dialog.note.cget("text"), "New size 106 × 64")
            dialog._accept()
            self.assertEqual(dialog.chosen, (10, 0, "e"))
        finally:
            window.root.destroy()
