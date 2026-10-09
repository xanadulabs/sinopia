"""Open a simple PSD or PSB into a document.

The folder of PNGs plus stack.txt stays the file you keep. This only reads.
"""

import zlib
from pathlib import Path

from sinopia.document import Document, Group, Layer, flatten
from sinopia.image import Image
from sinopia.style import shadow_image

MAX_EDGE = 8192
_LONG_KEYS = {
    "LMsk",
    "Lr16",
    "Lr32",
    "Layr",
    "Mt16",
    "Mt32",
    "Mtrn",
    "Alph",
    "FMsk",
    "lnk2",
    "FEid",
    "FXid",
    "PxSD",
}
_SMART = {"SoLd", "SoLE", "PlLd"}
_TYPE = {"TySh"}
_BLEND = {
    "diss": "Dissolve",
    "dark": "Darken",
    "mul ": "Multiply",
    "idiv": "Color Burn",
    "lbrn": "Linear Burn",
    "dkCl": "Darker Color",
    "lite": "Lighten",
    "scrn": "Screen",
    "div ": "Color Dodge",
    "lddg": "Linear Dodge",
    "lgCl": "Lighter Color",
    "over": "Overlay",
    "sLit": "Soft Light",
    "hLit": "Hard Light",
    "vLit": "Vivid Light",
    "lLit": "Linear Light",
    "pLit": "Pin Light",
    "hMix": "Hard Mix",
    "diff": "Difference",
    "smud": "Exclusion",
    "fsub": "Subtract",
    "fdiv": "Divide",
    "hue ": "Hue",
    "sat ": "Saturation",
    "colr": "Color",
    "lum ": "Luminosity",
}


class _File:
    def __init__(self, data: bytes):
        self.data = data
        self.at = 0

    def take(self, count: int) -> bytes:
        end = self.at + count
        if count < 0 or end > len(self.data):
            raise ValueError("the file ended early")
        chunk = self.data[self.at : end]
        self.at = end
        return chunk

    def u8(self) -> int:
        return self.take(1)[0]

    def u16(self) -> int:
        return int.from_bytes(self.take(2), "big")

    def i16(self) -> int:
        return int.from_bytes(self.take(2), "big", signed=True)

    def u32(self) -> int:
        return int.from_bytes(self.take(4), "big")

    def i32(self) -> int:
        return int.from_bytes(self.take(4), "big", signed=True)

    def u64(self) -> int:
        return int.from_bytes(self.take(8), "big")

    def i64(self) -> int:
        return int.from_bytes(self.take(8), "big", signed=True)

    def skip(self, count: int) -> None:
        self.take(count)


class _LayerBits:
    def __init__(self) -> None:
        self.top = self.left = self.bottom = self.right = 0
        self.channels: list[tuple[int, int]] = []
        self.blend = "norm"
        self.opacity = 255
        self.clipping = 0
        self.flags = 0
        self.name = ""
        self.section = 0
        self.tags: set[str] = set()
        self.mask: tuple[int, int, int, int, int, int] | None = None
        self.planes: dict[int, bytes] = {}

    @property
    def hidden(self) -> bool:
        return bool(self.flags & 0x02)

    @property
    def irrelevant(self) -> bool:
        return bool(self.flags & 0x10)


def measure(path: Path | str) -> tuple[int, int]:
    """Width and height from the file header, before the layers are read."""
    with Path(path).open("rb") as handle:
        header = handle.read(26)
    return _header(header)[2:]


def read_psd(path: Path | str) -> tuple[Document, list[str]]:
    """Read a simple 8-bit RGB PSD or PSB. Notes say what was left out."""
    return open_psd(Path(path).read_bytes())


def write_psd(path: Path | str, document: Document) -> None:
    """Write a PSD. The folder of PNGs plus stack.txt stays the file you keep.

    The only image resource is the print resolution. EXIF and similar notes are not written.
    """
    Path(path).write_bytes(psd_bytes(document))


