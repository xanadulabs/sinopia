"""The first picture: a red field and a soft green circle."""

from sinopia.document import Document, Layer
from sinopia.image import Image

SIZE = 96


def disk_mask() -> bytearray:
    mask = bytearray(SIZE * SIZE)
    center = (SIZE - 1) / 2
    radius = SIZE * 0.35
    for y in range(SIZE):
        for x in range(SIZE):
            distance = ((x - center) ** 2 + (y - center) ** 2) ** 0.5
            falloff = 1 - (distance - radius * 0.55) / (radius * 0.45)
            mask[y * SIZE + x] = int(max(0, min(255, round(falloff * 255))))
    return mask


def proof_document() -> Document:
    red = Image(SIZE, SIZE, (180, 24, 24, 255))
    green = Image(SIZE, SIZE, (32, 140, 64, 255))
    return Document(
        SIZE,
        SIZE,
        [
            Layer("red", red),
            Layer("green", green, disk_mask()),
        ],
    )
