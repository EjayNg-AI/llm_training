"""Shared infrastructure utilities for stage scripts."""

from .hashing import canonical_json, sha256_bytes, sha256_file, sha256_text, stable_hash_object
from .io_atomic import (
    atomic_append_jsonl,
    atomic_dump_json,
    atomic_dump_pickle,
    atomic_dump_pickle_with_checksum,
    atomic_dump_text,
    atomic_write_bytes,
    load_pickle_with_checksum,
)
from .manifest import (
    build_artifact_manifest,
    load_manifest,
    publish_artifact,
    resolve_artifact_dir,
)
from .run_dir import (
    begin_run,
    end_run,
    make_run_context,
    resolve_run_id,
    write_state,
    write_stage_metric,
)

__all__ = [
    "atomic_append_jsonl",
    "atomic_dump_json",
    "atomic_dump_pickle",
    "atomic_dump_pickle_with_checksum",
    "atomic_dump_text",
    "atomic_write_bytes",
    "begin_run",
    "build_artifact_manifest",
    "canonical_json",
    "end_run",
    "load_manifest",
    "load_pickle_with_checksum",
    "make_run_context",
    "publish_artifact",
    "resolve_artifact_dir",
    "resolve_run_id",
    "sha256_bytes",
    "sha256_file",
    "sha256_text",
    "stable_hash_object",
    "write_stage_metric",
    "write_state",
]
