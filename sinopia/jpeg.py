"""JPEG through libjpeg's cjpeg and djpeg.

The folder of PNGs plus stack.txt stays the file you keep. JPEG is an export.
The export is pixels. EXIF, XMP, IPTC, and comments are removed. A camera is
not invented in their place.
"""

import shutil
import subprocess
from pathlib import Path

from sinopia.image import Image


def read_jpeg(path: Path | str) -> Image:
    if shutil.which("djpeg") is None:
        raise RuntimeError("djpeg is not installed")
    ppm = subprocess.check_output(["djpeg", "-pnm", str(path)], stderr=subprocess.DEVNULL)
    return _from_ppm(ppm)


def write_jpeg(path: Path | str, image: Image, quality: int = 90) -> None:
    if shutil.which("cjpeg") is None:
        raise RuntimeError("cjpeg is not installed")
    encoded = subprocess.check_output(
        ["cjpeg", "-quality", str(quality)],
        input=_ppm_on_white(image),
        stderr=subprocess.DEVNULL,
    )
    Path(path).write_bytes(scrub_jpeg(encoded))


def scrub_jpeg(data: bytes) -> bytes:
    """Drop EXIF, XMP, IPTC, comments, and any JFIF thumbnail.

    A made-up camera in their place is easier to recognize than an empty
    header, and it would claim this copy is a photograph.
    """
    if len(data) < 4 or not data.startswith(b"\xff\xd8"):
        raise ValueError("not a jpeg")
    out = bytearray(data[:2])
    index = 2
    while index < len(data):
        if data[index] != 0xFF:
            raise ValueError("not a jpeg")
        index += 1
        while index < len(data) and data[index] == 0xFF:
            index += 1
        if index >= len(data):
            raise ValueError("not a jpeg")
        marker = data[index]
        marker_at = index - 1
        index += 1
        if marker == 0xDA:
            out += data[marker_at:]
            return bytes(out)
        if marker in range(0xD0, 0xD9) or marker == 0x01:
            out += bytes((0xFF, marker))
            continue
        if index + 2 > len(data):
            raise ValueError("not a jpeg")
        length = int.from_bytes(data[index : index + 2], "big")
        if length < 2 or index + length > len(data):
            raise ValueError("not a jpeg")
        segment = data[index : index + length]
        index += length
        if marker == 0xE0:
            segment = _jfif_without_thumbnail(segment)
            if segment is None:
                continue
        elif marker in (0xE1, 0xED, 0xFE):
            continue
        out += bytes((0xFF, marker)) + segment
    raise ValueError("not a jpeg")


def _jfif_without_thumbnail(segment: bytes) -> bytes | None:
    if len(segment) < 7:
        return segment
    if segment[2:7] == b"JFXX\x00":
        return None
    if segment[2:7] != b"JFIF\x00" or len(segment) < 16:
        return segment
    if segment[14] == 0 and segment[15] == 0:
        return segment
    head = bytearray(segment[:16])
    head[0:2] = (0, 16)
    head[14] = 0
    head[15] = 0
    return bytes(head)


def _from_ppm(data: bytes) -> Image:
    header, index = _ppm_header(data)
    magic, width, height, _max = header
    if magic != b"P6":
        raise ValueError("expected a color jpeg")
    count = width * height
    rgb = data[index : index + count * 3]
    if len(rgb) != count * 3:
        raise ValueError("truncated jpeg")
    pixels = bytearray(count * 4)
    pixels[0::4] = rgb[0::3]
    pixels[1::4] = rgb[1::3]
    pixels[2::4] = rgb[2::3]
    pixels[3::4] = b"\xff" * count
    return Image.from_pixels(width, height, pixels)


def _ppm_on_white(image: Image) -> bytes:
    count = len(image)
    rgb = bytearray(count * 3)
    source = image.pixels
    for index in range(count):
        i = index * 4
        alpha = source[i + 3]
        keep = 255 - alpha
        for channel in range(3):
            rgb[index * 3 + channel] = (source[i + channel] * alpha + 255 * keep + 127) // 255
    return b"P6\n%d %d\n255\n" % (image.width, image.height) + rgb


def _ppm_header(data: bytes) -> tuple[tuple[bytes, int, int, int], int]:
    if not data.startswith(b"P6") and not data.startswith(b"P5"):
        raise ValueError("not a ppm")
    index = 0
    tokens: list[bytes] = []
    while len(tokens) < 4:
        while index < len(data) and data[index] in b" \t\r\n":
            index += 1
        if index < len(data) and data[index] == ord("#"):
            while index < len(data) and data[index] not in b"\n\r":
                index += 1
            continue
        start = index
        while index < len(data) and data[index] not in b" \t\r\n":
            index += 1
        tokens.append(data[start:index])
    magic, width, height, maximum = tokens
    if data[index : index + 1] in b" \t\r\n":
        index += 1
    return (magic, int(width), int(height), int(maximum)), index
