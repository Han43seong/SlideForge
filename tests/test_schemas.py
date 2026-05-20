import pytest

from slideforge import schemas
from slideforge.guizang_html_composer import (
    AssetPlaceholder as LegacyAssetPlaceholder,
    ChartDatum as LegacyChartDatum,
    ComparisonColumn as LegacyComparisonColumn,
    ComparisonRow as LegacyComparisonRow,
    HtmlDeck as LegacyHtmlDeck,
    HtmlSlide as LegacyHtmlSlide,
    MetricRow as LegacyMetricRow,
    TimelineStep as LegacyTimelineStep,
    VisualChip as LegacyVisualChip,
)


def test_schema_classes_are_importable_from_dedicated_module():
    slide = schemas.HtmlSlide(
        slide_id="s1",
        title="Schema slide",
        visual_chips=[schemas.VisualChip(label="Aurora")],
        chart_data=[schemas.ChartDatum(label="Score", value=1.5)],
    )
    deck = schemas.HtmlDeck(title="Schema deck", slides=[slide])

    assert deck.slides[0].visual_chips[0].label == "Aurora"
    assert deck.slides[0].chart_data[0].value == 1.5


def test_legacy_composer_schema_imports_are_preserved_as_reexports():
    assert LegacyVisualChip is schemas.VisualChip
    assert LegacyAssetPlaceholder is schemas.AssetPlaceholder
    assert LegacyChartDatum is schemas.ChartDatum
    assert LegacyComparisonColumn is schemas.ComparisonColumn
    assert LegacyComparisonRow is schemas.ComparisonRow
    assert LegacyMetricRow is schemas.MetricRow
    assert LegacyTimelineStep is schemas.TimelineStep
    assert LegacyHtmlSlide is schemas.HtmlSlide
    assert LegacyHtmlDeck is schemas.HtmlDeck


def test_schema_validation_behavior_is_preserved_for_invalid_inputs():
    with pytest.raises(ValueError, match="visual chip label is required"):
        schemas.VisualChip(label=" ")

    with pytest.raises(ValueError, match="finite number"):
        schemas.ChartDatum(label="bad", value=float("nan"))

    with pytest.raises(ValueError, match="placeholder-only"):
        schemas.AssetPlaceholder(
            slot_id="hero",
            asset_type="cover_background",
            prompt="ok",
            generated_path="generated.png",
        )

    with pytest.raises(ValueError, match="at least one slide"):
        schemas.HtmlDeck(title="empty", slides=[])
