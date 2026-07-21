"""Shared helpers for resolving and parsing layout SVGs."""

import os
from pathlib import Path

from lxml import etree
from PIL import Image, ImageDraw, ImageFont

TEMPLATES_DIR = "layout/templates"


def parse_layout_id(layout_id: str) -> tuple[str, str]:
    """Splits a 'ratio/name' layout id (e.g. '9:16/btm_left') into (ratio, name)."""
    ratio, name = layout_id.split('/', 1)
    return ratio, name


def layout_svg_path(layout_id: str) -> str:
    """Resolves a 'ratio/name' layout id to its .svg file on disk."""
    ratio, name = parse_layout_id(layout_id)
    return os.path.join(TEMPLATES_DIR, ratio.replace(':', '-'), f"{name}.svg")

def discover_layouts(ratio: str) -> list[str]:
    """Lists every named .svg layout staged under this ratio's template directory, as 'ratio/name' ids."""
    ratio_dir = os.path.join(TEMPLATES_DIR, ratio.replace(':', '-'))
    return sorted(
        f"{ratio}/{Path(filename).stem}"
        for filename in os.listdir(ratio_dir)
        if filename.endswith('.svg')
    )

def get_fitted_font(text: str, font_path: str, max_w: int, max_h: int, min_size: int = 10) -> ImageFont.FreeTypeFont:
    """Calculates the largest font size (down to min_size) that fits text within max_w x max_h."""
    dummy_draw = ImageDraw.Draw(Image.new("RGB", (1, 1)))

    # Start from the box's own height, not a fixed constant - a fixed cap means text can
    # never scale past it even when the box has room for something much larger.
    font_size = max(int(max_h), min_size)
    font = ImageFont.truetype(font_path, font_size)

    while font_size > min_size:
        bbox = dummy_draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        if text_w <= max_w and text_h <= max_h:
            break

        font_size -= 2
        font = ImageFont.truetype(font_path, font_size)

    return font

def get_svg_rects(svg_path):
    """Reads the 'header'/'body' copy zones from the layout SVG, in the SVG's own viewBox units."""
    tree = etree.parse(svg_path)
    root = tree.getroot()

    viewbox = root.attrib.get('viewBox', '').split()
    canvas_w, canvas_h = (float(viewbox[2]), float(viewbox[3])) if len(viewbox) == 4 else (1000.0, 1000.0)

    rects = {}
    for rect in tree.xpath("//*[@id='header' or @id='body']"):
        rects[rect.get('id')] = {
            'x': float(rect.get('x')),
            'y': float(rect.get('y')),
            'w': float(rect.get('width')),
            'h': float(rect.get('height')),
        }
    return rects, canvas_w, canvas_h

