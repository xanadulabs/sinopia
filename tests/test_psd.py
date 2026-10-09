"""A simple PSD or PSB opens into layers. The folder stays the file we keep."""

import zlib
import unittest
from pathlib import Path
import tempfile

from sinopia.document import Document, Group, Layer, flatten, load, save
from sinopia.image import Image
from sinopia.psd import open_psd, psd_bytes


RED = (180, 24, 24, 255)
GREEN = (32, 140, 64, 255)


def _u16(value: int) -> bytes:
    return value.to_bytes(2, "big", signed=value < 0)


def _u32(value: int) -> bytes:
    return value.to_bytes(4, "big", signed=value < 0)


def _wide(value: int, psb: bool) -> bytes:
    return value.to_bytes(8 if psb else 4, "big", signed=value < 0)


def _pascal(name: str) -> bytes:
    raw = name.encode("latin-1")
    body = bytes([len(raw)]) + raw
    return body + bytes((4 - len(body) % 4) % 4)


def _tag(key: bytes, data: bytes) -> bytes:
    if len(data) % 2:
        data += b"\x00"
    return b"8BIM" + key + _u32(len(data)) + data


def _pack_row(row: bytes) -> bytes:
    out = bytearray()
    index = 0
    while index < len(row):
        run = index + 1
        while run < len(row) and row[run] == row[index]:
            run += 1
        if run - index >= 2 or index + 1 == len(row):
            left = run - index
            while left:
                take = min(left, 128)
                out.append((1 - take) & 255)
                out.append(row[index])
                left -= take
                index += take
            continue
        start = index
        index += 1
        while index < len(row):
            if index + 1 < len(row) and row[index] == row[index + 1]:
                break
            index += 1
        chunk = row[start:index]
        while chunk:
            take = chunk[:128]
            chunk = chunk[128:]
            out.append(len(take) - 1)
            out += take
    return bytes(out)


