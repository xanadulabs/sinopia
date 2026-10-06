"""The picture, and a tool column down the left side.

Tk draws the pixels. The folder on disk stays the document.
"""

import tkinter
from pathlib import Path
from tkinter import filedialog, messagebox

from sinopia.png import write_png
from sinopia.document import (
    Document,
    Group,
    Layer,
    add_layer,
    delete_item,
    group_item,
    layer_rows,
    load,
    place_above,
    place_below,
    place_into,
    rename_item,
    save,
    walk,
)
from sinopia.exchange import layer_name, read_picture, write_picture
from sinopia.history import History
from sinopia.icons import tool_cursor, tool_image
from sinopia.picker import choose_picture
from sinopia.proof import proof_document
from sinopia.stage import Stage, ppm_bytes
from sinopia.typeface import font_families

FRAME = Path("/tmp/sinopia-frame.ppm")

SCALE = 8
RAIL = "#d6d6d6"
RAIL_PRESSED = "#a6a6a6"
TOOLS = (("move", "V"), ("zoom", "Z"), ("brush", "B"), ("type", "T"), ("transform", "F"))


class Window:
    def __init__(self, stage: Stage, on_release=None):
        self.stage = stage
        self.on_release = on_release
        picture = stage.picture
        self.tool = "move"
        self.scale = SCALE
        self._pointer: tuple[int, int] | None = None
        self._paint_after: str | None = None
        self.root = tkinter.Tk()
        self.history = History(stage.document)
        self._history_lock = False
        pictures = Path.home() / "Pictures"
        self._open_dir = pictures if pictures.is_dir() else Path.home()
        self._build_menu()
        self.options = tkinter.Frame(self.root, bg=RAIL)
        self.options.pack(side="top", fill="x")
        body = tkinter.Frame(self.root, bg=RAIL)
        body.pack()
        rail = tkinter.Frame(body, bg=RAIL, padx=4, pady=4)
        rail.pack(side="left", fill="y")
        self.buttons: dict[str, tkinter.Button] = {}
        self._tool_images = {}
        for name, letter in TOOLS:
            self._tool_images[name] = tool_image(self.root, name, letter)
            button = tkinter.Button(
                rail,
                image=self._tool_images[name],
                bg=RAIL,
                activebackground=RAIL,
                relief="raised",
                bd=2,
                command=lambda chosen=name: self.set_tool(chosen),
            )
            button.pack(pady=2)
            self.buttons[name] = button
        self._source = tkinter.PhotoImage(width=picture.width, height=picture.height)
        self.photo = tkinter.PhotoImage(width=picture.width * SCALE, height=picture.height * SCALE)
        self.label = tkinter.Label(body, image=self.photo, borderwidth=0, bg=RAIL)
        self.label.pack(side="left")
        panel = tkinter.Frame(body, bg=RAIL)
        panel.pack(side="right", fill="y")
        self.layer_list = tkinter.Listbox(
            panel,
            width=18,
            height=16,
            exportselection=False,
            activestyle="none",
            bg="white",
            selectbackground="#3d6f99",
            selectforeground="white",
        )
        self.layer_list.pack(fill="both", expand=True, padx=4, pady=4)
        self.layer_list.bind("<<ListboxSelect>>", self._choose_layer)
        self.layer_list.bind("<ButtonPress-1>", self._layer_press)
        self.layer_list.bind("<B1-Motion>", self._layer_motion)
        self.layer_list.bind("<ButtonRelease-1>", self._layer_drop)
        self._layer_src: int | None = None
        self._layer_press_y: int | None = None
        self._layer_dragged = False
        self._rename_on_click = False
        self._rename_entry: tkinter.Entry | None = None
        self._rename_index: int | None = None
        commands = tkinter.Frame(panel, bg=RAIL)
        commands.pack(fill="x", padx=4, pady=(0, 4))
        self.add_button = tkinter.Button(commands, text="New", command=self._add_layer)
        self.group_button = tkinter.Button(commands, text="Group", command=self._group_layer)
        self.delete_button = tkinter.Button(commands, text="Delete", command=self._delete_layer)
        for button in (self.add_button, self.group_button, self.delete_button):
            button.pack(side="left", padx=1)
        tkinter.Label(panel, text="History", bg=RAIL, anchor="w").pack(fill="x", padx=6, pady=(8, 0))
        self.history_list = tkinter.Listbox(
            panel,
            height=6,
            exportselection=False,
            activestyle="none",
            bg="white",
            selectbackground="#3d6f99",
            selectforeground="white",
        )
        self.history_list.pack(fill="x", padx=4, pady=(2, 6))
        self.history_list.bind("<<ListboxSelect>>", self._jump_history)
        self._rows: list = []
        self.label.bind("<ButtonPress-1>", self._press)
        self.label.bind("<B1-Motion>", self._drag)
        self.label.bind("<ButtonRelease-1>", self._release)
        self.label.bind("<Motion>", self._hover)
        self.root.bind("<KeyPress>", self._key)
        self.root.bind("<Control-s>", self._save)
        self.root.bind("<Control-o>", self._open_file)
        self.root.bind("<Control-Shift-S>", self._save_as)
        self.root.bind("<Control-z>", self._undo)
        self.root.bind("<Control-Z>", self._undo)
        self.root.bind("<Control-y>", self._redo)
        self.root.bind("<Control-Shift-Z>", self._redo)
        self._mark_tools()
        self._show_options()
        self._title()
        self._refresh_layers()
        self._refresh_history()
        self._paint()

    def _refresh_layers(self) -> None:
        self.layer_list.delete(0, "end")
        self._rows = []
        for depth, item in layer_rows(self.stage.document):
            mark = "▸ " if isinstance(item, Group) else ""
            self.layer_list.insert("end", ("    " * depth) + mark + item.name)
            self._rows.append(item)
        self._highlight_selection()

    def _highlight_selection(self) -> None:
        if self.stage.target not in self._rows:
            return
        index = self._rows.index(self.stage.target)
        self.layer_list.selection_clear(0, "end")
        self.layer_list.selection_set(index)
        self.layer_list.activate(index)
        self.layer_list.see(index)

    def _layer_press(self, event) -> None:
        self._layer_src = self.layer_list.nearest(event.y)
        self._layer_press_y = event.y
        self._layer_dragged = False
        chosen = self.layer_list.curselection()
        self._rename_on_click = bool(chosen) and chosen[0] == self._layer_src

    def _layer_motion(self, event) -> None:
        if self._layer_press_y is None or abs(event.y - self._layer_press_y) < 4:
            return
        self._layer_dragged = True
        row = self.layer_list.nearest(event.y)
        self.layer_list.selection_clear(0, "end")
        self.layer_list.selection_set(row)

    def _layer_drop(self, event) -> None:
        src = self._layer_src
        self._layer_src = None
        self._layer_press_y = None
        if not self._layer_dragged:
            if self._rename_on_click and src is not None and self._rename_entry is None:
                self._begin_rename(src)
            return
        self._layer_dragged = False
        dst = self.layer_list.nearest(event.y)
        if src is None or src == dst or not (0 <= src < len(self._rows) and 0 <= dst < len(self._rows)):
            self._refresh_layers()
            return
        node = self._rows[src]
        target = self._rows[dst]
        box = self.layer_list.bbox(dst)
        fraction = 0.5
        on_name = False
        if box and box[3]:
            fraction = (event.y - box[1]) / box[3]
            if isinstance(target, Group):
                edge = 4 if box[3] > 12 else 0
                offset = event.y - box[1]
                on_name = edge <= offset < box[3] - edge
        if on_name:
            moved = place_into(self.stage.document, node, target)
        elif fraction < 0.5:
            moved = place_above(self.stage.document, node, target)
        else:
            moved = place_below(self.stage.document, node, target)
        if not moved:
            self._refresh_layers()
            return
        self.stage.retarget(node)
        self._refresh_layers()
        self._paint()
        self._commit("Restack")
        self._keep()

    def _begin_rename(self, index: int) -> None:
        box = self.layer_list.bbox(index)
        if not box:
            return
        entry = tkinter.Entry(self.layer_list)
        entry.insert(0, self._rows[index].name)
        entry.selection_range(0, "end")
        entry.place(x=0, y=box[1], width=box[2], height=box[3])
        entry.focus_set()
        entry.bind("<Return>", self._commit_rename)
        entry.bind("<Escape>", self._cancel_rename)
        entry.bind("<FocusOut>", self._commit_rename)
        self._rename_entry = entry
        self._rename_index = index

    def _commit_rename(self, event=None) -> str:
        entry = self._rename_entry
        index = self._rename_index
        if entry is None or index is None:
            return "break"
        item = self._rows[index]
        before = item.name
        if not rename_item(self.stage.document, item, entry.get()):
            if getattr(event, "keysym", "") == "Return":
                return "break"
            self._cancel_rename()
            return "break"
        self._rename_entry = None
        self._rename_index = None
        entry.destroy()
        if item.name != before:
            self._refresh_layers()
            self._commit("Rename")
            self._keep()
        return "break"

    def _cancel_rename(self, _event=None) -> str:
        entry = self._rename_entry
        self._rename_entry = None
        self._rename_index = None
        if entry is not None:
            entry.destroy()
        return "break"

    def _choose_layer(self, _event=None) -> None:
        chosen = self.layer_list.curselection()
        if not chosen:
            return
        self.stage.select(self._rows[chosen[0]])
        self._paint()

    def _add_layer(self) -> None:
        self.stage.select(add_layer(self.stage.document, self.stage.target))
        self._refresh_layers()
        self._paint()
        self._commit("Layer")
        self._keep()

    def _group_layer(self) -> None:
        self.stage.select(group_item(self.stage.document, self.stage.target))
        self._refresh_layers()
        self._paint()
        self._commit("Group")
        self._keep()

    def _delete_layer(self) -> None:
        kind = "Group" if isinstance(self.stage.target, Group) else "Layer"
        nxt = delete_item(self.stage.document, self.stage.target)
        if nxt is None:
            return
        self.stage.select(nxt)
        self._refresh_layers()
        self._paint()
        self._commit(f"Delete {kind}")
        self._keep()

    def _build_menu(self) -> None:
        bar = tkinter.Menu(self.root, tearoff=0)
        self.file_menu = tkinter.Menu(bar, tearoff=0)
        self.file_menu.add_command(label="Open...", command=self._open_file, accelerator="Ctrl+O")
        self.file_menu.add_command(label="Save", command=self._save, accelerator="Ctrl+S")
        self.file_menu.add_command(label="Save As...", command=self._save_as, accelerator="Ctrl+Shift+S")
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Exit", command=self.root.destroy)
        bar.add_cascade(label="File", menu=self.file_menu)
        self.edit_menu = tkinter.Menu(bar, tearoff=0)
        self.edit_menu.add_command(label="Undo", command=self._undo, accelerator="Ctrl+Z")
        self.edit_menu.add_command(label="Redo", command=self._redo, accelerator="Ctrl+Shift+Z")
        bar.add_cascade(label="Edit", menu=self.edit_menu)
        view = tkinter.Menu(bar, tearoff=0)
        view.add_command(label="Zoom In", command=lambda: self.set_scale(self.scale * 2), accelerator="+")
        view.add_command(label="Zoom Out", command=lambda: self.set_scale(self.scale // 2), accelerator="−")
        view.add_command(label="Actual Pixels", command=lambda: self.set_scale(1))
        bar.add_cascade(label="View", menu=view)
        about = tkinter.Menu(bar, tearoff=0)
        about.add_command(label="About Sinopia...", command=self._about)
        bar.add_cascade(label="About", menu=about)
        self.root.configure(menu=bar)

    def _about(self) -> None:
        messagebox.showinfo(
            "About Sinopia",
            "Sinopia\n\nA lightweight, minimalist compositor. An early Photoshop, "
            "without the modern bells and whistles.\n\n"
            "The picture you keep is a folder of PNGs plus stack.txt. "
            "PNG and JPEG are copies.",
            parent=self.root,
        )

    def _open_file(self, _event=None):
        path = choose_picture(self.root, self._open_dir)
        if path is None:
            return "break"
        self._open_dir = path.parent
        try:
            image = read_picture(path)
        except (OSError, ValueError, RuntimeError) as error:
            messagebox.showerror("Open", str(error), parent=self.root)
            return "break"
        document = self.stage.document
        document.width = image.width
        document.height = image.height
        document.layers = [Layer(layer_name(path), image)]
        self.history.commit("Open")
        self._restore_view(fit=True)
        return "break"

    def _save_as(self, _event=None):
        path = filedialog.asksaveasfilename(
            parent=self.root,
            title="Save As",
            defaultextension=".png",
            filetypes=[("PNG", "*.png"), ("JPEG", "*.jpg *.jpeg")],
        )
        if not path:
            return "break"
        if Path(path).suffix.lower() not in (".png", ".jpg", ".jpeg"):
            path += ".png"
        try:
            write_picture(path, self.stage.picture)
        except (OSError, ValueError, RuntimeError) as error:
            messagebox.showerror("Save As", str(error), parent=self.root)
        return "break"

    def _undo(self, _event=None):
        if self.stage.lettering.active:
            self.stage.lettering.cancel()
            self._title()
            self._paint()
            return "break"
        if not self.history.undo():
            return "break"
        self._restore_view()
        self._keep()
        return "break"

    def _redo(self, _event=None):
        if not self.history.redo():
            return "break"
        self._restore_view()
        self._keep()
        return "break"

    def _commit(self, label: str) -> None:
        if self.history.commit(label):
            self._refresh_history()

    def _jump_history(self, _event=None) -> None:
        if self._history_lock:
            return
        chosen = self.history_list.curselection()
        if not chosen or chosen[0] == self.history.index:
            return
        self.history.jump(chosen[0])
        self._restore_view()
        self._keep()

    def _restore_view(self, fit: bool = False) -> None:
        name = self.stage.target.name
        node = _named(self.stage.document, name)
        self.stage.retarget(node)
        if fit:
            while self.scale > 1 and self.stage.picture.width * self.scale > 960:
                self.scale //= 2
        self._install_picture()
        self._show_zoom()
        self._refresh_layers()
        self._refresh_history()
        self._title()
        self._paint()

    def _refresh_history(self) -> None:
        self._history_lock = True
        self.history_list.delete(0, "end")
        for label, _snap in self.history.steps:
            self.history_list.insert("end", label)
        self.history_list.selection_set(self.history.index)
        self.history_list.activate(self.history.index)
        self.history_list.see(self.history.index)
        self.edit_menu.entryconfig(0, state="normal" if self.history.can_undo() else "disabled")
        self.edit_menu.entryconfig(1, state="normal" if self.history.can_redo() else "disabled")
        self._history_lock = False

    def _keep(self) -> None:
        if self.on_release is not None:
            self.on_release()

    def _save(self, _event=None):
        self._keep()
        return "break"

    def set_scale(self, scale: int) -> None:
        scale = max(1, min(32, int(scale)))
        if scale == self.scale and self.photo.width() == self.stage.picture.width * scale:
            self._show_zoom()
            return
        self.scale = scale
        self._install_picture()
        self._show_zoom()
        self._paint()

    def _install_picture(self) -> None:
        picture = self.stage.picture
        self._source = tkinter.PhotoImage(width=picture.width, height=picture.height)
        self.photo = tkinter.PhotoImage(width=picture.width * self.scale, height=picture.height * self.scale)
        if getattr(self, "label", None) is not None:
            self.label.configure(image=self.photo)

    def _show_zoom(self) -> None:
        if getattr(self, "_zoom_readout", None) is not None:
            self._zoom_readout.configure(text=f"{self.scale}×")

    def set_tool(self, tool: str) -> None:
        if tool not in ("move", "brush", "type", "transform", "zoom"):
            raise ValueError(f"unknown tool {tool}")
        self.tool = tool
        self._mark_tools()
        self._show_options()
        self._title()
        self._paint()

    def _show_options(self) -> None:
        for child in self.options.winfo_children():
            child.destroy()
        if self.tool == "type":
            self._type_options()
        elif self.tool == "brush":
            self._brush_options()
        elif self.tool == "transform":
            tkinter.Label(self.options, text="Drag a corner to scale. Drag inside the box to move.", bg=RAIL).pack(
                side="left", padx=6, pady=4
            )
        elif self.tool == "zoom":
            tkinter.Label(self.options, text="Click to zoom in. Alt-click to zoom out.", bg=RAIL).pack(
                side="left", padx=6, pady=4
            )
        else:
            tkinter.Label(self.options, text="Move", bg=RAIL).pack(side="left", padx=6, pady=4)
        self._zoom_readout = tkinter.Label(self.options, text=f"{self.scale}×", bg=RAIL)
        self._zoom_readout.pack(side="right", padx=8)

    def _brush_options(self) -> None:
        tkinter.Label(self.options, text="Size", bg=RAIL).pack(side="left", padx=(6, 2), pady=4)
        self._radius_var = tkinter.IntVar(value=self.stage.radius)
        spin = tkinter.Spinbox(
            self.options,
            from_=0,
            to=64,
            width=4,
            textvariable=self._radius_var,
            command=self._apply_brush,
        )
        spin.pack(side="left", pady=4)
        spin.bind("<Return>", self._apply_brush)
        spin.bind("<FocusOut>", self._apply_brush)

    def _apply_brush(self, _event=None) -> None:
        try:
            self.stage.radius = max(0, int(self._radius_var.get()))
        except (tkinter.TclError, ValueError):
            return

    def _type_options(self) -> None:
        style = self.stage.lettering.style
        families = font_families()
        if style.family not in families:
            families.append(style.family)
        tkinter.Label(self.options, text="Font", bg=RAIL).pack(side="left", padx=(6, 2))
        self._font_var = tkinter.StringVar(value=style.family)
        tkinter.OptionMenu(self.options, self._font_var, *families, command=self._apply_type).pack(side="left")
        self._size_var = tkinter.IntVar(value=style.size)
        size = tkinter.Spinbox(
            self.options, from_=1, to=256, width=4, textvariable=self._size_var, command=self._apply_type
        )
        size.pack(side="left", padx=(6, 0))
        size.bind("<Return>", self._apply_type)
        size.bind("<FocusOut>", self._apply_type)
        self._unit_var = tkinter.StringVar(value=style.unit)
        tkinter.OptionMenu(self.options, self._unit_var, "px", "pt", command=self._apply_type).pack(side="left")
        self._bold_var = tkinter.IntVar(value=int(style.bold))
        self._italic_var = tkinter.IntVar(value=int(style.italic))
        self._strike_var = tkinter.IntVar(value=int(style.strikethrough))
        self._underline_var = tkinter.IntVar(value=int(style.underline))
        for text, var in (
            ("Bold", self._bold_var),
            ("Italic", self._italic_var),
            ("Strike", self._strike_var),
            ("Underline", self._underline_var),
        ):
            tkinter.Checkbutton(self.options, text=text, variable=var, bg=RAIL, command=self._apply_type).pack(
                side="left"
            )
        tkinter.Label(self.options, text="Kerning", bg=RAIL).pack(side="left", padx=(6, 2))
        self._kerning_var = tkinter.IntVar(value=style.kerning)
        kerning = tkinter.Spinbox(
            self.options, from_=-32, to=64, width=4, textvariable=self._kerning_var, command=self._apply_type
        )
        kerning.pack(side="left")
        kerning.bind("<Return>", self._apply_type)
        kerning.bind("<FocusOut>", self._apply_type)
        tkinter.Label(self.options, text="Stroke", bg=RAIL).pack(side="left", padx=(6, 2))
        self._stroke_var = tkinter.IntVar(value=style.stroke)
        stroke = tkinter.Spinbox(
            self.options, from_=0, to=16, width=3, textvariable=self._stroke_var, command=self._apply_type
        )
        stroke.pack(side="left", padx=(0, 6))
        stroke.bind("<Return>", self._apply_type)
        stroke.bind("<FocusOut>", self._apply_type)

    def _apply_type(self, _event=None) -> None:
        style = self.stage.lettering.style
        try:
            style.family = self._font_var.get()
            style.size = max(1, int(self._size_var.get()))
            style.unit = self._unit_var.get()
            style.bold = bool(self._bold_var.get())
            style.italic = bool(self._italic_var.get())
            style.strikethrough = bool(self._strike_var.get())
            style.underline = bool(self._underline_var.get())
            style.kerning = int(self._kerning_var.get())
            style.stroke = max(0, int(self._stroke_var.get()))
        except (tkinter.TclError, ValueError, AttributeError):
            return
        if self.stage.lettering.active:
            self.stage.lettering.refresh()
            self._paint()

    def _mark_tools(self) -> None:
        for name, button in self.buttons.items():
            if name == self.tool:
                button.configure(relief="sunken", bg=RAIL_PRESSED)
            else:
                button.configure(relief="raised", bg=RAIL)
        self.label.configure(cursor=tool_cursor(self.tool))

    def _title(self) -> None:
        if self.stage.lettering.active:
            self.root.title(f"Sinopia — type: {self.stage.lettering.text}")
        else:
            self.root.title(f"Sinopia — {self.tool}")

    def _key(self, event) -> None:
        if self._rename_entry is not None:
            return
        if self.stage.lettering.active:
            key = getattr(event, "keysym", "")
            if key == "Return":
                self.stage.lettering.commit()
                self._commit("Type")
            elif key == "Escape":
                self.stage.lettering.cancel()
            elif key == "BackSpace":
                self.stage.lettering.backspace()
            elif event.char:
                self.stage.lettering.insert(event.char)
            self._title()
            self._paint()
            return
        if event.char in ("b", "B"):
            self.set_tool("brush")
        elif event.char in ("v", "V"):
            self.set_tool("move")
        elif event.char in ("t", "T"):
            self.set_tool("type")
        elif event.char in ("f", "F"):
            self.set_tool("transform")
        elif event.char in ("z", "Z"):
            self.set_tool("zoom")
        elif getattr(event, "keysym", "") in ("plus", "equal", "KP_Add"):
            self.set_scale(self.scale * 2)
        elif getattr(event, "keysym", "") in ("minus", "KP_Subtract"):
            self.set_scale(self.scale // 2)

    def _doc(self, event) -> tuple[int, int]:
        return event.x // self.scale, event.y // self.scale

    def _press(self, event) -> None:
        self.root.focus_set()
        x, y = self._doc(event)
        self._pointer = (x, y)
        self._select_clicked(x, y)
        if self.tool == "brush":
            self.stage.brush_press(x, y)
            self._paint()
        elif self.tool == "type":
            if self.stage.lettering.active:
                self.stage.lettering.commit()
                self._commit("Type")
            self.stage.lettering.begin(x, y)
            self._title()
            self._paint()
        elif self.tool == "transform":
            handle = self._hit_handle(event.x, event.y)
            if handle is None and self._inside_box(event.x, event.y):
                handle = "move"
            if handle is not None:
                self.stage.transform_press(handle, x, y)
        else:
            self.stage.press(x, y)

    def _drag(self, event) -> None:
        x, y = self._doc(event)
        if (x, y) == self._pointer:
            return
        self._pointer = (x, y)
        if self.tool == "brush":
            self.stage.brush_drag(x, y)
        elif self.tool == "move":
            self.stage.shift(x, y)
        elif self.tool == "transform":
            self.stage.transform_drag(x, y, _shifted(event))
        else:
            return
        self._schedule()

    def _schedule(self) -> None:
        if self._paint_after is None:
            self._paint_after = self.root.after_idle(self._flush)

    def _flush(self) -> None:
        self._paint_after = None
        self.stage.reveal()
        self._paint()

    def _release(self, event) -> None:
        if self._paint_after is not None:
            self.root.after_cancel(self._paint_after)
            self._paint_after = None
        x, y = self._doc(event)
        if self.tool == "brush":
            self.stage.brush_release(x, y)
            self._commit("Brush")
        elif self.tool == "move":
            self.stage.release(x, y)
            self._commit("Move")
        elif self.tool == "transform":
            self.stage.transform_release(x, y, _shifted(event))
            self._commit("Transform")
        elif self.tool == "zoom":
            alt = bool(getattr(event, "state", 0) & 0x8)
            self.set_scale(self.scale // 2 if alt else self.scale * 2)
            return
        self._paint()
        if self.on_release is not None:
            self.on_release()

    def _select_clicked(self, x: int, y: int) -> None:
        hit = self.stage.pick(x, y)
        if hit is not None:
            self.stage.select(hit)
        self._highlight_selection()

    def _box_screen(self) -> tuple[int, int, int, int] | None:
        box = self.stage.content_box()
        if box is None:
            return None
        left, top, right, bottom = box
        return left * self.scale, top * self.scale, right * self.scale, bottom * self.scale

    def _handle_points(self) -> dict[str, tuple[int, int]]:
        box = self._box_screen()
        if box is None:
            return {}
        left, top, right, bottom = box
        mid_x = (left + right) // 2
        mid_y = (top + bottom) // 2
        return {
            "nw": (left, top),
            "n": (mid_x, top),
            "ne": (right, top),
            "e": (right, mid_y),
            "se": (right, bottom),
            "s": (mid_x, bottom),
            "sw": (left, bottom),
            "w": (left, mid_y),
        }

    def _hit_handle(self, x: int, y: int) -> str | None:
        points = self._handle_points()
        for name in ("nw", "ne", "se", "sw", "n", "e", "s", "w"):
            if name not in points:
                return None
            hx, hy = points[name]
            reach = 16 if len(name) == 2 else 10
            if abs(x - hx) <= reach and abs(y - hy) <= reach:
                return name
        return None

    def _inside_box(self, x: int, y: int) -> bool:
        box = self._box_screen()
        if box is None:
            return False
        left, top, right, bottom = box
        return left < x < right and top < y < bottom

    def _hover(self, event) -> None:
        if self.tool != "transform" or self.stage._transform is not None:
            return
        handle = self._hit_handle(event.x, event.y)
        if handle is None and self._inside_box(event.x, event.y):
            handle = "move"
        cursors = {
            "nw": "top_left_corner",
            "se": "bottom_right_corner",
            "ne": "top_right_corner",
            "sw": "bottom_left_corner",
            "n": "top_side",
            "s": "bottom_side",
            "e": "right_side",
            "w": "left_side",
            "move": "fleur",
        }
        self.label.configure(cursor=cursors.get(handle) or tool_cursor("transform"))

    def _draw_handles(self) -> None:
        box = self._box_screen()
        if box is None:
            return
        left, top, right, bottom = box
        self._frame(left, top, right, bottom)
        for name, (x, y) in self._handle_points().items():
            self._knob(x, y, 15 if len(name) == 2 else 9)

    def _frame(self, left: int, top: int, right: int, bottom: int) -> None:
        for x in range(left, right):
            self._mark(x, top)
            self._mark(x, bottom - 1)
        for y in range(top, bottom):
            self._mark(left, y)
            self._mark(right - 1, y)

    def _knob(self, cx: int, cy: int, size: int) -> None:
        half = size // 2
        width = self.photo.width()
        height = self.photo.height()
        x0 = min(max(0, cx - half), max(0, width - size))
        y0 = min(max(0, cy - half), max(0, height - size))
        for y in range(y0, y0 + size):
            for x in range(x0, x0 + size):
                edge = x in (x0, x0 + size - 1) or y in (y0, y0 + size - 1)
                self._mark(x, y, "#000000" if edge else "#ffffff")

    def _mark(self, x: int, y: int, color: str = "#ffffff") -> None:
        if 0 <= x < self.photo.width() and 0 <= y < self.photo.height():
            self.photo.put(color, (x, y))

    def _paint(self) -> None:
        FRAME.write_bytes(ppm_bytes(self.stage.picture))
        self._source.read(FRAME)
        self.photo.tk.call(self.photo, "copy", self._source, "-zoom", self.scale, self.scale)
        if self.tool == "transform":
            self._draw_handles()

    def mainloop(self) -> None:
        self.root.mainloop()


def _named(document: Document, name: str) -> Layer | Group:
    for item in walk(document.layers):
        if item.name == name:
            return item
    return document.layers[-1]


def _shifted(event) -> bool:
    return bool(getattr(event, "state", 0) & 0x1)


def main() -> None:
    from pathlib import Path

    folder = Path("out/document")
    if (folder / "stack.txt").is_file():
        document = load(folder)
    else:
        document = proof_document()
        folder.parent.mkdir(exist_ok=True)
        save(document, folder)
    stage = Stage(document)

    def keep(document: Document = document, folder=folder, stage: Stage = stage) -> None:
        save(document, folder)
        write_png(folder.parent / "proof.png", stage.picture)

    Window(stage, on_release=keep).mainloop()


if __name__ == "__main__":
    main()
