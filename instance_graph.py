"""Read-only projections and inspection of instance facts, separate from schema.

These helpers never write or expand the caller's graphs. Optional inference
uses a private graph and only exposes new relationships between instances that
already have facts in the selected data graph. URI references have no implied
existence, media verification, or generated content.
"""

from collections import Counter
import hashlib
from html import escape
import json
import math
import re
from urllib.parse import unquote, urlsplit

from rdflib import BNode, Graph, Literal, RDF, RDFS, URIRef
from rdflib.namespace import OWL, XSD

from project_store import ProjectError


_PALETTE = (
    "#2563eb", "#059669", "#d97706", "#7c3aed", "#dc2626",
    "#0891b2", "#db2777", "#65a30d", "#4f46e5", "#0d9488",
    "#9333ea", "#c2410c",
)
_EXTERNAL_GROUP = "__external__"
_UNTYPED_GROUP = "__untyped__"
_INFERENCE_MODES = {"none", "rdfs", "owlrl"}
_MAX_INFERENCE_INPUT_TRIPLES = 20000
_MAX_VISIBLE_EDGES = 10000
_SCHEMA_TYPES = {
    RDFS.Class, RDFS.Datatype, RDF.Property, OWL.Class, OWL.Ontology,
    OWL.Restriction, OWL.ObjectProperty, OWL.DatatypeProperty,
    OWL.AnnotationProperty, OWL.FunctionalProperty,
    OWL.InverseFunctionalProperty, OWL.TransitiveProperty,
    OWL.SymmetricProperty, OWL.AsymmetricProperty, OWL.ReflexiveProperty,
    OWL.IrreflexiveProperty, OWL.AllDifferent, OWL.AllDisjointClasses,
    OWL.AllDisjointProperties, OWL.Axiom, OWL.NegativePropertyAssertion,
}
_SCHEMA_PREDICATES = {
    RDF.type, RDF.first, RDF.rest,
    RDFS.subClassOf, RDFS.subPropertyOf, RDFS.domain, RDFS.range,
    OWL.imports, OWL.versionIRI, OWL.priorVersion, OWL.backwardCompatibleWith,
    OWL.incompatibleWith, OWL.equivalentClass, OWL.equivalentProperty,
    OWL.disjointWith, OWL.propertyDisjointWith, OWL.inverseOf,
    OWL.complementOf, OWL.unionOf, OWL.intersectionOf, OWL.oneOf,
    OWL.onProperty, OWL.someValuesFrom, OWL.allValuesFrom, OWL.hasValue,
    OWL.cardinality, OWL.minCardinality, OWL.maxCardinality,
    OWL.qualifiedCardinality, OWL.minQualifiedCardinality,
    OWL.maxQualifiedCardinality, OWL.onClass, OWL.onDataRange,
    OWL.propertyChainAxiom, OWL.hasKey, OWL.disjointUnionOf,
    OWL.members, OWL.distinctMembers, OWL.annotatedSource,
    OWL.annotatedProperty, OWL.annotatedTarget,
}
_VOCABULARY_PREFIXES = tuple(str(value) for value in (RDF, RDFS, OWL, XSD))
_GENERIC_TYPES = {OWL.NamedIndividual, RDFS.Resource, OWL.Thing}
_INVALID_URI_CHARACTERS = re.compile(r'[<>"{}\\^`|\x00-\x20]')


def _inputs(data_graph, schema_graph, namespace, inference="none"):
    if not isinstance(data_graph, Graph) or not isinstance(schema_graph, Graph):
        raise TypeError("Instance projections require RDFLib data and schema graphs")
    if not isinstance(namespace, str) or not namespace:
        raise ProjectError("인스턴스 네임스페이스가 필요합니다.")
    if inference not in _INFERENCE_MODES:
        raise ProjectError("inference는 none, rdfs, owlrl 중 하나여야 합니다.")
    return str(namespace)


def _local_name(value):
    uri = str(value)
    if "#" in uri:
        name = uri.rsplit("#", 1)[-1]
    else:
        name = uri.rstrip("/").rsplit("/", 1)[-1]
        if name == uri and ":" in uri:
            name = uri.rsplit(":", 1)[-1]
    return unquote(name or uri)


def _label(resource, data_graph, schema_graph):
    """Prefer Korean labels, then untagged/English labels, deterministically."""
    values = []
    for source_rank, graph in enumerate((data_graph, schema_graph)):
        for value in graph.objects(resource, RDFS.label):
            if not isinstance(value, Literal):
                continue
            language = (value.language or "").lower()
            language_rank = 0 if language.startswith("ko") else 1 if not language else 2 if language.startswith("en") else 3
            values.append((language_rank, source_rank, language, str(value)))
    return min(values)[-1] if values else _local_name(resource)


