"""The picture on screen. Dragging moves one layer; the brush paints that layer."""

import math

from sinopia.brush import BLACK, SPACING, dab, line, tip_offsets
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
        self.diameter = 5
        self.hardness = 100
        self.opacity = 100
        self.flow = 100
        self.erase = False
        self.clip: tuple[int, int, int, int] | None = None
        self.brush_mark: tuple[int, int] | None = None
        self.turn = 0.0
        self._pivot: tuple[float, float] | None = None
        self._pivot_custom = False
        self._session: dict | None = None
        self._press: tuple[int, int, int, int] | None = None
        self._stroke: tuple[int, int] | None = None
        self._walk: tuple[int, int] | None = None
        self._along = 0.0
        self._paint: tuple[bytes, bytearray] | None = None
        self._tip_key: tuple[int, int] | None = None
        self._tip_offsets: list[tuple[int, int, int]] = []
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
        self._walk = None
        self._paint = None
        self._pivot = None
        self._pivot_custom = False
        self.turn = 0.0
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

    @property
    def radius(self) -> int:
        """The old integer radius. Diameter 1 is radius 0, and it steps by two pixels."""
        return (self.diameter - 1) // 2

    @radius.setter
    def radius(self, value: int) -> None:
        self.diameter = max(0, int(value)) * 2 + 1

    def brush_press(self, x: int, y: int) -> None:
        if not isinstance(self.target, Layer):
            return
        self._stroke = None
        self._walk = None
        self._along = 0.0
        self._paint = None
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
        self._walk = None
        self._paint = None
        self.brush_mark = (x, y)

    def brush_line(self, start: tuple[int, int], end: tuple[int, int]) -> None:
        """One straight stroke from the last dab to this point. Shift-click does this."""
        self.brush_press(*start)
        if self._stroke is None:
            return
        self._brush_to(*end)

    def _brush_to(self, x: int, y: int, restack: bool = True) -> None:
        if self._stroke is None:
            points = [(x, y)]
        else:
            points = line(self._stroke, (x, y))[1:]
        if not isinstance(self.target, Layer):
            return
        image = self.target.image
        self._ensure_stroke(image)
        offsets = self._tip()
        step = max(1.0, self.diameter * SPACING / 100)
        for px, py in points:
            if self._walk is None:
                self._lay(image, px, py, offsets)
                self._walk = (px, py)
                self._along = 0.0
                continue
            self._along += math.hypot(px - self._walk[0], py - self._walk[1])
            self._walk = (px, py)
            while self._along >= step:
                self._along -= step
                self._lay(image, px, py, offsets)
        self._stroke = (x, y)
        if restack:
            self._restack()

    def _ensure_stroke(self, image: Image) -> None:
        if self._paint is None:
            self._paint = (bytes(image.pixels), bytearray(image.width * image.height))

    def _tip(self) -> list[tuple[int, int, int]]:
        key = (self.diameter, self.hardness)
        if self._tip_key != key:
            self._tip_key = key
            self._tip_offsets = tip_offsets(self.diameter, self.hardness)
        return self._tip_offsets

    def _lay(self, image: Image, x: int, y: int, offsets: list[tuple[int, int, int]]) -> None:
        if self._paint is None:
            return
        local_x, local_y = self.layer_point(x, y)
        origin, coverage = self._paint
        ink = (0, 0, 0, 0) if self.erase else self.color
        group_x, group_y = parent_offset(self.document, self.target)
        place = (self.target.x + group_x, self.target.y + group_y)
        dab(image, local_x, local_y, ink, offsets, self.flow, self.opacity, origin, coverage, self.clip, place)

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

    def pivot_point(self) -> tuple[float, float]:
        """Where a turn spins. The center of the box, unless that cross has been dragged."""
        if self._session is not None:
            return self._session["pivot"]
        if self._pivot_custom and self._pivot is not None:
            return self._pivot
        box = self.content_box()
        if box is None:
            return (0.0, 0.0)
        left, top, right, bottom = box
        return ((left + right) / 2, (top + bottom) / 2)

    def frame_corners(self) -> list[tuple[float, float]] | None:
        """The free-transform box. It stays tilted until Enter."""
        if self._session is None:
            box = self.content_box()
            if box is None:
                return None
            left, top, right, bottom = box
            return [(left, top), (right, top), (right, bottom), (left, bottom)]
        left, top, right, bottom = self._session["box"]
        pivot_x, pivot_y = self._session["pivot"]
        radians = math.radians(self._session["angle"])
        cos = math.cos(radians)
        sin = math.sin(radians)
        return [
            _spin(x, y, pivot_x, pivot_y, cos, sin)
            for x, y in ((left, top), (right, top), (right, bottom), (left, bottom))
        ]

    def _open_session(self) -> None:
        if self._session is not None or not isinstance(self.target, Layer):
            return
        box = self.content_box()
        if box is None:
            return
        image = self.target.image
        group_x, group_y = parent_offset(self.document, self.target)
        pivot = self._pivot if self._pivot_custom and self._pivot is not None else (
            (box[0] + box[2]) / 2,
            (box[1] + box[3]) / 2,
        )
        self._session = {
            "pixels": bytes(image.pixels),
            "mask": None if self.target.mask is None else bytes(self.target.mask),
            "origin": (self.target.x, self.target.y),
            "offset": (self.target.x + group_x, self.target.y + group_y),
            "src_box": box,
            "box": box,
            "angle": 0.0,
            "pivot": pivot,
            "pivot_was": self._pivot,
            "pivot_custom_was": self._pivot_custom,
        }

    def transform_press(self, handle: str, x: int, y: int) -> None:
        if not isinstance(self.target, Layer):
            self._transform = None
            return
        self._open_session()
        session = self._session
        if session is None:
            return
        self._transform = {
            "handle": handle,
            "press": (x, y),
            "box": session["box"],
            "src_box": session["src_box"],
            "src_at_press": session["src_box"],
            "pixels": session["pixels"],
            "mask": session["mask"],
            "origin": (self.target.x, self.target.y),
            "offset": session["offset"],
            "offset_at_press": session["offset"],
            "pivot": session["pivot"],
            "pivot_at_press": session["pivot"],
            "angle0": session["angle"],
        }

    def transform_drag(self, x: int, y: int, constrain: bool = False) -> None:
        """Scale from the opposite corner, move from inside, or turn around the cross."""
        if self._transform is None or self._session is None or not isinstance(self.target, Layer):
            return
        handle = self._transform["handle"]
        press_x, press_y = self._transform["press"]
        left, top, right, bottom = self._transform["box"]
        if handle == "pivot":
            base_x, base_y = self._transform["pivot_at_press"]
            self._pivot = (base_x + (x - press_x), base_y + (y - press_y))
            self._pivot_custom = True
            self._session["pivot"] = self._pivot
            self._transform["pivot"] = self._pivot
            if self._session["angle"]:
                self._resample_rotated(self._session["angle"])
            return
        if handle == "move":
            dx = x - press_x
            dy = y - press_y
            origin_x, origin_y = self._transform["origin"]
            self.target.x = origin_x + dx
            self.target.y = origin_y + dy
            self._session["box"] = (left + dx, top + dy, right + dx, bottom + dy)
            src_left, src_top, src_right, src_bottom = self._transform["src_at_press"]
            self._session["src_box"] = (src_left + dx, src_top + dy, src_right + dx, src_bottom + dy)
            pivot_x, pivot_y = self._transform["pivot_at_press"]
            self._session["pivot"] = (pivot_x + dx, pivot_y + dy)
            offset_x, offset_y = self._transform["offset_at_press"]
            self._session["offset"] = (offset_x + dx, offset_y + dy)
            self._box = self._session["box"]
            return
        if handle == "rotate":
            turn = self._transform["angle0"] + _turn_degrees(self._transform["pivot"], self._transform["press"], (x, y))
            if constrain:
                turn = round(turn / 15) * 15
            self._session["angle"] = turn
            self.turn = turn
            self._resample_rotated(turn)
            return
        dx = x - press_x
        dy = y - press_y
        if self._session["angle"]:
            dx, dy = _unspin_delta(dx, dy, self._session["angle"])
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
        self._session["box"] = (new_left, new_top, new_right, new_bottom)
        self._box = self._session["box"] if not self._session["angle"] else None
        if self._session["angle"]:
            self._resample_rotated(self._session["angle"])
        else:
            self._resample_box(new_left, new_top, new_right, new_bottom)

    def transform_release(self, x: int, y: int, constrain: bool = False) -> float | None:
        """End the drag. The free transform stays open, so the box can stay tilted."""
        if self._transform is None:
            return None
        self.transform_drag(x, y, constrain)
        self._transform = None
        self._box = None
        self._restack()
        return self.turn

    def transform_commit(self) -> None:
        """Enter. The pixels stay, and the box goes back to the upright bounds."""
        self._transform = None
        self._session = None
        self._box = None
        self.turn = 0.0
        self._restack()

    def transform_cancel(self) -> None:
        """Escape. Put the layer back to where the free transform started."""
        session = self._session
        self._transform = None
        self._session = None
        self._box = None
        self.turn = 0.0
        if session is None or not isinstance(self.target, Layer):
            return
        self.target.image.pixels[:] = session["pixels"]
        if session["mask"] is not None and self.target.mask is not None:
            self.target.mask[:] = session["mask"]
        self.target.x, self.target.y = session["origin"]
        self._pivot = session["pivot_was"]
        self._pivot_custom = session["pivot_custom_was"]
        self._restack()

    def rotate_by(self, degrees: float) -> None:
        """Turn the layer by `degrees` around the cross. Positive is clockwise."""
        if not isinstance(self.target, Layer) or abs(degrees) < 1e-6:
            return
        self._open_session()
        if self._session is None:
            return
        self.set_angle(self._session["angle"] + degrees)

    def set_angle(self, degrees: float) -> None:
        """The free-transform angle, measured from where this transform started."""
        self._open_session()
        if self._session is None:
            return
        self._session["angle"] = degrees
        self.turn = degrees
        self._box = None
        self._resample_rotated(degrees)
        self._restack()

    def _resample_box(self, left: int, top: int, right: int, bottom: int) -> None:
        gesture = self._transform
        if gesture is None or not isinstance(self.target, Layer):
            return
        src_left, src_top, src_right, src_bottom = gesture["src_box"]
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

    def _resample_rotated(self, degrees: float) -> None:
        """Rewrite the layer from the snapshot, turned clockwise around the cross."""
        session = self._session
        if session is None or not isinstance(self.target, Layer):
            return
        left, top, right, bottom = session["box"]
        src_left, src_top, src_right, src_bottom = session["src_box"]
        pivot_x, pivot_y = session["pivot"]
        offset_x, offset_y = session["offset"]
        src_pixels = session["pixels"]
        src_mask = session["mask"]
        image = self.target.image
        width, height = image.width, image.height
        radians = math.radians(degrees)
        cos = math.cos(radians)
        sin = math.sin(radians)
        corners = ((left, top), (right, top), (right, bottom), (left, bottom))
        src_w = src_right - src_left
        src_h = src_bottom - src_top
        dest_w = right - left
        dest_h = bottom - top
        turned = [_spin(x, y, pivot_x, pivot_y, cos, sin) for x, y in corners]
        min_x = max(offset_x, math.floor(min(point[0] for point in turned)))
        max_x = min(offset_x + width, math.ceil(max(point[0] for point in turned)))
        min_y = max(offset_y, math.floor(min(point[1] for point in turned)))
        max_y = min(offset_y + height, math.ceil(max(point[1] for point in turned)))
        out = bytearray(width * height * 4)
        mask_out = bytearray(width * height) if src_mask is not None else None
        for py in range(min_y, max_y):
            for px in range(min_x, max_x):
                dx = px + 0.5 - pivot_x
                dy = py + 0.5 - pivot_y
                sx = pivot_x + dx * cos + dy * sin
                sy = pivot_y - dx * sin + dy * cos
                if not (left <= sx < right and top <= sy < bottom) or dest_w < 1 or dest_h < 1:
                    continue
                sample_x = int(src_left + (sx - left) * src_w / dest_w) - offset_x
                sample_y = int(src_top + (sy - top) * src_h / dest_h) - offset_y
                local_x = px - offset_x
                local_y = py - offset_y
                if not (0 <= sample_x < width and 0 <= sample_y < height):
                    continue
                if not (0 <= local_x < width and 0 <= local_y < height):
                    continue
                si = (sample_y * width + sample_x) * 4
                if src_pixels[si + 3] == 0:
                    continue
                di = (local_y * width + local_x) * 4
                out[di : di + 4] = src_pixels[si : si + 4]
                if mask_out is not None and src_mask is not None:
                    mask_out[local_y * width + local_x] = src_mask[sample_y * width + sample_x]
        image.pixels[:] = out
        if mask_out is not None and self.target.mask is not None:
            self.target.mask[:] = mask_out
        self._box = None

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


def _turn_degrees(pivot: tuple[float, float], start: tuple[int, int], point: tuple[int, int]) -> float:
    """How far `point` has swung around `pivot` from `start`, in clockwise degrees."""
    px, py = pivot
    start_x, start_y = start
    point_x, point_y = point
    before = math.atan2(start_y - py, start_x - px)
    after = math.atan2(point_y - py, point_x - px)
    delta = math.degrees(after - before)
    while delta > 180:
        delta -= 360
    while delta < -180:
        delta += 360
    return delta


def _spin(x: float, y: float, pivot_x: float, pivot_y: float, cos: float, sin: float) -> tuple[float, float]:
    dx = x - pivot_x
    dy = y - pivot_y
    return (pivot_x + dx * cos - dy * sin, pivot_y + dx * sin + dy * cos)


def _unspin_delta(dx: float, dy: float, degrees: float) -> tuple[float, float]:
    """A pointer movement, taken back out of the layer's turn."""
    radians = math.radians(degrees)
    cos = math.cos(radians)
    sin = math.sin(radians)
    return (dx * cos + dy * sin, -dx * sin + dy * cos)


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
