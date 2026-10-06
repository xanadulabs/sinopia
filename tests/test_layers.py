"""Select, add, group, and delete layers. A group moves and fades its children together."""

import os
import tempfile
import unittest
from pathlib import Path

from sinopia.brush import BLACK
from sinopia.document import (
    Document,
    Group,
    Layer,
    add_layer,
    delete_item,
    flatten,
    group_item,
    load,
    place_above,
    place_below,
    place_into,
    save,
)
from sinopia.image import Image
from sinopia.proof import SIZE, proof_document
from sinopia.stage import Stage

RED = (180, 24, 24, 255)
GREEN = (32, 140, 64, 255)


class LayerMenuTest(unittest.TestCase):
    def test_a_clear_group_hides_its_child(self):
        red = Image(1, 1, RED)
        green = Image(1, 1, GREEN)
        group = Group("bunch", [Layer("green", green)], opacity=0)
        image = flatten(Document(1, 1, [Layer("red", red), group]))
        self.assertEqual(image.get(0, 0), RED)

    def test_a_group_offset_moves_its_child(self):
        red = Image(2, 1, RED)
        green = Image(2, 1)
        green.set(0, 0, GREEN)
        group = Group("bunch", [Layer("green", green)], x=1)
        image = flatten(Document(2, 1, [Layer("red", red), group]))
        self.assertEqual(image.get(0, 0), RED)
        self.assertEqual(image.get(1, 0), GREEN)

    def test_add_group_and_delete_round_trip(self):
        document = proof_document()
        added = add_layer(document, document.layers[-1])
        group = group_item(document, added)
        self.assertIs(group.children[0], added)
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            save(document, folder)
            text = (folder / "stack.txt").read_text(encoding="utf-8")
            self.assertIn("group group normal 255 0 0\n", text)
            self.assertIn("endgroup\n", text)
            opened = load(folder)
        self.assertIsInstance(opened.layers[-1], Group)
        self.assertEqual(opened.layers[-1].children[0].name, "layer")
        self.assertEqual(flatten(opened).pixels, flatten(document).pixels)
        nxt = delete_item(document, group)
        self.assertNotIsInstance(document.layers[-1], Group)
        self.assertIs(nxt, document.layers[-1])

    def test_the_last_layer_cannot_be_deleted(self):
        image = Image(1, 1, RED)
        document = Document(1, 1, [Layer("red", image)])
        self.assertIsNone(delete_item(document, document.layers[0]))
        self.assertEqual(len(document.layers), 1)

    def test_placing_a_layer_above_another_changes_the_picture(self):
        document = proof_document()
        red, green = document.layers
        self.assertTrue(place_above(document, red, green))
        self.assertEqual([item.name for item in document.layers], ["green", "red"])
        self.assertEqual(flatten(document).get(SIZE // 2, SIZE // 2), RED)

    def test_placing_a_layer_below_sends_it_under(self):
        document = proof_document()
        red, green = document.layers
        place_above(document, red, green)
        self.assertTrue(place_below(document, red, green))
        self.assertEqual([item.name for item in document.layers], ["red", "green"])

    def test_a_layer_can_be_dropped_into_a_group(self):
        document = proof_document()
        red, green = document.layers
        group = group_item(document, green)
        self.assertTrue(place_into(document, red, group))
        self.assertEqual(document.layers, [group])
        self.assertEqual([child.name for child in group.children], ["green", "red"])
        self.assertFalse(place_into(document, group, group))

    def test_the_brush_paints_the_selected_layer(self):
        document = proof_document()
        stage = Stage(document)
        stage.select(document.layers[0])
        stage.radius = 0
        stage.brush_press(0, 0)
        stage.brush_release(0, 0)
        self.assertEqual(document.layers[0].image.get(0, 0), BLACK)
        self.assertEqual(document.layers[1].image.get(0, 0), GREEN)
        self.assertEqual(stage.picture.get(0, 0), BLACK)


@unittest.skipUnless(os.environ.get("DISPLAY"), "no display")
class LayerPanelTest(unittest.TestCase):
    def test_the_panel_lists_selects_and_adds(self):
        from sinopia.window import Window

        document = proof_document()
        window = Window(Stage(document))
        try:
            window.root.update()
            self.assertEqual(window.layer_list.get(0), "green")
            self.assertEqual(window.layer_list.get(1), "red")
            window.layer_list.selection_clear(0, "end")
            window.layer_list.selection_set(1)
            window._choose_layer()
            self.assertIs(window.stage.target, document.layers[0])
            window.layer_list.selection_clear(0, "end")
            window.layer_list.selection_set(0)
            window._choose_layer()
            window.add_button.invoke()
            self.assertEqual(window.stage.target.name, "layer")
            self.assertEqual(window.layer_list.get(0), "layer")
            window.group_button.invoke()
            self.assertEqual(window.layer_list.get(0), "▸ group")
            self.assertEqual(window.layer_list.get(1), "    layer")
            window.delete_button.invoke()
            self.assertEqual(window.layer_list.get(0), "green")
            red_box = window.layer_list.bbox(1)
            green_box = window.layer_list.bbox(0)
            self.assertIsNotNone(red_box)
            self.assertIsNotNone(green_box)
            window._layer_press(_At(red_box[1] + red_box[3] // 2))
            window._layer_motion(_At(green_box[1] + 1))
            window._layer_drop(_At(green_box[1] + 1))
            self.assertEqual(window.layer_list.get(0), "red")
            self.assertEqual(document.layers[-1].name, "red")
        finally:
            window.root.destroy()


class _At:
    def __init__(self, y: int):
        self.y = y
