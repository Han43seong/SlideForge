# SlideForge

디자인 레퍼런스(PPTX 템플릿·스크린샷·이미지·PDF·웹 페이지)에서 고품질 프레젠테이션 덱을 생성하는 Python 파이프라인.

---

## 목적

슬라이드 덱 제작을 단계별로 분리한다: 디자인 분석 → 콘텐츠 매핑 → 비주얼 에셋 생성/승인 → HTML 컴포지션 → PPTX 딜리버리. 각 단계는 독립적으로 실행·검사·반복할 수 있다.

핵심 원칙:
- **텍스트/레이아웃 소유권 분리**: 한국어/영어 텍스트, 표, 차트, 다이어그램은 이미지 모델이 아닌 컴포저 코드가 결정론적으로 처리한다.
- **에셋 승인 우선**: 생성된 이미지 후보는 `asset-review-board`를 통해 검토·선택된 후 덱에 적용된다. 자동 삽입 없음.
- **에비던스 기록**: 모든 run은 manifest·브라우저 캡처·PPTX 게이트·승인 리포트·fidelity 요약 등 기계 가독 아티팩트를 남긴다.

---

## 원리 / 동작 방식

```text
레퍼런스 입력
  ↓
template_analyzer  →  design-spec.json  (색상·타이포그래피·슬라이드 아키타입)
  ↓
section_preparer + deck_preparer  →  sections.json + deck.json
  (archetype_mapper로 콘텐츠 섹션 → 슬라이드 아키타입 매핑)
  ↓
Visual Asset Approval Pipeline v2
  - 기본: OpenAI Images 수동 생성 → import-manual-assets
  - 선택: ComfyUI REST 엔드포인트 → comfyui-handoff
  → asset-generation-report.json → asset-review-board → approved-assets.json
  ↓
guizang_html_composer  →  deck.html
  (Playwright 선택 설치 시 browser_capture로 PNG 증거 캡처)
  ↓
apply-approved-assets  →  deck.approved.json
  ↓
pptx_export  →  deck.pptx  (python-pptx 선택 설치)
  ↓
export-evidence-pack  →  evidence-pack.zip
```

`run-source-local` / `run-design-source-local` 명령으로 전체 파이프라인을 단일 커맨드로 실행할 수 있다.

---

## 주요 기능

| 모듈 | 역할 |
|---|---|
| `template_analyzer`, `design_spec` | 레퍼런스 관찰값 → 색상·아키타입·그래픽 모티프 정의 |
| `section_preparer`, `deck_preparer` | Markdown/텍스트 소스 → 구조화 섹션 → HtmlDeck JSON |
| `archetype_mapper` | 콘텐츠 인텐트 → 슬라이드 아키타입 보수적 매핑 |
| `manual_prompts`, `manual_assets` | ChatGPT Pro/OpenAI Images 수동 워크플로 (API 자동화 없음) |
| `comfyui_handoff` | ComfyUI REST 핸드오프 리포트 (서버 없이도 브리프 생성) |
| `asset_approval` | 에셋 후보 리뷰 보드·승인 기록·덱 적용 |
| `guizang_html_composer` | 아키타입별 HTML 섹션 렌더링, 커스텀 프레젠테이션 모드 |
| `browser_capture` | Playwright Chromium 스크린샷·회귀 플랜 |
| `pptx_export`, `pptx_delivery_gate` | python-pptx 기반 PPTX 생성·게이트 계약 |
| `evidence_summary`, `evidence_pack` | run 요약 JSON/MD + ZIP 에비던스 팩 |
| `fidelity_scorer` | 100점 루브릭 템플릿 유사도 채점 |

---

## 설치 & 사용법

```bash
# 기본 (의존성 없음)
pip install -e '.'

# PPTX 출력 활성화
pip install -e '.[pptx]'

# Playwright 브라우저 캡처 활성화
pip install -e '.[browser]'
python -m playwright install chromium
```

### Quick start — 소스 파일에서 한 번에 실행

```bash
PYTHONPATH=src python -m slideforge.cli run-source-local \
  --source source.md \
  --title "폐쇄망 AI 운영 전략" \
  --runs-dir runs \
  --run-id my-run-001
```

`runs/my-run-001/` 아래에 `deck.html`, `run-summary.json`, 브라우저 회귀 플랜, PPTX 게이트 등이 생성된다.

### 디자인 레퍼런스 포함 실행

```bash
PYTHONPATH=src python -m slideforge.cli run-design-source-local \
  --source source.md \
  --observations observations.json \
  --design-name "Reference design" \
  --title "제목" \
  --runs-dir runs \
  --run-id my-run-001
```

### PPTX 출력

```bash
PYTHONPATH=src python -m slideforge.cli export-pptx \
  --deck runs/my-run-001/deck.json \
  --output runs/my-run-001/deck.pptx \
  --report-output runs/my-run-001/pptx-export-report.json \
  --run-id my-run-001
```

### 에비던스 팩 내보내기

```bash
PYTHONPATH=src python -m slideforge.cli export-evidence-pack \
  --run-dir runs/my-run-001 \
  --output runs/my-run-001-evidence-pack.zip \
  --manifest-output runs/my-run-001-evidence-pack-manifest.json
```

### 테스트

```bash
PYTHONPATH=src python -m pytest -q
```

---

## 요구사항 / 의존성

- **Python ≥ 3.11**
- 코어: 의존성 없음 (순수 Python)
- 선택 — PPTX 출력: `python-pptx >= 1.0.2`
- 선택 — 브라우저 캡처: `playwright >= 1.45` + `playwright install chromium`
- 개발/테스트: `pytest >= 8`

---

## 주요 변경 이력

| 날짜 | 내용 |
|---|---|
| 2026-05-20 | 프로젝트 초기화 (hermes-slide-forge → SlideForge 리네이밍) |
| 2026-05-20 | guizang HTML 컴포저·ComfyUI 핸드오프·슬라이드 스키마·아키타입 매핑 등 핵심 파이프라인 구현 |
| 2026-05-20 | PPTX 딜리버리 게이트·Playwright 스크린샷 캡처·fidelity 리포트 추가 |
| 2026-05-20 | `run-local` 오케스트레이터·에비던스 매니페스트·run 요약 추가 |
| 2026-05-21 | 에셋 승인 게이트·비주얼 리뷰 보드·PPTX 에셋 임베드·`run-source-local` 통합 명령 완성 |
| 2026-05-22 | OpenAI Images 수동 워크플로 추가 및 v2 파이프라인 이력 문서화 |
