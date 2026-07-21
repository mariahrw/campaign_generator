"""Prompt template for the product-free background scene."""

from .common import _hydrate, _with_constraints

BACKGROUND_SCENE_TEMPLATE = (
    "You are a senior art director creating a background scene for a paid social ad "
    "campaign hero shot. A product will be composited on top of this afterward - you "
    "are describing ONLY the backdrop/environment. "
    "Product category: {category}. "
    "Tone and Vibe: {tone}. "
    "SHOT TYPE: {shot_type} "
    "{scene_setting_section}"
    "{camera_framing} "
    "Reserve visually simple, relatively uncluttered negative space in the frame region "
    "matching that framing (avoid tall furniture, people, or busy focal objects there) "
    "for a product to be composited into afterward - though color/light/texture may "
    "extend through it naturally. "
    "Any staged props must be generic and period-appropriate, never an attempt to replicate "
    "the specific product's exact contents or appearance (e.g. don't render a competing "
    "{category} product) - the real product is composited in separately at full accuracy, "
    "so this scene's only job is atmosphere. Ordinary props unrelated to {category}, "
    "consistent with the staged scene described above, are fine and encouraged."
)
SCENE_SETTING_SECTION_TEMPLATE = "STAGED SCENE: {scene_setting} "
BACKGROUND_SCENE_CONSTRAINTS = [
    "Do not include any branded packaging, boxes, bottles, or containers - especially do "
    "not invent a competing or generic product package or logo of any kind.",
    "No jar, tin, bowl, or container may contain or resemble {category} - keep them empty, "
    "or holding items from a clearly different category. There must never be any other "
    "product anywhere in the scene, branded or not, that could read as competing with or "
    "duplicating the composited product - it is the only {category} product visible in "
    "this image.",
    "Contain ZERO text, words, letters, numbers, or typography anywhere in the image - no "
    "taglines, no signage, no captions.",
]


def background_scene_prompt(category: str, tone: str, shot_type: str, scene_setting: str, camera_framing: str) -> str:
    scene_setting_section = _hydrate(SCENE_SETTING_SECTION_TEMPLATE, scene_setting=scene_setting) if scene_setting else ""
    return _with_constraints(
        BACKGROUND_SCENE_TEMPLATE, BACKGROUND_SCENE_CONSTRAINTS,
        category=category, tone=tone, shot_type=shot_type,
        scene_setting_section=scene_setting_section, camera_framing=camera_framing,
    )
