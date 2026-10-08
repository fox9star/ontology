"""Workload conformance and performance-comparison trust boundaries."""

import copy
from pathlib import Path
import unittest

import pyshacl
from rdflib.namespace import OWL, RDF

import benchmark_sparql as benchmark
from benchmark_workload import MV, catalog_queries, expected_answers, generate_workload, query_answer
from ontology_loader import load_schema_graph, load_shape_graph

ROOT = Path(__file__).resolve().parents[1]


class BenchmarkTests(unittest.TestCase):
    def test_canonical_workload_is_conforming_and_uses_declared_mv_terms(self):
        graph, metadata = generate_workload(1000)
        schema = load_schema_graph(ROOT, "mv-schema.ttl")
        for subject, predicate, value in graph:
            for term in (predicate, value if predicate == RDF.type else None):
                if term is not None and str(term).startswith(str(MV)):
                    self.assertTrue(any(schema.triples((term, RDF.type, None))), str(term))
        conforms, _, text = pyshacl.validate(graph, shacl_graph=load_shape_graph(ROOT, "mv-shapes.ttl"),
                                            ont_graph=schema, inference="none", advanced=True)
        self.assertTrue(conforms, text)
        self.assertLess(len(graph) - 1000, 15)
        self.assertEqual(set(catalog_queries()), set(expected_answers(metadata)))

    def report(self):
        return {"environment": {"workload_version": "test", "packages": {"rdflib": "test"}},
                "policy": {"measured_repetitions": 10}, "sizes": [{"requested_triples": 10000,
                "actual_data_triples": 10008, "queries": {"BMV-01": {
                    "answer_sha256": "same", "p50_ms": 10.0, "p95_ms": 15.0,
                    "traced_query_peak_bytes": 1000}}}]}

    def test_measured_slowdown_and_memory_growth_trigger_regression(self):
        baseline = self.report()
        current = copy.deepcopy(baseline)
        current["sizes"][0]["queries"]["BMV-01"]["p95_ms"] = 20.0
        current["sizes"][0]["queries"]["BMV-01"]["traced_query_peak_bytes"] = 2000
        comparison = benchmark.compare_baseline(current, baseline)
        self.assertTrue(comparison["comparable"])
        self.assertEqual({row["metric"] for row in comparison["regressions"]},
                         {"p95_ms", "traced_query_peak_bytes"})

    def test_engine_schema_workload_answer_and_policy_changes_block_comparison(self):
        baseline = self.report()
        changes = (
            lambda r: r["environment"].update(packages={"rdflib": "new"}),
            lambda r: r["environment"].update(schema_source_sha256={"mv-schema.ttl": "changed"}),
            lambda r: r["environment"].update(workload_version="new"),
            lambda r: r["policy"].update(measured_repetitions=1),
            lambda r: r["sizes"][0]["queries"]["BMV-01"].update(answer_sha256="changed"),
            lambda r: r["sizes"][0].update(actual_data_triples=9000),
            lambda r: r.update(sizes=[]),
            lambda r: r["sizes"][0].update(queries={}),
        )
        for mutation in changes:
            with self.subTest(mutation=mutation):
                current = copy.deepcopy(baseline)
                mutation(current)
                self.assertFalse(benchmark.compare_baseline(current, baseline)["comparable"])

    def test_repetitions_must_supply_required_observations(self):
        with self.assertRaisesRegex(ValueError, "at least 10"):
            benchmark.run_benchmark([1000], repeats=1)
        with self.assertRaisesRegex(ValueError, "warm-up"):
            benchmark.run_benchmark([1000], repeats=10, warmups=0)


if __name__ == "__main__":
    unittest.main()
