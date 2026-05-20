from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any

from slideforge.evidence_summary import write_evidence_summary
from slideforge.smoke_run import SmokeDeckInput, write_smoke_run


DEFAULT_RUNS_DIR = "runs"
DEFAULT_SUMMARY_JSON_NAME = "run-summary.json"
DEFAULT_SUMMARY_MARKDOWN_NAME = "run-summary.md"
_RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True)
class LocalRunReport:
    run_dir: Path
    generated_artifacts: list[Path]
    summary_status: str
    warnings: list[str]
    blockers: list[str]
    next_actions: list[str]
    missing_external_evidence: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_kind": "local_run_report",
            "run_dir": self.run_dir.as_posix(),
            "generated_artifacts": [path.as_posix() for path in self.generated_artifacts],
            "summary_status": self.summary_status,
            "blockers": self.blockers,
            "warnings": self.warnings,
            "next_actions": self.next_actions,
            "missing_external_evidence": self.missing_external_evidence,
        }


def run_local(
    *,
    deck: str | Path,
    runs_dir: str | Path = DEFAULT_RUNS_DIR,
    run_id: str,
    summary_output: str | Path | None = None,
    summary_markdown_output: str | Path | None = None,
) -> LocalRunReport:
    """Create a deterministic local evidence run from an HtmlDeck-compatible JSON deck.

    The runner composes existing dependency-free primitives: smoke run generation first,
    then evidence summary aggregation. It does not perform browser capture, PPTX render,
    or ComfyUI generation; missing external evidence remains warnings/next actions in the
    summary.
    """
    validate_run_id(run_id)

    deck_payload = _load_deck_payload(Path(deck))
    run_dir = write_smoke_run(
        root=Path(runs_dir),
        run_id=run_id,
        deck=SmokeDeckInput(title=deck_payload["title"], slides=deck_payload.get("slides", [])),
    )
    summary_json = Path(summary_output) if summary_output is not None else run_dir / DEFAULT_SUMMARY_JSON_NAME
    summary_markdown = (
        Path(summary_markdown_output) if summary_markdown_output is not None else run_dir / DEFAULT_SUMMARY_MARKDOWN_NAME
    )
    summary = write_evidence_summary(run_dir=run_dir, output=summary_json, markdown_output=summary_markdown)

    generated = _existing_paths(
        [
            run_dir / "deck.json",
            run_dir / "deck.html",
            run_dir / "browser-regression-plan.json",
            run_dir / "pptx-delivery-gate.json",
            run_dir / "manifest.json",
            run_dir / "evidence-index.md",
            summary_json,
            summary_markdown,
        ]
    )
    return LocalRunReport(
        run_dir=run_dir,
        generated_artifacts=generated,
        summary_status=str(summary.get("status", "pending")),
        warnings=[str(item) for item in summary.get("warnings", [])],
        blockers=[str(item) for item in summary.get("blockers", [])],
        next_actions=[str(item) for item in summary.get("next_actions", [])],
        missing_external_evidence=_missing_external_evidence(summary),
    )


def validate_run_id(run_id: str) -> None:
    if not run_id.strip():
        raise ValueError("run_id is required")
    if not _RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError("run_id may contain only letters, numbers, dot, underscore, and hyphen")


def _load_deck_payload(path: Path) -> dict[str, Any]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("deck JSON must be an object")
    if not str(raw.get("title", "")).strip():
        raise ValueError("deck JSON must include a non-empty title")
    slides = raw.get("slides", [])
    if not isinstance(slides, list):
        raise ValueError("deck JSON slides must be a list when provided")
    return raw


def _existing_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    existing: list[Path] = []
    for path in paths:
        key = path.as_posix()
        if key not in seen and path.exists():
            seen.add(key)
            existing.append(path)
    return existing


def _missing_external_evidence(summary: dict[str, Any]) -> list[str]:
    sections = summary.get("sections", {})
    if not isinstance(sections, dict):
        return []
    missing: list[str] = []
    browser = sections.get("browser_capture", {})
    if isinstance(browser, dict) and browser.get("status") != "captured":
        missing.append("real_browser_screenshot_capture")
    pptx = sections.get("pptx", {})
    if isinstance(pptx, dict) and pptx.get("claim") != "pptx_export_report_present":
        missing.append("pptx_export_or_render_evidence")
    comfyui = sections.get("comfyui", {})
    if isinstance(comfyui, dict) and comfyui.get("status") not in {"available", "complete", "ready"}:
        missing.append("comfyui_generated_asset_evidence")
    fidelity = sections.get("fidelity", {})
    if isinstance(fidelity, dict) and fidelity.get("status") == "pending":
        missing.append("fidelity_score_or_report")
    return missing
