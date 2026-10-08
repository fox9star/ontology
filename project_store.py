"""Read registered local projects without granting arbitrary filesystem access."""

import hashlib
import json
import os
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import quote, unquote, urlsplit


PROJECTS_DIR = Path(__file__).resolve().parent / "projects"
PROJECT_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,79}\Z")


class ProjectError(ValueError):
    def __init__(self, message, status_code=400):
        super().__init__(message)
        self.status_code = status_code


def validate_project_id(project_id):
    if not isinstance(project_id, str) or not PROJECT_ID_PATTERN.fullmatch(project_id):
        raise ProjectError("프로젝트 ID 형식이 올바르지 않습니다.")
    return project_id


def _inside(path, directory):
    return path == directory or directory in path.parents


def project_directory(project_id):
    validate_project_id(project_id)
    root = Path(PROJECTS_DIR).resolve()
    directory = (root / project_id).resolve()
    if not _inside(directory, root):
        raise ProjectError("프로젝트 경로가 등록 폴더를 벗어났습니다.")
    if not directory.is_dir():
        raise ProjectError("등록된 프로젝트를 찾을 수 없습니다.", 404)
    return directory


def project_file(project_id, filename):
    directory = project_directory(project_id)
    path = (directory / filename).resolve()
    if not _inside(path, directory):
        raise ProjectError("프로젝트 파일 경로가 등록 폴더를 벗어났습니다.")
    if not path.is_file():
        raise ProjectError(f"프로젝트 파일이 없습니다: {filename}", 404)
    return path


def _read_json(path):
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ProjectError(f"프로젝트 JSON을 읽을 수 없습니다: {path.name}") from exc
    if not isinstance(value, dict):
        raise ProjectError(f"프로젝트 JSON은 객체여야 합니다: {path.name}")
    return value


def load_project(project_id, ontology=None):
    config = _read_json(project_file(project_id, "project.json"))
    if config.get("id") != project_id:
        raise ProjectError("등록 폴더와 project.json의 프로젝트 ID가 다릅니다.")
    if not isinstance(config.get("ontology"), str):
        raise ProjectError("프로젝트의 ontology 정보가 없습니다.")
    if ontology is not None and config["ontology"] != ontology:
        raise ProjectError("선택한 온톨로지와 프로젝트의 온톨로지가 다릅니다.")
    return config


def load_manifest(project_id):
    manifest = _read_json(project_file(project_id, "manifest.json"))
    if manifest.get("project_id") != project_id:
        raise ProjectError("manifest.json의 프로젝트 ID가 다릅니다.")
    for field in ("assets", "timeline"):
        if not isinstance(manifest.get(field), list):
            raise ProjectError(f"manifest.json의 {field}는 목록이어야 합니다.")
    ids = set()
    names = set()
    for asset in manifest["assets"]:
        if not isinstance(asset, dict):
            raise ProjectError("미디어 자산 정보가 올바르지 않습니다.")
        validate_project_id(asset.get("id"))
        filename = asset.get("file_name")
        if not isinstance(filename, str) or not filename:
            raise ProjectError("미디어 자산의 file_name이 없습니다.")
        if asset["id"] in ids or filename in names:
            raise ProjectError("미디어 자산 ID 또는 파일 이름이 중복되었습니다.")
        ids.add(asset["id"])
        names.add(filename)
    return manifest


def list_projects(ontology=None):
    root = Path(PROJECTS_DIR)
    if not root.is_dir():
        return []
    projects = []
    for directory in root.iterdir():
        if not directory.is_dir() or not PROJECT_ID_PATTERN.fullmatch(directory.name):
            continue
        try:
            config = load_project(directory.name)
        except ProjectError:
            continue
        if ontology is None or config["ontology"] == ontology:
            projects.append(config)
    return sorted(projects, key=lambda row: str(row.get("created_at", "")), reverse=True)


def asset_path(project_id, filename):
    """Resolve only an explicitly registered asset inside this project's assets/."""
    if not isinstance(filename, str) or not filename or "\\" in filename:
        raise ProjectError("미디어 파일 이름이 올바르지 않습니다.")
    directory = project_directory(project_id)
    assets_dir = (directory / "assets").resolve()
    if not _inside(assets_dir, directory):
        raise ProjectError("미디어 폴더가 프로젝트 폴더를 벗어났습니다.")
    relative = Path(filename)
    if relative.is_absolute() or ":" in filename or ".." in relative.parts:
        raise ProjectError("미디어 파일 경로가 올바르지 않습니다.")
    path = (assets_dir / relative).resolve()
    if path == assets_dir or not _inside(path, assets_dir):
        raise ProjectError("미디어 파일 경로가 등록 폴더를 벗어났습니다.")
    manifest = load_manifest(project_id)
    if not any(asset["file_name"] == filename for asset in manifest["assets"]):
        raise ProjectError("등록된 미디어 파일을 찾을 수 없습니다.", 404)
    return path


def _positive_number(value, integer=False):
    try:
        numeric = Decimal(str(value))
        return numeric.is_finite() and numeric > 0 and (not integer or numeric == numeric.to_integral_value())
    except (InvalidOperation, ValueError, TypeError):
        return False


