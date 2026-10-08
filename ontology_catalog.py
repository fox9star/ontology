"""Create and discover isolated, local draft ontology profiles without AI APIs."""

from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import re
import tempfile

from rdflib import BNode, Dataset, Graph, Literal, Namespace, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SH, XSD

from graph_io import graph_file_lock

ROOT = Path(__file__).resolve().parent
_ID = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*\Z")
_RESERVED = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(10)), *(f"lpt{i}" for i in range(10))}
_FILES = {"schema": "schema.ttl", "owl": "schema.owl", "shapes": "shapes.ttl", "example": "example.ttl", "questions": "questions.md",
          "questions_fixture": "question-fixture.ttl", "question_answers": "question-answers.json", "compatibility_cases": "consumer-cases.trig"}


def _identifier(value):
    if not isinstance(value, str) or not 2 <= len(value) <= 48 or not _ID.fullmatch(value) or value in _RESERVED:
        raise ValueError("ID는 영문 소문자로 시작하는 2~48자의 영문 소문자·숫자·하이픈이어야 합니다.")
    return value


def _text(payload, field, maximum, required=True):
    value = payload.get(field, "")
    if not isinstance(value, str):
        raise ValueError(f"{field}: 문자열을 입력해 주세요.")
    value = value.strip()
    if required and not value:
        raise ValueError(f"{field}: 필수 항목입니다.")
    if len(value) > maximum or any(ord(char) < 32 and char not in "\n\t" for char in value):
        raise ValueError(f"{field}: 최대 {maximum}자의 일반 텍스트를 입력해 주세요.")
    return value


def _plain_path(path, root):
    """Reject links/junctions even when they resolve back inside the workspace."""
    path, root = Path(path), Path(root).resolve()
    if not path.is_relative_to(root):
        raise ValueError("사용자 온톨로지 경로가 작업 폴더를 벗어났습니다.")
    for item in (path, *path.parents):
        if item == root:
            break
        if item.is_symlink() or getattr(item, "is_junction", lambda: False)():
            raise ValueError("사용자 온톨로지 경로에는 링크 또는 정션을 사용할 수 없습니다.")
    if not path.resolve().is_relative_to(root):
        raise ValueError("사용자 온톨로지 경로가 작업 폴더를 벗어났습니다.")
    return path


def _catalog_root(root):
    root = Path(root).resolve()
    return root, _plain_path(root / "custom-ontologies", root)


def _read_profile(directory, root):
    identifier = _identifier(directory.name)
    metadata = _plain_path(directory / "profile.json", root)
    if not metadata.is_file() or metadata.stat().st_size > 32_768:
        raise ValueError(f"{identifier}: profile.json 파일이 없거나 너무 큽니다.")
    try:
        profile = json.loads(metadata.read_text(encoding="utf-8"))
    except (ValueError, UnicodeError) as error:
        raise ValueError(f"{identifier}: profile.json 형식이 올바르지 않습니다.") from error
    if not isinstance(profile, dict) or profile.get("format_version") != 1 or profile.get("id") != identifier:
        raise ValueError(f"{identifier}: 사용자 온톨로지 메타데이터가 올바르지 않습니다.")
    for field, maximum in (("name", 160), ("description", 2000), ("name_en", 160), ("description_en", 2000)):
        profile[field] = _text(profile, field, maximum, required=field in {"name", "description"})
    expected_prefix = f"https://example.org/ontology/custom/{identifier}#"
    if profile.get("prefix") != expected_prefix or profile.get("custom") is not True or not isinstance(profile.get("draft"), bool):
        raise ValueError(f"{identifier}: 사용자 온톨로지 선언이 올바르지 않습니다.")
    if not isinstance(profile.get("version"), str) or not re.fullmatch(r"\d+\.\d+\.\d+(?:-[a-zA-Z0-9.-]+)?", profile["version"]):
        raise ValueError(f"{identifier}: 버전 형식이 올바르지 않습니다.")
    for key, filename in _FILES.items():
        expected = f"custom-ontologies/{identifier}/{filename}"
        if profile.get(key) != expected:
            raise ValueError(f"{identifier}: {key} 경로가 소유 디렉터리와 일치하지 않습니다.")
        file = _plain_path(root / expected, root)
        if not file.is_file():
            raise ValueError(f"{identifier}: {filename} 파일이 없습니다.")
    return profile


