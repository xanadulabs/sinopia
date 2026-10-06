"""The picture, and a tool column down the left side.

Tk draws the pixels. The folder on disk stays the document.
"""

import tkinter
from pathlib import Path

from sinopia.document import Document, load, save
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
        self._source = tkinter.PhotoImage(width=picture.width, height=picture.height)
        self.photo = tkinter.PhotoImage(width=picture.width * SCALE, height=picture.height * SCALE)
        self.label = tkinter.Label(body, image=self.photo, borderwidth=0, bg=RAIL)
        self.label.pack(side="left")
        self.label.bind("<ButtonPress-1>", self._press)
        self.label.bind("<B1-Motion>", self._drag)
        self.label.bind("<ButtonRelease-1>", self._release)
        self.root.bind("<KeyPress>", self._key)
        self._mark_tools()
        self._title()
        self._paint()

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

    def _doc(self, event) -> tuple[int, int]:
        return event.x // SCALE, event.y // SCALE

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
        self.photo.tk.call(self.photo, "copy", self._source, "-zoom", SCALE, SCALE)

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

    def keep(document: Document = document, folder=folder) -> None:
        save(document, folder)

    Window(stage, on_release=keep).mainloop()


if __name__ == "__main__":
    main()
