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

PPTX outputs require a visual render gate before final acceptance. SlideForge now writes a dependency-free `pptx-delivery-gate.json` contract for smoke runs or via `slideforge pptx-delivery-gate`; this records the source deck, desired PPTX path, available local validation tools, static/visual checks planned, status (`available`, `unavailable`, or `pending`), and blockers. The gate is strategy evidence only and does not claim PPTX export or visual rendering occurred.

SlideForge also exposes a real PPTX generation seam through `export-pptx`. Actual `.pptx` output requires the optional `pptx` extra (`python-pptx`) to be installed by an approved operator; the command never installs dependencies automatically and never creates a fake PPTX when the dependency is missing. It always writes a JSON report with dependency status, output path, file existence/size, expected/generated slide counts, and blockers. Renderer evidence is only attached as an availability path when `pptx-glimpse` is already on `PATH`; otherwise the report says that approved `pptx-glimpse` installation is required for visual evidence.

```bash
# Approved install step, if desired outside no-install tasks:
uv pip install -e '.[pptx]'
# If using a Python environment with pip available, `python -m pip install -e '.[pptx]'` is also fine.

PYTHONPATH=src python -m slideforge.cli export-pptx \
  --deck runs/<run-id>/deck.json \
  --output runs/<run-id>/deck.pptx \
  --report-output runs/<run-id>/pptx-export-report.json \
  --run-id <run-id>
```

The first-pass native PPTX seam maps deck title, subtitle, bullets, metrics, timeline, chart, comparison, and visual-chip content into deterministic PowerPoint shapes/text with Korean-capable font metadata where possible. It is not a visual parity claim; use renderer evidence or manual QA before final delivery.

## ComfyUI handoff report

`generate-asset-briefs` produces the text-free payload consumed by the ComfyUI handoff seam. `comfyui-handoff` writes evidence for an already-running ComfyUI-compatible REST endpoint without installing ComfyUI, downloading models, or claiming image generation when no output file exists.

```bash
PYTHONPATH=src python -m slideforge.cli generate-asset-briefs \
  --design-spec design-spec.json \
  --mappings mappings.json \
  --output runs/<run-id>/asset-briefs.json

PYTHONPATH=src python -m slideforge.cli comfyui-handoff \
  --asset-briefs runs/<run-id>/asset-briefs.json \
  --output-dir runs/<run-id> \
  --endpoint http://127.0.0.1:8188
```

The report records `provider`, `endpoint`, `status`, `server_available`, `workflow_path`, `generated_assets`, `pending_assets`, `failed_assets`, `blockers`, and `checked_at`. Optional submission is explicit: provide `--workflow workflow-api.json --execute`. Submitted prompts remain pending until concrete output files exist at their `output_hint`; Korean text, numbers, labels, charts, and PPTX structure stay owned by deterministic SlideForge composition.

## Real browser screenshot capture

`smoke-html` still writes the dependency-free `browser-regression-plan.json`. For real PNG evidence, install the optional browser extra and Chromium, then run the Playwright Chromium capture command against a generated HTML deck:

```bash
python -m pip install -e '.[browser]'
python -m playwright install chromium
PYTHONPATH=src python -m slideforge.cli capture-screenshots \
  --deck-html runs/<run-id>/deck.html \
  --output-dir runs/<run-id>/browser-capture \
  --expected-slide-count 5
```

The runner writes `browser-regression-report.json` plus `slide-XX.png` files. The report records `capture_mode: real_playwright_chromium`, detected slide count, viewport, browser name, console errors, capture status, and per-slide ids/archetypes when the HTML exposes `data-slide-id` and `data-archetype`.

## Local deterministic handoff runner

The full dependency-free operator path is now available as one source-material command:

```bash
PYTHONPATH=src python -m slideforge.cli run-source-local \
  --source source.md \
  --title "폐쇄망 AI 운영 전략" \
  --runs-dir runs \
  --run-id <run-id>
```

`run-source-local` writes deterministic handoff inputs to `runs/<run-id>-input/sections.json` and `runs/<run-id>-input/deck.json`, then writes smoke run artifacts and summaries under `runs/<run-id>/`. Its JSON stdout reports `run_dir`, `sections_path`, `deck_input_path`, generated artifacts, status, blockers, warnings, and missing external evidence. Use `--input-output-dir` only when an operator explicitly wants the handoff files outside the default `runs/<run-id>-input` location. It composes the same primitives operators can still run manually:

```text
prepare-sections -> prepare-deck -> run-local -> summarize-run
```

When the operator also has local design-reference observations JSON, use the all-in-one design-source path:

```bash
PYTHONPATH=src python -m slideforge.cli run-design-source-local \
  --source source.md \
  --observations observations.json \
  --design-name "Reference design" \
  --title "폐쇄망 AI 운영 전략" \
  --runs-dir runs \
  --run-id <run-id>
```

