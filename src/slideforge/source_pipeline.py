from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from slideforge.deck_preparer import DEFAULT_ARCHETYPE, load_sections_json, write_prepared_deck
from slideforge.design_spec import DesignSpec
from slideforge.run_pipeline import LocalRunReport, run_local, validate_run_id
from slideforge.section_preparer import write_prepared_sections


DEFAULT_SOURCE_INPUT_DIR_SUFFIX = "-input"
DEFAULT_SECTIONS_NAME = "sections.json"
DEFAULT_DECK_NAME = "deck.json"


@dataclass(frozen=True)
class SourceLocalRunReport:
    run_dir: Path
    sections_path: Path
    deck_input_path: Path
    generated_artifacts: list[Path]
    summary_status: str
    warnings: list[str]
    blockers: list[str]
    next_actions: list[str]
    missing_external_evidence: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_kind": "source_local_run_report",
            "run_dir": self.run_dir.as_posix(),
            "sections_path": self.sections_path.as_posix(),
            "deck_input_path": self.deck_input_path.as_posix(),
            "generated_artifacts": [path.as_posix() for path in self.generated_artifacts],
            "summary_status": self.summary_status,
            "blockers": self.blockers,
            "warnings": self.warnings,
            "next_actions": self.next_actions,
            "missing_external_evidence": self.missing_external_evidence,
        }


def run_source_local(
    *,
    source: str | Path,
    title: str,
    runs_dir: str | Path,
    run_id: str,
    default_intent: str = "policy",
    default_archetype: str = DEFAULT_ARCHETYPE,
    design_spec: DesignSpec | None = None,
    input_output_dir: str | Path | None = None,
) -> SourceLocalRunReport:
    """Run the deterministic source-material handoff path in one dependency-free call.

    The runner validates ``run_id`` through the same path used by ``run_local`` before
    writing any handoff or run artifacts. It then composes the existing primitives:
    ``write_prepared_sections`` -> ``write_prepared_deck`` -> ``run_local``. No LLM,
    browser, ComfyUI, or PPTX renderer is invoked; missing external evidence remains
    visible in the returned summary fields.
    """
    validate_run_id(run_id)

    handoff_dir = Path(input_output_dir) if input_output_dir is not None else Path(runs_dir) / f"{run_id}{DEFAULT_SOURCE_INPUT_DIR_SUFFIX}"
    sections_path = handoff_dir / DEFAULT_SECTIONS_NAME
    deck_input_path = handoff_dir / DEFAULT_DECK_NAME

    # write_prepared_sections parses before creating the output directory, so empty
    # or invalid source material fails without creating run artifacts.
    write_prepared_sections(source=source, output=sections_path, default_intent=default_intent)
    sections = load_sections_json(sections_path)
    write_prepared_deck(
        title=title,
        sections=sections,
        output=deck_input_path,
        design_spec=design_spec,
        default_archetype=default_archetype,
    )

    local_report = run_local(deck=deck_input_path, runs_dir=runs_dir, run_id=run_id)
    return _from_local_report(local_report, sections_path=sections_path, deck_input_path=deck_input_path)


def write_source_local_report(path: str | Path, report: SourceLocalRunReport) -> Path:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output


def _from_local_report(
    report: LocalRunReport,
    *,
    sections_path: Path,
    deck_input_path: Path,
) -> SourceLocalRunReport:
    return SourceLocalRunReport(
        run_dir=report.run_dir,
        sections_path=sections_path,
        deck_input_path=deck_input_path,
        generated_artifacts=[sections_path, deck_input_path, *report.generated_artifacts],
        summary_status=report.summary_status,
        warnings=report.warnings,
        blockers=report.blockers,
        next_actions=report.next_actions,
        missing_external_evidence=report.missing_external_evidence,
    )
