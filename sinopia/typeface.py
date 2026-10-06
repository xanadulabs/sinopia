"""Draw type into a layer.

Sinopia is a built-in face: the picture does not need a font installed.
Any other name is a fontconfig family, drawn by Pango and baked into the PNG.
"""

from dataclasses import dataclass

from sinopia.glyphs import ADVANCE, GLYPHS, HEIGHT
from sinopia.image import Image

BLACK = (0, 0, 0, 255)


@dataclass
class TextStyle:
    family: str = "Sinopia"
    size: int = 7
    unit: str = "px"
    bold: bool = False
    italic: bool = False
    strikethrough: bool = False
    underline: bool = False
    kerning: int = 0
    stroke: int = 0


def font_families() -> list[str]:
    """Sinopia first, then the families fontconfig can see."""
    try:
        import gi

        gi.require_version("PangoCairo", "1.0")
        from gi.repository import PangoCairo
    except (ImportError, ValueError):
        return ["Sinopia"]
    names = {family.get_name() for family in PangoCairo.font_map_get_default().list_families()}
    names.discard("Sinopia")
    return ["Sinopia", *sorted(names)]


def place_text(
    image: Image,
    x: int,
    y: int,
    text: str,
    color: tuple[int, int, int, int],
    style: TextStyle | None = None,
) -> None:
    """Draw `text` with its top-left at `x`, `y`. The default style is the 5×7 face."""
    if not text:
        return
    style = style or TextStyle()
    if style.family == "Sinopia":
        _place_bitmap(image, x, y, text, color, style)
    else:
        _place_pango(image, x, y, text, color, style)


def _pixel_size(style: TextStyle) -> int:
    if style.unit == "pt":
        return max(1, int(round(style.size * 96 / 72)))
    return max(1, style.size)


def _place_bitmap(
    image: Image,
    x: int,
    y: int,
    text: str,
    color: tuple[int, int, int, int],
    style: TextStyle,
) -> None:
    scale = max(1, int(round(_pixel_size(style) / HEIGHT)))
    fill: list[tuple[int, int]] = []
    cursor = x
    for index, char in enumerate(text):
        glyph = GLYPHS.get(char.upper())
        if glyph is None:
            raise ValueError(f"no glyph for {char!r}")
        for row, bits in enumerate(glyph):
            shift = (HEIGHT - 1 - row) * scale // 2 if style.italic else 0
            for col in range(5):
                if not bits & (1 << (4 - col)):
                    continue
                for sy in range(scale):
                    for sx in range(scale):
                        px = cursor + col * scale + sx + shift
                        py = y + row * scale + sy
                        fill.append((px, py))
                        if style.bold:
                            fill.append((px + scale, py))
        cursor += ADVANCE * scale
        if index + 1 < len(text):
            cursor += style.kerning
    if text and (style.strikethrough or style.underline):
        thickness = max(1, scale)
        left = x
        right = cursor
        if style.strikethrough:
            band = y + (HEIGHT * scale) // 2
            fill.extend((px, band + sy) for px in range(left, right) for sy in range(thickness))
        if style.underline:
            band = y + HEIGHT * scale
            fill.extend((px, band + sy) for px in range(left, right) for sy in range(thickness))
    _paint_mask(image, fill, color, style.stroke)


def _paint_mask(
    image: Image,
    fill: list[tuple[int, int]],
    color: tuple[int, int, int, int],
    stroke: int,
) -> None:
    if stroke <= 0:
        for px, py in fill:
            if 0 <= px < image.width and 0 <= py < image.height:
                image.set(px, py, color)
        return
    limit = stroke * stroke
    outline: set[tuple[int, int]] = set()
    for px, py in fill:
        for dy in range(-stroke, stroke + 1):
            for dx in range(-stroke, stroke + 1):
                if dx * dx + dy * dy <= limit:
                    outline.add((px + dx, py + dy))
    for px, py in outline:
        if 0 <= px < image.width and 0 <= py < image.height:
            image.set(px, py, BLACK)
    for px, py in fill:
        if 0 <= px < image.width and 0 <= py < image.height:
            image.set(px, py, color)


