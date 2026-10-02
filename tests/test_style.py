"""A drop shadow is a shifted black copy of what the layer actually shows."""

import tempfile
import unittest
from pathlib import Path

from sinopia.document import Document, Layer, flatten, load, save
from sinopia.image import Image

RED = (180, 24, 24, 255)
GREEN = (32, 140, 64, 255)
BLACK = (0, 0, 0, 255)


def _dot() -> Image:
    image = Image(2, 1)
    image.set(0, 0, GREEN)
    return image


class ShadowTest(unittest.TestCase):
    def test_shadow_sits_beside_the_visible_pixel(self):
        red = Image(2, 1, RED)
        document = Document(2, 1, [Layer("red", red), Layer("green", _dot(), shadow=(1, 0))])
        image = flatten(document)
        self.assertEqual(image.get(0, 0), GREEN)
        self.assertEqual(image.get(1, 0), BLACK)

    def test_a_clear_mask_casts_no_shadow(self):
        red = Image(2, 1, RED)
        mask = bytearray(b"\x00\x00")
        document = Document(2, 1, [Layer("red", red), Layer("green", _dot(), mask, shadow=(1, 0))])
        image = flatten(document)
        self.assertEqual(image.get(0, 0), RED)
        self.assertEqual(image.get(1, 0), RED)

    def test_shadow_round_trips_through_the_folder(self):
        document = Document(2, 1, [Layer("green", _dot(), shadow=(1, 0))])
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            save(document, folder)
            text = (folder / "stack.txt").read_text(encoding="utf-8")
            self.assertIn("shadow 1 0", text)
            opened = load(folder)
        self.assertEqual(opened.layers[0].shadow, (1, 0))
        self.assertEqual(flatten(opened).pixels, flatten(document).pixels)
