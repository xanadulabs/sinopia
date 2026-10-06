"""The picture, and a tool column down the left side.

Tk draws the pixels. The folder on disk stays the document.
"""

import tkinter
from pathlib import Path

from sinopia.png import write_png
from sinopia.document import (
    Document,
    Group,
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
)
from sinopia.proof import proof_document
from sinopia.stage import Stage, ppm_bytes

FRAME = Path("/tmp/sinopia-frame.ppm")

SCALE = 8
RAIL = "#d6d6d6"
RAIL_PRESSED = "#a6a6a6"
TOOLS = (("move", "V"), ("brush", "B"), ("type", "T"))


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
        body = tkinter.Frame(self.root, bg=RAIL)
        body.pack()
        rail = tkinter.Frame(body, bg=RAIL, padx=4, pady=4)
        rail.pack(side="left", fill="y")
        self.buttons: dict[str, tkinter.Button] = {}
        for name, letter in TOOLS:
            button = tkinter.Button(
                rail,
                text=letter,
                width=2,
                font=("Sans", 12, "bold"),
                bg=RAIL,
                activebackground=RAIL,
                relief="raised",
                bd=2,
                command=lambda chosen=name: self.set_tool(chosen),
            )
            button.pack(pady=2)
            self.buttons[name] = button
        zoom = tkinter.Frame(rail, bg=RAIL)
        zoom.pack(pady=(12, 0))
        self.zoom_out = tkinter.Button(zoom, text="−", width=2, command=lambda: self.set_scale(self.scale // 2))
        self.zoom_in = tkinter.Button(zoom, text="+", width=2, command=lambda: self.set_scale(self.scale * 2))
        self.zoom_out.pack(side="left")
        self.zoom_in.pack(side="left", padx=(2, 0))
        self.zoom_label = tkinter.Label(rail, text="", bg=RAIL)
        self.zoom_label.pack()
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
        self.save_button = tkinter.Button(panel, text="Save", command=self._save)
        self.save_button.pack(fill="x", padx=4, pady=(0, 4))
        self._rows: list = []
        self.label.bind("<ButtonPress-1>", self._press)
        self.label.bind("<B1-Motion>", self._drag)
        self.label.bind("<ButtonRelease-1>", self._release)
        self.root.bind("<KeyPress>", self._key)
        self.root.bind("<Control-s>", self._save)
        self._mark_tools()
        self._show_zoom()
        self._title()
        self._refresh_layers()
        self._paint()

    def _refresh_layers(self) -> None:
        self.layer_list.delete(0, "end")
        self._rows = []
        for depth, item in layer_rows(self.stage.document):
            mark = "▸ " if isinstance(item, Group) else ""
            self.layer_list.insert("end", ("    " * depth) + mark + item.name)
            self._rows.append(item)
        if self.stage.target in self._rows:
            index = self._rows.index(self.stage.target)
            self.layer_list.selection_set(index)
            self.layer_list.activate(index)

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
        self._keep()

    def _group_layer(self) -> None:
        self.stage.select(group_item(self.stage.document, self.stage.target))
        self._refresh_layers()
        self._paint()
        self._keep()

    def _delete_layer(self) -> None:
        nxt = delete_item(self.stage.document, self.stage.target)
        if nxt is None:
            return
        self.stage.select(nxt)
        self._refresh_layers()
        self._paint()
        self._keep()

    def _keep(self) -> None:
        if self.on_release is not None:
            self.on_release()

    def _save(self, _event=None):
        self._keep()
        return "break"

    def set_scale(self, scale: int) -> None:
        scale = max(1, min(32, int(scale)))
        if scale == self.scale:
            return
        self.scale = scale
        picture = self.stage.picture
        self.photo = tkinter.PhotoImage(width=picture.width * scale, height=picture.height * scale)
        self.label.configure(image=self.photo)
        self._paint()
        self._show_zoom()

    def _show_zoom(self) -> None:
        self.zoom_label.configure(text=f"{self.scale}×")

    def set_tool(self, tool: str) -> None:
        if tool not in ("move", "brush", "type"):
            raise ValueError(f"unknown tool {tool}")
        self.tool = tool
        self._mark_tools()
        self._title()

    def _mark_tools(self) -> None:
        for name, button in self.buttons.items():
            if name == self.tool:
                button.configure(relief="sunken", bg=RAIL_PRESSED)
            else:
                button.configure(relief="raised", bg=RAIL)

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
        elif getattr(event, "keysym", "") in ("plus", "equal", "KP_Add"):
            self.set_scale(self.scale * 2)
        elif getattr(event, "keysym", "") in ("minus", "KP_Subtract"):
            self.set_scale(self.scale // 2)

    def _doc(self, event) -> tuple[int, int]:
        return event.x // self.scale, event.y // self.scale

    def _press(self, event) -> None:
        x, y = self._doc(event)
        self._pointer = (x, y)
        if self.tool == "brush":
            self.stage.brush_press(x, y)
            self._paint()
        elif self.tool == "type":
            if self.stage.lettering.active:
                self.stage.lettering.commit()
            self.stage.lettering.begin(x, y)
            self._title()
            self._paint()
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
        elif self.tool == "move":
            self.stage.release(x, y)
        self._paint()
        if self.on_release is not None:
            self.on_release()

    def _paint(self) -> None:
        FRAME.write_bytes(ppm_bytes(self.stage.picture))
        self._source.read(FRAME)
        self.photo.tk.call(self.photo, "copy", self._source, "-zoom", self.scale, self.scale)

    def mainloop(self) -> None:
        self.root.mainloop()


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
