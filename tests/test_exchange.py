"""PNG and JPEG open as pictures. JPEG goes out through libjpeg."""

import shutil
import tempfile
import unittest
from pathlib import Path

from sinopia.exchange import read_picture, write_picture
from sinopia.image import Image
from sinopia.jpeg import scrub_jpeg
from sinopia.png import _chunk, _encode, read_rgba

RED = (180, 24, 24, 255)


class PngOpenTest(unittest.TestCase):
    def test_an_rgb_png_opens_with_solid_alpha(self):
        pixels = bytes((1, 2, 3) * 4)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plain.png"
            path.write_bytes(_encode(2, 2, 3, 2, pixels))
            image = read_rgba(path)
        self.assertEqual(image.get(1, 1), (1, 2, 3, 255))

    def test_text_time_and_exif_chunks_are_left_out_of_the_png(self):
        pixel = bytes((180, 24, 24, 255))
        body = _encode(1, 1, 4, 6, pixel)
        secret = b"SINOPIA-SECRET-PLACE"
        extra = _chunk(b"tEXt", b"Author\x00" + secret)
        extra += _chunk(b"eXIf", b"Exif\x00\x00GPSLatitude" + secret)
        extra += _chunk(b"tIME", b"\x07\xea\x0a\x07\x15\x1e\x00")
        poisoned = body[:-12] + extra + body[-12:]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "noted.png"
            path.write_bytes(poisoned)
            image = read_rgba(path)
            saved = Path(tmp) / "kept.png"
            write_picture(saved, image)
            data = saved.read_bytes()
        self.assertEqual(image.get(0, 0), (180, 24, 24, 255))
        self.assertEqual(_png_tags(data), [b"IHDR", b"IDAT", b"IEND"])
        self.assertNotIn(secret, data)
        self.assertNotIn(b"GPSLatitude", data)


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

    def test_a_jpeg_export_drops_exif_xmp_iptc_and_comments(self):
        image = Image(8, 8, RED)
        with tempfile.TemporaryDirectory() as tmp:
            plain = Path(tmp) / "plain.jpg"
            write_picture(plain, image)
            dirty = Path(tmp) / "dirty.jpg"
            dirty.write_bytes(_with_camera_notes(plain.read_bytes()))
            opened = read_picture(dirty)
            saved = Path(tmp) / "saved.jpg"
            write_picture(saved, opened)
            data = saved.read_bytes()
        self.assertNotIn(b"GPSLatitude", data)
        self.assertNotIn(b"SINOPIA-SECRET-PLACE", data)
        self.assertNotIn(b"http://ns.adobe.com/xap/", data)
        self.assertNotIn(b"Photoshop 3.0", data)
        self.assertFalse(_has_marker(data, 0xE1))
        self.assertFalse(_has_marker(data, 0xED))
        self.assertFalse(_has_marker(data, 0xFE))
        self.assertLess(abs(opened.get(4, 4)[0] - RED[0]), 8)


@unittest.skipUnless(shutil.which("cjpeg") and shutil.which("djpeg"), "libjpeg tools are not installed")
class JpegScrubTest(unittest.TestCase):
    def test_scrub_removes_a_jfif_thumbnail_and_leaves_the_picture(self):
        image = Image(4, 4, RED)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "plain.jpg"
            write_picture(path, image)
            plain = path.read_bytes()
        thumb = b"\xab\xcd\xef\x11\x22\x33"
        marked = _with_jfif_thumbnail(plain, 2, 1, thumb)
        self.assertIn(thumb, marked)
        cleaned = scrub_jpeg(marked)
        self.assertNotIn(thumb, cleaned)
        at = cleaned.find(b"JFIF\x00")
        self.assertEqual(cleaned[at + 12 : at + 14], b"\x00\x00")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "clean.jpg"
            path.write_bytes(cleaned)
            opened = read_picture(path)
        self.assertEqual(opened.width, 4)


def _app(marker: int, payload: bytes) -> bytes:
    return bytes((0xFF, marker)) + (2 + len(payload)).to_bytes(2, "big") + payload


def _with_camera_notes(data: bytes) -> bytes:
    notes = _app(0xE1, b"Exif\x00\x00GPSLatitudeSINOPIA-SECRET-PLACE")
    notes += _app(0xE1, b"http://ns.adobe.com/xap/1.0/\x00SINOPIA-SECRET-PLACE")
    notes += _app(0xED, b"Photoshop 3.0\x00SINOPIA-SECRET-PLACE")
    notes += _app(0xFE, b"SINOPIA-SECRET-PLACE")
    return data[:2] + notes + data[2:]


def _with_jfif_thumbnail(data: bytes, width: int, height: int, rgb: bytes) -> bytes:
    at = data.find(b"JFIF\x00")
    length_at = at - 2
    old = int.from_bytes(data[length_at:at], "big")
    segment = bytearray(data[length_at : length_at + old])
    segment[14] = width
    segment[15] = height
    segment += rgb
    segment[0:2] = len(segment).to_bytes(2, "big")
    return data[:length_at] + bytes(segment) + data[length_at + old :]


def _has_marker(data: bytes, marker: int) -> bool:
    index = 2
    while index < len(data) - 1:
        if data[index] != 0xFF:
            return False
        index += 1
        while index < len(data) and data[index] == 0xFF:
            index += 1
        if index >= len(data):
            return False
        found = data[index]
        index += 1
        if found == 0xDA:
            return False
        if found == marker:
            return True
        if found in range(0xD0, 0xD9) or found == 0x01:
            continue
        length = int.from_bytes(data[index : index + 2], "big")
        index += length
    return False


def _png_tags(data: bytes) -> list[bytes]:
    tags = []
    at = 8
    while at + 12 <= len(data):
        length = int.from_bytes(data[at : at + 4], "big")
        tags.append(data[at + 4 : at + 8])
        at += 12 + length
    return tags
