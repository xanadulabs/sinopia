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
    for y in range(height):
        sy = y - dy
        for x in range(width):
            sx = x - dx
            i = (y * width + x) * 4
            if 0 <= sx < width and 0 <= sy < height:
                s = (sy * width + sx) * 4
                src = (tp[s], tp[s + 1], tp[s + 2], tp[s + 3])
                mask_value = 255 if mask is None else mask[sy * width + sx]
            else:
                src = (0, 0, 0, 0)
                mask_value = 0
            cover = _covered(src[3], mask_value, opacity)
            keep = 255 - cover
            dst_a = bp[i + 3]
            out_a = cover + (dst_a * keep + 127) // 255
            op[i + 3] = out_a
            if out_a == 0:
                continue
            for c in range(3):
                mixed = src[c] * cover + (bp[i + c] * dst_a * keep + 127) // 255
                op[i + c] = (mixed + out_a // 2) // out_a
    return out
