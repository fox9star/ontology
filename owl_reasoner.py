"""
W3C OWL 2 RL & RDFS Semantic Deductive Reasoning Engine
Executes rule-based deductive expansion on ontology graphs using owlrl,
inferring transitive hierarchies, inverse relationships, and domain/range entailments.
Distinguishes asserted facts from logically entailed triples.
"""

import itertools
import json
import re

import owlrl
import rdflib
from rdflib import URIRef, Literal, RDF, RDFS, OWL, XSD
from rdflib.collection import Collection


def find_disjoint_type_violations(graph):
    """Find individuals assigned to both sides of declared disjoint classes."""
    disjoint_pairs = set()
    for left, right in graph.subject_objects(OWL.disjointWith):
        if isinstance(left, URIRef) and isinstance(right, URIRef):
            disjoint_pairs.add(tuple(sorted((left, right), key=str)))
    for declaration in graph.subjects(RDF.type, OWL.AllDisjointClasses):
        head = graph.value(declaration, OWL.members) or graph.value(declaration, OWL.distinctMembers)
        if head is None:
            continue
        members = [value for value in Collection(graph, head) if isinstance(value, URIRef)]
        for index, left in enumerate(members):
            for right in members[index + 1:]:
                disjoint_pairs.add(tuple(sorted((left, right), key=str)))

    violations = []
    for individual in set(graph.subjects(RDF.type, None)):
        types = set(graph.objects(individual, RDF.type))
        for left, right in disjoint_pairs:
            if left in types and right in types:
                violations.append({
                    "individual": str(individual),
                    "classes": [str(left), str(right)],
                })
    return sorted(violations, key=lambda item: (item["individual"], item["classes"]))


_INTEGER_BOUNDS = {
    XSD.integer: (None, None), XSD.nonPositiveInteger: (None, 0),
    XSD.negativeInteger: (None, -1), XSD.nonNegativeInteger: (0, None),
    XSD.positiveInteger: (1, None), XSD.long: (-(2**63), 2**63 - 1),
    XSD.int: (-(2**31), 2**31 - 1), XSD.short: (-(2**15), 2**15 - 1),
    XSD.byte: (-128, 127), XSD.unsignedLong: (0, 2**64 - 1),
    XSD.unsignedInt: (0, 2**32 - 1), XSD.unsignedShort: (0, 2**16 - 1),
    XSD.unsignedByte: (0, 255),
}
_CHECKED_DATATYPES = set(_INTEGER_BOUNDS) | {
    XSD.boolean, XSD.decimal, XSD.float, XSD.double, XSD.date, XSD.dateTime,
}
_COMPARABLE_DATATYPES = set(_INTEGER_BOUNDS) | {
    XSD.boolean, XSD.decimal, XSD.float, XSD.double, XSD.string, RDF.langString, None,
}


