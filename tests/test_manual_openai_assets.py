import json
from pathlib import Path

from slideforge.cli import main


def _write_spec(spec_dir: Path, asset_id: str = "cover-hero", slide_id: str = "slide-01") -> Path:
    spec_dir.mkdir(parents=True, exist_ok=True)
    path = spec_dir / f"{asset_id}.json"
    path.write_text(
        json.dumps(
            {
                "asset_id": asset_id,
                "role": "cover hero cinematic object",
                "slide_id": slide_id,
                "visual_style": "neon glass, dark gradient, premium enterprise",
                "palette": ["#050914", "#38d6ff"],
                "constraints": ["No people", "No extra UI frame"],
                "output_guidance": ["Transparent-looking edges when possible"],
            }
        ),
        encoding="utf-8",
    )
    return path


def test_generate_openai_manual_prompts_writes_pack_and_per_asset_prompt(tmp_path):
    spec_dir = tmp_path / "run" / "asset-specs"
    _write_spec(spec_dir)
    output_dir = tmp_path / "run" / "openai-manual-prompts"

    exit_code = main([
        "generate-openai-manual-prompts",
        "--asset-spec-dir",
        str(spec_dir),
        "--output-dir",
        str(output_dir),
    ])

    assert exit_code == 0
    prompt = (output_dir / "cover-hero.md").read_text(encoding="utf-8")
    assert "cover hero cinematic object" in prompt
    assert "slide-01" in prompt
    assert "#38d6ff" in prompt
    assert "No text, letters, numbers" in prompt
    assert "manual-generated-assets/cover-hero/A.png" in prompt
    pack = json.loads((output_dir / "prompt-pack.json").read_text(encoding="utf-8"))
    assert pack["report_kind"] == "openai_manual_prompt_pack"
    assert pack["provider"] == "openai_images"
    assert pack["prompts"][0]["manual_save_dir"] == "manual-generated-assets/cover-hero/"
    assert (output_dir / "prompt-pack.md").exists()


def test_import_manual_assets_copies_supported_files_and_writes_deterministic_report(tmp_path, capsys):
    run_dir = tmp_path / "runs" / "demo"
    spec_dir = run_dir / "asset-specs"
    _write_spec(spec_dir)
    _write_spec(spec_dir, asset_id="missing-asset", slide_id="slide-02")
    input_asset_dir = run_dir / "manual-generated-assets" / "cover-hero"
    input_asset_dir.mkdir(parents=True)
    (input_asset_dir / "A.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    (input_asset_dir / "B.JPG").write_bytes(b"jpg")
    (input_asset_dir / "notes.txt").write_text("ignore", encoding="utf-8")
    report_path = run_dir / "asset-generation-report.json"

    exit_code = main([
        "import-manual-assets",
        "--run-dir",
        str(run_dir),
        "--asset-spec-dir",
        str(spec_dir),
        "--input-dir",
        str(run_dir / "manual-generated-assets"),
        "--output-report",
        str(report_path),
    ])

    assert exit_code == 0
    stderr = capsys.readouterr().err
    assert "missing manual asset directory" in stderr
    assert "unsupported asset extension" in stderr
    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert data["candidate_count"] == 2
    assert data["warnings"]
    first = data["candidates"][0]
    assert first == {
        "slide_id": "slide-01",
        "asset_id": "cover-hero",
        "candidate_id": "A",
        "path": "imported-assets/cover-hero-A.png",
        "asset_path": "imported-assets/cover-hero-A.png",
        "provider": "openai_images",
        "source": "manual_openai_images",
        "generation_mode": "manual_chatgpt_pro",
        "prompt_file": "openai-manual-prompts/cover-hero.md",
        "license_note": "Generated manually by user in ChatGPT Pro/OpenAI Images; verify plan terms before commercial use.",
        "status": "generated",
        "notes": "Manual OpenAI Images candidate for cover hero cinematic object",
    }
    assert (run_dir / "imported-assets" / "cover-hero-A.png").read_bytes().startswith(b"\x89PNG")
    assert (run_dir / "imported-assets" / "cover-hero-B.jpg").exists()


def test_review_board_renders_empty_manual_openai_guidance(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    report_path = run_dir / "asset-generation-report.json"
    report_path.write_text(
        json.dumps(
            {
                "report_kind": "asset_generation_report",
                "run_id": "run",
                "source": "manual_openai_images",
                "generation_mode": "manual_chatgpt_pro",
                "asset_spec_dir": "asset-specs",
                "input_dir": "manual-generated-assets",
                "candidate_count": 0,
                "candidates": [],
                "warnings": ["missing manual asset directory for cover-hero"],
            }
        ),
        encoding="utf-8",
    )
    html_path = run_dir / "asset-review-board.html"
    md_path = run_dir / "asset-review-board.md"

    exit_code = main([
        "build-asset-review-board",
        "--candidates",
        str(report_path),
        "--output-html",
        str(html_path),
        "--output-md",
        str(md_path),
    ])

    assert exit_code == 0
    html = html_path.read_text(encoding="utf-8")
    md = md_path.read_text(encoding="utf-8")
    assert "No manual OpenAI Images candidates were imported yet" in html
    assert "manual-generated-assets/&lt;asset_id&gt;/A.png" in html
    assert "Rerun import-manual-assets" in md


def test_review_board_renders_manual_openai_metadata_and_relative_paths(tmp_path):
    run_dir = tmp_path / "run"
    (run_dir / "imported-assets").mkdir(parents=True)
    (run_dir / "imported-assets" / "cover-hero-A.png").write_bytes(b"\x89PNG\r\n\x1a\n")
    report = {
        "report_kind": "asset_generation_report",
        "run_id": "run",
        "candidate_count": 1,
        "candidates": [
            {
                "slide_id": "slide-01",
                "asset_id": "cover-hero",
                "candidate_id": "A",
                "path": "imported-assets/cover-hero-A.png",
                "provider": "openai_images",
                "source": "manual_openai_images",
                "generation_mode": "manual_chatgpt_pro",
                "prompt_file": "openai-manual-prompts/cover-hero.md",
                "license_note": "Generated manually by user in ChatGPT Pro/OpenAI Images; verify plan terms before commercial use.",
                "status": "generated",
            }
        ],
    }
    report_path = run_dir / "asset-generation-report.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    html_path = run_dir / "asset-review-board.html"
    md_path = run_dir / "asset-review-board.md"

    exit_code = main([
        "build-asset-review-board",
        "--candidates",
        str(report_path),
        "--output-html",
        str(html_path),
        "--output-md",
        str(md_path),
    ])

    assert exit_code == 0
    html = html_path.read_text(encoding="utf-8")
    md = md_path.read_text(encoding="utf-8")
    assert "manual_openai_images" in html
    assert "manual_chatgpt_pro" in html
    assert "openai-manual-prompts/cover-hero.md" in html
    assert "License note" in md

    approved_path = run_dir / "approved-assets.json"
    exit_code = main([
        "approve-assets",
        "--candidates",
        str(report_path),
        "--selection",
        "slide-01=A",
        "--output",
        str(approved_path),
    ])
    assert exit_code == 0
    approved = json.loads(approved_path.read_text(encoding="utf-8"))
    assert approved["approved_assets"][0]["asset_path"] == "imported-assets/cover-hero-A.png"
