from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any
from urllib import error, request
import uuid

from slideforge.asset_brief import AssetBrief, AssetBriefSet


DEFAULT_COMFYUI_ENDPOINT = "http://127.0.0.1:8188"
DEFAULT_REPORT_NAME = "comfyui-handoff-report.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_asset_brief_set(path: Path) -> AssetBriefSet:
    """Load the generated asset-brief payload written by generate-asset-briefs."""
    raw = _read_json(path)
    if not isinstance(raw, dict):
        raise ValueError("asset briefs JSON must be an object")
    briefs_raw = raw.get("briefs")
    if not isinstance(briefs_raw, list):
        raise ValueError("asset briefs JSON must include a briefs list")
    return AssetBriefSet(briefs=[AssetBrief(**item) for item in briefs_raw])


def _brief_record(brief: AssetBrief) -> dict[str, Any]:
    return {
        "slide_id": brief.slide_id,
        "asset_type": brief.asset_type,
        "prompt": brief.prompt,
        "negative_prompt": brief.negative_prompt,
        "aspect_ratio": brief.aspect_ratio,
        "output_hint": brief.output_hint,
        "text_policy": brief.text_policy,
    }


def _hint_candidates(output_dir: Path, output_hint: str | None) -> list[Path]:
    if not output_hint:
        return []
    hint = Path(output_hint)
    if hint.is_absolute():
        return [hint]
    return [output_dir / hint]


def _existing_output_path(output_dir: Path, output_hint: str | None) -> str | None:
    for candidate in _hint_candidates(output_dir, output_hint):
        if candidate.is_file():
            return str(candidate)
    return None


def check_comfyui_server(endpoint: str, timeout_seconds: float = 1.0) -> tuple[bool, str | None]:
    """Return honest availability for an already-running ComfyUI-compatible server."""
    url = endpoint.rstrip("/") + "/system_stats"
    try:
        with request.urlopen(url, timeout=timeout_seconds) as response:  # nosec B310 - user-provided local/service endpoint health check only
            if 200 <= response.status < 300:
                return True, None
            return False, f"ComfyUI health check returned HTTP {response.status} from {url}"
    except (error.URLError, TimeoutError, OSError) as exc:
        return False, f"ComfyUI health check failed for {url}: {exc}"


def _post_prompt(endpoint: str, workflow: dict[str, Any], brief: AssetBrief, timeout_seconds: float) -> dict[str, Any]:
    payload = {
        "prompt": workflow,
        "client_id": f"slideforge-{uuid.uuid4()}",
        "extra_data": {"slideforge_asset_brief": _brief_record(brief)},
    }
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        endpoint.rstrip("/") + "/prompt",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout_seconds) as response:  # nosec B310 - optional user-directed local REST handoff
        body = response.read().decode("utf-8")
        parsed = json.loads(body) if body else {}
        if not 200 <= response.status < 300:
            raise RuntimeError(f"ComfyUI prompt returned HTTP {response.status}: {body[:200]}")
        if isinstance(parsed, dict):
            return parsed
        return {"response": parsed}


def build_comfyui_handoff_report(
    brief_set: AssetBriefSet,
    *,
    output_dir: Path,
    endpoint: str = DEFAULT_COMFYUI_ENDPOINT,
    workflow_path: Path | None = None,
    execute: bool = False,
    timeout_seconds: float = 1.0,
    checked_at: str | None = None,
) -> dict[str, Any]:
    """Build an evidence-first handoff report and optionally submit workflow prompts.

    The report never treats queued/submitted work as generated imagery. An asset is
    listed under generated_assets only when its output_hint already resolves to an
    existing file in or below output_dir (or to an absolute existing path).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    workflow: dict[str, Any] | None = None
    blockers: list[str] = []
    failed_assets: list[dict[str, Any]] = []
    generated_assets: list[dict[str, Any]] = []
    pending_assets: list[dict[str, Any]] = []

    server_available, health_blocker = check_comfyui_server(endpoint, timeout_seconds=timeout_seconds)
    if health_blocker:
        blockers.append(health_blocker)

    if workflow_path is not None:
        workflow_raw = _read_json(workflow_path)
        if not isinstance(workflow_raw, dict):
            raise ValueError("ComfyUI workflow JSON must be an object")
        workflow = workflow_raw
    elif execute:
        blockers.append("workflow_path not provided; no ComfyUI prompts submitted")

    if execute and not server_available:
        blockers.append("ComfyUI execution skipped because the endpoint is unavailable")
    if not execute:
        blockers.append("execution disabled; report records handoff contract only")

    for brief in brief_set.briefs:
        record = _brief_record(brief)
        existing = _existing_output_path(output_dir, brief.output_hint)
        if existing:
            generated_assets.append({**record, "status": "generated", "path": existing})
            continue

        if brief.text_policy != "text-free":
            failed_assets.append({**record, "status": "failed", "blocker": "asset brief is not text-free"})
            continue

        if execute and server_available and workflow is not None:
            try:
                provider_response = _post_prompt(endpoint, workflow, brief, timeout_seconds)
            except Exception as exc:  # noqa: BLE001 - report handoff failure honestly per asset
                failed_assets.append({**record, "status": "failed", "blocker": f"ComfyUI prompt submit failed: {exc}"})
            else:
                pending_assets.append(
                    {
                        **record,
                        "status": "submitted",
                        "prompt_id": provider_response.get("prompt_id"),
                        "provider_response": provider_response,
                        "generation_claim": "not_generated_until_output_file_exists",
                    }
                )
        else:
            pending_assets.append({**record, "status": "pending", "generation_claim": "not_generated"})

    if failed_assets and (pending_assets or generated_assets):
        status = "partial_failure"
    elif failed_assets:
        status = "failed"
    elif not server_available:
        status = "unavailable"
    elif pending_assets and execute and workflow is not None:
        status = "submitted"
    elif pending_assets:
        status = "pending"
    else:
        status = "complete"

    return {
        "provider": "comfyui",
        "endpoint": endpoint,
        "status": status,
        "server_available": server_available,
        "checked_at": checked_at or _utc_now(),
        "workflow_path": str(workflow_path) if workflow_path is not None else None,
        "execution_requested": execute,
        "text_policy": "text-free",
        "brief_count": len(brief_set.briefs),
        "generated_assets": generated_assets,
        "pending_assets": pending_assets,
        "failed_assets": failed_assets,
        "blockers": blockers,
    }


def write_comfyui_handoff_report(
    *,
    asset_briefs_path: Path,
    output_dir: Path,
    endpoint: str = DEFAULT_COMFYUI_ENDPOINT,
    workflow_path: Path | None = None,
    report_name: str = DEFAULT_REPORT_NAME,
    execute: bool = False,
    timeout_seconds: float = 1.0,
) -> Path:
    brief_set = load_asset_brief_set(asset_briefs_path)
    report = build_comfyui_handoff_report(
        brief_set,
        output_dir=output_dir,
        endpoint=endpoint,
        workflow_path=workflow_path,
        execute=execute,
        timeout_seconds=timeout_seconds,
    )
    report_path = Path(output_dir) / report_name
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report_path
