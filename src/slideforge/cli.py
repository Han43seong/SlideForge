from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from slideforge.archetype_mapper import ArchetypeMapping
from slideforge.asset_brief_generator import generate_asset_briefs
from slideforge.design_spec import ColorToken, DesignSpec, SlideArchetype, TypographyToken
from slideforge.fidelity_report import render_fidelity_report
from slideforge.fidelity_scorer import FidelityScoreInput, score_fidelity
from slideforge.guizang_html_composer import HtmlDeck, HtmlSlide, compose_html_deck
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
    slides = [HtmlSlide(**item) for item in raw.get("slides", [])]
    return HtmlDeck(title=raw["title"], slides=slides)


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

    smoke_html = subparsers.add_parser("smoke-html", help="Write a compose-html smoke run with manifest/evidence artifacts")
    smoke_html.add_argument("--deck", required=True)
    smoke_html.add_argument("--runs-dir", required=True)
    smoke_html.add_argument("--run-id", required=True)
    smoke_html.set_defaults(func=_cmd_smoke_html)

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
