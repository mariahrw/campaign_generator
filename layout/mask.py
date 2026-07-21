"""Renders a layout SVG's product rect to a mask."""

import io
import re

import cairosvg
from lxml import etree
from PIL import Image

from layout.utils import layout_svg_path


def get_bbox(mask: Image.Image) -> tuple[int, int, int, int] | None:
    """Finds the white rectangle's bounding box directly from the mask's own pixels."""
    return mask.convert("L").point(lambda p: 255 if p > 200 else 0).getbbox()

def render(layout_id: str) -> Image.Image:
    """Renders the layout SVG's 'product' rect (transform applied) to an in-memory black-and-white mask."""
    svg_path = layout_svg_path(layout_id)
    tree = etree.parse(svg_path)
    root = tree.getroot()
    viewbox = root.attrib.get('viewBox', '0 0 1000 1000')
    vb_w, vb_h = (float(v) for v in viewbox.split()[2:4])

    product_rect = tree.xpath(".//*[@id='product']")[0]
    rect_svg = re.sub(r'class="[^"]*"', '', etree.tostring(product_rect).decode())  # strip fill color, force white-on-black

    wrapper_svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{viewbox}">'
        '<rect width="100%" height="100%" fill="black"/>'
        f'<g fill="white">{rect_svg}</g>'
        '</svg>'
    )

    png_bytes = cairosvg.svg2png(bytestring=wrapper_svg.encode(), output_width=vb_w, output_height=vb_h)
    return Image.open(io.BytesIO(png_bytes)).convert("L")