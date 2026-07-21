"""Prompt templates for the GenAI pipeline, split by domain (background, localization)."""
from .background_prompt import background_scene_prompt
from .localization_prompts import localize_prompt, localize_system_instruction

__all__ = [
    "background_scene_prompt",
    "localize_prompt",
    "localize_system_instruction",
]