def psd_bytes(document: Document) -> bytes:
    """An 8-bit RGB PSD of this document, laid out as Adobe specifies."""
    if document.width > 30000 or document.height > 30000:
        raise ValueError("a PSD cannot be larger than 30000 pixels on a side")
    records: list[tuple[bytes, bytes]] = []
    _write_items(document.layers, 0, 0, document.width, document.height, records)
    payload = _i16(len(records)) + b"".join(record for record, _blob in records)
    payload += b"".join(blob for _record, blob in records)
    if len(payload) % 2:
        payload += b"\x00"
    layer_info = _be32(len(payload)) + payload
    section = layer_info + _be32(0)
    merged = _merged_rle(flatten(document))
    return (
        _file_header(document.width, document.height)
        + _be32(0)
        + _resolution()
        + _be32(len(section))
        + section
        + merged
    )


def open_psd(data: bytes) -> tuple[Document, list[str]]:
    source = _File(data)
    version, channels, width, height = _header(source.take(26))
    _skip_block(source, wide=False)
    _skip_block(source, wide=False)
    psb = version == 2
    section_len = source.u64() if psb else source.u32()
    section_end = source.at + section_len
    info_len = source.u64() if psb else source.u32()
    notes: list[str] = []
    if info_len == 0:
        source.at = section_end
        return _flat(source, width, height, channels, psb), notes
    count = abs(source.i16())
    records = [_record(source, psb) for _ in range(count)]
    for record in records:
        _planes(source, record, psb)
    if source.at > section_end:
        raise ValueError("the layer data is incomplete")
    source.at = section_end
    layers = _stack(records, width, height, notes)
    if not layers:
        return _flat(source, width, height, channels, psb), notes
    return Document(width, height, layers), notes


def _header(header: bytes) -> tuple[int, int, int, int]:
    if len(header) < 26 or header[:4] != b"8BPS":
        raise ValueError("not a Photoshop document")
    version = int.from_bytes(header[4:6], "big")
    if version not in (1, 2):
        raise ValueError("not a Photoshop document")
    channels = int.from_bytes(header[12:14], "big")
    height = int.from_bytes(header[14:18], "big")
    width = int.from_bytes(header[18:22], "big")
    depth = int.from_bytes(header[22:24], "big")
    mode = int.from_bytes(header[24:26], "big")
    if depth != 8 or mode != 3:
        raise ValueError("only 8-bit RGB documents open")
    if channels < 1 or channels > 56:
        raise ValueError("only 8-bit RGB documents open")
    if width < 1 or height < 1 or width > MAX_EDGE or height > MAX_EDGE:
        raise ValueError(f"the picture is larger than {MAX_EDGE} pixels on a side")
    return version, channels, width, height


def _skip_block(source: _File, wide: bool) -> None:
    length = source.u64() if wide else source.u32()
    source.skip(length)


def _record(source: _File, psb: bool) -> _LayerBits:
    layer = _LayerBits()
    if psb:
        layer.top, layer.left, layer.bottom, layer.right = (source.i64() for _ in range(4))
    else:
        layer.top, layer.left, layer.bottom, layer.right = (source.i32() for _ in range(4))
    count = source.u16()
    wide = source.u64 if psb else source.u32
    layer.channels = [(source.i16(), wide()) for _ in range(count)]
    if source.take(4) != b"8BIM":
        raise ValueError("the layer data is incomplete")
    layer.blend = source.take(4).decode("latin-1")
    layer.opacity = source.u8()
    layer.clipping = source.u8()
    layer.flags = source.u8()
    source.u8()
    extra_len = source.u32()
    extra_end = source.at + extra_len
    layer.mask = _mask(source)
    source.skip(source.u32())
    layer.name = _pascal(source)
    while source.at + 12 <= extra_end:
        signature = source.take(4)
        if signature not in (b"8BIM", b"8B64"):
            break
        key = source.take(4).decode("latin-1")
        if signature == b"8B64" or (psb and key in _LONG_KEYS):
            length = source.u64()
        else:
            length = source.u32()
        data = source.take(length)
        layer.tags.add(key)
        if key == "luni":
            layer.name = _unicode_name(data) or layer.name
        elif key == "lsct" and len(data) >= 4:
            layer.section = int.from_bytes(data[:4], "big")
    if source.at > extra_end:
        raise ValueError("the layer data is incomplete")
    source.at = extra_end
    return layer


def _mask(source: _File) -> tuple[int, int, int, int, int, int] | None:
    size = source.u32()
    if size == 0:
        return None
    data = source.take(size)
    if size < 18:
        return None
    top, left, bottom, right = (int.from_bytes(data[i : i + 4], "big", signed=True) for i in (0, 4, 8, 12))
    default = data[16]
    flags = data[17]
    return top, left, bottom, right, default, flags


