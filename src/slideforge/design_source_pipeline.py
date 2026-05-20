from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from slideforge.deck_preparer import DEFAULT_ARCHETYPE
from slideforge.design_spec import DesignSpec
from slideforge.run_pipeline import validate_run_id
from slideforge.source_pipeline import (
    DEFAULT_SOURCE_INPUT_DIR_SUFFIX,
    SourceLocalRunReport,
    run_source_local,
)
from slideforge.template_analyzer import TemplateObservation, build_design_spec_from_observations

DEFAULT_DESIGN_SPEC_NAME = "design-spec.json"


@dataclass(frozen=True)
class DesignSourceLocalRunReport:
    run_dir: Path
    design_spec_path: Path
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
            "report_kind": "design_source_local_run_report",
            "run_dir": self.run_dir.as_posix(),
            "design_spec_path": self.design_spec_path.as_posix(),
            "sections_path": self.sections_path.as_posix(),
            "deck_input_path": self.deck_input_path.as_posix(),
            "generated_artifacts": [path.as_posix() for path in self.generated_artifacts],
            "summary_status": self.summary_status,
            "blockers": self.blockers,
            "warnings": self.warnings,
            "next_actions": self.next_actions,
            "missing_external_evidence": self.missing_external_evidence,
        }


def load_template_observations(path: str | Path) -> list[TemplateObservation]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("observations JSON must be a list")
    if not raw:
        raise ValueError("observations JSON must include at least one observation")
    observations: list[TemplateObservation] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError(f"observation {index} must be an object")
        observations.append(TemplateObservation(**item))
    return observations


def run_design_source_local(
    *,
    source: str | Path,
    observations: str | Path,
    design_name: str,
    title: str,
    runs_dir: str | Path,
    run_id: str,
    default_intent: str = "policy",
    default_archetype: str = DEFAULT_ARCHETYPE,
    input_output_dir: str | Path | None = None,
) -> DesignSourceLocalRunReport:
    """Build a design spec from observations, then run the local source pipeline.

    This is dependency-free and deterministic. It validates ``run_id`` before any
    writes, loads local observation JSON, writes ``design-spec.json`` in the
    handoff directory, and delegates section/deck/run artifact generation to the
    existing source-local path with the freshly built design spec.
    """
    validate_run_id(run_id)
    template_observations = load_template_observations(observations)
    design_spec = build_design_spec_from_observations(design_name, template_observations)

    handoff_dir = _handoff_dir(runs_dir=runs_dir, run_id=run_id, input_output_dir=input_output_dir)
    design_spec_path = handoff_dir / DEFAULT_DESIGN_SPEC_NAME
    _write_design_spec(design_spec_path, design_spec)

    source_report = run_source_local(
        source=source,
        title=title,
        runs_dir=runs_dir,
        run_id=run_id,
        default_intent=default_intent,
        default_archetype=default_archetype,
        design_spec=design_spec,
        input_output_dir=handoff_dir,
    )
    return _from_source_report(source_report, design_spec_path=design_spec_path)


def _handoff_dir(*, runs_dir: str | Path, run_id: str, input_output_dir: str | Path | None) -> Path:
    if input_output_dir is not None:
        return Path(input_output_dir)
    return Path(runs_dir) / f"{run_id}{DEFAULT_SOURCE_INPUT_DIR_SUFFIX}"


def _write_design_spec(path: Path, design_spec: DesignSpec) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(design_spec.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _from_source_report(
    report: SourceLocalRunReport,
    *,
    design_spec_path: Path,
) -> DesignSourceLocalRunReport:
    generated_artifacts = [
        design_spec_path,
        *[path for path in report.generated_artifacts if path != design_spec_path],
    ]
    return DesignSourceLocalRunReport(
        run_dir=report.run_dir,
        design_spec_path=design_spec_path,
        sections_path=report.sections_path,
        deck_input_path=report.deck_input_path,
        generated_artifacts=generated_artifacts,
        summary_status=report.summary_status,
        warnings=report.warnings,
        blockers=report.blockers,
        next_actions=report.next_actions,
        missing_external_evidence=report.missing_external_evidence,
    )