def _invalid_literal(value):
    """Check an explicitly bounded subset, preserving original lexical forms."""
    if not isinstance(value, Literal) or value.datatype not in _CHECKED_DATATYPES:
        return False
    lexical = str(value).strip(" \t\r\n")
    if value.datatype in _INTEGER_BOUNDS:
        if not re.fullmatch(r"[+-]?[0-9]+", lexical):
            return True
        minimum, maximum = _INTEGER_BOUNDS[value.datatype]
        if minimum is None and maximum is None:
            return False
        digits = lexical.lstrip("+-").lstrip("0")
        # XSD integers are unbounded; Python's defensive digit limit must not
        # reject them. All finite bounds below fit in at most twenty digits.
        number = ((-1 if lexical.startswith("-") else 1) * 10**31
                  if len(digits) > 30 else int(("-" if lexical.startswith("-") else "") + (digits or "0")))
        return (minimum is not None and number < minimum) or (maximum is not None and number > maximum)
    if value.datatype == XSD.boolean:
        return lexical not in {"true", "false", "1", "0"}
    if value.datatype == XSD.decimal:
        return re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)", lexical) is None
    if value.datatype in {XSD.float, XSD.double}:
        return (lexical not in {"INF", "-INF", "NaN"}
                and re.fullmatch(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?", lexical) is None)
    return value.ill_typed is True


def _literal_equal(left, right):
    """Return true/false only when RDFLib knows the values; otherwise unknown."""
    if not isinstance(left, Literal) or not isinstance(right, Literal):
        return None
    if _invalid_literal(left) or _invalid_literal(right):
        return None
    if left == right:
        return True
    if left.datatype not in _COMPARABLE_DATATYPES or right.datatype not in _COMPARABLE_DATATYPES:
        return None
    if left.datatype == right.datatype == XSD.boolean:
        return (str(left).strip(" \t\r\n") in {"1", "true"}) == (str(right).strip(" \t\r\n") in {"1", "true"})
    if ((left.datatype in {XSD.float, XSD.double} and str(left).strip(" \t\r\n") == "NaN")
            or (right.datatype in {XSD.float, XSD.double} and str(right).strip(" \t\r\n") == "NaN")):
        return None
    try:
        answer = left.eq(right)
    except (TypeError, ValueError):
        return None
    return answer if isinstance(answer, bool) else None


def _term(value):
    return value.n3() if isinstance(value, Literal) else str(value)


def _declared_pairs(graph, relation, collection_type):
    pairs = {tuple(sorted((left, right), key=_term)) for left, right in graph.subject_objects(relation)}
    for declaration in graph.subjects(RDF.type, collection_type):
        head = graph.value(declaration, OWL.members) or graph.value(declaration, OWL.distinctMembers)
        if head is not None:
            pairs.update(tuple(sorted(pair, key=_term)) for pair in itertools.combinations(Collection(graph, head), 2))
    return pairs


def find_semantic_violations(graph):
    """Find the documented consistency patterns on an already expanded graph.

    Distinct IRIs do not imply distinct individuals. Functional object properties
    and inverse functional properties therefore only force equality; conflicts
    require explicit inequality or provably different literal values.
    """
    parent = {}

    def representative(value):
        parent.setdefault(value, value)
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    for left, right in graph.subject_objects(OWL.sameAs):
        left_root, right_root = representative(left), representative(right)
        if left_root != right_root:
            parent[right_root] = left_root

    def equal(left, right):
        return representative(left) == representative(right) or _literal_equal(left, right) is True

    different_pairs = _declared_pairs(graph, OWL.differentFrom, OWL.AllDifferent)
    violations = []

    def add(kind, **details):
        violations.append({"kind": kind, **details})

    for violation in find_disjoint_type_violations(graph):
        add("disjoint_types", **violation)
    for left, right in different_pairs:
        if equal(left, right):
            add("identity_conflict", individuals=[_term(left), _term(right)])

    # Functional data properties can force equality of unequal values without
    # any explicit differentFrom statement. URI objects alone are not conflicts.
    for predicate in graph.subjects(RDF.type, OWL.FunctionalProperty):
        for subject in set(graph.subjects(predicate, None)):
            values = set(graph.objects(subject, predicate))
            for left, right in itertools.combinations(sorted(values, key=_term), 2):
                if _literal_equal(left, right) is False:
                    add("functional_literal_conflict", subject=_term(subject),
                        property=_term(predicate), values=[_term(left), _term(right)])

    for left, right in _declared_pairs(graph, OWL.propertyDisjointWith, OWL.AllDisjointProperties):
        for subject, value in graph.subject_objects(left):
            if any(equal(value, candidate) for candidate in graph.objects(subject, right)):
                add("disjoint_properties", subject=_term(subject), object=_term(value),
                    properties=[_term(left), _term(right)])

    for predicate in graph.subjects(RDF.type, OWL.IrreflexiveProperty):
        for subject, value in graph.subject_objects(predicate):
            if equal(subject, value):
                add("irreflexive_property", subject=_term(subject), property=_term(predicate), object=_term(value))
    for predicate in graph.subjects(RDF.type, OWL.AsymmetricProperty):
        for subject, value in graph.subject_objects(predicate):
            if (value, predicate, subject) in graph or equal(subject, value):
                endpoints = sorted([_term(subject), _term(value)])
                add("asymmetric_property", property=_term(predicate), individuals=endpoints)

    for assertion in graph.subjects(RDF.type, OWL.NegativePropertyAssertion):
        subject = graph.value(assertion, OWL.sourceIndividual)
        predicate = graph.value(assertion, OWL.assertionProperty)
        target = graph.value(assertion, OWL.targetIndividual)
        if target is None:
            target = graph.value(assertion, OWL.targetValue)
        if subject is not None and predicate is not None and target is not None:
            if any(equal(target, candidate) for candidate in graph.objects(subject, predicate)):
                add("negative_property_assertion", subject=_term(subject),
                    property=_term(predicate), object=_term(target))

    # Collapse closure-added occurrences of an invalid literal to one diagnostic.
    for value in set(graph.objects()):
        if _invalid_literal(value):
            add("invalid_literal", value=_term(value), datatype=str(value.datatype))
    unique = {json.dumps(violation, sort_keys=True): violation for violation in violations}
    return [unique[key] for key in sorted(unique)]


def run_owl_deductive_closure(graph, semantics="owlrl"):
    """
    Applies OWL 2 RL or RDFS deductive closure to the provided rdflib.Graph.
    Returns inference metrics and sample entailed facts.
    """
    asserted_triples = set(graph)

    # Execute deductive expansion in-place
    if semantics == "rdfs":
        owlrl.DeductiveClosure(owlrl.RDFS_Semantics).expand(graph)
    else:
        owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(graph)

    all_triples = set(graph)
    inferred_triples = all_triples - asserted_triples
    disjoint_violations = find_disjoint_type_violations(graph)
    semantic_violations = find_semantic_violations(graph)

    # Categorize and sample inferred facts
    subclass_inferences = []
    inverse_or_other = []

    for s, p, o in sorted(inferred_triples, key=lambda triple: tuple(_term(value) for value in triple)):
        s_lbl = str(s).split("#")[-1].split("/")[-1]
        p_lbl = str(p).split("#")[-1].split("/")[-1]
        o_lbl = str(o).split("#")[-1].split("/")[-1]

        item = {
            "subject": s_lbl,
            "predicate": p_lbl,
            "object": o_lbl,
            "is_inferred": True
        }

        if p == RDF.type:
            subclass_inferences.append(item)
        else:
            inverse_or_other.append(item)

    return {
        "success": True,
        "semantics": semantics,
        "asserted_count": len(asserted_triples),
        "inferred_count": len(inferred_triples),
        "total_expanded_count": len(all_triples),
        "subclass_inferred_count": len(subclass_inferences),
        "relation_inferred_count": len(inverse_or_other),
        "consistent": not semantic_violations,
        "consistency_scope": "documented-patterns; see SEMANTIC_VALIDATION.md",
        "semantic_violations": semantic_violations,
        "disjoint_type_violations": disjoint_violations,
        "samples": (subclass_inferences[:10] + inverse_or_other[:10])
    }
