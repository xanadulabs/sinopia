"""The brush paints one layer. The composite, and the window, show those pixels."""

import os
import tempfile
import unittest
from pathlib import Path

from sinopia.brush import BLACK, dab, line, stamp, tip_offsets
from sinopia.document import Document, Layer, flatten, load, save
from sinopia.image import Image
from sinopia.proof import SIZE, proof_document
from sinopia.stage import Stage

RED = (180, 24, 24, 255)
GREEN = (32, 140, 64, 255)


class BrushTest(unittest.TestCase):
    def test_one_pixel_replaces_the_layer_and_the_composite(self):
        document = proof_document()
        stage = Stage(document)
        stage.radius = 0
        stage.brush_press(SIZE // 2, SIZE // 2)
        stage.brush_release(SIZE // 2, SIZE // 2)
        self.assertEqual(stage.layer.image.get(SIZE // 2, SIZE // 2), BLACK)
        self.assertEqual(stage.picture.get(SIZE // 2, SIZE // 2), BLACK)
        self.assertEqual(stage.picture.get(0, 0), RED)
        self.assertEqual(stage.picture.pixels, flatten(document).pixels)

    def test_a_stroke_fills_the_pixels_between_the_ends(self):
        image = Image(4, 1, GREEN)
        document = Document(4, 1, [Layer("green", image)])
        stage = Stage(document)
        stage.radius = 0
        stage.brush_press(0, 0)
        stage.brush_drag(3, 0)
        stage.brush_release(3, 0)
        for x in range(4):
            self.assertEqual(image.get(x, 0), BLACK)

    def test_radius_skips_the_diagonal_corners(self):
        image = Image(3, 3, GREEN)
        stamp(image, 1, 1, BLACK, 1)
        self.assertEqual(image.get(1, 0), BLACK)
        self.assertEqual(image.get(0, 0), GREEN)

    def test_mask_hides_paint_on_the_layer(self):
        red = Image(1, 1, RED)
        green = Image(1, 1, GREEN)
        document = Document(1, 1, [Layer("red", red), Layer("green", green, bytearray(b"\x00"))])
        stage = Stage(document)
        stage.radius = 0
        stage.brush_press(0, 0)
        self.assertEqual(stage.layer.image.get(0, 0), BLACK)
        self.assertEqual(red.get(0, 0), RED)
        self.assertEqual(stage.picture.get(0, 0), RED)

    def test_paint_follows_a_moved_layer(self):
        image = Image(2, 1, GREEN)
        document = Document(2, 1, [Layer("green", image, x=1)])
        stage = Stage(document)
        stage.radius = 0
        stage.brush_press(1, 0)
        self.assertEqual(image.get(0, 0), BLACK)
        self.assertEqual(image.get(1, 0), GREEN)

    def test_painted_pixels_round_trip_through_the_folder(self):
        document = proof_document()
        stage = Stage(document)
        stage.radius = 0
        stage.brush_press(4, 4)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            save(document, folder)
            opened = load(folder)
        self.assertEqual(opened.layers[1].image.get(4, 4), BLACK)
        self.assertEqual(flatten(opened).pixels, stage.picture.pixels)

    def test_line_includes_both_ends(self):
        self.assertEqual(line((0, 0), (0, 2)), [(0, 0), (0, 1), (0, 2)])

    def test_a_hard_full_brush_matches_the_old_circle(self):
        painted = Image(5, 5, GREEN)
        expected = Image(5, 5, GREEN)
        stamp(expected, 2, 2, BLACK, 2)
        document = Document(5, 5, [Layer("green", painted)])
        stage = Stage(document)
        stage.diameter = 5
        stage.brush_press(2, 2)
        stage.brush_release(2, 2)
        self.assertEqual(painted.pixels, expected.pixels)

    def test_hardness_feathers_the_edge(self):
        image = Image(5, 5, GREEN)
        document = Document(5, 5, [Layer("green", image)])
        stage = Stage(document)
        stage.diameter = 5
        stage.hardness = 0
        stage.brush_press(2, 2)
        stage.brush_release(2, 2)
        self.assertEqual(image.get(2, 2), BLACK)
        self.assertNotEqual(image.get(3, 2), BLACK)
        self.assertNotEqual(image.get(3, 2), GREEN)
        self.assertLess(image.get(3, 2)[1], GREEN[1])
        self.assertEqual(image.get(0, 0), GREEN)

    def test_flow_builds_until_opacity_stops_it(self):
        image = Image(1, 1, GREEN)
        origin = bytes(image.pixels)
        coverage = bytearray(1)
        offsets = tip_offsets(1, 100)
        dab(image, 0, 0, BLACK, offsets, 40, 100, origin, coverage)
        once = image.get(0, 0)
        dab(image, 0, 0, BLACK, offsets, 40, 100, origin, coverage)
        twice = image.get(0, 0)
        self.assertNotEqual(once, GREEN)
        self.assertNotEqual(once, BLACK)
        self.assertLess(twice[1], once[1])
        dab(image, 0, 0, BLACK, offsets, 40, 100, origin, coverage)
        self.assertEqual(image.get(0, 0), BLACK)

        capped = Image(1, 1, GREEN)
        cap_origin = bytes(capped.pixels)
        cap_coverage = bytearray(1)
        dab(capped, 0, 0, BLACK, offsets, 100, 40, cap_origin, cap_coverage)
        held = capped.get(0, 0)
        dab(capped, 0, 0, BLACK, offsets, 100, 40, cap_origin, cap_coverage)
        self.assertEqual(capped.get(0, 0), held)
        self.assertNotEqual(held, BLACK)
        self.assertNotEqual(held, GREEN)

    def test_a_hard_stroke_stays_solid_between_dabs(self):
        image = Image(16, 5, GREEN)
        document = Document(16, 5, [Layer("green", image)])
        stage = Stage(document)
        stage.diameter = 5
        stage.brush_press(2, 2)
        stage.brush_drag(12, 2)
        stage.brush_release(12, 2)
        for x in range(4, 11):
            self.assertEqual(image.get(x, 2), BLACK, x)


@unittest.skipUnless(os.environ.get("DISPLAY"), "no display")
class BrushWindowTest(unittest.TestCase):
    def test_brush_key_paints_the_center_black(self):
        from sinopia.window import SCALE, Window

        document = proof_document()
        stage = Stage(document)
        stage.radius = 0
        window = Window(stage)
        window.root.update()
        window._key(_Event(char="b"))
        mid = SIZE // 2 * SCALE + SCALE // 2
        window._press(_Event(x=mid, y=mid))
        window._release(_Event(x=mid, y=mid))
        window.root.update()
        center = _rgb(window.photo.get(mid, mid))
        corner = _rgb(window.photo.get(0, 0))
        window.root.destroy()
        self.assertEqual(window.tool, "brush")
        self.assertEqual(center, BLACK[:3])
        self.assertEqual(corner, RED[:3])


class _Event:
    def __init__(self, x: int = 0, y: int = 0, char: str = ""):
        self.x = x
        self.y = y
        self.char = char


def _rgb(value) -> tuple[int, int, int]:
    if isinstance(value, tuple):
        return tuple(int(part) for part in value[:3])
    if str(value).startswith("#"):
        text = str(value)
        return tuple(int(text[i : i + 2], 16) for i in (1, 3, 5))
    return tuple(int(part) for part in str(value).split())
