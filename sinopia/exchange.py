"""Open a PNG or JPEG, and write the flattened picture back out.

The folder of PNGs plus stack.txt stays the file you keep. These are copies.
"""

from pathlib import Path

from sinopia.image import Image
from sinopia.jpeg import read_jpeg, write_jpeg
from sinopia.png import read_rgba, write_png


def read_picture(path: Path | str) -> Image:
    suffix = Path(path).suffix.lower()
    if suffix != ".png" and suffix not in (".jpg", ".jpeg"):
        raise ValueError("open a PNG or JPEG")
    from sinopia.pixbuf import try_load

    fast = try_load(path)
    if fast is not None:
        return fast
    if suffix == ".png":
        return read_rgba(path)
    return read_jpeg(path)


def write_picture(path: Path | str, image: Image) -> None:
    suffix = Path(path).suffix.lower()
    if suffix == ".png":
        write_png(path, image)
        return
    if suffix in (".jpg", ".jpeg"):
        write_jpeg(path, image)
        return
    raise ValueError("save as a PNG or JPEG")


def layer_name(path: Path | str) -> str:
    cleaned = []
    for char in Path(path).stem:
        cleaned.append(char if char.isalnum() or char in "-_" else "-")
    name = "".join(cleaned).strip("-")
    return name or "image"
