from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite


__all__ = [
    "VisualChip",
    "AssetPlaceholder",
    "TimelineStep",
    "MetricRow",
    "ChartDatum",
    "ComparisonColumn",
    "ComparisonRow",
    "HtmlSlide",
    "HtmlDeck",
]


@dataclass(frozen=True)
class VisualChip:
    label: str
    emphasis: str = "neutral"

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("visual chip label is required")


@dataclass(frozen=True)
class AssetPlaceholder:
    slot_id: str
    asset_type: str
    prompt: str
    provider: str = "comfyui"
    status: str = "placeholder-only"
    output_hint: str | None = None
    generated_path: str | None = None

    def __post_init__(self) -> None:
        if not self.slot_id.strip():
            raise ValueError("asset placeholder slot_id is required")
        if not self.asset_type.strip():
            raise ValueError("asset placeholder asset_type is required")
        if not self.prompt.strip():
            raise ValueError("asset placeholder prompt is required")
        if self.provider != "comfyui":
            raise ValueError("asset placeholders currently support only comfyui provider")
        if self.status != "placeholder-only":
            raise ValueError("asset placeholders must remain placeholder-only")
        if self.generated_path:
            raise ValueError("asset placeholders are placeholder-only; use output_hint, not generated_path")


@dataclass(frozen=True)
class TimelineStep:
    label: str
    detail: str = ""

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("timeline step label is required")


@dataclass(frozen=True)
class MetricRow:
    label: str
    value: str

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("metric row label is required")
        if not self.value.strip():
            raise ValueError("metric row value is required")


@dataclass(frozen=True)
class ChartDatum:
    label: str
    value: float
    note: str = ""
    color: str = ""

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("chart datum label is required")
        if not isinstance(self.value, int | float) or not isfinite(self.value):
            raise ValueError("chart datum value must be a finite number")


@dataclass(frozen=True)
class ComparisonColumn:
    label: str
    note: str = ""

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("comparison column label is required")


@dataclass(frozen=True)
class ComparisonRow:
    label: str
    values: list[str]
    note: str = ""

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("comparison row label is required")


@dataclass(frozen=True)
class HtmlSlide:
    slide_id: str
    title: str
    subtitle: str = ""
    bullets: list[str] = field(default_factory=list)
    archetype: str = "text_explainer"
    asset_path: str | None = None
    visual_chips: list[VisualChip] = field(default_factory=list)
    asset_placeholders: list[AssetPlaceholder] = field(default_factory=list)
    timeline_steps: list[TimelineStep] = field(default_factory=list)
    metric_rows: list[MetricRow] = field(default_factory=list)
    chart_data: list[ChartDatum] = field(default_factory=list)
    comparison_columns: list[ComparisonColumn] = field(default_factory=list)
    comparison_rows: list[ComparisonRow] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.slide_id.strip():
            raise ValueError("slide_id is required")
        if not self.title.strip():
            raise ValueError("slide title is required")


@dataclass(frozen=True)
class HtmlDeck:
    title: str
    slides: list[HtmlSlide]

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("deck title is required")
        if not self.slides:
            raise ValueError("HTML deck requires at least one slide")
