from __future__ import annotations

from dataclasses import dataclass, field
from html import escape


@dataclass(frozen=True)
class VisualChip:
    label: str
    emphasis: str = "neutral"

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("visual chip label is required")


@dataclass(frozen=True)
class AssetPlaceholder:
    slot_id: str
    asset_type: str
    prompt: str
    provider: str = "comfyui"
    status: str = "placeholder-only"
    output_hint: str | None = None
    generated_path: str | None = None

    def __post_init__(self) -> None:
        if not self.slot_id.strip():
            raise ValueError("asset placeholder slot_id is required")
        if not self.asset_type.strip():
            raise ValueError("asset placeholder asset_type is required")
        if not self.prompt.strip():
            raise ValueError("asset placeholder prompt is required")
        if self.provider != "comfyui":
            raise ValueError("asset placeholders currently support only comfyui provider")
        if self.status != "placeholder-only":
            raise ValueError("asset placeholders must remain placeholder-only")
        if self.generated_path:
            raise ValueError("asset placeholders are placeholder-only; use output_hint, not generated_path")


@dataclass(frozen=True)
class TimelineStep:
    label: str
    detail: str = ""

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("timeline step label is required")


@dataclass(frozen=True)
class MetricRow:
    label: str
    value: str

    def __post_init__(self) -> None:
        if not self.label.strip():
            raise ValueError("metric row label is required")
        if not self.value.strip():
            raise ValueError("metric row value is required")


@dataclass(frozen=True)
class HtmlSlide:
    slide_id: str
    title: str
    subtitle: str = ""
    bullets: list[str] = field(default_factory=list)
    archetype: str = "text_explainer"
    asset_path: str | None = None
    visual_chips: list[VisualChip] = field(default_factory=list)
    asset_placeholders: list[AssetPlaceholder] = field(default_factory=list)
    timeline_steps: list[TimelineStep] = field(default_factory=list)
    metric_rows: list[MetricRow] = field(default_factory=list)

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


def _render_default_bullets(slide: HtmlSlide) -> str:
    bullets = "\n".join(f"        <li>{escape(item)}</li>" for item in slide.bullets)
    return f"\n      <ul>\n{bullets}\n      </ul>" if slide.bullets else ""


def _is_asset_placeholder_archetype(archetype: str) -> bool:
    return archetype in {"visual_band", "architecture_visual", "cover"}


def _asset_type_for_visual_archetype(archetype: str) -> str:
    if archetype == "cover":
        return "cover_background"
    return "visual_band"


def _default_asset_placeholder(slide: HtmlSlide, chip_items: list[VisualChip]) -> AssetPlaceholder:
    context = ", ".join(chip.label for chip in chip_items[:4]) or slide.subtitle or "text-free generated visual"
    slot_kind = "cover-background" if slide.archetype == "cover" else "visual-band"
    asset_type = _asset_type_for_visual_archetype(slide.archetype)
    return AssetPlaceholder(
        slot_id=f"{slide.slide_id}-{slot_kind}",
        asset_type=asset_type,
        prompt=f"{slot_kind.replace('-', ' ')} placeholder for {slide.title}: {context}",
        output_hint=f"generated-assets/{slide.slide_id}-{asset_type}.png",
    )


def _render_asset_placeholder(placeholder: AssetPlaceholder) -> str:
    output_hint = escape(placeholder.output_hint or "")
    return f'''
        <aside class="asset-placeholder-card"
          data-asset-provider="{escape(placeholder.provider)}"
          data-asset-status="{escape(placeholder.status)}"
          data-asset-slot="{escape(placeholder.slot_id)}"
          data-asset-type="{escape(placeholder.asset_type)}"
          data-output-hint="{output_hint}"
          data-prompt="{escape(placeholder.prompt)}">
          <span class="asset-placeholder-kicker">ComfyUI asset placeholder</span>
          <strong>{escape(placeholder.asset_type)}</strong>
          <span class="asset-placeholder-slot">slot: {escape(placeholder.slot_id)}</span>
          <span class="asset-placeholder-hint">output: {output_hint or "pending"}</span>
          <span class="asset-placeholder-prompt">{escape(placeholder.prompt)}</span>
        </aside>'''


def _render_asset_placeholders(slide: HtmlSlide, chip_items: list[VisualChip]) -> str:
    if not _is_asset_placeholder_archetype(slide.archetype):
        return ""
    placeholders = slide.asset_placeholders or [_default_asset_placeholder(slide, chip_items)]
    cards = "".join(_render_asset_placeholder(placeholder) for placeholder in placeholders)
    return f'''
        <div class="asset-placeholder-stack" aria-label="ComfyUI asset placeholder slots">{cards}
        </div>'''


