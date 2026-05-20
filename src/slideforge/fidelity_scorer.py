from __future__ import annotations

from dataclasses import asdict, dataclass

_CATEGORY_MAXIMUMS = {
    "background": 20,
    "generated_assets": 20,
    "layout_archetype": 20,
    "typography": 10,
    "data_visuals": 10,
    "korean_readability": 10,
    "technical_validity": 10,
}


@dataclass(frozen=True)
class FidelityScoreInput:
    background: int
    generated_assets: int
    layout_archetype: int
    typography: int
    data_visuals: int
    korean_readability: int
    technical_validity: int


@dataclass(frozen=True)
class FidelityScore:
    total: int
    rating: str
    category_scores: dict[str, int]
    max_score: int = 100

    def to_dict(self) -> dict:
        return asdict(self)


def _rating(total: int) -> str:
    if total >= 85:
        return "high-fidelity candidate"
    if total >= 75:
        return "usable, polish required"
    if total >= 60:
        return "recognizable style but weak fidelity"
    return "not acceptable for template-match production"


def score_fidelity(score_input: FidelityScoreInput) -> FidelityScore:
    category_scores = asdict(score_input)
    for name, score in category_scores.items():
        maximum = _CATEGORY_MAXIMUMS[name]
        if score < 0 or score > maximum:
            raise ValueError(f"{name} score must be between 0 and {maximum}; got {score}")
    total = sum(category_scores.values())
    return FidelityScore(total=total, rating=_rating(total), category_scores=category_scores)
