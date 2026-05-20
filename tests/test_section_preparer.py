import json

import pytest

from slideforge.cli import main
from slideforge.section_preparer import prepare_sections_from_text


def test_prepare_sections_extracts_korean_english_markdown_outline():
    sections = prepare_sections_from_text(
        """
# 폐쇄망 AI 운영 전략
- 내부 데이터 보호
- Local evidence only

## KPI Metrics Table
* Availability: 99.9%
* Latency: 120ms

Architecture Flow
• Ingest source markdown
• Prepare deck JSON
"""
    )

    assert sections == [
        {
            "id": "폐쇄망-ai-운영-전략",
            "heading": "폐쇄망 AI 운영 전략",
            "intent": "policy",
            "bullets": ["내부 데이터 보호", "Local evidence only"],
        },
        {
            "id": "kpi-metrics-table",
            "heading": "KPI Metrics Table",
            "intent": "table",
            "bullets": ["Availability: 99.9%", "Latency: 120ms"],
        },
        {
            "id": "architecture-flow",
            "heading": "Architecture Flow",
            "intent": "architecture",
            "bullets": ["Ingest source markdown", "Prepare deck JSON"],
        },
    ]


def test_prepare_sections_infers_timeline_comparison_and_default_intent():
    sections = prepare_sections_from_text(
        """
Schedule Roadmap
- Phase 1: Discovery

비교 기준
- On-prem vs cloud

Unknown Topic
- Conservative extraction
""",
        default_intent="explainer",
    )

    assert [section["intent"] for section in sections] == ["timeline", "comparison", "explainer"]


def test_prepare_sections_avoids_substring_intent_false_positives():
    sections = prepare_sections_from_text(
        """
사업 목표
- 승인된 입력만 사용

성과 목표
- 현장 검증

Geometric Ecosystem
- Avoid substring keyword matches
""",
        default_intent="policy",
    )

    assert [section["intent"] for section in sections] == ["policy", "policy", "policy"]


def test_prepare_sections_supports_explicit_korean_table_phrases():
    sections = prepare_sections_from_text(
        """
운영 지표
- 가동률: 99.9%

KPI 표
- 응답시간: 120ms

표 형식 요약
- 승인 항목: 완료
""",
        default_intent="policy",
    )

    assert [section["intent"] for section in sections] == ["table", "table", "table"]


def test_prepare_sections_handles_duplicate_and_unsafe_heading_ids_safely():
    sections = prepare_sections_from_text(
        """
## KPI Table
- A: 1

## KPI Table
- B: 2

## !!!
- unsafe id fallback
"""
    )

    assert [section["id"] for section in sections] == ["kpi-table", "kpi-table-2", "section-3"]


def test_prepare_sections_cli_writes_sections_prepare_deck_and_run_local_can_consume(tmp_path):
    source_path = tmp_path / "source.md"
    sections_path = tmp_path / "sections.json"
    deck_path = tmp_path / "deck.json"
    runs_dir = tmp_path / "runs"
    source_path.write_text(
        """
# 운영 요약
- 승인된 입력만 사용
- 로컬 증거 산출

## Timeline Schedule
- 1단계: 요구사항 확정
- 2단계: 파일럿 검증
""",
        encoding="utf-8",
    )

    exit_code = main([
        "prepare-sections",
        "--source",
        str(source_path),
        "--output",
        str(sections_path),
    ])
    assert exit_code == 0
    sections = json.loads(sections_path.read_text(encoding="utf-8"))
    assert sections[0]["heading"] == "운영 요약"
    assert sections[1]["intent"] == "timeline"

    deck_exit_code = main([
        "prepare-deck",
        "--title",
        "섹션 준비 스모크",
        "--sections",
        str(sections_path),
        "--output",
        str(deck_path),
    ])
    assert deck_exit_code == 0

    run_exit_code = main([
        "run-local",
        "--deck",
        str(deck_path),
        "--runs-dir",
        str(runs_dir),
        "--run-id",
        "prepare-sections-cli-smoke",
    ])
    assert run_exit_code == 0
    assert (runs_dir / "prepare-sections-cli-smoke" / "deck.json").exists()
    assert (runs_dir / "prepare-sections-cli-smoke" / "run-summary.json").exists()


def test_prepare_sections_invalid_empty_source_behavior(tmp_path):
    with pytest.raises(ValueError, match="at least one heading or bullet"):
        prepare_sections_from_text("\n  \n")

    source_path = tmp_path / "empty.md"
    output_path = tmp_path / "sections.json"
    source_path.write_text("\n", encoding="utf-8")

    with pytest.raises(ValueError, match="at least one heading or bullet"):
        main([
            "prepare-sections",
            "--source",
            str(source_path),
            "--output",
            str(output_path),
        ])

    assert not output_path.exists()


def test_prepare_sections_rejects_unknown_default_intent():
    with pytest.raises(ValueError, match="default intent"):
        prepare_sections_from_text("# A\n- B", default_intent="unsupported")
