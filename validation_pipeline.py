"""Keep explicit-data acceptance separate from RDFS-expanded diagnostics.

Asserted dictionary types (e.g. controlled privacy concepts) are valid source
facts. Domain/range inference must never stand in for an instance's recorded
type. Reports can be reduced to counts before exposing clinical results.
"""

from rdflib import BNode, Graph, Literal, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SH
import pyshacl


def _class_constraint(schema, shapes, value, seen=None):
    seen = set() if seen is None else seen
    if value in seen:
        return None
    seen.add(value)
    head = schema.value(value, OWL.unionOf)
    if isinstance(value, URIRef) and head is None:
        if not ({OWL.Class, RDFS.Class} & set(schema.objects(value, RDF.type))):
            return None
        constraint = BNode()
        shapes.add((constraint, SH["class"], value))
        return constraint
    if head is None:
        return None
    members = [_class_constraint(schema, shapes, item, seen.copy()) for item in schema.items(head)]
    if not members or any(member is None for member in members):
        return None
    if isinstance(value, URIRef) and {OWL.Class, RDFS.Class} & set(schema.objects(value, RDF.type)):
        direct = BNode()
        shapes.add((direct, SH['class'], value))
        members.insert(0, direct)
    constraint, list_head = BNode(), BNode()
    shapes.add((constraint, SH["or"], list_head))
    cursor = list_head
    for index, member in enumerate(members):
        shapes.add((cursor, RDF.first, member))
        following = RDF.nil if index == len(members) - 1 else BNode()
        shapes.add((cursor, RDF.rest, following))
        cursor = following
    return constraint


def explicit_type_shapes(schema):
    """Require asserted compatible endpoint types for local class contracts.

    Subclass membership uses the asserted class hierarchy. Unspecified external
    classes and datatype ranges are outside this bounded contract.
    """
    shapes = Graph()
    for predicate, target in ((RDFS.domain, SH.targetSubjectsOf), (RDFS.range, SH.targetObjectsOf)):
        for prop, expected in schema.subject_objects(predicate):
            if not isinstance(prop, URIRef):
                continue
            constraint = _class_constraint(schema, shapes, expected)
            if constraint is not None:
                shapes.add((constraint, RDF.type, SH.NodeShape))
                shapes.add((constraint, target, prop))
                shapes.add((constraint, SH.message, Literal("An explicitly recorded compatible type is required; RDFS inference is not source evidence.")))
    return shapes


def validate_phases(data, schema, shapes):
    """Return independent raw/inferred reports; never mutate caller graphs."""
    raw = data + schema
    raw_shapes = shapes + explicit_type_shapes(schema)
    raw_ok, raw_report, raw_text = pyshacl.validate(raw, shacl_graph=raw_shapes, inference="none")
    expanded = data + schema
    inferred_ok, inferred_report, inferred_text = pyshacl.validate(
        expanded, shacl_graph=Graph() + shapes, inference="rdfs", inplace=True)
    instance_nodes = set(data.subjects()) | {value for value in data.objects() if isinstance(value, URIRef)}
    added_types = {(subject, kind) for subject, kind in expanded.subject_objects(RDF.type)
                   if subject in instance_nodes and (subject, RDF.type, kind) not in raw}
    return {"conforms": bool(raw_ok and inferred_ok), "raw_conforms": bool(raw_ok),
            "inferred_conforms": bool(inferred_ok), "inferred_type_count": len(added_types),
            "raw_results": len(set(raw_report.subjects(RDF.type, SH.ValidationResult))),
            "inferred_results": len(set(inferred_report.subjects(RDF.type, SH.ValidationResult))),
            "raw_report_graph": raw_report, "inferred_report_graph": inferred_report,
            "raw_report_text": raw_text, "inferred_report_text": inferred_text,
            "report_text": "[Explicit data and asserted schema]\n" + raw_text + "\n[RDFS-expanded diagnostics]\n" + inferred_text}


def public_summary(result):
    """Aggregate-only representation without identifiers or result messages."""
    return {key: result[key] for key in ("conforms", "raw_conforms", "inferred_conforms",
                                         "raw_results", "inferred_results", "inferred_type_count")}


def main(argv=None):
    import argparse
    import json
    from pathlib import Path
    from ontology_loader import load_schema_bundle, load_shape_graph
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--schema', required=True)
    parser.add_argument('--shapes', required=True)
    parser.add_argument('--json', type=Path)
    args = parser.parse_args(argv)
    data = Graph().parse(args.data, format='turtle' if args.data.suffix.lower() == '.ttl' else 'xml')
    schema, imports = load_schema_bundle(root, args.schema)
    result = public_summary(validate_phases(data, schema, load_shape_graph(root, args.shapes)))
    result['import_closure'] = imports
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + '\n'
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(encoded, encoding='utf-8')
    print(encoded)
    return 0 if result['conforms'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
