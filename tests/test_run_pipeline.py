import json
from pathlib import Path

import pytest

from slideforge.cli import main
from slideforge.run_pipeline import run_local


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
