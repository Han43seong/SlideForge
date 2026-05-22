from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AssetSpec:
    asset_id: str
    role: str
    target_slide: str
    visual_style: str
    palette: list[str] = field(default_factory=list)
    hard_constraints: list[str] = field(default_factory=list)
    output_guidance: list[str] = field(default_factory=list)
    allow_text: bool = False
    source_path: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def prompt_filename(self) -> str:
        return f"{self.asset_id}.md"


def load_asset_specs(asset_spec_dir: Path) -> list[AssetSpec]:
    """Load and normalize JSON visual asset specs from a directory."""
    if not asset_spec_dir.exists():
        raise FileNotFoundError(f"asset spec directory does not exist: {asset_spec_dir}")
    if not asset_spec_dir.is_dir():
        raise NotADirectoryError(f"asset spec path is not a directory: {asset_spec_dir}")

    specs: list[AssetSpec] = []
    for path in sorted(asset_spec_dir.glob("*.json")):
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ValueError(f"asset spec must be a JSON object: {path}")
        specs.append(normalize_asset_spec(raw, source_path=path))
    if not specs:
        raise ValueError(f"no JSON asset specs found in {asset_spec_dir}")
    return specs


def normalize_asset_spec(raw: dict[str, Any], *, source_path: Path | None = None) -> AssetSpec:
    asset_id = _first_text(raw, "asset_id", "id", "name", "slug")
    if not asset_id and source_path:
        asset_id = source_path.stem
    asset_id = _slug(asset_id)
    if not asset_id:
        raise ValueError(f"asset spec is missing asset_id/id/name: {source_path or '<memory>'}")

    role = _first_text(raw, "role", "asset_role", "visual_role", "type", default=asset_id.replace("-", " "))
    target_slide = _first_text(raw, "target_slide", "slide_id", "slide", "slide_title", default="unspecified slide")
    visual_style = _first_text(raw, "visual_style", "style", "design_style", "look", default="match the deck reference style")
    palette = _text_list(raw.get("palette") or raw.get("colors") or raw.get("color_palette"))
    hard_constraints = _text_list(raw.get("hard_constraints") or raw.get("constraints") or raw.get("negative_prompt"))
    output_guidance = _text_list(raw.get("output_guidance") or raw.get("output") or raw.get("delivery_guidance"))
    allow_text = bool(raw.get("allow_text") or raw.get("text_allowed"))

    return AssetSpec(
        asset_id=asset_id,
        role=role,
        target_slide=target_slide,
        visual_style=visual_style,
        palette=palette,
        hard_constraints=hard_constraints,
        output_guidance=output_guidance,
        allow_text=allow_text,
        source_path=str(source_path) if source_path else "",
        raw=dict(raw),
    )


def _first_text(raw: dict[str, Any], *keys: str, default: str = "") -> str:
    for key in keys:
        value = raw.get(key)
        if value is None:
            continue
        if isinstance(value, (str, int, float)):
            text = str(value).strip()
            if text:
                return text
        elif isinstance(value, dict):
            text = ", ".join(f"{k}: {v}" for k, v in value.items())
            if text.strip():
                return text
    return default


def _text_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in re.split(r"[\n;]+", value) if item.strip()]
    if isinstance(value, dict):
        return [f"{key}: {val}" for key, val in value.items()]
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()] if str(value).strip() else []


def _slug(value: str) -> str:
    text = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower()).strip("-._")
    return text
