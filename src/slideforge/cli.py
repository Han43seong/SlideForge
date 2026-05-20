from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from slideforge.fidelity_scorer import FidelityScoreInput, score_fidelity
from slideforge.template_analyzer import TemplateObservation, build_design_spec_from_observations


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_observations(path: Path) -> list[TemplateObservation]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("observations JSON must be a list")
    return [TemplateObservation(**item) for item in raw]


def _cmd_build_spec(args: argparse.Namespace) -> int:
    observations = _load_observations(Path(args.observations))
    spec = build_design_spec_from_observations(args.name, observations)
    _write_json(Path(args.output), spec.to_dict())
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
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="slideforge")
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_spec = subparsers.add_parser("build-spec", help="Build a design-spec JSON from template observations")
    build_spec.add_argument("--name", required=True)
    build_spec.add_argument("--observations", required=True)
    build_spec.add_argument("--output", required=True)
    build_spec.set_defaults(func=_cmd_build_spec)

    score = subparsers.add_parser("score-fidelity", help="Write a 100-point fidelity score report")
    score.add_argument("--background", type=int, required=True)
    score.add_argument("--generated-assets", type=int, required=True)
    score.add_argument("--layout-archetype", type=int, required=True)
    score.add_argument("--typography", type=int, required=True)
    score.add_argument("--data-visuals", type=int, required=True)
    score.add_argument("--korean-readability", type=int, required=True)
    score.add_argument("--technical-validity", type=int, required=True)
    score.add_argument("--output", required=True)
    score.set_defaults(func=_cmd_score_fidelity)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
