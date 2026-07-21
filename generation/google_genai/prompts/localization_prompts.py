"""Prompt templates for localizing campaign copy per market."""

from .common import _hydrate

LOCALIZE_INTRO = "You are an expert global copywriter and translator."
LOCALIZE_TASK_TEMPLATE = "Translate this marketing copy: tag:{tag} and body: {body} for the following markets:"
LOCALIZE_MARKET_LINE_TEMPLATE = "Region: {region}, Languages: {languages}"
LOCALIZE_SYSTEM_INSTRUCTION_INTRO = "Maintain the exact emotional resonance, intent, and tone of the original copy"
LOCALIZE_TONE_LINE_TEMPLATE = "Target Tone: {tone}"


def localize_prompt(tag: str, body: str, markets: list[tuple[str, str]]) -> str:
    lines = [LOCALIZE_INTRO, _hydrate(LOCALIZE_TASK_TEMPLATE, tag=tag, body=body)]
    lines += [_hydrate(LOCALIZE_MARKET_LINE_TEMPLATE, region=region, languages=languages) for region, languages in markets]
    return "\n".join(lines)


def localize_system_instruction(tone: str) -> str:
    return "\n".join([LOCALIZE_SYSTEM_INSTRUCTION_INTRO, _hydrate(LOCALIZE_TONE_LINE_TEMPLATE, tone=tone)])
