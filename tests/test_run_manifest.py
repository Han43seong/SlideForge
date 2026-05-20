import json

from slideforge.run_manifest import EvidenceArtifact, RunManifest, RunManifestWriter


def test_run_manifest_writer_creates_manifest_and_evidence_index(tmp_path):
    writer = RunManifestWriter(root=tmp_path)
    manifest = RunManifest(
        run_id="phase1-smoke",
        project="SlideForge",
        pipeline="template-to-asset-briefs",
        inputs={"reference": "slidesgo-blockchain-preview"},
        artifacts=[
            EvidenceArtifact(name="design_spec", path="design-spec.json", kind="json"),
            EvidenceArtifact(name="asset_briefs", path="asset-briefs.json", kind="json"),
        ],
        checks={"tests": "15 passed", "push": "synced"},
    )

    run_dir = writer.write(manifest)

    manifest_path = run_dir / "manifest.json"
    index_path = run_dir / "evidence-index.md"
    assert manifest_path.exists()
    assert index_path.exists()

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert data["run_id"] == "phase1-smoke"
    assert data["artifacts"][0]["name"] == "design_spec"

    index = index_path.read_text(encoding="utf-8")
    assert "# Evidence index: phase1-smoke" in index
    assert "design_spec" in index
    assert "template-to-asset-briefs" in index


def test_run_manifest_rejects_empty_run_id():
    try:
        RunManifest(run_id="", project="SlideForge", pipeline="x")
    except ValueError as exc:
        assert "run_id" in str(exc)
    else:
        raise AssertionError("expected ValueError")
