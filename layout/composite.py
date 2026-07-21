"""Pastes the product image into its background mask."""

from PIL import Image
from layout.mask import get_bbox


def product_into_scene(background: Image.Image, product_image: Image.Image, mask: Image.Image) -> Image.Image:
    """Pastes product_image into the mask's rectangle on background, at the mask's position/scale."""
    bbox = get_bbox(mask)
    if bbox is None:
        return background.convert("RGBA")

    scale_x = background.width / mask.width
    scale_y = background.height / mask.height
    box_x0, box_y0, box_x1, box_y1 = bbox
    box = {
        'x': box_x0 * scale_x, 'y': box_y0 * scale_y,
        'w': (box_x1 - box_x0) * scale_x, 'h': (box_y1 - box_y0) * scale_y,
    }

    return fit_and_paste(background, product_image, box)


def fit_and_paste(base: Image.Image, overlay: Image.Image, box: dict) -> Image.Image:
    """Contain-fits overlay into box {x,y,w,h} and pastes it centered onto a copy of base."""
    fitted = overlay.convert("RGBA")
    fitted.thumbnail((box['w'], box['h']), Image.LANCZOS)

    result = base.convert("RGBA").copy()
    paste_x = int(box['x'] + (box['w'] - fitted.width) / 2)
    paste_y = int(box['y'] + (box['h'] - fitted.height) / 2)
    result.paste(fitted, (paste_x, paste_y), fitted)
    return result

