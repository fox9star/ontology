# Healthcare ontology interoperability crosswalk

This guide documents the mapping used by the local, synthetic-only FHIR R5 export. It does not assert that local classes are equivalent to FHIR resources.

| Local class or property | FHIR R5 candidate | Mapping note |
| --- | --- | --- |
| `health:PatientRecord` | `Patient` | Keep identity linkage outside the local graph. Map an opaque reference only in an authorized exchange context. |
| `health:DiagnosticTask` | `Task` plus its result resources | The local class models an analysis execution; map workflow state separately from its clinical result. |
| `health:ClinicalObservation` | `Observation` | Map code system, code, value, unit, effective time, and subject only when those facts are present and verified. |
| `health:ClinicalReport` | `DiagnosticReport` | Map report status and findings, and reference coded `Observation` results where available. |
| `health:MedicalAnalysisAgent` | `Device`, `Organization`, or a practitioner-related resource | Choose the target based on the real system or responsible party; the class alone does not establish that identity. |
| `health:dataClassification` | Security labels, consent, and local access policy | FHIR security labels can carry exchange metadata, but they do not replace authorization in this application. |

The local model keeps direct patient identifiers and the identity-mapping table outside the graph. Its in-graph `health:patientId` value is an opaque internal key and is redacted by default. The privacy classification controls API redaction in this application; filesystem access and encryption at rest remain operating-system responsibilities.

## Implemented export

`GET /api/v1/healthcare/fhir-bundle` returns a FHIR R5 JSON `Bundle` with `type=collection` for the selected healthcare project. It includes only records explicitly classified `Synthetic`; patient keys and local RDF subject URIs are not emitted. Resource IDs are freshly generated per export to avoid stable cross-export identifiers.

The exporter maps available patient, diagnostic task, observation, and report data. It requires coded observation and report types, a valid report status, and a unit code plus unit system for quantitative values. Ambiguous scalar fields, observations linked to a task for a different subject, and reports attached to multiple tasks are omitted. A resource that lacks required exchange fields is omitted; the Bundle may include a generic `OperationOutcome` warning. Model confidence scores and local patient keys are not exported. Empty collections omit the `entry` property because FHIR JSON does not represent empty arrays.