def _render_visual_band(slide: HtmlSlide) -> str:
    chip_items = slide.visual_chips or [VisualChip(label=item) for item in slide.bullets]
    chips = "\n".join(
        f'          <span class="visual-chip" data-emphasis="{escape(chip.emphasis)}">{escape(chip.label)}</span>'
        for chip in chip_items
    )
    placeholders = _render_asset_placeholders(slide, chip_items)
    return f'''\n      <div class="visual-band" aria-label="visual motifs">
        <div class="orb orb-cyan"></div>
        <div class="orb orb-magenta"></div>
        <div class="light-ribbon"></div>
        <div class="visual-band-layout">{placeholders}
          <div class="visual-chip-rail" aria-label="visual chip labels">
            <div class="visual-chips">
{chips}
            </div>
          </div>
        </div>
      </div>'''


def _render_timeline(slide: HtmlSlide) -> str:
    steps = []
    step_items = slide.timeline_steps or [TimelineStep(label=item) for item in slide.bullets]
    total = max(len(step_items), 1)
    for idx, item in enumerate(step_items, start=1):
        detail = f'<span class="timeline-detail">{escape(item.detail)}</span>' if item.detail else ""
        steps.append(
            f'''        <div class="timeline-step" style="--step:{idx}; --total:{total}">
          <span class="timeline-dot">{idx:02d}</span>
          <span class="timeline-label">{escape(item.label)}</span>{detail}
        </div>'''
        )
    return "\n      <div class=\"timeline-track\">\n" + "\n".join(steps) + "\n      </div>" if steps else ""


def _metric_rows_from_bullets(bullets: list[str]) -> list[MetricRow]:
    rows = []
    for item in bullets:
        label, sep, value = item.partition("|")
        rows.append(MetricRow(label=label.strip(), value=value.strip() if sep else "—"))
    return rows


def _render_metric_table(slide: HtmlSlide) -> str:
    rows = []
    for item in slide.metric_rows or _metric_rows_from_bullets(slide.bullets):
        rows.append(
            f'''        <tr>
          <th>{escape(item.label)}</th>
          <td>{escape(item.value)}</td>
        </tr>'''
        )
    return "\n      <table class=\"metric-table\">\n" + "\n".join(rows) + "\n      </table>" if rows else ""


def _render_archetype_body(slide: HtmlSlide) -> str:
    if slide.archetype in {"visual_band", "architecture_visual", "cover"}:
        return _render_visual_band(slide)
    if slide.archetype == "timeline":
        return _render_timeline(slide)
    if slide.archetype in {"kpi_table", "table"}:
        return _render_metric_table(slide)
    return _render_default_bullets(slide)


