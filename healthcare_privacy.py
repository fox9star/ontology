"""Read-time redaction policy for non-synthetic healthcare instance graphs."""

from rdflib import Graph, Namespace
from rdflib.namespace import RDF

HEALTH = Namespace("http://example.org/ontology/healthcare#")
RDFS_LABEL = Namespace("http://www.w3.org/2000/01/rdf-schema#").label
PROV = Namespace("http://www.w3.org/ns/prov#")


def redact_graph(source):
    """Return a copy hiding unverified/protected records and their result nodes.

    Direct patient keys are removed even for records explicitly classified as
    synthetic. Any absent, conflicting, or unknown classification is treated
    as protected by default.
    """
    graph = Graph()
    graph += source

    records = set(graph.subjects(RDF.type, HEALTH.PatientRecord))
    protected_records = set()
    for record in records:
        classifications = set(graph.objects(record, HEALTH.dataClassification))
        if classifications != {HEALTH.Synthetic}:
            protected_records.add(record)

    protected_tasks = {
        task
        for record in protected_records
        for task in graph.subjects(HEALTH.associatedWithRecord, record)
    }
    protected_results = set()
    for record in protected_records:
        protected_results.update(graph.subjects(HEALTH.observesRecord, record))
    for task in protected_tasks:
        protected_results.update(graph.objects(task, HEALTH.generatesReport))
        protected_results.update(graph.objects(task, HEALTH.generatesObservation))
    protected_results.update(
        report for report in graph.subjects(PROV.wasGeneratedBy, None)
        if any(task in protected_tasks for task in graph.objects(report, PROV.wasGeneratedBy))
    )
    hidden = protected_records | protected_tasks | protected_results

    for triple in list(graph):
        subject, predicate, obj = triple
        if subject in hidden or obj in hidden:
            graph.remove(triple)
        elif predicate == HEALTH.patientId:
            graph.remove(triple)
        elif subject in protected_records and predicate == RDFS_LABEL:
            graph.remove(triple)
    return graph
