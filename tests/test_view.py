"""Zoom changes the picture size on screen. Save writes the folder."""

import os
import unittest

from sinopia.proof import SIZE, proof_document
from sinopia.stage import Stage


@unittest.skipUnless(os.environ.get("DISPLAY"), "no display")
class ViewTest(unittest.TestCase):
    def test_zoom_resizes_the_picture_and_the_pointer(self):
        from sinopia.window import Window

        document = proof_document()
        stage = Stage(document)
        window = Window(stage)
        try:
            window.root.update()
            self.assertEqual(window.scale, 1)
            self.assertEqual(window.photo.width(), SIZE)
            window.set_tool("zoom")
            window._release(_Point(1, 1))
            self.assertEqual(window.scale, 2)
            self.assertEqual(window.photo.width(), SIZE * 2)
            window.set_scale(2)
            window.set_tool("move")
            window._press(_Point(3 * 2, 0))
            window._release(_Point(6 * 2, 0))
            self.assertEqual(stage.layer.x, 3)
            self.assertEqual(window._zoom_readout["text"], "2×")
        finally:
            window.root.destroy()

    def test_save_writes_the_folder(self):
        from sinopia.window import Window

        calls = []
        window = Window(Stage(proof_document()), on_release=lambda: calls.append("saved"))
        try:
            window.file_menu.invoke(2)
            window.root.focus_force()
            window.root.update()
            window.root.event_generate("<Control-Key-s>")
            window.root.update()
        finally:
            window.root.destroy()
        self.assertEqual(calls, ["saved", "saved"])

    def test_a_small_picture_stays_in_the_middle_of_the_workspace(self):
        from sinopia.window import Window

        window = Window(Stage(proof_document()))
        try:
            window.root.update()
            window.set_scale(4)
            window._apply_new(40, 30)
            window.root.update()
            self.assertEqual(window.scale, 4)
            self.assertGreater(window.view.winfo_width(), window.photo.width())
            self.assertGreater(window.view.winfo_height(), window.photo.height())
            self.assertGreater(window._origin_x, 0)
            self.assertGreater(window._origin_y, 0)
        finally:
            window.root.destroy()

    def test_shortcuts_for_the_tools_we_have(self):
        from sinopia.window import Window

        window = Window(Stage(proof_document()))
        try:
            window.root.update()
            window._select_all()
            self.assertEqual(window.marquee, (0, 0, SIZE, SIZE))
            window._deselect()
            self.assertIsNone(window.marquee)
            window._free_transform()
            self.assertEqual(window.tool, "transform")
            window.set_tool("brush")
            window.stage.diameter = 5
            window._key(_Key("]", "bracketright"))
            self.assertEqual(window.stage.diameter, 6)
            window._key(_Key("[", "bracketleft"))
            self.assertEqual(window.stage.diameter, 5)
            window.set_scale(8)
            window._actual_pixels()
            self.assertEqual(window.scale, 1)
            window._fit_screen()
            self.assertGreater(window.scale, 1)
            self.assertLessEqual(SIZE * window.scale, window.view.winfo_width())
            self.assertLessEqual(SIZE * window.scale, window.view.winfo_height())
        finally:
            window.root.destroy()


class StartTest(unittest.TestCase):
    def test_the_module_opens_the_window(self):
        import sinopia.__main__ as program
        from sinopia.window import main

        self.assertIs(program.main, main)


class _Point:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y


class _Key:
    def __init__(self, char: str, keysym: str):
        self.char = char
        self.keysym = keysym
        self.state = 0
