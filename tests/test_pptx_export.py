import base64
import json
import tomllib
import zipfile

from slideforge.guizang_html_composer import HtmlDeck, HtmlSlide, VisualChip
from slideforge.pptx_export import PptxRendererEvidence, export_pptx_report
from slideforge.pptx_delivery_gate import ToolAvailability


def _deck() -> HtmlDeck:
    return HtmlDeck(
        title="폐쇄망 LLM 전략",
        slides=[
            HtmlSlide(
                slide_id="s1",
                title="폐쇄망 LLM 전략",
                subtitle="의사결정용",
                bullets=["GPU", "RAG"],
                archetype="cover",
            )
        ],
    )


def test_pyproject_declares_pptx_optional_dependency():
    data = tomllib.loads(open("pyproject.toml", "rb").read().decode("utf-8"))

    pptx_extra = data["project"]["optional-dependencies"]["pptx"]

    assert any(item.startswith("python-pptx>=") for item in pptx_extra)


def test_export_pptx_missing_dependency_writes_report_without_fake_output(tmp_path, monkeypatch):
    monkeypatch.setattr("slideforge.pptx_export.python_pptx_available", lambda: False)
    monkeypatch.setattr(
        "slideforge.pptx_export.PptxRendererEvidence.detect",
        lambda: PptxRendererEvidence(
            strategy="pptx_glimpse_required_for_renderer_evidence",
            status="unavailable",
            tool={"name": "pptx_glimpse", "executable": "pptx-glimpse", "available": False, "path": ""},
            blockers=["Renderer evidence requires approved pptx-glimpse installation; no install was performed."],
        ),
    )
    output = tmp_path / "deck.pptx"
    report_output = tmp_path / "pptx-export-report.json"

    report = export_pptx_report(_deck(), output, report_output, run_id="missing-smoke")
    persisted = json.loads(report_output.read_text(encoding="utf-8"))

    assert report["status"] == "unavailable"
    assert persisted["run_id"] == "missing-smoke"
    assert persisted["dependency"]["available"] is False
    assert persisted["generation_claim"] == "no_pptx_output_created_python_pptx_missing"
    assert persisted["output_exists"] is False
    assert persisted["slide_count_expected"] == 1
    assert persisted["slide_count_generated"] == 0
    assert persisted["generated_this_run"] is False
    assert "dependency_missing" in persisted["blockers"][0]
    assert "pptx-glimpse" in persisted["blockers"][1]
    assert not output.exists()


def test_export_pptx_missing_dependency_reports_stale_existing_output(tmp_path, monkeypatch):
    monkeypatch.setattr("slideforge.pptx_export.python_pptx_available", lambda: False)
    monkeypatch.setattr(
        "slideforge.pptx_export.PptxRendererEvidence.detect",
        lambda: PptxRendererEvidence(
            strategy="pptx_glimpse_required_for_renderer_evidence",
            status="unavailable",
            tool={"name": "pptx_glimpse", "executable": "pptx-glimpse", "available": False, "path": ""},
            blockers=[],
        ),
    )
    output = tmp_path / "deck.pptx"
    output.write_bytes(b"stale-pptx")
    report_output = tmp_path / "pptx-export-report.json"

    report = export_pptx_report(_deck(), output, report_output, run_id="stale-smoke")

    assert report["status"] == "unavailable"
    assert report["generation_claim"] == "no_pptx_output_created_python_pptx_missing"
    assert report["output_exists"] is True
    assert report["output_file_size_bytes"] == len(b"stale-pptx")
    assert report["generated_this_run"] is False
    assert "stale_output_path_exists" in "\n".join(report["blockers"])


def test_export_pptx_generation_exception_writes_report(tmp_path, monkeypatch):
    monkeypatch.setattr("slideforge.pptx_export.python_pptx_available", lambda: True)
    monkeypatch.setattr(
        "slideforge.pptx_export.PptxRendererEvidence.detect",
        lambda: PptxRendererEvidence(
            strategy="pptx_glimpse_required_for_renderer_evidence",
            status="unavailable",
            tool={"name": "pptx_glimpse", "executable": "pptx-glimpse", "available": False, "path": ""},
            blockers=[],
        ),
    )

    def boom(deck, output):
        raise RuntimeError("rendering failed")

    monkeypatch.setattr("slideforge.pptx_export._export_with_python_pptx", boom)
    output = tmp_path / "deck.pptx"
    report_output = tmp_path / "pptx-export-report.json"

    report = export_pptx_report(_deck(), output, report_output, run_id="error-smoke")
    persisted = json.loads(report_output.read_text(encoding="utf-8"))

    assert report["status"] == "unavailable"
    assert persisted["generation_claim"] == "no_pptx_output_created_generation_failed"
    assert persisted["generated_this_run"] is False
    assert persisted["output_exists"] is False
    assert "pptx_generation_failed: RuntimeError: rendering failed" in persisted["blockers"]


