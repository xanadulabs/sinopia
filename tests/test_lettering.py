"""Type previews on the composite, then Enter bakes the letters into the layer."""

import os
import unittest

from sinopia.brush import BLACK
from sinopia.document import Document, Layer
from sinopia.glyphs import ADVANCE
from sinopia.image import Image
from sinopia.lettering import place
from sinopia.proof import SIZE, proof_document
from sinopia.stage import Stage

GREEN = (32, 140, 64, 255)
RED = (180, 24, 24, 255)


class LetteringTest(unittest.TestCase):
    def test_h_paints_its_stems_and_leaves_the_gap(self):
        image = Image(12, 7, GREEN)
        place(image, 0, 0, "H", BLACK)
        self.assertEqual(image.get(0, 0), BLACK)
        self.assertEqual(image.get(1, 0), GREEN)
        self.assertEqual(image.get(4, 0), BLACK)

    def test_a_second_letter_starts_after_the_first_cell(self):
        image = Image(12, 7, GREEN)
        place(image, 0, 0, "HI", BLACK)
        self.assertEqual(image.get(ADVANCE, 0), GREEN)
        self.assertEqual(image.get(ADVANCE + 1, 0), BLACK)

    def test_preview_shows_the_letter_without_changing_the_layer(self):
        document = proof_document()
        stage = Stage(document)
        before = bytes(stage.layer.image.pixels)
        stage.lettering.begin(SIZE // 2, SIZE // 2)
        stage.lettering.insert("h")
        self.assertEqual(stage.lettering.text, "h")
        self.assertEqual(stage.picture.get(SIZE // 2, SIZE // 2), BLACK)
        self.assertEqual(bytes(stage.layer.image.pixels), before)

    def test_enter_bakes_the_letter_and_backspace_only_changes_the_preview(self):
        document = proof_document()
        stage = Stage(document)
        stage.lettering.begin(SIZE // 2, SIZE // 2)
        stage.lettering.insert("H")
        stage.lettering.insert("I")
        stage.lettering.backspace()
        self.assertEqual(stage.lettering.text, "H")
        self.assertEqual(stage.picture.get(SIZE // 2 + ADVANCE, SIZE // 2), GREEN)
        stage.lettering.commit()
        self.assertFalse(stage.lettering.active)
        self.assertEqual(stage.layer.image.get(SIZE // 2, SIZE // 2), BLACK)
        self.assertEqual(stage.picture.get(SIZE // 2, SIZE // 2), BLACK)

    def test_escape_drops_the_preview(self):
        document = proof_document()
        stage = Stage(document)
        stage.lettering.begin(SIZE // 2, SIZE // 2)
        stage.lettering.insert("H")
        stage.lettering.cancel()
        self.assertEqual(stage.picture.get(SIZE // 2, SIZE // 2), GREEN)
        self.assertEqual(stage.layer.image.get(SIZE // 2, SIZE // 2), GREEN)

    def test_the_mask_hides_type_the_same_way_it_hides_paint(self):
        red = Image(5, 7, RED)
        green = Image(5, 7, GREEN)
        mask = bytearray(5 * 7)
        document = Document(5, 7, [Layer("red", red), Layer("green", green, mask)])
        stage = Stage(document)
        stage.lettering.begin(0, 0)
        stage.lettering.insert("H")
        stage.lettering.commit()
        self.assertEqual(stage.layer.image.get(0, 0), BLACK)
        self.assertEqual(stage.picture.get(0, 0), RED)

    def test_unknown_keys_are_ignored(self):
        stage = Stage(proof_document())
        stage.lettering.begin(0, 0)
        stage.lettering.insert("!")
        self.assertEqual(stage.lettering.text, "")


@unittest.skipUnless(os.environ.get("DISPLAY"), "no display")
class TypeWindowTest(unittest.TestCase):
    def test_typing_h_shows_black_until_enter_bakes_it(self):
        from sinopia.window import SCALE, Window

        document = proof_document()
        stage = Stage(document)
        window = Window(stage)
        window.root.update()
        window._key(_Event(char="t", keysym="t"))
        origin = SIZE // 2 * SCALE
        window._press(_Event(x=origin, y=origin))
        window._key(_Event(char="H", keysym="H"))
        window.root.update()
        shown = _rgb(window.photo.get(origin, origin))
        self.assertEqual(shown, BLACK[:3])
        self.assertEqual(stage.layer.image.get(SIZE // 2, SIZE // 2), GREEN)
        window._key(_Event(char="\r", keysym="Return"))
        window.root.update()
        baked = _rgb(window.photo.get(origin, origin))
        window.root.destroy()
        self.assertEqual(baked, BLACK[:3])
        self.assertEqual(stage.layer.image.get(SIZE // 2, SIZE // 2), BLACK)


class _Event:
    def __init__(self, x: int = 0, y: int = 0, char: str = "", keysym: str = ""):
        self.x = x
        self.y = y
        self.char = char
        self.keysym = keysym


def _rgb(value) -> tuple[int, int, int]:
    if isinstance(value, tuple):
        return tuple(int(part) for part in value[:3])
    text = str(value)
    if text.startswith("#"):
        return tuple(int(text[i : i + 2], 16) for i in (1, 3, 5))
    return tuple(int(part) for part in text.split())
