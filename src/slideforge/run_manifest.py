from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EvidenceArtifact:
    name: str
    path: str
    kind: str
    description: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("artifact name is required")
        if not self.path.strip():
            raise ValueError("artifact path is required")
        if not self.kind.strip():
            raise ValueError("artifact kind is required")


@dataclass(frozen=True)
class RunManifest:
    run_id: str
    project: str
    pipeline: str
    inputs: dict[str, Any] = field(default_factory=dict)
    artifacts: list[EvidenceArtifact] = field(default_factory=list)
    checks: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ValueError("run_id is required")
        if not self.project.strip():
            raise ValueError("project is required")
        if not self.pipeline.strip():
            raise ValueError("pipeline is required")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RunManifestWriter:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def write(self, manifest: RunManifest) -> Path:
        run_dir = self.root / manifest.run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / "manifest.json").write_text(
            json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (run_dir / "evidence-index.md").write_text(self._render_index(manifest), encoding="utf-8")
        return run_dir

    def _render_index(self, manifest: RunManifest) -> str:
        lines = [
            f"# Evidence index: {manifest.run_id}",
            "",
            f"- project: `{manifest.project}`",
            f"- pipeline: `{manifest.pipeline}`",
            "",
            "## Inputs",
            "",
        ]
        if manifest.inputs:
            lines.extend(f"- {key}: `{value}`" for key, value in manifest.inputs.items())
        else:
            lines.append("- none recorded")
        lines.extend(["", "## Artifacts", ""])
        if manifest.artifacts:
            for artifact in manifest.artifacts:
                desc = f" — {artifact.description}" if artifact.description else ""
                lines.append(f"- `{artifact.name}` ({artifact.kind}): `{artifact.path}`{desc}")
        else:
            lines.append("- none recorded")
        lines.extend(["", "## Checks", ""])
        if manifest.checks:
            lines.extend(f"- {key}: `{value}`" for key, value in manifest.checks.items())
        else:
            lines.append("- none recorded")
        return "\n".join(lines) + "\n"
