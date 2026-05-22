from __future__ import annotations

import json
from collections import defaultdict
from html import escape
from pathlib import Path
from typing import Any

VALID_APPROVAL_MODES = {"explicit_user", "jarvis_recommended", "autonomous"}


def _parse_candidate_spec(spec: str) -> dict[str, Any]:
    """Parse slide_id=candidate_id:path[:source[:notes]] candidate specs."""
    if "=" not in spec:
        raise ValueError(f"candidate must use slide_id=candidate_id:path[:source[:notes]]: {spec}")
    slide_id, rest = spec.split("=", 1)
    parts = rest.split(":", 3)
    if len(parts) < 2:
        raise ValueError(f"candidate must include candidate_id and asset path: {spec}")
    candidate_id, asset_path = parts[0].strip(), parts[1].strip()
    source = parts[2].strip() if len(parts) >= 3 and parts[2].strip() else "manual_file"
    notes = parts[3].strip() if len(parts) >= 4 else ""
    slide_id = slide_id.strip()
    if not slide_id or not candidate_id or not asset_path:
        raise ValueError(f"candidate must include non-empty slide_id, candidate_id, and asset path: {spec}")
    if not Path(asset_path).exists():
        raise FileNotFoundError(f"candidate asset does not exist: {asset_path}")
    return {
        "slide_id": slide_id,
        "candidate_id": candidate_id,
        "asset_path": asset_path,
        "source": source,
        "status": "generated",
        "notes": notes,
    }


def write_asset_candidates_report(
    *,
    run_id: str,
    candidate_specs: list[str],
    output: Path,
) -> dict[str, Any]:
    if not candidate_specs:
        raise ValueError("at least one --candidate is required")
    candidates = [_parse_candidate_spec(spec) for spec in candidate_specs]
    payload = {
        "report_kind": "asset_generation_report",
        "run_id": run_id,
        "candidate_count": len(candidates),
        "candidates": candidates,
    }
    _write_json(output, payload)
    return payload


