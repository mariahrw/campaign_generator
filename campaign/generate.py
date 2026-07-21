"""Orchestrates the full brief-to-creatives generation pipeline."""

from pathlib import Path

from PIL import Image
from rich.panel import Panel

from generation.interfaces import ImageGenService
from utils.cli import console, header, step, warning
from utils.io import create_dir, create_versioned_dir, get_product_shot_path, process_product_json
from layout.engine import render_copy_to_image, parse_layout_id
from layout.utils import discover_layouts
from layout.crop import to_staged_ratios, normalize_ratio, get_rects


def generate_campaign(raw_json: str, gen_service: ImageGenService, output_dir: Path):
    with step("Validating campaign brief"):
        brief = process_product_json(raw_json)
    brief_dir = create_versioned_dir(output_dir, brief.id)

    layouts = sorted({layout for product in brief.products for layout in product.layouts})
    regions = ", ".join(market.target_region for market in brief.target_markets)
    console.print(Panel(
        f"Campaign: {brief.campaign_message.tag}\n"
        f"Products: {len(brief.products)} | Target Markets: {regions}\n"
        f"Layouts: {', '.join(layouts)}",
        title="Campaign Generator", border_style="cyan",
    ))

    for product in brief.products:
        if not get_product_shot_path(product.asset_dir):
            warning(
                f"Skipping '{product.name}' ({product.id})",
                f"no reference photo found in {product.asset_dir} (expected product.png)",
                severe=True,
            )
            continue

        product_dir = create_dir(brief_dir, product.id)
        header(product.name)

        # copy is the same regardless of which layout renders it - localize once per product
        with step("Localizing copy", indent=1):
            localized_copy = gen_service.localize(brief=brief)

        for ratio in product.layouts:
            for layout_id in discover_layouts(ratio):
                _, layout_name = parse_layout_id(layout_id)
                layout_dir = create_dir(product_dir, ratio)
                header(layout_name, indent=1)

                # 1. Generate the hero image, using the layout SVG as a spatial guide
                with step("Generating hero image", indent=2):
                    hero_image = gen_service.generate_product_image(
                        brief=brief, product=product, output_dir=layout_dir, layout_id=layout_id,
                    )

                # 2. Render the localized copy onto the hero image, per region/language
                with step("Rendering localized copy", indent=2):
                    localized_images = render_copy_to_image(
                        hero_image, localized_copy, brand=brief.brand, output_dir=layout_dir, layout_id=layout_id,
                    )

                # 3. Crop each localized hero into every ratio staged in this layout, saved -
                # skipped entirely (not just a no-op) when this layout has none staged, so the
                # step list doesn't imply cropping happened when it didn't
                crop_boxes, crop_canvas_w, crop_canvas_h = get_rects(layout_id)
                if not crop_boxes:
                    continue

                with step("Cropping staged ratios", indent=2):
                    for localized_img_path in localized_images:
                        region_name = localized_img_path.parent.name

                        with Image.open(localized_img_path) as img:
                            hero_img = img.convert("RGBA")
                            crops = to_staged_ratios(hero_img, crop_boxes, crop_canvas_w, crop_canvas_h)
                            # counts, not the raw crop id, drive the filename suffix - Illustrator's
                            # own disambiguator (e.g. a long pasted-duplicate ID) is noise once the
                            # ratio's been normalized, so a clean "-2", "-3", ... is used instead
                            ratio_counts: dict[str, int] = {}
                            for crop_name, crop_img in crops.items():
                                ratio_label = normalize_ratio(crop_name)
                                crop_ratio_dir = create_dir(create_dir(product_dir, ratio_label), region_name)
                                ratio_counts[ratio_label] = ratio_counts.get(ratio_label, 0) + 1
                                count = ratio_counts[ratio_label]
                                dedup_suffix = f"-{count}" if count > 1 else ""
                                crop_img.save(crop_ratio_dir / f"{localized_img_path.stem}{dedup_suffix}{localized_img_path.suffix}", "PNG")

    console.print(f"\n[green]✓[/green] Output saved to {brief_dir}")
