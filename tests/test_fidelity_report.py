from slideforge.fidelity_report import render_fidelity_report
from slideforge.fidelity_scorer import FidelityScoreInput, score_fidelity


def test_render_fidelity_report_contains_score_verdict_and_categories():
    score = score_fidelity(
        FidelityScoreInput(
            background=16,
            generated_assets=14,
            layout_archetype=15,
            typography=8,
            data_visuals=8,
            korean_readability=8,
            technical_validity=9,
        )
    )

    markdown = render_fidelity_report(score, title="Smoke HTML fidelity")

    assert markdown.startswith("# Smoke HTML fidelity")
    assert "Total score" in markdown
    assert "78 / 100" in markdown
    assert "PASS_WITH_WARNINGS" in markdown
    assert "background" in markdown
    assert "generated_assets" in markdown
    assert "technical_validity" in markdown


def test_render_fidelity_report_marks_fail_threshold():
    score = score_fidelity(
        FidelityScoreInput(
            background=4,
            generated_assets=4,
            layout_archetype=4,
            typography=4,
            data_visuals=4,
            korean_readability=4,
            technical_validity=4,
        )
    )

    markdown = render_fidelity_report(score)

    assert "FAIL" in markdown
    assert "28 / 100" in markdown
