"""Inspect immutable registered media and maintain scoped provenance sidecars.

This tool reads local files only. It verifies registered-copy integrity, never
the original model, prompt, or origin. Independent historical review is a
separate activity and is not simulated by a checksum comparison.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

import pyshacl
from rdflib import Graph, Literal, Namespace, RDF, URIRef, XSD


ROOT = Path(__file__).resolve().parent
EV = Namespace("https://example.org/ontology/evidence#")
MV = Namespace("https://example.org/mv#")
PROV = Namespace("http://www.w3.org/ns/prov#")
SCOPES = (EV.LocalFileIntegrity, EV.OriginalGeneration, EV.OriginalOrigin)
IDENTIFIER = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,79}\Z")
DIGEST = re.compile(r"[0-9a-f]{64}\Z")
VERSION = "local-evidence-checker-1.0.0"
GENERATION_UNKNOWN = ("No independently reviewed evidence identifies the original generation model and prompt. "
                      "Local importer metadata documents registration only.")
ORIGIN_UNKNOWN = ("Only a local source-copy location is recorded; no independently reviewed evidence establishes "
                  "the asset's original origin.")


def file_sha256(path):
    """Hash read-only bytes, rejecting a file changed while it was being read."""
    path = Path(path)
    before = path.stat()
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    after = path.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError("File changed during its integrity check")
    return digest.hexdigest()


def _read_inputs(project_dir):
    project_dir = Path(project_dir).resolve(strict=True)
    documents = {}
    for filename in ("project.json", "manifest.json", "data.ttl"):
        path = project_dir / filename
        if path.is_symlink() or not path.resolve().is_relative_to(project_dir):
            raise ValueError("Project registration inputs must be regular files inside the project")
        documents[filename] = path.read_bytes()
    project = json.loads(documents["project.json"].decode("utf-8-sig"))
    manifest = json.loads(documents["manifest.json"].decode("utf-8-sig"))
    if not isinstance(project, dict) or not isinstance(manifest, dict):
        raise ValueError("Project registration documents must be JSON objects")
    project_id = project.get("id")
    if not isinstance(project_id, str) or not IDENTIFIER.fullmatch(project_id):
        raise ValueError("Project identifier is invalid")
    if manifest.get("project_id") != project_id or project.get("ontology") != "mv":
        raise ValueError("Evidence refresh requires a matching registered MV project")
    assets = manifest.get("assets")
    if not isinstance(assets, list) or not assets:
        raise ValueError("Registration manifest has no asset list")
    seen = set()
    for asset in assets:
        if not isinstance(asset, dict):
            raise ValueError("Manifest assets must be objects")
        asset_id, filename, expected = (asset.get(key) for key in ("id", "file_name", "sha256"))
        if not isinstance(asset_id, str) or not IDENTIFIER.fullmatch(asset_id) or asset_id in seen:
            raise ValueError("Asset identifiers must be valid and unique")
        if not isinstance(filename, str) or not filename or Path(filename).name != filename or "\\" in filename or "/" in filename:
            raise ValueError("Asset filename must be a single local filename")
        if not isinstance(expected, str) or not DIGEST.fullmatch(expected):
            raise ValueError("Registered assets require a lowercase SHA-256 digest")
        if asset.get("kind") not in ("audio", "image", "video"):
            raise ValueError("Unsupported registered media kind")
        seen.add(asset_id)
    data = Graph().parse(data=documents["data.ttl"].decode("utf-8-sig"), format="turtle",
                         publicID=(project_dir / "data.ttl").as_uri())
    hashes = {filename: hashlib.sha256(content).hexdigest() for filename, content in documents.items()}
    return project_dir, project, manifest, data, hashes


def inspect_project(project_dir):
    """Measure registration and files without changing source or project inputs."""
    project_dir, project, manifest, data, hashes = _read_inputs(project_dir)
    rows = []
    asset_types = {"audio": MV.AudioAsset, "image": MV.ImageAsset, "video": MV.MusicVideo}
    manifest_nodes = {MV[asset["id"]] for asset in manifest["assets"]}
    graph_nodes = {node for term in asset_types.values() for node in data.subjects(RDF.type, term)}
    omitted_assets = len(graph_nodes - manifest_nodes)
    for asset in manifest["assets"]:
        node = MV[asset["id"]]
        copy = project_dir / "assets" / asset["file_name"]
        row = {"id": asset["id"], "kind": asset["kind"], "expected_sha256": asset["sha256"],
               "copy_uri": copy.as_uri(), "copy_sha256": None, "source_uri": None, "source_sha256": None,
               "source_copy_state": "not-recorded", "failures": []}
        if not copy.resolve().is_relative_to(project_dir / "assets") or copy.is_symlink():
            row["failures"].append("Registered-copy path escapes the project asset directory")
        elif not copy.is_file():
            row["failures"].append("Registered copy is missing")
        else:
            try:
                row["copy_sha256"] = file_sha256(copy)
                if row["copy_sha256"] != asset["sha256"]:
                    row["failures"].append("Registered-copy SHA-256 does not match the registration")
                if "size_bytes" in asset and copy.stat().st_size != asset["size_bytes"]:
                    row["failures"].append("Registered-copy size does not match the registration")
            except (OSError, ValueError):
                row["failures"].append("Registered copy cannot be read consistently")
        if str(asset.get("file_uri")) != copy.as_uri():
            row["failures"].append("Manifest file URI does not identify the registered copy")
        if (node, RDF.type, asset_types[asset["kind"]]) not in data:
            row["failures"].append("Asset type is missing or inconsistent in the registration graph")
        graph_hashes = list(data.objects(node, MV.checksum))
        if len(graph_hashes) != 1 or str(graph_hashes[0]) != asset["sha256"]:
            row["failures"].append("Graph checksum does not match the manifest checksum")
        graph_uris = list(data.objects(node, MV.fileUri))
        if len(graph_uris) != 1 or str(graph_uris[0]) != copy.as_uri():
            row["failures"].append("Graph file URI does not identify the registered copy")
        source_path = asset.get("source_file")
        if source_path:
            if not isinstance(source_path, str):
                raise ValueError("Recorded source_file must be a local path string")
            source = Path(source_path)
            if not source.is_absolute():
                raise ValueError("Recorded source_file must be an absolute local path")
            row["source_uri"] = source.as_uri()
            if not source.is_file():
                row["source_copy_state"] = "missing"
            else:
                try:
                    row["source_sha256"] = file_sha256(source)
                    row["source_copy_state"] = "matches" if row["source_sha256"] == asset["sha256"] else "mismatch"
                    if row["source_copy_state"] == "mismatch":
                        row["failures"].append("Local source-copy SHA-256 no longer matches the registered bytes")
                except (OSError, ValueError):
                    row["source_copy_state"] = "unreadable"
                    row["failures"].append("Recorded local source copy cannot be read consistently")
        if omitted_assets:
            row["failures"].append("Registration graph contains assets omitted by the manifest")
        row["status"] = "Failed" if row["failures"] else "Observed"
        rows.append(row)
    return {"project_id": project["id"], "checked_at": datetime.now(timezone.utc).isoformat(),
            "checker": VERSION, "registration_hashes": hashes, "assets": rows,
            "omitted_graph_assets": omitted_assets, "files_conform": all(not row["failures"] for row in rows)}


def build_evidence_graph(inspection, project_dir):
    """Create scoped claims; original history remains unknown after local checks."""
    graph = Graph()
    graph.bind("ev", EV)
    graph.bind("prov", PROV)
    project_dir = Path(project_dir).resolve()
    project_id = inspection["project_id"]
    claim_base = Namespace(f"https://example.org/ontology/evidence/claim/{project_id}/")
    checker = EV.LocalEvidenceChecker
    graph.add((checker, RDF.type, PROV.Agent))
    for scope in SCOPES:
        graph.add((scope, RDF.type, EV.ClaimScope))
    for status in (EV.Observed, EV.Verified, EV.Unverified, EV.Failed):
        graph.add((status, RDF.type, EV.VerificationStatus))

    def add_record(claim, token, uri, digest, role):
        record = URIRef(str(claim) + "/evidence/" + token)
        graph.add((record, RDF.type, EV.EvidenceRecord))
        graph.add((record, EV.evidenceURI, URIRef(uri)))
        graph.add((record, EV.sha256, Literal(digest)))
        graph.add((record, EV.evidenceRole, Literal(role)))
        graph.add((claim, EV.hasEvidence, record))

    for asset in inspection["assets"]:
        for scope in SCOPES:
            claim = claim_base[asset["id"] + "/" + str(scope).split("#")[-1]]
            graph.add((claim, RDF.type, EV.VerificationClaim))
            graph.add((claim, EV.aboutAsset, MV[asset["id"]]))
            graph.add((claim, EV.scope, scope))
            graph.add((claim, EV.projectIdentifier, Literal(project_id)))
            graph.add((claim, EV.assetIdentifier, Literal(asset["id"])))
            graph.add((claim, EV.checkedAt, Literal(inspection["checked_at"], datatype=XSD.dateTime)))
            graph.add((claim, EV.checkedBy, checker))
            if scope != EV.LocalFileIntegrity:
                graph.add((claim, EV.status, EV.Unverified))
                graph.add((claim, EV.unknownReason, Literal(GENERATION_UNKNOWN if scope == EV.OriginalGeneration else ORIGIN_UNKNOWN)))
                continue
            graph.add((claim, EV.status, EV[asset["status"]]))
            graph.add((claim, EV.expectedSHA256, Literal(asset["expected_sha256"])))
            graph.add((claim, EV.sourceCopyState, Literal(asset["source_copy_state"])))
            if asset["failures"]:
                graph.add((claim, EV.unknownReason, Literal("; ".join(asset["failures"]))))
            for filename, role in (("manifest.json", "registration-manifest"), ("data.ttl", "registration-graph")):
                add_record(claim, role, (project_dir / filename).as_uri(), inspection["registration_hashes"][filename], role)
            for prefix, role in (("copy", "registered-copy"), ("source", "local-source-copy")):
                if asset[prefix + "_sha256"] is not None:
                    add_record(claim, role, asset[prefix + "_uri"], asset[prefix + "_sha256"], role)
    return graph


def validate_evidence_graph(graph):
    """Validate explicitly recorded facts without filling missing facts by inference."""
    conforms, _, report = pyshacl.validate(
        graph, shacl_graph=Graph().parse(ROOT / "evidence-shapes.ttl", format="turtle"), inference="none")
    return bool(conforms), str(report)


def aggregate_report(inspection, *, graph_conforms, snapshot_conforms=True, claims_conform=True):
    """Export counts and boundaries only: no asset IRIs, source paths, or hashes."""
    counts = Counter(row["status"] for row in inspection["assets"])
    source_counts = Counter(row["source_copy_state"] for row in inspection["assets"])
    total = len(inspection["assets"])
    return {"format_version": 1, "checker": VERSION, "checked_at": inspection["checked_at"], "asset_count": total,
            "claim_count": total * 3, "scope_status_counts": {
                "LocalFileIntegrity": {"Observed": counts["Observed"], "Failed": counts["Failed"]},
                "OriginalGeneration": {"Unverified": total}, "OriginalOrigin": {"Unverified": total}},
            "source_copy_state_counts": dict(sorted(source_counts.items())),
            "checks": {"files_conform": inspection["files_conform"], "evidence_graph_conforms": graph_conforms,
                       "registration_snapshot_conforms": snapshot_conforms, "saved_claims_conform": claims_conform},
            "conforms": bool(inspection["files_conform"] and graph_conforms and snapshot_conforms and claims_conform),
            "limitations": ["A matching local source/copy checksum establishes byte identity only.",
                            "No independently reviewed original generation or origin evidence was supplied.",
                            "Missing source copies do not invalidate an intact registered copy; their current availability is reported separately.",
                            "Checks are observations at the recorded time, not continuous monitoring or independent notarization."]}


def _saved_claims_match(saved, inspection):
    # Compare semantic assertions only; checkedAt and evidence snapshot hashes
    # are checked separately. Refuse missing/extra scope claims or promotions.
    claims = list(saved.subjects(RDF.type, EV.VerificationClaim))
    if len(claims) != len(inspection["assets"]) * 3:
        return False
    assets = {asset["id"]: asset for asset in inspection["assets"]}
    pairs = set()
    for claim in claims:
        asset_id = str(saved.value(claim, EV.assetIdentifier))
        scope = saved.value(claim, EV.scope)
        project_id = str(saved.value(claim, EV.projectIdentifier))
        if asset_id not in assets or scope not in SCOPES or project_id != inspection["project_id"]:
            return False
        pair = (asset_id, scope)
        if pair in pairs or saved.value(claim, EV.aboutAsset) != MV[asset_id]:
            return False
        pairs.add(pair)
        if scope == EV.LocalFileIntegrity:
            row = assets[asset_id]
            if saved.value(claim, EV.status) != EV[row["status"]] or str(saved.value(claim, EV.expectedSHA256)) != row["expected_sha256"]:
                return False
            if str(saved.value(claim, EV.sourceCopyState)) != row["source_copy_state"]:
                return False
            actual_records = {}
            for record in saved.objects(claim, EV.hasEvidence):
                role = str(saved.value(record, EV.evidenceRole))
                if role in actual_records:
                    return False
                actual_records[role] = (str(saved.value(record, EV.evidenceURI)), str(saved.value(record, EV.sha256)))
            for prefix, role in (("copy", "registered-copy"), ("source", "local-source-copy")):
                digest = row[prefix + "_sha256"]
                if digest is None:
                    if role in actual_records:
                        return False
                elif actual_records.get(role) != (row[prefix + "_uri"], digest):
                    return False
        elif saved.value(claim, EV.status) != EV.Unverified:
            # This automated checker has no independent-review inputs and
            # cannot accept an original claim merely because a sidecar says so.
            return False
    return len(pairs) == len(inspection["assets"]) * 3


def check_project(project_dir):
    """Read saved evidence and independently recheck files and input snapshots."""
    project_dir = Path(project_dir).resolve(strict=True)
    inspection = inspect_project(project_dir)
    saved = Graph().parse(project_dir / "evidence.ttl", format="turtle")
    saved_json = json.loads((project_dir / "evidence.json").read_text(encoding="utf-8"))
    if not isinstance(saved_json, dict):
        raise ValueError("Saved evidence snapshot must be a JSON object")
    graph_conforms, _ = validate_evidence_graph(saved)
    snapshot_conforms = saved_json.get("registration_hashes") == inspection["registration_hashes"]
    # Also anchor registration hashes in the RDF records rather than relying
    # solely on the JSON sidecar.
    for role, filename in (("registration-manifest", "manifest.json"), ("registration-graph", "data.ttl")):
        records = list(saved.subjects(EV.evidenceRole, Literal(role)))
        if not records or any(str(saved.value(record, EV.sha256)) != inspection["registration_hashes"][filename]
                              or str(saved.value(record, EV.evidenceURI)) != (project_dir / filename).as_uri() for record in records):
            snapshot_conforms = False
    claims_conform = (_saved_claims_match(saved, inspection)
                      and saved_json.get("evidence_graph_sha256") == file_sha256(project_dir / "evidence.ttl"))
    return aggregate_report(inspection, graph_conforms=graph_conforms, snapshot_conforms=snapshot_conforms,
                            claims_conform=claims_conform)


def refresh_project(project_dir):
    """Refresh evidence outputs only, retaining an established input baseline."""
    project_dir = Path(project_dir).resolve(strict=True)
    inspection = inspect_project(project_dir)
    for filename in ("evidence.json", "evidence.ttl", "evidence-validation.txt", "evidence-summary.md"):
        target = project_dir / filename
        if target.is_symlink() or not target.resolve().is_relative_to(project_dir):
            raise ValueError("Evidence output paths must stay inside the project")
    sidecar_path = project_dir / "evidence.json"
    if sidecar_path.exists():
        previous = json.loads(sidecar_path.read_text(encoding="utf-8"))
        if not isinstance(previous, dict):
            raise ValueError("Saved evidence snapshot must be a JSON object")
        if previous.get("registration_hashes") != inspection["registration_hashes"]:
            raise ValueError("Registration inputs changed since the evidence baseline; review the project change before creating a new baseline")
    graph = build_evidence_graph(inspection, project_dir)
    conforms, validation = validate_evidence_graph(graph)
    if not conforms:
        raise ValueError("Generated evidence failed graph validation:\n" + validation)
    # Fixed sidecar filenames avoid touching manifest, registration graph,
    # imported copies, source media, or caller-selected source paths.
    graph.serialize(project_dir / "evidence.ttl", format="turtle", encoding="utf-8")
    inspection["evidence_graph_sha256"] = file_sha256(project_dir / "evidence.ttl")
    (project_dir / "evidence.json").write_text(json.dumps(inspection, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (project_dir / "evidence-validation.txt").write_text(validation, encoding="utf-8")
    lines = ["# 프로젝트 출처 확인 범위", "", f"검사 시점: {inspection['checked_at']}", "",
             "| 등록 자산 | 유형 | 등록 복사본 무결성 | 로컬 원본 대조 | 원본 생성 이력 | 원본 최초 출처 |",
             "|---|---|---|---|---|---|"]
    for asset in inspection["assets"]:
        lines.append(f"| {asset['id']} | {asset['kind']} | {asset['status']} | {asset['source_copy_state']} | Unverified | Unverified |")
    lines.extend(["", "등록 복사본과 현재 로컬 원본의 지문 대조는 파일 바이트의 일치만 확인합니다.",
                  "등록 시 기록한 도구와 버전은 가져오기 작업의 정보이며 원본 생성 모델과 프롬프트를 증명하지 않습니다.",
                  "세 범위의 주장은 자산별로 분리되어 있으며 원본 생성·최초 출처의 독립 근거가 없어 미확인 사유를 기록했습니다.",
                  "원본·등록 미디어·manifest.json·data.ttl·project.json은 이 도구가 수정하지 않습니다.",
                  "", "evidence.ttl에는 주장과 관찰 근거가, evidence.json에는 현재 검사 결과와 등록 기준선이 들어 있습니다.",
                  "공유할 때는 로컬 경로와 지문이 포함된 프로젝트 자료 대신 reports/provenance-evidence.json의 집계본을 사용합니다."])
    (project_dir / "evidence-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return aggregate_report(inspection, graph_conforms=True)


def write_shared_report(path, report, protected_paths=()):
    path = Path(path)
    resolved = path.resolve()
    if path.suffix.lower() != ".json" or path.is_symlink():
        raise ValueError("Shared report must be a regular JSON output")
    for protected in protected_paths:
        protected = Path(protected).resolve()
        if resolved == protected or (protected.is_dir() and resolved.is_relative_to(protected)):
            raise ValueError("Shared report cannot overwrite project inputs or source media")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("refresh", "check"))
    parser.add_argument("--project", required=True, type=Path, help="Registered MV project directory")
    parser.add_argument("--report", type=Path, help="Optional sanitized aggregate JSON output")
    options = parser.parse_args(argv)
    try:
        report = refresh_project(options.project) if options.operation == "refresh" else check_project(options.project)
        if options.report:
            project_dir, _, manifest, _, _ = _read_inputs(options.project)
            protected = [project_dir] + [Path(asset["source_file"]) for asset in manifest["assets"] if asset.get("source_file")]
            write_shared_report(options.report, report, protected)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        # Avoid echoing paths, URI values, or project data to a shared terminal.
        print(json.dumps({"conforms": False, "error": "Evidence operation failed", "error_type": type(exc).__name__}))
        return 2
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["conforms"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
