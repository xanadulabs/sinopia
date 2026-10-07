"""The open dialog shows the picture before it is opened."""

import os
import tempfile
import unittest
from pathlib import Path

from sinopia.image import Image
from sinopia.picker import _entries, thumbnail
from sinopia.png import write_png


class ThumbnailTest(unittest.TestCase):
    def test_a_wide_picture_shrinks_and_keeps_its_color(self):
        image = Image(400, 20, (180, 24, 24, 255))
        small = thumbnail(image, max_edge=100)
        self.assertLess(small.width, image.width)
        self.assertLessEqual(max(small.width, small.height), 100)
        self.assertEqual(small.get(0, 0), (180, 24, 24, 255))

    def test_a_psd_is_listed_with_the_pictures(self):
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw)
            (folder / "scan.psd").write_bytes(b"8BPS")
            (folder / "big.psb").write_bytes(b"8BPS")
            (folder / "notes.txt").write_text("no")
            names = [path.name for _kind, path in _entries(folder)]
        self.assertEqual(names, ["big.psb", "scan.psd"])


@unittest.skipUnless(os.environ.get("DISPLAY"), "no display")
class PickerWindowTest(unittest.TestCase):
    def test_selecting_a_file_shows_its_size_and_a_preview(self):
        from sinopia.picker import PictureDialog
        from sinopia.proof import proof_document
        from sinopia.stage import Stage
        from sinopia.window import Window

        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw)
            write_png(folder / "wall.png", Image(320, 40, (32, 140, 64, 255)))
            (folder / "notes.txt").write_text("not a picture")
            window = Window(Stage(proof_document()))
            try:
                dialog = PictureDialog(window.root, folder)
                window.root.update()
                names = list(dialog.list.get(0, "end"))
                self.assertEqual(names, ["wall.png"])
                self.assertEqual(dialog.size_label.cget("text"), "320 × 40")
                self.assertLess(dialog._photo.width(), 320)
                self.assertEqual(dialog._photo.get(0, 0), (32, 140, 64))
                dialog._cancel()
            finally:
                window.root.destroy()
