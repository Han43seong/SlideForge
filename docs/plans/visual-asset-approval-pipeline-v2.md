# Visual Asset Approval Pipeline v2 Implementation Plan

> **For Hermes:** Use subagent-driven-development or Codex/OMX producer-reviewer loop to implement this plan task-by-task.

**Goal:** Extend the existing Visual Asset Approval Pipeline to support OpenAI Images manual web generation via ChatGPT Pro, without renaming the overall pipeline.

**Architecture:** SlideForge remains responsible for reference analysis, asset slot/spec creation, prompt-pack generation, manual asset import, review board, approval, deck assembly, and evidence-first QA. The image generation step is performed manually by the user in ChatGPT Pro/OpenAI Images, then downloaded files are imported as first-class asset candidates.

**Tech Stack:** Python, existing SlideForge CLI, JSON artifacts, HTML review board, pytest.

---

## Implementation status

Implemented in this repo:

- Asset spec loading/normalization from `runs/<run_id>/asset-specs` or any `--asset-spec-dir`.
- `generate-openai-manual-prompts` for `prompt-pack.md`, `prompt-pack.json`, and per-asset prompt files.
- `import-manual-assets` for manually downloaded ChatGPT Pro / OpenAI Images candidates with deterministic `imported-assets/<asset_id>-<candidate_id>.<ext>` copies.
- Existing review board rendering now displays provider/source/generation mode/prompt-file/license metadata when present.
- Approval/apply flow remains unchanged and resolves report-relative candidate paths where possible.

Still intentionally out of scope:

- Automating ChatGPT web UI.
- Adding OpenAI API calls or billing-backed provider execution.
- Renaming the Visual Asset Approval Pipeline.


## Pipeline v2 operating sequence

1. Intake: user provides topic, audience, slide count, tone, output format, and design reference.
2. Source / reference collection: collect content sources and multi-slide design references.
3. Research & content repair: fill content gaps and verify sources.
4. Slide plan: define slide narrative, slide families, and visual roles.
5. Design analysis: extract palette, typography, layout grammar, icon/card/data-display motifs.
6. Asset specs: write asset slots such as cover hero, section object, icon set, chart decoration.
7. OpenAI manual prompt pack: generate ChatGPT Pro / OpenAI Images prompts per asset slot.
8. Manual image generation: user creates images in ChatGPT Pro and downloads them.
9. Manual asset import: SlideForge imports downloaded files as candidate assets.
10. Asset review: build existing review board and record user approval.
11. Deck assembly: insert approved assets into deterministic HTML/PPTX layout.
12. QA: browser capture, console checks, reference-vs-produced board, similarity QA, evidence pack.
13. Revision loop: regenerate/import only weak assets or fix layout tokens.
14. Final delivery: final deck, screenshots, QA report, evidence pack.

---

## Artifact conventions

For a run directory `runs/<run_id>/`:

```text
asset-specs/
  cover-hero.json
  contents-icons-ui.json
  content-illustration.json
  section-divider-object.json
  closing-visual.json

openai-manual-prompts/
  prompt-pack.md
  prompt-pack.json
  cover-hero.md
  contents-icons-ui.md
  content-illustration.md
  section-divider-object.md
  closing-visual.md

manual-generated-assets/
  cover-hero/
    A.png
    B.png
    C.png
  section-divider-object/
    A.png
    B.png

imported-assets/
  cover-hero-A.png
  cover-hero-B.png
  section-divider-object-A.png

asset-generation-report.json
asset-review-board.html
approved-assets.json
deck.html
browser-capture/
design-similarity-qa.json
```

Existing artifact names should be preserved where possible:

```text
asset-generation-report.json
asset-review-board.html
approved-assets.json
```

---

## Candidate source enum

Add or support these source values:

```text
deterministic_svg
comfyui_local
manual_openai_images
manual_upload
future_openai_api
future_recraft_api
```

Pipeline v2 only needs `manual_openai_images` now.

---

## Task 1: Add asset spec and manual prompt artifacts

**Objective:** Represent visual asset slots and create OpenAI Images prompt packs without invoking any external API.

**Files:**
- Create or extend: `src/slideforge/asset_spec.py`
- Create or extend: `src/slideforge/manual_prompts.py`
- Modify: `src/slideforge/cli.py`
- Test: `tests/test_manual_openai_assets.py`

**CLI:**

```bash
PYTHONPATH=src python -m slideforge.cli generate-openai-manual-prompts \
  --asset-spec-dir runs/<run_id>/asset-specs \
  --output-dir runs/<run_id>/openai-manual-prompts
```

**Expected outputs:**

```text
openai-manual-prompts/prompt-pack.md
openai-manual-prompts/prompt-pack.json
openai-manual-prompts/<asset_id>.md
```

**Prompt requirements:**
- State asset role and target slide.
- Include visual style and palette.
- Include hard constraints: no text, letters, numbers, logos, watermarks, people unless requested.
- Include output guidance: high-resolution, clean edges, presentation-ready.
- Include save path instructions for the user.

---

## Task 2: Add manual asset import provider

