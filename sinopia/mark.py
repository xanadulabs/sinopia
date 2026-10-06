"""The Sinopia mark: a figure drawn in sinopia on a broken plaster fragment.

Sinopia is the red-earth underdrawing on the plaster of a fresco. The same
picture is the window icon, the desktop shortcut, and the left half of the
About box. `sinopia.png` at the root of the project is that file.
"""

from sinopia.image import Image

WIDTH = 64
HEIGHT = 80
SHORTCUT_ZOOM = 4
ABOUT_ZOOM = 5

LINE = (148, 58, 40, 255)
LINE_DEEP = (104, 38, 26, 255)
PLASTER = (
    (232, 208, 160, 255),
    (214, 182, 128, 255),
    (198, 160, 108, 255),
    (176, 138, 90, 255),
    (158, 122, 78, 255),
)
RIM = (122, 88, 54, 255)
FACE = (86, 58, 36, 255)


def tablet() -> Image:
    """A plaster shard with a standing figure sketched in sinopia."""
    image = Image(WIDTH, HEIGHT)
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if _plaster(x, y):
                image.set(x, y, _tone(x, y))
    _rim(image)
    _figure(image)
    return image


def _plaster(x: int, y: int) -> bool:
    """A worn shard. The drawing sits on it, and the rim crumbles away."""
    dx = (x - 32) / 30
    dy = (y - 40) / 38
    block = ((x // 2) * 3 + (y // 2) * 5) % 9
    dist = dx * dx + dy * dy
    if dist > 1.02 + (block - 4) * 0.03:
        return False
    if dist > 0.86 and block % 3 == 0:
        return False
    if y > 62 and x > 46 + (y % 3) - (y - 62):
        return False
    if x < 8 and y < 16:
        return False
    return True


def _tone(x: int, y: int) -> tuple[int, int, int, int]:
    stain = (x * 13 + y * 7 + (x // 4) * (y // 5)) % 17
    if stain in (0, 11):
        return PLASTER[0]
    if stain in (1, 8, 14):
        return PLASTER[3]
    if stain == 4:
        return PLASTER[4]
    if (x + y) % 5 == 0:
        return PLASTER[2]
    return PLASTER[1]


def _rim(image: Image) -> None:
    for y in range(HEIGHT):
        for x in range(WIDTH):
            if image.get(x, y)[3] == 0:
                continue
            if not _open(image, x, y):
                continue
            image.set(x, y, FACE if y >= 34 and x >= 28 else RIM)


def _open(image: Image, x: int, y: int) -> bool:
    for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nx, ny = x + dx, y + dy
        if not (0 <= nx < WIDTH and 0 <= ny < HEIGHT) or image.get(nx, ny)[3] == 0:
            return True
    return False


def _figure(image: Image) -> None:
    """A mother and child, the usual sinopia cartoon: halo, veil, and robe."""
    ink = LINE_DEEP
    soft = LINE
    _arc(image, 26, 24, 16, 200, 340, soft)
    _oval(image, 26, 26, 7, 8, ink)
    _curve(image, (16, 20), (12, 34), (14, 48), ink)
    _curve(image, (36, 20), (40, 32), (38, 46), ink)
    _curve(image, (20, 33), (26, 36), (34, 33), soft)
    _stroke(image, 23, 24, 25, 24, ink)
    _stroke(image, 29, 24, 31, 24, ink)
    _stroke(image, 27, 25, 28, 29, soft)
    _stroke(image, 25, 31, 30, 31, soft)
    _arc(image, 44, 30, 8, 200, 350, soft)
    _oval(image, 44, 32, 5, 5, ink)
    _stroke(image, 42, 31, 44, 31, ink)
    _stroke(image, 46, 31, 48, 31, ink)
    _stroke(image, 45, 33, 46, 35, soft)
    _stroke(image, 41, 37, 40, 46, ink)
    _stroke(image, 47, 37, 48, 46, ink)
    _stroke(image, 40, 46, 48, 47, ink)
    _stroke(image, 41, 40, 34, 43, ink)
    _stroke(image, 33, 41, 36, 47, soft)
    _curve(image, (14, 46), (8, 60), (12, 70), ink)
    _curve(image, (46, 50), (54, 62), (48, 72), ink)
    _curve(image, (12, 70), (30, 76), (48, 72), ink)
    _curve(image, (20, 52), (22, 62), (18, 70), soft)
    _curve(image, (28, 50), (30, 62), (26, 72), soft)
    _curve(image, (36, 52), (34, 64), (38, 72), soft)
    _stroke(image, 22, 23, 25, 22, soft)
    _stroke(image, 28, 23, 31, 22, soft)


def _curve(image: Image, start: tuple[int, int], bend: tuple[int, int], end: tuple[int, int], color: tuple[int, int, int, int]) -> None:
    previous = start
    for step in range(1, 13):
        t = step / 12
        u = 1 - t
        x = round(u * u * start[0] + 2 * u * t * bend[0] + t * t * end[0])
        y = round(u * u * start[1] + 2 * u * t * bend[1] + t * t * end[1])
        _stroke(image, previous[0], previous[1], x, y, color)
        previous = (x, y)


def _arc(image: Image, cx: int, cy: int, radius: int, start: int, end: int, color: tuple[int, int, int, int]) -> None:
    import math

    previous = None
    for degree in range(start, end + 1, 8):
        theta = math.radians(degree)
        point = (round(cx + radius * math.cos(theta)), round(cy + radius * math.sin(theta)))
        if previous is not None:
            _stroke(image, previous[0], previous[1], point[0], point[1], color)
        previous = point


def _plot(image: Image, x: int, y: int, color: tuple[int, int, int, int]) -> None:
    if 0 <= x < WIDTH and 0 <= y < HEIGHT and image.get(x, y)[3]:
        image.set(x, y, color)


def _stroke(image: Image, x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int, int]) -> None:
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    error = dx - dy
    while True:
        _plot(image, x0, y0, color)
        if x0 == x1 and y0 == y1:
            return
        doubled = 2 * error
        if doubled > -dy:
            error -= dy
            x0 += sx
        if doubled < dx:
            error += dx
            y0 += sy


def _oval(image: Image, cx: int, cy: int, rx: int, ry: int, color: tuple[int, int, int, int]) -> None:
    x = 0
    y = ry
    decision = ry * ry - rx * rx * ry + (rx * rx) // 4
    while ry * ry * x < rx * rx * y:
        _ring(image, cx, cy, x, y, color)
        if decision < 0:
            decision += ry * ry * (2 * x + 3)
        else:
            decision += ry * ry * (2 * x + 3) + rx * rx * (2 - 2 * y)
            y -= 1
        x += 1
    decision = ry * ry * (x + 1) * (x + 1) + rx * rx * (y - 1) * (y - 1) - rx * rx * ry * ry
    while y >= 0:
        _ring(image, cx, cy, x, y, color)
        if decision > 0:
            decision += rx * rx * (3 - 2 * y)
        else:
            decision += ry * ry * (2 * x + 2) + rx * rx * (3 - 2 * y)
            x += 1
        y -= 1


def _ring(image: Image, cx: int, cy: int, x: int, y: int, color: tuple[int, int, int, int]) -> None:
    for px, py in ((cx + x, cy + y), (cx - x, cy + y), (cx + x, cy - y), (cx - x, cy - y)):
        _plot(image, px, py, color)


def scaled(image: Image, factor: int) -> Image:
    """Nearest-neighbor zoom, so the desktop file stays pixelated."""
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


def photo(root, zoom: int = 1):
    """A Tk picture of the mark. Empty pixels stay transparent."""
    import tkinter

    image = tablet()
    shot = tkinter.PhotoImage(width=image.width, height=image.height)
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = image.get(x, y)
            if alpha:
                shot.put(f"#{red:02x}{green:02x}{blue:02x}", (x, y))
    if zoom == 1:
        return shot
    return shot.zoom(zoom, zoom)
