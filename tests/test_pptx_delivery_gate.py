import json

from slideforge.pptx_delivery_gate import (
    PptxDeliveryGate,
    ToolAvailability,
    write_pptx_delivery_gate,
)


def test_pptx_delivery_gate_records_unavailable_strategy_honestly(tmp_path):
    source = tmp_path / "deck.html"
    source.write_text("<!doctype html><title>deck</title>", encoding="utf-8")
    desired = tmp_path / "deck.pptx"

    gate = PptxDeliveryGate.from_paths(
        source_path=source,
        desired_pptx_path=desired,
        run_id="smoke-001",
        tool_availability={
            "libreoffice": ToolAvailability(name="libreoffice", executable="soffice", available=False),
            "pptx_glimpse": ToolAvailability(name="pptx_glimpse", executable="pptx-glimpse", available=False),
        },
    )

    payload = gate.to_dict()

    assert payload["report_kind"] == "pptx_delivery_gate"
    assert payload["run_id"] == "smoke-001"
    assert payload["source_path"] == str(source)
    assert payload["desired_pptx_path"] == str(desired)
    assert payload["current_status"] == "unavailable"
    assert payload["renderer_strategy"]["selected"] == "manual_or_external_pptx_renderer"
    assert payload["static_checks_planned"]
    assert payload["visual_checks_planned"]
    assert payload["blockers"] == [
        "No local PPTX export/render validation tool is available: libreoffice, pptx_glimpse.",
        "Renderer evidence requires approved pptx-glimpse installation; no install was performed.",
    ]
    assert payload["validation_claim"] == "strategy_contract_only_no_pptx_export_or_visual_render_performed"


def test_write_pptx_delivery_gate_uses_relative_paths_and_status_available_when_tools_exist(tmp_path):
    source = tmp_path / "run" / "deck.html"
    source.parent.mkdir()
    source.write_text("<!doctype html><title>deck</title>", encoding="utf-8")

    report_path = write_pptx_delivery_gate(
        source_path=source,
        desired_pptx_path=tmp_path / "run" / "deck.pptx",
        output_dir=source.parent,
        run_id="smoke-002",
        tool_availability={
            "libreoffice": ToolAvailability(name="libreoffice", executable="soffice", available=True, path="/usr/bin/soffice"),
            "pptx_glimpse": ToolAvailability(name="pptx_glimpse", executable="pptx-glimpse", available=False),
        },
    )

    data = json.loads(report_path.read_text(encoding="utf-8"))

    assert report_path == source.parent / "pptx-delivery-gate.json"
    assert data["source_path"] == "deck.html"
    assert data["desired_pptx_path"] == "deck.pptx"
    assert data["current_status"] == "available"
    assert data["renderer_strategy"]["selected"] == "libreoffice_headless_export_then_render_check"
    assert data["blockers"] == []
