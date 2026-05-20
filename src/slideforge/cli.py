from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from slideforge.archetype_mapper import ArchetypeMapping
from slideforge.asset_brief_generator import generate_asset_briefs
from slideforge.browser_capture import capture_html_deck_screenshots
from slideforge.comfyui_handoff import (
    DEFAULT_COMFYUI_ENDPOINT,
    DEFAULT_REPORT_NAME,
    write_comfyui_handoff_report,
)
from slideforge.design_spec import ColorToken, DesignSpec, SlideArchetype, TypographyToken
from slideforge.fidelity_report import render_fidelity_report
from slideforge.fidelity_scorer import FidelityScoreInput, score_fidelity
from slideforge.guizang_html_composer import (
    AssetPlaceholder,
    ChartDatum,
    ComparisonColumn,
    ComparisonRow,
    HtmlDeck,
    HtmlSlide,
    MetricRow,
    TimelineStep,
    VisualChip,
    compose_html_deck,
)
from slideforge.pptx_delivery_gate import write_pptx_delivery_gate
from slideforge.pptx_export import export_pptx_report
from slideforge.smoke_run import SmokeDeckInput, write_smoke_run
from slideforge.template_analyzer import TemplateObservation, build_design_spec_from_observations


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_observations(path: Path) -> list[TemplateObservation]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("observations JSON must be a list")
    return [TemplateObservation(**item) for item in raw]


def _load_design_spec(path: Path) -> DesignSpec:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return DesignSpec(
        name=raw["name"],
        source_refs=raw.get("source_refs", []),
        colors=[ColorToken(**item) for item in raw.get("colors", [])],
        typography=[TypographyToken(**item) for item in raw.get("typography", [])],
        slide_archetypes=[SlideArchetype(**item) for item in raw.get("slide_archetypes", [])],
        background_layers=raw.get("background_layers", []),
        graphic_motifs=raw.get("graphic_motifs", []),
    )


def _load_mappings(path: Path) -> list[ArchetypeMapping]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("mappings JSON must be a list")
    return [ArchetypeMapping(**item) for item in raw]


def _load_html_deck(path: Path) -> HtmlDeck:
    raw = json.loads(path.read_text(encoding="utf-8"))
    slides = [_load_html_slide(item) for item in raw.get("slides", [])]
    return HtmlDeck(title=raw["title"], slides=slides)


def _load_html_slide(raw: dict[str, Any]) -> HtmlSlide:
    payload = dict(raw)
    payload["visual_chips"] = [VisualChip(**item) for item in payload.get("visual_chips", [])]
    payload["asset_placeholders"] = [AssetPlaceholder(**item) for item in payload.get("asset_placeholders", [])]
    payload["timeline_steps"] = [TimelineStep(**item) for item in payload.get("timeline_steps", [])]
    payload["metric_rows"] = [MetricRow(**item) for item in payload.get("metric_rows", [])]
    payload["chart_data"] = [ChartDatum(**item) for item in payload.get("chart_data", [])]
    payload["comparison_columns"] = [ComparisonColumn(**item) for item in payload.get("comparison_columns", [])]
    payload["comparison_rows"] = [ComparisonRow(**item) for item in payload.get("comparison_rows", [])]
    return HtmlSlide(**payload)


def _cmd_build_spec(args: argparse.Namespace) -> int:
    observations = _load_observations(Path(args.observations))
    spec = build_design_spec_from_observations(args.name, observations)
    _write_json(Path(args.output), spec.to_dict())
    return 0


def _cmd_generate_asset_briefs(args: argparse.Namespace) -> int:
    spec = _load_design_spec(Path(args.design_spec))
    mappings = _load_mappings(Path(args.mappings))
    brief_set = generate_asset_briefs(spec, mappings)
    _write_json(Path(args.output), brief_set.to_comfyui_queue_payload(seed=args.seed))
    return 0


