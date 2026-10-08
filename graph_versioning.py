"""Scoped, integrity-checked snapshots of data graphs (schema is excluded)."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from rdflib import Graph
from rdflib.compare import graph_diff, to_isomorphic

from graph_io import graph_file_lock, write_bytes_atomic, write_graph_atomic

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SNAPSHOT_DIR = os.path.join(BASE_DIR, ".snapshots")
_ALL_PROJECTS = object()
_COMPONENT = re.compile(r"[A-Za-z0-9_-]{1,100}\Z")
_SNAPSHOT_ID = re.compile(r"snap_[A-Za-z0-9_-]{1,240}\Z")


def ensure_snapshot_dir():
    Path(SNAPSHOT_DIR).mkdir(parents=True, exist_ok=True)


def _scope(domain, project_id):
    if not isinstance(domain, str) or not _COMPONENT.fullmatch(domain):
        raise ValueError("Invalid snapshot domain")
    if project_id is not None and (
        not isinstance(project_id, str) or not _COMPONENT.fullmatch(project_id)
    ):
        raise ValueError("Invalid snapshot project_id")
    return {"domain": domain, "project_id": project_id}


def _paths(snapshot_id):
    if not isinstance(snapshot_id, str) or not _SNAPSHOT_ID.fullmatch(snapshot_id):
        raise ValueError("Invalid snapshot_id")
    ensure_snapshot_dir()
    root = Path(SNAPSHOT_DIR).resolve()
    paths = tuple(root / f"{snapshot_id}.{extension}" for extension in ("ttl", "json"))
    for path in paths:
        if path.is_symlink() or path.resolve().parent != root:
            raise ValueError("Snapshot path must stay inside the snapshot directory")
    return paths


def create_snapshot(domain, graph, description="Manual snapshot", author="system", project_id=None):
    """Persist a data-only graph. Callers must pass the selected data graph.

    Scope and source kind are recorded explicitly; merged schema/data snapshots
    produced by older versions remain readable, but cannot be restored.
    """
    scope = _scope(domain, project_id)
    now = datetime.now(timezone.utc)
    snapshot_id = f"snap_{domain}_{now.strftime('%Y%m%d_%H%M%S_%f')}_{uuid4().hex}"
    ttl_path, meta_path = _paths(snapshot_id)
    metadata = {
        "format_version": 2,
        "snapshot_id": snapshot_id,
        "domain": domain,
        "project_id": project_id,
        "scope": scope,
        "source_kind": "data_only",
        "created_at": now.isoformat(),
        "author": str(author),
        "description": str(description),
        "triples_count": len(graph),
        "file_path": str(ttl_path),
    }
    with graph_file_lock(ttl_path):
        write_graph_atomic(graph, ttl_path)
        try:
            metadata["sha256"] = hashlib.sha256(ttl_path.read_bytes()).hexdigest()
            write_bytes_atomic(
                json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8"), meta_path
            )
        except BaseException:
            ttl_path.unlink(missing_ok=True)
            raise
    return metadata


def load_snapshot_metadata(snapshot_id):
    """Read metadata using the validated ID; ignore any metadata-supplied path."""
    _, meta_path = _paths(snapshot_id)
    try:
        metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError) as exc:
        raise ValueError("Snapshot metadata is invalid") from exc
    if not isinstance(metadata, dict) or metadata.get("snapshot_id") != snapshot_id:
        raise ValueError("Snapshot metadata ID does not match its filename")
    return metadata


def _verify_content(metadata, payload):
    if metadata.get("format_version") == 2:
        digest = metadata.get("sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError("Snapshot integrity hash is missing or invalid")
        if not hmac.compare_digest(hashlib.sha256(payload).hexdigest(), digest):
            raise ValueError("Snapshot integrity check failed")


def validate_metadata_scope(snapshot_id, domain, project_id=None):
    """Reject legacy/unscoped snapshots and snapshots from another data source."""
    expected = _scope(domain, project_id)
    ttl_path, _ = _paths(snapshot_id)
    with graph_file_lock(ttl_path):
        metadata = load_snapshot_metadata(snapshot_id)
        if metadata.get("format_version") != 2 or metadata.get("source_kind") != "data_only":
            raise ValueError("Legacy or merged-schema snapshots cannot be restored; create a data-only snapshot")
        if metadata.get("scope") != expected or (
            metadata.get("domain") != domain or metadata.get("project_id") != project_id
        ):
            raise ValueError("Snapshot domain/project scope does not match the selected data source")
        _verify_content(metadata, ttl_path.read_bytes())
    return metadata


def list_snapshots(domain=None, project_id=_ALL_PROJECTS):
    """List newest first. Explicit project_id=None selects only global snapshots."""
    ensure_snapshot_dir()
    snapshots = []
    for meta_path in Path(SNAPSHOT_DIR).glob("snap_*.json"):
        try:
            metadata = load_snapshot_metadata(meta_path.stem)
            if domain is not None and metadata.get("domain") != domain:
                continue
            if project_id is not _ALL_PROJECTS and metadata.get("project_id") != project_id:
                continue
            metadata["restorable"] = (
                metadata.get("format_version") == 2
                and metadata.get("source_kind") == "data_only"
                and isinstance(metadata.get("sha256"), str)
                and re.fullmatch(r"[0-9a-f]{64}", metadata["sha256"]) is not None
                and metadata.get("scope") == {
                    "domain": metadata.get("domain"), "project_id": metadata.get("project_id")
                }
            )
            snapshots.append(metadata)
        except (OSError, ValueError):
            continue
    snapshots.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return snapshots


def load_snapshot_graph(snapshot_id):
    """Read a fresh graph; new snapshots must pass their content hash check."""
    ttl_path, _ = _paths(snapshot_id)
    with graph_file_lock(ttl_path):
        metadata = load_snapshot_metadata(snapshot_id)
        payload = ttl_path.read_bytes()
        _verify_content(metadata, payload)
        graph = Graph().parse(data=payload, format="turtle")
        if metadata.get("format_version") == 2 and metadata.get("triples_count") != len(graph):
            raise ValueError("Snapshot triple count does not match metadata")
        return graph


def compute_graph_diff(graph_a, graph_b):
    """Compute semantic counts, including stable blank-node comparison.

    Lists contain up to 50 examples using full URIs; counts cover all triples.
    Old aliases are retained for existing API consumers.
    """
    common, removed, added = graph_diff(to_isomorphic(graph_a), to_isomorphic(graph_b))

    def examples(graph):
        triples = sorted(graph, key=lambda triple: tuple(term.n3() for term in triple))
        return [
            {"subject": str(s), "predicate": str(p), "object": str(o),
             "object_n3": o.n3()}
            for s, p, o in triples[:50]
        ]

    added_samples, removed_samples = examples(added), examples(removed)
    return {
        "unchanged_count": len(common), "common_count": len(common),
        "added_count": len(added), "removed_count": len(removed),
        "added": added_samples, "removed": removed_samples,
        "added_samples": added_samples, "removed_samples": removed_samples,
        "sample_limit": 50,
    }


def rollback_to_snapshot(domain, snapshot_id, target_graph, destination_path=None, project_id=None):
    """Restore the selected data file first, then update the in-memory graph.

    The caller validates SHACL/media before calling. A write failure leaves
    both the old disk file and target_graph intact. A destination is mandatory
    to avoid reporting a transient in-memory replacement as a persisted restore.
    """
    if destination_path is None:
        raise ValueError("A persistent data destination_path is required for rollback")
    ttl_path, _ = _paths(snapshot_id)
    with graph_file_lock(ttl_path):
        validate_metadata_scope(snapshot_id, domain, project_id)
        restored = load_snapshot_graph(snapshot_id)
        with graph_file_lock(destination_path):
            write_graph_atomic(restored, destination_path)
            target_graph.remove((None, None, None))
            for prefix, namespace in restored.namespaces():
                target_graph.bind(prefix, namespace)
            for triple in restored:
                target_graph.add(triple)
    return {
        "success": True, "domain": domain, "project_id": project_id,
        "snapshot_id": snapshot_id, "triples_restored": len(restored),
        "destination_path": str(Path(destination_path).resolve()), "persisted": True,
    }
