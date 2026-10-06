"""The picture on screen. Dragging moves one layer; the brush paints that layer."""

from sinopia.brush import BLACK, line, stamp
from sinopia.composite import _covered
from sinopia.document import Document, Group, Layer, flatten, parent_offset
from sinopia.image import Image
from sinopia.lettering import Lettering


class Stage:
    def __init__(self, document: Document):
        if not document.layers:
            raise ValueError("a stage needs a layer to drag")
        self.document = document
        self.target: Layer | Group = document.layers[-1]
        self.picture = flatten(document)
        self.color = BLACK
        self.radius = 2
        self._press: tuple[int, int, int, int] | None = None
        self._stroke: tuple[int, int] | None = None
        self._transform: dict | None = None
        self._box: tuple[int, int, int, int] | None = None
        self.lettering = Lettering(self)

    @property
    def layer(self) -> Layer | Group:
        return self.target

    def pick(self, x: int, y: int) -> Layer | None:
        """The top layer that covers this document point, not merely the top of the stack."""
        return _top_layer(self.document.layers, x, y, 0, 0, 255)

    def select(self, node: Layer | Group) -> None:
        if node is self.target:
            return
        self.retarget(node)

    def retarget(self, node: Layer | Group) -> None:
        if self.lettering.active and node is not self.target:
            self.lettering.cancel()
        self.target = node
        self._press = None
        self._stroke = None
        self._transform = None
        self._box = None
        self.picture = flatten(self.document)

    def layer_point(self, x: int, y: int) -> tuple[int, int]:
        group_x, group_y = parent_offset(self.document, self.target)
        return x - self.target.x - group_x, y - self.target.y - group_y

    def press(self, x: int, y: int) -> None:
        self._press = (x, y, self.target.x, self.target.y)

    def shift(self, x: int, y: int) -> None:
        if self._press is None:
            return
        x0, y0, origin_x, origin_y = self._press
        self.target.x = origin_x + (x - x0)
        self.target.y = origin_y + (y - y0)

    def drag(self, x: int, y: int) -> None:
        self.shift(x, y)
        if self._press is not None:
            self._restack()

    def reveal(self) -> None:
        self._restack()

    def release(self, x: int, y: int) -> None:
        self.drag(x, y)
        self._press = None

    def brush_press(self, x: int, y: int) -> None:
        if not isinstance(self.target, Layer):
            return
        self._stroke = None
        self._brush_to(x, y)

    def brush_drag(self, x: int, y: int) -> None:
        if self._stroke is None:
            return
        self._brush_to(x, y, restack=False)

    def brush_release(self, x: int, y: int) -> None:
        if self._stroke is None:
            return
        self._brush_to(x, y)
        self._stroke = None

    def _brush_to(self, x: int, y: int, restack: bool = True) -> None:
        if self._stroke is None:
            points = [(x, y)]
        else:
            points = line(self._stroke, (x, y))[1:]
        if not isinstance(self.target, Layer):
            return
        image = self.target.image
        for px, py in points:
            local_x, local_y = self.layer_point(px, py)
            stamp(image, local_x, local_y, self.color, self.radius)
        self._stroke = (x, y)
        if restack:
            self._restack()

    def content_box(self) -> tuple[int, int, int, int] | None:
        """Exclusive document box around the layer's opaque pixels. None for a group or an empty layer."""
        if self._box is not None:
            return self._box
        if not isinstance(self.target, Layer):
            return None
        bounds = _opaque_bounds(self.target.image)
        if bounds is None:
            return None
        left, top, right, bottom = bounds
        group_x, group_y = parent_offset(self.document, self.target)
        origin_x = self.target.x + group_x
        origin_y = self.target.y + group_y
        return (left + origin_x, top + origin_y, right + origin_x + 1, bottom + origin_y + 1)

    def transform_press(self, handle: str, x: int, y: int) -> None:
        if not isinstance(self.target, Layer):
            self._transform = None
            return
        box = self.content_box()
        if box is None:
            return
        image = self.target.image
        group_x, group_y = parent_offset(self.document, self.target)
        self._transform = {
            "handle": handle,
            "press": (x, y),
            "box": box,
            "pixels": bytes(image.pixels),
            "mask": None if self.target.mask is None else bytes(self.target.mask),
            "origin": (self.target.x, self.target.y),
            "offset": (self.target.x + group_x, self.target.y + group_y),
        }

    def transform_drag(self, x: int, y: int, constrain: bool = False) -> None:
        """Scale from the opposite corner, or move the layer when the pointer started inside."""
        if self._transform is None or not isinstance(self.target, Layer):
            return
        handle = self._transform["handle"]
        press_x, press_y = self._transform["press"]
        left, top, right, bottom = self._transform["box"]
        if handle == "move":
            origin_x, origin_y = self._transform["origin"]
            self.target.x = origin_x + (x - press_x)
            self.target.y = origin_y + (y - press_y)
            self._box = (left + (x - press_x), top + (y - press_y), right + (x - press_x), bottom + (y - press_y))
            return
        dx = x - press_x
        dy = y - press_y
        new_left, new_top, new_right, new_bottom = left, top, right, bottom
        if "e" in handle:
            new_right = right + dx
        if "w" in handle:
            new_left = left + dx
        if "s" in handle:
            new_bottom = bottom + dy
        if "n" in handle:
            new_top = top + dy
        if new_right < new_left + 1:
            if "w" in handle:
                new_left = new_right - 1
            else:
                new_right = new_left + 1
        if new_bottom < new_top + 1:
            if "n" in handle:
                new_top = new_bottom - 1
            else:
                new_bottom = new_top + 1
        if constrain and handle in ("nw", "ne", "se", "sw"):
            new_left, new_top, new_right, new_bottom = _uniform(
                handle, left, top, right, bottom, new_left, new_top, new_right, new_bottom
            )
        self._box = (new_left, new_top, new_right, new_bottom)
        self._resample_box(new_left, new_top, new_right, new_bottom)

    def transform_release(self, x: int, y: int, constrain: bool = False) -> None:
        if self._transform is None:
            return
        self.transform_drag(x, y, constrain)
        self._transform = None
        self._box = None
        self._restack()

    def _resample_box(self, left: int, top: int, right: int, bottom: int) -> None:
        gesture = self._transform
        if gesture is None or not isinstance(self.target, Layer):
            return
        src_left, src_top, src_right, src_bottom = gesture["box"]
        src_pixels = gesture["pixels"]
        src_mask = gesture["mask"]
        offset_x, offset_y = gesture["offset"]
        image = self.target.image
        width, height = image.width, image.height
        src_w = src_right - src_left
        src_h = src_bottom - src_top
        dest_w = right - left
        dest_h = bottom - top
        out = bytearray(width * height * 4)
        mask_out = bytearray(width * height) if src_mask is not None else None
        y_start = max(top, offset_y)
        y_stop = min(bottom, offset_y + height)
        x_start = max(left, offset_x)
        x_stop = min(right, offset_x + width)
        for py in range(y_start, y_stop):
            sy = src_top + (py - top) * src_h // dest_h
            local_y = py - offset_y
            for px in range(x_start, x_stop):
                sx = src_left + (px - left) * src_w // dest_w
                local_x = px - offset_x
                si = ((sy - offset_y) * width + (sx - offset_x)) * 4
                di = (local_y * width + local_x) * 4
                out[di : di + 4] = src_pixels[si : si + 4]
                if mask_out is not None and src_mask is not None:
                    mask_out[local_y * width + local_x] = src_mask[(sy - offset_y) * width + (sx - offset_x)]
        image.pixels[:] = out
        if mask_out is not None and self.target.mask is not None:
            self.target.mask[:] = mask_out

    def _restack(self) -> None:
        self.picture = flatten(self.document)


