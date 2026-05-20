from __future__ import annotations

from dataclasses import asdict
import json
from pathlib import Path
import re
from typing import Any

from slideforge.archetype_mapper import ContentSection, map_sections_to_archetypes
from slideforge.design_spec import DesignSpec
from slideforge.schemas import HtmlDeck, HtmlSlide, MetricRow, TimelineStep

DEFAULT_ARCHETYPE = "text_explainer"
_INTENT_ARCHETYPE_ALIASES = {
    "architecture": "architecture_visual",
    "comparison": "two_column_comparison",
    "explainer": "text_explainer",
    "kpi": "kpi_table",
    "metrics": "kpi_table",
    "policy": "text_explainer",
    "table": "kpi_table",
    "timeline": "timeline",
    "visual": "visual_break",
}


def prepare_deck(
    *,
    title: str,
    sections: list[dict[str, Any]] | list[ContentSection],
    design_spec: DesignSpec | None = None,
    default_archetype: str = DEFAULT_ARCHETYPE,
) -> dict[str, Any]:
    """Build an HtmlDeck-compatible dict from operator-supplied content sections.

    This is deterministic and extractive: it validates and carries supplied text into
    slides without synthesizing additional claims.
    """
    normalized_title = _normalize_required_text(title, "deck title")
    normalized_default = _normalize_required_text(default_archetype, "default archetype")
    content_sections = _load_sections(sections)
    archetypes = _archetypes_for_sections(content_sections, design_spec, normalized_default)
    slides = [
        _section_to_slide(section, archetypes[section.id])
        for section in content_sections
    ]
    deck = HtmlDeck(title=normalized_title, slides=slides)
    return {"title": deck.title, "slides": [_slide_to_dict(slide) for slide in deck.slides]}


def write_prepared_deck(
    *,
    title: str,
    sections: list[dict[str, Any]] | list[ContentSection],
    output: str | Path,
    design_spec: DesignSpec | None = None,
    default_archetype: str = DEFAULT_ARCHETYPE,
) -> Path:
    deck = prepare_deck(
        title=title,
        sections=sections,
        design_spec=design_spec,
        default_archetype=default_archetype,
    )
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(deck, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def load_sections_json(path: str | Path) -> list[dict[str, Any]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("sections JSON must be a list")
    if not all(isinstance(item, dict) for item in raw):
        raise ValueError("sections JSON must contain objects")
    return raw


def _load_sections(sections: list[dict[str, Any]] | list[ContentSection]) -> list[ContentSection]:
    if not isinstance(sections, list):
        raise ValueError("sections must be a list")
    if not sections:
        raise ValueError("sections must include at least one section")

    loaded: list[ContentSection] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(sections):
        raw = asdict(item) if isinstance(item, ContentSection) else item
        if not isinstance(raw, dict):
            raise ValueError(f"section {index} must be an object")
        section_id = _normalize_required_text(raw.get("id"), f"section {index} id")
        if section_id in seen_ids:
            raise ValueError(f"duplicate section id: {section_id}")
        seen_ids.add(section_id)
        heading = _normalize_required_text(raw.get("heading"), f"section {section_id} heading")
        intent = _normalize_required_text(raw.get("intent"), f"section {section_id} intent").lower()
        bullets_raw = raw.get("bullets", [])
        if bullets_raw is None:
            bullets_raw = []
        if not isinstance(bullets_raw, list):
            raise ValueError(f"section {section_id} bullets must be a list")
        bullets: list[str] = []
        for bullet_index, bullet in enumerate(bullets_raw):
            if not isinstance(bullet, str):
                raise ValueError(f"section {section_id} bullet {bullet_index} must be a string")
            normalized = _normalize_text(bullet)
            if normalized:
                bullets.append(normalized)
        loaded.append(ContentSection(id=section_id, heading=heading, intent=intent, bullets=bullets))
    return loaded


def _archetypes_for_sections(
    sections: list[ContentSection],
    design_spec: DesignSpec | None,
    default_archetype: str,
) -> dict[str, str]:
    if design_spec is not None and design_spec.slide_archetypes:
        names = [archetype.name for archetype in design_spec.slide_archetypes]
        mappings = map_sections_to_archetypes(sections, names)
        return {mapping.section_id: mapping.archetype_name for mapping in mappings}
    return {
        section.id: _INTENT_ARCHETYPE_ALIASES.get(section.intent, default_archetype)
        for section in sections
    }


def _section_to_slide(section: ContentSection, archetype: str) -> HtmlSlide:
    timeline_steps: list[TimelineStep] = []
    metric_rows: list[MetricRow] = []
    if section.intent == "timeline" or archetype == "timeline":
        timeline_steps = [_timeline_step_from_bullet(bullet) for bullet in section.bullets]
    if section.intent in {"kpi", "metrics", "table"} or archetype == "kpi_table":
        metric_rows = [row for bullet in section.bullets if (row := _metric_row_from_bullet(bullet)) is not None]
    return HtmlSlide(
        slide_id=section.id,
        title=section.heading,
        subtitle=f"Intent: {section.intent}",
        bullets=section.bullets,
        archetype=archetype,
        timeline_steps=timeline_steps,
        metric_rows=metric_rows,
    )


def _timeline_step_from_bullet(bullet: str) -> TimelineStep:
    label, detail = _split_label_value(bullet)
    return TimelineStep(label=label, detail=detail)


def _metric_row_from_bullet(bullet: str) -> MetricRow | None:
    label, value = _split_label_value(bullet)
    if not value:
        return None
    return MetricRow(label=label, value=value)


def _split_label_value(text: str) -> tuple[str, str]:
    for pattern in (r"\s*[:：]\s*", r"\s+[–—-]\s+"):
        parts = re.split(pattern, text, maxsplit=1)
        if len(parts) == 2 and parts[0].strip() and parts[1].strip():
            return parts[0].strip(), parts[1].strip()
    return text, ""


def _slide_to_dict(slide: HtmlSlide) -> dict[str, Any]:
    payload = asdict(slide)
    return {key: value for key, value in payload.items() if value not in (None, [], "")}


def _normalize_required_text(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    normalized = _normalize_text(value)
    if not normalized:
        raise ValueError(f"{label} is required")
    return normalized


def _normalize_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()
