"""Regenerate compatibility RDF/XML files from canonical Turtle schemas."""

import argparse
from pathlib import Path

from rdflib import Graph
from rdflib.compare import to_isomorphic
from ontology_catalog import load_custom_profiles


ROOT = Path(__file__).resolve().parent
EXPORTS = (
    ("mv-schema.ttl", "mv.owl"),
    ("agent-schema.ttl", "agent.owl"),
    ("devops-schema.ttl", "devops.owl"),
    ("ecommerce-schema.ttl", "ecommerce.owl"),
    ("healthcare-schema.ttl", "healthcare.owl"),
    ("academic-schema.ttl", "academic-schema.owl"),
    ("camping-schema.ttl", "camping.owl"),
    ("politics-schema.ttl", "politics.owl"),
    ("theme-park-schema.ttl", "theme-park.owl"),
)
EXPORTS += tuple((config['schema'], config['owl']) for config in load_custom_profiles(ROOT).values())


def read_turtle(filename):
    return Graph().parse(ROOT / filename, format="turtle")


def check_exports():
    drift = []
    for source, target in EXPORTS:
        canonical = read_turtle(source)
        exported = Graph().parse(ROOT / target, format="xml")
        if to_isomorphic(canonical) != to_isomorphic(exported):
            drift.append((source, target, len(canonical), len(exported)))
    if drift:
        for source, target, source_count, target_count in drift:
            print(f"DRIFT {source} ({source_count} triples) != {target} ({target_count} triples)")
        return 1
    print(f"OK: {len(EXPORTS)} RDF/XML exports match their canonical Turtle schemas.")
    return 0


def write_exports():
    for source, target in EXPORTS:
        graph = read_turtle(source)
        graph.serialize(destination=str(ROOT / target), format="xml", encoding="utf-8")
        print(f"Wrote {target} from {source} ({len(graph)} triples).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Report stale exports without writing.")
    options = parser.parse_args()
    raise SystemExit(check_exports() if options.check else (write_exports() or 0))
