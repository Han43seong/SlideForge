from slideforge.guizang_html_composer import HtmlDeck, HtmlSlide, MetricRow, TimelineStep, VisualChip, compose_html_deck


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
