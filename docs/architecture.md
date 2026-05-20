# Architecture

## Purpose

This repository exists to rebuild the slide-generation system around a narrower and cleaner production architecture:

- `codex-guizang-html` for primary high-fidelity composition.
- `codex-presentation-pptx` for PPTX delivery.
- ComfyUI for graphical asset generation.
- JARVIS/Hermes for planning, routing, verification, and acceptance.

## Modules

```text
src/slideforge/
  template_analyzer.py       # extract design grammar from reference inputs
  design_spec.py             # structured color/layout/type/style rules
  archetype_mapper.py        # map source content to template-like slide archetypes
  asset_brief.py             # generate text-free asset briefs for ComfyUI
  comfyui_handoff.py         # evidence-first ComfyUI REST handoff/report seam
  guizang_html_composer.py   # primary HTML deck composition route
  pptx_delivery.py           # PPTX output route and template-native adapter
  fidelity_scorer.py         # 100-point template similarity scoring
```

## Key principle

Do not let image generation own facts or text.

ComfyUI should produce visual assets only. Deterministic code should own:

- Korean titles and body copy
- tables
- charts
- timelines
- architecture diagrams
- slide counters and presentation controls
- evidence metadata

## Fidelity scoring rubric

```text
Background fidelity:              20
3D art / generated asset fidelity: 20
Layout archetype match:           20
Typography hierarchy:             10
Tables/charts/infographics:       10
Readability / Korean layout:      10
Technical validity / export:      10
Total:                           100
```

Interpretation:

```text
85+: high-fidelity candidate
75-84: usable, polish required
60-74: recognizable style but weak fidelity
<60: not acceptable for template-match production
```

## Initial target workflow

1. Accept a reference image/link/PDF/PPTX.
2. Build a deep design analysis and design spec.
3. Map content into slide archetypes.
4. Create ComfyUI asset briefs for text-free backgrounds and 3D art.
5. Write a ComfyUI handoff report; optionally submit a workflow API JSON to an already-running local endpoint while treating queued work as pending until files exist.
6. Compose an HTML presentation through the guizang route.
7. Score template similarity and readability.
8. If required, deliver PPTX through the presentation-pptx route.
