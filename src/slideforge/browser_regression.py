from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from slideforge.schemas import HtmlDeck


@dataclass(frozen=True)
class BrowserRegressionExpectation:
    """Browser-checkable evidence contract for a generated HTML deck.

    This intentionally records a deterministic plan/manifest rather than
    pretending to capture screenshots. Real screenshots can be attached by an
    external browser runner later without adding a dependency to SlideForge.
    """

    deck_path: str
    expected_slide_count: int
    expected_slide_ids: list[str]
    expected_archetypes: list[str]
    generated_report_path: str = "browser-regression-plan.json"

    @classmethod
    def from_deck(cls, deck: HtmlDeck, deck_path: str | Path) -> "BrowserRegressionExpectation":
        return cls(
            deck_path=str(deck_path),
            expected_slide_count=len(deck.slides),
            expected_slide_ids=[slide.slide_id for slide in deck.slides],
            expected_archetypes=[slide.archetype for slide in deck.slides],
        )

    def with_expected_slide_count(self, expected_slide_count: int) -> "BrowserRegressionExpectation":
        if expected_slide_count != self.expected_slide_count:
            raise ValueError(
                f"expected slide count {expected_slide_count} does not match deck slide count {self.expected_slide_count}"
            )
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_kind": "browser_regression_plan",
            "capture_mode": "manual_or_external_browser",
            "deck_path": self.deck_path,
            "expected_slide_count": self.expected_slide_count,
            "expected_slide_ids": self.expected_slide_ids,
            "expected_archetypes": self.expected_archetypes,
            "generated_report_path": self.generated_report_path,
            "screenshot_capture": {
                "status": "not_captured",
                "reason": "No browser automation dependency is required or assumed by SlideForge.",
            },
            "checks": [
                {
                    "name": "open_deck_in_browser",
                    "expectation": f"Browser can load {self.deck_path} without console-blocking asset dependencies.",
                },
                {
                    "name": "verify_slide_count",
                    "expectation": f"Deck exposes {self.expected_slide_count} .slide elements.",
                },
                {
                    "name": "verify_slide_ids",
                    "expectation": "Rendered slides preserve data-slide-id order.",
                    "expected": self.expected_slide_ids,
                },
                {
                    "name": "verify_archetypes",
                    "expectation": "Rendered slides preserve source archetype order for visual review.",
                    "expected": self.expected_archetypes,
                },
            ],
        }


def _relative_to_output(path: Path, output_dir: Path) -> str:
    try:
        return path.relative_to(output_dir).as_posix()
    except ValueError:
        return path.as_posix()


def write_browser_regression_plan(
    deck: HtmlDeck,
    deck_path: str | Path,
    output_dir: str | Path,
    report_name: str = "browser-regression-plan.json",
) -> Path:
    """Write a deterministic browser regression plan for an HTML deck.

    The plan is dependency-free evidence for what a browser/screenshot pass must
    validate: deck path, slide count, slide ids, archetypes, and where this
    report lives. It does not claim that screenshots were captured.
    """

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    report_path = destination / report_name
    deck_location = Path(deck_path)
    expectation = BrowserRegressionExpectation.from_deck(
        deck=deck,
        deck_path=_relative_to_output(deck_location, destination),
    )
    if report_name != expectation.generated_report_path:
        expectation = BrowserRegressionExpectation(
            deck_path=expectation.deck_path,
            expected_slide_count=expectation.expected_slide_count,
            expected_slide_ids=expectation.expected_slide_ids,
            expected_archetypes=expectation.expected_archetypes,
            generated_report_path=report_name,
        )

    report_path.write_text(json.dumps(expectation.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report_path
