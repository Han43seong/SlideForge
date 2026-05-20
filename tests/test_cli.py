import json
from pathlib import Path

from slideforge.cli import main


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