def _render_slide(slide: HtmlSlide, index: int, total: int) -> str:
    subtitle = f'<p class="subtitle">{escape(slide.subtitle)}</p>' if slide.subtitle else ""
    body = _render_archetype_body(slide)
    asset_style = ""
    if slide.asset_path:
        asset_style = f'<div class="asset" style="background-image:url(\'{escape(slide.asset_path)}\')"></div>'
    return f'''    <section class="slide" data-slide-id="{escape(slide.slide_id)}" data-archetype="{escape(slide.archetype)}">
      {asset_style}
      <div class="slide-content">
        <div class="eyebrow">{index:02d} / {total:02d}</div>
        <h1>{escape(slide.title)}</h1>
        {subtitle}{body}
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
    .slide[data-archetype="visual_band"] .slide-content, .slide[data-archetype="architecture_visual"] .slide-content, .slide[data-archetype="cover"] .slide-content {{ position:static; max-width:500px; }}
    .slide[data-archetype="visual_band"] .eyebrow, .slide[data-archetype="visual_band"] h1, .slide[data-archetype="visual_band"] .subtitle, .slide[data-archetype="architecture_visual"] .eyebrow, .slide[data-archetype="architecture_visual"] h1, .slide[data-archetype="architecture_visual"] .subtitle, .slide[data-archetype="cover"] .eyebrow, .slide[data-archetype="cover"] h1, .slide[data-archetype="cover"] .subtitle {{ position:relative; z-index:2; max-width:500px; }}
    .eyebrow {{ color:var(--cyan); letter-spacing:.18em; font-size:18px; font-weight:800; margin-bottom:28px; }}
    h1 {{ margin:0; font-size:68px; line-height:1.03; letter-spacing:-.04em; text-wrap:balance; }}
    .slide[data-archetype="visual_band"] h1, .slide[data-archetype="architecture_visual"] h1, .slide[data-archetype="cover"] h1 {{ font-size:54px; line-height:1.08; }}
    .subtitle {{ color:var(--muted); font-size:28px; margin:22px 0 0; }}
    ul {{ margin:40px 0 0; padding:0; list-style:none; display:grid; gap:16px; }}
    li {{ max-width:760px; padding:18px 22px; border:1px solid rgba(53,231,255,.28); border-radius:18px; background:rgba(255,255,255,.055); font-size:24px; }}
    .visual-band {{ position:absolute; right:72px; bottom:76px; width:40%; height:32%; border:1px solid rgba(53,231,255,.24); border-radius:32px; background:linear-gradient(135deg, rgba(53,231,255,.12), rgba(255,79,216,.11)); overflow:hidden; box-shadow:0 24px 90px rgba(0,0,0,.35); }}
    .orb {{ position:absolute; width:180px; height:180px; border-radius:999px; filter:blur(6px); opacity:.78; }}
    .orb-cyan {{ right:18%; top:8%; background:radial-gradient(circle, rgba(53,231,255,.95), rgba(53,231,255,.08) 64%, transparent 70%); }}
    .orb-magenta {{ left:10%; bottom:2%; background:radial-gradient(circle, rgba(255,79,216,.82), rgba(255,79,216,.08) 64%, transparent 70%); }}
    .light-ribbon {{ position:absolute; inset:38% -12%; height:24px; background:linear-gradient(90deg, transparent, rgba(53,231,255,.82), rgba(255,79,216,.78), transparent); filter:blur(4px); transform:rotate(-14deg); }}
    .visual-band-layout {{ position:absolute; inset:24px; z-index:2; display:grid; grid-template-rows:minmax(0, 1fr) auto; gap:18px; align-content:space-between; }}
    .visual-chip-rail {{ padding-top:14px; border-top:1px solid rgba(255,255,255,.14); }}
    .visual-chips {{ display:flex; flex-wrap:wrap; gap:10px; }}
    .visual-chip {{ padding:9px 13px; border-radius:999px; background:rgba(2,3,10,.62); border:1px solid rgba(255,255,255,.18); color:#e6fbff; font-size:14px; font-weight:700; }}
    .asset-placeholder-stack {{ display:grid; gap:10px; min-width:0; }}
    .asset-placeholder-card {{ display:grid; gap:4px; padding:12px 14px; border:1px dashed rgba(53,231,255,.5); border-radius:16px; background:rgba(2,3,10,.7); color:#dff9ff; font-size:12px; box-shadow:0 12px 34px rgba(0,0,0,.24); }}
    .asset-placeholder-kicker {{ color:var(--cyan); font-size:11px; font-weight:900; letter-spacing:.12em; text-transform:uppercase; }}
    .asset-placeholder-card strong {{ font-size:15px; }}
    .asset-placeholder-slot, .asset-placeholder-hint, .asset-placeholder-prompt {{ color:var(--muted); overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }}
    .timeline-track {{ margin-top:58px; position:relative; display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:22px; max-width:960px; }}
    .timeline-track::before {{ content:""; position:absolute; left:0; right:0; top:31px; height:2px; background:linear-gradient(90deg, var(--cyan), var(--magenta)); opacity:.62; }}
    .timeline-step {{ position:relative; padding-top:76px; }}
    .timeline-dot {{ position:absolute; top:0; left:0; width:62px; height:62px; border-radius:18px; display:grid; place-items:center; background:linear-gradient(135deg, var(--cyan), var(--magenta)); color:#02030a; font-weight:900; box-shadow:0 14px 42px rgba(53,231,255,.22); }}
    .timeline-label {{ display:block; padding:18px 18px 8px; min-height:62px; border-radius:18px 18px 0 0; background:rgba(255,255,255,.065); border:1px solid rgba(255,255,255,.12); border-bottom:0; font-size:22px; }}
    .timeline-detail {{ display:block; padding:0 18px 18px; border-radius:0 0 18px 18px; background:rgba(255,255,255,.065); border:1px solid rgba(255,255,255,.12); border-top:0; color:var(--muted); font-size:17px; }}
    .metric-table {{ margin-top:42px; border-collapse:separate; border-spacing:0 12px; min-width:720px; max-width:940px; }}
    .metric-table th, .metric-table td {{ padding:20px 24px; background:rgba(255,255,255,.07); border-top:1px solid rgba(53,231,255,.18); border-bottom:1px solid rgba(53,231,255,.18); font-size:24px; }}
    .metric-table th {{ text-align:left; color:#dff9ff; border-left:1px solid rgba(53,231,255,.18); border-radius:18px 0 0 18px; }}
    .metric-table td {{ text-align:right; color:var(--cyan); font-weight:900; border-right:1px solid rgba(53,231,255,.18); border-radius:0 18px 18px 0; }}
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
