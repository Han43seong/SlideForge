from slideforge.guizang_html_composer import (
    AssetPlaceholder,
    HtmlDeck,
    HtmlSlide,
    MetricRow,
    TimelineStep,
    VisualChip,
    compose_html_deck,
)


def test_compose_html_deck_outputs_presentation_shell():
    deck = HtmlDeck(
        title="폐쇄망 LLM 전략",
        slides=[
            HtmlSlide(
                slide_id="s1",
                title="폐쇄망 LLM 전략",
                subtitle="의사결정용 요약",
                bullets=["GPU 추론 계층", "RAG 서비스 계층"],
                archetype="cover",
            ),
            HtmlSlide(
                slide_id="s2",
                title="90일 실행계획",
                bullets=["PoC", "Pilot", "Scale"],
                archetype="timeline",
            ),
        ],
    )

    html = compose_html_deck(deck)

    assert "<!doctype html>" in html
    assert "<title>폐쇄망 LLM 전략</title>" in html
    assert html.count('class="slide"') == 2
    assert 'data-slide-id="s1"' in html
    assert "function showSlide" in html
    assert "ArrowRight" in html
    assert "#counter" in html
    assert "16 / 9" in html
    assert "GPU 추론 계층" in html


def test_compose_html_deck_renders_archetype_specific_sections():
    deck = HtmlDeck(
        title="archetype deck",
        slides=[
            HtmlSlide(slide_id="visual", title="비주얼 밴드", bullets=["Aurora", "3D chip"], archetype="visual_band"),
            HtmlSlide(slide_id="timeline", title="일정", bullets=["PoC", "Pilot", "Scale"], archetype="timeline"),
            HtmlSlide(slide_id="table", title="KPI", bullets=["정확도 | 85%", "응답시간 | 2초"], archetype="kpi_table"),
        ],
    )

    html = compose_html_deck(deck)

    assert 'class="visual-band"' in html
    assert 'class="timeline-track"' in html
    assert 'class="timeline-step"' in html
    assert 'class="metric-table"' in html
    assert "정확도" in html
    assert "85%" in html


def test_compose_html_deck_supports_structured_archetype_content():
    deck = HtmlDeck(
        title="structured deck",
        slides=[
            HtmlSlide(
                slide_id="visual",
                title="비주얼 밴드",
                archetype="visual_band",
                visual_chips=[VisualChip(label="Aurora", emphasis="cyan"), VisualChip(label="3D chip", emphasis="magenta")],
            ),
            HtmlSlide(
                slide_id="timeline",
                title="일정",
                archetype="timeline",
                timeline_steps=[TimelineStep(label="PoC", detail="0~30일"), TimelineStep(label="Pilot", detail="31~60일")],
            ),
            HtmlSlide(
                slide_id="table",
                title="KPI",
                archetype="kpi_table",
                metric_rows=[MetricRow(label="정확도", value="85%"), MetricRow(label="응답시간", value="2초")],
            ),
        ],
    )

    html = compose_html_deck(deck)

    assert 'data-emphasis="cyan"' in html
    assert "0~30일" in html
    assert "31~60일" in html
    assert "정확도" in html
    assert "85%" in html
    assert "정확도 | 85%" not in html



def test_compose_html_deck_renders_comfyui_asset_placeholders_for_visual_archetypes():
    deck = HtmlDeck(
        title="asset placeholders",
        slides=[
            HtmlSlide(
                slide_id="cover-1",
                title="전략 표지",
                archetype="cover",
                asset_placeholders=[
                    AssetPlaceholder(
                        slot_id="hero-bg",
                        asset_type="cover_background",
                        prompt="text-free dark aurora background",
                        output_hint="generated-assets/cover-1-cover_background.png",
                    )
                ],
            ),
            HtmlSlide(
                slide_id="arch-1",
                title="아키텍처",
                archetype="architecture_visual",
                visual_chips=[VisualChip(label="RAG"), VisualChip(label="GPU")],
            ),
            HtmlSlide(slide_id="text-1", title="본문", archetype="text_explainer", bullets=["no placeholder"]),
        ],
    )

    html = compose_html_deck(deck)

    assert 'class="visual-band-layout"' in html
    assert 'class="visual-chip-rail"' in html
    assert 'grid-template-rows:minmax(0, 1fr) auto' in html
    assert 'gap:18px' in html
    assert 'border-top:1px solid rgba(255,255,255,.14)' in html
    assert 'class="asset-placeholder-card"' in html
    assert 'data-asset-provider="comfyui"' in html
    assert 'data-asset-status="placeholder-only"' in html
    assert 'data-asset-slot="hero-bg"' in html
    assert 'data-asset-type="cover_background"' in html
    assert 'data-output-hint="generated-assets/cover-1-cover_background.png"' in html
    assert "ComfyUI asset placeholder" in html
    assert "text-free dark aurora background" in html
    assert 'data-asset-slot="arch-1-visual-band"' in html
    assert 'data-prompt="visual band placeholder for 아키텍처: RAG, GPU"' in html
    assert 'data-asset-slot="text-1' not in html


