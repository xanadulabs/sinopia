"""An 8-bit RGBA image. Straight alpha, not premultiplied."""


class Image:
    def __init__(self, width: int, height: int, fill: tuple[int, int, int, int] = (0, 0, 0, 0)):
        if width < 1 or height < 1:
            raise ValueError("image must be at least 1x1")
        self.width = width
        self.height = height
        pixel = bytes(int(c) & 255 for c in fill)
        self.pixels = bytearray(pixel * (width * height))

    def __len__(self) -> int:
        return self.width * self.height

    def get(self, x: int, y: int) -> tuple[int, int, int, int]:
        i = (y * self.width + x) * 4
        p = self.pixels
        return p[i], p[i + 1], p[i + 2], p[i + 3]

    def set(self, x: int, y: int, pixel: tuple[int, int, int, int]) -> None:
        i = (y * self.width + x) * 4
        self.pixels[i : i + 4] = bytes(int(c) & 255 for c in pixel)
