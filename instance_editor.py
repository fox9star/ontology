"""Validated instance creation/deletion with locked, atomic data transactions."""

import os
from pathlib import Path
from uuid import uuid4

from rdflib import Graph, Literal, Namespace, RDF, RDFS, URIRef
from rdflib.namespace import OWL

import app as studio
from graph_io import graph_file_lock, write_graph_atomic
from instance_relations import (
    PROTECTED_PREDICATES,
    PROJECT_PROTECTED_PREDICATES,
    _definition_nodes,
    _effective_policy,
    _instance_endpoint,
    _require_class_compatibility,
    _uri,
)


def _data_graph(path):
    graph = Graph()
    format = "turtle" if Path(path).suffix.lower() == ".ttl" else "xml"
    if os.path.exists(path):
        graph.parse(path, format=format)
    return graph, format


def _schema_graph(ont_key):
    return studio.load_schema_graph(ont_key)


def _allowed_classes(data_graph, schema_graph, namespace_uri):
    definitions = _definition_nodes(data_graph, schema_graph)
    prefix = str(namespace_uri)
    is_domain_term = lambda value: isinstance(value, URIRef) and str(value).startswith(prefix)
    classes = {
        subject for subject in schema_graph.subjects(RDF.type, OWL.Class)
        if is_domain_term(subject)
    }
    classes.update(subject for subject in schema_graph.subjects(RDF.type, RDFS.Class)
                   if is_domain_term(subject))
    classes.update(
        kind for subject, kind in data_graph.subject_objects(RDF.type)
        if isinstance(subject, URIRef) and subject not in definitions
        and is_domain_term(kind)
        and kind not in {OWL.NamedIndividual, OWL.Thing, RDFS.Resource, OWL.Class, RDFS.Class}
    )
    return classes, definitions


def _creation_predicates(data_graph, schema_graph, namespace_uri):
    prefix = str(namespace_uri)
    kinds = {}
    for graph in (schema_graph, data_graph):
        for property_type in (OWL.ObjectProperty, OWL.DatatypeProperty, OWL.AnnotationProperty):
            for predicate in graph.subjects(RDF.type, property_type):
                if isinstance(predicate, URIRef) and str(predicate).startswith(prefix):
                    kinds.setdefault(predicate, set()).add(property_type)
    observed = {predicate for _, predicate, _ in data_graph
                if isinstance(predicate, URIRef) and str(predicate).startswith(prefix)}
    allowed = set(kinds) | observed | {RDFS.label}
    allowed.difference_update(PROTECTED_PREDICATES)
    allowed.difference_update(PROJECT_PROTECTED_PREDICATES)
    allowed.difference_update({RDF.type, RDFS.subClassOf, RDFS.subPropertyOf, RDFS.domain, RDFS.range,
                               OWL.equivalentClass, OWL.equivalentProperty, OWL.inverseOf})
    allowed = {predicate for predicate in allowed
               if _effective_policy(schema_graph, predicate, project_id=None)["editable"]}
    return allowed, kinds


