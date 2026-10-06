"""The Sinopia mark: a pixel sketch in sinopia on a broken clay tablet.

The same picture is the window icon, the desktop shortcut, and the left half
of the About box. `sinopia.png` at the root of the project is that file.
"""

from sinopia.image import Image

# A worn slab. The lower right is snapped off. The inset is the proof:
# a sinopia field and the green circle, in chunky pixels.
_ROWS = (
    "                                        ",
    "                                        ",
    "      ==========================        ",
    "    ++##########################//      ",
    "   +#############################//     ",
    "   +####RRRRRRRRRRRR############///     ",
    "   +####RrrrrrrrrrrR###########////     ",
    "   +####RrrrrrrrrrrR##########////      ",
    "   +####RrrrgggrrrR#########////        ",
    "   +####RrrggggggrR########////         ",
    "   +####RrgggggggrR#######////          ",
    "   +####RrgggggggrR######////           ",
    "   +####RrrggggggrR#####////            ",
    "   +####RrrrgggrrrR####////             ",
    "   +####RrrrrrrrrR#####///              ",
    "   +####RRRRRRRRRR####///               ",
    "   +##################//                ",
    "   +#################//                 ",
    "   +#############c###/                  ",
    "   +###########c####/                   ",
    "   +#########c######/                   ",
    "   +#######c########/                   ",
    "   +#####c##########/                   ",
    "   +###c############/                   ",
    "   +#c##############/                   ",
    "   +################/                   ",
    "   //////////////////                   ",
    "                                        ",
    "                                        ",
)

_COLOR = {
    "#": (198, 150, 102, 255),
    "+": (230, 198, 156, 255),
    "=": (120, 82, 48, 255),
    "/": (74, 48, 30, 255),
    "c": (74, 48, 30, 255),
    "R": (112, 28, 20, 255),
    "r": (176, 52, 34, 255),
    "G": (18, 86, 40, 255),
    "g": (32, 132, 62, 255),
}


SHORTCUT_ZOOM = 8


def tablet() -> Image:
    """A partial clay tablet with the proof painted on it in chunky pixels."""
    width = len(_ROWS[0])
    image = Image(width, len(_ROWS))
    for y, row in enumerate(_ROWS):
        if len(row) != width:
            raise ValueError("mark rows must be the same width")
        for x, cell in enumerate(row):
            if cell != " ":
                image.set(x, y, _COLOR[cell])
    return image


def scaled(image: Image, factor: int) -> Image:
    """Nearest-neighbor zoom, so the desktop file stays pixelated."""
    if factor < 1:
        raise ValueError("scale must be at least 1")
    out = Image(image.width * factor, image.height * factor)
    span = out.width * 4
    for y in range(image.height):
        wide = bytearray()
        row = y * image.width * 4
        for x in range(image.width):
            wide += image.pixels[row + x * 4 : row + x * 4 + 4] * factor
        block = bytes(wide)
        start = y * factor * span
        for _step in range(factor):
            out.pixels[start : start + span] = block
            start += span
    return out


def photo(root, zoom: int = 1):
    """A Tk picture of the mark. Empty pixels stay transparent."""
    import tkinter

    image = tablet()
    shot = tkinter.PhotoImage(width=image.width, height=image.height)
    for y in range(image.height):
        for x in range(image.width):
            red, green, blue, alpha = image.get(x, y)
            if alpha:
                shot.put(f"#{red:02x}{green:02x}{blue:02x}", (x, y))
    if zoom == 1:
        return shot
    return shot.zoom(zoom, zoom)
