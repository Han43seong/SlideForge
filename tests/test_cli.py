import json
from pathlib import Path

from slideforge.cli import main
from slideforge.pptx_export import PptxRendererEvidence


def test_cli_build_spec_writes_design_spec_json(tmp_path):
    observations_path = tmp_path / "observations.json"
    output_path = tmp_path / "design-spec.json"
    observations_path.write_text(
        json.dumps(
            [
                {
                    "source_ref": "preview-01.png",
                    "slide_role": "cover",
                    "colors": {"deep_navy": "#02030A"},
                    "typography": {"title": {"font_family": "Inter", "size_px": 72, "weight": 800}},
                    "background_layers": ["aurora ribbon"],
                    "graphic_motifs": ["3D glass chip"],
                    "layout_notes": ["hero visual"],
                }
            ]
        ),
        encoding="utf-8",
    )

    exit_code = main(["build-spec", "--name", "Blockchain visual", "--observations", str(observations_path), "--output", str(output_path)])

    assert exit_code == 0
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["name"] == "Blockchain visual"
    assert data["slide_archetypes"][0]["name"] == "cover"


def test_cli_generate_asset_briefs_writes_comfyui_payload(tmp_path):
    design_spec_path = tmp_path / "design-spec.json"
    mappings_path = tmp_path / "mappings.json"
    output_path = tmp_path / "asset-briefs.json"
    design_spec_path.write_text(
        json.dumps(
            {
                "name": "Blockchain visual",
                "source_refs": [],
                "colors": [],
                "typography": [],
                "slide_archetypes": [],
                "background_layers": ["aurora ribbon"],
                "graphic_motifs": ["3D glass chip"],
            }
        ),
        encoding="utf-8",
    )
    mappings_path.write_text(
        json.dumps(
            [
                {"section_id": "s1", "archetype_name": "cover", "content_summary": "전략"},
                {"section_id": "s2", "archetype_name": "kpi_table", "content_summary": "KPI"},
            ]
        ),
        encoding="utf-8",
    )

    exit_code = main(
        [
            "generate-asset-briefs",
            "--design-spec",
            str(design_spec_path),
            "--mappings",
            str(mappings_path),
            "--output",
            str(output_path),
            "--seed",
            "42",
        ]
    )

    assert exit_code == 0
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["seed"] == 42
    assert data["briefs"][0]["asset_type"] == "cover_background"
    assert data["briefs"][1]["text_policy"] == "text-free"


