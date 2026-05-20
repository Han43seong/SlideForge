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
