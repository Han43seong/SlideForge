from slideforge.guizang_html_composer import HtmlDeck, HtmlSlide, compose_html_deck


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