def _pascal(source: _File) -> str:
    length = source.u8()
    name = source.take(length).decode("latin-1", "replace")
    padding = (4 - ((1 + length) % 4)) % 4
    source.skip(padding)
    return name.replace("\x00", "")


def _unicode_name(data: bytes) -> str:
    if len(data) < 4:
        return ""
    count = int.from_bytes(data[:4], "big")
    return data[4 : 4 + count * 2].decode("utf-16-be", "replace").replace("\x00", "")


def _planes(source: _File, layer: _LayerBits, psb: bool) -> None:
    for channel_id, length in layer.channels:
        end = source.at + length
        if length < 2:
            source.at = end
            continue
        width, height = _channel_size(layer, channel_id)
        if width <= 0 or height <= 0 or layer.irrelevant or layer.section in (1, 2, 3):
            source.at = end
            continue
        layer.planes[channel_id] = _decode(source, width, height, end, psb)
        source.at = end


def _channel_size(layer: _LayerBits, channel_id: int) -> tuple[int, int]:
    if channel_id in (-2, -3) and layer.mask is not None:
        top, left, bottom, right = layer.mask[:4]
        return right - left, bottom - top
    return layer.right - layer.left, layer.bottom - layer.top


def _decode(source: _File, width: int, height: int, end: int, psb: bool) -> bytes:
    kind = source.u16()
    count = width * height
    if kind == 0:
        raw = source.take(count)
    elif kind == 1:
        wide = source.u32 if psb else source.u16
        counts = [wide() for _ in range(height)]
        rows = bytearray()
        for row_bytes in counts:
            rows += _packbits(source.take(row_bytes), width)
        raw = bytes(rows)
    elif kind in (2, 3):
        try:
            raw = zlib.decompress(source.data[source.at : end])
        except zlib.error as error:
            raise ValueError("the layer data is incomplete") from error
        source.at = end
        if kind == 3:
            raw = _predict(raw, width, height)
    else:
        raise ValueError("the layer data is incomplete")
    if len(raw) < count:
        raise ValueError("the layer data is incomplete")
    return raw[:count]


def _packbits(data: bytes, width: int) -> bytes:
    out = bytearray()
    index = 0
    while len(out) < width and index < len(data):
        control = data[index]
        index += 1
        if control >= 128:
            control -= 256
        if control == -128:
            continue
        if control >= 0:
            out += data[index : index + control + 1]
            index += control + 1
        else:
            if index >= len(data):
                break
            out += bytes([data[index]]) * (1 - control)
            index += 1
    if len(out) < width:
        raise ValueError("the layer data is incomplete")
    return bytes(out[:width])


def _predict(raw: bytes, width: int, height: int) -> bytes:
    out = bytearray(raw[: width * height])
    for y in range(height):
        row = y * width
        for x in range(1, width):
            out[row + x] = (out[row + x] + out[row + x - 1]) & 255
    return bytes(out)


def _stack(records: list[_LayerBits], width: int, height: int, notes: list[str]) -> list:
    root: list = []
    parents: list[list] = [root]
    groups: list[Group] = []
    used: set[str] = set()
    for record in records:
        if record.section == 3:
            group = Group("group", [], 255, "normal")
            parents[-1].append(group)
            parents.append(group.children)
            groups.append(group)
            continue
        if record.section in (1, 2) and groups:
            _finish_group(groups.pop(), parents, record, notes, used)
            continue
        if not _has_color(record):
            if record.section in (1, 2, 3):
                continue
            name = _claim(_label(record), used)
            if record.irrelevant:
                notes.append(f"{name} is not pixels, and it was not kept")
                continue
            _mention(record, name, notes)
            opacity = 0 if record.hidden else record.opacity
            parents[-1].append(Layer(name, Image(width, height), None, opacity, "normal"))
            continue
        parents[-1].append(_painted(record, width, height, notes, _claim(_label(record), used)))
    if groups:
        raise ValueError("a group in the file was not closed")
    return root


def _finish_group(group: Group, parents: list[list], record: _LayerBits, notes: list[str], used: set[str]) -> None:
    parents.pop()
    group.name = _claim(_label(record), used)
    group.opacity = 0 if record.hidden else record.opacity
    _mention(record, group.name, notes)


