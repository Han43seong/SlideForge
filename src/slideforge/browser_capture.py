from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


DEFAULT_CAPTURE_REPORT_NAME = "browser-regression-report.json"
DEFAULT_VIEWPORT = {"width": 1280, "height": 720}


@dataclass(frozen=True)
class SlideScreenshot:
    index: int
    slide_id: str
    archetype: str
    path: str

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"index": self.index, "path": self.path}
        if self.slide_id:
            payload["id"] = self.slide_id
        if self.archetype:
            payload["archetype"] = self.archetype
        return payload


@dataclass(frozen=True)
class BrowserCaptureReport:
    deck_path: str
    output_dir: str
    status: str
    slide_count_detected: int
    screenshots: list[SlideScreenshot]
    viewport: dict[str, int]
    browser_name: str = "chromium"
    console_errors: list[str] = field(default_factory=list)
    generated_report_path: str = DEFAULT_CAPTURE_REPORT_NAME
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        capture: dict[str, Any] = {"status": self.status}
        if self.failure_reason:
            capture["reason"] = self.failure_reason
        return {
            "report_kind": "browser_regression_report",
            "capture_mode": "real_playwright_chromium",
            "deck_path": self.deck_path,
            "output_dir": self.output_dir,
            "screenshot_capture": capture,
            "slide_count_detected": self.slide_count_detected,
            "screenshots": [screenshot.to_dict() for screenshot in self.screenshots],
            "viewport": self.viewport,
            "browser_name": self.browser_name,
            "console_errors": self.console_errors,
            "generated_report_path": self.generated_report_path,
        }


def _relative_to_output(path: Path, output_dir: Path) -> str:
    try:
        return path.relative_to(output_dir).as_posix()
    except ValueError:
        return path.as_posix()


def _coerce_viewport(viewport: dict[str, int] | None = None) -> dict[str, int]:
    raw = viewport or DEFAULT_VIEWPORT
    width = int(raw["width"])
    height = int(raw["height"])
    if width <= 0 or height <= 0:
        raise ValueError("viewport width and height must be positive")
    return {"width": width, "height": height}


def write_browser_capture_report(report: BrowserCaptureReport, output_dir: str | Path) -> Path:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    report_path = destination / report.generated_report_path
    report_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report_path


def build_failed_capture_report(
    deck_path: str | Path,
    output_dir: str | Path,
    reason: str,
    *,
    viewport: dict[str, int] | None = None,
    slide_count_detected: int = 0,
    report_name: str = DEFAULT_CAPTURE_REPORT_NAME,
) -> BrowserCaptureReport:
    destination = Path(output_dir)
    return BrowserCaptureReport(
        deck_path=_relative_to_output(Path(deck_path), destination),
        output_dir=destination.as_posix(),
        status="failed",
        slide_count_detected=slide_count_detected,
        screenshots=[],
        viewport=_coerce_viewport(viewport),
        generated_report_path=report_name,
        failure_reason=reason,
    )


def capture_html_deck_screenshots(
    deck_html: str | Path,
    output_dir: str | Path,
    *,
    expected_slide_count: int | None = None,
    viewport: dict[str, int] | None = None,
    report_name: str = DEFAULT_CAPTURE_REPORT_NAME,
) -> Path:
    """Capture per-slide screenshots for a local SlideForge HTML deck.

    Playwright is imported lazily so the rest of SlideForge stays dependency-free
    unless this real browser runner is invoked.
    """

    deck_path = Path(deck_html).expanduser().resolve()
    if not deck_path.exists():
        raise FileNotFoundError(f"deck HTML does not exist: {deck_path}")
    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    viewport_value = _coerce_viewport(viewport)

    try:
        from playwright.sync_api import sync_playwright
    except ModuleNotFoundError as exc:  # pragma: no cover - environment-dependent branch
        report = build_failed_capture_report(
            deck_path,
            destination,
            "Playwright is not installed. Install with `python -m pip install -e .[browser]`.",
            viewport=viewport_value,
            report_name=report_name,
        )
        write_browser_capture_report(report, destination)
        raise RuntimeError(report.failure_reason) from exc

    screenshots: list[SlideScreenshot] = []
    console_errors: list[str] = []
    slide_count = 0
    browser: Any | None = None
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport=viewport_value, device_scale_factor=1)
            page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
            page.on("pageerror", lambda error: console_errors.append(str(error)))
            page.goto(deck_path.as_uri(), wait_until="networkidle")
            page.wait_for_selector(".slide", state="attached")
            slide_metadata = page.locator(".slide").evaluate_all(
                """
                slides => slides.map((slide, index) => ({
                  index: index + 1,
                  id: slide.getAttribute('data-slide-id') || slide.id || '',
                  archetype: slide.getAttribute('data-archetype') || ''
                }))
                """
            )
            slide_count = len(slide_metadata)
            if expected_slide_count is not None and slide_count != expected_slide_count:
                raise ValueError(
                    f"expected slide count {expected_slide_count} does not match detected slide count {slide_count}"
                )
            for zero_based_index, slide in enumerate(slide_metadata):
                page.evaluate(
                    """
                    index => {
                      if (typeof window.showSlide === 'function') {
                        window.showSlide(index);
                        return;
                      }
                      const slides = Array.from(document.querySelectorAll('.slide'));
                      slides.forEach((slide, i) => {
                        slide.classList.toggle('active', i === index);
                        slide.style.display = i === index ? 'block' : 'none';
                      });
                    }
                    """,
                    zero_based_index,
                )
                page.wait_for_timeout(50)
                screenshot_name = f"slide-{int(slide['index']):02d}.png"
                screenshot_path = destination / screenshot_name
                page.locator(".deck").screenshot(path=str(screenshot_path))
                screenshots.append(
                    SlideScreenshot(
                        index=int(slide["index"]),
                        slide_id=str(slide.get("id") or ""),
                        archetype=str(slide.get("archetype") or ""),
                        path=_relative_to_output(screenshot_path, destination),
                    )
                )
            browser.close()
            browser = None
    except Exception as exc:
        failure_reason = str(exc)
        if exc.__class__.__name__ == "Error" or "Executable doesn't exist" in failure_reason:
            failure_reason = (
                f"Playwright Chromium capture failed: {failure_reason}. "
                "Install browser binaries with `python -m playwright install chromium`."
            )
        report = build_failed_capture_report(
            deck_path,
            destination,
            failure_reason,
            viewport=viewport_value,
            slide_count_detected=slide_count,
            report_name=report_name,
        )
        report.console_errors.extend(console_errors)
        write_browser_capture_report(report, destination)
        raise
    finally:
        if browser is not None:
            browser.close()

    report = BrowserCaptureReport(
        deck_path=_relative_to_output(deck_path, destination),
        output_dir=destination.as_posix(),
        status="captured",
        slide_count_detected=slide_count,
        screenshots=screenshots,
        viewport=viewport_value,
        console_errors=console_errors,
        generated_report_path=report_name,
    )
    return write_browser_capture_report(report, destination)
