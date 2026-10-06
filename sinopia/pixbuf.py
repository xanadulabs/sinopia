"""Load pictures through GdkPixbuf, which is already on this desktop.

The folder of PNGs plus stack.txt stays the file you keep. This module only
reads a PNG or JPEG. Without GdkPixbuf, the Python PNG reader and djpeg still work.
"""

from pathlib import Path

from sinopia.image import Image


class PixbufMissing(Exception):
    """GdkPixbuf is not installed."""


def try_load(path: Path | str) -> Image | None:
    """The full picture, or None when GdkPixbuf is missing or refuses the file."""
    try:
        pixbuf = _open(path, None)
    except PixbufMissing:
        return None
    except ValueError:
        return None
    return _image(pixbuf)


def image_size(path: Path | str) -> tuple[int, int]:
    """Width and height from the file header."""
    Pixbuf, _error = _library()
    info = Pixbuf.Pixbuf.get_file_info(str(path))
    if info is None or info[0] is None or info[1] < 1 or info[2] < 1:
        raise ValueError("not a picture")
    return int(info[1]), int(info[2])


def preview_image(path: Path | str, max_edge: int) -> Image:
    """A copy that fits in a square of `max_edge` pixels."""
    if max_edge < 1:
        raise ValueError("preview edge must be at least 1")
    return _image(_open(path, max_edge))


def _open(path: Path | str, max_edge: int | None):
    Pixbuf, error = _library()
    try:
        if max_edge is None:
            return Pixbuf.Pixbuf.new_from_file(str(path))
        return Pixbuf.Pixbuf.new_from_file_at_scale(str(path), max_edge, max_edge, True)
    except error as failure:
        raise ValueError(str(failure)) from failure


def _library():
    try:
        import gi

        gi.require_version("GdkPixbuf", "2.0")
        from gi.repository import GdkPixbuf, GLib
    except (ImportError, ValueError) as failure:
        raise PixbufMissing(str(failure)) from failure
    return GdkPixbuf, GLib.Error


def _image(pixbuf) -> Image:
    width = pixbuf.get_width()
    height = pixbuf.get_height()
    channels = pixbuf.get_n_channels()
    stride = pixbuf.get_rowstride()
    raw = pixbuf.get_pixels()
    if channels not in (3, 4) or width < 1 or height < 1:
        raise ValueError("unsupported picture")
    count = width * height
    out = bytearray(count * 4)
    if channels == 4 and stride == width * 4:
        out[:] = raw[: count * 4]
    elif channels == 3 and stride == width * 3:
        out[0::4] = raw[0::3]
        out[1::4] = raw[1::3]
        out[2::4] = raw[2::3]
        out[3::4] = b"\xff" * count
    else:
        for y in range(height):
            row = raw[y * stride : y * stride + width * channels]
            dest = y * width * 4
            if channels == 4:
                out[dest : dest + width * 4] = row
                continue
            for x in range(width):
                start = x * 3
                at = dest + x * 4
                out[at : at + 3] = row[start : start + 3]
                out[at + 3] = 255
    return Image.from_pixels(width, height, out)
