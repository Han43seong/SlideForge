from __future__ import annotations

from slideforge.archetype_mapper import ArchetypeMapping
from slideforge.asset_brief import AssetBrief, AssetBriefSet
from slideforge.design_spec import DesignSpec

_VISUAL_TYPES = {
    "cover": "cover_background",
    "section_intro": "section_divider_background",
    "section_divider": "section_divider_background",
    "timeline": "visual_band",
    "architecture_visual": "visual_band",
    "visual_break": "visual_band",
}


def _asset_type_for(archetype_name: str) -> str:
    return _VISUAL_TYPES.get(archetype_name, "subtle_panel_background")


def _style_phrase(spec: DesignSpec) -> str:
    layers = ", ".join(spec.background_layers) if spec.background_layers else "dark presentation background"
    motifs = ", ".join(spec.graphic_motifs) if spec.graphic_motifs else "subtle cinematic depth"
    return f"{layers}, {motifs}"


def _prompt_for(asset_type: str, spec: DesignSpec) -> str:
    style = _style_phrase(spec)
    if asset_type == "cover_background":
        return f"text-free high-fidelity cover background, {style}, generous dark title-safe area, no text"
    if asset_type == "section_divider_background":
        return f"text-free cinematic section divider background, {style}, atmospheric depth, no text"
    if asset_type == "visual_band":
        return f"text-free wide visual band, {style}, low contrast center for overlays, no text"
    return f"text-free subtle dark translucent panel background, {style}, minimal detail for readable overlays, no text"


def generate_asset_briefs(spec: DesignSpec, mappings: list[ArchetypeMapping]) -> AssetBriefSet:
    briefs = []
    for mapping in mappings:
        asset_type = _asset_type_for(mapping.archetype_name)
        briefs.append(
            AssetBrief(
                slide_id=mapping.section_id,
                asset_type=asset_type,
                prompt=_prompt_for(asset_type, spec),
                negative_prompt="text, letters, numbers, labels, watermark, logo, UI screenshot",
                aspect_ratio="16:9",
                output_hint=f"generated-assets/{mapping.section_id}-{asset_type}.png",
            )
        )
    return AssetBriefSet(briefs=briefs)
