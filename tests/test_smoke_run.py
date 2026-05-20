import json

from slideforge.smoke_run import SmokeDeckInput, write_smoke_run


def test_write_smoke_run_creates_html_manifest_and_source_deck(tmp_path):
    run_dir = write_smoke_run(
        root=tmp_path,
        run_id="smoke-001",
        deck=SmokeDeckInput(
            title="폐쇄망 LLM 전략",
            slides=[
                {
                    "slide_id": "s1",
                    "title": "폐쇄망 LLM 전략",
                    "subtitle": "의사결정용 요약",
                    "bullets": ["GPU 추론 계층", "RAG 서비스 계층"],
                    "archetype": "cover",
                },
                {
                    "slide_id": "s2",
                    "title": "90일 실행계획",
                    "bullets": ["PoC", "Pilot", "Scale"],
                    "archetype": "timeline",
                },
            ],
        ),
    )

    assert (run_dir / "deck.json").exists()
    assert (run_dir / "deck.html").exists()
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "evidence-index.md").exists()
    assert (run_dir / "browser-regression-plan.json").exists()

    html = (run_dir / "deck.html").read_text(encoding="utf-8")
    assert "function showSlide" in html
    assert "폐쇄망 LLM 전략" in html

    manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["run_id"] == "smoke-001"
    assert manifest["pipeline"] == "compose-html-smoke"
    assert {item["name"] for item in manifest["artifacts"]} == {"source_deck", "html_deck", "browser_regression_plan"}
    assert manifest["checks"]["html_contains_presentation_shell"] == "pass"
    assert manifest["checks"]["browser_regression_plan_written"] == "pass"

    regression = json.loads((run_dir / "browser-regression-plan.json").read_text(encoding="utf-8"))
    assert regression["deck_path"] == "deck.html"
    assert regression["expected_slide_count"] == 2
    assert regression["expected_slide_ids"] == ["s1", "s2"]
    assert regression["expected_archetypes"] == ["cover", "timeline"]
    assert regression["generated_report_path"] == "browser-regression-plan.json"
