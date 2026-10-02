"""Write an Image as an 8-bit RGBA PNG. No dependencies beyond the stdlib."""

import struct
import zlib
from pathlib import Path

from sinopia.image import Image


def _chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def _encode(width: int, height: int, channels: int, color_type: int, pixels: bytes | bytearray) -> bytes:
    raw = bytearray()
    row = width * channels
    for y in range(height):
        raw.append(0)  # filter: none
        start = y * row
        raw += pixels[start : start + row]
    ihdr = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += _chunk(b"IEND", b"")
    return png


def write_png(path: Path | str, image: Image) -> None:
    Path(path).write_bytes(_encode(image.width, image.height, 4, 6, image.pixels))


def write_mask(path: Path | str, width: int, height: int, samples: bytes | bytearray) -> None:
    if len(samples) != width * height:
        raise ValueError("mask has the wrong size")
    Path(path).write_bytes(_encode(width, height, 1, 0, samples))


def _paeth(left: int, up: int, up_left: int) -> int:
    estimate = left + up - up_left
    distance_left = abs(estimate - left)
    distance_up = abs(estimate - up)
    distance_up_left = abs(estimate - up_left)
    if distance_left <= distance_up and distance_left <= distance_up_left:
        return left
    if distance_up <= distance_up_left:
        return up
    return up_left


def _reconstruct(raw: bytes, width: int, height: int, channels: int) -> bytes:
    stride = width * channels
    if len(raw) != height * (stride + 1):
        raise ValueError("image data has the wrong size")
    out = bytearray(height * stride)
    previous = bytearray(stride)
    for y in range(height):
        row_at = y * (stride + 1)
        filter_type = raw[row_at]
        filtered = raw[row_at + 1 : row_at + 1 + stride]
        if filter_type > 4:
            raise ValueError(f"unknown png filter {filter_type}")
        recon = bytearray(stride)
        for x in range(stride):
            left = recon[x - channels] if x >= channels else 0
            up = previous[x]
            up_left = previous[x - channels] if x >= channels else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = up
            elif filter_type == 3:
                predictor = (left + up) // 2
            else:
                predictor = _paeth(left, up, up_left)
            recon[x] = (filtered[x] + predictor) & 255
        out[y * stride : (y + 1) * stride] = recon
        previous = recon
    return bytes(out)


def _read(path: Path | str) -> tuple[int, int, int, bytes]:
    data = Path(path).read_bytes()
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("not a png")
    header = None
    idat = bytearray()
    saw_end = False
    at = 8
    while at + 12 <= len(data):
        length = struct.unpack(">I", data[at : at + 4])[0]
        tag = data[at + 4 : at + 8]
        chunk = data[at + 8 : at + 8 + length]
        crc_at = at + 8 + length
        if crc_at + 4 > len(data) or len(chunk) != length:
            raise ValueError("truncated png chunk")
        stored = struct.unpack(">I", data[crc_at : crc_at + 4])[0]
        if zlib.crc32(tag + chunk) & 0xFFFFFFFF != stored:
            raise ValueError("png chunk checksum mismatch")
        if tag == b"IHDR":
            if len(chunk) != 13:
                raise ValueError("bad png header")
            width, height, depth, color_type, compression, filter_method, interlace = struct.unpack(">IIBBBBB", chunk)
            if depth != 8 or compression != 0 or filter_method != 0 or interlace != 0:
                raise ValueError("unsupported png encoding")
            if color_type == 6:
                channels = 4
            elif color_type == 0:
                channels = 1
            else:
                raise ValueError("png must be grayscale or RGBA")
            if width < 1 or height < 1:
                raise ValueError("png has no pixels")
            header = (width, height, channels)
        elif tag == b"IDAT":
            idat += chunk
        elif tag == b"IEND":
            saw_end = True
        elif not (tag[0] & 32):
            raise ValueError(f"unsupported png chunk {tag.decode('ascii', 'replace')}")
        at = crc_at + 4
    if header is None or not saw_end or not idat:
        raise ValueError("incomplete png")
    width, height, channels = header
    raw = zlib.decompress(bytes(idat))
    return width, height, channels, _reconstruct(raw, width, height, channels)


def read_png(path: Path | str) -> Image:
    width, height, channels, pixels = _read(path)
    if channels != 4:
        raise ValueError("expected an RGBA png")
    return Image.from_pixels(width, height, pixels)


def read_mask(path: Path | str) -> tuple[int, int, bytearray]:
    width, height, channels, pixels = _read(path)
    if channels != 1:
        raise ValueError("expected a grayscale mask")
    return width, height, bytearray(pixels)
