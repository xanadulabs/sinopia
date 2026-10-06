"""A round brush. It paints the layer image and leaves the mask alone.

Diameter is the width of the tip, in pixels. Hardness is the feather of that
tip: 100 is solid, 0 fades from the middle to the rim. Flow is how much of
the ink each dab lays down. Opacity is the cap for the whole stroke, so
scrubbing builds up and then stops. Dabs sit a quarter of the diameter apart.
"""

import math

from sinopia.image import Image

BLACK = (0, 0, 0, 255)
SPACING = 25


def stamp(image: Image, x: int, y: int, color: tuple[int, int, int, int], radius: int) -> None:
    """Paint a filled circle. `x` and `y` are pixels in the layer image."""
    if radius < 0:
        raise ValueError("radius must be zero or more")
    limit = radius * radius
    ink = bytes(int(channel) & 255 for channel in color)
    pixels = image.pixels
    width = image.width
    height = image.height
    for dy in range(-radius, radius + 1):
        py = y + dy
        if not 0 <= py < height:
            continue
        row = py * width
        for dx in range(-radius, radius + 1):
            if dx * dx + dy * dy > limit:
                continue
            px = x + dx
            if 0 <= px < width:
                start = (row + px) * 4
                pixels[start : start + 4] = ink


def tip_offsets(diameter: int, hardness: int) -> list[tuple[int, int, int]]:
    """Pixels in the tip, as dx, dy, and an alpha from 0 to 255."""
    diameter = max(1, int(diameter))
    hardness = max(0, min(100, int(hardness)))
    radius = (diameter - 1) / 2
    limit = radius * radius
    core = radius * hardness / 100
    span = radius - core
    reach = math.floor(radius + 1e-9)
    offsets: list[tuple[int, int, int]] = []
    for dy in range(-reach, reach + 1):
        for dx in range(-reach, reach + 1):
            dist2 = dx * dx + dy * dy
            if dist2 > limit:
                continue
            if hardness >= 100 or span <= 0:
                alpha = 255
            else:
                dist = math.sqrt(dist2)
                if dist <= core:
                    alpha = 255
                else:
                    alpha = round((radius - dist) / span * 255)
                    if alpha <= 0:
                        continue
                    if alpha > 255:
                        alpha = 255
            offsets.append((dx, dy, alpha))
    return offsets


def dab(
    image: Image,
    x: int,
    y: int,
    color: tuple[int, int, int, int],
    offsets: list[tuple[int, int, int]],
    flow: int,
    opacity: int,
    origin: bytes,
    coverage: bytearray,
) -> None:
    """Add one dab. Coverage builds up to `opacity` and does not pass it."""
    flow_byte = _percent(flow)
    cap = _percent(opacity)
    if flow_byte == 0 or cap == 0 or not offsets:
        return
    ink = bytes(int(channel) & 255 for channel in color)
    pixels = image.pixels
    width = image.width
    height = image.height
    for dx, dy, tip in offsets:
        px = x + dx
        py = y + dy
        if not (0 <= px < width and 0 <= py < height):
            continue
        index = py * width + px
        add = tip * flow_byte // 255
        if add == 0:
            continue
        new = coverage[index] + add
        if new > cap:
            new = cap
        if new == coverage[index]:
            continue
        coverage[index] = new
        start = index * 4
        if new >= 255:
            pixels[start : start + 4] = ink
            continue
        keep = 255 - new
        mixed = bytearray(4)
        for channel in range(4):
            mixed[channel] = (ink[channel] * new + origin[start + channel] * keep + 127) // 255
        pixels[start : start + 4] = mixed


def _percent(value: int) -> int:
    value = max(0, min(100, int(value)))
    return (value * 255 + 50) // 100


def line(start: tuple[int, int], end: tuple[int, int]) -> list[tuple[int, int]]:
    """Every pixel from start to end, including both ends."""
    x0, y0 = start
    x1, y1 = end
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    error = dx - dy
    points: list[tuple[int, int]] = []
    while True:
        points.append((x0, y0))
        if x0 == x1 and y0 == y1:
            return points
        doubled = 2 * error
        if doubled > -dy:
            error -= dy
            x0 += sx
        if doubled < dx:
            error += dx
            y0 += sy
