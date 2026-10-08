"""Reproducible canonical MV catalog-query benchmark with correctness gates."""

import argparse
import ctypes
from datetime import datetime, timezone
import hashlib
from importlib.metadata import version
import json
import math
import os
from pathlib import Path
import platform
import statistics
import time
import tracemalloc

import pyshacl
from rdflib.namespace import OWL

from benchmark_workload import ROOT, catalog_queries, expected_answers, generate_workload, query_answer
from ontology_loader import load_schema_graph, load_shape_graph

WORKLOAD_VERSION = "canonical-mv-archive-v1"
BENCHMARK_SIZES = [10000, 100000]


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _working_set():
    """Current and lifetime peak process working set, bytes; Windows native API."""
    if os.name != "nt":
        return None
    class Counters(ctypes.Structure):
        _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t), ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = ctypes.c_void_p
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(Counters), ctypes.c_ulong]
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return {"current_bytes": counters.WorkingSetSize, "lifetime_peak_bytes": counters.PeakWorkingSetSize}


def environment(schema, queries):
    return {
        "python": platform.python_version(), "platform": platform.platform(),
        "machine": platform.machine(), "processor": platform.processor(), "cpu_count": os.cpu_count(),
        "packages": {name: version(name) for name in ("rdflib", "pyshacl", "owlrl")},
        "workload_version": WORKLOAD_VERSION,
        "schema_versions": sorted(str(value) for value in schema.objects(None, OWL.versionInfo)),
        "schema_source_sha256": {name: _sha(ROOT / name) for name in (
            "mv-schema.ttl", "core-schema.ttl", "controlled-vocabularies.ttl", "mv-shapes.ttl",
            "core-shapes.ttl", "property-contract-shapes.ttl")},
        "catalog_queries_sha256": hashlib.sha256(json.dumps(queries, sort_keys=True).encode()).hexdigest(),
    }


def compare_baseline(current, baseline, max_regression_percent=25):
    """Only compare equal workload, schema, query, engine, size, and run policy."""
    comparable_keys = ("python", "platform", "machine", "processor", "cpu_count", "packages", "workload_version",
                       "schema_versions", "schema_source_sha256", "catalog_queries_sha256")
    differences = [key for key in comparable_keys if current["environment"].get(key) != baseline["environment"].get(key)]
    if current["policy"] != baseline["policy"]:
        differences.append("policy")
    if differences:
        return {"comparable": False, "incompatible_fields": differences, "regressions": []}
    old_by_size = {row["requested_triples"]: row for row in baseline["sizes"]}
    new_sizes = [row['requested_triples'] for row in current['sizes']]
    if not new_sizes or len(old_by_size) != len(baseline['sizes']) or len(set(new_sizes)) != len(new_sizes) or set(new_sizes) != set(old_by_size):
        return {"comparable": False, "incompatible_fields": ["sizes"], "regressions": []}
    rows, regressions = [], []
    for size in current["sizes"]:
        old = old_by_size.get(size["requested_triples"])
        if old is None or old["actual_data_triples"] != size["actual_data_triples"]:
            return {"comparable": False, "incompatible_fields": ["sizes"], "regressions": []}
        if not size['queries'] or set(size['queries']) != set(old['queries']):
            return {"comparable": False, "incompatible_fields": ["queries"], "regressions": []}
        for identifier, query in size["queries"].items():
            old_query = old["queries"].get(identifier)
            if old_query is None or old_query["answer_sha256"] != query["answer_sha256"]:
                return {"comparable": False, "incompatible_fields": ["answers"], "regressions": []}
            for metric in ("p50_ms", "p95_ms", "traced_query_peak_bytes"):
                previous, observed = old_query[metric], query[metric]
                change = (observed / previous - 1) * 100 if previous else 0
                row = {"requested_triples": size["requested_triples"], "question": identifier,
                       "metric": metric, "baseline": previous, "current": observed,
                       "change_percent": round(change, 2)}
                rows.append(row)
                if change > max_regression_percent:
                    regressions.append(row)
    return {"comparable": True, "threshold_percent": max_regression_percent,
            "measurements": rows, "regressions": regressions}


