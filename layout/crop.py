"""Crops a hero image into every staged aspect ratio."""

import re
from PIL import Image, ImageDraw, ImageFont
from layout.utils import layout_svg_path
import xml.etree.ElementTree as ET


def to_staged_ratios(main_img: Image.Image, crop_boxes: dict, canvas_w: float, canvas_h: float) -> dict:
    """Crops main_img to each staged aspect ratio's guide rect. Returns {crop_name: cropped_image}."""
    processed_crops = {}

    scale_x = main_img.width / canvas_w
    scale_y = main_img.height / canvas_h

    for crop_name, box in crop_boxes.items():
        left = box['x'] * scale_x
        top = box['y'] * scale_y
        right = left + box['w'] * scale_x
        bottom = top + box['h'] * scale_y

        processed_crops[crop_name] = main_img.crop((left, top, right, bottom))

    return processed_crops

def normalize_ratio(crop_name: str) -> str:
    """Strips Illustrator's '-N' or auto-generated ID suffix from a duplicate crop id, e.g. '1:1-2' -> '1:1'."""
    # TODO: move Illustrator-specific export logic into own file
    crop_name = re.sub(r'_\d{10,}_?$', '', crop_name)
    return re.sub(r'-\d+$', '', crop_name)


_PATH_TOKEN_RE = re.compile(r'([MmHhVvLlZz])([^MmHhVvLlZz]*)')


def _first_subpath_bbox(d: str) -> dict | None:
    """Walks the first M..(next M) subpath's H/h/V/v/L/l commands to compute its bounding box, tolerant of either absolute or relative casing."""
    x = y = 0.0
    xs: list[float] = []
    ys: list[float] = []
    started = False

    for command, raw_args in _PATH_TOKEN_RE.findall(d):
        if command in 'Zz':
            break
        if command in 'Mm' and started:
            break  # second subpath - only want the first (the real crop rect)

        nums = [float(n) for n in re.findall(r'-?\d+\.?\d*', raw_args)]
        if command == 'M':
            x, y = nums[0], nums[1]
        elif command == 'm':
            x, y = x + nums[0], y + nums[1]
        elif command == 'H':
            x = nums[0]
        elif command == 'h':
            x = x + nums[0]
        elif command == 'V':
            y = nums[0]
        elif command == 'v':
            y = y + nums[0]
        elif command == 'L':
            x, y = nums[0], nums[1]
        elif command == 'l':
            x, y = x + nums[0], y + nums[1]
        else:
            continue

        started = True
        xs.append(x)
        ys.append(y)

    if not xs:
        return None
    return {'x': min(xs), 'y': min(ys), 'w': max(xs) - min(xs), 'h': max(ys) - min(ys)}


def get_rects(layout_id: str):
    """Parses the layout SVG's Crop_Zones layer. Returns the crop rects plus the SVG canvas size."""
    tree = ET.parse(layout_svg_path(layout_id))
    root = tree.getroot()

    viewbox = root.attrib.get('viewBox', '').split()
    canvas_w, canvas_h = (float(viewbox[2]), float(viewbox[3])) if len(viewbox) == 4 else (1000.0, 1000.0)

    # strip namespaces: '{http://www.w3.org/2000/svg}g' -> 'g'
    for elem in root.iter():
        if '}' in elem.tag:
            elem.tag = elem.tag.split('}', 1)[1]

    crop_boxes = {}
    crop_layer = root.find(".//g[@id='Crop_Zones']")

    if crop_layer is not None:
        for group in crop_layer.findall("g"):
            crop_name = group.attrib.get('id', 'unknown').lstrip('_')  # Illustrator prefixes IDs like "_1:1"

            rect = group.find("rect")
            if rect is not None:
                crop_boxes[crop_name] = {
                    'x': float(rect.attrib.get('x', 0)),
                    'y': float(rect.attrib.get('y', 0)),
                    'w': float(rect.attrib.get('width', 0)),
                    'h': float(rect.attrib.get('height', 0)),
                }
                continue

            # crop guides exported as a compound <path> instead of <rect>: two subpaths,
            # the first is the real crop rect, the second just traces the full canvas
            path = group.find("path")
            if path is not None:
                bbox = _first_subpath_bbox(path.attrib.get('d', ''))
                if bbox is not None:
                    crop_boxes[crop_name] = bbox
                else:
                    print(f"Failed to parse crop path for '{crop_name}'. Please change layer to a solid-fill rect in Illustrator.")

    return crop_boxes, canvas_w, canvas_h

