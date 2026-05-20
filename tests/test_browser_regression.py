import json

from slideforge.browser_regression import BrowserRegressionExpectation, write_browser_regression_plan
from slideforge.guizang_html_composer import HtmlDeck, HtmlSlide


def test_write_browser_regression_plan_records_browser_checkable_expectations(tmp_path):
    deck_path = tmp_path / "deck.html"
    deck_path.write_text("<!doctype html><title>deck</title>", encoding="utf-8")
    deck = HtmlDeck(
        title="폐쇄망 LLM 전략",
        slides=[
            HtmlSlide(slide_id="s1", title="폐쇄망 LLM 전략", archetype="cover"),
            HtmlSlide(slide_id="s2", title="90일 실행계획", archetype="timeline"),
        ],
    )

    plan_path = write_browser_regression_plan(deck=deck, deck_path=deck_path, output_dir=tmp_path)

    data = json.loads(plan_path.read_text(encoding="utf-8"))
    assert data["report_kind"] == "browser_regression_plan"
    assert data["capture_mode"] == "manual_or_external_browser"
    assert data["deck_path"] == "deck.html"
    assert data["expected_slide_count"] == 2
    assert data["expected_slide_ids"] == ["s1", "s2"]
    assert data["expected_archetypes"] == ["cover", "timeline"]
    assert data["generated_report_path"] == "browser-regression-plan.json"
    assert data["screenshot_capture"] == {
        "status": "not_captured",
        "reason": "No browser automation dependency is required or assumed by SlideForge.",
    }
    assert data["checks"][0] == {
        "name": "open_deck_in_browser",
        "expectation": "Browser can load deck.html without console-blocking asset dependencies.",
    }


def test_browser_regression_expectation_rejects_slide_mismatch():
    deck = HtmlDeck(title="deck", slides=[HtmlSlide(slide_id="s1", title="one")])
    expectation = BrowserRegressionExpectation.from_deck(deck=deck, deck_path="deck.html")

    try:
        expectation.with_expected_slide_count(2)
    except ValueError as exc:
        assert "expected slide count 2 does not match deck slide count 1" in str(exc)
    else:
        raise AssertionError("expected slide count mismatch to fail")
