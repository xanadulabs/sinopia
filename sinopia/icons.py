"""Toolbox pictures. The shapes are ours: a move cross, a brush nib, and an A.

The shortcut letter sits in the corner of the button. The canvas cursor is the
shape alone, so the click lands on the working point.
"""

from pathlib import Path

from sinopia.glyphs import GLYPHS

SIZE = 24
INK = "#202020"


def tool_bits(name: str, letter: str | None = None) -> tuple[list[str], tuple[int, int]]:
    grid = [["0"] * SIZE for _ in range(SIZE)]
    hotspot = _draw_shape(grid, name)
    if letter:
        _draw_letter(grid, letter)
    return ["".join(row) for row in grid], hotspot


def tool_image(root, name: str, letter: str):
    import tkinter

    bits, _hot = tool_bits(name, letter)
    image = tkinter.PhotoImage(width=SIZE, height=SIZE)
    for y, row in enumerate(bits):
        for x, bit in enumerate(row):
            if bit == "1":
                image.put(INK, (x, y))
    return image


def tool_cursor(name: str) -> str:
    bits, (hot_x, hot_y) = tool_bits(name)
    path = Path(f"/tmp/sinopia-cursor-{name}.xbm")
    path.write_text(_xbm(name, bits, hot_x, hot_y), encoding="ascii")
    return f"@{path} black"


def _draw_shape(grid: list[list[str]], name: str) -> tuple[int, int]:
    if name == "move":
        for i in range(4, 20):
            _plot(grid, i, 11)
            _plot(grid, 11, i)
        _head(grid, 4, 11, -1, 0)
        _head(grid, 19, 11, 1, 0)
        _head(grid, 11, 4, 0, -1)
        _head(grid, 11, 19, 0, 1)
        return 11, 11
    if name == "brush":
        for i in range(11):
            _plot(grid, 16 - i, 3 + i)
            _plot(grid, 17 - i, 3 + i)
            _plot(grid, 16 - i, 4 + i)
        _plot(grid, 5, 15)
        return 5, 15
    if name == "type":
        for col, row in (
            (11, 2),
            (10, 3),
            (12, 3),
            (9, 4),
            (13, 4),
            (8, 5),
            (14, 5),
            (8, 6),
            (9, 6),
            (10, 6),
            (11, 6),
            (12, 6),
            (13, 6),
            (14, 6),
            (8, 7),
            (14, 7),
            (8, 8),
            (14, 8),
            (8, 9),
            (14, 9),
        ):
            _plot(grid, col, row)
        return 8, 2
    raise ValueError(f"unknown tool {name}")


def _head(grid: list[list[str]], x: int, y: int, dx: int, dy: int) -> None:
    _plot(grid, x, y)
    side_x, side_y = -dy, dx
    _plot(grid, x - dx + side_x, y - dy + side_y)
    _plot(grid, x - dx - side_x, y - dy - side_y)


def _draw_letter(grid: list[list[str]], letter: str) -> None:
    glyph = GLYPHS[letter.upper()]
    origin_x = SIZE - 6
    origin_y = SIZE - 8
    for row, bits in enumerate(glyph):
        for col in range(5):
            if bits & (1 << (4 - col)):
                _plot(grid, origin_x + col, origin_y + row)


def _plot(grid: list[list[str]], x: int, y: int) -> None:
    if 0 <= x < SIZE and 0 <= y < SIZE:
        grid[y][x] = "1"


def _xbm(name: str, bits: list[str], hot_x: int, hot_y: int) -> str:
    values: list[str] = []
    for row in bits:
        acc = 0
        for index, bit in enumerate(row):
            if bit == "1":
                acc |= 1 << (index % 8)
            if index % 8 == 7:
                values.append(f"0x{acc:02x}")
                acc = 0
        if len(row) % 8:
            values.append(f"0x{acc:02x}")
    lines = []
    for start in range(0, len(values), 12):
        lines.append("  " + ", ".join(values[start : start + 12]))
    body = ",\n".join(lines)
    return (
        f"#define {name}_width {SIZE}\n"
        f"#define {name}_height {SIZE}\n"
        f"#define {name}_x_hot {hot_x}\n"
        f"#define {name}_y_hot {hot_y}\n"
        f"static unsigned char {name}_bits[] = {{\n{body}}};\n"
    )
