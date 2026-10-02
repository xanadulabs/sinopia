"""A document is a folder: stack.txt plus one PNG per layer.

stack.txt is the description. The PNGs are the pixels. Bottom layer first.

    size 96 96
    layer red.png normal 255 - 0 0
    layer green.png normal 255 green.mask.png 0 0

The last two numbers are the layer's position. Older files omit them and sit at 0 0.
"""

from pathlib import Path

from sinopia.composite import composite
from sinopia.image import Image
from sinopia.png import read_mask, read_png, write_mask, write_png
from sinopia.style import shadow_image


class Layer:
    def __init__(
        self,
        name: str,
        image: Image,
        mask: bytearray | None = None,
        opacity: int = 255,
        blend: str = "normal",
        x: int = 0,
        y: int = 0,
        shadow: tuple[int, int] | None = None,
    ):
        self.name = name
        self.image = image
        self.mask = mask
        self.opacity = opacity
        self.blend = blend
        self.x = x
        self.y = y
        self.shadow = shadow


class Document:
    def __init__(self, width: int, height: int, layers: list[Layer] | None = None):
        if width < 1 or height < 1:
            raise ValueError("document must be at least 1x1")
        self.width = width
        self.height = height
        self.layers = [] if layers is None else layers


def flatten(document: Document) -> Image:
    """Composite every layer, bottom to top, over a transparent canvas."""
    acc = Image(document.width, document.height)
    for layer in document.layers:
        if layer.blend != "normal":
            raise ValueError(f"unsupported blend {layer.blend}")
        if layer.image.width != document.width or layer.image.height != document.height:
            raise ValueError(f"layer {layer.name} is the wrong size")
        if layer.mask is not None and len(layer.mask) != document.width * document.height:
            raise ValueError(f"layer {layer.name} mask is the wrong size")
        if layer.shadow is not None:
            shift_x, shift_y = layer.shadow
            acc = composite(
                acc,
                shadow_image(layer),
                None,
                255,
                layer.x + shift_x,
                layer.y + shift_y,
            )
        acc = composite(acc, layer.image, layer.mask, layer.opacity, layer.x, layer.y)
    return acc


def _layer_name(filename: str) -> str:
    if not filename.endswith(".png") or filename.endswith(".mask.png"):
        raise ValueError(f"layer file must be a .png name, got {filename}")
    name = filename[: -len(".png")]
    _check_name(name)
    return name


def _check_name(name: str) -> None:
    if not name or name in {".", ".."}:
        raise ValueError("empty layer name")
    if any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in name):
        raise ValueError(f"layer name {name} has characters that are not safe in a filename")


def save(document: Document, folder: Path | str) -> None:
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    seen: set[str] = set()
    lines = [f"size {document.width} {document.height}"]
    for layer in document.layers:
        _check_name(layer.name)
        if layer.name in seen:
            raise ValueError(f"duplicate layer name {layer.name}")
        seen.add(layer.name)
        if layer.image.width != document.width or layer.image.height != document.height:
            raise ValueError(f"layer {layer.name} is the wrong size")
        image_name = f"{layer.name}.png"
        write_png(folder / image_name, layer.image)
        mask_name = "-"
        if layer.mask is not None:
            if len(layer.mask) != document.width * document.height:
                raise ValueError(f"layer {layer.name} mask is the wrong size")
            mask_name = f"{layer.name}.mask.png"
            write_mask(folder / mask_name, document.width, document.height, layer.mask)
        if layer.blend != "normal":
            raise ValueError(f"unsupported blend {layer.blend}")
        if not 0 <= layer.opacity <= 255:
            raise ValueError("opacity must be 0-255")
        line = f"layer {image_name} {layer.blend} {layer.opacity} {mask_name} {layer.x} {layer.y}"
        if layer.shadow is not None:
            line += f" shadow {layer.shadow[0]} {layer.shadow[1]}"
        lines.append(line)
    (folder / "stack.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def load(folder: Path | str) -> Document:
    folder = Path(folder)
    text = (folder / "stack.txt").read_text(encoding="utf-8")
    width = height = None
    layers: list[Layer] = []
    seen: set[str] = set()
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        if parts[0] == "size":
            if width is not None or len(parts) != 3:
                raise ValueError("size must be one line: size WIDTH HEIGHT")
            width = int(parts[1])
            height = int(parts[2])
            continue
        if parts[0] != "layer" or len(parts) not in (5, 7, 10):
            raise ValueError(f"bad stack line: {line}")
        if width is None or height is None:
            raise ValueError("size line must come first")
        image_name, blend, opacity_text, mask_name = parts[1:5]
        origin_x = int(parts[5]) if len(parts) >= 7 else 0
        origin_y = int(parts[6]) if len(parts) >= 7 else 0
        shadow = None
        if len(parts) == 10:
            if parts[7] != "shadow":
                raise ValueError(f"bad stack line: {line}")
            shadow = (int(parts[8]), int(parts[9]))
        name = _layer_name(image_name)
        if name in seen:
            raise ValueError(f"duplicate layer name {name}")
        seen.add(name)
        if blend != "normal":
            raise ValueError(f"unsupported blend {blend}")
        opacity = int(opacity_text)
        if not 0 <= opacity <= 255:
            raise ValueError("opacity must be 0-255")
        image = read_png(folder / image_name)
        if image.width != width or image.height != height:
            raise ValueError(f"{image_name} is the wrong size")
        mask = None
        if mask_name != "-":
            if Path(mask_name).name != mask_name:
                raise ValueError("mask name must be a file in the folder")
            mask_width, mask_height, mask = read_mask(folder / mask_name)
            if mask_width != width or mask_height != height:
                raise ValueError(f"{mask_name} is the wrong size")
        layers.append(Layer(name, image, mask, opacity, blend, origin_x, origin_y, shadow))
    if width is None or height is None:
        raise ValueError("stack.txt has no size")
    return Document(width, height, layers)
