"""Pydantic models for the campaign brief schema."""

from pydantic import BaseModel


class Brand(BaseModel):
    """Fonts and colors used to render copy onto the hero image."""

    # TODO: reconsider how this object is organized.
    primary_font: str
    secondary_font: str
    primary_color: str
    secondary_color: str
    copy_background_color: str = "#000000"
    copy_background_opacity: float = 0.0  # 0 = no rect behind copy (default), 1 = fully opaque


class Market(BaseModel):
    """A target region and the language(s) copy gets localized into for it."""

    target_region: str
    
    # TODO: validate against real region codes (e.g. via the langcodes library)
    IETF_codes: list[str]


class CampaignMessage(BaseModel):
    """A headline/body copy pair, in one language."""

    tag: str
    body: str


class Product(BaseModel):
    """A single product to generate hero images for, across its staged layouts."""

    id: str

    # TODO: add orientation notes to product names, to make this easier to parse downstream.
    name: str

    asset_dir: str  # must contain product.png (transparent cutout), or this product is skipped (no generated-packaging fallback)

    # TODO: needs more detail/constraints - a thin description let the LLM generate the product in a pantry and invent competitor assets.
    description: str

    category: str  # e.g. "cereal", "footwear" - keeps background-scene prompts generic
    layouts: list[str] = ["9:16"]  # ratios to generate
    shot_type: str = ()
    scene_setting: str = ""  # concrete background staging; empty omits the prompt line


class Brief(BaseModel):
    """The full campaign input: products, markets, tone, and brand to generate assets for."""

    id: str
    products: list[Product]
    target_markets: list[Market]
    target_audience: str
    campaign_message: CampaignMessage
    tone: list[str]
    brand: Brand