def _painted(record: _LayerBits, width: int, height: int, notes: list[str], name: str) -> Layer:
    _mention(record, name, notes)
    if record.tags & _TYPE:
        notes.append(f"{name} kept its pixels. The type was not kept as type")
    if record.tags & _SMART:
        notes.append(f"{name} kept its pixels. The smart object was not kept")
    image = Image(width, height)
    _place_color(image, record)
    mask = _place_mask(width, height, record, name, notes)
    opacity = 0 if record.hidden else record.opacity
    return Layer(name, image, mask, opacity, "normal", 0, 0)


def _mention(record: _LayerBits, name: str, notes: list[str]) -> None:
    if record.blend not in ("norm", "pass"):
        kind = _BLEND.get(record.blend, record.blend.strip() or "another blend")
        notes.append(f"{name} used {kind}, and was kept as Normal")
    if record.clipping:
        notes.append(f"{name} was clipped to the layer under it, and that clip was not kept")


def _place_color(image: Image, record: _LayerBits) -> None:
    layer_w = record.right - record.left
    layer_h = record.bottom - record.top
    if layer_w <= 0 or layer_h <= 0:
        return
    red = record.planes.get(0)
    green = record.planes.get(1)
    blue = record.planes.get(2)
    alpha = record.planes.get(-1)
    pixels = image.pixels
    for y in range(layer_h):
        dest_y = record.top + y
        if not 0 <= dest_y < image.height:
            continue
        x0 = max(0, -record.left)
        x1 = min(layer_w, image.width - record.left)
        if x1 <= x0:
            continue
        row = y * layer_w
        for x in range(x0, x1):
            index = row + x
            pixel = (dest_y * image.width + record.left + x) * 4
            pixels[pixel] = 0 if red is None else red[index]
            pixels[pixel + 1] = 0 if green is None else green[index]
            pixels[pixel + 2] = 0 if blue is None else blue[index]
            pixels[pixel + 3] = 255 if alpha is None else alpha[index]


def _place_mask(width: int, height: int, record: _LayerBits, name: str, notes: list[str]) -> bytearray | None:
    if record.mask is None or -2 not in record.planes:
        if record.mask is not None and -2 not in record.planes:
            notes.append(f"{name} had a mask, and it was not kept")
        return None
    top, left, bottom, right, default, flags = record.mask
    if flags & 0x02:
        notes.append(f"{name} had a mask, and it was not kept")
        return None
    mask = bytearray([default]) * (width * height)
    plane = record.planes[-2]
    mask_w = right - left
    mask_h = bottom - top
    for y in range(mask_h):
        dest_y = top + y
        if not 0 <= dest_y < height:
            continue
        x0 = max(0, -left)
        x1 = min(mask_w, width - left)
        if x1 <= x0:
            continue
        row = y * mask_w
        base = dest_y * width + left
        for x in range(x0, x1):
            mask[base + x] = plane[row + x]
    return mask


def _has_color(record: _LayerBits) -> bool:
    return any(channel in record.planes for channel in (0, 1, 2, -1))


def _label(record: _LayerBits) -> str:
    return record.name.strip() or "layer"


def _flat(source: _File, width: int, height: int, channels: int, psb: bool) -> Document:
    if source.at + 2 > len(source.data):
        raise ValueError("this file has no picture")
    planes = _merged(source, width, height, channels, psb)
    record = _LayerBits()
    record.top = 0
    record.left = 0
    record.bottom = height
    record.right = width
    for index, plane in enumerate(planes[:4]):
        record.planes[index if index < 3 else -1] = plane
    if -1 not in record.planes:
        record.planes[-1] = bytes([255]) * (width * height)
    return Document(width, height, [_painted(record, width, height, [], "image")])


def _merged(source: _File, width: int, height: int, channels: int, psb: bool) -> list[bytes]:
    kind = source.u16()
    count = width * height
    if kind == 0:
        return [source.take(count) for _ in range(channels)]
    if kind == 1:
        counts = [source.u32() if psb else source.u16() for _ in range(height * channels)]
        planes = []
        for channel in range(channels):
            rows = bytearray()
            for row in range(height):
                rows += _packbits(source.take(counts[channel * height + row]), width)
            planes.append(bytes(rows))
        return planes
    if kind in (2, 3):
        try:
            raw = zlib.decompress(source.data[source.at :])
        except zlib.error as error:
            raise ValueError("the layer data is incomplete") from error
        if kind == 3:
            raw = b"".join(_predict(raw[index * count : (index + 1) * count], width, height) for index in range(channels))
        return [raw[index * count : (index + 1) * count] for index in range(channels)]
    raise ValueError("the layer data is incomplete")


