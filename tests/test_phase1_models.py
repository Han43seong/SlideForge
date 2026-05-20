import pytest

from slideforge.asset_brief import AssetBrief, AssetBriefSet
from slideforge.design_spec import ColorToken, DesignSpec, SlideArchetype, TypographyToken
from slideforge.fidelity_scorer import FidelityScore, FidelityScoreInput, score_fidelity


def test_design_spec_records_template_grammar_and_round_trips_to_dict():
    spec = DesignSpec(
        name="Blockchain visual reference",
        source_refs=["https://example.test/template"],
        colors=[
            ColorToken(name="deep_navy", hex="#02030A", role="background"),
            ColorToken(name="aurora_cyan", hex="#35E7FF", role="accent"),
        ],
        typography=[
            TypographyToken(name="title", font_family="Inter", size_px=72, weight=800),
        ],
        slide_archetypes=[
            SlideArchetype(
                name="cover",
                purpose="Hero title with 3D visual",
                required_elements=["full-bleed aurora background", "3D glass chip", "large title"],
                forbidden_elements=["body-heavy paragraphs"],
            )
        ],
        background_layers=["deep navy base", "aurora ribbon", "foreground light streak"],
        graphic_motifs=["transparent 3D chip", "cyan-magenta data stream"],
    )

    data = spec.to_dict()

    assert data["name"] == "Blockchain visual reference"
    assert data["colors"][1]["hex"] == "#35E7FF"
    assert data["slide_archetypes"][0]["name"] == "cover"
    assert data["background_layers"] == ["deep navy base", "aurora ribbon", "foreground light streak"]


def test_design_spec_rejects_invalid_hex_color():
    with pytest.raises(ValueError, match="hex color"):
        ColorToken(name="bad", hex="35E7FF", role="accent")


def test_asset_briefs_are_text_free_and_comfyui_ready():
    brief = AssetBrief(
        slide_id="slide-01",
        asset_type="cover_background",
        prompt="dark futuristic aurora background with transparent glass chip, no text",
        negative_prompt="text, letters, watermark, logo",
        aspect_ratio="16:9",
        output_hint="generated-assets/slide-01-cover.png",
    )
    brief_set = AssetBriefSet(briefs=[brief])

    payload = brief_set.to_comfyui_queue_payload(seed=1234)

    assert payload["seed"] == 1234
    assert payload["briefs"][0]["text_policy"] == "text-free"
    assert "text" in payload["briefs"][0]["negative_prompt"]


def test_asset_brief_rejects_prompt_that_requests_text_rendering():
    with pytest.raises(ValueError, match="text-free"):
        AssetBrief(
            slide_id="slide-02",
            asset_type="chart_background",
            prompt="render Korean title 폐쇄망 LLM on the image",
            negative_prompt="watermark",
        )


def test_fidelity_scorer_totals_and_interprets_rubric():
    score = score_fidelity(
        FidelityScoreInput(
            background=18,
            generated_assets=16,
            layout_archetype=17,
            typography=8,
            data_visuals=8,
            korean_readability=9,
            technical_validity=10,
        )
    )

    assert isinstance(score, FidelityScore)
    assert score.total == 86
    assert score.rating == "high-fidelity candidate"
    assert score.to_dict()["max_score"] == 100


def test_fidelity_scorer_rejects_scores_over_category_maximum():
    with pytest.raises(ValueError, match="background"):
        score_fidelity(
            FidelityScoreInput(
                background=21,
                generated_assets=16,
                layout_archetype=17,
                typography=8,
                data_visuals=8,
                korean_readability=9,
                technical_validity=10,
            )
        )
