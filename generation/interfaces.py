"""Abstract interfaces for image generation and copy localization."""

from abc import ABC, abstractmethod
from pathlib import Path

from models import Brief, Product

# Use abstract classes to keep the calling contract consistent, no matter which LLM backs each category (image gen vs. copy gen)
# Keeps provider swaps possible down the line, and
# Allows testing against a stubbed endpoint.


class ImageGenService(ABC):
    @abstractmethod
    def generate_product_image(self, brief: Brief, product: Product, output_dir: Path, layout_id: str) -> Path:
        """Generate a hero image for the product, matching the brief's tone and campaign message."""
        pass


class CopyGenService(ABC):
    @abstractmethod
    def localize(self, brief: Brief):
        """Localize the brief's campaign copy into each target market's language(s), preserving tone."""
        pass
