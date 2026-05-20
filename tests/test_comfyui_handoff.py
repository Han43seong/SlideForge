import json

from slideforge.asset_brief import AssetBrief, AssetBriefSet
from slideforge.cli import main
from slideforge.comfyui_handoff import build_comfyui_handoff_report, write_comfyui_handoff_report


def _brief_set() -> AssetBriefSet:
    return AssetBriefSet(
        briefs=[
            AssetBrief(
                slide_id="s1",
                asset_type="cover_background",
                prompt="dark aurora glass technology background, no text",
                negative_prompt="text, letters, numbers, labels, watermark, logo",
                output_hint="generated-assets/s1.png",
            )
        ]
    )


def test_comfyui_handoff_report_contract_from_asset_briefs(monkeypatch, tmp_path):
    monkeypatch.setattr("slideforge.comfyui_handoff.check_comfyui_server", lambda endpoint, timeout_seconds=1.0: (True, None))

    report = build_comfyui_handoff_report(
        _brief_set(),
        output_dir=tmp_path,
        endpoint="http://127.0.0.1:8188",
        checked_at="2026-05-20T00:00:00Z",
    )

    assert report["provider"] == "comfyui"
    assert report["status"] == "pending"
    assert report["server_available"] is True
    assert report["checked_at"] == "2026-05-20T00:00:00Z"
    assert report["workflow_path"] is None
    assert report["generated_assets"] == []
    assert report["pending_assets"][0]["slide_id"] == "s1"
    assert report["pending_assets"][0]["text_policy"] == "text-free"


def test_unavailable_server_writes_honest_blockers(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "slideforge.comfyui_handoff.check_comfyui_server",
        lambda endpoint, timeout_seconds=1.0: (False, "ComfyUI health check failed for /system_stats: refused"),
    )

    briefs_path = tmp_path / "asset-briefs.json"
    briefs_path.write_text(json.dumps(_brief_set().to_comfyui_queue_payload()), encoding="utf-8")
    report_path = write_comfyui_handoff_report(asset_briefs_path=briefs_path, output_dir=tmp_path / "out")
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert report["status"] == "unavailable"
    assert report["server_available"] is False
    assert any("health check failed" in blocker for blocker in report["blockers"])
    assert report["generated_assets"] == []
    assert report["pending_assets"][0]["status"] == "pending"


def test_text_free_prompt_preserved_and_no_generated_path_false_claim(monkeypatch, tmp_path):
    monkeypatch.setattr("slideforge.comfyui_handoff.check_comfyui_server", lambda endpoint, timeout_seconds=1.0: (True, None))

    report = build_comfyui_handoff_report(_brief_set(), output_dir=tmp_path, checked_at="2026-05-20T00:00:00Z")

    pending = report["pending_assets"][0]
    assert pending["prompt"] == "dark aurora glass technology background, no text"
    assert "numbers" in pending["negative_prompt"]
    assert pending["text_policy"] == "text-free"
    assert "path" not in pending
    assert pending["generation_claim"] == "not_generated"


def test_comfyui_handoff_cli_writes_expected_report(tmp_path):
    briefs_path = tmp_path / "asset-briefs.json"
    output_dir = tmp_path / "handoff"
    briefs_path.write_text(json.dumps(_brief_set().to_comfyui_queue_payload(seed=7)), encoding="utf-8")

    exit_code = main(
        [
            "comfyui-handoff",
            "--asset-briefs",
            str(briefs_path),
            "--output-dir",
            str(output_dir),
            "--endpoint",
            "http://127.0.0.1:9",
            "--timeout",
            "0.1",
        ]
    )

    report_path = output_dir / "comfyui-handoff-report.json"
    assert exit_code == 0
    assert report_path.exists()
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["provider"] == "comfyui"
    assert report["status"] in {"unavailable", "pending"}
    assert report["brief_count"] == 1
    assert report["generated_assets"] == []
