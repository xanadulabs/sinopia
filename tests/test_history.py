"""Ctrl+Z walks back through saved steps."""

import os
import unittest

from sinopia.brush import BLACK
from sinopia.history import History
from sinopia.proof import proof_document
from sinopia.stage import Stage


class HistoryTest(unittest.TestCase):
    def test_undo_restores_the_pixel_and_redo_puts_it_back(self):
        document = proof_document()
        history = History(document)
        document.layers[-1].image.set(0, 0, BLACK)
        self.assertTrue(history.commit("Paint"))
        self.assertTrue(history.undo())
        self.assertNotEqual(document.layers[-1].image.get(0, 0), BLACK)
        self.assertTrue(history.redo())
        self.assertEqual(document.layers[-1].image.get(0, 0), BLACK)


@unittest.skipUnless(os.environ.get("DISPLAY"), "no display")
class HistoryWindowTest(unittest.TestCase):
    def test_the_menu_and_history_list_follow_a_move(self):
        from sinopia.window import Window

        window = Window(Stage(proof_document()))
        try:
            window.root.update()
            self.assertEqual(window.file_menu.entrycget(0, "label"), "New...")
            self.assertEqual(window.file_menu.entrycget(1, "label"), "Open...")
            self.assertEqual(window.file_menu.entrycget(3, "label"), "Save As...")
            self.assertEqual(window.history_list.get(0), "New")
            self.assertEqual(str(window.edit_menu.entrycget(0, "state")), "disabled")
            window._press(_Click(16, 16))
            window._release(_Click(40, 16))
            self.assertEqual(window.history_list.get(1), "Move")
            self.assertNotEqual(window.stage.target.x, 0)
            window._undo()
            self.assertEqual(window.stage.target.x, 0)
            self.assertEqual(window.history_list.curselection(), (0,))
        finally:
            window.root.destroy()

    def test_a_new_layer_or_group_is_named_by_type(self):
        from sinopia.window import Window

        window = Window(Stage(proof_document()))
        try:
            window.root.update()
            window._add_layer()
            self.assertEqual(window.history_list.get(1), "Layer")
            window._group_layer()
            self.assertEqual(window.history_list.get(2), "Group")
            window._delete_layer()
            self.assertEqual(window.history_list.get(3), "Delete Group")
        finally:
            window.root.destroy()


class _Click:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
