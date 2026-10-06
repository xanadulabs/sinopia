"""PNG and JPEG open as pictures. JPEG goes out through libjpeg."""

import shutil
import tempfile
import unittest
from pathlib import Path

from sinopia.exchange import read_picture, write_picture
from sinopia.image import Image
from sinopia.png import _encode, read_rgba

RED = (180, 24, 24, 255)


class PngOpenTest(unittest.TestCase):
    def test_an_rgb_png_opens_with_solid_alpha(self):
        pixels = bytes((1, 2, 3) * 4)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plain.png"
            path.write_bytes(_encode(2, 2, 3, 2, pixels))
            image = read_rgba(path)
        self.assertEqual(image.get(1, 1), (1, 2, 3, 255))


@unittest.skipUnless(shutil.which("cjpeg") and shutil.which("djpeg"), "libjpeg tools are not installed")
class JpegRoundTripTest(unittest.TestCase):
    def test_a_flat_color_survives_jpeg(self):
        image = Image(8, 8, RED)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "flat.jpg"
            write_picture(path, image)
            opened = read_picture(path)
        self.assertEqual(opened.width, 8)
        pixel = opened.get(4, 4)
        self.assertLess(abs(pixel[0] - RED[0]), 8)
        self.assertLess(abs(pixel[1] - RED[1]), 8)
        self.assertEqual(pixel[3], 255)
