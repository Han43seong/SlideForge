from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ContentSection:
    id: str
    heading: str
    intent: str
    bullets: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ArchetypeMapping:
    section_id: str
    archetype_name: str
    content_summary: str


_INTENT_ALIASES = {
    "table": "kpi_table",
    "kpi": "kpi_table",
    "comparison": "two_column_comparison",
    "architecture": "architecture_visual",
    "visual": "visual_break",
    "policy": "text_explainer",
    "explainer": "text_explainer",
}


def _choose_archetype(intent: str, archetype_names: list[str]) -> str:
    if intent in archetype_names:
        return intent
    alias = _INTENT_ALIASES.get(intent)
    if alias and alias in archetype_names:
        return alias
    if "text_explainer" in archetype_names:
        return "text_explainer"
    if archetype_names:
        return archetype_names[0]
    raise ValueError("at least one archetype name is required")


def _summarize(section: ContentSection) -> str:
    if section.bullets:
        return f"{section.heading}: {' / '.join(section.bullets)}"
    return section.heading


def map_sections_to_archetypes(
    sections: list[ContentSection],
    archetype_names: list[str],
) -> list[ArchetypeMapping]:
    return [
        ArchetypeMapping(
            section_id=section.id,
            archetype_name=_choose_archetype(section.intent, archetype_names),
            content_summary=_summarize(section),
        )
        for section in sections
    ]
