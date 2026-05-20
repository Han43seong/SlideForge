from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any


DEFAULT_SUMMARY_NAME = "run-summary.json"


@dataclass
class EvidenceSummary:
    run_dir: Path
    artifacts: dict[str, str] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)
    sections: dict[str, dict[str, Any]] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    next_actions: list[str] = field(default_factory=list)
    status: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        return {
            "report_kind": "run_evidence_summary",
            "status": self.status,
            "run_dir": self.run_dir.as_posix(),
            "artifacts": dict(sorted(self.artifacts.items())),
            "counts": dict(sorted(self.counts.items())),
            "sections": self.sections,
            "blockers": self.blockers,
            "warnings": self.warnings,
            "next_actions": self.next_actions,
        }


def summarize_run(run_dir: str | Path) -> dict[str, Any]:
    root = Path(run_dir)
    summary = EvidenceSummary(run_dir=root)

    if not root.exists():
        summary.status = "blocked"
        summary.blockers.append("run_dir_missing: run directory does not exist")
        summary.next_actions.append("Create or point --run-dir at a SlideForge run directory.")
        return summary.to_dict()
    if not root.is_dir():
        summary.status = "blocked"
        summary.blockers.append("run_dir_not_directory: --run-dir is not a directory")
        summary.next_actions.append("Point --run-dir at a directory containing run artifacts.")
        return summary.to_dict()

    _summarize_core_artifacts(root, summary)
    _summarize_browser(root, summary)
    _summarize_pptx(root, summary)
    _summarize_comfyui(root, summary)
    _summarize_fidelity(root, summary)
    _finalize(summary)
    return summary.to_dict()


def write_evidence_summary(
    run_dir: str | Path,
    output: str | Path | None = None,
    markdown_output: str | Path | None = None,
) -> dict[str, Any]:
    root = Path(run_dir)
    payload = summarize_run(root)
    output_path = Path(output) if output is not None else root / DEFAULT_SUMMARY_NAME
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if markdown_output is not None:
        markdown_path = Path(markdown_output)
        markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown_path.write_text(render_markdown_summary(payload), encoding="utf-8")
    return payload


def render_markdown_summary(summary: dict[str, Any]) -> str:
    sections = summary.get("sections", {})
    lines = [
        "# SlideForge run evidence summary",
        "",
        f"- Run directory: `{summary.get('run_dir', '')}`",
        f"- Status: **{summary.get('status', 'pending')}**",
        "",
        "## HTML",
        "",
        _section_line(sections.get("html", {})),
        "",
        "## Browser capture",
        "",
        _section_line(sections.get("browser_capture", {})),
        "",
        "## PPTX",
        "",
        _section_line(sections.get("pptx", {})),
        "",
        "## ComfyUI",
        "",
        _section_line(sections.get("comfyui", {})),
        "",
        "## Fidelity",
        "",
        _section_line(sections.get("fidelity", {})),
        "",
        "## Blockers",
        "",
        *_bullet_lines(summary.get("blockers", []), empty="- None recorded."),
        "",
        "## Warnings",
        "",
        *_bullet_lines(summary.get("warnings", []), empty="- None recorded."),
        "",
        "## Next actions",
        "",
        *_bullet_lines(summary.get("next_actions", []), empty="- No next action recorded."),
    ]
    return "\n".join(lines) + "\n"


def _section_line(section: dict[str, Any]) -> str:
    if not section:
        return "- Status: `pending`"
    parts = [f"- Status: `{section.get('status', 'pending')}`"]
    for key in ("claim", "path", "screenshots", "slide_count", "generated_this_run", "renderer_status", "generated_assets", "pending_assets", "total"):
        if key in section:
            parts.append(f"  - {key}: `{section[key]}`")
    return "\n".join(parts)


def _bullet_lines(items: list[Any], *, empty: str) -> list[str]:
    if not items:
        return [empty]
    return [f"- {item}" for item in items]


def _summarize_core_artifacts(root: Path, summary: EvidenceSummary) -> None:
    for name in ("manifest.json", "evidence-index.md", "deck.json", "deck.html"):
        path = root / name
        if path.exists():
            summary.artifacts[name] = _rel(path, root)

    deck_json = root / "deck.json"
    deck_html = root / "deck.html"
    html_status = "available" if deck_html.exists() else "pending"
    if deck_json.exists():
        raw = _read_json(deck_json, summary, "deck.json")
        if isinstance(raw, dict):
            slides = raw.get("slides", [])
            if isinstance(slides, list):
                summary.counts["deck_json_slides"] = len(slides)
    if deck_html.exists():
        summary.sections["html"] = {
            "status": html_status,
            "path": _rel(deck_html, root),
            "claim": "deck_html_available_static_artifact",
        }
    elif deck_json.exists():
        summary.sections["html"] = {"status": "pending", "claim": "deck_json_available_but_deck_html_missing"}
        summary.warnings.append("html_pending: deck.json exists but deck.html was not found")
    else:
        summary.sections["html"] = {"status": "missing", "claim": "no_deck_html_or_deck_json_found"}
        summary.blockers.append("html_missing: no deck.html or deck.json found in run directory")


