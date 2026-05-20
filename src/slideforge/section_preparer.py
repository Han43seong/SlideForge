from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any

SUPPORTED_INTENTS = {
    "architecture",
    "comparison",
    "explainer",
    "kpi",
    "metrics",
    "policy",
    "table",
    "timeline",
    "visual",
}

_INTENT_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("timeline", ("timeline", "schedule", "roadmap", "milestone", "일정", "로드맵", "단계", "마일스톤")),
    ("table", ("kpi", "metric", "metrics", "table", "scorecard", "지표", "테이블", "표 형식", "kpi 표")),
    ("comparison", ("comparison", "compare", "versus", " vs ", "vs.", "비교", "대비")),
    ("architecture", ("architecture", "system", "flow", "pipeline", "topology", "아키텍처", "구조", "시스템", "흐름")),
    ("visual", ("visual", "image", "diagram", "illustration", "screenshot", "비주얼", "이미지", "그림", "다이어그램")),
)

_BULLET_RE = re.compile(r"^[-*•]\s+(.+)$")
_MARKDOWN_HEADING_RE = re.compile(r"^#{1,2}\s+(.+?)\s*#*\s*$")
_UNSAFE_ID_CHARS_RE = re.compile(r"[^0-9A-Za-z가-힣]+")


@dataclass
class _DraftSection:
    heading: str
    bullets: list[str] = field(default_factory=list)


def prepare_sections_from_text(text: str, *, default_intent: str = "policy") -> list[dict[str, Any]]:
    """Extract local Markdown-like source material into prepare-deck sections.

    The parser is deterministic and extractive: Markdown ``#``/``##`` headings and
    non-empty non-bullet title lines start sections, while ``-``, ``*``, and ``•``
    bullet lines become section bullets. Intent inference is a documented keyword
    alias pass over the extracted heading and bullets; otherwise ``default_intent``
    is used. No unsupported facts are synthesized.
    """
    if not isinstance(text, str):
        raise ValueError("source text must be a string")
    fallback_intent = _normalize_intent(default_intent, "default intent")
    drafts = _parse_outline(text)
    if not drafts:
        raise ValueError("source must include at least one heading or bullet")

    used_ids: set[str] = set()
    sections: list[dict[str, Any]] = []
    for index, draft in enumerate(drafts, start=1):
        heading = _normalize_required_text(draft.heading, f"section {index} heading")
        bullets = [
            _normalize_required_text(bullet, f"section {index} bullet {bullet_index}")
            for bullet_index, bullet in enumerate(draft.bullets)
        ]
        section_id = _unique_id(_slugify_heading(heading, index), used_ids)
        sections.append(
            {
                "id": section_id,
                "heading": heading,
                "intent": infer_intent(heading=heading, bullets=bullets, default_intent=fallback_intent),
                "bullets": bullets,
            }
        )
    return sections


def prepare_sections_from_file(path: str | Path, *, default_intent: str = "policy") -> list[dict[str, Any]]:
    source = Path(path)
    return prepare_sections_from_text(source.read_text(encoding="utf-8"), default_intent=default_intent)


def write_prepared_sections(*, source: str | Path, output: str | Path, default_intent: str = "policy") -> Path:
    sections = prepare_sections_from_file(source, default_intent=default_intent)
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(sections, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output_path


def infer_intent(*, heading: str, bullets: list[str] | None = None, default_intent: str = "policy") -> str:
    fallback_intent = _normalize_intent(default_intent, "default intent")
    parts = [heading]
    if bullets:
        parts.extend(bullets)
    haystack = f" {' '.join(parts)} ".lower()
    for intent, keywords in _INTENT_KEYWORDS:
        if any(_keyword_matches(haystack, keyword) for keyword in keywords):
            return intent
    return fallback_intent


def _keyword_matches(haystack: str, keyword: str) -> bool:
    lowered = keyword.lower()
    if re.fullmatch(r"[a-z0-9. ]+", lowered):
        return re.search(rf"(?<![a-z0-9]){re.escape(lowered)}(?![a-z0-9])", haystack) is not None
    return lowered in haystack


def _parse_outline(text: str) -> list[_DraftSection]:
    sections: list[_DraftSection] = []
    current: _DraftSection | None = None
    pending_blank = True

    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        if not line:
            pending_blank = True
            continue

        bullet_match = _BULLET_RE.match(line)
        if bullet_match:
            if current is None:
                raise ValueError("source bullet appears before the first heading or title line")
            bullet = _normalize_text(bullet_match.group(1))
            if bullet:
                current.bullets.append(bullet)
            pending_blank = False
            continue

        heading_match = _MARKDOWN_HEADING_RE.match(line)
        heading = _normalize_text(heading_match.group(1) if heading_match else line)
        if not heading:
            pending_blank = True
            continue

        # Practical operator format: Markdown headings always start a section;
        # plain title lines start sections when they are the first content line,
        # after a blank, or after bullets. Consecutive non-blank prose under a
        # heading is retained as extractive bullet text instead of being invented.
        if heading_match or current is None or pending_blank or current.bullets:
            current = _DraftSection(heading=heading)
            sections.append(current)
        else:
            current.bullets.append(heading)
        pending_blank = False

    return [section for section in sections if section.heading.strip() or section.bullets]


def _slugify_heading(heading: str, index: int) -> str:
    lowered = heading.lower()
    slug = _UNSAFE_ID_CHARS_RE.sub("-", lowered).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    return slug or f"section-{index}"


def _unique_id(base: str, used_ids: set[str]) -> str:
    candidate = base
    suffix = 2
    while candidate in used_ids:
        candidate = f"{base}-{suffix}"
        suffix += 1
    used_ids.add(candidate)
    return candidate


def _normalize_intent(value: Any, label: str) -> str:
    intent = _normalize_required_text(value, label).lower()
    if intent not in SUPPORTED_INTENTS:
        raise ValueError(f"{label} must be one of: {', '.join(sorted(SUPPORTED_INTENTS))}")
    return intent


def _normalize_required_text(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} must be a string")
    normalized = _normalize_text(value)
    if not normalized:
        raise ValueError(f"{label} is required")
    return normalized


def _normalize_text(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n").strip()
