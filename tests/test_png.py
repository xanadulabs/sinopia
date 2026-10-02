"""PNG read-back, including a row that uses the Sub filter."""

import struct
import unittest
import zlib
from pathlib import Path
import tempfile

from sinopia.image import Image
from sinopia.png import read_png, write_png


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


class PngTest(unittest.TestCase):
    def test_sub_filter_round_trip_bytes(self):
        # Two RGBA pixels. The second is stored as a difference from the first.
        first = bytes((10, 20, 30, 40))
        second = bytes((1, 2, 3, 4))
        stored_second = bytes((a - b) & 255 for a, b in zip(second, first))
        raw = bytes([1]) + first + stored_second
        ihdr = struct.pack(">IIBBBBB", 2, 1, 8, 6, 0, 0, 0)
        png = b"\x89PNG\r\n\x1a\n"
        png += _chunk(b"IHDR", ihdr)
        png += _chunk(b"IDAT", zlib.compress(raw))
        png += _chunk(b"IEND", b"")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sub.png"
            path.write_bytes(png)
            image = read_png(path)
        self.assertEqual(image.get(0, 0), (10, 20, 30, 40))
        self.assertEqual(image.get(1, 0), (1, 2, 3, 4))

    def test_bad_checksum_is_rejected(self):
        image = Image(1, 1, (1, 2, 3, 4))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.png"
            write_png(path, image)
            data = bytearray(path.read_bytes())
            data[-20] ^= 0xFF
            path.write_bytes(data)
            with self.assertRaises(ValueError):
                read_png(path)


if __name__ == "__main__":
    unittest.main()