def _summarize_browser(root: Path, summary: EvidenceSummary) -> None:
    plan = root / "browser-regression-plan.json"
    if plan.exists():
        summary.artifacts["browser-regression-plan.json"] = _rel(plan, root)

    report = _first_existing(root, ["browser-capture/browser-regression-report.json", "browser-regression-report.json"])
    if report is None:
        status = "not_captured" if plan.exists() else "pending"
        summary.sections["browser_capture"] = {
            "status": status,
            "claim": "browser_plan_present_without_real_capture_report" if plan.exists() else "no_browser_capture_artifacts_found",
        }
        summary.warnings.append("browser_capture_not_captured: real browser screenshot evidence is missing")
        summary.next_actions.append("Run capture-screenshots to create browser-capture/browser-regression-report.json.")
        return

    summary.artifacts["browser-regression-report.json"] = _rel(report, root)
    raw = _read_json(report, summary, _rel(report, root))
    screenshots = raw.get("screenshots", []) if isinstance(raw, dict) else []
    capture = raw.get("screenshot_capture", {}) if isinstance(raw, dict) else {}
    capture_status = capture.get("status") if isinstance(capture, dict) else raw.get("status") if isinstance(raw, dict) else None
    screenshot_count = len(screenshots) if isinstance(screenshots, list) else 0
    summary.counts["browser_screenshots"] = screenshot_count
    if capture_status == "captured":
        status = "captured"
    elif capture_status in {"failed", "unavailable"}:
        status = "unavailable"
        reason = capture.get("reason") if isinstance(capture, dict) else "browser capture did not complete"
        summary.blockers.append(f"browser_capture_unavailable: {reason}")
    else:
        status = "pending"
        summary.warnings.append("browser_capture_pending: browser report does not record captured screenshots")
    summary.sections["browser_capture"] = {
        "status": status,
        "path": _rel(report, root),
        "screenshots": screenshot_count,
        "slide_count": raw.get("slide_count_detected") if isinstance(raw, dict) else 0,
        "claim": "real_browser_screenshot_evidence_recorded" if status == "captured" else "browser_report_present_without_captured_status",
    }


def _summarize_pptx(root: Path, summary: EvidenceSummary) -> None:
    section: dict[str, Any] = {"status": "pending", "claim": "no_pptx_artifacts_found"}
    gate = root / "pptx-delivery-gate.json"
    export = root / "pptx-export-report.json"
    if gate.exists():
        summary.artifacts["pptx-delivery-gate.json"] = _rel(gate, root)
        raw_gate = _read_json(gate, summary, "pptx-delivery-gate.json")
        if isinstance(raw_gate, dict):
            section = {
                "status": raw_gate.get("current_status", "pending"),
                "path": _rel(gate, root),
                "claim": raw_gate.get("validation_claim", "pptx_delivery_gate_present"),
            }
            for blocker in _string_list(raw_gate.get("blockers")):
                summary.warnings.append(f"pptx_gate_pending: {blocker}")
    if export.exists():
        summary.artifacts["pptx-export-report.json"] = _rel(export, root)
        raw = _read_json(export, summary, "pptx-export-report.json")
        if isinstance(raw, dict):
            generated_this_run = bool(raw.get("generated_this_run"))
            renderer = raw.get("renderer_evidence", {})
            renderer_status = renderer.get("status") if isinstance(renderer, dict) else None
            output_exists = bool(raw.get("output_exists"))
            status = raw.get("status", "pending")
            section = {
                "status": status,
                "path": _rel(export, root),
                "claim": raw.get("generation_claim", "pptx_export_report_present"),
                "generated_this_run": generated_this_run,
                "renderer_status": renderer_status or "unknown",
                "slide_count": raw.get("slide_count_generated", 0),
            }
            summary.counts["pptx_slides_generated"] = int(raw.get("slide_count_generated") or 0)
            blockers = _string_list(raw.get("blockers"))
            for blocker in blockers:
                if "stale_output" in blocker or "generated by this run" in blocker:
                    summary.blockers.append(f"pptx_stale_output: {blocker}")
                else:
                    summary.warnings.append(f"pptx_pending: {blocker}")
            if not generated_this_run or not output_exists:
                summary.warnings.append("pptx_not_final_visual_evidence: PPTX output was not generated this run or output evidence is missing")
            if renderer_status != "available":
                summary.warnings.append("pptx_renderer_evidence_missing: no real PPTX render evidence recorded")
    summary.sections["pptx"] = section