**Objective:** Import user-downloaded ChatGPT Pro/OpenAI Images files as first-class SlideForge asset candidates.

**Files:**
- Create: `src/slideforge/manual_assets.py`
- Modify: `src/slideforge/asset_approval.py` if needed
- Modify: `src/slideforge/cli.py`
- Test: `tests/test_manual_openai_assets.py`

**CLI:**

```bash
PYTHONPATH=src python -m slideforge.cli import-manual-assets \
  --run-dir runs/<run_id> \
  --asset-spec-dir runs/<run_id>/asset-specs \
  --input-dir runs/<run_id>/manual-generated-assets \
  --output-report runs/<run_id>/asset-generation-report.json
```

**Input naming convention:**

```text
manual-generated-assets/<asset_id>/A.png
manual-generated-assets/<asset_id>/B.png
manual-generated-assets/<asset_id>/C.png
```

**Report fields per candidate:**

```json
{
  "asset_id": "cover-hero",
  "candidate_id": "A",
  "path": "imported-assets/cover-hero-A.png",
  "provider": "openai_images",
  "source": "manual_openai_images",
  "generation_mode": "manual_chatgpt_pro",
  "prompt_file": "openai-manual-prompts/cover-hero.md",
  "license_note": "Generated manually by user in ChatGPT Pro/OpenAI Images; verify plan terms before commercial use."
}
```

**Verification:**
- Missing asset directory should produce a warning, not crash.
- Unsupported file extensions should be ignored with warning.
- Imported filenames should be deterministic.
- Relative paths in report should resolve from run dir.

---

## Task 3: Extend review board metadata

**Objective:** Existing review board should display manually generated OpenAI Images candidates without special casing in approval flow.

**Files:**
- Modify: `src/slideforge/asset_approval.py`
- Test: existing asset approval tests plus `tests/test_manual_openai_assets.py`

**Review board additions:**
- provider
- source
- generation mode
- prompt file link/path
- license note
- user save instructions if no candidates found

**Verification:**

```bash
PYTHONPATH=src python -m slideforge.cli build-asset-review-board \
  --candidate-report runs/<run_id>/asset-generation-report.json \
  --output-html runs/<run_id>/asset-review-board.html \
  --output-md runs/<run_id>/asset-review-board.md
```

Expected: HTML/Markdown board renders images and metadata.

---

## Task 4: Keep approval/apply flow unchanged

**Objective:** Approved manual OpenAI assets should use the same `approved-assets.json` and apply path as existing sources.

**Files:**
- Modify only if necessary: `src/slideforge/asset_approval.py`, `src/slideforge/cli.py`
- Test: `tests/test_manual_openai_assets.py`

**Acceptance:**
- `approve-assets` accepts candidates from `manual_openai_images`.
- `apply-approved-assets` writes the same deck asset fields used by current HTML composer.
- No ComfyUI-specific assumptions leak into approval/apply code.

---

## Task 5: Document Pipeline v2

**Objective:** Document user workflow for manual ChatGPT Pro/OpenAI Images generation.

**Files:**
- Modify: `README.md`
- Optionally create: `docs/visual-asset-approval-pipeline-v2.md`

**Docs should include:**
- Pipeline v2 sequence.
- Folder naming convention.
- How to generate prompt pack.
- How user saves images from ChatGPT Pro.
- How to import assets.
- How to build review board.
- How approval/deck QA remains unchanged.

---

## Task 6: Apply to current PC-VR STT deck as a smoke run

**Objective:** Use the new v2 workflow on the existing high-similarity layout skeleton.

**Run id:**

```text
pc-vr-stt-model-selection-007-openai-manual
```

**Base:**

```text
runs/pc-vr-stt-model-selection-003-high-similarity/deck.html
```

**Asset slots:**
- cover-hero
- contents-icons-ui
- content-illustration
- section-divider-object
- closing-visual

**Smoke acceptance:**
- prompt pack generated.
- user can manually place at least one asset under `manual-generated-assets/<asset_id>/A.png`.
- import creates `asset-generation-report.json`.
- review board renders imported asset.
- approval/apply works.
- deck capture still reports slide_count 10 and console_errors 0.

---

## Safety / non-goals

- Do not automate ChatGPT web UI as an API replacement.
- Do not store ChatGPT credentials, cookies, or session tokens.
- Do not require OpenAI API billing for v2.
- Do not bake Korean body text, chart values, or source labels into images.
- Do not rename the overall pipeline; version it to v2.
- Do not remove ComfyUI support; keep it as optional/local fallback.

---

## Verification commands

```bash
cd /home/hskim/projects/SlideForge
PYTHONPATH=src python -m pytest -q
PYTHONPATH=src python -m slideforge.cli --help
```

After smoke run:

```bash
PYTHONPATH=src python -m slideforge.cli capture-screenshots \
  --deck-html runs/pc-vr-stt-model-selection-007-openai-manual/deck.html \
  --output-dir runs/pc-vr-stt-model-selection-007-openai-manual/browser-capture
```

Expected:

```text
slide_count: 10
console_errors: 0
```
