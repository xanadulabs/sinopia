"""Dragging a layer moves the composite, and the window paints those same pixels."""

import os
import unittest

from sinopia.document import Document, Layer, flatten, load, save
from sinopia.image import Image
from sinopia.proof import SIZE, proof_document
from sinopia.stage import Stage, scaled_rgb

RED = (180, 24, 24, 255)
GREEN = (32, 140, 64, 255)


class StageTest(unittest.TestCase):
    def test_unmoved_picture_matches_the_flatten(self):
        document = proof_document()
        stage = Stage(document)
        self.assertEqual(stage.picture.pixels, flatten(document).pixels)
        self.assertEqual(stage.picture.get(0, 0), RED)
        self.assertEqual(stage.picture.get(SIZE // 2, SIZE // 2), GREEN)

    def test_drag_shifts_the_top_layer(self):
        red = Image(2, 2, RED)
        green = Image(2, 2, GREEN)
        document = Document(2, 2, [Layer("red", red), Layer("green", green)])
        stage = Stage(document)
        stage.press(0, 0)
        stage.drag(1, 0)
        self.assertEqual(stage.layer.x, 1)
        self.assertEqual(stage.picture.get(0, 0), RED)
        self.assertEqual(stage.picture.get(1, 0), GREEN)
        stage.release(1, 0)
        self.assertEqual(stage.picture.pixels, flatten(document).pixels)

    def test_drag_moves_the_proof_disk(self):
        document = proof_document()
        stage = Stage(document)
        stage.press(0, 0)
        stage.release(40, 0)
        self.assertEqual(stage.picture.get(SIZE // 2, SIZE // 2), RED)
        self.assertEqual(stage.picture.get(SIZE // 2 + 40, SIZE // 2), GREEN)

    def test_position_round_trips_through_the_folder(self):
        document = proof_document()
        document.layers[1].x = 12
        document.layers[1].y = -3
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            save(document, folder)
            text = (folder / "stack.txt").read_text(encoding="utf-8")
            self.assertIn("green.mask.png 12 -3", text)
            opened = load(folder)
        self.assertEqual((opened.layers[1].x, opened.layers[1].y), (12, -3))
        self.assertEqual(flatten(opened).pixels, flatten(document).pixels)

    def test_scaled_rows_repeat_each_pixel(self):
        image = Image(1, 1, GREEN)
        rows = scaled_rgb(image, 2)
        self.assertEqual(rows, ["#208c40 #208c40", "#208c40 #208c40"])


@unittest.skipUnless(os.environ.get("DISPLAY"), "no display")
class WindowPixelsTest(unittest.TestCase):
    def test_window_pixel_matches_the_composite(self):
        import tkinter

        from sinopia.window import SCALE, Window

        document = proof_document()
        stage = Stage(document)
        window = Window(stage)
        window.root.update()
        mid = SIZE // 2 * SCALE
        corner = _rgb(window.photo.get(0, 0))
        center = _rgb(window.photo.get(mid, mid))
        window.root.destroy()
        self.assertEqual(corner, RED[:3])
        self.assertEqual(center, GREEN[:3])


def _rgb(value) -> tuple[int, int, int]:
    if isinstance(value, tuple):
        return tuple(int(part) for part in value[:3])
    if value.startswith("#"):
        return tuple(int(value[i : i + 2], 16) for i in (1, 3, 5))
    return tuple(int(part) for part in value.split())
