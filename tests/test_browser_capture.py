import json

import pytest

from slideforge.browser_capture import (
    BrowserCaptureReport,
    SlideScreenshot,
    build_failed_capture_report,
    capture_html_deck_screenshots,
    write_browser_capture_report,
)


def test_browser_capture_report_records_real_playwright_contract(tmp_path):
    report = BrowserCaptureReport(
        deck_path="deck.html",
        output_dir=tmp_path.as_posix(),
        status="captured",
        slide_count_detected=2,
        screenshots=[
            SlideScreenshot(index=1, slide_id="s1", archetype="cover", path="slide-01.png"),
            SlideScreenshot(index=2, slide_id="s2", archetype="timeline", path="slide-02.png"),
        ],
        viewport={"width": 1280, "height": 720},
    )

    report_path = write_browser_capture_report(report, tmp_path)

    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert report_path.name == "browser-regression-report.json"
    assert data["report_kind"] == "browser_regression_report"
    assert data["capture_mode"] == "real_playwright_chromium"
    assert data["deck_path"] == "deck.html"
    assert data["output_dir"] == tmp_path.as_posix()
    assert data["screenshot_capture"] == {"status": "captured"}
    assert data["slide_count_detected"] == 2
    assert data["screenshots"] == [
        {"index": 1, "path": "slide-01.png", "id": "s1", "archetype": "cover"},
        {"index": 2, "path": "slide-02.png", "id": "s2", "archetype": "timeline"},
    ]
    assert data["viewport"] == {"width": 1280, "height": 720}
    assert data["browser_name"] == "chromium"
    assert data["console_errors"] == []
    assert data["generated_report_path"] == "browser-regression-report.json"


def test_failed_browser_capture_report_has_failed_status_and_reason(tmp_path):
    deck_path = tmp_path / "deck.html"
    deck_path.write_text("<!doctype html><title>deck</title>", encoding="utf-8")

    report = build_failed_capture_report(deck_path, tmp_path, "browser unavailable")
    report_path = write_browser_capture_report(report, tmp_path)

    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert data["deck_path"] == "deck.html"
    assert data["screenshot_capture"] == {"status": "failed", "reason": "browser unavailable"}
    assert data["slide_count_detected"] == 0
    assert data["screenshots"] == []
    assert data["browser_name"] == "chromium"
    assert data["console_errors"] == []


def test_capture_html_deck_rejects_missing_file(tmp_path):
    with pytest.raises(FileNotFoundError):
        capture_html_deck_screenshots(tmp_path / "missing.html", tmp_path / "screens")


@pytest.mark.browser
def test_capture_html_deck_with_playwright_when_available(tmp_path):
    pytest.importorskip("playwright.sync_api")
    deck_path = tmp_path / "deck.html"
    deck_path.write_text(
        """
        <!doctype html>
        <html><head><style>
        body { margin: 0; } .deck { width: 1280px; height: 720px; }
        .slide { display: none; width: 1280px; height: 720px; background: #02030a; color: white; }
        .slide.active { display: block; }
        </style></head><body>
        <main class="deck">
          <section class="slide" data-slide-id="s1" data-archetype="cover"><h1>One</h1></section>
          <section class="slide" data-slide-id="s2" data-archetype="timeline"><h1>Two</h1></section>
        </main>
        <script>
          const slides = Array.from(document.querySelectorAll('.slide'));
          function showSlide(index) { slides.forEach((slide, i) => slide.classList.toggle('active', i === index)); }
          showSlide(0);
        </script>
        </body></html>
        """,
        encoding="utf-8",
    )

    try:
        report_path = capture_html_deck_screenshots(deck_path, tmp_path / "screens", expected_slide_count=2)
    except Exception as exc:
        pytest.skip(f"Playwright browser unavailable: {exc}")

    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert data["screenshot_capture"]["status"] == "captured"
    assert data["slide_count_detected"] == 2
    assert (report_path.parent / "slide-01.png").exists()
    assert (report_path.parent / "slide-02.png").exists()
