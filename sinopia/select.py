"""A rectangular marquee, and the pixels copied out of it.

Copy keeps those pixels in this program. File → New reads their size from here.
"""

from sinopia.image import Image

_copied: Image | None = None


def copy_pixels(image: Image) -> None:
    global _copied
    _copied = Image.from_pixels(image.width, image.height, bytes(image.pixels))


def copied_image() -> Image | None:
    return _copied


def clear_copied() -> None:
    global _copied
    _copied = None


def crop(image: Image, box: tuple[int, int, int, int]) -> Image:
    """Pixels inside `box`. The right and bottom edges are excluded."""
    left, top, right, bottom = box
    if not (0 <= left < right <= image.width and 0 <= top < bottom <= image.height):
        raise ValueError("selection is outside the picture")
    width = right - left
    height = bottom - top
    out = bytearray(width * height * 4)
    for y in range(height):
        start = ((top + y) * image.width + left) * 4
        out[y * width * 4 : (y + 1) * width * 4] = image.pixels[start : start + width * 4]
    return Image.from_pixels(width, height, out)


def marquee_box(
    anchor: tuple[int, int],
    point: tuple[int, int],
    square: bool,
    width: int,
    height: int,
) -> tuple[int, int, int, int] | None:
    """The dragged rectangle, or None when the press and release are the same pixel."""
    ax, ay = anchor
    x, y = point
    if square:
        side = max(abs(x - ax), abs(y - ay))
        if side == 0:
            return None
        x = ax + (side if x >= ax else -side)
        y = ay + (side if y >= ay else -side)
    if (ax, ay) == (x, y):
        return None
    left, right = sorted((ax, x))
    top, bottom = sorted((ay, y))
    right += 1
    bottom += 1
    left = max(0, min(left, width))
    top = max(0, min(top, height))
    right = max(left, min(right, width))
    bottom = max(top, min(bottom, height))
    if right == left or bottom == top:
        return None
    return left, top, right, bottom
