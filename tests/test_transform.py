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

    def test_a_turn_spins_around_the_cross(self):
        image = Image(8, 8)
        image.set(1, 1, RED)
        stage = Stage(Document(8, 8, [Layer("red", image)]))
        stage._pivot = (2, 2)
        stage._pivot_custom = True
        stage.rotate_by(180)
        self.assertEqual(image.get(1, 1)[3], 0)
        self.assertEqual(image.get(2, 2), RED)

    def test_a_quarter_turn_swaps_the_sides(self):
        image = Image(8, 8)
        for y in range(3, 5):
            for x in range(2, 6):
                image.set(x, y, RED)
        stage = Stage(Document(8, 8, [Layer("red", image)]))
        stage.rotate_by(90)
        left, top, right, bottom = stage.content_box()
        self.assertGreater(bottom - top, right - left)

    def test_the_box_stays_tilted_until_enter(self):
        image = Image(8, 8)
        for y in range(3, 5):
            for x in range(2, 6):
                image.set(x, y, RED)
        stage = Stage(Document(8, 8, [Layer("red", image)]))
        stage.rotate_by(90)
        start, end = stage.frame_corners()[0], stage.frame_corners()[1]
        self.assertGreater(abs(end[1] - start[1]), abs(end[0] - start[0]))
        stage.transform_commit()
        start, end = stage.frame_corners()[0], stage.frame_corners()[1]
        self.assertGreater(abs(end[0] - start[0]), abs(end[1] - start[1]))

    def test_escape_after_letting_go_puts_the_pixels_back(self):
        image = _block()
        stage = Stage(Document(4, 4, [Layer("red", image)]))
        before = bytes(image.pixels)
        stage.transform_press("se", 2, 2)
        stage.transform_release(4, 4)
        stage.transform_cancel()
        self.assertEqual(bytes(image.pixels), before)

    def test_escape_puts_the_pixels_back(self):
        image = _block()
        stage = Stage(Document(4, 4, [Layer("red", image)]))
        before = bytes(image.pixels)
        stage.transform_press("se", 2, 2)
        stage.transform_drag(4, 4)
        stage.transform_cancel()
        self.assertEqual(bytes(image.pixels), before)
        self.assertEqual(stage.content_box(), (0, 0, 2, 2))


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
            self.assertEqual(window._transform_handle(-30, -30), "rotate")
            self.assertTrue(window._hit_pivot(48, 48))
        finally:
            window.root.destroy()
