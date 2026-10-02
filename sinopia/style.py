"""Layer styles. A drop shadow is a black copy of the visible layer, shifted."""

from sinopia.composite import _covered
from sinopia.image import Image


def shadow_image(layer) -> Image:
    """Black pixels where the layer would show, including its mask and opacity."""
    image = Image(layer.image.width, layer.image.height)
    source = layer.image.pixels
    for index in range(len(layer.image)):
        mask = 255 if layer.mask is None else layer.mask[index]
        alpha = _covered(source[index * 4 + 3], mask, layer.opacity)
        if alpha:
            image.pixels[index * 4 + 3] = alpha
    return image
