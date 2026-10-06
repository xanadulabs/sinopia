"""Type on a layer. Letters preview until Enter bakes them into the pixels."""

from sinopia.document import Layer, flatten
from sinopia.glyphs import GLYPHS
from sinopia.image import Image
from sinopia.typeface import TextStyle, place_text


def place(
    image: Image,
    x: int,
    y: int,
    text: str,
    color: tuple[int, int, int, int],
    style: TextStyle | None = None,
) -> None:
    """Draw `text` into the layer image. The built-in face still maps lower case to upper."""
    place_text(image, x, y, text, color, style)


class Lettering:
    def __init__(self, stage):
        self.stage = stage
        self.active = False
        self.origin = (0, 0)
        self.text = ""
        self.style = TextStyle()

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
        if not self._accepts(char):
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

    def refresh(self) -> None:
        if self.active:
            self._preview()

    def _accepts(self, char: str) -> bool:
        if self.style.family == "Sinopia":
            return char.upper() in GLYPHS
        return char.isprintable()

    def _preview(self) -> None:
        original = bytearray(self.stage.layer.image.pixels)
        self._draw(self.stage.layer.image)
        self.stage.picture = flatten(self.stage.document)
        self.stage.layer.image.pixels[:] = original

    def _draw(self, image: Image) -> None:
        x, y = self.stage.layer_point(self.origin[0], self.origin[1])
        place(image, x, y, self.text, self.stage.color, self.style)