def write_asset_review_board(
    *,
    candidates_path: Path,
    deck_path: Path | None,
    output_html: Path,
    output_md: Path | None = None,
    recommended: str = "",
) -> dict[str, Any]:
    report = _load_json(candidates_path)
    candidates = report.get("candidates", [])
    if not isinstance(candidates, list):
        raise ValueError("candidate report must contain a candidates list")
    deck = _load_json(deck_path) if deck_path else {}
    slide_titles = {
        str(slide.get("slide_id", "")): str(slide.get("title", ""))
        for slide in deck.get("slides", [])
        if isinstance(slide, dict)
    }
    recommended_by_slide = _parse_selection(recommended) if recommended else {}
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidates:
        if isinstance(candidate, dict):
            slide_id = str(candidate.get("slide_id") or candidate.get("target_slide") or candidate.get("asset_id") or "")
            grouped[slide_id].append(candidate)

    html_parts = [
        "<!doctype html>",
        "<html lang=\"en\"><head><meta charset=\"utf-8\"><title>Asset Review Board</title>",
        "<style>body{font-family:Inter,Arial,sans-serif;background:#0b1020;color:#eaf2ff;margin:32px}"
        ".slide{border:1px solid #26324f;border-radius:18px;padding:20px;margin:0 0 24px;background:#111832}"
        ".grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}"
        ".card{border:1px solid #33415f;border-radius:14px;padding:12px;background:#151f3d}"
        ".card.recommended{border-color:#38d6ff;box-shadow:0 0 0 1px #38d6ff55}"
        "img{width:100%;height:auto;border-radius:10px;background:#050914}.meta{color:#9fb0d9;font-size:13px}"
        "code{background:#050914;padding:2px 6px;border-radius:6px}</style></head><body>",
        "<h1>Asset Review Board</h1>",
        f"<p class=\"meta\">Run: {escape(str(report.get('run_id', '')))} · Candidates: {len(candidates)}</p>",
    ]
    md_parts = ["# Asset Review Board", "", f"Run: {report.get('run_id', '')}", ""]

    if not grouped:
        guidance = _empty_candidate_guidance(report)
        html_parts.extend(
            [
                "<section class=\"slide\"><h2>No candidate assets found</h2>",
                f"<p>{escape(guidance['message'])}</p>",
                "<ul>",
                *[f"<li>{escape(item)}</li>" for item in guidance["actions"]],
                "</ul></section>",
            ]
        )
        md_parts.extend(
            [
                "## No candidate assets found",
                "",
                guidance["message"],
                "",
                *[f"- {item}" for item in guidance["actions"]],
                "",
            ]
        )

    for slide_id in sorted(grouped):
        title = slide_titles.get(slide_id, "")
        heading = f"Slide {slide_id}" + (f" · {title}" if title else "")
        html_parts.append(f"<section class=\"slide\"><h2>{escape(heading)}</h2><div class=\"grid\">")
        md_parts.extend([f"## {heading}", ""])
        for candidate in grouped[slide_id]:
            candidate_id = str(candidate.get("candidate_id", ""))
            asset_path = str(candidate.get("asset_path") or candidate.get("path") or "")
            source = str(candidate.get("source", ""))
            notes = str(candidate.get("notes", ""))
            metadata = _candidate_metadata_lines(candidate)
            is_recommended = recommended_by_slide.get(slide_id) == candidate_id
            badge = " <strong>Recommended</strong>" if is_recommended else ""
            card_class = "card recommended" if is_recommended else "card"
            metadata_html = "".join(
                f"<p class=\"meta\">{escape(label)}: {escape(value)}</p>" for label, value in metadata
            )
            html_parts.append(
                f"<article class=\"{card_class}\"><h3>Candidate {escape(candidate_id)}{badge}</h3>"
                f"<img src=\"{escape(asset_path)}\" alt=\"Slide {escape(slide_id)} candidate {escape(candidate_id)}\">"
                f"<p class=\"meta\">Source: {escape(source)}</p>"
                f"{metadata_html}<p>{escape(notes)}</p></article>"
            )
            md_parts.extend([
                f"- Candidate {candidate_id}" + (" — Recommended" if is_recommended else ""),
                f"  - file: {asset_path}",
                f"  - source: {source}",
                *[f"  - {label}: {value}" for label, value in metadata],
                f"  - notes: {notes}",
            ])
        selection_hint = recommended or ",".join(
            f"{slide_id}={items[0].get('candidate_id', '')}" for slide_id, items in grouped.items() if items
        )
        selection_hint_html = escape(selection_hint, quote=False)
        html_parts.append(
            "</div>"
            f"<p>Approval command: <code>approve-assets --selection \"{selection_hint_html}\"</code></p>"
            "</section>"
        )
        md_parts.extend(["", f"Approval command: `approve-assets --selection \"{selection_hint}\"`", ""])

    html_parts.append("</body></html>")
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text("\n".join(html_parts) + "\n", encoding="utf-8")
    if output_md:
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text("\n".join(md_parts) + "\n", encoding="utf-8")
    return {
        "report_kind": "asset_review_board",
        "run_id": report.get("run_id", ""),
        "candidate_count": len(candidates),
        "slide_count": len(grouped),
        "output_html": str(output_html),
        "output_md": str(output_md) if output_md else "",
        "recommended": recommended_by_slide,
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _empty_candidate_guidance(report: dict[str, Any]) -> dict[str, list[str] | str]:
    source = str(report.get("source", ""))
    input_dir = str(report.get("input_dir") or "manual-generated-assets")
    asset_spec_dir = str(report.get("asset_spec_dir") or "asset-specs")
    if source == "manual_openai_images":
        return {
            "message": "No manual OpenAI Images candidates were imported yet.",
            "actions": [
                f"Generate or review prompts under openai-manual-prompts/ from specs in {asset_spec_dir}.",
                f"Save downloaded ChatGPT Pro / OpenAI Images files as {input_dir}/<asset_id>/A.png, B.png, C.png.",
                "Rerun import-manual-assets, then rebuild this asset review board.",
            ],
        }
    return {
        "message": "No candidate assets are available in this asset-generation report.",
        "actions": [
            "Generate or import candidate assets, then rebuild this asset review board.",
        ],
    }


def _candidate_metadata_lines(candidate: dict[str, Any]) -> list[tuple[str, str]]:
    labels = {
        "asset_id": "Asset ID",
        "provider": "Provider",
        "generation_mode": "Generation mode",
        "prompt_file": "Prompt file",
        "license_note": "License note",
    }
    lines: list[tuple[str, str]] = []
    for key, label in labels.items():
        value = str(candidate.get(key, "")).strip()
        if value:
            lines.append((label, value))
    return lines


def _resolve_report_relative(path_text: str, report_path: Path) -> Path:
    path = Path(path_text)
    if path.is_absolute() or path.exists():
        return path
    return report_path.parent / path


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
        slide_id = str(candidate.get("slide_id") or candidate.get("target_slide") or candidate.get("asset_id") or "")
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
        asset_path = str(candidate.get("asset_path") or candidate.get("path") or "")
        if not asset_path:
            raise ValueError(f"candidate {slide_id}={candidate_id} is missing asset_path")
        resolved_asset_path = _resolve_report_relative(asset_path, candidates_path)
        if not resolved_asset_path.exists():
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
        if not _resolve_report_relative(asset_path, approved_assets_path).exists():
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
