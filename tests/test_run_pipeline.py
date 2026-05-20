import json
from pathlib import Path

import pytest

from slideforge.cli import main
from slideforge.run_pipeline import run_local
from slideforge.source_pipeline import run_source_local


def _write_deck(path: Path) -> None:
    path.write_text(
        json.dumps(
            {
                "title": "폐쇄망 LLM 전략",
                "slides": [
                    {
                        "slide_id": "s1",
                        "title": "폐쇄망 LLM 전략",
                        "subtitle": "의사결정용",
                        "bullets": ["GPU", "RAG"],
                        "archetype": "cover",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )


def test_run_local_api_writes_run_artifacts_and_summary(tmp_path):
    deck_path = tmp_path / "deck.json"
    runs_dir = tmp_path / "runs"
    _write_deck(deck_path)

    report = run_local(deck=deck_path, runs_dir=runs_dir, run_id="local-api")

    run_dir = runs_dir / "local-api"
    assert report.run_dir == run_dir
    assert report.summary_status == "needs_visual_evidence"
    assert (run_dir / "deck.html").exists()
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "evidence-index.md").exists()
    assert (run_dir / "run-summary.json").exists()
    assert (run_dir / "run-summary.md").exists()
    assert run_dir / "deck.html" in report.generated_artifacts
    summary = json.loads((run_dir / "run-summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "needs_visual_evidence"
    assert summary["sections"]["browser_capture"]["status"] == "not_captured"
    assert any("browser_capture_not_captured" in warning for warning in summary["warnings"])


def test_cli_run_local_writes_outputs_and_honest_summary(tmp_path, capsys):
    deck_path = tmp_path / "deck.json"
    runs_dir = tmp_path / "runs"
    _write_deck(deck_path)

    exit_code = main(["run-local", "--deck", str(deck_path), "--runs-dir", str(runs_dir), "--run-id", "local-cli"])

    assert exit_code == 0
    run_dir = runs_dir / "local-cli"
    assert (run_dir / "deck.html").exists()
    assert (run_dir / "manifest.json").exists()
    assert (run_dir / "run-summary.json").exists()
    assert (run_dir / "run-summary.md").exists()
    summary = json.loads((run_dir / "run-summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "needs_visual_evidence"
    report = json.loads(capsys.readouterr().out)
    assert report["summary_status"] == "needs_visual_evidence"
    assert any(path.endswith("run-summary.md") for path in report["generated_artifacts"])


def test_run_local_missing_deck_fails_without_creating_runs_dir(tmp_path):
    runs_dir = tmp_path / "runs"

    with pytest.raises(FileNotFoundError):
        run_local(deck=tmp_path / "missing.json", runs_dir=runs_dir, run_id="missing")

    assert not runs_dir.exists()


def test_run_local_rejects_path_like_run_id_before_creating_directories(tmp_path):
    deck_path = tmp_path / "deck.json"
    runs_dir = tmp_path / "runs"
    _write_deck(deck_path)

    with pytest.raises(ValueError, match="run_id"):
        run_local(deck=deck_path, runs_dir=runs_dir, run_id="../escape")

    assert not runs_dir.exists()


def test_cli_run_local_missing_deck_fails_without_creating_runs_dir(tmp_path):
    runs_dir = tmp_path / "runs"

    with pytest.raises(FileNotFoundError):
        main([
            "run-local",
            "--deck",
            str(tmp_path / "missing.json"),
            "--runs-dir",
            str(runs_dir),
            "--run-id",
            "missing-cli",
        ])

    assert not runs_dir.exists()


def _write_source(path: Path) -> None:
    path.write_text(
        """# Operating model\n- Timeline: Phase 1 pilot\n- Phase 2 rollout\n\n## KPI scorecard\n- Latency: under 2s\n- Quality: reviewed weekly\n""",
        encoding="utf-8",
    )


def test_run_source_local_api_writes_sections_deck_run_and_honest_summary(tmp_path):
    source_path = tmp_path / "source.md"
    runs_dir = tmp_path / "runs"
    _write_source(source_path)

    report = run_source_local(
        source=source_path,
        title="Source Local API",
        runs_dir=runs_dir,
        run_id="source-api",
    )

    run_dir = runs_dir / "source-api"
    sections_path = runs_dir / "source-api-input" / "sections.json"
    deck_path = runs_dir / "source-api-input" / "deck.json"
    assert report.run_dir == run_dir
    assert report.sections_path == sections_path
    assert report.deck_input_path == deck_path
    assert sections_path.exists()
    assert deck_path.exists()
    assert (run_dir / "deck.html").exists()
    assert (run_dir / "run-summary.json").exists()
    assert report.summary_status == "needs_visual_evidence"
    assert report.blockers == []
    assert "real_browser_screenshot_capture" in report.missing_external_evidence
    assert "pptx_export_or_render_evidence" in report.missing_external_evidence
    assert "comfyui_generated_asset_evidence" in report.missing_external_evidence
    assert "fidelity_score_or_report" in report.missing_external_evidence
    assert any("browser_capture_not_captured" in warning for warning in report.warnings)


def test_cli_run_source_local_prints_compact_report_and_preserves_smoke_status(tmp_path, capsys):
    source_path = tmp_path / "source.md"
    runs_dir = tmp_path / "runs"
    handoff_dir = tmp_path / "handoff"
    _write_source(source_path)

    exit_code = main([
        "run-source-local",
        "--source",
        str(source_path),
        "--title",
        "Source Local CLI",
        "--runs-dir",
        str(runs_dir),
        "--run-id",
        "source-cli",
        "--input-output-dir",
        str(handoff_dir),
    ])

    assert exit_code == 0
    report = json.loads(capsys.readouterr().out)
    assert report["report_kind"] == "source_local_run_report"
    assert report["summary_status"] == "needs_visual_evidence"
    assert report["blockers"] == []
    assert report["sections_path"] == (handoff_dir / "sections.json").as_posix()
    assert report["deck_input_path"] == (handoff_dir / "deck.json").as_posix()
    assert any(path.endswith("run-summary.json") for path in report["generated_artifacts"])
    summary = json.loads((runs_dir / "source-cli" / "run-summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "needs_visual_evidence"
    assert any("pptx_gate_pending" in warning for warning in summary["warnings"])
    assert any("fidelity_pending" in warning for warning in summary["warnings"])


def test_run_source_local_empty_source_fails_before_creating_run_artifacts(tmp_path):
    source_path = tmp_path / "empty.md"
    runs_dir = tmp_path / "runs"
    source_path.write_text("\n  \n", encoding="utf-8")

    with pytest.raises(ValueError, match="source"):
        run_source_local(source=source_path, title="Empty", runs_dir=runs_dir, run_id="empty-source")

    assert not runs_dir.exists()


def test_run_source_local_rejects_path_like_run_id_before_creating_artifacts(tmp_path):
    source_path = tmp_path / "source.md"
    runs_dir = tmp_path / "runs"
    _write_source(source_path)

    with pytest.raises(ValueError, match="run_id"):
        run_source_local(source=source_path, title="Bad", runs_dir=runs_dir, run_id="../escape")

    assert not runs_dir.exists()


def test_run_source_local_default_intent_reaches_sections_and_deck(tmp_path):
    source_path = tmp_path / "source.md"
    runs_dir = tmp_path / "runs"
    source_path.write_text("# Plain update\n- No keyword alias here\n", encoding="utf-8")

    report = run_source_local(
        source=source_path,
        title="Default Intent",
        runs_dir=runs_dir,
        run_id="default-intent",
        default_intent="explainer",
    )

    sections = json.loads(report.sections_path.read_text(encoding="utf-8"))
    deck = json.loads(report.deck_input_path.read_text(encoding="utf-8"))
    assert sections[0]["intent"] == "explainer"
    assert deck["slides"][0]["subtitle"] == "Intent: explainer"
    assert deck["slides"][0]["archetype"] == "text_explainer"
