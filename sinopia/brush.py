"""A round brush. It paints the layer image and leaves the mask alone."""

from sinopia.image import Image

BLACK = (0, 0, 0, 255)


def stamp(image: Image, x: int, y: int, color: tuple[int, int, int, int], radius: int) -> None:
    """Paint a filled circle. `x` and `y` are pixels in the layer image."""
    if radius < 0:
        raise ValueError("radius must be zero or more")
    limit = radius * radius
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            if dx * dx + dy * dy > limit:
                continue
            px = x + dx
            py = y + dy
            if 0 <= px < image.width and 0 <= py < image.height:
                image.set(px, py, color)


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