def test_cli_compose_html_writes_presentation_file(tmp_path):
    deck_path = tmp_path / "deck.json"
    output_path = tmp_path / "deck.html"
    deck_path.write_text(
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

    exit_code = main(["compose-html", "--deck", str(deck_path), "--output", str(output_path)])

    assert exit_code == 0
    html = output_path.read_text(encoding="utf-8")
    assert "<!doctype html>" in html
    assert "function showSlide" in html
    assert "폐쇄망 LLM 전략" in html


def test_cli_smoke_html_run_writes_evidence_artifacts(tmp_path):
    deck_path = tmp_path / "deck.json"
    runs_dir = tmp_path / "runs"
    deck_path.write_text(
        json.dumps(
            {
                "title": "폐쇄망 LLM 전략",
                "slides": [
                    {"slide_id": "s1", "title": "폐쇄망 LLM 전략", "bullets": ["GPU"]}
                ],
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(["smoke-html", "--deck", str(deck_path), "--runs-dir", str(runs_dir), "--run-id", "smoke-cli"])

    assert exit_code == 0
    assert (runs_dir / "smoke-cli" / "deck.html").exists()
    assert (runs_dir / "smoke-cli" / "manifest.json").exists()
    assert (runs_dir / "smoke-cli" / "browser-regression-plan.json").exists()
    assert (runs_dir / "smoke-cli" / "pptx-delivery-gate.json").exists()


def test_cli_pptx_delivery_gate_writes_strategy_contract(tmp_path):
    source_path = tmp_path / "deck.html"
    source_path.write_text("<!doctype html><title>deck</title>", encoding="utf-8")
    output_dir = tmp_path / "evidence"

    exit_code = main(
        [
            "pptx-delivery-gate",
            "--source",
            str(source_path),
            "--desired-pptx",
            str(tmp_path / "deck.pptx"),
            "--output-dir",
            str(output_dir),
            "--run-id",
            "gate-cli",
        ]
    )

    assert exit_code == 0
    data = json.loads((output_dir / "pptx-delivery-gate.json").read_text(encoding="utf-8"))
    assert data["run_id"] == "gate-cli"
    assert data["report_kind"] == "pptx_delivery_gate"
    assert data["desired_pptx_path"].endswith("deck.pptx")
    assert data["validation_claim"] == "strategy_contract_only_no_pptx_export_or_visual_render_performed"


def test_cli_export_pptx_missing_dependency_writes_report_without_fake_output(tmp_path, monkeypatch):
    monkeypatch.setattr("slideforge.pptx_export.python_pptx_available", lambda: False)
    monkeypatch.setattr(
        "slideforge.pptx_export.PptxRendererEvidence.detect",
        lambda: PptxRendererEvidence(
            strategy="pptx_glimpse_required_for_renderer_evidence",
            status="unavailable",
            tool={"name": "pptx_glimpse", "executable": "pptx-glimpse", "available": False, "path": ""},
            blockers=["Renderer evidence requires approved pptx-glimpse installation; no install was performed."],
        ),
    )
    deck_path = tmp_path / "deck.json"
    output_path = tmp_path / "deck.pptx"
    report_path = tmp_path / "pptx-export-report.json"
    deck_path.write_text(
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

    exit_code = main([
        "export-pptx",
        "--deck",
        str(deck_path),
        "--output",
        str(output_path),
        "--report-output",
        str(report_path),
        "--run-id",
        "cli-missing",
    ])

    assert exit_code == 0
    data = json.loads(report_path.read_text(encoding="utf-8"))
    assert data["report_kind"] == "pptx_export"
    assert data["status"] == "unavailable"
    assert data["generation_claim"] == "no_pptx_output_created_python_pptx_missing"
    assert data["slide_count_expected"] == 1
    assert data["slide_count_generated"] == 0
    assert not output_path.exists()


def test_cli_export_evidence_pack_writes_zip(tmp_path):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "deck.html").write_text("<!doctype html><title>deck</title>", encoding="utf-8")
    (run_dir / "run-summary.json").write_text(
        json.dumps({"status": "needs_visual_evidence", "warnings": [], "blockers": [], "missing_external_evidence": ["browser_capture"]}),
        encoding="utf-8",
    )
    output = tmp_path / "pack.zip"
    sidecar = tmp_path / "pack-manifest.json"

    exit_code = main([
        "export-evidence-pack",
        "--run-dir",
        str(run_dir),
        "--output",
        str(output),
        "--manifest-output",
        str(sidecar),
    ])

    assert exit_code == 0
    assert output.exists()
    data = json.loads(sidecar.read_text(encoding="utf-8"))
    assert data["report_kind"] == "evidence_pack_report"
    assert data["summary_status"] == "needs_visual_evidence"
    assert data["artifacts"][0]["sha256"]

def test_cli_approve_assets_records_comfyui_ui_selection(tmp_path):
    candidate = tmp_path / "generated-assets" / "candidates" / "slide-01-b.png"
    candidate.parent.mkdir(parents=True)
    candidate.write_bytes(b"fake-png")
    candidates_path = tmp_path / "asset-generation-report.json"
    candidates_path.write_text(
        json.dumps(
            {
                "report_kind": "asset_generation_report",
                "run_id": "asset-gate-smoke",
                "candidates": [
                    {
                        "slide_id": "slide-01",
                        "candidate_id": "B",
                        "asset_path": str(candidate),
                        "source": "comfyui_ui",
                        "status": "generated",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "approved-assets.json"

    exit_code = main(
        [
            "approve-assets",
            "--candidates",
            str(candidates_path),
            "--selection",
            "slide-01=B",
            "--output",
            str(output_path),
            "--approved-by",
            "user",
            "--approval-mode",
            "explicit_user",
        ]
    )

    assert exit_code == 0
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["report_kind"] == "approved_assets"
    assert data["run_id"] == "asset-gate-smoke"
    assert data["approval_status"] == "approved"
    assert data["approved_assets"] == [
        {
            "slide_id": "slide-01",
            "selected_candidate": "B",
            "asset_path": str(candidate),
            "approved_by": "user",
            "approval_mode": "explicit_user",
            "notes": "",
            "source": "comfyui_ui",
        }
    ]
    assert data["regeneration_requests"] == []


def test_cli_apply_approved_assets_writes_deck_with_only_selected_assets(tmp_path):
    selected_asset = tmp_path / "generated-assets" / "candidates" / "slide-01-b.png"
    selected_asset.parent.mkdir(parents=True)
    selected_asset.write_bytes(b"fake-png")
    deck_path = tmp_path / "deck.json"
    deck_path.write_text(
        json.dumps(
            {
                "title": "Asset approval deck",
                "slides": [
                    {"slide_id": "slide-01", "title": "Cover", "archetype": "cover"},
                    {"slide_id": "slide-02", "title": "Text", "archetype": "text_explainer"},
                ],
            }
        ),
        encoding="utf-8",
    )
    approved_path = tmp_path / "approved-assets.json"
    approved_path.write_text(
        json.dumps(
            {
                "report_kind": "approved_assets",
                "run_id": "asset-gate-smoke",
                "approval_status": "approved",
                "approved_assets": [
                    {
                        "slide_id": "slide-01",
                        "selected_candidate": "B",
                        "asset_path": str(selected_asset),
                        "approved_by": "user",
                        "approval_mode": "explicit_user",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    output_path = tmp_path / "deck.approved.json"
    report_path = tmp_path / "approved-asset-application-report.json"

    exit_code = main(
        [
            "apply-approved-assets",
            "--deck",
            str(deck_path),
            "--approved-assets",
            str(approved_path),
            "--output",
            str(output_path),
            "--report-output",
            str(report_path),
        ]
    )

    assert exit_code == 0
    deck = json.loads(output_path.read_text(encoding="utf-8"))
    assert deck["slides"][0]["asset_path"] == str(selected_asset)
    assert "asset_path" not in deck["slides"][1]
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["report_kind"] == "approved_asset_application"
    assert report["applied_asset_count"] == 1
    assert report["unmatched_approved_slide_ids"] == []
    assert report["deck_output"] == str(output_path)


def test_cli_score_fidelity_writes_report_json(tmp_path):
    output_path = tmp_path / "score.json"

    exit_code = main(
        [
            "score-fidelity",
            "--background",
            "18",
            "--generated-assets",
            "16",
            "--layout-archetype",
            "17",
            "--typography",
            "8",
            "--data-visuals",
            "8",
            "--korean-readability",
            "9",
            "--technical-validity",
            "10",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["total"] == 86
    assert data["rating"] == "high-fidelity candidate"


def test_cli_score_fidelity_can_write_markdown_report(tmp_path):
    json_path = tmp_path / "score.json"
    markdown_path = tmp_path / "score.md"

    exit_code = main(
        [
            "score-fidelity",
            "--background",
            "16",
            "--generated-assets",
            "14",
            "--layout-archetype",
            "15",
            "--typography",
            "8",
            "--data-visuals",
            "8",
            "--korean-readability",
            "8",
            "--technical-validity",
            "9",
            "--output",
            str(json_path),
            "--markdown-output",
            str(markdown_path),
        ]
    )

    assert exit_code == 0
    markdown = markdown_path.read_text(encoding="utf-8")
    assert "78 / 100" in markdown
    assert "PASS_WITH_WARNINGS" in markdown


def test_cli_compose_html_loads_chart_and_comparison_schema(tmp_path):
    deck_path = tmp_path / "deck.json"
    output_path = tmp_path / "deck.html"
    deck_path.write_text(
        json.dumps(
            {
                "title": "structured visuals",
                "slides": [
                    {
                        "slide_id": "chart-1",
                        "title": "차트",
                        "archetype": "chart",
                        "chart_data": [{"label": "A", "value": 10, "note": "n", "color": "cyan"}],
                    },
                    {
                        "slide_id": "matrix-1",
                        "title": "비교",
                        "archetype": "matrix",
                        "comparison_columns": [{"label": "A"}, {"label": "B", "note": "beta"}],
                        "comparison_rows": [{"label": "Cost", "values": ["Low", "High"], "note": "range"}],
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    exit_code = main(["compose-html", "--deck", str(deck_path), "--output", str(output_path)])

    assert exit_code == 0
    html = output_path.read_text(encoding="utf-8")
    assert 'class="chart-panel"' in html
    assert 'class="comparison-matrix"' in html
    assert "Cost" in html
