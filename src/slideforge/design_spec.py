from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re

_HEX_RE = re.compile(r"^#[0-9A-Fa-f]{6}$")


@dataclass(frozen=True)
class ColorToken:
    name: str
    hex: str
    role: str

    def __post_init__(self) -> None:
        if not _HEX_RE.match(self.hex):
            raise ValueError(f"invalid hex color for {self.name!r}: {self.hex!r}")


@dataclass(frozen=True)
class TypographyToken:
    name: str
    font_family: str
    size_px: int
    weight: int | str

    def __post_init__(self) -> None:
        if self.size_px <= 0:
            raise ValueError("typography size_px must be positive")


@dataclass(frozen=True)
class SlideArchetype:
    name: str
    purpose: str
    required_elements: list[str] = field(default_factory=list)
    forbidden_elements: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("slide archetype name is required")
        if not self.required_elements:
            raise ValueError("slide archetype requires at least one required element")


@dataclass(frozen=True)
class DesignSpec:
    name: str
    source_refs: list[str] = field(default_factory=list)
    colors: list[ColorToken] = field(default_factory=list)
    typography: list[TypographyToken] = field(default_factory=list)
    slide_archetypes: list[SlideArchetype] = field(default_factory=list)
    background_layers: list[str] = field(default_factory=list)
    graphic_motifs: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("design spec name is required")

    def to_dict(self) -> dict:
        return asdict(self)
