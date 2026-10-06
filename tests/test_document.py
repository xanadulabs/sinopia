"""Save a stack to a folder and open that same folder."""

import tempfile
import unittest
from pathlib import Path

from sinopia.document import Document, Group, Layer, flatten, load, rename_item, save
from sinopia.image import Image
from sinopia.png import read_png, write_png
from sinopia.proof import proof_document

RED = (180, 24, 24, 255)
GREEN = (32, 140, 64, 255)


def _same_picture(left, right) -> bool:
    return left.width == right.width and left.height == right.height and left.pixels == right.pixels


class RoundTripTest(unittest.TestCase):
    def test_saved_folder_flattens_to_the_same_proof(self):
        original = proof_document()
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            save(original, folder)
            opened = load(folder)
            self.assertEqual([layer.name for layer in opened.layers], ["red", "green"])
            self.assertIsNone(opened.layers[0].mask)
            self.assertEqual(opened.layers[1].mask, original.layers[1].mask)
            self.assertTrue(_same_picture(flatten(opened), flatten(original)))

    def test_saving_again_writes_the_same_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp) / "doc"
            save(proof_document(), folder)
            first = {path.name: path.read_bytes() for path in folder.iterdir()}
            opened = load(folder)
            save(opened, folder)
            second = {path.name: path.read_bytes() for path in folder.iterdir()}
            self.assertEqual(second, first)

    def test_stack_text_names_the_pngs(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            save(proof_document(), folder)
            text = (folder / "stack.txt").read_text(encoding="utf-8")
            self.assertEqual(
                text,
                "size 96 96\n"
                "layer red.png normal 255 - 0 0\n"
                "layer green.png normal 255 green.mask.png 0 0\n",
            )
            self.assertTrue((folder / "red.png").is_file())
            self.assertTrue((folder / "green.mask.png").is_file())

    def test_renaming_replaces_the_old_png(self):
        document = proof_document()
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            save(document, folder)
            self.assertTrue(rename_item(document, document.layers[1], "soft light"))
            self.assertEqual(document.layers[1].name, "soft-light")
            group = Group("bunch", [document.layers[1]])
            document.layers[1] = group
            self.assertTrue(rename_item(document, group, "pile"))
            self.assertFalse(rename_item(document, document.layers[0], "pile"))
            save(document, folder)
            self.assertFalse((folder / "green.png").exists())
            self.assertFalse((folder / "green.mask.png").exists())
            self.assertTrue((folder / "soft-light.png").is_file())
            self.assertTrue((folder / "soft-light.mask.png").is_file())
            opened = load(folder)
            self.assertEqual(opened.layers[1].name, "pile")
            self.assertEqual(opened.layers[1].children[0].name, "soft-light")

    def test_bottom_layer_can_be_partial(self):
        mask = bytearray(b"\xff\x00\x00\x00")
        green = Image(2, 2, GREEN)
        document = Document(2, 2, [Layer("green", green, mask)])
        image = flatten(document)
        self.assertEqual(image.get(0, 0), GREEN)
        self.assertEqual(image.get(1, 0), (0, 0, 0, 0))

    def test_png_written_by_the_compositor_reads_back(self):
        image = flatten(proof_document())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "proof.png"
            write_png(path, image)
            self.assertTrue(_same_picture(read_png(path), image))


if __name__ == "__main__":
    unittest.main()
