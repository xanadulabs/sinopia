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

    out = Image(bottom.width, bottom.height)
    bp = bottom.pixels
    tp = top.pixels
    op = out.pixels
    width = bottom.width
    height = bottom.height
    opaque = opacity == 255
    for y in range(height):
        sy = y - dy
        row_inside = 0 <= sy < height
        mask_row = None if mask is None or not row_inside else sy * width
        for x in range(width):
            i = (y * width + x) * 4
            if row_inside:
                sx = x - dx
                if 0 <= sx < width:
                    s = (sy * width + sx) * 4
                    src_a = tp[s + 3]
                    mask_value = 255 if mask_row is None else mask[mask_row + sx]
                    if opaque and src_a == 255 and mask_value == 255:
                        op[i] = tp[s]
                        op[i + 1] = tp[s + 1]
                        op[i + 2] = tp[s + 2]
                        op[i + 3] = 255
                        continue
                else:
                    s = 0
                    src_a = 0
                    mask_value = 0
            else:
                s = 0
                src_a = 0
                mask_value = 0
            cover = _covered(src_a, mask_value, opacity)
            if cover == 0:
                op[i : i + 4] = bp[i : i + 4]
                continue
            keep = 255 - cover
            dst_a = bp[i + 3]
            out_a = cover + (dst_a * keep + 127) // 255
            op[i + 3] = out_a
            if out_a == 0:
                continue
            for c in range(3):
                mixed = tp[s + c] * cover + (bp[i + c] * dst_a * keep + 127) // 255
                op[i + c] = (mixed + out_a // 2) // out_a
    return out
