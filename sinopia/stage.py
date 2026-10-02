"""The picture on screen. Dragging moves one layer; the brush paints that layer."""

from sinopia.brush import BLACK, line, stamp
from sinopia.document import Document, flatten
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
        self.lettering = Lettering(self)

    @property
    def layer(self):
        return self.document.layers[self.layer_index]

    def press(self, x: int, y: int) -> None:
        self._press = (x, y, self.layer.x, self.layer.y)

    def drag(self, x: int, y: int) -> None:
        if self._press is None:
            return
        x0, y0, origin_x, origin_y = self._press
        self.layer.x = origin_x + (x - x0)
        self.layer.y = origin_y + (y - y0)
        self.picture = flatten(self.document)

    def release(self, x: int, y: int) -> None:
        self.drag(x, y)
        self._press = None

    def brush_press(self, x: int, y: int) -> None:
        self._stroke = None
        self._brush_to(x, y)

    def brush_drag(self, x: int, y: int) -> None:
        if self._stroke is None:
            return
        self._brush_to(x, y)

    def brush_release(self, x: int, y: int) -> None:
        if self._stroke is None:
            return
        self._brush_to(x, y)
        self._stroke = None

    def _brush_to(self, x: int, y: int) -> None:
        if self._stroke is None:
            points = [(x, y)]
        else:
            points = line(self._stroke, (x, y))[1:]
        image = self.layer.image
        for px, py in points:
            stamp(image, px - self.layer.x, py - self.layer.y, self.color, self.radius)
        self._stroke = (x, y)
        self.picture = flatten(self.document)


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
