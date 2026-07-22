"""Derives camera framing and renders copy onto hero images."""

import os
import re
import textwrap
from pathlib import Path
from typing import Dict

from lxml import etree
from PIL import Image, ImageColor, ImageDraw, ImageFont

from models import CampaignMessage, Brand
from layout.utils import parse_layout_id, layout_svg_path, get_fitted_font, get_svg_rects
from layout.mask import get_bbox, render
TEMPLATES_DIR = "layout/templates"


def describe_camera_framing(layout_id: str) -> str:
    """Derives a camera-angle/framing text description from the mask rect's geometry."""
    # Feeding Gemini the mask as an image and asking it to infer composition gave inconsistent results, so its position/size get translated into literal camera-angle language instead.
    # The general principle: wherever real product imagery isn't available to composite from, extract concrete geometric information (position, framing, rotation) and hand the model literal instructions rather than pasting in partial visual references.
    mask = render(layout_id)
    bbox = get_bbox(mask)
    if bbox is None:
        return ""

    x0, y0, x1, y1 = bbox
    width_scale = (x1 - x0) / mask.width
    height_scale = (y1 - y0) / mask.height
    center_x_frac = ((x0 + x1) / 2) / mask.width
    center_y_frac = ((y0 + y1) / 2) / mask.height

    if center_x_frac < 0.4:
        h_pos = "the subject sits toward the left third of the frame"
    elif center_x_frac > 0.6:
        h_pos = "the subject sits toward the right third of the frame"
    else:
        h_pos = "the subject is centered horizontally"

    if center_y_frac > 0.55:
        camera_height = (
            "the camera is positioned near table/surface height, roughly eye-level with the "
            "product and angled slightly downward - not an overhead flat-lay, not a distant "
            "elevated shot"
        )
    elif center_y_frac < 0.45:
        camera_height = "the camera is positioned slightly above the product, a gentle high angle looking down"
    else:
        camera_height = "the camera is at the product's own eye-level, a straight-on framing"

    scale = min(width_scale, height_scale)
    if scale >= 0.55:
        distance = "an extreme close-up / macro framing - the subject fills nearly the entire vertical frame"
    elif scale >= 0.3:
        distance = "a close, intimate framing - the subject is the dominant foreground element"
    else:
        distance = "a wider environmental framing - the subject is one element within a larger scene"

    return (
        f"CAMERA & FRAMING: {distance}. {h_pos.capitalize()}. {camera_height.capitalize()}. "
        "This exact camera framing and perspective must be shared by every generated image in "
        "this shoot, so they read as one consistent photograph rather than independently "
        "angled shots."
    )


def _draw_copy_backgrounds(hero_img: Image.Image, boxes: list[dict], brand: Brand) -> Image.Image:
    """Composites a translucent brand-colored rect behind each copy box, via a separate overlay since PIL doesn't alpha-blend a direct draw."""
    overlay = Image.new("RGBA", hero_img.size, (0, 0, 0, 0))
    overlay_draw = ImageDraw.Draw(overlay)
    fill = ImageColor.getrgb(brand.copy_background_color) + (round(brand.copy_background_opacity * 255),)

    for box in boxes:
        overlay_draw.rectangle([box['x'], box['y'], box['x'] + box['w'], box['y'] + box['h']], fill=fill)

    return Image.alpha_composite(hero_img, overlay)


def render_copy_to_image(
    base_img: Path,
    localized_copy: Dict[str, Dict[str, CampaignMessage]],
    brand: Brand,
    output_dir: Path,
    layout_id: str,
) -> list[Path]:
    """Draws each region/language's localized copy onto a fresh copy of the hero image."""
    rendered_images = []

    _, layout_name = parse_layout_id(layout_id)
    rects, canvas_w, canvas_h = get_svg_rects(layout_svg_path(layout_id))

    for region, languages in localized_copy.items():
        region_dir = os.path.join(output_dir, region.replace(" ", "_"))
        os.makedirs(region_dir, exist_ok=True)

        for language, message in languages.items():
            hero_img = Image.open(base_img).convert("RGBA")

            # The SVG rects live in the layout's own viewBox coordinate space,
            # which rarely matches the actual rendered image's pixel size.
            scale_x = hero_img.width / canvas_w
            scale_y = hero_img.height / canvas_h

            def scaled_box(box):
                return {
                    'x': box['x'] * scale_x,
                    'y': box['y'] * scale_y,
                    'w': box['w'] * scale_x,
                    'h': box['h'] * scale_y,
                }

            header_box = scaled_box(rects['header']) if 'header' in rects and message.tag else None
            body_box = scaled_box(rects['body']) if 'body' in rects and message.body else None

            if brand.copy_background_opacity > 0:
                hero_img = _draw_copy_backgrounds(hero_img, [b for b in (header_box, body_box) if b], brand)

            draw = ImageDraw.Draw(hero_img)

            if header_box:
                # Narrower wrap width than body - shorter lines let get_fitted_font use more
                # of the box's height, since it was previously measuring the tag as one long
                # unwrapped line and shrinking to fit the box's width alone.
                header_lines = textwrap.wrap(message.tag, width=20)
                header_font = get_fitted_font("\n".join(header_lines), brand.primary_font, header_box['w'], header_box['h'])

                current_y = header_box['y']
                for line in header_lines:
                    draw.text((header_box['x'], current_y), line, fill=brand.primary_color, font=header_font)
                    current_y += header_font.size + 10

            if body_box:
                center_x = body_box['x'] + (body_box['w'] / 2)

                # Wrap the text and fit the font to the body box, not the header's
                lines = textwrap.wrap(message.body, width=40)
                body_font = get_fitted_font("\n".join(lines), brand.primary_font, body_box['w'], body_box['h'])

                current_y = body_box['y']
                for line in lines:
                    draw.text((center_x, current_y), line, fill=brand.secondary_color, font=body_font, anchor="ma")
                    current_y += body_font.size + 10

            # layout_name keeps this unique once multiple layouts share one output ratio folder
            save_path = os.path.join(region_dir, f"hero_{language}_{layout_name}.png")
            hero_img.save(save_path, "PNG")
            rendered_images.append(Path(save_path))

    return rendered_images
