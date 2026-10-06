"""Steps you can walk back through. The current picture is one of them."""

from sinopia.document import Document, Group, Layer
from sinopia.image import Image


class History:
    def __init__(self, document: Document):
        self.document = document
        self.steps: list[tuple[str, tuple]] = [("New", capture(document))]
        self.index = 0

    def commit(self, label: str) -> bool:
        snap = capture(self.document)
        if snap == self.steps[self.index][1]:
            return False
        del self.steps[self.index + 1 :]
        self.steps.append((label, snap))
        overflow = len(self.steps) - 40
        if overflow > 0:
            del self.steps[:overflow]
        self.index = len(self.steps) - 1
        return True

    def can_undo(self) -> bool:
        return self.index > 0

    def can_redo(self) -> bool:
        return self.index < len(self.steps) - 1

    def undo(self) -> bool:
        if not self.can_undo():
            return False
        self.index -= 1
        restore(self.document, self.steps[self.index][1])
        return True

    def redo(self) -> bool:
        if not self.can_redo():
            return False
        self.index += 1
        restore(self.document, self.steps[self.index][1])
        return True

    def jump(self, index: int) -> None:
        self.index = index
        restore(self.document, self.steps[self.index][1])


def capture(document: Document) -> tuple:
    return (document.width, document.height, tuple(_capture(item) for item in document.layers))


def restore(document: Document, snap: tuple) -> None:
    width, height, items = snap
    document.width = width
    document.height = height
    document.layers = [_rebuild(item) for item in items]


def _capture(item: Layer | Group) -> tuple:
    if isinstance(item, Group):
        children = tuple(_capture(child) for child in item.children)
        return ("group", item.name, item.opacity, item.blend, item.x, item.y, children)
    mask = None if item.mask is None else bytes(item.mask)
    return (
        "layer",
        item.name,
        bytes(item.image.pixels),
        item.image.width,
        item.image.height,
        mask,
        item.opacity,
        item.blend,
        item.x,
        item.y,
        item.shadow,
    )


def _rebuild(item: tuple) -> Layer | Group:
    if item[0] == "group":
        _, name, opacity, blend, x, y, children = item
        return Group(name, [_rebuild(child) for child in children], opacity, blend, x, y)
    _, name, pixels, width, height, mask, opacity, blend, x, y, shadow = item
    image = Image(width, height)
    image.pixels[:] = pixels
    return Layer(name, image, None if mask is None else bytearray(mask), opacity, blend, x, y, shadow)