def _channel(plane: bytes, kind: str, width: int, psb: bool) -> bytes:
    if kind == "raw":
        return b"\x00\x00" + plane
    if kind == "rle":
        height = len(plane) // width
        rows = [_pack_row(plane[y * width : (y + 1) * width]) for y in range(height)]
        size = 4 if psb else 2
        counts = b"".join(len(row).to_bytes(size, "big") for row in rows)
        return b"\x00\x01" + counts + b"".join(rows)
    stored = bytearray(plane)
    if kind == "zip-predict":
        for y in range(len(plane) // width):
            row = y * width
            previous = stored[row]
            for x in range(1, width):
                current = stored[row + x]
                stored[row + x] = (current - previous) & 255
                previous = current
    compressed = zlib.compress(bytes(stored))
    marker = b"\x00\x03" if kind == "zip-predict" else b"\x00\x02"
    return marker + compressed


def _layer(
    name: str,
    color: tuple[int, int, int, int],
    top: int,
    left: int,
    bottom: int,
    right: int,
    kind: str = "raw",
    psb: bool = False,
    opacity: int = 255,
    flags: int = 0,
    clipping: int = 0,
    blend: bytes = b"norm",
    tags: bytes = b"",
    mask: bytes | None = None,
    mask_rect: tuple[int, int, int, int] | None = None,
) -> tuple[bytes, bytes]:
    width = right - left
    height = bottom - top
    channels = []
    for index, value in enumerate(color):
        plane = bytes([value]) * (width * height)
        channel_id = index if index < 3 else -1
        channels.append((channel_id, _channel(plane, kind, width, psb)))
    if mask is not None and mask_rect is not None:
        mask_w = mask_rect[3] - mask_rect[1]
        channels.append((-2, _channel(mask, kind if kind == "raw" else "raw", mask_w, psb)))
    record = _wide(top, psb) + _wide(left, psb) + _wide(bottom, psb) + _wide(right, psb)
    record += _u16(len(channels))
    for channel_id, blob in channels:
        record += _u16(channel_id) + _wide(len(blob), psb)
    mask_data = b""
    if mask_rect is not None:
        top_m, left_m, bottom_m, right_m = mask_rect
        mask_data = _u32(top_m) + _u32(left_m) + _u32(bottom_m) + _u32(right_m) + bytes((0, 0, 0, 0))
    extra = _u32(len(mask_data)) + mask_data + _u32(0) + _pascal(name) + tags
    record += b"8BIM" + blend + bytes((opacity, clipping, flags, 0)) + _u32(len(extra)) + extra
    return record, b"".join(blob for _, blob in channels)


def _marker(name: str, kind: int, psb: bool = False) -> tuple[bytes, bytes]:
    record = _wide(0, psb) * 4 + _u16(0)
    extra = _u32(0) + _u32(0) + _pascal(name) + _tag(b"lsct", _u32(kind))
    record += b"8BIM" + b"norm" + bytes((255, 0, 0, 0)) + _u32(len(extra)) + extra
    return record, b""


def _document(width: int, height: int, layers: list[tuple[bytes, bytes]], psb: bool = False, merged: bytes | None = None, channels: int = 3) -> bytes:
    version = 2 if psb else 1
    header = b"8BPS" + _u16(version) + bytes(6) + _u16(channels) + _u32(height) + _u32(width) + _u16(8) + _u16(3)
    payload = _u16(len(layers)) + b"".join(record for record, _blob in layers) + b"".join(blob for _record, blob in layers)
    if len(payload) % 2:
        payload += b"\x00"
    info = _wide(len(payload), psb) + payload
    if not layers:
        info = _wide(0, psb)
    section = info + _u32(0)
    body = header + _u32(0) + _u32(0) + _wide(len(section), psb) + section
    if merged is None:
        merged = b"\x00\x00" + bytes(width * height * channels)
    return body + merged


class PsdTest(unittest.TestCase):
    def test_two_layers_keep_their_place_and_opacity(self):
        data = _document(
            4,
            3,
            [
                _layer("red", RED, 0, 0, 3, 4),
                _layer("green", GREEN, 1, 1, 2, 3, opacity=128),
            ],
        )
        document, notes = open_psd(data)
        self.assertEqual(notes, [])
        self.assertEqual(document.width, 4)
        self.assertEqual([item.name for item in document.layers], ["red", "green"])
        red, green = document.layers
        self.assertEqual(red.image.get(0, 0), RED)
        self.assertEqual(green.opacity, 128)
        self.assertEqual(green.x, 0)
        self.assertEqual(green.image.get(1, 1), GREEN)
        self.assertEqual(green.image.get(0, 0), (0, 0, 0, 0))

    def test_rle_zip_and_prediction_round_trip_a_row(self):
        for kind in ("rle", "zip", "zip-predict"):
            data = _document(4, 1, [_layer("red", RED, 0, 0, 1, 4, kind=kind)])
            document, _notes = open_psd(data)
            self.assertEqual(document.layers[0].image.get(2, 0), RED, kind)

    def test_a_hidden_layer_comes_in_at_opacity_zero(self):
        data = _document(2, 2, [_layer("red", RED, 0, 0, 2, 2, flags=0x02)])
        document, _notes = open_psd(data)
        self.assertEqual(document.layers[0].opacity, 0)

    def test_a_mask_lands_on_the_layer(self):
        mask = bytes((0, 255, 255, 0))
        data = _document(2, 2, [_layer("red", RED, 0, 0, 2, 2, mask=mask, mask_rect=(0, 0, 2, 2))])
        document, notes = open_psd(data)
        self.assertEqual(notes, [])
        self.assertEqual(bytes(document.layers[0].mask), mask)

    def test_a_group_wraps_the_layers_inside_it(self):
        data = _document(
            2,
            2,
            [
                _marker("</Layer group>", 3),
                _layer("red", RED, 0, 0, 2, 2),
                _marker("bunch", 1),
                _layer("green", GREEN, 0, 0, 2, 2),
            ],
        )
        document, notes = open_psd(data)
        self.assertEqual(notes, [])
        self.assertEqual(len(document.layers), 2)
        group, green = document.layers
        self.assertIsInstance(group, Group)
        self.assertEqual(group.name, "bunch")
        self.assertEqual([child.name for child in group.children], ["red"])
        self.assertIsInstance(green, Layer)

    def test_groups_nest(self):
        data = _document(
            2,
            2,
            [
                _marker("</Layer group>", 3),
                _marker("</Layer group>", 3),
                _layer("red", RED, 0, 0, 2, 2),
                _marker("inner", 1),
                _marker("outer", 1),
            ],
        )
        document, notes = open_psd(data)
        self.assertEqual(notes, [])
        outer = document.layers[0]
        self.assertEqual(outer.name, "outer")
        inner = outer.children[0]
        self.assertEqual(inner.name, "inner")
        self.assertEqual(inner.children[0].name, "red")

    def test_another_blend_is_kept_as_normal_and_said_so(self):
        data = _document(2, 2, [_layer("red", RED, 0, 0, 2, 2, blend=b"mul ")])
        document, notes = open_psd(data)
        self.assertEqual(document.layers[0].blend, "normal")
        self.assertEqual(notes, ["red used Multiply, and was kept as Normal"])

    def test_a_flat_file_opens_as_one_layer(self):
        plane = bytes([180, 24, 24, 180])
        merged = b"\x00\x00" + plane + bytes([32, 140, 64, 32]) + bytes([64, 64, 64, 64])
        document, notes = open_psd(_document(2, 2, [], merged=merged))
        self.assertEqual(notes, [])
        self.assertEqual(document.layers[0].name, "image")
        self.assertEqual(document.layers[0].image.get(0, 0), (180, 32, 64, 255))
        self.assertEqual(document.layers[0].image.get(1, 0), (24, 140, 64, 255))

    def test_a_psb_uses_the_wide_fields(self):
        data = _document(2, 2, [_layer("red", RED, 0, 0, 2, 2, psb=True)], psb=True)
        document, notes = open_psd(data)
        self.assertEqual(notes, [])
        self.assertEqual(document.layers[0].image.get(1, 1), RED)

    def test_a_space_in_the_name_becomes_a_hyphen_and_the_folder_reloads(self):
        data = _document(2, 2, [_layer("My Layer", RED, 0, 0, 2, 2)])
        document, _notes = open_psd(data)
        self.assertEqual(document.layers[0].name, "My-Layer")
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            save(document, folder)
            loaded = load(folder)
        self.assertEqual(loaded.layers[0].image.get(0, 0), RED)

    def test_sixteen_bit_cmyk_and_a_huge_canvas_are_refused(self):
        base = _document(2, 2, [_layer("red", RED, 0, 0, 2, 2)])
        sixteen = bytearray(base)
        sixteen[22:24] = _u16(16)
        with self.assertRaises(ValueError):
            open_psd(bytes(sixteen))
        cmyk = bytearray(base)
        cmyk[24:26] = _u16(4)
        with self.assertRaisesRegex(ValueError, "8-bit RGB"):
            open_psd(bytes(cmyk))
        huge = _document(8193, 2, [])
        with self.assertRaisesRegex(ValueError, "8192"):
            open_psd(huge)

    def test_saving_a_psd_keeps_the_layers_the_mask_and_the_group(self):
        red = Image(4, 3)
        red.set(2, 1, RED)
        mask = bytearray(b"\xff" * 12)
        mask[1 * 4 + 2] = 128
        green = Image(4, 3, GREEN)
        document = Document(
            4,
            3,
            [
                Group("bunch", [Layer("red", red, mask, 128, x=0, y=0)]),
                Layer("green", green, opacity=200),
            ],
        )
        opened, notes = open_psd(psd_bytes(document))
        self.assertEqual(notes, [])
        self.assertEqual(opened.layers[0].name, "bunch")
        self.assertEqual(opened.layers[0].children[0].name, "red")
        self.assertEqual(opened.layers[0].children[0].opacity, 128)
        self.assertEqual(opened.layers[0].children[0].image.get(2, 1), RED)
        self.assertEqual(opened.layers[0].children[0].mask[1 * 4 + 2], 128)
        self.assertEqual(opened.layers[1].name, "green")
        self.assertEqual(opened.layers[1].opacity, 200)
        self.assertEqual(flatten(opened).pixels, flatten(document).pixels)

    def test_a_saved_psd_leaves_out_exif(self):
        secret = b"SINOPIA-SECRET-PLACE"
        document = Document(2, 2, [Layer("red", Image(2, 2, RED))])
        noted = _with_exif_resource(psd_bytes(document), secret)
        self.assertIn(secret, noted)
        opened, _notes = open_psd(noted)
        saved = psd_bytes(opened)
        self.assertNotIn(secret, saved)
        self.assertNotIn(b"GPSLatitude", saved)
        self.assertEqual(_resource_ids(saved), [0x03ED])
        self.assertEqual(opened.layers[0].image.get(0, 0), RED)

    def test_a_drop_shadow_survives_in_the_saved_psd(self):
        dot = Image(2, 1)
        dot.set(0, 0, GREEN)
        document = Document(2, 1, [Layer("green", dot, shadow=(1, 0))])
        opened, notes = open_psd(psd_bytes(document))
        self.assertEqual(notes, [])
        self.assertEqual(flatten(opened).get(0, 0), GREEN)
        self.assertEqual(flatten(opened).get(1, 0)[:3], (0, 0, 0))
        self.assertGreater(flatten(opened).get(1, 0)[3], 0)

    def test_a_clipped_layer_is_opened_and_the_clip_is_reported(self):
        data = _document(2, 2, [_layer("red", RED, 0, 0, 2, 2, clipping=1)])
        document, notes = open_psd(data)
        self.assertEqual(document.layers[0].image.get(0, 0), RED)
        self.assertIn("clip", notes[0])


def _with_exif_resource(data: bytes, secret: bytes) -> bytes:
    color_len = int.from_bytes(data[26:30], "big")
    res_at = 30 + color_len
    res_len = int.from_bytes(data[res_at : res_at + 4], "big")
    payload = b"Exif\x00\x00GPSLatitude" + secret
    raw_len = len(payload)
    if raw_len % 2:
        payload += b"\x00"
    block = b"8BIM" + _u16(0x0422) + b"\x00\x00" + _u32(raw_len) + payload
    start = res_at + 4
    resources = data[start : start + res_len] + block
    return data[:res_at] + _u32(len(resources)) + resources + data[start + res_len :]


def _resource_ids(data: bytes) -> list[int]:
    color_len = int.from_bytes(data[26:30], "big")
    res_at = 30 + color_len
    res_len = int.from_bytes(data[res_at : res_at + 4], "big")
    blob = data[res_at + 4 : res_at + 4 + res_len]
    ids = []
    at = 0
    while at + 12 <= len(blob) and blob[at : at + 4] == b"8BIM":
        ids.append(int.from_bytes(blob[at + 4 : at + 6], "big"))
        name_field = 1 + blob[at + 6]
        if name_field % 2:
            name_field += 1
        size_at = at + 6 + name_field
        size = int.from_bytes(blob[size_at : size_at + 4], "big")
        at = size_at + 4 + size + (size % 2)
    return ids
