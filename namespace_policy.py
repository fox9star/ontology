"""Check ontology URI/version declarations and guard placeholder releases."""

import argparse
import re
from pathlib import Path
from urllib.parse import urlsplit

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF, RDFS, SKOS
from ontology_registry import schema_files, read_registry

ROOT = Path(__file__).resolve().parent
SCHEMA_FILES = schema_files(ROOT)
_NUMERIC_VERSION = r"(?:0|[1-9][0-9]*)"
_PRERELEASE_PART = rf"(?:{_NUMERIC_VERSION}|[0-9A-Za-z-]*[A-Za-z-][0-9A-Za-z-]*)"
SEMVER = re.compile(rf"^{_NUMERIC_VERSION}\.{_NUMERIC_VERSION}\.{_NUMERIC_VERSION}(?:-{_PRERELEASE_PART}(?:\.{_PRERELEASE_PART})*)?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$")
PLACEHOLDER_HOSTS = {"example.org", "www.example.org", "example.com", "www.example.com"}
EXTERNAL_IMPORTS = frozenset(read_registry(ROOT)["external_imports"])
# Shared SKOS status/privacy concepts retain the healthcare IRIs used by data.
# This exception permits only concept roles, never schema classes/properties.
NAMESPACE_EXCEPTIONS = {
    "controlled-vocabularies.ttl": {
        "http://example.org/ontology/healthcare#": {"concept", "concept_scheme"},
    },
}
TERM_ROLES = {
    OWL.Class: "class", RDFS.Class: "class",
    OWL.ObjectProperty: "object_property", OWL.DatatypeProperty: "datatype_property",
    OWL.AnnotationProperty: "annotation_property", RDF.Property: "property",
    SKOS.Concept: "concept", SKOS.ConceptScheme: "concept_scheme",
}


def is_absolute_iri(value):
    """Accept an RDF IRI with a scheme, never literals or relative paths."""
    if not isinstance(value, URIRef) or any(char.isspace() or ord(char) < 32 for char in str(value)):
        return False
    try:
        parsed = urlsplit(str(value))
    except ValueError:
        return False
    return bool(parsed.scheme and str(value).split(":", 1)[1] and (parsed.netloc if parsed.scheme in ("http", "https") else True))


def declared_terms(graph):
    """Return named term roles; duplicate owl:Class/rdfs:Class is one role."""
    terms = {}
    for term_type, role in TERM_ROLES.items():
        for term in graph.subjects(RDF.type, term_type):
            if isinstance(term, URIRef):
                terms.setdefault(term, set()).add(role)
    return terms


def _host(value):
    try:
        return (urlsplit(str(value)).hostname or "").lower()
    except ValueError:
        return ""


def read_schema_bundle(root=ROOT):
    """Read only bundled schemas; external imports are never downloaded."""
    root = Path(root)
    return {filename: Graph().parse(root / filename, format="turtle") for filename in SCHEMA_FILES}


