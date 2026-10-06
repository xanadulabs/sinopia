"""Open dialog with a picture beside the file list.

The system file dialog names the files and does not show them. This one does.
"""

import tkinter
from pathlib import Path

from sinopia.exchange import read_picture
from sinopia.image import Image
from sinopia.pixbuf import PixbufMissing, image_size, preview_image

RAIL = "#d6d6d6"
PANE = "#b4b4b4"
PREVIEW = 280
KINDS = {".png", ".jpg", ".jpeg"}


def choose_picture(parent: tkinter.Misc, start: Path) -> Path | None:
    dialog = PictureDialog(parent, start)
    parent.wait_window(dialog.top)
    return dialog.chosen


def thumbnail(image: Image, max_edge: int = PREVIEW) -> Image:
    """A smaller copy that still shows the picture. Each sample is a block average."""
    if max_edge < 1:
        raise ValueError("preview edge must be at least 1")
    longest = max(image.width, image.height)
    factor = max(1, (longest + max_edge - 1) // max_edge)
    width = max(1, image.width // factor)
    height = max(1, image.height // factor)
    if factor == 1:
        return image
    out = bytearray(width * height * 4)
    source = image.pixels
    for y in range(height):
        for x in range(width):
            red = green = blue = alpha = 0
            count = 0
            y0 = y * factor
            x0 = x * factor
            y1 = min(y0 + factor, image.height)
            x1 = min(x0 + factor, image.width)
            for sy in range(y0, y1):
                row = sy * image.width
                for sx in range(x0, x1):
                    i = (row + sx) * 4
                    red += source[i]
                    green += source[i + 1]
                    blue += source[i + 2]
                    alpha += source[i + 3]
                    count += 1
            j = (y * width + x) * 4
            out[j] = red // count
            out[j + 1] = green // count
            out[j + 2] = blue // count
            out[j + 3] = alpha // count
    return Image.from_pixels(width, height, out)


class PictureDialog:
    def __init__(self, parent: tkinter.Misc, start: Path):
        self.chosen: Path | None = None
        self._shown: Path | None = None
        self._photo: tkinter.PhotoImage | None = None
        self._token = 0
        self._after: str | None = None
        self._rows: list[tuple[str, Path]] = []
        self.top = tkinter.Toplevel(parent)
        self.top.title("Open")
        self.top.configure(bg=RAIL)
        self.top.transient(parent)
        self.folder = start if start.is_dir() else start.parent
        bar = tkinter.Frame(self.top, bg=RAIL)
        bar.pack(fill="x", padx=8, pady=(8, 4))
        self.path_var = tkinter.StringVar(value=str(self.folder))
        entry = tkinter.Entry(bar, textvariable=self.path_var)
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", self._go)
        tkinter.Button(bar, text="Up", command=self._up).pack(side="left", padx=(6, 0))
        body = tkinter.Frame(self.top, bg=RAIL)
        body.pack(fill="both", expand=True, padx=8)
        self.list = tkinter.Listbox(
            body,
            width=36,
            height=16,
            exportselection=False,
            activestyle="none",
            bg="white",
            selectbackground="#3d6f99",
            selectforeground="white",
        )
        self.list.pack(side="left", fill="both", expand=True)
        self.list.bind("<<ListboxSelect>>", self._on_select)
        self.list.bind("<Double-Button-1>", self._activate)
        self.list.bind("<Return>", self._activate)
        side = tkinter.Frame(body, bg=RAIL)
        side.pack(side="left", fill="y", padx=(8, 0))
        pane = tkinter.Frame(side, width=PREVIEW, height=200, bg=PANE, relief="sunken", bd=2)
        pane.pack_propagate(False)
        pane.pack()
        self.preview = tkinter.Label(pane, bg=PANE, fg="#202020", text="Select a picture")
        self.preview.pack(expand=True)
        self.size_label = tkinter.Label(side, text="", bg=RAIL, anchor="w")
        self.size_label.pack(fill="x", pady=(6, 0))
        buttons = tkinter.Frame(self.top, bg=RAIL)
        buttons.pack(fill="x", padx=8, pady=8)
        tkinter.Button(buttons, text="Cancel", command=self._cancel).pack(side="right")
        tkinter.Button(buttons, text="Open", command=self._accept).pack(side="right", padx=(0, 6))
        self.top.bind("<Escape>", self._cancel)
        self.top.protocol("WM_DELETE_WINDOW", self._cancel)
        self._fill()
        self.list.focus_set()
        self.top.grab_set()

    def _fill(self) -> None:
        self.path_var.set(str(self.folder))
        self.list.delete(0, "end")
        self._rows = _entries(self.folder)
        first_file = None
        for index, (kind, path) in enumerate(self._rows):
            self.list.insert("end", path.name + ("/" if kind == "dir" else ""))
            if kind == "file" and first_file is None:
                first_file = index
        self._clear_preview()
        if first_file is not None:
            self.list.selection_set(first_file)
            self.list.activate(first_file)
            self.list.see(first_file)
            self._show(self._rows[first_file][1])

    def _selected(self) -> tuple[str, Path] | None:
        chosen = self.list.curselection()
        if not chosen:
            return None
        return self._rows[chosen[0]]

    def _on_select(self, _event=None) -> None:
        item = self._selected()
        if item is None or item[0] != "file":
            self._clear_preview()
            return
        self._show(item[1])

    def _show(self, path: Path) -> None:
        if path == self._shown and self._photo is not None:
            return
        self._shown = path
        self._token += 1
        token = self._token
        try:
            width, height = image_size(path)
        except PixbufMissing:
            width = height = 0
        except (OSError, ValueError, RuntimeError) as error:
            self._fail(str(error))
            return
        if width:
            self.size_label.configure(text=f"{width} × {height}")
        if self._after is not None:
            self.top.after_cancel(self._after)
        self._after = self.top.after_idle(lambda: self._load_preview(path, token))

    def _load_preview(self, path: Path, token: int) -> None:
        self._after = None
        if token != self._token:
            return
        try:
            image = preview_image(path, PREVIEW)
        except PixbufMissing:
            try:
                image = thumbnail(read_picture(path))
            except (OSError, ValueError, RuntimeError) as error:
                self._fail(str(error))
                return
        except (OSError, ValueError, RuntimeError) as error:
            self._fail(str(error))
            return
        if token != self._token:
            return
        self._photo = _photo(self.top, image)
        self.preview.configure(image=self._photo, text="")
        if not self.size_label.cget("text"):
            self.size_label.configure(text=f"{image.width} × {image.height}")

    def _fail(self, message: str) -> None:
        self._photo = None
        self.preview.configure(image="", text=message)
        self.size_label.configure(text="")

    def _clear_preview(self) -> None:
        self._token += 1
        if self._after is not None:
            self.top.after_cancel(self._after)
            self._after = None
        self._shown = None
        self._photo = None
        self.preview.configure(image="", text="Select a picture")
        self.size_label.configure(text="")

    def _activate(self, _event=None) -> str:
        item = self._selected()
        if item is None:
            return "break"
        kind, path = item
        if kind == "dir":
            self.folder = path
            self._fill()
        else:
            self._accept()
        return "break"

    def _go(self, _event=None) -> str:
        path = Path(self.path_var.get()).expanduser()
        if path.is_dir():
            self.folder = path
            self._fill()
        elif path.is_file() and path.suffix.lower() in KINDS:
            self.folder = path.parent
            self._fill()
            for index, (kind, candidate) in enumerate(self._rows):
                if kind == "file" and candidate == path:
                    self.list.selection_clear(0, "end")
                    self.list.selection_set(index)
                    self.list.activate(index)
                    self._show(path)
                    break
        return "break"

    def _up(self) -> None:
        parent = self.folder.parent
        if parent == self.folder:
            return
        self.folder = parent
        self._fill()

    def _accept(self) -> None:
        item = self._selected()
        if item is None or item[0] != "file":
            return
        self.chosen = item[1]
        self.top.destroy()

    def _cancel(self, _event=None) -> None:
        self.chosen = None
        self.top.destroy()


def _entries(folder: Path) -> list[tuple[str, Path]]:
    folders = []
    pictures = []
    try:
        children = list(folder.iterdir())
    except OSError:
        return []
    for child in children:
        if child.name.startswith("."):
            continue
        if child.is_dir():
            folders.append(child)
        elif child.is_file() and child.suffix.lower() in KINDS:
            pictures.append(child)
    folders.sort(key=lambda path: path.name.lower())
    pictures.sort(key=lambda path: path.name.lower())
    return [("dir", path) for path in folders] + [("file", path) for path in pictures]


def _photo(master: tkinter.Misc, image: Image) -> tkinter.PhotoImage:
    """PPM over the preview gray, so a transparent PNG is not a black rectangle."""
    count = len(image)
    rgb = bytearray(count * 3)
    source = image.pixels
    for index in range(count):
        i = index * 4
        alpha = source[i + 3]
        keep = 255 - alpha
        for channel in range(3):
            gray = 180
            rgb[index * 3 + channel] = (source[i + channel] * alpha + gray * keep + 127) // 255
    header = b"P6\n%d %d\n255\n" % (image.width, image.height)
    path = Path("/tmp/sinopia-preview.ppm")
    path.write_bytes(header + rgb)
    return tkinter.PhotoImage(master=master, file=str(path))


MAX_EDGE = 8192


def choose_size(
    parent: tkinter.Misc,
    current: tuple[int, int],
    clipboard: tuple[int, int] | None,
) -> tuple[int, int] | None:
    """Width and height for a new picture. A copied selection fills the fields."""
    dialog = SizeDialog(parent, current, clipboard)
    parent.wait_window(dialog.top)
    return dialog.chosen


class SizeDialog:
    def __init__(
        self,
        parent: tkinter.Misc,
        current: tuple[int, int],
        clipboard: tuple[int, int] | None,
    ):
        self.chosen: tuple[int, int] | None = None
        self._clipboard = clipboard
        self.top = tkinter.Toplevel(parent)
        self.top.title("New")
        self.top.configure(bg=RAIL)
        self.top.transient(parent)
        start = clipboard if clipboard is not None else current
        form = tkinter.Frame(self.top, bg=RAIL)
        form.pack(padx=12, pady=(12, 4))
        tkinter.Label(form, text="Width", bg=RAIL).grid(row=0, column=0, sticky="w")
        tkinter.Label(form, text="Height", bg=RAIL).grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.width_var = tkinter.StringVar(value=str(start[0]))
        self.height_var = tkinter.StringVar(value=str(start[1]))
        tkinter.Entry(form, textvariable=self.width_var, width=8).grid(row=0, column=1, padx=(8, 0))
        tkinter.Entry(form, textvariable=self.height_var, width=8).grid(row=1, column=1, padx=(8, 0), pady=(6, 0))
        note = "Type the width and height in pixels."
        if clipboard is not None:
            note = f"Clipboard is {clipboard[0]} × {clipboard[1]}."
            tkinter.Button(form, text="Clipboard", command=self._use_clipboard).grid(row=0, column=2, rowspan=2, padx=(8, 0))
        self.note = tkinter.Label(self.top, text=note, bg=RAIL, anchor="w")
        self.note.pack(fill="x", padx=12, pady=(4, 0))
        buttons = tkinter.Frame(self.top, bg=RAIL)
        buttons.pack(fill="x", padx=12, pady=12)
        tkinter.Button(buttons, text="Cancel", command=self._cancel).pack(side="right")
        tkinter.Button(buttons, text="OK", command=self._accept).pack(side="right", padx=(0, 6))
        self.top.bind("<Return>", self._accept)
        self.top.bind("<Escape>", self._cancel)
        self.top.protocol("WM_DELETE_WINDOW", self._cancel)
        self.top.grab_set()

    def _use_clipboard(self) -> None:
        if self._clipboard is None:
            return
        self.width_var.set(str(self._clipboard[0]))
        self.height_var.set(str(self._clipboard[1]))
        self.note.configure(text=f"Clipboard is {self._clipboard[0]} × {self._clipboard[1]}.")

    def _accept(self, _event=None) -> str:
        try:
            width = int(self.width_var.get())
            height = int(self.height_var.get())
        except ValueError:
            self.note.configure(text="Type the width and height in pixels.")
            return "break"
        if not (1 <= width <= MAX_EDGE and 1 <= height <= MAX_EDGE):
            self.note.configure(text=f"Use a size from 1 to {MAX_EDGE}.")
            return "break"
        self.chosen = (width, height)
        self.top.destroy()
        return "break"

    def _cancel(self, _event=None) -> None:
        self.chosen = None
        self.top.destroy()


def choose_canvas(parent: tkinter.Misc, width: int, height: int) -> tuple[int, int, str] | None:
    """How many pixels to add, and which square the picture stays on."""
    dialog = CanvasDialog(parent, width, height)
    parent.wait_window(dialog.top)
    return dialog.chosen


class CanvasDialog:
    def __init__(self, parent: tkinter.Misc, width: int, height: int):
        self.chosen: tuple[int, int, str] | None = None
        self._width = width
        self._height = height
        self.anchor = "c"
        self.top = tkinter.Toplevel(parent)
        self.top.title("Canvas Size")
        self.top.configure(bg=RAIL)
        self.top.transient(parent)
        form = tkinter.Frame(self.top, bg=RAIL)
        form.pack(padx=12, pady=(12, 4))
        tkinter.Label(form, text=f"Current {width} × {height}", bg=RAIL).grid(row=0, column=0, columnspan=3, sticky="w")
        tkinter.Label(form, text="Width", bg=RAIL).grid(row=1, column=0, sticky="w", pady=(8, 0))
        tkinter.Label(form, text="Height", bg=RAIL).grid(row=2, column=0, sticky="w", pady=(6, 0))
        self.width_var = tkinter.StringVar(value="0")
        self.height_var = tkinter.StringVar(value="0")
        width_entry = tkinter.Entry(form, textvariable=self.width_var, width=8)
        height_entry = tkinter.Entry(form, textvariable=self.height_var, width=8)
        width_entry.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=(8, 0))
        height_entry.grid(row=2, column=1, sticky="w", padx=(8, 0), pady=(6, 0))
        self.width_var.trace_add("write", lambda *_args: self._preview())
        self.height_var.trace_add("write", lambda *_args: self._preview())
        grid = tkinter.Frame(form, bg=RAIL)
        grid.grid(row=1, column=2, rowspan=2, padx=(16, 0), pady=(8, 0))
        self._anchor_buttons = {}
        for name, row, column in (
            ("nw", 0, 0),
            ("n", 0, 1),
            ("ne", 0, 2),
            ("w", 1, 0),
            ("c", 1, 1),
            ("e", 1, 2),
            ("sw", 2, 0),
            ("s", 2, 1),
            ("se", 2, 2),
        ):
            button = tkinter.Button(grid, text=" " if name != "c" else "●", width=2, command=lambda chosen=name: self._pick(chosen))
            button.grid(row=row, column=column, padx=1, pady=1)
            self._anchor_buttons[name] = button
        self.note = tkinter.Label(self.top, text=self._note(0, 0), bg=RAIL, anchor="w")
        self.note.pack(fill="x", padx=12, pady=(8, 0))
        tkinter.Label(self.top, text="The picture stays on the square you select.", bg=RAIL, anchor="w").pack(
            fill="x", padx=12
        )
        buttons = tkinter.Frame(self.top, bg=RAIL)
        buttons.pack(fill="x", padx=12, pady=12)
        tkinter.Button(buttons, text="Cancel", command=self._cancel).pack(side="right")
        tkinter.Button(buttons, text="OK", command=self._accept).pack(side="right", padx=(0, 6))
        self.top.bind("<Return>", self._accept)
        self.top.bind("<Escape>", self._cancel)
        self.top.protocol("WM_DELETE_WINDOW", self._cancel)
        self.top.grab_set()

    def _pick(self, anchor: str) -> None:
        self.anchor = anchor
        for name, button in self._anchor_buttons.items():
            button.configure(text="●" if name == anchor else " ", relief="sunken" if name == anchor else "raised")

    def _amounts(self) -> tuple[int, int] | None:
        try:
            width = int(self.width_var.get())
            height = int(self.height_var.get())
        except ValueError:
            return None
        if width < 0 or height < 0:
            return None
        return width, height

    def _note(self, extra_w: int, extra_h: int) -> str:
        return f"New size {self._width + extra_w} × {self._height + extra_h}"

    def _preview(self) -> None:
        amounts = self._amounts()
        if amounts is None:
            self.note.configure(text="Type how many pixels to add.")
            return
        self.note.configure(text=self._note(*amounts))

    def _accept(self, _event=None) -> str:
        amounts = self._amounts()
        if amounts is None:
            self.note.configure(text="Type how many pixels to add.")
            return "break"
        extra_w, extra_h = amounts
        if self._width + extra_w > MAX_EDGE or self._height + extra_h > MAX_EDGE:
            self.note.configure(text=f"Keep each side within {MAX_EDGE}.")
            return "break"
        self.chosen = (extra_w, extra_h, self.anchor)
        self.top.destroy()
        return "break"

    def _cancel(self, _event=None) -> None:
        self.chosen = None
        self.top.destroy()
