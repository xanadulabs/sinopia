"""The first compositor: Normal blending of two straight-alpha layers."""

import unittest

from sinopia.composite import composite
from sinopia.document import flatten
from sinopia.image import Image
from sinopia.proof import SIZE, proof_document

RED = (180, 24, 24, 255)
GREEN = (32, 140, 64, 255)


class CompositeTest(unittest.TestCase):
    def test_opaque_top_replaces_bottom(self):
        out = composite(Image(1, 1, RED), Image(1, 1, GREEN))
        self.assertEqual(out.get(0, 0), GREEN)

    def test_clear_mask_leaves_bottom(self):
        out = composite(Image(1, 1, RED), Image(1, 1, GREEN), bytearray(b"\x00"))
        self.assertEqual(out.get(0, 0), RED)

    def test_half_mask_mixes_both_colors(self):
        out = composite(Image(1, 1, RED), Image(1, 1, GREEN), bytearray(b"\x80"))
        self.assertEqual(out.get(0, 0), (106, 82, 44, 255))

    def test_half_opacity_matches_half_mask(self):
        masked = composite(Image(1, 1, RED), Image(1, 1, GREEN), bytearray(b"\x80"))
        faded = composite(Image(1, 1, RED), Image(1, 1, GREEN), opacity=128)
        self.assertEqual(faded.get(0, 0), masked.get(0, 0))

    def test_zero_opacity_leaves_bottom(self):
        out = composite(Image(1, 1, RED), Image(1, 1, GREEN), opacity=0)
        self.assertEqual(out.get(0, 0), RED)

    def test_rejects_a_mismatched_mask(self):
        with self.assertRaises(ValueError):
            composite(Image(1, 1, RED), Image(1, 1, GREEN), bytearray(b"\xff\xff"))

    def test_opaque_shift_keeps_the_uncovered_edge(self):
        out = composite(Image(3, 1, RED), Image(3, 1, GREEN), dx=1)
        self.assertEqual(out.get(0, 0), RED)
        self.assertEqual(out.get(1, 0), GREEN)
        self.assertEqual(out.get(2, 0), GREEN)

    def test_a_clear_pixel_does_not_erase_the_picture(self):
        top = Image(2, 1, (0, 0, 0, 0))
        top.set(1, 0, GREEN)
        out = composite(Image(2, 1, RED), top)
        self.assertEqual(out.get(0, 0), RED)
        self.assertEqual(out.get(1, 0), GREEN)

    def test_proof_corner_stays_red_and_center_turns_green(self):
        image = flatten(proof_document())
        self.assertEqual(image.get(0, 0), RED)
        self.assertEqual(image.get(SIZE // 2, SIZE // 2), GREEN)
        # A pixel in the falloff band is neither color.
        edge = image.get(74, SIZE // 2)
        self.assertNotEqual(edge, RED)
        self.assertNotEqual(edge, GREEN)
        self.assertEqual(edge[3], 255)


if __name__ == "__main__":
    unittest.main()
