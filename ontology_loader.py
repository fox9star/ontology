"""Load canonical schemas and their bundled core/vocabulary without network imports."""

import hashlib
from pathlib import Path

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, RDF
from rdflib.compare import isomorphic
from ontology_registry import local_path, read_registry


CORE_ONTOLOGY_URI = URIRef("https://example.org/ontology/core")
CONTROLLED_VOCAB_ONTOLOGY_URI = URIRef("https://example.org/ontology/vocab")


def _configured_path(root, filename, kind):
    """Resolve a trusted static config path while blocking relative traversal."""
    candidate = Path(filename)
    path = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    if not candidate.is_absolute() and not path.is_relative_to(root):
        raise ValueError(f"Ontology {kind} path escapes the application directory")
    return path


def load_schema_bundle(base_dir, schema_name):
    """Resolve transitive local ontology/version IRIs and return closure evidence.

    Only explicitly listed external imports remain references. Never fetch
    imports over the network. Unresolved imports, collisions and cycles fail.
    """
    root = Path(base_dir).resolve()
    path = _configured_path(root, schema_name, "schema")
    if not path.is_file():
        raise FileNotFoundError(f"Ontology schema not found: {path.name}")
    registry = read_registry(root)
    aliases, modules, metadata, captured = {}, {}, {}, {}
    for entry in registry["modules"]:
        filename = entry["schema"]
        source = local_path(root, filename)
        if not source.is_file():
            raise FileNotFoundError(f"Registered local schema is missing: {filename}")
        payload = source.read_bytes()
        captured[source] = payload
        module = Graph().parse(data=payload, publicID=source.as_uri(), format="turtle" if source.suffix.lower() == ".ttl" else "xml")
        nodes = set(module.subjects(RDF.type, OWL.Ontology))
        if len(nodes) != 1:
            if registry.get("strict_declarations", True) or nodes:
                raise ValueError(f"Registered module must declare one ontology: {filename}")
            continue
        ontology = next(iter(nodes))
        versions = list(module.objects(ontology, OWL.versionIRI))
        if not isinstance(ontology, URIRef) or len(versions) > 1 or any(not isinstance(value, URIRef) for value in versions):
            raise ValueError(f"Invalid module ontology/version IRI: {filename}")
        for alias in [ontology, *versions]:
            if alias in aliases and aliases[alias] != filename:
                raise ValueError(f"Local ontology/version IRI collision: {alias}")
            aliases[alias] = filename
        modules[filename] = module
        metadata[filename] = {"file": filename, "ontology": str(ontology),
                              "version": str(module.value(ontology, OWL.versionInfo) or ""),
                              "sha256": hashlib.sha256(payload).hexdigest()}
    initial_bytes = captured[path] if path in captured else path.read_bytes()
    initial = Graph().parse(data=initial_bytes, publicID=path.as_uri(), format="turtle" if path.suffix.lower() == ".ttl" else "xml")
    nodes = set(initial.subjects(RDF.type, OWL.Ontology))
    initial_id = aliases.get(next(iter(nodes))) if len(nodes) == 1 else None
    if initial_id and not isomorphic(initial, modules[initial_id]):
        raise ValueError("Requested schema representation differs from its registered canonical module")
    initial_id = initial_id or str(path)
    graph, visiting, visited, loaded, external = Graph(), set(), set(), {}, set()
    allowed_external = {URIRef(value) for value in registry.get("external_imports", [])}

    def visit(identifier, module):
        if identifier in visiting:
            raise ValueError("Local ontology import cycle")
        if identifier in visited:
            return
        visiting.add(identifier)
        for imported in sorted(set(module.objects(None, OWL.imports)), key=str):
            if not isinstance(imported, URIRef):
                raise ValueError("Ontology imports must use an IRI")
            if imported in aliases:
                dependency = aliases[imported]
                visit(dependency, modules[dependency])
            elif imported in allowed_external:
                external.add(str(imported))
            else:
                raise FileNotFoundError(f"Unresolved local ontology import: {imported}")
        graph.__iadd__(module)
        visiting.remove(identifier)
        visited.add(identifier)
        if identifier in metadata:
            loaded[identifier] = metadata[identifier]

    visit(initial_id, initial)
    details = {"root_source": {"file": path.name, "sha256": hashlib.sha256(initial_bytes).hexdigest()},
               "modules": [loaded[name] for name in sorted(loaded)],
               "external_references_not_loaded": sorted(external), "network_imports": False}
    return graph, details


def load_schema_graph(base_dir, schema_name):
    return load_schema_bundle(base_dir, schema_name)[0]


def load_shape_graph(base_dir, shapes_name):
    """Load domain SHACL shapes together with shared core constraints."""
    root = Path(base_dir).resolve()
    path = _configured_path(root, shapes_name, "shapes")
    if not path.is_file():
        raise FileNotFoundError(f"Ontology shapes not found: {path.name}")

    graph = Graph().parse(path, format="turtle")
    for filename in read_registry(root).get("shared_shapes", []):
        shared = local_path(root, filename)
        if not shared.is_file():
            raise FileNotFoundError(f"Registered shared shapes are missing: {filename}")
        if path != shared:
            graph.parse(shared, format="turtle")
    return graph