def _cmd_compose_html(args: argparse.Namespace) -> int:
    deck = _load_html_deck(Path(args.deck))
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(compose_html_deck(deck), encoding="utf-8")
    return 0


def _cmd_smoke_html(args: argparse.Namespace) -> int:
    raw = json.loads(Path(args.deck).read_text(encoding="utf-8"))
    write_smoke_run(
        root=Path(args.runs_dir),
        run_id=args.run_id,
        deck=SmokeDeckInput(title=raw["title"], slides=raw.get("slides", [])),
    )
    return 0


def _cmd_comfyui_handoff(args: argparse.Namespace) -> int:
    write_comfyui_handoff_report(
        asset_briefs_path=Path(args.asset_briefs),
        output_dir=Path(args.output_dir),
        endpoint=args.endpoint,
        workflow_path=Path(args.workflow) if args.workflow else None,
        report_name=args.report_name,
        execute=args.execute,
        timeout_seconds=args.timeout,
    )
    return 0


def _cmd_capture_screenshots(args: argparse.Namespace) -> int:
    viewport = {"width": args.viewport_width, "height": args.viewport_height}
    capture_html_deck_screenshots(
        deck_html=Path(args.deck_html),
        output_dir=Path(args.output_dir),
        expected_slide_count=args.expected_slide_count,
        viewport=viewport,
        report_name=args.report_name,
    )
    return 0


def _cmd_export_pptx(args: argparse.Namespace) -> int:
    deck = _load_html_deck(Path(args.deck))
    export_pptx_report(
        deck=deck,
        output_path=Path(args.output),
        report_output=Path(args.report_output),
        run_id=args.run_id or "",
    )
    return 0


def _cmd_pptx_delivery_gate(args: argparse.Namespace) -> int:
    write_pptx_delivery_gate(
        source_path=Path(args.source),
        desired_pptx_path=Path(args.desired_pptx),
        output_dir=Path(args.output_dir),
        run_id=args.run_id or "",
        report_name=args.report_name,
    )
    return 0


