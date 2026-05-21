from __future__ import annotations

from html import escape

from slideforge.schemas import (
    AssetPlaceholder,
    ChartDatum,
    ComparisonColumn,
    ComparisonRow,
    HtmlDeck,
    HtmlSlide,
    MetricRow,
    TimelineStep,
    VisualChip,
)

__all__ = [
    "AssetPlaceholder",
    "ChartDatum",
    "ComparisonColumn",
    "ComparisonRow",
    "HtmlDeck",
    "HtmlSlide",
    "MetricRow",
    "TimelineStep",
    "VisualChip",
    "compose_html_deck",
]


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
    if slide.asset_path:
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


def _chart_data_from_bullets(bullets: list[str]) -> list[ChartDatum]:
    data = []
    for item in bullets:
        label, sep, value = item.partition("|")
        if not sep:
            continue
        try:
            numeric_value = float(value.strip())
        except ValueError:
            continue
        data.append(ChartDatum(label=label.strip(), value=numeric_value))
    return data


def _format_chart_value(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:g}"


def _render_chart(slide: HtmlSlide) -> str:
    data = slide.chart_data or _chart_data_from_bullets(slide.bullets)
    if not data:
        return _render_default_bullets(slide)

    max_value = max((abs(item.value) for item in data), default=0) or 1
    row_height = 50
    chart_width = 560
    chart_height = max(len(data) * row_height, row_height)
    rows = []
    legend_items = []
    for idx, item in enumerate(data):
        width = round((abs(item.value) / max_value) * (chart_width - 112), 1)
        y = idx * row_height + 10
        value_text = _format_chart_value(float(item.value))
        note = f'<span class="chart-note">{escape(item.note)}</span>' if item.note else ""
        color_label = f'<span class="chart-color-label">{escape(item.color)}</span>' if item.color else ""
        rows.append(
            f'''          <g class="bar-row" data-chart-label="{escape(item.label)}" data-chart-value="{escape(value_text)}" data-chart-color="{escape(item.color)}">
            <text x="0" y="{y + 20}" class="bar-label">{escape(item.label)}</text>
            <rect x="112" y="{y}" width="{width}" height="24" rx="8" class="bar-rect bar-rect-{idx % 4}" />
            <text x="{120 + width}" y="{y + 20}" class="bar-value">{escape(value_text)}</text>
          </g>'''
        )
        legend_items.append(
            f'''          <li><span class="chart-legend-label">{escape(item.label)}</span><strong>{escape(value_text)}</strong>{note}{color_label}</li>'''
        )
    return f'''
      <div class="chart-panel" data-chart-kind="{escape(slide.archetype)}" data-series-count="{len(data)}">
        <svg class="bar-chart" viewBox="0 0 {chart_width} {chart_height}" role="img" aria-label="{escape(slide.title)} chart">
{chr(10).join(rows)}
        </svg>
        <ul class="chart-legend">
{chr(10).join(legend_items)}
        </ul>
      </div>'''


def _comparison_rows_from_bullets(bullets: list[str]) -> tuple[list[ComparisonColumn], list[ComparisonRow]]:
    rows = []
    max_values = 0
    for item in bullets:
        parts = [part.strip() for part in item.split("|")]
        if not parts or not parts[0]:
            continue
        values = parts[1:]
        max_values = max(max_values, len(values))
        rows.append(ComparisonRow(label=parts[0], values=values))
    columns = [ComparisonColumn(label=f"Option {idx}") for idx in range(1, max_values + 1)]
    return columns, rows


def _render_comparison_matrix(slide: HtmlSlide) -> str:
    columns = slide.comparison_columns
    rows = slide.comparison_rows
    if not rows:
        columns, rows = _comparison_rows_from_bullets(slide.bullets)
    if not rows:
        return _render_default_bullets(slide)
    column_count = max(len(columns), max((len(row.values) for row in rows), default=0))
    if not columns:
        columns = [ComparisonColumn(label=f"Option {idx}") for idx in range(1, column_count + 1)]
    elif len(columns) < column_count:
        columns = columns + [
            ComparisonColumn(label=f"Option {idx}") for idx in range(len(columns) + 1, column_count + 1)
        ]

    header = "\n".join(
        f'''          <th scope="col"><span>{escape(column.label)}</span>{f'<small>{escape(column.note)}</small>' if column.note else ''}</th>'''
        for column in columns
    )
    body_rows = []
    for row in rows:
        values = list(row.values) + ["—"] * (len(columns) - len(row.values))
        cells = "\n".join(f"          <td>{escape(value)}</td>" for value in values[: len(columns)])
        row_note = f'<small>{escape(row.note)}</small>' if row.note else ""
        body_rows.append(
            f'''        <tr>
          <th scope="row"><span>{escape(row.label)}</span>{row_note}</th>
{cells}
        </tr>'''
        )
    return f'''
      <table class="comparison-matrix" data-column-count="{len(columns)}">
        <thead>
        <tr>
          <th scope="col">Criteria</th>
{header}
        </tr>
        </thead>
        <tbody>
{chr(10).join(body_rows)}
        </tbody>
      </table>'''


