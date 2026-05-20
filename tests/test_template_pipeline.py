from slideforge.archetype_mapper import ContentSection, map_sections_to_archetypes
from slideforge.template_analyzer import TemplateObservation, build_design_spec_from_observations


def test_template_analyzer_builds_design_spec_from_observations():
    observations = [
        TemplateObservation(
            source_ref="preview-01.png",
            slide_role="cover",
            colors={"deep_navy": "#02030A", "aurora_cyan": "#35E7FF"},
            typography={"title": {"font_family": "Inter", "size_px": 72, "weight": 800}},
            background_layers=["deep navy base", "aurora ribbon"],
            graphic_motifs=["3D glass chip"],
            layout_notes=["large title left", "hero object center-right"],
        ),
        TemplateObservation(
            source_ref="preview-02.png",
            slide_role="timeline",
            colors={"magenta": "#FF4FD8"},
            typography={"body": {"font_family": "Inter", "size_px": 24, "weight": 400}},
            background_layers=["dark translucent card"],
            graphic_motifs=["glowing timeline nodes"],
            layout_notes=["horizontal milestones"],
        ),
    ]

    spec = build_design_spec_from_observations("Blockchain visual", observations)

    assert spec.name == "Blockchain visual"
    assert spec.source_refs == ["preview-01.png", "preview-02.png"]
    assert [color.name for color in spec.colors] == ["deep_navy", "aurora_cyan", "magenta"]
    assert [token.name for token in spec.typography] == ["title", "body"]
    assert [archetype.name for archetype in spec.slide_archetypes] == ["cover", "timeline"]
    assert "3D glass chip" in spec.graphic_motifs


def test_archetype_mapper_prefers_semantic_matches_and_keeps_order():
    sections = [
        ContentSection(id="s1", heading="전략 개요", intent="cover", bullets=["폐쇄망 LLM 전략"]),
        ContentSection(id="s2", heading="90일 실행계획", intent="timeline", bullets=["PoC", "Pilot", "Scale"]),
        ContentSection(id="s3", heading="KPI", intent="table", bullets=["정확도", "응답시간"]),
    ]
    archetype_names = ["cover", "agenda", "timeline", "kpi_table"]

    mappings = map_sections_to_archetypes(sections, archetype_names)

    assert [mapping.section_id for mapping in mappings] == ["s1", "s2", "s3"]
    assert [mapping.archetype_name for mapping in mappings] == ["cover", "timeline", "kpi_table"]
    assert mappings[1].content_summary == "90일 실행계획: PoC / Pilot / Scale"


def test_archetype_mapper_falls_back_to_text_explainer_for_unknown_intent():
    mappings = map_sections_to_archetypes(
        [ContentSection(id="s1", heading="보안 원칙", intent="policy", bullets=[])],
        ["cover", "text_explainer"],
    )

    assert mappings[0].archetype_name == "text_explainer"
