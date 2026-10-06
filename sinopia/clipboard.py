"""The desktop clipboard, which is where Print Screen puts a picture.

The folder of PNGs plus stack.txt stays the file you keep. This only reads or
offers a picture on the clipboard. GTK is the same library the desktop uses.
If it cannot see a picture, New still uses a rectangle copied in Sinopia.
"""

from sinopia.image import Image
from sinopia.pixbuf import _image
from sinopia.select import copied_image

_kept = None


def clipboard_picture() -> Image | None:
    """The picture on the desktop clipboard, or one copied inside Sinopia."""
    found = system_image()
    if found is not None:
        return found
    return copied_image()


def system_image() -> Image | None:
    try:
        pixbuf = _gtk_clipboard().wait_for_image()
    except Exception:
        return None
    if pixbuf is None:
        return None
    try:
        return _image(pixbuf)
    except ValueError:
        return None


def clear_system() -> None:
    clipboard = _gtk_clipboard()
    clipboard.clear()
    clipboard.store()
    _flush()


def publish_image(image: Image) -> None:
    """Offer `image` on the desktop clipboard so other programs, and New, can see it."""
    global _kept
    pixbuf, data = _pixbuf(image)
    _kept = (pixbuf, data)
    clipboard = _gtk_clipboard()
    clipboard.set_image(pixbuf)
    clipboard.store()
    _flush()


def _gtk_clipboard():
    import gi

    gi.require_version("Gtk", "3.0")
    gi.require_version("Gdk", "3.0")
    from gi.repository import Gdk, Gtk

    if not getattr(_gtk_clipboard, "ready", False):
        Gtk.init_check([])
        _gtk_clipboard.ready = True
    return Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)


def _flush() -> None:
    from gi.repository import Gtk

    for _ in range(30):
        if not Gtk.events_pending():
            return
        Gtk.main_iteration_do(False)


def _pixbuf(image: Image):
    import gi

    gi.require_version("GdkPixbuf", "2.0")
    from gi.repository import GdkPixbuf, GLib

    raw = bytes(image.pixels)
    data = GLib.Bytes.new(raw)
    pixbuf = GdkPixbuf.Pixbuf.new_from_bytes(
        data,
        GdkPixbuf.Colorspace.RGB,
        True,
        8,
        image.width,
        image.height,
        image.width * 4,
    )
    return pixbuf, data