def check_namespaces(root=ROOT, release=False, external_imports=EXTERNAL_IMPORTS):
    """Return policy errors; development mode permits reserved example.org IRIs."""
    root = Path(root)
    errors = []
    seen = {}
    graphs = read_schema_bundle(root)
    term_owners = {}
    module_imports = {}
    version_iris = {}
    for filename, graph in graphs.items():
        ontology_nodes = set(graph.subjects(RDF.type, OWL.Ontology))
        if len(ontology_nodes) != 1:
            errors.append(f"{filename}: expected exactly one owl:Ontology declaration")
            continue
        ontology = next(iter(ontology_nodes))
        if not is_absolute_iri(ontology):
            errors.append(f"{filename}: owl:Ontology must have an absolute IRI")
        if ontology in seen:
            errors.append(f"{filename}: ontology URI is already declared in {seen[ontology]}")
        seen[ontology] = filename
        imports = set(graph.objects(ontology, OWL.imports))
        module_imports[ontology] = imports
        for imported in imports:
            if not is_absolute_iri(imported):
                errors.append(f"{filename}: owl:imports must reference an absolute IRI")
        declared_versions = list(graph.objects(ontology, OWL.versionIRI))
        if len(declared_versions) > 1:
            errors.append(f"{filename}: owl:versionIRI must have at most one IRI")
        for version_iri in declared_versions:
            if not is_absolute_iri(version_iri):
                errors.append(f"{filename}: owl:versionIRI must reference an absolute IRI")
            if version_iri in version_iris:
                errors.append(f"{filename}: version IRI is already declared in {version_iris[version_iri]}")
            version_iris[version_iri] = filename
            if release and _host(version_iri) in PLACEHOLDER_HOSTS:
                errors.append(f"{filename}: placeholder version IRI {version_iri} cannot be published")
        versions = [str(value) for value in graph.objects(ontology, OWL.versionInfo)]
        if len(versions) != 1 or not SEMVER.fullmatch(versions[0]):
            errors.append(f"{filename}: owl:versionInfo must contain one semantic version")
        host = _host(ontology)
        if release and host in PLACEHOLDER_HOSTS:
            errors.append(f"{filename}: placeholder namespace {ontology} cannot be published")
        namespace = f"{str(ontology).rstrip('#/')}#"
        for term, roles in declared_terms(graph).items():
            allowed_shared = any(
                str(term).startswith(prefix) and str(term) != prefix and roles <= allowed_roles
                for prefix, allowed_roles in NAMESPACE_EXCEPTIONS.get(filename, {}).items()
            )
            if not is_absolute_iri(term) or not (str(term).startswith(namespace) and str(term) != namespace or allowed_shared):
                errors.append(f"{filename}: declared term {term} is outside its module namespace {namespace}")
            if term in term_owners:
                errors.append(f"{filename}: term {term} is already declared in {term_owners[term]}")
            term_owners[term] = filename
            if release and _host(term) in PLACEHOLDER_HOSTS:
                errors.append(f"{filename}: placeholder term namespace {term} cannot be published")
            specific_roles = roles - {"property"}
            if len(specific_roles) > 1:
                errors.append(f"{filename}: term {term} has conflicting roles {sorted(specific_roles)}")
    import_targets = {ontology: ontology for ontology in seen}
    for version_iri, filename in version_iris.items():
        ontology_nodes = set(graphs[filename].subjects(RDF.type, OWL.Ontology))
        if len(ontology_nodes) == 1:
            import_targets[version_iri] = next(iter(ontology_nodes))
    for ontology, imports in module_imports.items():
        for imported in imports:
            if imported not in import_targets and str(imported) not in external_imports:
                errors.append(f"{seen[ontology]}: unresolved import {imported}; bundle locally or explicitly approve the external import")
    for version_iri, filename in version_iris.items():
        if version_iri in seen:
            errors.append(f"{filename}: version IRI collides with ontology IRI {version_iri}")

    # Acyclic local imports make module closure deterministic and inspectable.
    visiting, visited = set(), set()

    def visit(ontology, path):
        if ontology in visiting:
            errors.append("Local import cycle: " + " -> ".join(map(str, path + [ontology])))
            return
        if ontology in visited:
            return
        visiting.add(ontology)
        for imported in sorted(module_imports.get(ontology, ()), key=str):
            if imported in import_targets:
                visit(import_targets[imported], path + [ontology])
        visiting.remove(ontology)
        visited.add(ontology)

    for ontology in sorted(seen, key=str):
        visit(ontology, [])
    return errors


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", action="store_true", help="Reject reserved example.org/example.com namespaces")
    parser.add_argument("--root", type=Path, default=ROOT, help="Directory containing the canonical bundled schemas")
    options = parser.parse_args(argv)
    errors = check_namespaces(root=options.root, release=options.release)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    mode = "release" if options.release else "development"
    print(f"OK: {len(SCHEMA_FILES)} modules have unique term namespaces, semantic versions and a resolved local import closure ({mode} policy).")
    if not options.release:
        print("NOTE: --release remains blocked until placeholder example.org namespaces are replaced.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
