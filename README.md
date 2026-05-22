# SlideForge

SlideForge is a clean restart of the slide-generation pipeline learned from `hermes-slide-director`.

The project focuses on high-fidelity slide production from design references that may be PPTX templates, slide-preview links, screenshots, images, PDFs, or web pages.

## Project overview

SlideForge is an evidence-first production toolkit for turning source material and visual references into presentation decks. It is not a single image generator and it is not a black-box slide bot. The project separates planning, visual asset generation, deterministic layout composition, approval, QA, and delivery so each stage can be inspected and repeated.

Core ideas:

- **Reference-aware production:** extract design grammar from template observations and map user content into slide archetypes instead of generating arbitrary slides.
- **Deterministic text/layout ownership:** Korean/English text, tables, charts, metrics, diagrams, and PPTX structure are produced by SlideForge/composer code, not baked into generated images.
- **Asset approval before assembly:** visual candidates become durable records in `asset-generation-report.json`, are reviewed in `asset-review-board.html`/`.md`, then selected in `approved-assets.json` before being applied to a deck.
- **Evidence-first delivery:** every run should leave machine-readable reports for manifests, browser plans/captures, PPTX gates/exports, asset approvals, summaries, and fidelity checks.
- **Provider-routed visuals:** OpenAI Images through manual ChatGPT Pro generation is the default v2 workflow; ComfyUI and other providers remain optional candidate sources rather than the slide-production core.

Typical output artifacts include `deck.json`, `deck.html`, optional `.pptx`, screenshots, review boards, approval reports, fidelity reports, run summaries, and portable evidence packs.

## Fixed production architecture

