from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from slideforge.asset_spec import AssetSpec, load_asset_specs

DEFAULT_HARD_CONSTRAINTS = [
    "No text, letters, numbers, charts labels, UI words, logos, brand marks, signatures, or watermarks unless this spec explicitly permits them.",
    "No people, faces, hands, or recognizable copyrighted characters unless this spec explicitly asks for them.",
    "Do not include mock slide text; SlideForge will overlay all Korean/English content deterministically.",
]

DEFAULT_OUTPUT_GUIDANCE = [
    "Generate a high-resolution presentation-ready image with clean edges and strong composition.",
    "Prefer a wide 16:9-friendly composition with safe empty space for slide layout overlays when appropriate.",
    "Keep the result as a standalone visual asset, not a complete slide screenshot.",
]


def write_openai_manual_prompt_pack(*, asset_spec_dir: Path, output_dir: Path) -> dict[str, Any]:
    specs = load_asset_specs(asset_spec_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    prompt_entries: list[dict[str, Any]] = []
    pack_sections = [
        "# OpenAI Images Manual Prompt Pack",
        "",
        "Use these prompts manually in ChatGPT Pro / OpenAI Images. Do not automate the ChatGPT web UI and do not call the OpenAI API for this workflow.",
        "Save generated candidates under the requested run folder using the specified filenames before running `import-manual-assets`.",
        "",
    ]

    for spec in specs:
        prompt_text = render_manual_prompt(spec)
        prompt_path = output_dir / spec.prompt_filename
        prompt_path.write_text(prompt_text, encoding="utf-8")
        entry = {
            "asset_id": spec.asset_id,
            "role": spec.role,
            "target_slide": spec.target_slide,
            "prompt_file": spec.prompt_filename,
            "manual_save_dir": f"manual-generated-assets/{spec.asset_id}/",
            "manual_save_examples": [
                f"manual-generated-assets/{spec.asset_id}/A.png",
                f"manual-generated-assets/{spec.asset_id}/B.png",
                f"manual-generated-assets/{spec.asset_id}/C.png",
            ],
            "source_spec": spec.source_path,
        }
        prompt_entries.append(entry)
        pack_sections.extend([f"## {spec.asset_id}", "", prompt_text, ""])

    (output_dir / "prompt-pack.md").write_text("\n".join(pack_sections).rstrip() + "\n", encoding="utf-8")
    payload = {
        "report_kind": "openai_manual_prompt_pack",
        "provider": "openai_images",
        "generation_mode": "manual_chatgpt_pro",
        "asset_spec_dir": str(asset_spec_dir),
        "output_dir": str(output_dir),
        "asset_count": len(prompt_entries),
        "prompts": prompt_entries,
    }
    (output_dir / "prompt-pack.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload


def render_manual_prompt(spec: AssetSpec) -> str:
    constraints = list(DEFAULT_HARD_CONSTRAINTS)
    if spec.allow_text:
        constraints = [
            "Avoid logos, brand marks, signatures, and watermarks.",
            "Only include text if the asset spec explicitly describes exact intended text; otherwise keep it text-free.",
            "No recognizable copyrighted characters unless explicitly requested.",
        ]
    constraints.extend(spec.hard_constraints)
    output_guidance = [*DEFAULT_OUTPUT_GUIDANCE, *spec.output_guidance]
    palette = ", ".join(spec.palette) if spec.palette else "match the deck reference palette"

    return "\n".join(
        [
            f"# Prompt for `{spec.asset_id}`",
            "",
            "## Copy/paste prompt",
            f"Create a presentation visual asset for role: {spec.role}.",
            f"Target slide: {spec.target_slide}.",
            f"Visual style: {spec.visual_style}.",
            f"Palette: {palette}.",
            "",
            "Hard constraints:",
            *[f"- {item}" for item in constraints],
            "",
            "Output guidance:",
            *[f"- {item}" for item in output_guidance],
            "",
            "User save path instructions:",
            f"- Download 2-4 candidate images from ChatGPT Pro / OpenAI Images.",
            f"- Save them as `manual-generated-assets/{spec.asset_id}/A.png`, `manual-generated-assets/{spec.asset_id}/B.png`, `manual-generated-assets/{spec.asset_id}/C.png`, etc. inside the run directory.",
            f"- Keep the asset id directory name exactly `{spec.asset_id}` so SlideForge can import it deterministically.",
            "",
        ]
    )
