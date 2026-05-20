import json

import pytest

from slideforge.cli import main
from slideforge.deck_preparer import prepare_deck
from slideforge.design_spec import DesignSpec, SlideArchetype


def test_prepare_deck_from_korean_sections_without_design_spec():
    deck = prepare_deck(
        title="폐쇄망 AI 운영 전략",
        sections=[
            {
                "id": "intro",
                "heading": "핵심 방향",
                "intent": "explainer",
                "bullets": ["내부 데이터 보호", "운영 비용 예측 가능성"],
            },
            {
                "id": "milestones",
                "heading": "도입 일정",
                "intent": "timeline",
                "bullets": ["1단계: 요구사항 확정", "2단계: 파일럿 검증"],
            },
        ],
    )

    assert deck["title"] == "폐쇄망 AI 운영 전략"
    assert deck["slides"][0] == {
        "slide_id": "intro",
        "title": "핵심 방향",
        "subtitle": "Intent: explainer",
        "bullets": ["내부 데이터 보호", "운영 비용 예측 가능성"],
        "archetype": "text_explainer",
    }
    assert deck["slides"][1]["archetype"] == "timeline"
    assert deck["slides"][1]["timeline_steps"] == [
        {"label": "1단계", "detail": "요구사항 확정"},
        {"label": "2단계", "detail": "파일럿 검증"},
    ]


def test_prepare_deck_uses_design_spec_archetype_alias_mapping():
    spec = DesignSpec(
        name="운영 템플릿",
        slide_archetypes=[
            SlideArchetype(name="cover", purpose="표지", required_elements=["title"]),
            SlideArchetype(name="kpi_table", purpose="지표", required_elements=["rows"]),
            SlideArchetype(name="text_explainer", purpose="설명", required_elements=["bullets"]),
        ],
    )

    deck = prepare_deck(
        title="KPI 보고",
        design_spec=spec,
        sections=[
            {
                "id": "kpi",
                "heading": "주요 지표",
                "intent": "table",
                "bullets": ["가동률: 99.9%", "응답시간: 120ms"],
            }
        ],
    )

    slide = deck["slides"][0]
    assert slide["archetype"] == "kpi_table"
    assert slide["metric_rows"] == [
        {"label": "가동률", "value": "99.9%"},
        {"label": "응답시간", "value": "120ms"},
    ]


def test_prepare_deck_rejects_duplicate_ids_and_invalid_bullets():
    with pytest.raises(ValueError, match="duplicate section id"):
        prepare_deck(
            title="중복 검증",
            sections=[
                {"id": "same", "heading": "A", "intent": "policy", "bullets": []},
                {"id": "same", "heading": "B", "intent": "policy", "bullets": []},
            ],
        )

    with pytest.raises(ValueError, match="bullets must be a list"):
        prepare_deck(
            title="불릿 검증",
            sections=[{"id": "s1", "heading": "A", "intent": "policy", "bullets": "not-a-list"}],
        )

    with pytest.raises(ValueError, match="bullet 0 must be a string"):
        prepare_deck(
            title="불릿 검증",
            sections=[{"id": "s1", "heading": "A", "intent": "policy", "bullets": [123]}],
        )


def test_prepare_deck_cli_writes_deck_run_local_can_consume(tmp_path):
    sections_path = tmp_path / "sections.json"
    deck_path = tmp_path / "deck.json"
    runs_dir = tmp_path / "runs"
    sections_path.write_text(
        json.dumps(
            [
                {
                    "id": "s1",
                    "heading": "운영 요약",
                    "intent": "policy",
                    "bullets": ["승인된 입력만 사용", "로컬 증거 산출"],
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    exit_code = main([
        "prepare-deck",
        "--title",
        "운영 핸드오프",
        "--sections",
        str(sections_path),
        "--output",
        str(deck_path),
    ])
    assert exit_code == 0

    run_exit_code = main([
        "run-local",
        "--deck",
        str(deck_path),
        "--runs-dir",
        str(runs_dir),
        "--run-id",
        "prepare-deck-cli-smoke",
    ])

    assert run_exit_code == 0
    assert (runs_dir / "prepare-deck-cli-smoke" / "deck.json").exists()
    assert (runs_dir / "prepare-deck-cli-smoke" / "run-summary.json").exists()


def test_prepare_deck_cli_invalid_payload_fails_before_output_created(tmp_path):
    sections_path = tmp_path / "sections.json"
    output_path = tmp_path / "deck.json"
    sections_path.write_text(
        json.dumps([{"id": "s1", "heading": " ", "intent": "policy", "bullets": ["ok"]}]),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="heading"):
        main([
            "prepare-deck",
            "--title",
            "Invalid",
            "--sections",
            str(sections_path),
            "--output",
            str(output_path),
        ])

    assert not output_path.exists()