def _top_layer(items: list, x: int, y: int, dx: int, dy: int, opacity: int) -> Layer | None:
    if opacity <= 0:
        return None
    for item in reversed(items):
        if isinstance(item, Group):
            child_opacity = opacity * item.opacity // 255
            hit = _top_layer(item.children, x, y, dx + item.x, dy + item.y, child_opacity)
            if hit is not None:
                return hit
            continue
        if _covers(item, x, y, dx, dy, opacity):
            return item
    return None


def _covers(layer: Layer, x: int, y: int, dx: int, dy: int, opacity: int) -> bool:
    if _covers_at(layer, x, y, dx, dy, opacity):
        return True
    if layer.shadow is None:
        return False
    shift_x, shift_y = layer.shadow
    return _covers_at(layer, x - shift_x, y - shift_y, dx, dy, opacity)


def _covers_at(layer: Layer, x: int, y: int, dx: int, dy: int, opacity: int) -> bool:
    local_x = x - dx - layer.x
    local_y = y - dy - layer.y
    image = layer.image
    if not (0 <= local_x < image.width and 0 <= local_y < image.height):
        return False
    mask = 255 if layer.mask is None else layer.mask[local_y * image.width + local_x]
    alpha = image.pixels[(local_y * image.width + local_x) * 4 + 3]
    return _covered(alpha, mask, min(255, opacity * layer.opacity // 255)) > 0


def _opaque_bounds(image: Image) -> tuple[int, int, int, int] | None:
    left, top = image.width, image.height
    right = bottom = -1
    pixels = image.pixels
    width = image.width
    for y in range(image.height):
        row = y * width * 4
        for x in range(width):
            if pixels[row + x * 4 + 3] == 0:
                continue
            if x < left:
                left = x
            if y < top:
                top = y
            if x > right:
                right = x
            if y > bottom:
                bottom = y
    if right < 0:
        return None
    return left, top, right, bottom


def _uniform(
    handle: str,
    left: int,
    top: int,
    right: int,
    bottom: int,
    new_left: int,
    new_top: int,
    new_right: int,
    new_bottom: int,
) -> tuple[int, int, int, int]:
    old_w = right - left
    old_h = bottom - top
    if old_w < 1 or old_h < 1:
        return new_left, new_top, new_right, new_bottom
    new_w = new_right - new_left
    new_h = new_bottom - new_top
    if abs(new_w / old_w - 1) >= abs(new_h / old_h - 1):
        scale = new_w / old_w
    else:
        scale = new_h / old_h
    scaled_w = max(1, int(round(old_w * scale)))
    scaled_h = max(1, int(round(old_h * scale)))
    if "e" in handle:
        new_right = new_left + scaled_w
    else:
        new_left = new_right - scaled_w
    if "s" in handle:
        new_bottom = new_top + scaled_h
    else:
        new_top = new_bottom - scaled_h
    return new_left, new_top, new_right, new_bottom


def ppm_bytes(image: Image) -> bytes:
    """An uncompressed RGB picture. Empty pixels show white. Tk reads this faster than color names."""
    width = image.width
    height = image.height
    source = image.pixels
    count = width * height
    header = b"P6\n%d %d\n255\n" % (width, height)
    if source[3::4] == b"\xff" * count:
        rgb = bytearray(count * 3)
        rgb[0::3] = source[0::4]
        rgb[1::3] = source[1::4]
        rgb[2::3] = source[2::4]
        return header + rgb
    rgb = bytearray(b"\xff" * (count * 3))
    clear = b"\x00" * width
    solid = b"\xff" * width
    for y in range(height):
        base = y * width * 4
        alphas = source[base + 3 : base + width * 4 : 4]
        if alphas == clear:
            continue
        row = y * width * 3
        if alphas == solid:
            span = source[base : base + width * 4]
            rgb[row : row + width * 3 : 3] = span[0::4]
            rgb[row + 1 : row + width * 3 : 3] = span[1::4]
            rgb[row + 2 : row + width * 3 : 3] = span[2::4]
            continue
        pixel = row
        for index in range(base, base + width * 4, 4):
            alpha = source[index + 3]
            if alpha == 255:
                rgb[pixel] = source[index]
                rgb[pixel + 1] = source[index + 1]
                rgb[pixel + 2] = source[index + 2]
            elif alpha:
                keep = 255 - alpha
                rgb[pixel] = (source[index] * alpha + 255 * keep + 127) // 255
                rgb[pixel + 1] = (source[index + 1] * alpha + 255 * keep + 127) // 255
                rgb[pixel + 2] = (source[index + 2] * alpha + 255 * keep + 127) // 255
            pixel += 3
    return header + rgb


def scaled_rgb(image: Image, scale: int) -> list[str]:
    """Nearest-neighbor rows of #rrggbb pixels, one string per screen row."""
    if scale < 1:
        raise ValueError("scale must be at least 1")
    rows: list[str] = []
    width = image.width
    pixels = image.pixels
    for y in range(image.height):
        colors = []
        start = y * width * 4
        for x in range(width):
            i = start + x * 4
            color = f"#{pixels[i]:02x}{pixels[i + 1]:02x}{pixels[i + 2]:02x}"
            colors.extend([color] * scale)
        row = " ".join(colors)
        rows.extend([row] * scale)
    return rows
