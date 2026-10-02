"""The picture on screen. Dragging moves one layer; the pixels stay the flattened document."""

from sinopia.document import Document, flatten
from sinopia.image import Image


class Stage:
    def __init__(self, document: Document, layer_index: int = -1):
        if not document.layers:
            raise ValueError("a stage needs a layer to drag")
        self.document = document
        self.layer_index = layer_index
        self.picture = flatten(document)
        self._press: tuple[int, int, int, int] | None = None

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
