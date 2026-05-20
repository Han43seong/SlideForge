import json
from pathlib import Path
from zipfile import ZipFile

import pytest

from slideforge.evidence_pack import MANIFEST_ENTRY_NAME, build_evidence_pack


def _write_smoke_run(run_dir: Path) -> None:
    run_dir.mkdir(parents=True)
    (run_dir / "deck.html").write_text("<!doctype html><title>deck</title>", encoding="utf-8")
    (run_dir / "deck.json").write_text(json.dumps({"title": "Deck", "slides": [{"slide_id": "s1"}]}), encoding="utf-8")
    (run_dir / "run-summary.json").write_text(
        json.dumps(
            {
                "report_kind": "run_evidence_summary",
                "status": "needs_visual_evidence",
                "warnings": ["browser_capture_not_captured: real browser screenshot evidence is missing"],
                "blockers": [],
                "missing_external_evidence": ["browser_capture", "pptx_render_or_export_evidence"],
                "sections": {
                    "browser_capture": {"status": "not_captured"},
                    "pptx": {"status": "unavailable"},
                },
            }
        ),
        encoding="utf-8",
    )


def test_build_evidence_pack_writes_zip_manifest_sidecar_and_hashes(tmp_path):
    run_dir = tmp_path / "runs" / "smoke"
    _write_smoke_run(run_dir)
    output = tmp_path / "smoke-evidence-pack.zip"
    sidecar = tmp_path / "smoke-evidence-pack-manifest.json"

    result = build_evidence_pack(run_dir=run_dir, output=output, manifest_output=sidecar)

    assert output.exists()
    assert sidecar.exists()
    assert result.manifest["report_kind"] == "evidence_pack_report"
    assert result.manifest["summary_status"] == "needs_visual_evidence"
    assert result.manifest["missing_external_evidence"] == ["browser_capture", "pptx_render_or_export_evidence"]
    artifacts = {item["relative_path"]: item for item in result.manifest["artifacts"]}
    assert set(artifacts) == {"deck.html", "deck.json", "run-summary.json"}
    assert artifacts["deck.html"]["size_bytes"] > 0
    assert len(artifacts["deck.html"]["sha256"]) == 64

    with ZipFile(output) as archive:
        names = archive.namelist()
        assert names == ["deck.html", "deck.json", "run-summary.json", MANIFEST_ENTRY_NAME]
        embedded = json.loads(archive.read(MANIFEST_ENTRY_NAME).decode("utf-8"))
    assert embedded == json.loads(sidecar.read_text(encoding="utf-8"))
    assert embedded["summary_status"] == "needs_visual_evidence"


def test_build_evidence_pack_preserves_run_summary_values(tmp_path):
    run_dir = tmp_path / "run"
    _write_smoke_run(run_dir)
    summary = json.loads((run_dir / "run-summary.json").read_text(encoding="utf-8"))
    summary["blockers"] = ["operator_blocker"]
    summary["warnings"].append("fidelity_pending: no fidelity score/report artifact found")
    (run_dir / "run-summary.json").write_text(json.dumps(summary), encoding="utf-8")

    manifest = build_evidence_pack(run_dir, tmp_path / "pack.zip").manifest

    assert manifest["summary_status"] == "needs_visual_evidence"
    assert manifest["warnings"] == summary["warnings"]
    assert manifest["blockers"] == ["operator_blocker"]
    assert manifest["missing_external_evidence"] == ["browser_capture", "pptx_render_or_export_evidence"]


def test_build_evidence_pack_reports_missing_summary_honestly(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "deck.html").write_text("<!doctype html>", encoding="utf-8")

    manifest = build_evidence_pack(run_dir, tmp_path / "pack.zip").manifest

    assert manifest["summary_status"] == "pending_missing_run_summary"
    assert "run-summary.json" in manifest["missing_external_evidence"]
    assert manifest["warnings"] == ["run_summary_missing: run-summary.json was not found; evidence status was not upgraded"]


def test_build_evidence_pack_rejects_missing_and_non_directory_run_dir(tmp_path):
    with pytest.raises(ValueError, match="does not exist"):
        build_evidence_pack(tmp_path / "missing", tmp_path / "pack.zip")

    not_dir = tmp_path / "not-dir"
    not_dir.write_text("not a directory", encoding="utf-8")
    with pytest.raises(ValueError, match="not a directory"):
        build_evidence_pack(not_dir, tmp_path / "pack.zip")


def test_build_evidence_pack_skips_symlinks_without_escaping_run_dir(tmp_path):
    run_dir = tmp_path / "run"
    _write_smoke_run(run_dir)
    outside = tmp_path / "outside-secret.txt"
    outside.write_text("do not package", encoding="utf-8")
    (run_dir / "outside-link.txt").symlink_to(outside)

    manifest = build_evidence_pack(run_dir, tmp_path / "pack.zip").manifest

    artifacts = {item["relative_path"] for item in manifest["artifacts"]}
    assert "outside-link.txt" not in artifacts
    assert manifest["skipped_artifacts"] == [{"relative_path": "outside-link.txt", "reason": "symlink_skipped_not_followed"}]
    with ZipFile(tmp_path / "pack.zip") as archive:
        assert "outside-link.txt" not in archive.namelist()
        assert b"do not package" not in archive.read(MANIFEST_ENTRY_NAME)


def test_build_evidence_pack_rejects_output_inside_run_dir(tmp_path):
    run_dir = tmp_path / "run"
    _write_smoke_run(run_dir)

    with pytest.raises(ValueError, match="outside run_dir"):
        build_evidence_pack(run_dir, run_dir / "pack.zip")
    with pytest.raises(ValueError, match="manifest-output"):
        build_evidence_pack(run_dir, tmp_path / "pack.zip", manifest_output=run_dir / "manifest.json")