def _claim(label: str, used: set[str]) -> str:
    cleaned = []
    for char in label:
        if ("a" <= char <= "z") or ("A" <= char <= "Z") or char.isdigit() or char in "-_":
            cleaned.append(char)
        else:
            cleaned.append("-")
    name = "".join(cleaned).strip("-") or "layer"
    base = name
    number = 2
    while name in used:
        name = f"{base}-{number}"
        number += 1
    used.add(name)
    return name


def _file_header(width: int, height: int) -> bytes:
    return b"8BPS" + _be16(1) + bytes(6) + _be16(4) + _be32(height) + _be32(width) + _be16(8) + _be16(3)


def _resolution() -> bytes:
    dpi = 72 << 16
    data = _be32(dpi) + _be16(1) + _be16(1) + _be32(dpi) + _be16(1) + _be16(1)
    block = b"8BIM" + _be16(0x03ED) + b"\x00\x00" + _be32(len(data)) + data
    return _be32(len(block)) + block


def _write_items(items: list, dx: int, dy: int, width: int, height: int, out: list[tuple[bytes, bytes]]) -> None:
    for item in items:
        if isinstance(item, Group):
            out.append(_folder_record("</Layer group>", 255, 3, b"norm"))
            _write_items(item.children, dx + item.x, dy + item.y, width, height, out)
            out.append(_folder_record(item.name, item.opacity, 1, b"pass"))
            continue
        origin_x = dx + item.x
        origin_y = dy + item.y
        if item.shadow is not None:
            sx, sy = item.shadow
            shadow = shadow_image(item)
            out.append(_pixel_record(f"{item.name}-shadow", 255, shadow, None, origin_x + sx, origin_y + sy, width, height))
        out.append(_pixel_record(item.name, item.opacity, item.image, item.mask, origin_x, origin_y, width, height))


def _pixel_record(
    name: str,
    opacity: int,
    image: Image,
    mask: bytearray | None,
    origin_x: int,
    origin_y: int,
    doc_w: int,
    doc_h: int,
) -> tuple[bytes, bytes]:
    sheet = _crop(image, origin_x, origin_y, doc_w, doc_h)
    if sheet is None:
        return _layer_record(name, opacity, 0, 0, 0, 0, {}, b"norm", _luni(name))
    top, left, bottom, right, planes = sheet
    if mask is not None:
        planes[-2] = _sample_mask(mask, image.width, top, left, bottom, right, origin_x, origin_y)
    return _layer_record(name, opacity, top, left, bottom, right, planes, b"norm", b"")


def _crop(
    image: Image, origin_x: int, origin_y: int, doc_w: int, doc_h: int
) -> tuple[int, int, int, int, dict[int, bytes]] | None:
    width = image.width
    pixels = image.pixels
    top = left = bottom = right = 0
    found = False
    for y in range(image.height):
        row = y * width
        for x in range(width):
            if pixels[(row + x) * 4 + 3] == 0:
                continue
            dx = x + origin_x
            dy = y + origin_y
            if not (0 <= dx < doc_w and 0 <= dy < doc_h):
                continue
            if not found:
                top = bottom = dy
                left = right = dx
                found = True
            else:
                top = min(top, dy)
                left = min(left, dx)
                bottom = max(bottom, dy)
                right = max(right, dx)
    if not found:
        return None
    bottom += 1
    right += 1
    box_w = right - left
    box_h = bottom - top
    planes = {channel: bytearray(box_w * box_h) for channel in (0, 1, 2, -1)}
    for y in range(box_h):
        for x in range(box_w):
            lx = left + x - origin_x
            ly = top + y - origin_y
            index = y * box_w + x
            if not (0 <= lx < width and 0 <= ly < image.height):
                continue
            pixel = (ly * width + lx) * 4
            planes[0][index] = pixels[pixel]
            planes[1][index] = pixels[pixel + 1]
            planes[2][index] = pixels[pixel + 2]
            planes[-1][index] = pixels[pixel + 3]
    return top, left, bottom, right, {channel: bytes(plane) for channel, plane in planes.items()}