def run_benchmark(sizes=BENCHMARK_SIZES, repeats=10, warmups=1, baseline=None, max_regression_percent=25):
    if repeats < 10 or warmups < 1:
        raise ValueError("Use at least 10 measured repetitions and one warm-up")
    queries = catalog_queries()
    if len(queries) != 6:
        raise ValueError("Expected six BMV catalog questions")
    schema = load_schema_graph(ROOT, "mv-schema.ttl")
    shapes = load_shape_graph(ROOT, "mv-shapes.ttl")
    report = {"created_at": datetime.now(timezone.utc).isoformat(), "environment": environment(schema, queries),
              "policy": {"warmups": warmups, "measured_repetitions": repeats, "query_mode": "raw-data-no-inference",
                         "query_preparation": "graph.query text parsing included", "p95_method": "nearest-rank",
                         "memory_method": "one additional tracemalloc query outside timed repetitions; Windows process working set",
                         "validation_mode": "full data graph plus canonical imported schemas; inference none"}, "sizes": []}
    for target in sizes:
        print(f"Generating and validating {target} requested data triples...", flush=True)
        started = time.perf_counter()
        graph, metadata = generate_workload(target)
        generation_seconds = time.perf_counter() - started
        validation_started = time.perf_counter()
        conforms, _, validation_text = pyshacl.validate(graph, shacl_graph=shapes, ont_graph=schema,
                                                      inference="none", inplace=False, advanced=True)
        validation_seconds = time.perf_counter() - validation_started
        if not conforms:
            raise ValueError(f"Generated benchmark dataset failed SHACL: {validation_text}")
        answers = expected_answers(metadata)
        record = dict(metadata, generation_seconds=round(generation_seconds, 4),
                      validation_seconds=round(validation_seconds, 4), shacl_conforms=True,
                      working_set_after_validation=_working_set(), queries={})
        for identifier, query in queries.items():
            for _ in range(warmups):
                observed = query_answer(graph, query)
                if observed != answers[identifier]:
                    raise AssertionError(f"Warm-up answer mismatch: {identifier}: {observed}")
            timings = []
            for _ in range(repeats):
                started = time.perf_counter()
                observed = query_answer(graph, query)
                timings.append((time.perf_counter() - started) * 1000)
                if observed != answers[identifier]:
                    raise AssertionError(f"Measured answer mismatch: {identifier}: {observed}")
            tracemalloc.start()
            try:
                memory_observed = query_answer(graph, query)
                _, peak = tracemalloc.get_traced_memory()
            finally:
                tracemalloc.stop()
            if memory_observed != answers[identifier]:
                raise AssertionError(f"Memory-run answer mismatch: {identifier}")
            ordered = sorted(timings)
            record["queries"][identifier] = {
                "p50_ms": round(statistics.median(timings), 4),
                "p95_ms": round(ordered[math.ceil(0.95 * len(ordered)) - 1], 4),
                "runs_ms": [round(t, 4) for t in timings], "traced_query_peak_bytes": peak,
                "result_correct": True, "result_rows": len(observed["rows"]),
                "answer_sha256": hashlib.sha256(json.dumps(observed, sort_keys=True).encode()).hexdigest(),
                "answer": observed,
            }
            print(f"{len(graph)} triples {identifier}: p50={record['queries'][identifier]['p50_ms']:.2f} ms "
                  f"p95={record['queries'][identifier]['p95_ms']:.2f} ms; correct", flush=True)
        record["working_set_after_queries"] = _working_set()
        report["sizes"].append(record)
    if baseline:
        report["comparison"] = compare_baseline(report, baseline, max_regression_percent)
    else:
        report["comparison"] = {"comparable": None, "reason": "Initial baseline; no previous comparable observation"}
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", nargs="+", type=int, default=BENCHMARK_SIZES)
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--warmups", type=int, default=1)
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "sparql-benchmark.json")
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--max-regression-percent", type=float, default=25)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text(encoding="utf-8")) if args.baseline else None
    report = run_benchmark(args.sizes, args.repeats, args.warmups, baseline, args.max_regression_percent)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Report saved: {args.output}", flush=True)
    return 1 if report["comparison"].get("comparable") is False or report["comparison"].get("regressions") else 0


if __name__ == "__main__":
    raise SystemExit(main())
