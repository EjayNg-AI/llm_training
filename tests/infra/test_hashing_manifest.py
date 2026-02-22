from __future__ import annotations

import json
from pathlib import Path

from llm_training.infra.hashing import stable_hash_object
from llm_training.infra.manifest import (
    build_artifact_manifest,
    collect_checksums,
    publish_artifact,
    resolve_artifact_dir,
)


def test_stable_hash_object_is_order_independent_for_dict_keys() -> None:
    left = {"b": 2, "a": 1, "nested": {"y": 2, "x": 1}}
    right = {"a": 1, "b": 2, "nested": {"x": 1, "y": 2}}
    assert stable_hash_object(left) == stable_hash_object(right)


def test_publish_artifact_writes_manifest_and_registry(tmp_path: Path) -> None:
    artifacts_root = tmp_path / "artifacts"
    artifact_dir = resolve_artifact_dir(artifacts_root, "corpus", "corpus_test")
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "docs.jsonl.gz").write_bytes(b"test")

    checksums = collect_checksums(artifact_dir)
    manifest = build_artifact_manifest(
        artifact_type="corpus",
        artifact_id="corpus_test",
        source_run_id="run_001",
        config_hash="cfg_hash",
        git_commit="deadbeef",
        inputs=[],
        stats={"doc_count": 1, "docs_file": "docs.jsonl.gz"},
        checksums=checksums,
    )
    manifest_path = publish_artifact(artifacts_root=artifacts_root, artifact_dir=artifact_dir, manifest=manifest)

    assert manifest_path.exists()
    saved_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert saved_manifest["artifact_id"] == "corpus_test"

    registry_path = artifacts_root / "registry.jsonl"
    lines = registry_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["artifact_id"] == "corpus_test"
    assert Path(entry["manifest_path"]) == manifest_path
