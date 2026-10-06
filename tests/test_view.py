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
            self.assertEqual(window.photo.width(), SIZE * window.scale)
            window.set_tool("zoom")
            window._release(_Point(1, 1))
            self.assertEqual(window.scale, 16)
            self.assertEqual(window.photo.width(), SIZE * 16)
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
            window.file_menu.invoke(1)
            window.root.focus_force()
            window.root.update()
            window.root.event_generate("<Control-Key-s>")
            window.root.update()
        finally:
            window.root.destroy()
        self.assertEqual(calls, ["saved", "saved"])


class _Point:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
