"""Type on a layer. Letters preview until Enter bakes them into the pixels."""

from sinopia.document import Layer, flatten
from sinopia.glyphs import ADVANCE, GLYPHS
from sinopia.image import Image


def place(image: Image, x: int, y: int, text: str, color: tuple[int, int, int, int]) -> None:
    """Draw `text` into the layer image. Lower case uses the upper-case glyph."""
    cursor = x
    for char in text:
        glyph = GLYPHS.get(char.upper())
        if glyph is None:
            raise ValueError(f"no glyph for {char!r}")
        for row, bits in enumerate(glyph):
            for col in range(5):
                if bits & (1 << (4 - col)):
                    px = cursor + col
                    py = y + row
                    if 0 <= px < image.width and 0 <= py < image.height:
                        image.set(px, py, color)
        cursor += ADVANCE


class Lettering:
    def __init__(self, stage):
        self.stage = stage
        self.active = False
        self.origin = (0, 0)
        self.text = ""

    def begin(self, x: int, y: int) -> None:
        if not isinstance(self.stage.target, Layer):
            return
        self.active = True
        self.origin = (x, y)
        self.text = ""
        self._preview()

    def insert(self, char: str) -> None:
        if not self.active or len(char) != 1:
            return
        if char.upper() not in GLYPHS:
            return
        self.text += char
        self._preview()

    def backspace(self) -> None:
        if not self.active or not self.text:
            return
        self.text = self.text[:-1]
        self._preview()

    def commit(self) -> None:
        if not self.active:
            return
        self._draw(self.stage.layer.image)
        self.active = False
        self.stage.picture = flatten(self.stage.document)

    def cancel(self) -> None:
        if not self.active:
            return
        self.active = False
        self.text = ""
        self.stage.picture = flatten(self.stage.document)

    def _preview(self) -> None:
        original = bytearray(self.stage.layer.image.pixels)
        self._draw(self.stage.layer.image)
        self.stage.picture = flatten(self.stage.document)
        self.stage.layer.image.pixels[:] = original

    def _draw(self, image: Image) -> None:
        x, y = self.stage.layer_point(self.origin[0], self.origin[1])
        place(image, x, y, self.text, self.stage.color)
