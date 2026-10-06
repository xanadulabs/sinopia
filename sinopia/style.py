"""Layer styles. A drop shadow is a black copy of the visible layer, shifted."""

from sinopia.composite import _covered
from sinopia.image import Image


def shadow_image(layer) -> Image:
    """Black pixels where the layer would show, including its mask and opacity."""
    image = Image(layer.image.width, layer.image.height)
    source = layer.image.pixels
    width = layer.image.width
    out = image.pixels
    if layer.mask is None and layer.opacity == 255:
        out[3::4] = source[3::4]
        return image
    clear = b"\x00" * width
    for y in range(layer.image.height):
        base = y * width * 4
        alphas = source[base + 3 : base + width * 4 : 4]
        if alphas == clear:
            continue
        row = y * width
        for x in range(width):
            mask = 255 if layer.mask is None else layer.mask[row + x]
            alpha = _covered(alphas[x], mask, layer.opacity)
            if alpha:
                out[(row + x) * 4 + 3] = alpha
    return image
