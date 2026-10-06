"""Normal-mode 'source over' for straight-alpha layers."""

from sinopia.image import Image


def _covered(src_alpha: int, mask: int, opacity: int) -> int:
    """How much of this source pixel replaces the destination, 0-255."""
    return (src_alpha * mask * opacity + 127 * 255) // (255 * 255)


def composite(
    bottom: Image,
    top: Image,
    mask: bytearray | None = None,
    opacity: int = 255,
    dx: int = 0,
    dy: int = 0,
) -> Image:
    """Paint `top` over `bottom`. `dx` and `dy` shift the top layer. A missing mask is fully opaque."""
    if bottom.width != top.width or bottom.height != top.height:
        raise ValueError("layers must be the same size")
    if mask is not None and len(mask) != len(bottom):
        raise ValueError("mask must have one value per pixel")
    if not 0 <= opacity <= 255:
        raise ValueError("opacity must be 0-255")
    if opacity == 0:
        return _copy(bottom)
    if mask is None and opacity == 255 and _solid(top.pixels):
        return _blit(bottom, top, dx, dy)
    return _blend(bottom, top, mask, opacity, dx, dy)


def _copy(image: Image) -> Image:
    out = Image(image.width, image.height)
    out.pixels[:] = image.pixels
    return out


def _solid(pixels: bytearray) -> bool:
    count = len(pixels) // 4
    return pixels[3::4] == b"\xff" * count


def _blit(bottom: Image, top: Image, dx: int, dy: int) -> Image:
    """Copy an opaque layer. Pixels it does not cover stay the picture underneath."""
    width = bottom.width
    height = bottom.height
    if dx == 0 and dy == 0:
        return _copy(top)
    out = _copy(bottom)
    x0 = max(0, dx)
    x1 = min(width, width + dx)
    y0 = max(0, dy)
    y1 = min(height, height + dy)
    if x1 <= x0 or y1 <= y0:
        return out
    span = (x1 - x0) * 4
    source_x = x0 - dx
    for y in range(y0, y1):
        dest = (y * width + x0) * 4
        src = ((y - dy) * width + source_x) * 4
        out.pixels[dest : dest + span] = top.pixels[src : src + span]
    return out


def _blend(
    bottom: Image,
    top: Image,
    mask: bytearray | None,
    opacity: int,
    dx: int,
    dy: int,
) -> Image:
    """The same blend as before, skipping rows the top layer does not touch."""
    out = _copy(bottom)
    bp = bottom.pixels
    tp = top.pixels
    op = out.pixels
    width = bottom.width
    height = bottom.height
    opaque = opacity == 255
    clear = b"\x00" * width
    solid = b"\xff" * width
    x0 = max(0, dx)
    x1 = min(width, width + dx)
    if x1 <= x0:
        return out
    source_x = x0 - dx
    span = x1 - x0
    for y in range(height):
        sy = y - dy
        if not 0 <= sy < height:
            continue
        src_row = sy * width
        alphas = tp[(src_row + source_x) * 4 + 3 : (src_row + source_x + span) * 4 : 4]
        if alphas == clear[:span]:
            continue
        mask_row = None if mask is None else src_row
        masks = None if mask_row is None else mask[mask_row + source_x : mask_row + source_x + span]
        if masks is not None and masks == clear[:span]:
            continue
        covered = opaque and alphas == solid[:span] and (masks is None or masks == solid[:span])
        if covered:
            dest = (y * width + x0) * 4
            src = (src_row + source_x) * 4
            op[dest : dest + span * 4] = tp[src : src + span * 4]
            continue
        band = alphas if masks is None else masks
        lead = len(band) - len(band.lstrip(b"\x00"))
        core = len(band.lstrip(b"\x00").rstrip(b"\x00"))
        for x in range(x0 + lead, x0 + lead + core):
            sx = x - dx
            i = (y * width + x) * 4
            s = (src_row + sx) * 4
            src_a = tp[s + 3]
            mask_value = 255 if mask_row is None else mask[mask_row + sx]
            if opaque and src_a == 255 and mask_value == 255:
                op[i : i + 4] = tp[s : s + 4]
                continue
            cover = _covered(src_a, mask_value, opacity)
            if cover == 0:
                continue
            keep = 255 - cover
            dst_a = bp[i + 3]
            out_a = cover + (dst_a * keep + 127) // 255
            op[i + 3] = out_a
            for c in range(3):
                mixed = tp[s + c] * cover + (bp[i + c] * dst_a * keep + 127) // 255
                op[i + c] = (mixed + out_a // 2) // out_a
    return out