The known `https://loinc.org` and `https://unitsofmeasure.org` aliases are normalized to their canonical exchange identifiers. For LOINC `29463-7`, the exporter applies the R5 [Body Weight profile](https://hl7.org/fhir/R5/bodyweight.html): its required `vital-signs` category, an effective time, and a UCUM quantity using `kg`, `g`, or `[lb_av]`. Other clinical code profiles need their own explicit mapping and validation before exchange.

FHIR R5 defines JSON, XML, and RDF/Turtle representations. Its RDF format is positioned primarily for analysis and knowledge processing, so this project uses the table as a crosswalk and keeps Turtle as its canonical local representation. See the official [FHIR R5 resource formats](https://hl7.org/fhir/R5/resource-formats.html), [Patient](https://hl7.org/fhir/R5/patient.html), [Observation](https://hl7.org/fhir/R5/observation.html), [DiagnosticReport](https://hl7.org/fhir/R5/diagnosticreport.html), and [Task](https://hl7.org/fhir/R5/task.html) definitions.

## Validation commands

`fhir_validation.py` checks the bounded local export contract for Patient, Task, Observation, DiagnosticReport, and OperationOutcome. It recursively resolves references in every nested object and array, including relative `ResourceType/id` and entry-scoped contained references. It rejects duplicate identities/fullUrls, malformed codes and code-system URIs, nonnumeric or nonfinite quantities, invalid timestamps, conflicting observation values, invalid subject/result types, and cross-subject report results. These checks inspect lexical and structural unit data; they do not verify arbitrary UCUM or LOINC codes.

`fhir_validate.py` provides three separate modes. In Windows PowerShell use `.\.venv\Scripts\python.exe` in place of `python` below:

```text
python fhir_validate.py --synthetic-fixture --output-dir .runtime/fhir-validation-local
python fhir_validate.py --synthetic-fixture --official structural --fetch-validator --output-dir .runtime/fhir-validation-structural
python fhir_validate.py --synthetic-fixture --official terminology --fetch-validator --output-dir .runtime/fhir-validation-terminology
```

Local-only validation of an existing JSON file is available with `--bundle file.json`. Official validation accepts only the committed, entirely constructed `tests/fixtures/fhir/synthetic-clinical.ttl` fixture. It never reads a project dataset or an API response. An arbitrary `--bundle` cannot be passed to the official modes.

The official runner uses the local [HL7 Java validator 6.10.4 release](https://github.com/hapifhir/org.hl7.fhir.core/releases/tag/6.10.4), FHIR R5 `5.0.0`, and the Bundle base profile. The engine also validates referenced resources and implicit profiles, including body weight when its LOINC code is present. Configuration and SHA-256 pins are in `fhir-validator-config.json`; `--fetch-validator` prepares the verified JAR and all five pinned engine packages beneath `.runtime/fhir-tools`. Java is discovered on PATH, through `--java`, or in the project's portable runtime. `--validator-jar` can choose a different local path, but its contents must match the pinned JAR checksum.

The runner checks every cached definition file against its verified package archive. The engine-generated `.index.json` search indexes are excluded from content checks; extra JSON definition files are rejected. Archive extraction accepts ordinary files/directories below `package/` and rejects path escapes, links, and special members on Python 3.10 and newer. A run also checks the engine's reported package set against the configuration, so a dynamically loaded or missing package does not produce a passing gate.

Official structural mode uses `-tx n/a -no-http-access` after package preparation. It verifies profiles and computable R5 constraints offline and reports `terminology_service_validated=false`. Terminology mode uses the configured HTTPS service and a fresh, isolated terminology cache, records the service log, and requires evidence of `$validate-code` or `$expand` calls before claiming terminology-service coverage. Setup downloads and terminology mode require network access. The Java resource fetcher is disabled, and the runner passes an explicit settings file without API keys.

To validate a partner's implementation guide, add its exact `package#version`, its SHA-256-verified archive, and all dependencies to the configuration, then use `--ig package#version --profile canonical-profile-uri`. Package servers are disabled during official execution; missing definitions remain a failing/incomplete check. No partner guide has been selected for this project, so the current gate asserts only base R5 and applicable core profile conformance for the constructed fixture.

Each mode writes `validation-report.json`. Official modes additionally write `<mode>-validator.log`, `<mode>-outcome.json`, and, for terminology mode, a terminology service log. The report records input hash, validator/hash/Java version, loaded packages, profiles, terminology mode, issue counts, and outcome paths. Exit codes are **0 passed, 1 failed, 2 blocked/incomplete, 3 requested validation skipped**. Every unsuccessful requested official check exits nonzero. A timeout fails, and stale outcome files are removed before each run.

## Observed validation evidence

On 2026-10-05 the actual official offline structural run passed with Java Temurin 21.0.12.1, validator 6.10.4, R5 5.0.0, and all five verified pinned packages. It returned zero fatal/errors, six warnings, and five informational messages. The first run identified two missing category constraints from the implicit Body Weight profile; the exporter was corrected and the passing run repeated. Retained warnings concern narrative/performer recommendations and external terminology that cannot be verified offline. Live artifacts are under `.runtime/fhir-validation-structural`.

The separate actual terminology run also passed on 2026-10-05. Its fresh service log records `$validate-code` calls to `https://tx.fhir.org/r5`; the result contained zero fatal/errors, four warnings, and four informational messages. Narrative/performer recommendations remain warnings, and two informational Task output-type bindings have no defined source. This confirms the fixture's configured terminology checks were executed; it does not establish partner-specific bindings or clinical correctness. Live artifacts are under `.runtime/fhir-validation-terminology`.

`fhir-validation-evidence.json` preserves the observed modes, pinned and loaded versions, input/artifact hashes, issue counts/findings, and trust limits in a compact committed record. Raw runtime logs and OperationOutcomes are intentionally kept under `.runtime`.

The original targeted 23-test regression suite covers RDF/JSON round trips, privacy and fresh identifiers, reference scopes, malformed values, subject consistency, body-weight profile fields, decimal precision, timezone order, cached-definition tampering, unsafe archives, checksum rejection, absent validators, and timeout/stale-outcome behavior. Its original round trip was local RDF serialization followed by FHIR JSON serialization/deserialization.

## Bounded FHIR-to-local import

`fhir_import.py` now provides local-only collection ingestion for the supported
exchange fields, with fresh local resource identities, explicit closed-reference
and subject checks, and a sanitized field-loss report. Every arbitrary input is
Unverified; incoming metadata cannot establish Synthetic trust. Patient identity
fields and unverified clinical free text remain in a restricted, exact-byte raw
source sidecar. Only the checksum-pinned constructed fixture has a Synthetic
entry point. Existing project datasets are never overwritten or merged.

`fhir_roundtrip.py` compares the constructed fixture's supported local facts
after actual FHIR-to-local RDF import and validates its new FHIR export. Optional
official validation is offline structural mode, with the same pinned tool and
packages. This demonstrates supported semantic equivalence, not a lossless
clinical import or conformance to a partner implementation guide.

See [FHIR_IMPORT.md](FHIR_IMPORT.md) for commands, acceptance and storage rules,
and [FHIR_FIELD_LOSS_MATRIX.md](FHIR_FIELD_LOSS_MATRIX.md) for field-level
preservation, privacy withholding, normalization, and re-export limits.
