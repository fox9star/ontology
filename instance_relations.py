"""Scoped instance relations with validation, snapshots and atomic persistence.

This module never edits schema definitions, media files or recorded attribution.
The application is imported only inside the mutation entry point.
"""

from pathlib import Path
from urllib.parse import urlsplit

from rdflib import BNode, Graph, Literal, Namespace, OWL, RDF, RDFS, URIRef

from graph_io import graph_file_lock, write_graph_atomic
from project_store import ProjectError

PROV = Namespace("http://www.w3.org/ns/prov#")
MV = Namespace("https://example.org/mv#")
AG = Namespace("https://example.org/agent#")

SAFE_PROV_RELATIONS = frozenset({PROV.alternateOf, PROV.specializationOf, PROV.hadMember})
PROV_REFERENCE_PREDICATES = SAFE_PROV_RELATIONS | frozenset({
    PROV.wasGeneratedBy, PROV.wasDerivedFrom, PROV.wasAssociatedWith,
    PROV.wasAttributedTo, PROV.used, PROV.generated, PROV.atLocation,
    PROV.wasInfluencedBy, PROV.wasInformedBy, PROV.actedOnBehalfOf,
    PROV.hadPrimarySource, PROV.wasRevisionOf, PROV.wasQuotedFrom,
    PROV.wasStartedBy, PROV.wasEndedBy, PROV.wasInvalidatedBy, PROV.invalidated,
    PROV.qualifiedGeneration, PROV.qualifiedDerivation, PROV.qualifiedAttribution,
    PROV.qualifiedAssociation, PROV.qualifiedUsage, PROV.qualifiedCommunication,
    PROV.qualifiedStart, PROV.qualifiedEnd,
})

PROTECTED_PREDICATES = frozenset({RDF.type, MV.fileUri, AG.artifactUri, PROV.atLocation}) | (
    PROV_REFERENCE_PREDICATES - SAFE_PROV_RELATIONS
)
PROJECT_PROTECTED_PREDICATES = frozenset(MV[name] for name in (
    "hasBrief", "hasAudio", "hasImage", "hasTimeline", "hasFinalVideo",
    "hasShot", "usesImage", "usesAudio", "fileUri", "checksum", "mimeType",
    "targetDurationSeconds", "durationSeconds", "width", "height", "orderIndex",
    "startSecond", "endSecond", "sizeBytes", "sampleRate", "channels", "codec",
))
_TBOX_TYPES = frozenset({
    OWL.Class, RDFS.Class, RDF.Property, OWL.ObjectProperty, OWL.DatatypeProperty,
    OWL.AnnotationProperty, OWL.OntologyProperty, OWL.Ontology, OWL.Restriction,
    RDFS.Datatype, OWL.FunctionalProperty, OWL.InverseFunctionalProperty,
    OWL.TransitiveProperty, OWL.SymmetricProperty, OWL.AsymmetricProperty,
    OWL.ReflexiveProperty, OWL.IrreflexiveProperty,
})
_TBOX_RELATIONS = frozenset({
    RDFS.subClassOf, RDFS.subPropertyOf, RDFS.domain, RDFS.range,
    OWL.equivalentClass, OWL.equivalentProperty, OWL.disjointWith,
    OWL.inverseOf, OWL.onProperty, OWL.unionOf, OWL.intersectionOf,
})
_LOCATION_PREDICATES = frozenset({MV.fileUri, AG.artifactUri, PROV.atLocation})


def _uri(value):
    if isinstance(value, (BNode, Literal)) or not isinstance(value, (str, URIRef)) or not value:
        raise ProjectError("관계의 주체, 속성, 대상은 URI 문자열이어야 합니다.")
    if any(character.isspace() or ord(character) < 32 or ord(character) == 127 or character in '<>"{}|\\^`' for character in str(value)):
        raise ProjectError("관계 URI 형식이 올바르지 않습니다.")
    try:
        parts = urlsplit(str(value))
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
            raise ValueError("Absolute HTTP(S) identifier required")
        parts.port  # Reject malformed port components.
    except ValueError:
        raise ProjectError("관계 URI는 절대 HTTP 또는 HTTPS 식별자여야 합니다.") from None
    return URIRef(value)


