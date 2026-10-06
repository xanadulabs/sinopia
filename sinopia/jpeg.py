"""JPEG through libjpeg's cjpeg and djpeg.

The folder of PNGs plus stack.txt stays the file you keep. JPEG is an export.
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
    subprocess.run(
        ["cjpeg", "-quality", str(quality), "-outfile", str(path)],
        input=_ppm_on_white(image),
        check=True,
        stderr=subprocess.DEVNULL,
    )


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