def _identifier(prefix, subject, predicate, object_value):
    terms = [subject.n3(), predicate.n3(), object_value.n3()]
    payload = json.dumps(terms, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return prefix + hashlib.sha256(payload).hexdigest()


def _triple_key(triple):
    return tuple(term.n3() for term in triple)


def _vocabulary(resource):
    return isinstance(resource, URIRef) and str(resource).startswith(_VOCABULARY_PREFIXES)


def _definitions(data_graph, schema_graph):
    """Exclude declared and implicitly referenced classes/properties from ABox."""
    definitions = set()
    classes = set()
    for graph in (schema_graph, data_graph):
        for subject, predicate, object_value in graph:
            if isinstance(predicate, URIRef):
                definitions.add(predicate)
            if predicate == RDF.type:
                if isinstance(object_value, URIRef):
                    definitions.add(object_value)
                    if object_value not in _GENERIC_TYPES and object_value not in _SCHEMA_TYPES and not _vocabulary(object_value):
                        classes.add(object_value)
                if object_value in _SCHEMA_TYPES:
                    definitions.add(subject)
                if object_value in (OWL.Class, RDFS.Class) and isinstance(subject, URIRef):
                    classes.add(subject)
            if predicate in _SCHEMA_PREDICATES and predicate != RDF.type:
                definitions.add(subject)
                if predicate in (RDFS.subClassOf, RDFS.domain, RDFS.range, OWL.equivalentClass, OWL.disjointWith):
                    if isinstance(object_value, URIRef):
                        definitions.add(object_value)
                        if not _vocabulary(object_value):
                            classes.add(object_value)
    return definitions, classes


def _instances(data_graph, definitions):
    return {
        subject for subject in data_graph.subjects()
        if isinstance(subject, URIRef) and subject not in definitions and not _vocabulary(subject)
    }


def _is_relationship(triple, definitions):
    subject, predicate, object_value = triple
    return (
        isinstance(subject, URIRef) and isinstance(predicate, URIRef)
        and isinstance(object_value, URIRef) and predicate not in _SCHEMA_PREDICATES
        and object_value not in definitions and not _vocabulary(object_value)
    )


def _inferred_relationships(data_graph, schema_graph, instances, definitions, inference):
    if inference == "none":
        return set()
    if len(data_graph) + len(schema_graph) > _MAX_INFERENCE_INPUT_TRIPLES:
        raise ProjectError("추론 입력은 20,000개 트리플까지 지원합니다. 큰 그래프는 inference=none으로 조회하세요.")
    import owlrl

    work = Graph()
    for graph in (data_graph, schema_graph):
        for triple in graph:
            work.add(triple)
    asserted = set(work)
    semantics = owlrl.RDFS_Semantics if inference == "rdfs" else owlrl.OWLRL_Semantics
    # Disable process-wide datatype conversion changes as well as extra axioms.
    owlrl.DeductiveClosure(semantics, improved_datatypes=False,
                          axiomatic_triples=False, datatype_axioms=False).expand(work)
    return {
        triple for triple in work
        if triple not in asserted and triple[0] in instances and triple[2] in instances
        and _is_relationship(triple, definitions)
        and not (triple[1] == OWL.sameAs and triple[0] == triple[2])
    }


def _projection(data_graph, schema_graph, namespace, include_external, inference):
    definitions, classes = _definitions(data_graph, schema_graph)
    instances = _instances(data_graph, definitions)
    selected = {uri for uri in instances if include_external or str(uri).startswith(namespace)}
    asserted = {
        triple for triple in data_graph
        if triple[0] in selected and _is_relationship(triple, definitions)
    }
    if include_external:
        # These objects are references, not newly asserted or verified instances.
        selected |= {triple[2] for triple in asserted}
    asserted = {triple for triple in asserted if triple[2] in selected}
    inferred = _inferred_relationships(data_graph, schema_graph, instances, definitions, inference)
    inferred = {triple for triple in inferred if triple[0] in selected and triple[2] in selected}
    return definitions, classes, instances, selected, asserted, inferred


def _types(resource, data_graph, schema_graph):
    values = {
        value for value in data_graph.objects(resource, RDF.type)
        if isinstance(value, URIRef) and value not in _GENERIC_TYPES and value not in _SCHEMA_TYPES
    }
    return [{"uri": str(value), "label": _label(value, data_graph, schema_graph)}
            for value in sorted(values, key=str)]


def _color(group):
    if group == _EXTERNAL_GROUP:
        return "#94a3b8"
    if group == _UNTYPED_GROUP:
        return "#64748b"
    digest = hashlib.sha256(group.encode("utf-8")).digest()
    return _PALETTE[int.from_bytes(digest[:4], "big") % len(_PALETTE)]


def _shape(group, external):
    if external:
        return "dot"
    name = _local_name(group).lower()
    if "task" in name or "run" in name or "activity" in name:
        return "diamond"
    if any(value in name for value in ("asset", "artifact", "image", "video", "audio", "product", "report")):
        return "box"
    if "project" in name or "pipeline" in name:
        return "star"
    if "timeline" in name or "shot" in name or "handoff" in name:
        return "ellipse"
    return "dot"


def _status(resource, data_graph):
    values = []
    for predicate, object_value in data_graph.predicate_objects(resource):
        name = _local_name(predicate).lower()
        if isinstance(object_value, Literal) and (name == "status" or name.endswith("status")):
            values.append((0 if name == "status" else 1, str(predicate), str(object_value)))
    return min(values)[-1] if values else None


def _node(resource, data_graph, schema_graph, namespace, instances, incoming, outgoing):
    uri = str(resource)
    label = _label(resource, data_graph, schema_graph)
    types = _types(resource, data_graph, schema_graph)
    external = not uri.startswith(namespace) or resource not in instances
    group = _EXTERNAL_GROUP if external else types[0]["uri"] if types else _UNTYPED_GROUP
    degree = incoming[resource] + outgoing[resource]
    type_labels = ", ".join(value["label"] for value in types) or "유형 미지정"
    title = ("<b>" + escape(label, quote=True) + "</b><br>유형: " + escape(type_labels, quote=True)
             + "<br>URI: " + escape(uri, quote=True) + "<br>관계 수: " + str(degree))
    return {
        "id": uri, "uri": uri, "label": label, "title": title, "types": types,
        "group": group, "color": _color(group), "shape": _shape(group, external),
        "size": round((13 if external else 18) + min(18, math.sqrt(degree) * 3), 2),
        "degree": degree, "incoming_count": incoming[resource], "outgoing_count": outgoing[resource],
        "external": external, "referenced_only": resource not in instances,
        "status": _status(resource, data_graph),
        "literal_count": sum(1 for value in data_graph.objects(resource) if isinstance(value, Literal)),
    }


def _edge(triple, data_graph, schema_graph, namespace, project_id, inferred=False, eligibility=None):
    from instance_relations import relation_is_editable, relation_policy

    subject, predicate, object_value = triple
    predicate_label = _label(predicate, data_graph, schema_graph)
    subject_label = _label(subject, data_graph, schema_graph)
    object_label = _label(object_value, data_graph, schema_graph)
    eligibility = eligibility or {}
    editable = not inferred and relation_is_editable(
        data_graph, schema_graph, namespace, subject, predicate, object_value, project_id=project_id,
        definitions=eligibility.get("definitions"),
        known_predicates=eligibility.get("known_predicates"))
    policy = relation_policy(predicate, project_id=project_id)
    reason = ("추론 관계는 읽기 전용입니다." if inferred else
              "" if editable else policy.get("reason") or "선택 데이터의 편집 가능한 개체 간 관계가 아닙니다.")
    provenance = "추론된 관계" if inferred else "명시된 관계"
    title = ("<b>" + escape(predicate_label, quote=True) + "</b><br>"
             + escape(subject_label, quote=True) + " → " + escape(object_label, quote=True)
             + "<br>URI: " + escape(str(predicate), quote=True) + "<br>" + provenance)
    return {
        "id": _identifier("edge_", subject, predicate, object_value),
        "from": str(subject), "to": str(object_value),
        "subject": str(subject), "predicate": str(predicate), "object": str(object_value),
        "subject_label": subject_label, "predicate_label": predicate_label, "object_label": object_label,
        "label": predicate_label, "title": title, "arrows": "to", "inferred": bool(inferred),
        "editable": bool(editable), "protected": not editable, "reason": reason,
        "dashes": bool(inferred),
        "color": {"color": "#a78bfa" if inferred else "#94a3b8", "highlight": "#2563eb"},
    }


def build_instance_graph(data_graph, schema_graph, namespace, include_external=False,
                         inference="none", limit=500, project_id=None):
    """Project selected URI instances, with stable IDs and optional read-only edges.

    ``limit`` bounds displayed nodes; totals and degree counts describe the full
    eligible projection. External references are included only on request.
    ``relation_predicates`` is the editing catalog; ``predicates`` describes
    displayed edges including protected and inferred predicates for filtering.
    """
    from instance_relations import _definition_nodes, _known_predicates, build_relation_catalog

    namespace = _inputs(data_graph, schema_graph, namespace, inference)
    if not isinstance(include_external, bool):
        raise ProjectError("include_external은 true 또는 false여야 합니다.")
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 1000:
        raise ProjectError("그래프 표시 개수는 1~1,000이어야 합니다.")
    definitions, classes, instances, selected, asserted, inferred = _projection(
        data_graph, schema_graph, namespace, include_external, inference)
    eligibility = {
        "definitions": _definition_nodes(data_graph, schema_graph),
        "known_predicates": _known_predicates(schema_graph, data_graph),
    }
    relations = asserted | inferred
    outgoing = Counter(subject for subject, _, _ in relations)
    incoming = Counter(object_value for _, _, object_value in relations)
    ordered = sorted(selected, key=lambda uri: (not str(uri).startswith(namespace) or uri not in instances, str(uri)))
    full_nodes = [_node(uri, data_graph, schema_graph, namespace, instances, incoming, outgoing) for uri in ordered]
    nodes = full_nodes[:limit]
    visible = {URIRef(value["id"]) for value in nodes}
    visible_relations = [triple for triple in sorted(relations, key=_triple_key)
                         if triple[0] in visible and triple[2] in visible]
    edges = [
        _edge(triple, data_graph, schema_graph, namespace, project_id,
              inferred=triple in inferred, eligibility=eligibility)
        for triple in visible_relations[:_MAX_VISIBLE_EDGES]
    ]
    edges_truncated = len(edges) < len(relations)
    counts = Counter(value["group"] for value in full_nodes)
    visible_counts = Counter(value["group"] for value in nodes)
    groups = []
    for group, count in sorted(counts.items()):
        label = ("외부 또는 미정의 참조" if group == _EXTERNAL_GROUP else
                 "유형 미지정" if group == _UNTYPED_GROUP else _label(URIRef(group), data_graph, schema_graph))
        groups.append({"id": group, "label": label, "color": _color(group),
                       "count": count, "visible_count": visible_counts[group]})
    predicate_counts = Counter(edge["predicate"] for edge in edges)
    predicate_asserted_counts = Counter(edge["predicate"] for edge in edges if not edge["inferred"])
    predicate_inferred_counts = Counter(edge["predicate"] for edge in edges if edge["inferred"])
    predicate_editable = {edge["predicate"] for edge in edges if edge["editable"]}
    predicates = []
    for uri, count in sorted(predicate_counts.items()):
        predicates.append({"uri": uri, "label": _label(URIRef(uri), data_graph, schema_graph),
                           "count": count, "asserted_count": predicate_asserted_counts[uri],
                           "inferred_count": predicate_inferred_counts[uri],
                           "editable": uri in predicate_editable})
    class_counts = Counter(value["uri"] for node in full_nodes for value in node["types"])
    class_metadata = [{"uri": str(uri), "label": _label(uri, data_graph, schema_graph),
                       "count": class_counts[str(uri)], "color": _color(str(uri))}
                      for uri in sorted(classes, key=str)]
    summary = {
        "total_nodes": len(full_nodes), "total_edges": len(relations),
        "visible_nodes": len(nodes), "visible_edges": len(edges),
        "truncated_nodes": len(nodes) < len(full_nodes),
        "truncated_edges": edges_truncated,
        "isolated_nodes": sum(node["degree"] == 0 for node in full_nodes),
        "inferred_edges": len(inferred), "asserted_edges": len(asserted),
        "visible_inferred_edges": sum(edge["inferred"] for edge in edges),
        "external_nodes": sum(node["external"] for node in full_nodes),
        "class_count": len(class_metadata), "predicate_count": len(predicates),
        "literal_count": sum(node["literal_count"] for node in full_nodes),
        "data_triples": len(data_graph),
        "excluded_schema_resources": len({subject for subject in data_graph.subjects() if subject in definitions}),
        "excluded_blank_nodes": len({subject for subject in data_graph.subjects() if isinstance(subject, BNode)}),
        "status_counts": dict(sorted(Counter(node["status"] for node in full_nodes if node["status"] is not None).items())),
        "inference": inference, "include_external": include_external,
    }
    return {
        "nodes": nodes, "edges": edges, "count_nodes": len(nodes), "count_edges": len(edges),
        "groups": groups, "classes": class_metadata, "predicates": predicates,
        "relation_predicates": build_relation_catalog(schema_graph, data_graph, project_id=project_id),
        "summary": summary,
        "truncated": len(nodes) < len(full_nodes) or edges_truncated,
        "truncated_edges": edges_truncated,
        "edge_limit": _MAX_VISIBLE_EDGES, "limit": limit,
        "inference": inference, "include_external": include_external,
    }


def _validated_uri(uri):
    if not isinstance(uri, str) or not uri or _INVALID_URI_CHARACTERS.search(uri):
        raise ProjectError("올바른 인스턴스 URI가 필요합니다.")
    try:
        parts = urlsplit(uri)
        if not parts.scheme or not (parts.netloc or parts.path):
            raise ValueError("URI must be absolute")
        if parts.scheme.lower() in ("http", "https") and not parts.hostname:
            raise ValueError("HTTP URI must have a host")
    except ValueError:
        raise ProjectError("올바른 인스턴스 URI가 필요합니다.") from None
    return URIRef(uri)


def describe_instance(data_graph, schema_graph, namespace, uri, project_id=None, inference="none"):
    """Inspect a selected instance or its existing reference without fetching it.

    Foreign URIs not present in this data projection are never inspected.
    References without their own asserted facts are explicitly read-only.
    ``triples`` retains the legacy simple property view alongside rich fields.
    """
    namespace = _inputs(data_graph, schema_graph, namespace, inference)
    resource = _validated_uri(uri)
    definitions, _, instances, selected, asserted, inferred = _projection(
        data_graph, schema_graph, namespace, True, inference)
    if resource in definitions or _vocabulary(resource):
        raise ProjectError("클래스와 속성 정의는 인스턴스 편집 대상이 아닙니다.")
    if resource not in selected:
        raise ProjectError("선택 데이터의 인스턴스나 참조를 찾을 수 없습니다.", 404)
    relations = asserted | inferred
    outgoing_counts = Counter(subject for subject, _, _ in relations)
    incoming_counts = Counter(object_value for _, _, object_value in relations)
    node = _node(resource, data_graph, schema_graph, namespace, instances, incoming_counts, outgoing_counts)
    literals = []
    triples = []
    for subject, predicate, object_value in sorted(data_graph.triples((resource, None, None)), key=_triple_key):
        predicate_label = _label(predicate, data_graph, schema_graph)
        triples.append({"predicate": predicate_label,
                        "object": _label(object_value, data_graph, schema_graph) if isinstance(object_value, URIRef) else str(object_value),
                        "predicate_uri": str(predicate),
                        "object_uri": str(object_value) if isinstance(object_value, URIRef) else None})
        if isinstance(object_value, Literal):
            literals.append({
                "id": _identifier("literal_", subject, predicate, object_value),
                "predicate": predicate_label, "predicate_uri": str(predicate), "object": str(object_value),
                "datatype": str(object_value.datatype) if object_value.datatype else None,
                "language": object_value.language or None,
                "editable": False, "protected": True,
            })
    from instance_relations import _definition_nodes, _known_predicates
    eligibility = {"definitions": _definition_nodes(data_graph, schema_graph),
                   "known_predicates": _known_predicates(schema_graph, data_graph)}
    outgoing = [
        _edge(triple, data_graph, schema_graph, namespace, project_id,
              inferred=triple in inferred, eligibility=eligibility)
        for triple in sorted(relations, key=_triple_key) if triple[0] == resource
    ]
    incoming = [
        _edge(triple, data_graph, schema_graph, namespace, project_id,
              inferred=triple in inferred, eligibility=eligibility)
        for triple in sorted(relations, key=_triple_key) if triple[2] == resource
    ]
    readonly = node["external"] or node["referenced_only"]
    return {
        **node, "uri": str(resource), "triples": triples, "literals": literals,
        "outgoing": outgoing, "incoming": incoming,
        "literal_count": len(literals), "triple_count": len(triples),
        "readonly": readonly, "readOnly": readonly, "editable": not readonly,
        "protected": readonly, "inference": inference,
        "asserted_outgoing_count": sum(not edge["inferred"] for edge in outgoing),
        "asserted_incoming_count": sum(not edge["inferred"] for edge in incoming),
        "inferred_outgoing_count": sum(edge["inferred"] for edge in outgoing),
        "inferred_incoming_count": sum(edge["inferred"] for edge in incoming),
    }