def relation_policy(predicate, project_id=None):
    """Explain immutable provenance, vocabulary and project manifest edges."""
    try:
        predicate = _uri(predicate)
    except ProjectError:
        return {"editable": False, "reason": "URI 형식이 올바르지 않습니다."}
    if predicate in PROTECTED_PREDICATES or (
        str(predicate).startswith(str(PROV)) and predicate not in SAFE_PROV_RELATIONS
    ):
        return {"editable": False, "reason": "파일 위치와 기록된 생성·출처 이력은 관계 편집으로 변경할 수 없습니다."}
    if any(str(predicate).startswith(str(namespace)) for namespace in (RDF, RDFS, OWL)):
        return {"editable": False, "reason": "클래스와 스키마 정의는 인스턴스 관계 편집 대상이 아닙니다."}
    if project_id and predicate in PROJECT_PROTECTED_PREDICATES:
        return {"editable": False, "reason": "등록 미디어와 장면·타임라인 관계는 프로젝트 등록 정보에서 관리합니다."}
    return {"editable": True, "reason": ""}


def _property_family(schema_graph, predicate):
    """Include semantic aliases and ancestors for immutable edge protection."""
    seen, pending = set(), [predicate]
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        pending.extend(value for value in schema_graph.objects(current, RDFS.subPropertyOf) if isinstance(value, URIRef))
        for relation in (OWL.equivalentProperty, OWL.inverseOf):
            pending.extend(value for value in schema_graph.objects(current, relation) if isinstance(value, URIRef))
            pending.extend(value for value in schema_graph.subjects(relation, current) if isinstance(value, URIRef))
    return seen


def _effective_policy(schema_graph, predicate, project_id):
    for equivalent in sorted(_property_family(schema_graph, predicate), key=str):
        policy = relation_policy(equivalent, project_id)
        if not policy["editable"]:
            return policy
    return {"editable": True, "reason": ""}


def _known_predicates(schema_graph, data_graph):
    predicates = {value for value in schema_graph.subjects(RDF.type, OWL.ObjectProperty) if isinstance(value, URIRef)}
    for predicate in PROV_REFERENCE_PREDICATES:
        declared = (predicate, RDF.type, OWL.ObjectProperty) in schema_graph or (predicate, RDF.type, OWL.ObjectProperty) in data_graph
        recorded = any(isinstance(value, URIRef) for value in data_graph.objects(None, predicate))
        if declared or recorded:
            predicates.add(predicate)
    return predicates


def _definition_nodes(data_graph, schema_graph):
    definitions = set()
    for graph in (schema_graph, data_graph):
        definitions.update(predicate for predicate in graph.predicates() if isinstance(predicate, URIRef))
        for node, kind in graph.subject_objects(RDF.type):
            if kind in _TBOX_TYPES:
                definitions.add(node)
            if isinstance(kind, URIRef) and kind != OWL.NamedIndividual:
                definitions.add(kind)
        for predicate in _TBOX_RELATIONS:
            definitions.update(graph.subjects(predicate, None))
        for predicate in (RDFS.subClassOf, RDFS.subPropertyOf, OWL.equivalentClass, OWL.equivalentProperty, OWL.inverseOf):
            definitions.update(graph.objects(None, predicate))
    return definitions


def _instance_endpoint(data_graph, schema_graph, namespace, endpoint, definitions=None):
    prefix = str(namespace)
    if not isinstance(endpoint, URIRef) or not str(endpoint).startswith(prefix) or str(endpoint) in {prefix, prefix.rstrip("#/")}:
        return False
    if str(endpoint).lower().startswith("file:"):
        return False
    if not any(data_graph.triples((endpoint, None, None))):
        return False
    if endpoint in (definitions if definitions is not None else _definition_nodes(data_graph, schema_graph)):
        return False
    for predicate in _LOCATION_PREDICATES:
        if any(data_graph.triples((None, predicate, endpoint))):
            return False
    return True