def _render_archetype_body(slide: HtmlSlide) -> str:
    if slide.archetype in {"visual_band", "architecture_visual", "cover"}:
        return _render_visual_band(slide)
    if slide.archetype == "timeline":
        return _render_timeline(slide)
    if slide.archetype in {"kpi_table", "table"}:
        return _render_metric_table(slide)
    if slide.archetype in {"chart", "bar_chart"}:
        return _render_chart(slide)
    if slide.archetype in {"comparison_matrix", "matrix"}:
        return _render_comparison_matrix(slide)
    return _render_default_bullets(slide)


def _render_slide(slide: HtmlSlide, index: int, total: int) -> str:
    if slide.archetype == "architecture_visual" and slide.asset_path:
        return f'''    <section class="slide architecture-diagram-slide" data-slide-id="{escape(slide.slide_id)}" data-archetype="{escape(slide.archetype)}">
      <img class="asset-diagram" src="{escape(slide.asset_path)}" alt="{escape(slide.title)}" />
      <div class="page-count">{index} / {total}</div>
    </section>'''
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
    .architecture-diagram-slide {{ padding:0; display:none; background:#02030a; }}
    .architecture-diagram-slide.active {{ display:block; }}
    .architecture-diagram-slide::before {{ display:none; }}
    .asset-diagram {{ position:absolute; inset:0; width:100%; height:100%; object-fit:cover; }}
    .architecture-diagram-slide .page-count {{ position:absolute; right:32px; bottom:24px; z-index:2; color:rgba(247,251,255,.72); font-size:16px; font-weight:700; }}
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
    .chart-panel {{ margin-top:26px; display:grid; grid-template-columns:1.4fr .9fr; gap:20px; align-items:start; max-width:960px; }}
    .bar-chart {{ width:100%; min-height:240px; padding:16px; border:1px solid rgba(53,231,255,.2); border-radius:22px; background:rgba(255,255,255,.055); overflow:visible; }}
    .bar-label {{ fill:#dff9ff; font-size:16px; font-weight:800; }}
    .bar-value {{ fill:var(--cyan); font-size:16px; font-weight:900; }}
    .bar-rect {{ fill:var(--cyan); opacity:.82; }}
    .bar-rect-1 {{ fill:var(--magenta); }}
    .bar-rect-2 {{ fill:#9df071; }}
    .bar-rect-3 {{ fill:#ffd166; }}
    .chart-legend {{ margin:0; display:grid; gap:8px; }}
    .chart-legend li {{ max-width:none; padding:11px 13px; display:grid; grid-template-columns:1fr auto; gap:4px 10px; font-size:15px; }}
    .chart-note, .chart-color-label {{ color:var(--muted); font-size:12px; grid-column:1 / -1; }}
    .comparison-matrix {{ margin-top:38px; border-collapse:separate; border-spacing:0; min-width:780px; max-width:1000px; overflow:hidden; border:1px solid rgba(53,231,255,.2); border-radius:24px; background:rgba(255,255,255,.045); }}
    .comparison-matrix th, .comparison-matrix td {{ padding:16px 18px; border-right:1px solid rgba(255,255,255,.1); border-bottom:1px solid rgba(255,255,255,.1); font-size:18px; vertical-align:top; }}
    .comparison-matrix th {{ text-align:left; color:#dff9ff; font-weight:900; background:rgba(53,231,255,.08); }}
    .comparison-matrix td {{ color:#f7fbff; }}
    .comparison-matrix small {{ display:block; margin-top:5px; color:var(--muted); font-size:13px; font-weight:600; }}
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
