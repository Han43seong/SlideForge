from slideforge.archetype_mapper import ArchetypeMapping
from slideforge.asset_brief_generator import generate_asset_briefs
from slideforge.design_spec import DesignSpec


def test_generate_asset_briefs_creates_text_free_prompts_for_visual_archetypes():
    spec = DesignSpec(
        name="Blockchain visual",
        background_layers=["deep navy base", "aurora ribbon"],
        graphic_motifs=["transparent 3D glass chip", "cyan-magenta data stream"],
    )
    mappings = [
        ArchetypeMapping(section_id="s1", archetype_name="cover", content_summary="폐쇄망 LLM 전략"),
        ArchetypeMapping(section_id="s2", archetype_name="timeline", content_summary="90일 실행계획"),
        ArchetypeMapping(section_id="s3", archetype_name="kpi_table", content_summary="KPI"),
    ]

    brief_set = generate_asset_briefs(spec, mappings)

    assert [brief.slide_id for brief in brief_set.briefs] == ["s1", "s2", "s3"]
    assert brief_set.briefs[0].asset_type == "cover_background"
    assert brief_set.briefs[1].asset_type == "visual_band"
    assert brief_set.briefs[2].asset_type == "subtle_panel_background"
    assert all(brief.text_policy == "text-free" for brief in brief_set.briefs)
    assert "no text" in brief_set.briefs[0].prompt
    assert "transparent 3D glass chip" in brief_set.briefs[0].prompt
    assert "KPI" not in brief_set.briefs[2].prompt


def test_generate_asset_briefs_uses_safe_defaults_without_graphic_motifs():
    brief_set = generate_asset_briefs(
        DesignSpec(name="minimal"),
        [ArchetypeMapping(section_id="s1", archetype_name="text_explainer", content_summary="보안 원칙")],
    )

    assert brief_set.briefs[0].asset_type == "subtle_panel_background"
    assert brief_set.briefs[0].negative_prompt.startswith("text, letters")