def relation_is_editable(data_graph, schema_graph, namespace, subject, predicate, object_uri, project_id=None,
                         *, definitions=None, known_predicates=None):
    """Shared UI/backend eligibility; malformed or out-of-scope edges are false.

    Class compatibility is checked when adding an edge. Removing an existing
    incompatible edge can repair a graph, provided the candidate then validates.
    """
    try:
        subject, predicate, target = _uri(subject), _uri(predicate), _uri(object_uri)
        if predicate not in (known_predicates if known_predicates is not None
                             else _known_predicates(schema_graph, data_graph)):
            return False
        if not _effective_policy(schema_graph, predicate, project_id)["editable"]:
            return False
        if definitions is None:
            definitions = _definition_nodes(data_graph, schema_graph)
        return _instance_endpoint(data_graph, schema_graph, namespace, subject, definitions) and _instance_endpoint(
            data_graph, schema_graph, namespace, target, definitions
        )
    except (ProjectError, TypeError, ValueError):
        return False


def build_relation_catalog(schema_graph, data_graph, project_id=None):
    """List selected-schema properties and observed/imported PROV references."""
    records = []
    for predicate in sorted(_known_predicates(schema_graph, data_graph), key=str):
        labels = list(schema_graph.objects(predicate, RDFS.label))
        labels.sort(key=lambda value: (getattr(value, "language", None) not in {"ko", None, ""}, str(value)))
        policy = _effective_policy(schema_graph, predicate, project_id)
        records.append({
            "uri": str(predicate),
            "label": str(labels[0]) if labels else str(predicate).rsplit("#", 1)[-1].rsplit("/", 1)[-1],
            "editable": policy["editable"], "reason": policy["reason"],
            "domains": sorted(str(value) for value in schema_graph.objects(predicate, RDFS.domain) if isinstance(value, URIRef)),
            "ranges": sorted(str(value) for value in schema_graph.objects(predicate, RDFS.range) if isinstance(value, URIRef)),
        })
    return records


relation_palette = build_relation_catalog


def _class_closure(data_graph, schema_graph, endpoint):
    seen = set()
    pending = [value for value in data_graph.objects(endpoint, RDF.type) if isinstance(value, URIRef) and value != OWL.NamedIndividual]
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        for graph in (schema_graph, data_graph):
            pending.extend(value for value in graph.objects(current, RDFS.subClassOf) if isinstance(value, URIRef))
            pending.extend(value for value in graph.objects(current, OWL.equivalentClass) if isinstance(value, URIRef))
            pending.extend(value for value in graph.subjects(OWL.equivalentClass, current) if isinstance(value, URIRef))
    return seen


def _list_members(graph, head):
    members, seen = [], set()
    while head != RDF.nil:
        if head in seen:
            return None
        seen.add(head)
        first, rest = graph.value(head, RDF.first), graph.value(head, RDF.rest)
        if first is None or rest is None:
            return None
        members.append(first)
        head = rest
    return members


def _matches_constraint(schema_graph, classes, constraint, visited=None):
    if isinstance(constraint, URIRef):
        return constraint in {OWL.Thing, RDFS.Resource} or constraint in classes
    if not isinstance(constraint, BNode):
        return False
    visited = set(visited or ())
    if constraint in visited:
        return False
    visited.add(constraint)
    for relation, operation in ((OWL.unionOf, any), (OWL.intersectionOf, all)):
        head = schema_graph.value(constraint, relation)
        if head is not None:
            members = _list_members(schema_graph, head)
            return bool(members) and operation(_matches_constraint(schema_graph, classes, member, visited) for member in members)
    return False


def _property_constraints(schema_graph, predicate, direction):
    seen, pending, constraints = set(), [(predicate, direction)], set()
    while pending:
        current, current_direction = pending.pop()
        if (current, current_direction) in seen:
            continue
        seen.add((current, current_direction))
        constraints.update(schema_graph.objects(current, current_direction))
        pending.extend((parent, current_direction) for parent in schema_graph.objects(current, RDFS.subPropertyOf) if isinstance(parent, URIRef))
        pending.extend((other, current_direction) for other in schema_graph.objects(current, OWL.equivalentProperty) if isinstance(other, URIRef))
        pending.extend((other, current_direction) for other in schema_graph.subjects(OWL.equivalentProperty, current) if isinstance(other, URIRef))
        inverse_direction = RDFS.range if current_direction == RDFS.domain else RDFS.domain
        pending.extend((other, inverse_direction) for other in schema_graph.objects(current, OWL.inverseOf) if isinstance(other, URIRef))
        pending.extend((other, inverse_direction) for other in schema_graph.subjects(OWL.inverseOf, current) if isinstance(other, URIRef))
    return constraints