def test_pptx_glimpse_unavailable_renderer_semantics(monkeypatch):
    monkeypatch.setattr(
        "slideforge.pptx_export.ToolAvailability.detect",
        lambda name, executable: ToolAvailability(name=name, executable=executable, available=False),
    )

    evidence = PptxRendererEvidence.detect().to_dict()

    assert evidence["status"] == "unavailable"
    assert evidence["strategy"] == "pptx_glimpse_required_for_renderer_evidence"
    assert evidence["tool"]["executable"] == "pptx-glimpse"
    assert evidence["blockers"] == [
        "Renderer evidence requires approved pptx-glimpse installation; no install was performed."
    ]
    assert evidence["evidence_claim"] == "availability_only_no_visual_render_performed"


def test_export_pptx_embeds_generated_asset_images(tmp_path, monkeypatch):
    monkeypatch.setattr("slideforge.pptx_export.PptxRendererEvidence.detect", lambda: PptxRendererEvidence(
        strategy="pptx_glimpse_available_for_renderer_evidence",
        status="available",
        tool={"name": "pptx_glimpse", "executable": "pptx-glimpse", "available": True, "path": "pptx-glimpse"},
        blockers=[],
    ))
    asset_dir = tmp_path / "generated-assets"
    asset_dir.mkdir()
    asset = asset_dir / "visual.png"
    asset.write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    ))
    deck = HtmlDeck(
        title="asset deck",
        slides=[
            HtmlSlide(
                slide_id="s1",
                title="생성 이미지",
                archetype="visual_band",
                asset_path="generated-assets/visual.png",
                visual_chips=[],
            )
        ],
    )
    output = tmp_path / "deck.pptx"

    report = export_pptx_report(deck, output, tmp_path / "report.json", run_id="asset-smoke")

    assert report["status"] == "available"
    assert report["embedded_asset_count"] == 1
    assert report["missing_asset_paths"] == []
    with zipfile.ZipFile(output) as pptx:
        media_files = [name for name in pptx.namelist() if name.startswith("ppt/media/")]
        slide_rels = pptx.read("ppt/slides/_rels/slide1.xml.rels").decode("utf-8")
    assert media_files
    assert "../media/" in slide_rels


def test_export_pptx_omits_visual_placeholder_label_when_asset_is_embedded(tmp_path, monkeypatch):
    monkeypatch.setattr("slideforge.pptx_export.PptxRendererEvidence.detect", lambda: PptxRendererEvidence(
        strategy="pptx_glimpse_available_for_renderer_evidence",
        status="available",
        tool={"name": "pptx_glimpse", "executable": "pptx-glimpse", "available": True, "path": "pptx-glimpse"},
        blockers=[],
    ))
    (tmp_path / "generated-assets").mkdir()
    (tmp_path / "generated-assets" / "visual.png").write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    ))
    deck = HtmlDeck(
        title="asset deck",
        slides=[
            HtmlSlide(
                slide_id="s1",
                title="생성 이미지",
                archetype="visual_band",
                asset_path="generated-assets/visual.png",
                visual_chips=[],
            )
        ],
    )
    output = tmp_path / "deck.pptx"

    export_pptx_report(deck, output, tmp_path / "report.json", run_id="asset-smoke")

    with zipfile.ZipFile(output) as pptx:
        slide_xml = pptx.read("ppt/slides/slide1.xml").decode("utf-8")
    assert "Visual asset placeholder" not in slide_xml
    assert "deterministic text overlay" not in slide_xml


def test_export_pptx_architecture_asset_omits_overlay_title_and_chips(tmp_path, monkeypatch):
    monkeypatch.setattr("slideforge.pptx_export.PptxRendererEvidence.detect", lambda: PptxRendererEvidence(
        strategy="pptx_glimpse_available_for_renderer_evidence",
        status="available",
        tool={"name": "pptx_glimpse", "executable": "pptx-glimpse", "available": True, "path": "pptx-glimpse"},
        blockers=[],
    ))
    (tmp_path / "generated-assets").mkdir()
    (tmp_path / "generated-assets" / "diagram.png").write_bytes(base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
    ))
    deck = HtmlDeck(
        title="asset deck",
        slides=[
            HtmlSlide(
                slide_id="s1",
                title="Architecture Flow",
                subtitle="Intent: architecture",
                archetype="architecture_visual",
                asset_path="generated-assets/diagram.png",
                visual_chips=[VisualChip(label="폐쇄망 RAG")],
            )
        ],
    )
    output = tmp_path / "deck.pptx"

    report = export_pptx_report(deck, output, tmp_path / "report.json", run_id="diagram-smoke")

    assert report["embedded_asset_count"] == 1
    with zipfile.ZipFile(output) as pptx:
        slide_xml = pptx.read("ppt/slides/slide1.xml").decode("utf-8")
    assert "Architecture Flow" not in slide_xml
    assert "Intent: architecture" not in slide_xml
    assert "폐쇄망 RAG" not in slide_xml
