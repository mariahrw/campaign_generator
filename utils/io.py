"""Brief loading and output directory/versioning helpers."""

import os
from pathlib import Path

from models import Brief


def process_product_json(file_path: str) -> Brief:
    """Loads a JSON file from a local path and validates it into the Brief Pydantic model."""
    with open(file_path, "r", encoding="utf-8") as f:
        raw_json = f.read()
    return Brief.model_validate_json(raw_json)


def create_dir(parent_path: Path, name: str) -> Path:
    """Sanitizes a name string and builds/creates a directory under the parent path."""
    sanitized_name = name.strip().replace(" ", "_")
    target_dir = parent_path / sanitized_name
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir


def create_versioned_dir(parent_path: Path, name: str) -> Path:
    """Creates parent_path/name/vN, N one higher than any existing vN sibling."""
    base_dir = create_dir(parent_path, name)
    existing_versions = [
        int(p.name[1:]) for p in base_dir.iterdir()
        if p.is_dir() and p.name.startswith('v') and p.name[1:].isdigit()
    ]
    version_dir = base_dir / f"v{max(existing_versions, default=0) + 1}"
    version_dir.mkdir(parents=True, exist_ok=True)
    return version_dir


def get_product_shot_path(product_folder_name: str) -> str | None:
    """Finds product.png in the root directory."""
    potential_path = os.path.join(product_folder_name, "product.png")
    return potential_path if os.path.isfile(potential_path) else None
