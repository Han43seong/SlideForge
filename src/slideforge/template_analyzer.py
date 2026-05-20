from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from slideforge.design_spec import ColorToken, DesignSpec, SlideArchetype, TypographyToken


@dataclass(frozen=True)
class TemplateObservation:
    source_ref: str
    slide_role: str
    colors: dict[str, str] = field(default_factory=dict)
    typography: dict[str, dict[str, Any]] = field(default_factory=dict)
    background_layers: list[str] = field(default_factory=list)
    graphic_motifs: list[str] = field(default_factory=list)
    layout_notes: list[str] = field(default_factory=list)


def _append_unique(items: list, item) -> None:
    if item not in items:
        items.append(item)


def build_design_spec_from_observations(name: str, observations: list[TemplateObservation]) -> DesignSpec:
    source_refs: list[str] = []
    colors: list[ColorToken] = []
    typography: list[TypographyToken] = []
    slide_archetypes: list[SlideArchetype] = []
    background_layers: list[str] = []
    graphic_motifs: list[str] = []
    color_names: set[str] = set()
    typography_names: set[str] = set()
    archetype_names: set[str] = set()

    for observation in observations:
        _append_unique(source_refs, observation.source_ref)
        for color_name, hex_value in observation.colors.items():
            if color_name not in color_names:
                colors.append(ColorToken(name=color_name, hex=hex_value, role="observed"))
                color_names.add(color_name)
        for token_name, token in observation.typography.items():
            if token_name not in typography_names:
                typography.append(
                    TypographyToken(
                        name=token_name,
                        font_family=token["font_family"],
                        size_px=int(token["size_px"]),
                        weight=token["weight"],
                    )
                )
                typography_names.add(token_name)
        if observation.slide_role not in archetype_names:
            required = list(observation.layout_notes or [f"{observation.slide_role} layout"])
            required.extend(observation.graphic_motifs)
            slide_archetypes.append(
                SlideArchetype(
                    name=observation.slide_role,
                    purpose=f"Observed {observation.slide_role} slide pattern",
                    required_elements=required,
                )
            )
            archetype_names.add(observation.slide_role)
        for layer in observation.background_layers:
            _append_unique(background_layers, layer)
        for motif in observation.graphic_motifs:
            _append_unique(graphic_motifs, motif)

    return DesignSpec(
        name=name,
        source_refs=source_refs,
        colors=colors,
        typography=typography,
        slide_archetypes=slide_archetypes,
        background_layers=background_layers,
        graphic_motifs=graphic_motifs,
    )