def test_visual_archetype_uses_generated_asset_path_without_placeholder_card():
    deck = HtmlDeck(
        title="generated asset deck",
        slides=[
            HtmlSlide(
                slide_id="generated-visual",
                title="생성 에셋",
                archetype="visual_band",
                asset_path="generated-assets/visual.png",
                visual_chips=[VisualChip(label="AI maintenance")],
            )
        ],
    )

    html = compose_html_deck(deck)

    assert "background-image:url('generated-assets/visual.png')" in html
    assert "ComfyUI asset placeholder" not in html
    assert 'class="asset-placeholder-card"' not in html
    assert 'data-asset-status="placeholder-only"' not in html
    assert "AI maintenance" in html


def test_asset_placeholder_rejects_real_integration_paths_and_escapes_metadata():
    try:
        AssetPlaceholder(slot_id="bad", asset_type="cover_background", prompt="ok", generated_path="generated.png")
    except ValueError as exc:
        assert "placeholder-only" in str(exc)
    else:
        raise AssertionError("expected ValueError")

    html = compose_html_deck(
        HtmlDeck(
            title="escape",
            slides=[
                HtmlSlide(
                    slide_id="s1",
                    title="safe",
                    archetype="cover",
                    asset_placeholders=[
                        AssetPlaceholder(
                            slot_id="slot-<x>",
                            asset_type="cover_background",
                            prompt="<script>alert(1)</script>",
                            output_hint="assets/a&b.png",
                        )
                    ],
                )
            ],
        )
    )

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert 'data-asset-slot="slot-&lt;x&gt;"' in html
    assert 'data-output-hint="assets/a&amp;b.png"' in html

def test_compose_html_deck_escapes_user_content():
    deck = HtmlDeck(
        title="<script>alert(1)</script>",
        slides=[HtmlSlide(slide_id="s1", title="위험 <b>제목</b>", bullets=["<img src=x>"])],
    )

    html = compose_html_deck(deck)

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "위험 &lt;b&gt;제목&lt;/b&gt;" in html
    assert "&lt;img src=x&gt;" in html


def test_compose_html_deck_rejects_empty_slides():
    try:
        compose_html_deck(HtmlDeck(title="empty", slides=[]))
    except ValueError as exc:
        assert "at least one slide" in str(exc)
    else:
        raise AssertionError("expected ValueError")


def test_compose_html_deck_renders_chart_schema_as_deterministic_svg_bars():
    from slideforge.guizang_html_composer import ChartDatum

    deck = HtmlDeck(
        title="chart deck",
        slides=[
            HtmlSlide(
                slide_id="chart-1",
                title="채널 성과",
                archetype="bar_chart",
                chart_data=[
                    ChartDatum(label="Organic", value=80, note="baseline", color="#35e7ff"),
                    ChartDatum(label="Paid <unsafe>", value=40, note="needs & review"),
                ],
            )
        ],
    )

    html = compose_html_deck(deck)

    assert 'class="chart-panel"' in html
    assert '<svg class="bar-chart"' in html
    assert 'data-chart-kind="bar_chart"' in html
    assert 'data-chart-value="80"' in html
    assert 'width="448.0"' in html
    assert 'viewBox="0 0 560 100"' in html
    assert 'height="24" rx="8"' in html
    assert '.chart-panel { margin-top:26px; display:grid; grid-template-columns:1.4fr .9fr; gap:20px; align-items:start; max-width:960px; }' in html
    assert '.bar-chart { width:100%; min-height:240px; padding:16px;' in html
    assert '.chart-legend { margin:0; display:grid; gap:8px; }' in html
    assert '.chart-legend li { max-width:none; padding:11px 13px;' in html
    assert 'Paid &lt;unsafe&gt;' in html
    assert 'needs &amp; review' in html
    assert "<unsafe>" not in html


def test_compose_html_deck_renders_comparison_matrix_schema_and_escapes_cells():
    from slideforge.guizang_html_composer import ComparisonColumn, ComparisonRow

    deck = HtmlDeck(
        title="matrix deck",
        slides=[
            HtmlSlide(
                slide_id="matrix-1",
                title="옵션 비교",
                archetype="comparison_matrix",
                comparison_columns=[ComparisonColumn(label="A&B", note="fast"), ComparisonColumn(label="B")],
                comparison_rows=[
                    ComparisonRow(label="위험", values=["낮음", "<script>x</script>"], note="검토"),
                    ComparisonRow(label="비용", values=["중", "고"]),
                ],
            )
        ],
    )

    html = compose_html_deck(deck)

    assert 'class="comparison-matrix"' in html
    assert 'data-column-count="2"' in html
    assert "A&amp;B" in html
    assert "&lt;script&gt;x&lt;/script&gt;" in html
    assert "<script>x</script>" not in html
    assert "검토" in html