def _require_class_compatibility(data_graph, schema_graph, subject, predicate, target):
    for endpoint, direction, description in ((subject, RDFS.domain, "주체"), (target, RDFS.range, "대상")):
        constraints = _property_constraints(schema_graph, predicate, direction)
        classes = _class_closure(data_graph, schema_graph, endpoint)
        if any(not _matches_constraint(schema_graph, classes, constraint) for constraint in constraints):
            raise ProjectError(f"선택한 {description}의 클래스가 이 관계의 허용 범위와 맞지 않습니다.", 422)


def mutate_relation(ont_key, project_id, subject, predicate, object_uri, action="add"):
    """Change one directed relation in the selected data file as a transaction."""
    import app as studio
    import graph_versioning

    if not isinstance(action, str) or action not in {"add", "delete"}:
        raise ProjectError("관계 작업은 add 또는 delete여야 합니다.")
    if project_id is not None and not isinstance(project_id, str):
        raise ProjectError("프로젝트 ID는 문자열이어야 합니다.")
    project_id = project_id or None
    cfg = studio.ontology_config(ont_key)
    namespace = Namespace(cfg["prefix"])
    subject, predicate, target = _uri(subject), _uri(predicate), _uri(object_uri)
    data_path = studio.selected_data_path(ont_key, project_id)
    data_format = "turtle" if Path(data_path).suffix.lower() == ".ttl" else "xml"
    with graph_file_lock(data_path):
        current = studio._load_data_graph(ont_key, project_id)
        schema = studio.load_schema_graph(ont_key)
        if predicate not in _known_predicates(schema, current):
            raise ProjectError("선택한 스키마의 객체 속성 또는 등록된 PROV 관계만 선택할 수 있습니다.")
        policy = _effective_policy(schema, predicate, project_id)
        if not policy["editable"]:
            raise ProjectError(policy["reason"], 403)
        definitions = _definition_nodes(current, schema)
        if not _instance_endpoint(current, schema, namespace, subject, definitions) or not _instance_endpoint(current, schema, namespace, target, definitions):
            raise ProjectError("주체와 대상은 선택한 그래프 안에 실제로 등록된 인스턴스여야 합니다.")
        triple = (subject, predicate, target)
        exists = triple in current
        if (action == "add" and exists) or (action == "delete" and not exists):
            return {
                "success": True, "changed": False, "snapshot_id": None,
                "validation": {"shacl_supported": bool(cfg["shapes"]), "shacl_conforms": None,
                               "report": "변경 사항이 없어 검증과 저장을 실행하지 않았습니다."},
                "message": "이미 존재하는 관계입니다." if exists else "삭제할 관계가 없습니다.",
            }
        if action == "add":
            _require_class_compatibility(current, schema, subject, predicate, target)
        candidate = Graph()
        for prefix, bound_namespace in current.namespaces():
            candidate.bind(prefix, bound_namespace)
        for recorded_triple in current:
            candidate.add(recorded_triple)
        if action == "add":
            candidate.add(triple)
        else:
            candidate.remove(triple)
        validation = studio._validate_candidate(candidate, ont_key, project_id)
        snapshot = None
        try:
            snapshot = graph_versioning.create_snapshot(
                ont_key, current, description="관계 추가 전 자동 스냅샷" if action == "add" else "관계 삭제 전 자동 스냅샷",
                author="local_owner", project_id=project_id,
            )
            write_graph_atomic(candidate, data_path, format=data_format)
        except OSError as exc:
            message = (
                "관계 저장 중 파일 오류가 발생했습니다. 저장 전 상태의 스냅샷을 확인하세요: " + snapshot["snapshot_id"]
                if snapshot else "관계 저장 전에 스냅샷 생성이 실패했습니다. 데이터 파일을 변경하지 않았습니다."
            )
            raise ProjectError(message, 500) from exc
    return {
        "success": True, "changed": True, "snapshot_id": snapshot["snapshot_id"],
        "validation": validation, "message": "관계를 추가했습니다." if action == "add" else "관계를 삭제했습니다.",
        "subject": str(subject), "predicate": str(predicate), "object": str(target),
    }
