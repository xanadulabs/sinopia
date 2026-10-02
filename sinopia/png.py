"""Write an Image as an 8-bit RGBA PNG. No dependencies beyond the stdlib."""

import struct
import zlib
from pathlib import Path

from sinopia.image import Image


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def write_png(path: Path | str, image: Image) -> None:
    raw = bytearray()
    row = image.width * 4
    pixels = image.pixels
    for y in range(image.height):
        raw.append(0)  # filter: none
        start = y * row
        raw += pixels[start : start + row]
    ihdr = struct.pack(">IIBBBBB", image.width, image.height, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    Path(path).write_bytes(png)