def _profiles(root=ROOT):
    root, directory = _catalog_root(root)
    if not directory.exists():
        return {}
    if not directory.is_dir():
        raise ValueError("custom-ontologies가 디렉터리가 아닙니다.")
    profiles = {}
    for child in sorted(directory.iterdir(), key=lambda path: path.name):
        if child.name.startswith("."):
            continue  # In-progress private staging directories are never profiles.
        child = _plain_path(child, root)
        if not child.is_dir():
            continue
        profiles[child.name] = _read_profile(child, root)
    return profiles


def load_custom_profiles(root=ROOT):
    """Read validated paths for app.ONTOLOGIES; no RDF or network evaluation."""
    return {key: {name: value for name, value in profile.items() if name not in {"format_version", "id"}}
            for key, profile in _profiles(root).items()}


def _module(profile):
    return {"id": profile['id'], "schema": profile["schema"], "shapes": [profile["shapes"]],
            "example": profile["example"], "questions": profile["questions"],
            **{key: profile[key] for key in ('questions_fixture', 'question_answers', 'compatibility_cases')},
            "documentation": True, "custom": True, "draft": profile["draft"]}


def custom_modules(root=ROOT):
    """Registry entries for validated custom profiles, discovered after restart."""
    return [_module(profile) for profile in _profiles(root).values()]


def public_catalog(builtin_configs, root=ROOT):
    """Searchable metadata, keeping builtin profiles ahead of custom drafts."""
    profiles = {key: dict(value) for key, value in builtin_configs.items()}
    for key, profile in load_custom_profiles(root).items():
        if key in profiles and not profiles[key].get("custom"):
            raise ValueError(f"{key}: 기본 온톨로지 ID와 충돌합니다.")
        profiles[key] = profile
    return [{"id": key, "name": profile["name"], "description": profile.get("description", ""),
             "name_en": profile.get("name_en", ""), "description_en": profile.get("description_en", ""),
             "version": profile.get("version", ""), "custom": bool(profile.get("custom")),
             "draft": bool(profile.get("draft")), "prefix": profile.get("prefix", "")}
            for key, profile in profiles.items()]


def _write(path, text):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())


def _scaffold(profile, directory):
    ns = Namespace(profile["prefix"])
    ontology = URIRef(profile["prefix"].removesuffix("#"))
    schema, shapes, example = Graph(), Graph(), Graph()
    for graph in (schema, shapes, example):
        graph.bind("custom", ns)
    schema.bind("owl", OWL)
    schema.bind("rdfs", RDFS)
    shapes.bind("sh", SH)
    schema.add((ontology, RDF.type, OWL.Ontology))
    schema.add((ontology, OWL.versionInfo, Literal(profile["version"])))
    schema.add((ontology, OWL.versionIRI, URIRef(str(ontology) + "/0.1.0")))
    for language, label, definition in (
        ("ko", profile["name"], profile["description"]),
        ("en", profile["name_en"] or f"Custom ontology {profile['id']}",
         profile["description_en"] or "A local draft ontology scaffold whose domain model requires further definition."),
    ):
        schema.add((ontology, RDFS.label, Literal(label, lang=language)))
        schema.add((ontology, RDFS.comment, Literal(definition, lang=language)))
    for term, kind, ko_label, en_label, ko_comment, en_comment in (
        (ns.Record, OWL.Class, "기록", "Record", "새 도메인 모델을 정의하기 전에 이름을 기록하는 초안의 기본 개체입니다.",
         "A named draft record used while the domain-specific entity model is being defined."),
        (ns.displayName, OWL.DatatypeProperty, "표시 이름", "Display name", "사용자가 초안 기록을 구별하기 위해 입력하는 표시용 이름입니다.",
         "The display name supplied by the user to distinguish a draft record."),
    ):
        schema.add((term, RDF.type, kind))
        for predicate, ko, en in ((RDFS.label, ko_label, en_label), (RDFS.comment, ko_comment, en_comment)):
            schema.add((term, predicate, Literal(ko, lang="ko")))
            schema.add((term, predicate, Literal(en, lang="en")))
    schema.add((ns.displayName, RDFS.domain, ns.Record))
    schema.add((ns.displayName, RDFS.range, XSD.string))
    node, prop = ns.RecordShape, BNode()
    shapes.add((node, RDF.type, SH.NodeShape))
    shapes.add((node, SH.targetClass, ns.Record))
    shapes.add((node, SH.targetSubjectsOf, ns.displayName))
    shapes.add((node, SH["class"], ns.Record))
    shapes.add((node, SH.property, prop))
    shapes.add((prop, SH.path, ns.displayName))
    shapes.add((prop, SH.minCount, Literal(1)))
    shapes.add((prop, SH.maxCount, Literal(1)))
    shapes.add((prop, SH.datatype, XSD.string))
    shapes.add((prop, SH.minLength, Literal(1)))
    shapes.add((prop, SH.message, Literal("기록에는 비어 있지 않은 표시 이름이 하나 필요합니다.", lang="ko")))
    example.add((ns.sampleRecord, RDF.type, ns.Record))
    example.add((ns.sampleRecord, ns.displayName, Literal(profile["name"] + " 예시 기록", datatype=XSD.string)))
    for filename, graph, fmt in (("schema.ttl", schema, "turtle"), ("schema.owl", schema, "xml"),
                                 ("shapes.ttl", shapes, "turtle"), ("example.ttl", example, "turtle")):
        _write(directory / filename, graph.serialize(format=fmt))
    questions = f"""# 사용자 온톨로지 초안 질문

이 초안의 Record와 displayName은 도메인 모델을 작성하기 위한 시작점입니다.
도메인 개념, 관계, 규칙과 실제 업무 질문을 정의한 뒤 초안 상태를 검토합니다.
아래 예시 기록은 합성 데이터입니다.

### CUSTOM-{profile['id'].upper()}-01. 어떤 기록이 어떤 표시 이름으로 등록되어 있는가?

~~~sparql
PREFIX custom: <{ns}>
SELECT ?record ?name WHERE {{
  ?record a custom:Record ; custom:displayName ?name .
}}
ORDER BY ?record
~~~

기대 결과: sampleRecord 한 건. 표시 이름이 없거나 Record 유형이 빠지면 결과에서 제외됩니다.
"""
    _write(directory / "questions.md", questions)
    _write(directory / 'question-fixture.ttl', example.serialize(format='turtle'))
    answers = {f"CUSTOM-{profile['id'].upper()}-01": {
        'variables': ['record', 'name'], 'rows': [[str(ns.sampleRecord), profile['name'] + ' 예시 기록']]}}
    _write(directory / 'question-answers.json', json.dumps(answers, ensure_ascii=False, indent=2) + '\n')
    cases = Dataset()
    accept = cases.graph(URIRef('https://example.test/consumer/' + profile['id'] + '-accept'))
    for triple in example:
        accept.add(triple)
    reject = cases.graph(URIRef('https://example.test/consumer/' + profile['id'] + '-reject'))
    reject.add((ns.sampleRecord, RDF.type, ns.Record))
    _write(directory / 'consumer-cases.trig', cases.serialize(format='trig'))
    _write(directory / "profile.json", json.dumps(profile, ensure_ascii=False, indent=2) + "\n")


