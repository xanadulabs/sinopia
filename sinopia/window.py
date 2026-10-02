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
        self.root = tkinter.Tk()
        self.root.title("Sinopia")
        self.photo = tkinter.PhotoImage(width=picture.width * SCALE, height=picture.height * SCALE)
        label = tkinter.Label(self.root, image=self.photo, borderwidth=0)
        label.pack()
        label.bind("<ButtonPress-1>", self._press)
        label.bind("<B1-Motion>", self._drag)
        label.bind("<ButtonRelease-1>", self._release)
        self._paint()

    def _doc(self, event) -> tuple[int, int]:
        return event.x // SCALE, event.y // SCALE

    def _press(self, event) -> None:
        self.stage.press(*self._doc(event))

    def _drag(self, event) -> None:
        self.stage.drag(*self._doc(event))
        self._paint()

    def _release(self, event) -> None:
        self.stage.release(*self._doc(event))
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
