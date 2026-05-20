from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import stat
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


MANIFEST_ENTRY_NAME = "evidence-pack-manifest.json"
SUMMARY_NAME = "run-summary.json"


@dataclass(frozen=True)
class ArtifactEntry:
    relative_path: str
    size_bytes: int
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "size_bytes": self.size_bytes,
            "sha256": self.sha256,
        }


@dataclass(frozen=True)
class EvidencePackResult:
    output: Path
    manifest: dict[str, Any]


def build_evidence_pack(
    run_dir: str | Path,
    output: str | Path,
    manifest_output: str | Path | None = None,
) -> EvidencePackResult:
    """Package an existing run directory into a zip evidence pack.

    This function only packages regular files that live directly inside ``run_dir``.
    Symlinks are skipped rather than followed so a run cannot leak files outside
    its tree. The manifest preserves any existing run-summary status honestly;
    this command packages evidence, it does not generate missing evidence.
    """

    run_root = Path(run_dir)
    output_path = Path(output)
    manifest_output_path = Path(manifest_output) if manifest_output is not None else None
    _validate_paths(run_root, output_path, manifest_output_path)

    resolved_run_root = run_root.resolve()
    skipped: list[dict[str, str]] = []
    artifacts = _collect_artifacts(resolved_run_root, skipped)
    summary = _load_summary(resolved_run_root / SUMMARY_NAME)
    generated_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    manifest: dict[str, Any] = {
        "report_kind": "evidence_pack_report",
        "run_dir": run_root.as_posix(),
        "output_path": output_path.as_posix(),
        "generated_at": generated_at,
        "manifest_entry": MANIFEST_ENTRY_NAME,
        "artifact_count": len(artifacts),
        "artifacts": [artifact.to_dict() for artifact in artifacts],
        "summary_status": summary["status"],
        "warnings": summary["warnings"],
        "blockers": summary["blockers"],
        "missing_external_evidence": summary["missing_external_evidence"],
        "excluded_patterns": ["symlinks", "non_regular_files", "evidence_pack_output_inside_run_dir"],
        "policy_notes": [
            "Evidence packs archive existing artifacts only; they do not create browser, PPTX, ComfyUI, or fidelity evidence.",
            "Only regular files inside run_dir are included; symlinks are skipped and never followed.",
        ],
    }
    if skipped:
        manifest["skipped_artifacts"] = skipped
        manifest["warnings"] = [
            *manifest["warnings"],
            "skipped_artifacts_present: one or more symlinks or non-regular files were not packaged",
        ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8") + b"\n"
    with ZipFile(output_path, "w", compression=ZIP_DEFLATED) as archive:
        for artifact in artifacts:
            source = resolved_run_root / artifact.relative_path
            archive.write(source, artifact.relative_path)
        info = ZipInfo(MANIFEST_ENTRY_NAME)
        info.compress_type = ZIP_DEFLATED
        archive.writestr(info, manifest_bytes)

    if manifest_output_path is not None:
        manifest_output_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_output_path.write_bytes(manifest_bytes)

    return EvidencePackResult(output=output_path, manifest=manifest)


def _validate_paths(run_root: Path, output_path: Path, manifest_output_path: Path | None) -> None:
    if not run_root.exists():
        raise ValueError(f"run_dir does not exist: {run_root}")
    if not run_root.is_dir():
        raise ValueError(f"run_dir is not a directory: {run_root}")

    resolved_run_root = run_root.resolve()
    if _is_inside(output_path.resolve(), resolved_run_root):
        raise ValueError("output path must be outside run_dir to avoid recursive evidence-pack packaging")
    if manifest_output_path is not None and _is_inside(manifest_output_path.resolve(), resolved_run_root):
        raise ValueError("manifest-output path must be outside run_dir to avoid modifying the packaged run directory")


def _collect_artifacts(run_root: Path, skipped: list[dict[str, str]]) -> list[ArtifactEntry]:
    entries: list[ArtifactEntry] = []
    for path in sorted(run_root.rglob("*"), key=lambda item: item.relative_to(run_root).as_posix()):
        relative = path.relative_to(run_root).as_posix()
        try:
            mode = path.lstat().st_mode
        except OSError as exc:
            skipped.append({"relative_path": relative, "reason": f"lstat_failed:{type(exc).__name__}"})
            continue
        if stat.S_ISLNK(mode):
            skipped.append({"relative_path": relative, "reason": "symlink_skipped_not_followed"})
            continue
        if not stat.S_ISREG(mode):
            if not stat.S_ISDIR(mode):
                skipped.append({"relative_path": relative, "reason": "non_regular_file_skipped"})
            continue
        entries.append(_artifact_entry(path, relative))
    return entries


def _artifact_entry(path: Path, relative_path: str) -> ArtifactEntry:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(chunk)
            digest.update(chunk)
    return ArtifactEntry(relative_path=relative_path, size_bytes=size, sha256=digest.hexdigest())


def _load_summary(summary_path: Path) -> dict[str, Any]:
    if not summary_path.exists():
        return {
            "status": "pending_missing_run_summary",
            "warnings": ["run_summary_missing: run-summary.json was not found; evidence status was not upgraded"],
            "blockers": [],
            "missing_external_evidence": ["run-summary.json"],
        }
    try:
        raw = json.loads(summary_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001 - manifest should record malformed summary honestly
        return {
            "status": "blocked_invalid_run_summary",
            "warnings": [f"run_summary_unreadable: {type(exc).__name__}: {exc}"],
            "blockers": ["run-summary.json could not be parsed"],
            "missing_external_evidence": [],
        }
    if not isinstance(raw, dict):
        return {
            "status": "blocked_invalid_run_summary",
            "warnings": ["run_summary_invalid: run-summary.json is not a JSON object"],
            "blockers": ["run-summary.json is not a JSON object"],
            "missing_external_evidence": [],
        }
    return {
        "status": str(raw.get("status") or "pending"),
        "warnings": _string_list(raw.get("warnings")),
        "blockers": _string_list(raw.get("blockers")),
        "missing_external_evidence": _summary_missing_external_evidence(raw),
    }


def _summary_missing_external_evidence(summary: dict[str, Any]) -> list[str]:
    explicit = summary.get("missing_external_evidence")
    if explicit is not None:
        return _string_list(explicit)

    missing: list[str] = []
    sections = summary.get("sections")
    if isinstance(sections, dict):
        browser = sections.get("browser_capture")
        if isinstance(browser, dict) and browser.get("status") != "captured":
            missing.append("browser_capture")
        pptx = sections.get("pptx")
        if isinstance(pptx, dict):
            claim = str(pptx.get("claim") or "")
            if "no_pptx_export" in claim or pptx.get("status") in {"pending", "unavailable"}:
                missing.append("pptx_render_or_export_evidence")
        comfyui = sections.get("comfyui")
        if isinstance(comfyui, dict) and comfyui.get("status") not in {"generated", "available", "complete"}:
            missing.append("comfyui_generated_asset_evidence")
        fidelity = sections.get("fidelity")
        if isinstance(fidelity, dict) and fidelity.get("status") != "available":
            missing.append("fidelity_score_or_report")

    status = str(summary.get("status") or "")
    if not missing and status in {"needs_visual_evidence", "pending", "blocked"}:
        missing.append(status)
    return _dedupe(missing)


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str):
        return [value]
    return []


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _is_inside(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False
