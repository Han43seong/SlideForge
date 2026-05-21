from __future__ import annotations

import json
from pathlib import Path
from typing import Any

VALID_APPROVAL_MODES = {"explicit_user", "jarvis_recommended", "autonomous"}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_selection(selection: str) -> dict[str, str]:
    selected: dict[str, str] = {}
    for raw_item in selection.split(","):
        item = raw_item.strip()
        if not item:
            continue
        if "=" not in item:
            raise ValueError(f"selection item must be slide_id=candidate_id: {item}")
        slide_id, candidate_id = item.split("=", 1)
        slide_id = slide_id.strip()
        candidate_id = candidate_id.strip()
        if not slide_id or not candidate_id:
            raise ValueError(f"selection item must include non-empty slide_id and candidate_id: {item}")
        selected[slide_id] = candidate_id
    if not selected:
        raise ValueError("at least one asset selection is required")
    return selected


def write_approved_assets(
    *,
    candidates_path: Path,
    selection: str,
    output: Path,
    approved_by: str = "user",
    approval_mode: str = "explicit_user",
    notes: str = "",
) -> dict[str, Any]:
    if approval_mode not in VALID_APPROVAL_MODES:
        raise ValueError(f"approval_mode must be one of {sorted(VALID_APPROVAL_MODES)}")
    report = _load_json(candidates_path)
    selected = _parse_selection(selection)
    candidates = report.get("candidates", [])
    if not isinstance(candidates, list):
        raise ValueError("candidate report must contain a candidates list")

    by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        slide_id = str(candidate.get("slide_id", ""))
        candidate_id = str(candidate.get("candidate_id", ""))
        if slide_id and candidate_id:
            by_key[(slide_id, candidate_id)] = candidate

    approved_assets: list[dict[str, Any]] = []
    for slide_id, candidate_id in selected.items():
        candidate = by_key.get((slide_id, candidate_id))
        if candidate is None:
            raise ValueError(f"selection {slide_id}={candidate_id} does not match any candidate")
        if candidate.get("status", "generated") not in {"generated", "available", "approved_candidate"}:
            raise ValueError(f"candidate {slide_id}={candidate_id} is not available for approval")
        asset_path = str(candidate.get("asset_path", ""))
        if not asset_path:
            raise ValueError(f"candidate {slide_id}={candidate_id} is missing asset_path")
        if not Path(asset_path).exists():
            raise FileNotFoundError(f"approved candidate asset does not exist: {asset_path}")
        approved_assets.append(
            {
                "slide_id": slide_id,
                "selected_candidate": candidate_id,
                "asset_path": asset_path,
                "approved_by": approved_by,
                "approval_mode": approval_mode,
                "notes": notes,
                "source": str(candidate.get("source", "")),
            }
        )

    payload = {
        "report_kind": "approved_assets",
        "run_id": report.get("run_id", ""),
        "approval_status": "approved" if approved_assets else "empty",
        "approved_assets": approved_assets,
        "rejected_assets": [],
        "regeneration_requests": [],
    }
    _write_json(output, payload)
    return payload


def apply_approved_assets(
    *,
    deck_path: Path,
    approved_assets_path: Path,
    output: Path,
    report_output: Path | None = None,
) -> dict[str, Any]:
    deck = _load_json(deck_path)
    approved = _load_json(approved_assets_path)
    slides = deck.get("slides", [])
    if not isinstance(slides, list):
        raise ValueError("deck JSON must contain a slides list")
    approved_assets = approved.get("approved_assets", [])
    if not isinstance(approved_assets, list):
        raise ValueError("approved-assets JSON must contain an approved_assets list")

    by_slide: dict[str, dict[str, Any]] = {}
    for asset in approved_assets:
        if not isinstance(asset, dict):
            continue
        slide_id = str(asset.get("slide_id", ""))
        asset_path = str(asset.get("asset_path", ""))
        if not slide_id or not asset_path:
            raise ValueError("each approved asset must include slide_id and asset_path")
        if not Path(asset_path).exists():
            raise FileNotFoundError(f"approved asset does not exist: {asset_path}")
        by_slide[slide_id] = asset

    applied_slide_ids: list[str] = []
    for slide in slides:
        if not isinstance(slide, dict):
            continue
        slide_id = str(slide.get("slide_id", ""))
        if slide_id in by_slide:
            slide["asset_path"] = str(by_slide[slide_id]["asset_path"])
            applied_slide_ids.append(slide_id)

    unmatched = sorted(set(by_slide) - set(applied_slide_ids))
    _write_json(output, deck)
    report = {
        "report_kind": "approved_asset_application",
        "run_id": approved.get("run_id", ""),
        "deck_input": str(deck_path),
        "approved_assets_input": str(approved_assets_path),
        "deck_output": str(output),
        "applied_asset_count": len(applied_slide_ids),
        "applied_slide_ids": applied_slide_ids,
        "unmatched_approved_slide_ids": unmatched,
    }
    if report_output:
        _write_json(report_output, report)
    return report
