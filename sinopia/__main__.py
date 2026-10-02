"""Write out/proof.png: a red field with a soft green circle masked over it."""

from pathlib import Path

from sinopia.composite import composite
from sinopia.image import Image
from sinopia.png import write_png

SIZE = 96


def _disk_mask() -> bytearray:
    mask = bytearray(SIZE * SIZE)
    center = (SIZE - 1) / 2
    radius = SIZE * 0.35
    for y in range(SIZE):
        for x in range(SIZE):
            distance = ((x - center) ** 2 + (y - center) ** 2) ** 0.5
            falloff = 1 - (distance - radius * 0.55) / (radius * 0.45)
            mask[y * SIZE + x] = int(max(0, min(255, round(falloff * 255))))
    return mask


def proof() -> Image:
    red = Image(SIZE, SIZE, (180, 24, 24, 255))
    green = Image(SIZE, SIZE, (32, 140, 64, 255))
    return composite(red, green, _disk_mask())


def main() -> None:
    image = proof()
    # Corner of the mask is 0, so the red layer shows through unchanged.
    if image.get(0, 0) != (180, 24, 24, 255):
        raise SystemExit(f"corner pixel was {image.get(0, 0)}")
    # Center of the mask is 255, so the green layer replaces the red.
    mid = SIZE // 2
    if image.get(mid, mid) != (32, 140, 64, 255):
        raise SystemExit(f"center pixel was {image.get(mid, mid)}")

    out = Path("out")
    out.mkdir(exist_ok=True)
    destination = out / "proof.png"
    write_png(destination, image)
    print(destination)


if __name__ == "__main__":
    main()
