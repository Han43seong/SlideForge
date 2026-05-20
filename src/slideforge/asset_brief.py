from __future__ import annotations

from dataclasses import asdict, dataclass, field
import re

_TEXT_REQUEST_RE = re.compile(
    r"\b(render|write|add|include|place)\b[^.]{0,40}\b(text|title|letters|words|korean|hangul|한글|제목)\b|\b(text|title|letters|words|한글|제목)\b[^.]{0,40}\b(render|write|add|include|place)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class AssetBrief:
    slide_id: str
    asset_type: str
    prompt: str
    negative_prompt: str = "text, letters, logo, watermark"
    aspect_ratio: str = "16:9"
    output_hint: str | None = None
    text_policy: str = "text-free"

    def __post_init__(self) -> None:
        if self.text_policy != "text-free":
            raise ValueError("asset briefs must use text-free policy")
        if not self.slide_id.strip():
            raise ValueError("slide_id is required")
        if not self.asset_type.strip():
            raise ValueError("asset_type is required")
        if not self.prompt.strip():
            raise ValueError("prompt is required")
        if _TEXT_REQUEST_RE.search(self.prompt):
            raise ValueError("ComfyUI asset prompts must be text-free; overlay text deterministically")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class AssetBriefSet:
    briefs: list[AssetBrief] = field(default_factory=list)

    def to_comfyui_queue_payload(self, seed: int | None = None) -> dict:
        payload = {"briefs": [brief.to_dict() for brief in self.briefs]}
        if seed is not None:
            payload["seed"] = seed
        return payload