def create_instance(ont_key, class_uri, label, properties=None, project_id=None):
    """Validate a candidate graph before replacing the selected data file."""
    cfg = studio.ontology_config(ont_key)
    if not isinstance(class_uri, str) or not class_uri.strip():
        raise ValueError("class_uri must be a nonempty string")
    if not isinstance(label, str) or not label.strip():
        raise ValueError("label must be a nonempty string")
    if properties is not None and not isinstance(properties, dict):
        raise ValueError("properties must be an object")
    data_path = studio.selected_data_path(ont_key, project_id)
    schema = _schema_graph(ont_key)
    namespace = Namespace(cfg["prefix"])
    with graph_file_lock(data_path):
        candidate, format = _data_graph(data_path)
        class_uri = str(_uri(class_uri))
        allowed_classes, definitions = _allowed_classes(candidate, schema, cfg["prefix"])
        class_ref = URIRef(class_uri)
        if class_ref not in allowed_classes:
            raise studio.project_store.ProjectError("선택한 클래스가 현재 온톨로지에 정의되어 있지 않습니다.", 422)
        allowed_predicates, property_kinds = _creation_predicates(candidate, schema, cfg["prefix"])
        initial_count = len(candidate)
        clean_label = "".join(character for character in label if character.isalnum() or character in ("_", "-")) or "NewItem"
        prefix = cfg["prefix"]
        instance_uri = URIRef(f"{prefix}{clean_label}_{uuid4().hex}")
        candidate.add((instance_uri, RDF.type, URIRef(class_uri)))
        candidate.add((instance_uri, RDFS.label, Literal(label, lang="ko")))
        for property_key, property_value in (properties or {}).items():
            if not property_value:
                continue
            if not isinstance(property_key, str):
                raise ValueError("Property names must be strings")
            predicate = URIRef(property_key if property_key.startswith("http") else f"{prefix}{property_key}")
            if predicate not in allowed_predicates:
                raise studio.project_store.ProjectError("선택한 온톨로지에서 사용 중인 편집 가능 속성만 새 개체에 추가할 수 있습니다.", 422)
            if isinstance(property_value, str) and property_value.startswith(("http://", "https://")):
                value = URIRef(property_value)
            else:
                value = Literal(str(property_value))
            kinds = property_kinds.get(predicate, set())
            is_object_property = OWL.ObjectProperty in kinds or (
                not kinds and any(isinstance(existing, URIRef) for existing in candidate.objects(None, predicate))
            )
            if is_object_property:
                if not isinstance(value, URIRef) or not _instance_endpoint(candidate, schema, namespace, value, definitions):
                    raise studio.project_store.ProjectError("관계 속성의 값은 선택한 데이터에 등록된 인스턴스여야 합니다.", 422)
                _require_class_compatibility(candidate, schema, instance_uri, predicate, value)
            elif isinstance(value, URIRef):
                raise studio.project_store.ProjectError("문자열 속성에는 URI가 아닌 문자 값을 입력해야 합니다.", 422)
            candidate.add((instance_uri, predicate, value))
        validation = studio._validate_candidate(candidate, ont_key, project_id)
        write_graph_atomic(candidate, data_path, format=format)
        count_added = len(candidate) - initial_count
    return {
        "success": True,
        "instance_uri": str(instance_uri),
        "label": label,
        "class_uri": class_uri,
        "triples_added": count_added,
        "shacl_supported": validation["shacl_supported"],
        "shacl_conforms": validation["shacl_conforms"],
        "report": validation["report"],
    }


def delete_instance(ont_key, instance_uri, project_id=None):
    """Remove incoming/outgoing triples only when the candidate remains valid."""
    config = studio.ontology_config(ont_key)
    if not isinstance(instance_uri, str) or not instance_uri.strip():
        raise ValueError("instance_uri must be a nonempty string")
    data_path = studio.selected_data_path(ont_key, project_id)
    schema = _schema_graph(ont_key)
    namespace = Namespace(config["prefix"])
    with graph_file_lock(data_path):
        if not os.path.exists(data_path):
            return {"success": False, "message": "Data file does not exist."}
        candidate, format = _data_graph(data_path)
        initial_count = len(candidate)
        target = _uri(instance_uri)
        definitions = _definition_nodes(candidate, schema)
        if not _instance_endpoint(candidate, schema, namespace, target, definitions):
            raise studio.project_store.ProjectError("삭제 대상은 선택한 데이터 안의 실제 인스턴스여야 합니다.", 422)
        protected = set(PROTECTED_PREDICATES) - {RDF.type}
        if project_id:
            protected.update(PROJECT_PROTECTED_PREDICATES)
        protected_incident = [
            (subject, predicate, obj) for subject, predicate, obj in candidate
            if (subject == target or obj == target)
            and (predicate in protected or str(predicate).startswith("http://www.w3.org/ns/prov#"))
        ]
        if protected_incident:
            raise studio.project_store.ProjectError(
                "삭제 대상이 출처·미디어·프로젝트 보호 관계에 연결되어 있습니다. 해당 연결은 유지해야 합니다.", 403
            )
        candidate.remove((target, None, None))
        candidate.remove((None, None, target))
        removed = initial_count - len(candidate)
        validation = studio._validate_candidate(candidate, ont_key, project_id)
        if removed:
            write_graph_atomic(candidate, data_path, format=format)
    return {
        "success": True,
        "instance_uri": instance_uri,
        "triples_removed": removed,
        "shacl_supported": validation["shacl_supported"],
        "shacl_conforms": validation["shacl_conforms"],
        "report": validation["report"],
    }
