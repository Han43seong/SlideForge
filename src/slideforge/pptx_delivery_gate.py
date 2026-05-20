from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import shutil
from typing import Any, Mapping


@dataclass(frozen=True)
class ToolAvailability:
    """Local availability record for a PPTX export/render validation tool."""

    name: str
    executable: str
    available: bool
    path: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("tool name is required")
        if not self.executable.strip():
            raise ValueError("tool executable is required")

    @classmethod
    def detect(cls, name: str, executable: str) -> "ToolAvailability":
        path = shutil.which(executable) or ""
        return cls(name=name, executable=executable, available=bool(path), path=path)


@dataclass(frozen=True)
class PptxDeliveryGate:
    """Dependency-free contract for honest PPTX delivery/render validation.

    The gate records what would be required to validate a PPTX export. It does
    not export PPTX, render slides, or claim visual validation happened.
    """

    source_path: str
    desired_pptx_path: str
    run_id: str = ""
    current_status: str = "pending"
    renderer_strategy: dict[str, Any] = field(default_factory=dict)
    static_checks_planned: list[str] = field(default_factory=list)
    visual_checks_planned: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    tool_availability: dict[str, dict[str, Any]] = field(default_factory=dict)
    validation_claim: str = "strategy_contract_only_no_pptx_export_or_visual_render_performed"
    generated_report_path: str = "pptx-delivery-gate.json"

    def __post_init__(self) -> None:
        if not self.source_path.strip():
            raise ValueError("source_path is required")
        if not self.desired_pptx_path.strip():
            raise ValueError("desired_pptx_path is required")
        if self.current_status not in {"available", "unavailable", "pending"}:
            raise ValueError("current_status must be available, unavailable, or pending")

    @classmethod
    def from_paths(
        cls,
        source_path: str | Path,
        desired_pptx_path: str | Path,
        run_id: str = "",
        tool_availability: Mapping[str, ToolAvailability] | None = None,
        generated_report_path: str = "pptx-delivery-gate.json",
    ) -> "PptxDeliveryGate":
        tools = dict(tool_availability) if tool_availability is not None else detect_pptx_validation_tools()
        available_tools = [tool for tool in tools.values() if tool.available]
        missing_tools = [tool.name for tool in tools.values() if not tool.available]

        if any(tool.name == "libreoffice" and tool.available for tool in available_tools):
            status = "available"
            selected = "libreoffice_headless_export_then_render_check"
            blockers: list[str] = []
        elif any(tool.name == "pptx_glimpse" and tool.available for tool in available_tools):
            status = "available"
            selected = "pptx_glimpse_static_visual_inspection"
            blockers = []
        elif tools:
            status = "unavailable"
            selected = "manual_or_external_pptx_renderer"
            blockers = [
                "No local PPTX export/render validation tool is available: " + ", ".join(missing_tools) + ".",
                "Renderer evidence requires approved pptx-glimpse installation; no install was performed.",
            ]
        else:
            status = "pending"
            selected = "tool_availability_not_checked"
            blockers = ["PPTX validation tool availability has not been checked."]

        return cls(
            source_path=str(source_path),
            desired_pptx_path=str(desired_pptx_path),
            run_id=run_id,
            current_status=status,
            renderer_strategy={
                "selected": selected,
                "candidates": [
                    {
                        "name": "libreoffice_headless_export_then_render_check",
                        "requires": ["soffice/libreoffice executable"],
                        "purpose": "Export the approved HTML/deck source to PPTX and render exported slides for visual comparison.",
                    },
                    {
                        "name": "pptx_glimpse_static_visual_inspection",
                        "requires": ["pptx-glimpse executable"],
                        "purpose": "Inspect PPTX structure/render previews when the tool is explicitly available.",
                    },
                    {
                        "name": "manual_or_external_pptx_renderer",
                        "requires": ["approved external renderer or human QA pass"],
                        "purpose": "Track required PPTX checks without pretending local validation passed.",
                    },
                ],
            },
            static_checks_planned=[
                "Confirm desired PPTX file exists after export step.",
                "Confirm PPTX file extension and non-empty file size.",
                "Confirm source slide count maps to PPTX slide count.",
                "Confirm text placeholders and asset references are accounted for in the PPTX route.",
            ],
            visual_checks_planned=[
                "Render each PPTX slide to an image or review in a trusted presentation viewer.",
                "Compare rendered PPTX slides against approved HTML/browser evidence for layout, typography, colors, and asset placement.",
                "Record any render screenshots or manual reviewer notes as follow-up evidence artifacts.",
            ],
            blockers=blockers,
            tool_availability={name: asdict(tool) for name, tool in tools.items()},
            generated_report_path=generated_report_path,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_kind": "pptx_delivery_gate",
            "validation_claim": self.validation_claim,
            "run_id": self.run_id,
            "source_path": self.source_path,
            "desired_pptx_path": self.desired_pptx_path,
            "current_status": self.current_status,
            "renderer_strategy": self.renderer_strategy,
            "static_checks_planned": self.static_checks_planned,
            "visual_checks_planned": self.visual_checks_planned,
            "blockers": self.blockers,
            "tool_availability": self.tool_availability,
            "generated_report_path": self.generated_report_path,
        }


def detect_pptx_validation_tools() -> dict[str, ToolAvailability]:
    libreoffice = ToolAvailability.detect("libreoffice", "soffice")
    if not libreoffice.available:
        libreoffice = ToolAvailability.detect("libreoffice", "libreoffice")
    return {
        "libreoffice": libreoffice,
        "pptx_glimpse": ToolAvailability.detect("pptx_glimpse", "pptx-glimpse"),
    }


def _relative_to_output(path: Path, output_dir: Path) -> str:
    try:
        return path.relative_to(output_dir).as_posix()
    except ValueError:
        return path.as_posix()


def write_pptx_delivery_gate(
    source_path: str | Path,
    desired_pptx_path: str | Path,
    output_dir: str | Path,
    run_id: str = "",
    report_name: str = "pptx-delivery-gate.json",
    tool_availability: Mapping[str, ToolAvailability] | None = None,
) -> Path:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    report_path = destination / report_name
    gate = PptxDeliveryGate.from_paths(
        source_path=_relative_to_output(Path(source_path), destination),
        desired_pptx_path=_relative_to_output(Path(desired_pptx_path), destination),
        run_id=run_id,
        tool_availability=tool_availability,
        generated_report_path=report_name,
    )
    report_path.write_text(json.dumps(gate.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report_path
