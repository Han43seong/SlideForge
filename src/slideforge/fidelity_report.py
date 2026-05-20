from __future__ import annotations

from slideforge.fidelity_scorer import FidelityScore


def _verdict(total: int) -> str:
    if total >= 85:
        return "PASS"
    if total >= 75:
        return "PASS_WITH_WARNINGS"
    if total >= 60:
        return "WEAK_PASS"
    return "FAIL"


def render_fidelity_report(score: FidelityScore, title: str = "SlideForge fidelity report") -> str:
    lines = [
        f"# {title}",
        "",
        f"- Total score: **{score.total} / {score.max_score}**",
        f"- Verdict: **{_verdict(score.total)}**",
        f"- Rating: {score.rating}",
        "",
        "## Category scores",
        "",
        "| Category | Score |",
        "| --- | ---: |",
    ]
    for category, value in score.category_scores.items():
        lines.append(f"| `{category}` | {value} |")
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            _interpretation(score.total),
        ]
    )
    return "\n".join(lines) + "\n"


def _interpretation(total: int) -> str:
    if total >= 85:
        return "Production-quality candidate. Proceed to visual QA and delivery packaging."
    if total >= 75:
        return "Usable candidate with visible polish gaps. Proceed only with reviewer notes."
    if total >= 60:
        return "Recognizable direction, but template fidelity is not strong enough for final delivery."
    return "Reject for production. Rework design analysis, assets, or layout before continuing."
