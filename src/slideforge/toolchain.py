from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProductionToolchain:
    """Fixed production toolchain for high-fidelity slide generation."""

    design_planning: str = "JARVIS + hermes-slide-director learnings"
    asset_forge: str = "ComfyUI"
    primary_composer: str = "codex-guizang-html"
    pptx_delivery: str = "codex-presentation-pptx"


def default_toolchain() -> ProductionToolchain:
    return ProductionToolchain()
