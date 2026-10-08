"""Check that SHACL literal codes stay aligned with the SKOS vocabularies."""

from pathlib import Path

from rdflib import Graph, Namespace, URIRef
from rdflib.namespace import RDF, RDFS
from rdflib.collection import Collection

ROOT = Path(__file__).resolve().parent
SH = Namespace("http://www.w3.org/ns/shacl#")
SKOS = Namespace("http://www.w3.org/2004/02/skos/core#")
HEALTH = Namespace("http://example.org/ontology/healthcare#")
VOCAB = Namespace("https://example.org/ontology/vocab#")

STATUS_SCHEMES = (
    ("mv-shapes.ttl", URIRef("https://example.org/mv#status"), VOCAB.MVStatusScheme),
    ("agent-shapes.ttl", URIRef("https://example.org/agent#status"), VOCAB.AgentRunStatusScheme),
    ("agent-shapes.ttl", URIRef("https://example.org/agent#decision"), VOCAB.ReviewDecisionScheme),
    ("devops-shapes.ttl", URIRef("http://example.org/ontology/devops#executionStatus"), VOCAB.DevOpsStatusScheme),
    ("ecommerce-shapes.ttl", URIRef("http://example.org/ontology/ecommerce#orderStatus"), VOCAB.EcommerceOrderStatusScheme),
    ("ecommerce-shapes.ttl", URIRef("http://example.org/ontology/ecommerce#priceCurrencyStatus"), VOCAB.EcommerceCurrencyStatusScheme),
    ("ecommerce-shapes.ttl", URIRef("http://example.org/ontology/ecommerce#fromStatus"), VOCAB.EcommerceOrderStatusScheme),
    ("ecommerce-shapes.ttl", URIRef("http://example.org/ontology/ecommerce#toStatus"), VOCAB.EcommerceOrderStatusScheme),
    ("healthcare-shapes.ttl", URIRef("http://example.org/ontology/healthcare#diagnosticStatus"), VOCAB.HealthcareDiagnosticStatusScheme),
    ("healthcare-shapes.ttl", URIRef("http://example.org/ontology/healthcare#taskIntent"), HEALTH.DiagnosticTaskIntentScheme),
    ("healthcare-shapes.ttl", URIRef("http://example.org/ontology/healthcare#observationStatus"), HEALTH.ClinicalObservationStatusScheme),
    ("healthcare-shapes.ttl", URIRef("http://example.org/ontology/healthcare#reportStatus"), HEALTH.ClinicalReportStatusScheme),
)


def _shape_codes(path, property_iri):
    graph = Graph().parse(ROOT / path, format="turtle")
    values = set()
    found = False
    for property_shape in graph.subjects(SH.path, property_iri):
        for head in graph.objects(property_shape, SH["in"]):
            found = True
            values.update(str(value) for value in Collection(graph, head))
    return values if found else None


def _scheme_codes(graph, scheme):
    codes = []
    for concept in graph.subjects(SKOS.inScheme, scheme):
        codes.extend(str(value) for value in graph.objects(concept, SKOS.notation))
    return codes


def check_vocabularies(root=ROOT):
    """Return human-readable consistency errors without modifying files."""
    root = Path(root)
    vocabulary = Graph().parse(root / "controlled-vocabularies.ttl", format="turtle")
    errors = []
    for path, property_iri, scheme in STATUS_SCHEMES:
        allowed = _shape_codes(root / path, property_iri)
        if allowed is None:
            errors.append(f"{path}: no sh:in values for {property_iri}")
            continue
        notations = _scheme_codes(vocabulary, scheme)
        if len(notations) != len(set(notations)):
            errors.append(f"{scheme}: duplicate skos:notation values")
        if allowed != set(notations):
            errors.append(
                f"{scheme}: SKOS codes {sorted(notations)} do not match SHACL codes {sorted(allowed)}"
            )

    healthcare_schema = Graph().parse(root / "healthcare-schema.ttl", format="turtle")
    privacy_values = set(healthcare_schema.subjects(RDF.type, HEALTH.PrivacyClassification))
    privacy_vocab_values = set(vocabulary.subjects(SKOS.inScheme, HEALTH.PrivacyClassificationScheme))
    if privacy_values != privacy_vocab_values:
        errors.append("Healthcare privacy classes do not match their SKOS concept scheme")

    for concept in vocabulary.subjects(RDF.type, SKOS.Concept):
        languages = {label.language for label in vocabulary.objects(concept, SKOS.prefLabel)}
        if not {"ko", "en"}.issubset(languages):
            errors.append(f"{concept}: requires Korean and English skos:prefLabel values")
        if not list(vocabulary.objects(concept, SKOS.notation)):
            errors.append(f"{concept}: missing skos:notation")
    return errors


def main():
    errors = check_vocabularies()
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print(f"OK: {len(STATUS_SCHEMES)} status schemes and healthcare privacy concepts match SHACL.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