def create_ontology(payload, builtin_configs, root=ROOT):
    """Publish a fully written draft directory once; never replace existing data."""
    if not isinstance(payload, dict):
        raise ValueError("온톨로지 정보는 JSON 객체여야 합니다.")
    identifier = _identifier(payload.get("id"))
    if identifier in builtin_configs:
        raise FileExistsError("이미 사용 중인 온톨로지 ID입니다.")
    profile = {"format_version": 1, "id": identifier,
               "name": _text(payload, "name", 160), "description": _text(payload, "description", 2000),
               "name_en": _text(payload, "name_en", 160, False),
               "description_en": _text(payload, "description_en", 2000, False),
               "version": "0.1.0", "prefix": f"https://example.org/ontology/custom/{identifier}#",
               "custom": True, "draft": True, "created_at": dt.datetime.now(dt.timezone.utc).isoformat()}
    profile.update({key: f"custom-ontologies/{identifier}/{filename}" for key, filename in _FILES.items()})
    root, catalog = _catalog_root(root)
    catalog.mkdir(mode=0o700, parents=True, exist_ok=True)
    destination = _plain_path(catalog / identifier, root)
    _plain_path(catalog / ".catalog.lock", root)
    with graph_file_lock(catalog / "catalog", timeout=10):
        if destination.exists():
            raise FileExistsError("이미 사용 중인 온톨로지 ID입니다.")
        stage = Path(tempfile.mkdtemp(prefix=".creating-", dir=catalog))
        try:
            _scaffold(profile, stage)
            # A directory rename exposes the metadata and all graph files together.
            os.rename(stage, destination)
        finally:
            if stage.exists():
                _plain_path(stage, root)
                for child in stage.iterdir():
                    if child.is_file() and not child.is_symlink():
                        child.unlink()
                stage.rmdir()
    return {"id": identifier, "config": {key: value for key, value in profile.items() if key not in {"id", "format_version"}},
            "module": _module(profile), "draft": True,
            "message": "기본 기록 모델을 가진 초안을 만들었습니다. 도메인 개념과 관계를 추가해 주세요."}
