from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path
from typing import Any

from slideforge.asset_spec import AssetSpec, load_asset_specs

SUPPORTED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"}
LICENSE_NOTE = "Generated manually by user in ChatGPT Pro/OpenAI Images; verify plan terms before commercial use."


def import_manual_openai_assets(
    *,
    run_dir: Path,
    asset_spec_dir: Path,
    input_dir: Path,
    output_report: Path,
) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    asset_spec_dir = _resolve_existing_from_run(run_dir, asset_spec_dir)
    specs = load_asset_specs(asset_spec_dir)
    input_dir = _resolve_existing_from_run(run_dir, input_dir)
    output_report = _resolve_output_from_run(run_dir, output_report)
    imported_dir = run_dir / "imported-assets"
    imported_dir.mkdir(parents=True, exist_ok=True)

    warnings: list[str] = []
    candidates: list[dict[str, Any]] = []
    for spec in specs:
        asset_input_dir = input_dir / spec.asset_id
        if not asset_input_dir.exists():
            _warn(warnings, f"missing manual asset directory for {spec.asset_id}: {asset_input_dir}")
            continue
        if not asset_input_dir.is_dir():
            _warn(warnings, f"manual asset path is not a directory for {spec.asset_id}: {asset_input_dir}")
            continue

        for source_path in sorted(path for path in asset_input_dir.iterdir() if path.is_file()):
            ext = source_path.suffix.lower()
            if ext not in SUPPORTED_IMAGE_EXTENSIONS:
                _warn(warnings, f"ignored unsupported asset extension for {spec.asset_id}: {source_path.name}")
                continue
            candidate_id = source_path.stem.strip()
            if not candidate_id:
                _warn(warnings, f"ignored empty candidate id for {spec.asset_id}: {source_path.name}")
                continue
            dest = imported_dir / f"{spec.asset_id}-{candidate_id}{ext}"
            shutil.copy2(source_path, dest)
            rel_dest = dest.relative_to(run_dir).as_posix()
            candidates.append(_candidate_payload(spec, candidate_id=candidate_id, rel_dest=rel_dest))

    payload = {
        "report_kind": "asset_generation_report",
        "run_id": run_dir.name,
        "provider": "openai_images",
        "source": "manual_openai_images",
        "generation_mode": "manual_chatgpt_pro",
        "asset_spec_dir": _display_path(asset_spec_dir, run_dir),
        "input_dir": _display_path(input_dir, run_dir),
        "imported_dir": "imported-assets",
        "candidate_count": len(candidates),
        "candidates": candidates,
        "warnings": warnings,
    }
    output_report.parent.mkdir(parents=True, exist_ok=True)
    output_report.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def _candidate_payload(spec: AssetSpec, *, candidate_id: str, rel_dest: str) -> dict[str, Any]:
    return {
        "slide_id": spec.target_slide,
        "asset_id": spec.asset_id,
        "candidate_id": candidate_id,
        "path": rel_dest,
        "asset_path": rel_dest,
        "provider": "openai_images",
        "source": "manual_openai_images",
        "generation_mode": "manual_chatgpt_pro",
        "prompt_file": f"openai-manual-prompts/{spec.asset_id}.md",
        "license_note": LICENSE_NOTE,
        "status": "generated",
        "notes": f"Manual OpenAI Images candidate for {spec.role}",
    }


def _resolve_existing_from_run(run_dir: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    run_relative = run_dir / path
    if run_relative.exists():
        return run_relative
    if path.exists():
        return path
    return run_relative


def _resolve_output_from_run(run_dir: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    run_relative = run_dir / path
    if run_relative.parent.exists():
        return run_relative
    if path.parent.exists():
        return path
    return run_relative


def _display_path(path: Path, run_dir: Path) -> str:
    try:
        return path.resolve().relative_to(run_dir).as_posix()
    except ValueError:
        return str(path)


def _warn(warnings: list[str], message: str) -> None:
    warnings.append(message)
    print(f"warning: {message}", file=sys.stderr)
