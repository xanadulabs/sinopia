"""Tool buttons carry an icon and a shortcut letter. The pointer matches the tool."""

import os
import unittest

from sinopia.icons import tool_bits


class IconBitsTest(unittest.TestCase):
    def test_the_shortcut_letter_sits_in_the_corner(self):
        bits, hot = tool_bits("move", "V")
        self.assertEqual(bits[16][18], "1")
        self.assertEqual(hot, (11, 11))
        _brush, brush_hot = tool_bits("brush")
        self.assertEqual(brush_hot, (5, 15))
        _type, type_hot = tool_bits("type")
        self.assertEqual(type_hot, (8, 2))
        transform, transform_hot = tool_bits("transform", "F")
        self.assertEqual(transform[16][18], "1")
        self.assertEqual(transform_hot, (6, 4))


@unittest.skipUnless(os.environ.get("DISPLAY"), "no display")
class IconWindowTest(unittest.TestCase):
    def test_the_pointer_changes_with_the_tool(self):
        from sinopia.proof import proof_document
        from sinopia.stage import Stage
        from sinopia.window import Window

        window = Window(Stage(proof_document()))
        try:
            window.root.update()
            self.assertEqual(window._tool_images["move"].width(), 48)
            self.assertEqual(window._tool_images["move"].get(36, 32), (32, 32, 32))
            self.assertIn("move", str(window.label.cget("cursor")))
            window.set_tool("brush")
            self.assertIn("brush", str(window.label.cget("cursor")))
            window.set_tool("type")
            self.assertIn("type", str(window.label.cget("cursor")))
            window.set_tool("transform")
            self.assertIn("transform", str(window.label.cget("cursor")))
            words = " ".join(child.cget("text") for child in window.options.winfo_children())
            self.assertIn("corner", words)
        finally:
            window.root.destroy()
