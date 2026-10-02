"""Normal-mode 'source over' for straight-alpha layers."""

from sinopia.image import Image


def _covered(src_alpha: int, mask: int, opacity: int) -> int:
    """How much of this source pixel replaces the destination, 0-255."""
    return (src_alpha * mask * opacity + 127 * 255) // (255 * 255)


def composite(bottom: Image, top: Image, mask: bytearray | None = None, opacity: int = 255) -> Image:
    """Paint `top` over `bottom`. A missing mask is fully opaque."""
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
    n = len(bottom)
    for p in range(n):
        i = p * 4
        cover = _covered(tp[i + 3], 255 if mask is None else mask[p], opacity)
        keep = 255 - cover
        dst_a = bp[i + 3]
        out_a = cover + (dst_a * keep + 127) // 255
        op[i + 3] = out_a
        if out_a == 0:
            continue
        for c in range(3):
            src_c = tp[i + c]
            dst_c = bp[i + c]
            mixed = src_c * cover + (dst_c * dst_a * keep + 127) // 255
            op[i + c] = (mixed + out_a // 2) // out_a
    return out
