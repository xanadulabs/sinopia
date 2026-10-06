"""The Sinopia mark.

Two rounded tiles, plaster behind sinopia. The same drawing is the window
icon, the About picture, and `sinopia.png`.
"""

from sinopia.image import Image

SIZE = 256
SHORTCUT_ZOOM = 1
ABOUT_ZOOM = 1

LINE = (184, 72, 48, 255)
LINE_DEEP = (114, 42, 32, 255)
PLASTER = (
    (236, 214, 168, 255),
    (222, 186, 128, 255),
    (198, 158, 104, 255),
    (176, 136, 88, 255),
    (154, 116, 74, 255),
)


_mark: Image | None = None


def tablet() -> Image:
    """The mark at the size used in About and in the shortcut file."""
    global _mark
    if _mark is None:
        _mark = mark(SIZE)
    return _mark


def mark(size: int) -> Image:
    """The tiles, drawn to `size`. Corners stay empty."""
    image = Image(size, size)
    _tile(image, 0.09, 0.09, 0.66, PLASTER[0])
    _tile(image, 0.33, 0.35, 0.66, LINE_DEEP)
    _tile(image, 0.31, 0.31, 0.66, LINE)
    return image


def icon_images() -> tuple[Image, Image, Image]:
    """Small, medium, and the full mark. Largest last."""
    return (mark(32), mark(64), tablet())


def _tile(image: Image, left: float, top: float, span: float, color: tuple[int, int, int, int]) -> None:
    size = image.width
    x0 = round(left * size)
    y0 = round(top * size)
    side = round(span * size)
    _rounded(image, x0, y0, x0 + side, y0 + side, round(side * 0.28), color)


def _rounded(image: Image, x0: int, y0: int, x1: int, y1: int, radius: int, color: tuple[int, int, int, int]) -> None:
    radius = max(1, min(radius, (x1 - x0) // 2, (y1 - y0) // 2))
    width = image.width
    height = image.height
    for y in range(max(0, y0), min(height, y1)):
        for x in range(max(0, x0), min(width, x1)):
            cx = cy = None
            if x < x0 + radius and y < y0 + radius:
                cx, cy = x0 + radius - 0.5, y0 + radius - 0.5
            elif x >= x1 - radius and y < y0 + radius:
                cx, cy = x1 - radius - 0.5, y0 + radius - 0.5
            elif x < x0 + radius and y >= y1 - radius:
                cx, cy = x0 + radius - 0.5, y1 - radius - 0.5
            elif x >= x1 - radius and y >= y1 - radius:
                cx, cy = x1 - radius - 0.5, y1 - radius - 0.5
            if cx is None or (x + 0.5 - cx) ** 2 + (y + 0.5 - cy) ** 2 <= radius * radius:
                image.set(x, y, color)


def scaled(image: Image, factor: int) -> Image:
    """Nearest-neighbor zoom, so the desktop file stays the same drawing."""
    if factor < 1:
        raise ValueError("scale must be at least 1")
    out = Image(image.width * factor, image.height * factor)
    span = out.width * 4
    for y in range(image.height):
        wide = bytearray()
        row = y * image.width * 4
        for x in range(image.width):
            wide += image.pixels[row + x * 4 : row + x * 4 + 4] * factor
        block = bytes(wide)
        start = y * factor * span
        for _step in range(factor):
            out.pixels[start : start + span] = block
            start += span
    return out


def photo(root, zoom: int = 1, image: Image | None = None):
    """A Tk picture of the mark. Empty pixels stay transparent."""
    import tkinter

    image = tablet() if image is None else image
    shot = tkinter.PhotoImage(width=image.width, height=image.height)
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = image.get(x, y)
            if alpha:
                shot.put(f"#{red:02x}{green:02x}{blue:02x}", (x, y))
    if zoom == 1:
        return shot
    return shot.zoom(zoom, zoom)
