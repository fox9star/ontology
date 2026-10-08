# Namespace and URI migration worksheet

Complete this worksheet before a public release. Keep `example.org` terms in development data until an owned namespace is selected. The repository's `namespace_policy.py --release` command must pass after the migration.

## Namespace decisions

| Vocabulary | Current namespace | New owned namespace | Owner and contact | Versioned URI policy |
| --- | --- | --- | --- | --- |
| Core | `https://example.org/ontology/core#` |  |  |  |
| Music video and E2E | `https://example.org/mv#` |  |  |  |
| Agent collaboration | `https://example.org/agent#` |  |  |  |
| DevOps | `http://example.org/ontology/devops#` |  |  |  |
| E-commerce | `http://example.org/ontology/ecommerce#` |  |  |  |
| Healthcare | `http://example.org/ontology/healthcare#` |  |  |  |
| Academic | `https://example.org/ontology/academic#` |  |  |  |
| Controlled vocabulary | `https://example.org/ontology/vocab#` |  |  |  |

## Term-level mappings

| Old IRI | New IRI | Action (`move`, `deprecate`, `retain`) | Semantic change | Compatibility period | Consumer impact |
| --- | --- | --- | --- | --- | --- |
|  |  |  |  |  |  |

## Migration checklist

- Preserve each local term's suffix unless the concept itself is changing.
- Update schema, SHACL, examples, project instance graphs, competency queries, app namespace configuration, SPARQL templates, tests, and API documentation.
- Migrate stored graph snapshots only with an explicit backup and a reviewed old-to-new IRI map. Do not rewrite literal strings, external media URLs, unknown provenance, or source files as part of an IRI-only change.
- Add `owl:deprecated true` and `dcterms:isReplacedBy` to terms that remain published only for compatibility. Do not assert `owl:equivalentClass` or `owl:equivalentProperty` unless the semantics truly match.
- Rebuild RDF/XML exports, run `verify_all.py`, `controlled_vocab_check.py`, `namespace_policy.py --release`, and the full unit suite.
- Record the old/new version, migration date, affected graph hashes, and rollback procedure in release notes.


## Prepared migration tool

The release hostname is undecided. Keep the development IRIs until the owner domain and consumer compatibility plan are recorded above.

```powershell
# Read-only preview; replace the placeholder with a hostname you control.
.\.venv\Scripts\python.exe .\namespace_migration.py --host <owned-hostname>

# Apply only after reviewing the dry-run file list and term mapping.
.\.venv\Scripts\python.exe .\namespace_migration.py --host <owned-hostname> --apply

# Include project graphs and snapshots only after their migration is reviewed.
.\.venv\Scripts\python.exe .\namespace_migration.py --host <owned-hostname> --apply --include-project-data
```

Apply mode saves a copy of each changed file under `.runtime/namespace-migrations/<timestamp>/`. The default scan excludes `projects/` and `snapshots/`, and leaves unrelated asset URLs such as `https://example.org/assets/...` unchanged. After migration, regenerate RDF/XML and run `verify_all.py`, `controlled_vocab_check.py`, `namespace_policy.py --release`, the export parity check, and the full test suite.

## Lifecycle and compatibility gates

The owner domain remains undecided. No public IRI has been migrated by preparing these tools, and development checks do not mark a release ready.

- Follow [TERM_LIFECYCLE.md](TERM_LIFECYCLE.md) for reviewed retirement, replacement and equivalence decisions.
- Run `term_lifecycle.py check` to reject missing/incorrect replacement targets, role changes, replacement chains/cycles, duplicate declarations and unreviewed equivalence assertions.
- Compare the candidate against a preserved reviewed baseline with `term_lifecycle.py compare --previous ontology-compatibility-baseline.json`. Removed terms, changed asserted semantics, ontology IRIs or imports require an affected-module major version increase. Do not regenerate the baseline automatically to silence compatibility failures.
- Record SHACL acceptance changes and test previous instance fixtures as well as schema axioms. The baseline command measures schema compatibility; API, query and data migration compatibility also require reviewed consumer evidence.
- Run `ontology_docs_check.py` for measured Korean and English label/definition coverage; explicit translation exceptions must identify one term and reason and cannot inflate coverage.
- Review `namespace_policy.py`'s limited healthcare SKOS namespace exception and explicit offline external import list when the namespace policy changes.
