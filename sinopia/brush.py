"""A round brush. It paints the layer image and leaves the mask alone."""

from sinopia.image import Image

BLACK = (0, 0, 0, 255)


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