def _summarize_comfyui(root: Path, summary: EvidenceSummary) -> None:
    report = root / "comfyui-handoff-report.json"
    if not report.exists():
        summary.sections["comfyui"] = {"status": "pending", "claim": "no_comfyui_handoff_report_found"}
        return
    summary.artifacts["comfyui-handoff-report.json"] = _rel(report, root)
    raw = _read_json(report, summary, "comfyui-handoff-report.json")
    if not isinstance(raw, dict):
        summary.sections["comfyui"] = {"status": "unavailable", "path": _rel(report, root), "claim": "invalid_comfyui_report"}
        return
    generated = raw.get("generated_assets", [])
    pending = raw.get("pending_assets", [])
    failed = raw.get("failed_assets", [])
    generated_count = len(generated) if isinstance(generated, list) else 0
    pending_count = len(pending) if isinstance(pending, list) else 0
    failed_count = len(failed) if isinstance(failed, list) else 0
    summary.counts["comfyui_generated_assets"] = generated_count
    summary.counts["comfyui_pending_assets"] = pending_count
    summary.counts["comfyui_failed_assets"] = failed_count
    status = raw.get("status", "pending")
    summary.sections["comfyui"] = {
        "status": status,
        "path": _rel(report, root),
        "generated_assets": generated_count,
        "pending_assets": pending_count,
        "claim": "generated_assets_exist" if generated_count else "handoff_or_pending_assets_only_no_generated_image_claim",
    }
    for blocker in _string_list(raw.get("blockers")):
        summary.warnings.append(f"comfyui_pending: {blocker}")
    if pending_count:
        summary.next_actions.append("Generate or attach ComfyUI assets if this run requires external imagery.")


def _summarize_fidelity(root: Path, summary: EvidenceSummary) -> None:
    candidates = [
        path
        for path in root.glob("*.json")
        if path.name not in {DEFAULT_SUMMARY_NAME} and ("fidelity" in path.name.lower() or "score" in path.name.lower())
    ]
    if not candidates:
        candidates = [path for path in root.glob("*fidelity*.md")]
    if not candidates:
        summary.sections["fidelity"] = {"status": "pending", "claim": "no_fidelity_score_or_report_found"}
        summary.warnings.append("fidelity_pending: no fidelity score/report artifact found")
        return
    path = sorted(candidates)[0]
    summary.artifacts["fidelity-report"] = _rel(path, root)
    section: dict[str, Any] = {"status": "available", "path": _rel(path, root), "claim": "fidelity_artifact_detected"}
    if path.suffix == ".json":
        raw = _read_json(path, summary, _rel(path, root))
        if isinstance(raw, dict):
            if "total" in raw:
                section["total"] = raw["total"]
            if "rating" in raw:
                section["rating"] = raw["rating"]
    summary.sections["fidelity"] = section


def _finalize(summary: EvidenceSummary) -> None:
    browser_status = summary.sections.get("browser_capture", {}).get("status")
    html_status = summary.sections.get("html", {}).get("status")
    if summary.blockers:
        summary.status = "blocked"
    elif browser_status != "captured" and html_status == "available":
        summary.status = "needs_visual_evidence"
    elif summary.warnings:
        summary.status = "ready_with_warnings"
    else:
        summary.status = "ready"

    if summary.status == "blocked":
        summary.next_actions.append("Resolve blockers, then regenerate the run evidence summary.")
    if summary.status == "needs_visual_evidence":
        summary.next_actions.append("Capture real browser screenshots before claiming visual readiness.")
    if summary.status == "ready_with_warnings":
        summary.next_actions.append("Review warnings before operator delivery.")
    summary.next_actions = _dedupe(summary.next_actions)
    summary.warnings = _dedupe(summary.warnings)
    summary.blockers = _dedupe(summary.blockers)


def _first_existing(root: Path, names: list[str]) -> Path | None:
    for name in names:
        path = root / name
        if path.exists():
            return path
    return None


def _read_json(path: Path, summary: EvidenceSummary, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - evidence summary records malformed artifacts instead of crashing
        summary.warnings.append(f"artifact_unreadable: {label}: {type(exc).__name__}: {exc}")
        return None


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [value]
    return []


def _rel(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