def _sample_mask(
    mask: bytearray, width: int, top: int, left: int, bottom: int, right: int, origin_x: int, origin_y: int
) -> bytes:
    box_w = right - left
    box_h = bottom - top
    out = bytearray(box_w * box_h)
    for y in range(box_h):
        for x in range(box_w):
            lx = left + x - origin_x
            ly = top + y - origin_y
            if 0 <= lx < width and 0 <= ly < len(mask) // width:
                out[y * box_w + x] = mask[ly * width + lx]
    return bytes(out)


def _folder_record(name: str, opacity: int, kind: int, blend: bytes) -> tuple[bytes, bytes]:
    tags = _luni(name) + _info(b"lsct", _be32(kind) + b"8BIM" + blend)
    return _layer_record(name, opacity, 0, 0, 0, 0, {}, blend, tags)


def _layer_record(
    name: str,
    opacity: int,
    top: int,
    left: int,
    bottom: int,
    right: int,
    planes: dict[int, bytes],
    blend: bytes,
    tags: bytes,
) -> bytes:
    order = [channel for channel in (0, 1, 2, -1, -2) if channel in planes]
    blobs = []
    listed = b""
    box_w = right - left
    for channel in order:
        blob = _rle(planes[channel], box_w)
        listed += _be16(channel) + _be32(len(blob))
        blobs.append(blob)
    mask = b""
    if -2 in planes:
        mask = _be32(top) + _be32(left) + _be32(bottom) + _be32(right) + bytes(4)
    if not tags:
        tags = _luni(name)
    extra = _be32(len(mask)) + mask + _be32(0) + _pascal_bytes(name) + tags
    record = _be32(top) + _be32(left) + _be32(bottom) + _be32(right)
    record += _be16(len(order)) + listed
    record += b"8BIM" + blend + bytes((opacity & 255, 0, 0x08, 0)) + _be32(len(extra)) + extra
    return record, b"".join(blobs)


def _rle(plane: bytes, width: int) -> bytes:
    if width <= 0:
        return b"\x00\x00"
    height = len(plane) // width
    rows = [_pack_row(plane[y * width : (y + 1) * width]) for y in range(height)]
    counts = b"".join(len(row).to_bytes(2, "big") for row in rows)
    return b"\x00\x01" + counts + b"".join(rows)


def _pack_row(row: bytes) -> bytes:
    out = bytearray()
    index = 0
    while index < len(row):
        if index + 1 < len(row) and row[index] == row[index + 1]:
            end = index + 2
            while end < len(row) and row[end] == row[index] and end - index < 128:
                end += 1
            out.append((1 - (end - index)) & 255)
            out.append(row[index])
            index = end
            continue
        end = index + 1
        while end < len(row) and end - index < 128:
            if end + 1 < len(row) and row[end] == row[end + 1]:
                break
            end += 1
        chunk = row[index:end]
        out.append(len(chunk) - 1)
        out += chunk
        index = end
    return bytes(out)


def _merged_rle(image: Image) -> bytes:
    pixels = image.pixels
    rows = []
    counts = b""
    for channel in range(4):
        plane = pixels[channel::4]
        for y in range(image.height):
            packed = _pack_row(plane[y * image.width : (y + 1) * image.width])
            rows.append(packed)
            counts += len(packed).to_bytes(2, "big")
    return b"\x00\x01" + counts + b"".join(rows)


def _pascal_bytes(name: str) -> bytes:
    raw = name.encode("latin-1", "replace")[:255]
    body = bytes([len(raw)]) + raw
    return body + bytes((4 - len(body) % 4) % 4)


def _luni(name: str) -> bytes:
    encoded = name.encode("utf-16-be")
    return _info(b"luni", _be32(len(encoded) // 2) + encoded)


def _info(key: bytes, data: bytes) -> bytes:
    if len(data) % 2:
        data += b"\x00"
    return b"8BIM" + key + _be32(len(data)) + data


def _be16(value: int) -> bytes:
    return int(value).to_bytes(2, "big", signed=value < 0)


def _be32(value: int) -> bytes:
    return int(value).to_bytes(4, "big", signed=value < 0)


def _i16(value: int) -> bytes:
    return int(value).to_bytes(2, "big", signed=True)
