from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from slideforge.guizang_html_composer import HtmlDeck, HtmlSlide, MetricRow, TimelineStep, VisualChip, compose_html_deck
from slideforge.run_manifest import EvidenceArtifact, RunManifest, RunManifestWriter


@dataclass(frozen=True)
class SmokeDeckInput:
    title: str
    slides: list[dict[str, Any]]

    def to_html_deck(self) -> HtmlDeck:
        return HtmlDeck(title=self.title, slides=[_load_smoke_slide(slide) for slide in self.slides])

    def to_dict(self) -> dict[str, Any]:
        return {"title": self.title, "slides": self.slides}


def _load_smoke_slide(raw: dict[str, Any]) -> HtmlSlide:
    payload = dict(raw)
    payload["visual_chips"] = [VisualChip(**item) for item in payload.get("visual_chips", [])]
    payload["timeline_steps"] = [TimelineStep(**item) for item in payload.get("timeline_steps", [])]
    payload["metric_rows"] = [MetricRow(**item) for item in payload.get("metric_rows", [])]
    return HtmlSlide(**payload)


def write_smoke_run(root: str | Path, run_id: str, deck: SmokeDeckInput) -> Path:
    run_root = Path(root)
    run_dir = run_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    deck_json = run_dir / "deck.json"
    deck_html = run_dir / "deck.html"
    html = compose_html_deck(deck.to_html_deck())
    deck_json.write_text(json.dumps(deck.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    deck_html.write_text(html, encoding="utf-8")

    checks = {
        "html_contains_presentation_shell": "pass" if "function showSlide" in html else "fail",
        "html_contains_counter": "pass" if "#counter" in html else "fail",
        "html_slide_count": str(html.count('class="slide"')),
    }

    manifest = RunManifest(
        run_id=run_id,
        project="SlideForge",
        pipeline="compose-html-smoke",
        inputs={"deck_title": deck.title, "slide_count": str(len(deck.slides))},
        artifacts=[
            EvidenceArtifact(name="source_deck", path="deck.json", kind="json"),
            EvidenceArtifact(name="html_deck", path="deck.html", kind="html"),
        ],
        checks=checks,
    )
    RunManifestWriter(run_root).write(manifest)
    return run_dir