```text
Design analysis / planning:
  JARVIS + hermes-slide-director learnings

High-quality graphical assets:
  Visual Asset Approval Pipeline v2
  - default: OpenAI Images via manual ChatGPT Pro generation and SlideForge import
  - fallback/special cases: ComfyUI local/private/high-control assets

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

### Visual asset providers

SlideForge treats image generation as a provider-routed candidate source, not as the slide composer itself.

Default v2 route:

- SlideForge writes OpenAI Images prompt packs from asset specs.
- The operator manually uses ChatGPT Pro / OpenAI Images in the browser.
- Downloaded images are saved under the run directory and imported into the same approval gate as every other candidate.

ComfyUI remains useful for:

- local/private generation where assets cannot leave the workstation
- high-control model/workflow experiments
- cases where the operator wants to use the ComfyUI UI as the visual review surface
- fallback production when OpenAI Images is unavailable or not appropriate

All generated assets should be text-free unless a spec explicitly allows otherwise. Korean text, tables, charts, and diagrams should be overlaid deterministically by the slide composer.

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

## Production pipeline history and v2 rationale

### What happened in the earlier version

The first production direction treated ComfyUI as the primary source for high-quality graphical assets. That was attractive because it can run locally and gives strong control over models/workflows, but practical slide runs exposed several problems:

- **Quality mismatch:** high-quality standalone image generation did not automatically improve slide-reference similarity. Some ComfyUI-heavy attempts scored worse than simpler HTML/CSS/SVG layout skeletons because generated assets changed the visual language too much.
- **Operational overhead:** local model setup, workflow tuning, GPU/runtime management, and output-path tracking created extra work before a deck could even enter normal review.
- **Pipeline brittleness:** asset generation, candidate review, and final deck assembly were too tightly associated with one provider. If ComfyUI was unavailable or produced weak assets, the whole production path felt blocked.
- **Text risk:** generated images can contain unwanted letters, numbers, logos, watermarks, or pseudo-labels. SlideForge needs deterministic text, charts, and Korean copy controlled by the composer, not by image models.
- **Cost/account reality:** the operator already has ChatGPT Pro and can manually use OpenAI Images, while automated API usage would require separate API billing and credentials.

### How the design changed

The pipeline name stayed the same, but the asset-generation stage became provider-routed and versioned as Visual Asset Approval Pipeline v2.

The default v2 flow is:

```text
asset-specs/*.json
  -> generate-openai-manual-prompts
  -> openai-manual-prompts/prompt-pack.md
  -> operator manually generates images in ChatGPT Pro / OpenAI Images
  -> manual-generated-assets/<asset_id>/A.png, B.png, C.png
  -> import-manual-assets
  -> asset-generation-report.json
  -> build-asset-review-board
  -> approve-assets
  -> approved-assets.json
  -> apply-approved-assets / deck assembly / QA evidence
```

This keeps image generation as a candidate source while preserving the durable review/approval/apply artifacts already used by the project.

### Why this design is better

- **Uses the available paid tool without pretending it is an API:** ChatGPT Pro / OpenAI Images is used manually in the browser; SlideForge does not automate the web UI, store cookies, or call the OpenAI API.
- **Keeps provenance:** imported candidates record `provider=openai_images`, `source=manual_openai_images`, `generation_mode=manual_chatgpt_pro`, prompt file, license note, asset id, candidate id, and final path.
- **Preserves approval discipline:** every visual still goes through `asset-review-board` and `approved-assets.json`; no image is silently inserted into the deck.
- **Keeps layout deterministic:** image models produce text-free visual objects; SlideForge owns slide text, charts, tables, and final composition.
- **Allows fallback and future providers:** ComfyUI, deterministic SVG, Recraft, Ideogram, FLUX, or a future OpenAI API provider can all become candidate sources without changing the approval contract.
- **Improves operator handoff:** if no candidates are imported, the review board now gives explicit save-path and rerun instructions instead of becoming a dead end.

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

## Visual asset approval gate

The review board is the default durable review surface for v2. ComfyUI UI, local files, manual OpenAI Images downloads, deterministic SVG outputs, or messaging review can all feed candidate assets into the same gate; the source of truth is always `approved-assets.json`.

```text
Provider/manual candidate source
  -> generate-asset-candidates
  -> asset-generation-report.json
  -> build-asset-review-board
  -> asset-review-board.html / asset-review-board.md
  -> approve-assets
  -> approved-assets.json
  -> apply-approved-assets
  -> deck.approved.json
  -> run-local / HTML / PPTX / evidence
```

Create an asset candidate report from already-generated ComfyUI/diagram files:

```bash
PYTHONPATH=src python -m slideforge.cli generate-asset-candidates \
  --run-id <run-id> \
  --candidate "slide-01=A:runs/<run-id>/generated-assets/slide-01-a.png:comfyui_ui" \
  --candidate "slide-01=B:runs/<run-id>/generated-assets/slide-01-b.png:comfyui_ui" \
  --output runs/<run-id>/asset-generation-report.json
```

Build the visual review board:

```bash
PYTHONPATH=src python -m slideforge.cli build-asset-review-board \
  --candidates runs/<run-id>/asset-generation-report.json \
  --deck runs/<run-id>/deck.json \
  --output-html runs/<run-id>/asset-review-board.html \
  --output-md runs/<run-id>/asset-review-board.md \
  --recommended "slide-01=B"
```

Record a ComfyUI UI selection from an asset candidate report:

```bash
PYTHONPATH=src python -m slideforge.cli approve-assets \
  --candidates runs/<run-id>/asset-generation-report.json \
  --selection "slide-01=B,slide-03=A" \
  --output runs/<run-id>/approved-assets.json \
  --approved-by user \
  --approval-mode explicit_user
```

Apply only approved assets to the deck:

```bash
PYTHONPATH=src python -m slideforge.cli apply-approved-assets \
  --deck runs/<run-id>/deck.json \
  --approved-assets runs/<run-id>/approved-assets.json \
  --output runs/<run-id>/deck.approved.json \
  --report-output runs/<run-id>/approved-asset-application-report.json
```


### Manual OpenAI Images prompt/import workflow (v2)

The Visual Asset Approval Pipeline also supports manual ChatGPT Pro / OpenAI Images generation without automating the web UI, calling the OpenAI API, or renaming the pipeline. SlideForge only prepares prompts, imports files the operator downloaded manually, and keeps the existing review/approval artifacts.

Create JSON asset specs under `runs/<run-id>/asset-specs/`, then generate the manual prompt pack:

```bash
PYTHONPATH=src python -m slideforge.cli generate-openai-manual-prompts \
  --asset-spec-dir runs/<run-id>/asset-specs \
  --output-dir runs/<run-id>/openai-manual-prompts
```

This writes `prompt-pack.md`, `prompt-pack.json`, and one `<asset_id>.md` prompt per spec. Each prompt includes the asset role, target slide, style/palette, text/logo/watermark constraints, output guidance, and save-path instructions.

After manually generating images in ChatGPT Pro / OpenAI Images, save candidates as:

```text
runs/<run-id>/manual-generated-assets/<asset_id>/A.png
runs/<run-id>/manual-generated-assets/<asset_id>/B.png
runs/<run-id>/manual-generated-assets/<asset_id>/C.png
```

Import them into the existing candidate report shape:

```bash
PYTHONPATH=src python -m slideforge.cli import-manual-assets \
  --run-dir runs/<run-id> \
  --asset-spec-dir runs/<run-id>/asset-specs \
  --input-dir runs/<run-id>/manual-generated-assets \
  --output-report runs/<run-id>/asset-generation-report.json
```

The import step copies supported images into `runs/<run-id>/imported-assets/<asset_id>-<candidate_id>.<ext>`, records candidates with `provider=openai_images`, `source=manual_openai_images`, `generation_mode=manual_chatgpt_pro`, prompt-file and license-note metadata, warns for missing asset folders, and ignores unsupported extensions. The existing `build-asset-review-board`, `approve-assets`, and `apply-approved-assets` commands remain the approval/apply flow.

`generate-asset-candidates` validates existing candidate files and writes an `asset-generation-report.json` that can represent ComfyUI UI history selections, deterministic diagram outputs, or candidates delivered through another channel. `build-asset-review-board` turns that report into a user-facing HTML/Markdown board with actual candidate images, slide titles, source/notes, a recommended badge, and an approval command hint.

`approve-assets` validates selected candidate ids and asset files, then records `approved_by`, `approval_mode` (`explicit_user`, `jarvis_recommended`, or `autonomous`), candidate source, and selected asset paths. `apply-approved-assets` writes a new deck JSON with `asset_path` applied only to matching approved slide ids and records unmatched approvals in the application report.

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

## Current pipeline
```text
Reference Input
  ↓
Template Deep Analyzer
  ↓
Design Spec
  ↓
Content-to-Archetype Mapper
  ↓
Asset Spec Generator
  ↓
Visual Asset Approval Pipeline v2
  - OpenAI Images manual prompt/import path by default
  - ComfyUI/local/provider candidates when appropriate
  ↓
Guizang HTML Composer
  ↓
Asset Approval Application
  ↓
Visual QA + Fidelity Scoring + Evidence Summary
  ↓
Optional PPTX Delivery
```

## First milestone

Phase 1 should prove that this repository can take a graphic-heavy design reference, generate or define appropriate visual asset briefs, compose a high-fidelity HTML presentation with `codex-guizang-html`, and score template similarity with a 100-point fidelity rubric.

Current Phase 1 primitives:

- `slideforge.design_spec` — structured colors, typography, slide archetypes, background layers, and graphic motifs.
- `slideforge.template_analyzer` — converts template observations into a design spec.
- `slideforge.archetype_mapper` — maps content sections to template-like slide archetypes.
- `slideforge.asset_brief` — defines text-free local/provider asset briefs.
- `slideforge.asset_spec` — normalizes visual asset slots for provider-routed generation.
- `slideforge.manual_prompts` — writes ChatGPT Pro / OpenAI Images prompt packs from asset specs.
- `slideforge.manual_assets` — imports manually downloaded OpenAI Images candidates into the approval report shape.
- `slideforge.asset_approval` — builds review boards, records approvals, and applies approved assets.
- `slideforge.fidelity_scorer` — scores output fidelity with the 100-point rubric.
- `slideforge.cli` — writes design-spec, asset, approval, run, and fidelity artifacts.

Example local checks:

```bash
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m slideforge.cli --help
```
