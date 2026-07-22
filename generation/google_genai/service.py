"""Gemini-backed image generation and copy localization service."""

import io
import json
import os
from pathlib import Path
from typing import Dict

from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image

from generation.interfaces import ImageGenService, CopyGenService
from models import Product, Brief, CampaignMessage
from utils.cli import warning
from utils.io import get_product_shot_path
from layout.engine import describe_camera_framing, parse_layout_id
from layout.mask import render as render_product_mask
from layout.composite import product_into_scene
from . import prompts

IMAGE_GEN_MODEL = "gemini-2.5-flash-image"

LOCALIZER_TEMP = 0.1
LOCALIZER_MODEL = "gemini-3.1-flash-lite"

# TODO: this class inherits both ImageGenService and CopyGenService at once, split into separate classes per interface.
class GoogleGenAIService(ImageGenService, CopyGenService):
    def __init__(self):
        load_dotenv(dotenv_path=".env")
        api_key = os.environ.get("GEMINI_API_KEY")
        # Heavy client setup only happens once
        self.client = genai.Client(api_key=api_key)

    def _generate_image(self, parts: list[types.Part], aspect_ratio: str, retries: int = 2) -> Image.Image:
        """Shared plumbing for the hero-image sub-generations (cutout, background). Retries on empty/failed responses."""
        last_error = None
        for attempt in range(1 + retries):
            response = self.client.models.generate_content(
                model=IMAGE_GEN_MODEL,
                contents=parts,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(aspect_ratio=aspect_ratio),
                ),
            )
            if response.parts:
                for part in response.parts:
                    if part.inline_data:
                        # part.as_image() returns google.genai.types.Image (a bytes wrapper),
                        # not a PIL Image - convert so callers get normal PIL operations.
                        return Image.open(io.BytesIO(part.as_image().image_bytes))
            last_error = f"no image data (prompt_feedback={response.prompt_feedback})"
            if attempt < retries:
                print(f"GenAI image generation attempt {attempt + 1} failed ({last_error}), retrying...")
        raise RuntimeError(f"GenAI response contained no image data after {1 + retries} attempts: {last_error}")

    def generate_background_scene(self, brief: Brief, product: Product, layout_id: str) -> Image.Image:
        """Generates the environment only - no product/packaging - to be composited with the cutout afterward."""
        camera_framing = describe_camera_framing(layout_id)
        prompt_text = prompts.background_scene_prompt(
            category=product.category,
            tone=", ".join(brief.tone),
            shot_type=product.shot_type,
            scene_setting=product.scene_setting,
            camera_framing=camera_framing,
        )
        parts = [types.Part.from_text(text=prompt_text)]

        ratio, _ = parse_layout_id(layout_id)
        return self._generate_image(parts, aspect_ratio=ratio)

    def generate_product_image(
        self,
        brief: Brief,
        product: Product,
        output_dir: Path,
        layout_id: str = "9:16/btm_left",
    ) -> Path:
        """Composites the product's real reference photo onto a generated background."""
        reference_photo_path = get_product_shot_path(product.asset_dir)
        if not reference_photo_path:
            raise ValueError(
                f"No reference photo found for product '{product.id}' in {product.asset_dir} "
                "(expected product.png) - TrueFrame requires a real product photo; "
                "it does not generate trademarked packaging from a text description."
            )
        product_image = Image.open(reference_photo_path).convert("RGBA")

        background = self.generate_background_scene(brief, product, layout_id)
        # deterministic placement only - no GenAI lighting/shadow harmonization pass
        hero_image = product_into_scene(background, product_image, render_product_mask(layout_id))

        _, layout_name = parse_layout_id(layout_id)
        save_path = output_dir / f"{product.id}_hero_{layout_name}.png"
        hero_image.convert("RGB").save(save_path, "PNG")
        return save_path

    def localize(self, brief: Brief) -> Dict[str, Dict[str, CampaignMessage]]:
        markets = [(market.target_region, ", ".join(market.IETF_codes)) for market in brief.target_markets]

        if not brief.campaign_message.tag or not brief.campaign_message.body:
            warning("No copy in campaign_message (tag or body empty) - skipping translation, images will have no copy", indent=1)
            empty_msg = CampaignMessage(tag="", body="")
            return {
                market.target_region: {lang: empty_msg for lang in market.IETF_codes}
                for market in brief.target_markets
            }

        prompt_text = prompts.localize_prompt(brief.campaign_message.tag, brief.campaign_message.body, markets)
        system_instruction = prompts.localize_system_instruction(", ".join(brief.tone))

        response = self.client.models.generate_content(
            model=LOCALIZER_MODEL,
            contents=prompt_text,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=LOCALIZER_TEMP,
                response_mime_type="application/json",
            ),
        )

        localization_payload = json.loads(response.text)

        transformed_data: Dict[str, Dict[str, CampaignMessage]] = {}
        for item in localization_payload:
            region = item["region"]
            lang = item["language"]
            msg = CampaignMessage(tag=item["tag"], body=item["body"])
            transformed_data.setdefault(region, {})[lang] = msg

        return transformed_data
