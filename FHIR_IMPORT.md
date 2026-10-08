# Local FHIR R5 ingestion and round-trip boundaries

`fhir_import.py` accepts a bounded, closed `Bundle` with `type=collection`. It
maps Patient, Task, Observation, and DiagnosticReport exchange facts to a fresh
local RDF graph, and retains OperationOutcome and unsupported fields in the raw
source sidecar. This is an ingestion graph, not a complete clinical importer or
an assertion of clinical correctness.

## Commands

```powershell
.\.venv\Scripts\python.exe fhir_import.py --bundle C:\local\input.json
.\.venv\Scripts\python.exe fhir_import.py --synthetic-fixture
.\.venv\Scripts\python.exe fhir_import.py --bundle C:\local\input.json --output-dir .runtime\fhir-imports\review-001
.\.venv\Scripts\python.exe fhir_roundtrip.py --official structural --output-dir .runtime\fhir-roundtrip-check
```

CLI imports always publish a new directory under `.runtime/fhir-imports`; an
existing directory is rejected. The source file and existing project datasets
are never modified. This command does not merge imports into a selected project.
The final directory appears only after all artifacts have been written.

The round-trip runner uses only the pinned, entirely constructed repository
fixture. It accepts no arbitrary Bundle or patient dataset, and its optional
official check is offline structural validation. Existing terminology evidence
for the source fixture is documented in `healthcare-fhir-crosswalk.md`; a
round-trip structural pass does not imply new terminology validation.

## Output and privacy

| Artifact | Contents and access |
| --- | --- |
| `healthcare-import.ttl` | Fresh opaque RDF URNs and supported exchange facts. No original resource IDs, fullUrls, Patient names, identifiers, or `health:patientId`. |
| `import-report.json` | Sanitized counts, fixed field paths/actions, source digest, mapping limits, and storage protection status. It contains no incoming field values or arbitrary key names. |
| `protected/source-bundle.json` | Exact original input bytes, including unmapped fields. Treat it as sensitive. |
| `protected/mapping.json` | Original fullUrls and ResourceType/id references mapped to new local URNs. Treat it as sensitive. |

Before writing any source bytes, the staging directory is restricted to the
current Windows account and SYSTEM using an explicit ACL with inherited access
removed. On POSIX it uses owner-only directory/file modes. Protection failures
abort publication and remove staging output. These controls do not encrypt data
and do not exclude an operating-system administrator. Runtime files are ignored
by Git. Retention and deletion of sensitive source sidecars are an operator
responsibility; do not commit or upload these directories.

Every arbitrary input receives `health:Unverified`, even if its metadata claims
Synthetic or it is identical to a previously exported fixture Bundle. The only
Synthetic entry point loads the exact SHA-256-pinned
`tests/fixtures/fhir/synthetic-clinical.ttl` and exports it internally. Modified
fixture bytes fail closed. There is no `--trust-synthetic` option.

Unverified `valueString` and `conclusion` are retained only in the protected
source because free text can contain direct identifiers. Known fixture text is
safe to map. Unverified graphs are hidden by the existing healthcare redaction
policy and are ineligible for synthetic-only FHIR export.

## Accepted subset

- A closed collection with unique fullUrls and resource IDs, identified entries,
  and timezone-aware full timestamps where mapped.
- Patient references resolve within the Bundle, using either fullUrl or
  `ResourceType/id`. External and contained resource references are rejected;
  the importer never fetches resources or calls a terminology service.
- Exactly one code-system/code pair per Observation or DiagnosticReport.
  Multiple codings are rejected rather than silently choosing one.
- Numeric Observation values need a finite JSON number and coded unit; text
  values are source-only for unverified data. Multiple value choices are rejected.
- Every mapped Observation and DiagnosticReport has exactly one Task.output
  reference association. Subjects must agree. Report results must reference
  Observations of the same subject. Missing, duplicate, or cross-subject
  associations fail without inventing provenance.
- Valid FHIR Task states with no local equivalent remain in the sidecar, with
  an explicit loss action. Local status is never guessed.

The import uses existing local structure/reference/lexical checks, not a general
FHIR validator. These checks deliberately reject several valid FHIR patterns
outside this bounded model. LOINC/UCUM terminology correctness, partner profiles,
clinical interpretation, and authorization are outside local acceptance.

## Studio validation and semantic equivalence

Import acceptance is distinct from the full studio healthcare SHACL profile.
Imports omit display labels, patient internal keys, analysis agents, and model
confidence when the source does not establish them. The import report states
these gaps; they must be reviewed under an appropriate ingestion profile before
project adoption. No confidence score, actor, or identity is fabricated to make
studio validation pass.

The constructed round-trip compares supported class/relationship facts,
workflow status and intent, code/system, quantity/unit, timestamps, report
status/code/results, and known synthetic report text. Original patient keys,
RDF subject URIs, FHIR resource IDs, profile/category metadata, and arbitrary
unmapped fields are outside RDF semantic equivalence. They are described in
`reports/fhir-field-loss-matrix.json` and `FHIR_FIELD_LOSS_MATRIX.md`.

Restoring `protected/source-bundle.json` recovers the original JSON document
byte-for-byte, including unsupported fields. Re-exporting RDF creates a new,
privacy-filtered Bundle and does not reconstruct all original fields. Restoring
source bytes and exporting a local graph are separate operations.