def _registered_root_uri():
    """Read an explicit original workspace URI for a relocated local copy."""
    value = os.environ.get("ONTOLOGY_REGISTERED_ROOT_URI", "")
    if not value:
        return None
    message = "ONTOLOGY_REGISTERED_ROOT_URI must be an absolute local file URI ending in /, without traversal."
    if any(character.isspace() or ord(character) < 32 or ord(character) == 127 for character in value):
        raise ProjectError(message)
    if re.search(r"%(?![0-9A-Fa-f]{2})", value):
        raise ProjectError(message)
    try:
        parts = urlsplit(value)
        if parts.scheme != "file" or parts.netloc or parts.query or parts.fragment:
            raise ValueError("Not an absolute local file URI")
        if not value.startswith("file:///") or not parts.path.startswith("/") or not parts.path.endswith("/"):
            raise ValueError("Directory URI required")
        segments = parts.path[1:-1].split("/")
        if not segments or any(not segment for segment in segments):
            raise ValueError("Empty directory component")
        for segment in segments:
            decoded = unquote(segment, encoding="utf-8", errors="strict")
            if decoded in {".", ".."} or "/" in decoded or "\\" in decoded:
                raise ValueError("URI traversal or encoded separator")
            if any(ord(character) < 32 or ord(character) == 127 for character in decoded):
                raise ValueError("URI control character")
    except (ValueError, UnicodeError):
        raise ProjectError(message) from None
    return value


def _expected_asset_uri(path, registered_root):
    if registered_root is None:
        return path.as_uri()
    try:
        relative = path.resolve().relative_to(Path(PROJECTS_DIR).resolve())
    except ValueError:
        raise ProjectError("Asset path is outside the registered projects directory.") from None
    return registered_root + "/".join(quote(component, safe="") for component in ("projects", *relative.parts))


def check_assets(project_id, graph, namespace):
    """Check file integrity and that registered metadata agrees with the RDF data."""
    registered_root = _registered_root_uri()
    manifest = load_manifest(project_id)
    checks = []
    if not manifest["assets"]:
        checks.append({"id": "manifest", "file_name": "manifest.json", "exists": True,
                       "metadata_valid": False, "sha256_matches": None, "valid": False,
                       "errors": ["등록된 미디어 자산이 없습니다."]})
    registered_subjects = {namespace[asset["id"]] for asset in manifest["assets"]}
    # mv:fileUri has mv:MediaAsset as its domain, including inferred media assets.
    for subject in sorted(set(graph.subjects(namespace.fileUri, None)), key=str):
        if subject not in registered_subjects:
            checks.append({"id": str(subject), "file_name": str(graph.value(subject, namespace.fileUri)),
                           "exists": False, "metadata_valid": False, "sha256_matches": None,
                           "valid": False, "errors": ["RDF의 미디어 자산이 manifest에 등록되어 있지 않습니다."]})
    for asset in manifest["assets"]:
        problems = []
        check = {"id": asset["id"], "file_name": asset["file_name"], "exists": False,
                 "metadata_valid": True, "sha256_matches": None}
        try:
            path = asset_path(project_id, asset["file_name"])
            check["exists"] = path.is_file()
            if not check["exists"]:
                problems.append("등록 파일이 없습니다.")
            expected_uri = _expected_asset_uri(path, registered_root)
            if asset.get("file_uri") != expected_uri:
                problems.append("manifest의 파일 URI가 등록 파일 위치와 다릅니다.")
            subject = namespace[asset["id"]]
            rdf_uri = graph.value(subject, namespace.fileUri)
            if str(rdf_uri) != expected_uri:
                problems.append("RDF의 파일 URI가 등록 파일 위치와 다릅니다.")
            kind = asset.get("kind")
            if kind not in ("audio", "image", "video"):
                problems.append("미디어 종류가 올바르지 않습니다.")
            numeric_fields = []
            if kind in ("audio", "video"):
                numeric_fields.append(("duration_seconds", namespace.durationSeconds, False))
            if kind in ("image", "video"):
                numeric_fields.extend((("width", namespace.width, True), ("height", namespace.height, True)))
            for field, predicate, integer in numeric_fields:
                value = asset.get(field)
                check[field] = value
                rdf_value = graph.value(subject, predicate)
                if not _positive_number(value, integer):
                    problems.append(f"{field} 메타데이터는 양수{' 정수' if integer else ''}여야 합니다.")
                else:
                    try:
                        if Decimal(str(rdf_value)) != Decimal(str(value)):
                            problems.append(f"{field} 값이 manifest와 RDF에서 다릅니다.")
                    except InvalidOperation:
                        problems.append(f"RDF에 {field} 메타데이터가 없습니다.")
            expected_hash = asset.get("sha256")
            if not isinstance(expected_hash, str) or not re.fullmatch(r"[a-fA-F0-9]{64}", expected_hash):
                problems.append("파일 SHA256 정보가 올바르지 않습니다.")
            elif check["exists"]:
                digest = hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
                actual_hash = digest.hexdigest()
                check["sha256_matches"] = actual_hash == expected_hash.lower()
                if not check["sha256_matches"]:
                    problems.append("파일 내용이 등록 당시 SHA256과 다릅니다.")
        except (ProjectError, OSError) as exc:
            problems.append(str(exc))
        check["metadata_valid"] = not problems
        check["valid"] = check["exists"] and not problems
        check["errors"] = problems
        checks.append(check)
    return checks
