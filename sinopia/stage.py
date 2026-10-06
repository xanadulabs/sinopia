"""The picture on screen. Dragging moves one layer; the brush paints that layer."""

from sinopia.brush import BLACK, line, stamp
from sinopia.document import Document, flatten, flatten_below, paint_layer
from sinopia.image import Image
from sinopia.lettering import Lettering


class Stage:
    def __init__(self, document: Document, layer_index: int = -1):
        if not document.layers:
            raise ValueError("a stage needs a layer to drag")
        self.document = document
        self.layer_index = layer_index
        self.picture = flatten(document)
        self.color = BLACK
        self.radius = 2
        self._press: tuple[int, int, int, int] | None = None
        self._stroke: tuple[int, int] | None = None
        self._under: Image | None = None
        self.lettering = Lettering(self)

    @property
    def layer(self):
        return self.document.layers[self.layer_index]

    def press(self, x: int, y: int) -> None:
        self._remember_under()
        self._press = (x, y, self.layer.x, self.layer.y)

    def shift(self, x: int, y: int) -> None:
        if self._press is None:
            return
        x0, y0, origin_x, origin_y = self._press
        self.layer.x = origin_x + (x - x0)
        self.layer.y = origin_y + (y - y0)

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
        self._remember_under()
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
        image = self.layer.image
        for px, py in points:
            stamp(image, px - self.layer.x, py - self.layer.y, self.color, self.radius)
        self._stroke = (x, y)
        if restack:
            self._restack()

    def _remember_under(self) -> None:
        index = self.layer_index
        if index < 0:
            index += len(self.document.layers)
        self._under = flatten_below(self.document, index)

    def _restack(self) -> None:
        if self._under is None:
            self.picture = flatten(self.document)
        else:
            self.picture = paint_layer(self._under, self.layer)


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
