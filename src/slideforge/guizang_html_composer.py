from __future__ import annotations

from dataclasses import dataclass, field
from html import escape


@dataclass(frozen=True)
class HtmlSlide:
    slide_id: str
    title: str
    subtitle: str = ""
    bullets: list[str] = field(default_factory=list)
    archetype: str = "text_explainer"
    asset_path: str | None = None

    def __post_init__(self) -> None:
        if not self.slide_id.strip():
            raise ValueError("slide_id is required")
        if not self.title.strip():
            raise ValueError("slide title is required")


@dataclass(frozen=True)
class HtmlDeck:
    title: str
    slides: list[HtmlSlide]

    def __post_init__(self) -> None:
        if not self.title.strip():
            raise ValueError("deck title is required")
        if not self.slides:
            raise ValueError("HTML deck requires at least one slide")


def _render_slide(slide: HtmlSlide, index: int, total: int) -> str:
    subtitle = f'<p class="subtitle">{escape(slide.subtitle)}</p>' if slide.subtitle else ""
    bullets = "\n".join(f"        <li>{escape(item)}</li>" for item in slide.bullets)
    bullet_block = f"\n      <ul>\n{bullets}\n      </ul>" if slide.bullets else ""
    asset_style = ""
    if slide.asset_path:
        asset_style = f'<div class="asset" style="background-image:url(\'{escape(slide.asset_path)}\')"></div>'
    return f'''    <section class="slide" data-slide-id="{escape(slide.slide_id)}" data-archetype="{escape(slide.archetype)}">
      {asset_style}
      <div class="slide-content">
        <div class="eyebrow">{index:02d} / {total:02d}</div>
        <h1>{escape(slide.title)}</h1>
        {subtitle}{bullet_block}
      </div>
    </section>'''


def compose_html_deck(deck: HtmlDeck) -> str:
    slides = "\n".join(_render_slide(slide, idx, len(deck.slides)) for idx, slide in enumerate(deck.slides, start=1))
    title = escape(deck.title)
    return f'''<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    :root {{ color-scheme: dark; --bg:#02030a; --fg:#f7fbff; --muted:#9eb6cc; --cyan:#35e7ff; --magenta:#ff4fd8; }}
    * {{ box-sizing: border-box; }}
    body {{ margin:0; min-height:100vh; background:radial-gradient(circle at 70% 20%, rgba(53,231,255,.25), transparent 34%), var(--bg); color:var(--fg); font-family: Inter, Pretendard, system-ui, sans-serif; overflow:hidden; }}
    .deck {{ width:min(100vw, calc(100vh * 16 / 9)); height:min(100vh, calc(100vw * 9 / 16)); margin:auto; position:relative; aspect-ratio:16 / 9; overflow:hidden; }}
    .slide {{ position:absolute; inset:0; display:none; padding:72px; background:linear-gradient(135deg, rgba(2,3,10,.96), rgba(10,18,36,.9)); }}
    .slide.active {{ display:block; }}
    .slide::before {{ content:""; position:absolute; inset:-20%; background:linear-gradient(120deg, transparent 20%, rgba(53,231,255,.18), rgba(255,79,216,.16), transparent 72%); filter:blur(26px); transform:rotate(-8deg); }}
    .asset {{ position:absolute; inset:0; background-size:cover; background-position:center; opacity:.74; mix-blend-mode:screen; }}
    .slide-content {{ position:relative; z-index:1; max-width:940px; }}
    .eyebrow {{ color:var(--cyan); letter-spacing:.18em; font-size:18px; font-weight:800; margin-bottom:28px; }}
    h1 {{ margin:0; font-size:68px; line-height:1.03; letter-spacing:-.04em; text-wrap:balance; }}
    .subtitle {{ color:var(--muted); font-size:28px; margin:22px 0 0; }}
    ul {{ margin:40px 0 0; padding:0; list-style:none; display:grid; gap:16px; }}
    li {{ max-width:760px; padding:18px 22px; border:1px solid rgba(53,231,255,.28); border-radius:18px; background:rgba(255,255,255,.055); font-size:24px; }}
    #counter {{ position:fixed; right:28px; bottom:24px; color:var(--muted); font-weight:700; z-index:10; }}
    #progress {{ position:fixed; left:0; bottom:0; height:4px; background:linear-gradient(90deg, var(--cyan), var(--magenta)); width:0; z-index:10; }}
    @media print {{ body {{ overflow:visible; }} .deck {{ width:100vw; height:100vh; }} .slide {{ display:block; position:relative; page-break-after:always; }} #counter, #progress {{ display:none; }} }}
  </style>
</head>
<body>
  <main class="deck" aria-label="{title}">
{slides}
  </main>
  <div id="counter">1 / {len(deck.slides)}</div>
  <div id="progress"></div>
  <script>
    const slides = Array.from(document.querySelectorAll('.slide'));
    let current = 0;
    function showSlide(index) {{
      current = Math.max(0, Math.min(index, slides.length - 1));
      slides.forEach((slide, i) => slide.classList.toggle('active', i === current));
      document.querySelector('#counter').textContent = `${{current + 1}} / ${{slides.length}}`;
      document.querySelector('#progress').style.width = `${{((current + 1) / slides.length) * 100}}%`;
    }}
    document.addEventListener('keydown', (event) => {{
      if (['ArrowRight', 'PageDown', ' '].includes(event.key)) showSlide(current + 1);
      if (['ArrowLeft', 'PageUp'].includes(event.key)) showSlide(current - 1);
      if (event.key === 'Home') showSlide(0);
      if (event.key === 'End') showSlide(slides.length - 1);
    }});
    showSlide(0);
  </script>
</body>
</html>
'''
