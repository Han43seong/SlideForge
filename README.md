# SlideForge

SlideForge is a clean restart of the slide-generation pipeline learned from `hermes-slide-director`.

The project focuses on high-fidelity slide production from design references that may be PPTX templates, slide-preview links, screenshots, images, PDFs, or web pages.

## Fixed production architecture

```text
Design analysis / planning:
  JARVIS + hermes-slide-director learnings

High-quality graphical assets:
  ComfyUI

Primary slide production:
  codex-guizang-html

PPTX delivery:
  codex-presentation-pptx
```

## Role separation

### JARVIS / Director

- Classifies input type and output requirement.
- Extracts template/design grammar.
- Maps user content into slide archetypes.
- Defines quality gates and evidence requirements.
- Performs final verification and acceptance decisions.

### ComfyUI asset forge

ComfyUI is not the slide composer. It generates visual assets such as:

- aurora / neon / cinematic backgrounds
- 3D glass technology objects
- section-divider art
- visual bands
- style-matched infographic or icon assets

Generated assets should be text-free. Korean text, tables, charts, and diagrams should be overlaid deterministically by the slide composer.

### codex-guizang-html composer

Primary production route for:

- high-fidelity HTML decks
- custom presentation mode
- browser visual QA
- PDF/export-oriented prototypes
- precise layout, typography, tables, charts, and SVG diagrams

### codex-presentation-pptx delivery

PPTX route for:

- real PPTX template-native/R22-style editing
- final `.pptx` delivery
- recreation of an approved HTML prototype as PPTX

PPTX outputs require a visual render gate before final acceptance.

## Non-production routes

- `codex-reveal-playwright`: fallback/export experiment only.
- `codex-editable-html-slides`: excluded from competitive production selection.

## Initial pipeline

```text
Reference Input
  ↓
Template Deep Analyzer
  ↓
Design Spec
  ↓
Content-to-Archetype Mapper
  ↓
Asset Brief Generator
  ↓
ComfyUI Asset Forge
  ↓
Guizang HTML Composer
  ↓
Visual QA + Fidelity Scoring
  ↓
Optional PPTX Delivery
```

## First milestone

Phase 1 should prove that this repository can take a graphic-heavy design reference, generate or define appropriate visual asset briefs, compose a high-fidelity HTML presentation with `codex-guizang-html`, and score template similarity with a 100-point fidelity rubric.

Current Phase 1 primitives:

- `slideforge.design_spec` — structured colors, typography, slide archetypes, background layers, and graphic motifs.
- `slideforge.template_analyzer` — converts template observations into a design spec.
- `slideforge.archetype_mapper` — maps content sections to template-like slide archetypes.
- `slideforge.asset_brief` — defines text-free ComfyUI asset briefs.
- `slideforge.fidelity_scorer` — scores output fidelity with the 100-point rubric.
- `slideforge.cli` — writes design-spec and fidelity-score JSON artifacts.

Example local checks:

```bash
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m slideforge.cli --help
```