`run-design-source-local` first builds `runs/<run-id>-input/design-spec.json` from the local observations, then uses that design spec while writing `sections.json`, `deck.json`, and the smoke run under `runs/<run-id>/`. Its compact JSON stdout includes `run_dir`, `design_spec_path`, `sections_path`, `deck_input_path`, generated artifacts, summary status, blockers, warnings, and missing external evidence. Use `--input-output-dir` only as an explicit handoff-directory override if the operator wants `design-spec.json`, `sections.json`, and `deck.json` outside the default `runs/<run-id>-input` location. This is deterministic design-spec preparation and local source handoff only; it is not provider inference, visual-reference understanding, browser evidence, PPTX evidence, or ComfyUI generation evidence.

These shortcuts do not replace final browser screenshot capture, PPTX export/render evidence, ComfyUI image generation evidence, or fidelity scoring. A smoke-only run is expected to remain `needs_visual_evidence` until those real artifacts are attached.

To share or archive the completed local run directory, package the existing artifacts into a portable evidence pack:

```bash
PYTHONPATH=src python -m slideforge.cli export-evidence-pack \
  --run-dir runs/<run-id> \
  --output runs/<run-id>-evidence-pack.zip \
  --manifest-output runs/<run-id>-evidence-pack-manifest.json
```

`export-evidence-pack` is dependency-free and writes a `.zip` with an embedded `evidence-pack-manifest.json` plus optional sidecar manifest. The manifest lists each packaged regular file with `relative_path`, `size_bytes`, and `sha256`, preserves `run-summary.json` status/warnings/blockers/missing external evidence when present, skips symlinks instead of following them, and rejects outputs inside the run directory to avoid recursive packaging. It packages evidence only; it does not generate missing browser, PPTX/render, ComfyUI, or fidelity evidence, so smoke-only packs should honestly preserve `needs_visual_evidence`.

`prepare-sections` turns local plain text/Markdown-like source material into structured section JSON that `prepare-deck` can consume. It is deterministic and extractive: `#`/`##` headings and practical non-empty title lines become section headings, `-`, `*`, and `•` lines become bullets, ids are normalized from headings with duplicate-safe suffixes, and no provider output or unsupported facts are invented. Intent inference uses conservative keyword aliases: timeline/schedule/roadmap/일정/로드맵 -> `timeline`, KPI/metric/table/지표/테이블/표 형식 -> `table`, comparison/compare/vs/비교/대비 -> `comparison`, architecture/system/flow/아키텍처/구조/시스템/흐름 -> `architecture`, visual/image/diagram/비주얼/이미지/다이어그램 -> `visual`; otherwise `--default-intent` is used (`policy` by default).

```bash
PYTHONPATH=src python -m slideforge.cli prepare-sections \
  --source source.md \
  --output runs/<run-id>-input/sections.json \
  --default-intent policy
```

`prepare-deck` turns structured sections into an HtmlDeck-compatible JSON without calling providers or inventing unsupported claims. Sections are a JSON list with `id`, `heading`, `intent`, and optional list-of-string `bullets`; `--design-spec` may provide available archetypes, otherwise conservative intent aliases and `text_explainer` fallback are used.

```bash
PYTHONPATH=src python -m slideforge.cli prepare-deck \
  --title "폐쇄망 AI 운영 전략" \
  --sections runs/<run-id>-input/sections.json \
  --output runs/<run-id>-input/deck.json
```

`run-local` is the one-command local operator handoff path for an existing HtmlDeck-compatible JSON deck. It is dependency-free: it writes the smoke HTML run, manifest/evidence index, browser regression plan, PPTX delivery gate, and default `run-summary.json` plus `run-summary.md` in the run directory. It does not perform final visual, PPTX render, or ComfyUI acceptance; those remain warnings/next actions until real evidence artifacts are attached.

```bash
PYTHONPATH=src python -m slideforge.cli run-local \
  --deck runs/<run-id>-input/deck.json \
  --runs-dir runs \
  --run-id <run-id>
```

## Run evidence summary

`summarize-run` aggregates existing run artifacts into one operator-readable JSON report and, when requested, a plain Markdown report. It is dependency-free and evidence-first: missing optional artifacts become warnings or pending next actions, and reports never claim browser, PPTX, or ComfyUI evidence unless the corresponding artifact records it.

```bash
PYTHONPATH=src python -m slideforge.cli summarize-run \
  --run-dir runs/<run-id> \
  --output runs/<run-id>/run-summary.json \
  --markdown-output runs/<run-id>/run-summary.md
```

The summary inspects `manifest.json`, `evidence-index.md`, `deck.json`, `deck.html`, browser plans/capture reports, PPTX gate/export reports, ComfyUI handoff reports, and naturally named fidelity score/report files. Top-level statuses include `ready`, `ready_with_warnings`, `needs_visual_evidence`, and `blocked`.

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
