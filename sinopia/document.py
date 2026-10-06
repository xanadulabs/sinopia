"""A document is a folder: stack.txt plus one PNG per layer.

stack.txt is the description. The PNGs are the pixels. Bottom layer first.

    size 96 96
    layer red.png normal 255 - 0 0
    group bunch normal 255 0 0
    layer green.png normal 255 green.mask.png 0 0
    endgroup

The last two numbers on a layer are its position. A group line ends with its position, and the group's offset moves everything inside it.
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


class Group:
    def __init__(
        self,
        name: str,
        children: list | None = None,
        opacity: int = 255,
        blend: str = "normal",
        x: int = 0,
        y: int = 0,
    ):
        self.name = name
        self.children = [] if children is None else children
        self.opacity = opacity
        self.blend = blend
        self.x = x
        self.y = y


class Document:
    def __init__(self, width: int, height: int, layers: list[Layer] | None = None):
        if width < 1 or height < 1:
            raise ValueError("document must be at least 1x1")
        self.width = width
        self.height = height
        self.layers = [] if layers is None else layers


def paint_layer(under: Image, layer: Layer, dx: int = 0, dy: int = 0) -> Image:
    """Composite one layer, and its shadow, over an image that is left unchanged."""
    if layer.blend != "normal":
        raise ValueError(f"unsupported blend {layer.blend}")
    if layer.image.width != under.width or layer.image.height != under.height:
        raise ValueError(f"layer {layer.name} is the wrong size")
    if layer.mask is not None and len(layer.mask) != under.width * under.height:
        raise ValueError(f"layer {layer.name} mask is the wrong size")
    origin_x = layer.x + dx
    origin_y = layer.y + dy
    if layer.shadow is not None:
        shift_x, shift_y = layer.shadow
        under = composite(under, shadow_image(layer), None, 255, origin_x + shift_x, origin_y + shift_y)
    return composite(under, layer.image, layer.mask, layer.opacity, origin_x, origin_y)


def paint_item(under: Image, item: Layer | Group, dx: int = 0, dy: int = 0) -> Image:
    """Composite a layer, or a group of them, onto `under`."""
    if isinstance(item, Group):
        inner = Image(under.width, under.height)
        for child in item.children:
            inner = paint_item(inner, child, dx + item.x, dy + item.y)
        plate = Layer(item.name, inner, opacity=item.opacity, blend=item.blend)
        return paint_layer(under, plate)
    return paint_layer(under, item, dx, dy)


def flatten(document: Document) -> Image:
    """Composite every layer, bottom to top, over a transparent canvas."""
    acc = Image(document.width, document.height)
    for item in document.layers:
        acc = paint_item(acc, item)
    return acc


def flatten_below(document: Document, index: int) -> Image:
    """Composite the top-level items under `index`."""
    if index < 0:
        index += len(document.layers)
    acc = Image(document.width, document.height)
    for item in document.layers[:index]:
        acc = paint_item(acc, item)
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
    for item in document.layers:
        _write_item(item, lines, seen, folder, document)
    (folder / "stack.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_item(item: Layer | Group, lines: list[str], seen: set[str], folder: Path, document: Document) -> None:
    _check_name(item.name)
    if item.name in seen:
        raise ValueError(f"duplicate layer name {item.name}")
    seen.add(item.name)
    if isinstance(item, Group):
        if item.blend != "normal":
            raise ValueError(f"unsupported blend {item.blend}")
        if not 0 <= item.opacity <= 255:
            raise ValueError("opacity must be 0-255")
        lines.append(f"group {item.name} {item.blend} {item.opacity} {item.x} {item.y}")
        for child in item.children:
            _write_item(child, lines, seen, folder, document)
        lines.append("endgroup")
        return
    if item.image.width != document.width or item.image.height != document.height:
        raise ValueError(f"layer {item.name} is the wrong size")
    image_name = f"{item.name}.png"
    write_png(folder / image_name, item.image)
    mask_name = "-"
    if item.mask is not None:
        if len(item.mask) != document.width * document.height:
            raise ValueError(f"layer {item.name} mask is the wrong size")
        mask_name = f"{item.name}.mask.png"
        write_mask(folder / mask_name, document.width, document.height, item.mask)
    if item.blend != "normal":
        raise ValueError(f"unsupported blend {item.blend}")
    if not 0 <= item.opacity <= 255:
        raise ValueError("opacity must be 0-255")
    line = f"layer {image_name} {item.blend} {item.opacity} {mask_name} {item.x} {item.y}"
    if item.shadow is not None:
        line += f" shadow {item.shadow[0]} {item.shadow[1]}"
    lines.append(line)


def load(folder: Path | str) -> Document:
    folder = Path(folder)
    text = (folder / "stack.txt").read_text(encoding="utf-8")
    width = height = None
    layers: list = []
    stack: list[list] = [layers]
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
        if width is None or height is None:
            raise ValueError("size line must come first")
        if parts[0] == "endgroup" and len(parts) == 1:
            if len(stack) == 1:
                raise ValueError("endgroup without a group")
            stack.pop()
            continue
        if parts[0] == "group" and len(parts) == 6:
            name, blend, opacity_text, origin_x, origin_y = parts[1:]
            _claim_name(name, seen)
            if blend != "normal":
                raise ValueError(f"unsupported blend {blend}")
            opacity = int(opacity_text)
            if not 0 <= opacity <= 255:
                raise ValueError("opacity must be 0-255")
            group = Group(name, [], opacity, blend, int(origin_x), int(origin_y))
            stack[-1].append(group)
            stack.append(group.children)
            continue
        if parts[0] != "layer" or len(parts) not in (5, 7, 10):
            raise ValueError(f"bad stack line: {line}")
        image_name, blend, opacity_text, mask_name = parts[1:5]
        origin_x = int(parts[5]) if len(parts) >= 7 else 0
        origin_y = int(parts[6]) if len(parts) >= 7 else 0
        shadow = None
        if len(parts) == 10:
            if parts[7] != "shadow":
                raise ValueError(f"bad stack line: {line}")
            shadow = (int(parts[8]), int(parts[9]))
        name = _layer_name(image_name)
        _claim_name(name, seen)
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
        stack[-1].append(Layer(name, image, mask, opacity, blend, origin_x, origin_y, shadow))
    if width is None or height is None:
        raise ValueError("stack.txt has no size")
    if len(stack) != 1:
        raise ValueError("a group was not closed")
    return Document(width, height, layers)


def _claim_name(name: str, seen: set[str]) -> None:
    _check_name(name)
    if name in seen:
        raise ValueError(f"duplicate layer name {name}")
    seen.add(name)


def walk(items: list):
    for item in items:
        yield item
        if isinstance(item, Group):
            yield from walk(item.children)


def parent_offset(document: Document, node: Layer | Group) -> tuple[int, int]:
    """How far parent groups have already moved this layer."""

    def search(items: list, dx: int, dy: int):
        for item in items:
            if item is node:
                return dx, dy
            if isinstance(item, Group):
                found = search(item.children, dx + item.x, dy + item.y)
                if found is not None:
                    return found
        return None

    found = search(document.layers, 0, 0)
    if found is None:
        raise ValueError(f"{node.name} is not in the document")
    return found


def _locate(document: Document, node: Layer | Group) -> tuple[list, int]:
    def search(items: list):
        for index, item in enumerate(items):
            if item is node:
                return items, index
            if isinstance(item, Group):
                found = search(item.children)
                if found is not None:
                    return found
        return None

    found = search(document.layers)
    if found is None:
        raise ValueError(f"{node.name} is not in the document")
    return found


def _fresh_name(document: Document, stem: str) -> str:
    taken = {item.name for item in walk(document.layers)}
    if stem not in taken:
        return stem
    number = 2
    while f"{stem}-{number}" in taken:
        number += 1
    return f"{stem}-{number}"


def _layer_count(items: list) -> int:
    total = 0
    for item in items:
        if isinstance(item, Group):
            total += _layer_count(item.children)
        else:
            total += 1
    return total


def layer_rows(document: Document) -> list[tuple[int, Layer | Group]]:
    """Panel order: the top of the stack first, children indented under their group."""
    rows: list[tuple[int, Layer | Group]] = []

    def visit(items: list, depth: int) -> None:
        for item in reversed(items):
            rows.append((depth, item))
            if isinstance(item, Group):
                visit(item.children, depth + 1)

    visit(document.layers, 0)
    return rows


def add_layer(document: Document, above: Layer | Group) -> Layer:
    """Insert an empty layer above `above`. Inside a selected group, it becomes the top child."""
    if isinstance(above, Group):
        parent = above.children
        index = len(parent)
    else:
        parent, index = _locate(document, above)
        index += 1
    layer = Layer(_fresh_name(document, "layer"), Image(document.width, document.height))
    parent.insert(index, layer)
    return layer


def delete_item(document: Document, node: Layer | Group) -> Layer | Group | None:
    """Remove `node`. Returns what to select next, or None if this is the last layer."""
    removed = _layer_count([node])
    if _layer_count(document.layers) - removed < 1:
        return None
    parent, index = _locate(document, node)
    if index + 1 < len(parent):
        neighbor = parent[index + 1]
    elif index > 0:
        neighbor = parent[index - 1]
    else:
        neighbor = None
        for item in walk(document.layers):
            if isinstance(item, Group) and item.children is parent:
                neighbor = item
                break
    del parent[index]
    return neighbor


def _contains(node: Layer | Group, other: Layer | Group) -> bool:
    if not isinstance(node, Group):
        return False
    return any(item is other for item in walk(node.children))


def _detach(document: Document, node: Layer | Group) -> None:
    parent, index = _locate(document, node)
    del parent[index]


def place_above(document: Document, node: Layer | Group, target: Layer | Group) -> bool:
    """Put `node` just above `target` in the picture, as its sibling."""
    if node is target or _contains(node, target):
        return False
    _detach(document, node)
    parent, index = _locate(document, target)
    parent.insert(index + 1, node)
    return True


def place_below(document: Document, node: Layer | Group, target: Layer | Group) -> bool:
    """Put `node` just under `target` in the picture, as its sibling."""
    if node is target or _contains(node, target):
        return False
    _detach(document, node)
    parent, index = _locate(document, target)
    parent.insert(index, node)
    return True


def place_into(document: Document, node: Layer | Group, group: Group) -> bool:
    """Make `node` the top layer inside `group`."""
    if node is group or _contains(node, group):
        return False
    _detach(document, node)
    group.children.append(node)
    return True


def group_item(document: Document, node: Layer | Group) -> Group:
    """Wrap `node` in a new group and return that group."""
    parent, index = _locate(document, node)
    group = Group(_fresh_name(document, "group"), [node])
    parent[index] = group
    return group
