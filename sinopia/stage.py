"""The picture on screen. Dragging moves one layer; the brush paints that layer."""

from sinopia.brush import BLACK, line, stamp
from sinopia.document import Document, Group, Layer, flatten, parent_offset
from sinopia.image import Image
from sinopia.lettering import Lettering


class Stage:
    def __init__(self, document: Document):
        if not document.layers:
            raise ValueError("a stage needs a layer to drag")
        self.document = document
        self.target: Layer | Group = document.layers[-1]
        self.picture = flatten(document)
        self.color = BLACK
        self.radius = 2
        self._press: tuple[int, int, int, int] | None = None
        self._stroke: tuple[int, int] | None = None
        self.lettering = Lettering(self)

    @property
    def layer(self) -> Layer | Group:
        return self.target

    def select(self, node: Layer | Group) -> None:
        if node is self.target:
            return
        if self.lettering.active:
            self.lettering.cancel()
        self.target = node
        self._press = None
        self._stroke = None
        self.picture = flatten(self.document)

    def layer_point(self, x: int, y: int) -> tuple[int, int]:
        group_x, group_y = parent_offset(self.document, self.target)
        return x - self.target.x - group_x, y - self.target.y - group_y

    def press(self, x: int, y: int) -> None:
        self._press = (x, y, self.target.x, self.target.y)

    def shift(self, x: int, y: int) -> None:
        if self._press is None:
            return
        x0, y0, origin_x, origin_y = self._press
        self.target.x = origin_x + (x - x0)
        self.target.y = origin_y + (y - y0)

    def drag(self, x: int, y: int) -> None:
        self.shift(x, y)
        if self._press is not None:
            self._restack()

    def reveal(self) -> None:
        self._restack()

    def release(self, x: int, y: int) -> None:
        self.drag(x, y)
        self._press = None

    def brush_press(self, x: int, y: int) -> None:
        if not isinstance(self.target, Layer):
            return
        self._stroke = None
        self._brush_to(x, y)

    def brush_drag(self, x: int, y: int) -> None:
        if self._stroke is None:
            return
        self._brush_to(x, y, restack=False)

    def brush_release(self, x: int, y: int) -> None:
        if self._stroke is None:
            return
        self._brush_to(x, y)
        self._stroke = None

    def _brush_to(self, x: int, y: int, restack: bool = True) -> None:
        if self._stroke is None:
            points = [(x, y)]
        else:
            points = line(self._stroke, (x, y))[1:]
        if not isinstance(self.target, Layer):
            return
        image = self.target.image
        for px, py in points:
            local_x, local_y = self.layer_point(px, py)
            stamp(image, local_x, local_y, self.color, self.radius)
        self._stroke = (x, y)
        if restack:
            self._restack()

    def _restack(self) -> None:
        self.picture = flatten(self.document)


def ppm_bytes(image: Image) -> bytes:
    """An uncompressed RGB picture. Tk reads this much faster than a grid of color names."""
    width = image.width
    height = image.height
    source = image.pixels
    rgb = bytearray(width * height * 3)
    pixel = 0
    for index in range(0, len(source), 4):
        rgb[pixel] = source[index]
        rgb[pixel + 1] = source[index + 1]
        rgb[pixel + 2] = source[index + 2]
        pixel += 3
    return b"P6\n%d %d\n255\n" % (width, height) + rgb


def scaled_rgb(image: Image, scale: int) -> list[str]:
    """Nearest-neighbor rows of #rrggbb pixels, one string per screen row."""
    if scale < 1:
        raise ValueError("scale must be at least 1")
    rows: list[str] = []
    width = image.width
    pixels = image.pixels
    for y in range(image.height):
        colors = []
        start = y * width * 4
        for x in range(width):
            i = start + x * 4
            color = f"#{pixels[i]:02x}{pixels[i + 1]:02x}{pixels[i + 2]:02x}"
            colors.extend([color] * scale)
        row = " ".join(colors)
        rows.extend([row] * scale)
    return rows
