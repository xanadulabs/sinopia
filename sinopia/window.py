"""A bare window: the composite, and a drag that moves the top layer.

Tk draws the pixels. The folder on disk stays the document.
"""

import tkinter

from sinopia.document import Document, load, save
from sinopia.proof import proof_document
from sinopia.stage import Stage, scaled_rgb

SCALE = 8


class Window:
    def __init__(self, stage: Stage, on_release=None):
        self.stage = stage
        self.on_release = on_release
        picture = stage.picture
        self.tool = "move"
        self.root = tkinter.Tk()
        self.photo = tkinter.PhotoImage(width=picture.width * SCALE, height=picture.height * SCALE)
        label = tkinter.Label(self.root, image=self.photo, borderwidth=0)
        label.pack()
        label.bind("<ButtonPress-1>", self._press)
        label.bind("<B1-Motion>", self._drag)
        label.bind("<ButtonRelease-1>", self._release)
        self.root.bind("<KeyPress>", self._key)
        self._title()
        self._paint()

    def set_tool(self, tool: str) -> None:
        if tool not in ("move", "brush", "type"):
            raise ValueError(f"unknown tool {tool}")
        self.tool = tool
        self._title()

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
        if self.tool == "brush":
            self.stage.brush_drag(x, y)
        else:
            self.stage.drag(x, y)
        self._paint()

    def _release(self, event) -> None:
        x, y = self._doc(event)
        if self.tool == "brush":
            self.stage.brush_release(x, y)
        else:
            self.stage.release(x, y)
        self._paint()
        if self.on_release is not None:
            self.on_release()

    def _paint(self) -> None:
        for y, row in enumerate(scaled_rgb(self.stage.picture, SCALE)):
            self.photo.put("{" + row + "}", to=(0, y))

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