def _cmd_score_fidelity(args: argparse.Namespace) -> int:
    score = score_fidelity(
        FidelityScoreInput(
            background=args.background,
            generated_assets=args.generated_assets,
            layout_archetype=args.layout_archetype,
            typography=args.typography,
            data_visuals=args.data_visuals,
            korean_readability=args.korean_readability,
            technical_validity=args.technical_validity,
        )
    )
    _write_json(Path(args.output), score.to_dict())
    if args.markdown_output:
        markdown_output = Path(args.markdown_output)
        markdown_output.parent.mkdir(parents=True, exist_ok=True)
        markdown_output.write_text(render_fidelity_report(score), encoding="utf-8")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="slideforge")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_spec = subparsers.add_parser("build-spec", help="Build a design-spec JSON from template observations")
    build_spec.add_argument("--name", required=True)
    build_spec.add_argument("--observations", required=True)
    build_spec.add_argument("--output", required=True)
    build_spec.set_defaults(func=_cmd_build_spec)

    asset_briefs = subparsers.add_parser(
        "generate-asset-briefs",
        help="Generate text-free ComfyUI asset briefs from a design spec and archetype mappings",
    )
    asset_briefs.add_argument("--design-spec", required=True)
    asset_briefs.add_argument("--mappings", required=True)
    asset_briefs.add_argument("--output", required=True)
    asset_briefs.add_argument("--seed", type=int)
    asset_briefs.set_defaults(func=_cmd_generate_asset_briefs)

    compose_html = subparsers.add_parser("compose-html", help="Compose a guizang-style HTML presentation")
    compose_html.add_argument("--deck", required=True)
    compose_html.add_argument("--output", required=True)
    compose_html.set_defaults(func=_cmd_compose_html)

    comfyui = subparsers.add_parser(
        "comfyui-handoff",
        help="Write an honest ComfyUI asset handoff report and optionally submit to an already-running REST endpoint",
    )
    comfyui.add_argument("--asset-briefs", required=True, help="JSON payload from generate-asset-briefs")
    comfyui.add_argument("--output-dir", required=True, help="Directory for the handoff report")
    comfyui.add_argument("--endpoint", default=DEFAULT_COMFYUI_ENDPOINT)
    comfyui.add_argument("--workflow", help="Optional ComfyUI workflow API JSON to submit when --execute is set")
    comfyui.add_argument("--report-name", default=DEFAULT_REPORT_NAME)
    comfyui.add_argument(
        "--execute",
        action="store_true",
        help="Submit prompts only when endpoint health succeeds and --workflow is provided",
    )
    comfyui.add_argument("--timeout", type=float, default=1.0, help="HTTP health/submit timeout in seconds")
    comfyui.set_defaults(func=_cmd_comfyui_handoff)

    smoke_html = subparsers.add_parser("smoke-html", help="Write a compose-html smoke run with manifest/evidence artifacts")
    smoke_html.add_argument("--deck", required=True)
    smoke_html.add_argument("--runs-dir", required=True)
    smoke_html.add_argument("--run-id", required=True)
    smoke_html.set_defaults(func=_cmd_smoke_html)

    capture = subparsers.add_parser(
        "capture-screenshots",
        help="Capture per-slide screenshots from a local HTML deck with Playwright Chromium",
    )
    capture.add_argument("--deck-html", required=True, help="Path to the local HTML deck to open in Chromium")
    capture.add_argument("--output-dir", required=True, help="Directory for PNG screenshots and browser-regression-report.json")
    capture.add_argument("--expected-slide-count", type=int, help="Fail if the detected .slide count differs")
    capture.add_argument("--viewport-width", type=int, default=1280)
    capture.add_argument("--viewport-height", type=int, default=720)
    capture.add_argument("--report-name", default="browser-regression-report.json")
    capture.set_defaults(func=_cmd_capture_screenshots)

    export_pptx = subparsers.add_parser(
        "export-pptx",
        help="Export a deck JSON to PPTX when optional python-pptx is installed; otherwise write an honest unavailable report",
    )
    export_pptx.add_argument("--deck", required=True, help="HtmlDeck-compatible deck JSON")
    export_pptx.add_argument("--output", required=True, help="PPTX output path to create only when python-pptx is available")
    export_pptx.add_argument("--report-output", required=True, help="JSON report path for generation/static evidence")
    export_pptx.add_argument("--run-id", default="")
    export_pptx.set_defaults(func=_cmd_export_pptx)

    pptx_gate = subparsers.add_parser(
        "pptx-delivery-gate",
        help="Write a dependency-free PPTX delivery/render strategy contract",
    )
    pptx_gate.add_argument("--source", required=True, help="Source HTML/deck path to be exported or recreated as PPTX")
    pptx_gate.add_argument("--desired-pptx", required=True, help="Desired PPTX output path")
    pptx_gate.add_argument("--output-dir", required=True, help="Directory for the gate JSON artifact")
    pptx_gate.add_argument("--run-id", default="")
    pptx_gate.add_argument("--report-name", default="pptx-delivery-gate.json")
    pptx_gate.set_defaults(func=_cmd_pptx_delivery_gate)

    score = subparsers.add_parser("score-fidelity", help="Write a 100-point fidelity score report")
    score.add_argument("--background", type=int, required=True)
    score.add_argument("--generated-assets", type=int, required=True)
    score.add_argument("--layout-archetype", type=int, required=True)
    score.add_argument("--typography", type=int, required=True)
    score.add_argument("--data-visuals", type=int, required=True)
    score.add_argument("--korean-readability", type=int, required=True)
    score.add_argument("--technical-validity", type=int, required=True)
    score.add_argument("--output", required=True)
    score.add_argument("--markdown-output")
    score.set_defaults(func=_cmd_score_fidelity)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
