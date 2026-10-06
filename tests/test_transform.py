"""Corners scale from the opposite side. The inside of the box moves the layer."""

import os
import unittest

from sinopia.document import Document, Layer
from sinopia.image import Image
from sinopia.stage import Stage

RED = (180, 24, 24, 255)


def _block() -> Image:
    image = Image(4, 4)
    for y in range(2):
        for x in range(2):
            image.set(x, y, RED)
    return image


class TransformTest(unittest.TestCase):
    def test_the_opposite_corner_stays_put(self):
        image = _block()
        stage = Stage(Document(4, 4, [Layer("red", image)]))
        self.assertEqual(stage.content_box(), (0, 0, 2, 2))
        stage.transform_press("se", 2, 2)
        stage.transform_release(4, 4)
        self.assertEqual(image.get(0, 0), RED)
        self.assertEqual(image.get(3, 3), RED)
        self.assertEqual(image.get(3, 0), RED)
        self.assertEqual(stage.content_box(), (0, 0, 4, 4))

    def test_an_edge_scales_one_side(self):
        image = _block()
        stage = Stage(Document(4, 4, [Layer("red", image)]))
        stage.transform_press("e", 2, 1)
        stage.transform_release(4, 1)
        self.assertEqual(image.get(3, 0), RED)
        self.assertEqual(image.get(0, 2), (0, 0, 0, 0))
        self.assertEqual(stage.content_box(), (0, 0, 4, 2))

    def test_dragging_inside_moves_the_layer(self):
        image = _block()
        layer = Layer("red", image)
        stage = Stage(Document(4, 4, [layer]))
        before = bytes(image.pixels)
        stage.transform_press("move", 1, 1)
        stage.transform_release(3, 2)
        self.assertEqual(layer.x, 2)
        self.assertEqual(layer.y, 1)
        self.assertEqual(bytes(image.pixels), before)
        self.assertEqual(stage.content_box(), (2, 1, 4, 3))

    def test_shift_keeps_the_proportions(self):
        image = _block()
        stage = Stage(Document(4, 4, [Layer("red", image)]))
        stage.transform_press("se", 2, 2)
        stage.transform_release(4, 3, constrain=True)
        self.assertEqual(stage.content_box(), (0, 0, 4, 4))


@unittest.skipUnless(os.environ.get("DISPLAY"), "no display")
class TransformHandlesTest(unittest.TestCase):
    def test_the_corner_handle_is_drawn_on_the_picture(self):
        from sinopia.proof import proof_document
        from sinopia.window import Window

        window = Window(Stage(proof_document()))
        try:
            window.set_tool("transform")
            window.root.update()
            self.assertEqual(window.photo.get(4, 4), (255, 255, 255))
            self.assertEqual(window._hit_handle(0, 0), "nw")
        finally:
            window.root.destroy()
