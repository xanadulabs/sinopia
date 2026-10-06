"""Grow the canvas. The picture stays put and the new pixels are empty."""

from sinopia.document import Document, Group, Layer, walk
from sinopia.image import Image

ANCHORS = ("nw", "n", "ne", "w", "c", "e", "sw", "s", "se")


def placement(extra_w: int, extra_h: int, anchor: str) -> tuple[int, int, int, int]:
    """Pixels added on the left, right, top, and bottom.

    The anchor is the square where the current picture stays. Extra width and
    height grow away from that square. An odd count keeps the spare pixel on
    the right or the bottom.
    """
    if anchor not in ANCHORS:
        raise ValueError(f"unknown anchor {anchor}")
    if extra_w < 0 or extra_h < 0:
        raise ValueError("canvas can only grow")
    column, row = {
        "nw": (0, 0),
        "n": (1, 0),
        "ne": (2, 0),
        "w": (0, 1),
        "c": (1, 1),
        "e": (2, 1),
        "sw": (0, 2),
        "s": (1, 2),
        "se": (2, 2),
    }[anchor]
    left = 0 if column == 0 else extra_w if column == 2 else extra_w // 2
    top = 0 if row == 0 else extra_h if row == 2 else extra_h // 2
    return left, extra_w - left, top, extra_h - top


def resize_canvas(document: Document, extra_w: int, extra_h: int, anchor: str) -> None:
    """Add `extra_w` and `extra_h` pixels. `anchor` is where the picture stays."""
    left, right, top, bottom = placement(extra_w, extra_h, anchor)
    if left == right == top == bottom == 0:
        return
    width = document.width + left + right
    height = document.height + top + bottom
    for item in walk(document.layers):
        if isinstance(item, Group):
            continue
        if item.image.width != document.width or item.image.height != document.height:
            raise ValueError(f"layer {item.name} is the wrong size")
        item.image = _pad_image(item.image, left, right, top, bottom)
        if item.mask is not None:
            item.mask = _pad_mask(item.mask, document.width, document.height, left, right, top, bottom)
    document.width = width
    document.height = height


def _pad_image(image: Image, left: int, right: int, top: int, bottom: int) -> Image:
    out = Image(image.width + left + right, image.height + top + bottom)
    row = image.width * 4
    for y in range(image.height):
        start = y * row
        dest = ((y + top) * out.width + left) * 4
        out.pixels[dest : dest + row] = image.pixels[start : start + row]
    return out


def _pad_mask(
    mask: bytearray, width: int, height: int, left: int, right: int, top: int, bottom: int
) -> bytearray:
    out_w = width + left + right
    out = bytearray(out_w * (height + top + bottom))
    for y in range(height):
        start = y * width
        dest = (y + top) * out_w + left
        out[dest : dest + width] = mask[start : start + width]
    return out