def _place_pango(
    image: Image,
    x: int,
    y: int,
    text: str,
    color: tuple[int, int, int, int],
    style: TextStyle,
) -> None:
    import gi

    gi.require_version("Pango", "1.0")
    gi.require_version("PangoCairo", "1.0")
    import cairo
    from gi.repository import Pango, PangoCairo

    scratch = cairo.ImageSurface(cairo.FORMAT_ARGB32, 1, 1)
    layout = _pango_layout(cairo.Context(scratch), text, style)
    ink, _logical = layout.get_pixel_extents()
    pad = max(0, style.stroke) + 1
    width = max(1, ink.width + pad * 2 + 2)
    height = max(1, ink.height + pad * 2 + 2)
    surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, width, height)
    ctx = cairo.Context(surface)
    ctx.translate(pad - ink.x, pad - ink.y)
    layout = _pango_layout(ctx, text, style)
    fill = tuple(channel / 255 for channel in color)
    if style.stroke > 0:
        PangoCairo.layout_path(ctx, layout)
        ctx.set_source_rgba(0, 0, 0, 1)
        ctx.set_line_width(style.stroke * 2)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke_preserve()
        ctx.set_source_rgba(*fill)
        ctx.fill()
    else:
        ctx.set_source_rgba(*fill)
        PangoCairo.show_layout(ctx, layout)
    _blit(image, x - pad, y - pad, surface)


def _pango_layout(ctx, text: str, style: TextStyle):
    import gi

    gi.require_version("Pango", "1.0")
    gi.require_version("PangoCairo", "1.0")
    from gi.repository import Pango, PangoCairo

    layout = PangoCairo.create_layout(ctx)
    desc = Pango.FontDescription()
    desc.set_family(style.family)
    if style.unit == "px":
        desc.set_absolute_size(max(1, style.size) * Pango.SCALE)
    else:
        desc.set_size(max(1, style.size) * Pango.SCALE)
    desc.set_weight(Pango.Weight.BOLD if style.bold else Pango.Weight.NORMAL)
    desc.set_style(Pango.Style.ITALIC if style.italic else Pango.Style.NORMAL)
    layout.set_font_description(desc)
    attrs = Pango.AttrList()
    if style.strikethrough:
        attrs.insert(Pango.attr_strikethrough_new(True))
    if style.underline:
        attrs.insert(Pango.attr_underline_new(Pango.Underline.SINGLE))
    if style.kerning:
        spacing = int(round(style.kerning * Pango.SCALE * 72 / 96))
        attrs.insert(Pango.attr_letter_spacing_new(spacing))
    layout.set_attributes(attrs)
    layout.set_text(text, -1)
    PangoCairo.update_layout(ctx, layout)
    return layout


def _blit(image: Image, dx: int, dy: int, surface) -> None:
    data = surface.get_data()
    stride = surface.get_stride()
    width = surface.get_width()
    height = surface.get_height()
    for sy in range(height):
        py = dy + sy
        if not 0 <= py < image.height:
            continue
        row = sy * stride
        for sx in range(width):
            px = dx + sx
            if not 0 <= px < image.width:
                continue
            i = row + sx * 4
            b, g, r, a = data[i], data[i + 1], data[i + 2], data[i + 3]
            if a == 0:
                continue
            if a < 255:
                r = min(255, r * 255 // a)
                g = min(255, g * 255 // a)
                b = min(255, b * 255 // a)
            _over(image, px, py, (r, g, b, a))


def _over(image: Image, x: int, y: int, src: tuple[int, int, int, int]) -> None:
    sr, sg, sb, sa = src
    if sa >= 255:
        image.set(x, y, (sr, sg, sb, 255))
        return
    dr, dg, db, da = image.get(x, y)
    keep = 255 - sa
    out_a = sa + (da * keep + 127) // 255
    if out_a == 0:
        image.set(x, y, (0, 0, 0, 0))
        return

    def mix(s: int, d: int) -> int:
        mixed = s * sa + (d * da * keep + 127) // 255
        return (mixed + out_a // 2) // out_a

    image.set(x, y, (mix(sr, dr), mix(sg, dg), mix(sb, db), out_a))
