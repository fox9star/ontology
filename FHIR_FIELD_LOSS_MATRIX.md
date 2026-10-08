# FHIR field mapping and information retention

Machine-readable counterpart: `reports/fhir-field-loss-matrix.json`.

| Source field | Local RDF import | Re-export or loss boundary |
| --- | --- | --- |
| Bundle.id/type/timestamp | No Bundle identity node | New collection ID/timestamp generated; original bytes retained. |
| entry.fullUrl / resource.id | Fresh local URN; mapping in protected sidecar | Fresh IDs on export; original identity omitted. |
| Patient.resourceType | `health:PatientRecord` | Synthetic patients export as opaque Patient resources. |
| Patient.name/identifier/contact/address/birthDate and other demographics | Sidecar only | Never emitted by this synthetic-only exporter. |
| Patient.meta/security or any input Synthetic assertion | No trust promotion | Arbitrary input remains Unverified. |
| Task.for | `health:associatedWithRecord` | Equivalent opaque subject link. |
| Task.status requested/in-progress/completed/failed/cancelled | PENDING/ANALYZING/COMPLETED/FAILED/CANCELLED | Corresponding FHIR code preserved. |
| Task.businessStatus.text exactly VERIFIED with completed status | VERIFIED | Export includes completed plus VERIFIED businessStatus. Other content is sidecar only. |
| Other valid Task.status codes | Sidecar only; no guessed local status | Task omitted on export if no valid local state exists. |
| Task.intent | `health:taskIntent` | Supported R5 intent code preserved. |
| Task.executionPeriod.start/end | `prov:startedAtTime` / `prov:endedAtTime` | Instants preserved; equivalent lexical/timezone spelling may normalize. |
| Task.output.valueReference | `health:generatesObservation` / `health:generatesReport`; Observation `prov:wasGeneratedBy` | Subject-consistent result links preserved. Exactly one Task association required. |
| Task.output.type and unsupported output value choices | Sidecar only | Export regenerates generic result-type text. |
| Observation.code.coding[0].system/code | `health:codeSystem` / `health:observationCode` | Single coding preserved. Known URI aliases normalize on export. Extra codings reject input. |
| Observation.code text, display, version, userSelected | Sidecar only | Not reconstructed. |
| Observation.subject/status/effectiveDateTime | `health:observesRecord` / `health:observationStatus` / `health:observedAt` | Subject/status and supported full timestamp preserved. |
| Observation.valueQuantity value/system/code | `health:numericValue` / `health:unitCodeSystem` / `health:unitCode` | Finite supported JSON quantity/code preserved. Exact source numeric spelling remains in raw bytes. |
| Observation.valueQuantity.unit | Local coded unit uses code, not arbitrary display | Display differences reported; raw display retained. |
| Observation.valueString | Known fixture text maps to `health:textValue`; unverified text stays sidecar only | Unverified text observation is not eligible for export. |
| Observation.category | Sidecar only | Exporter reconstructs only its known body-weight category/profile behavior. |
| DiagnosticReport.code.coding[0].system/code/status | `health:reportCodeSystem` / `health:reportCode` / `health:reportStatus` | Single coding/status preserved; extra codings reject input. |
| DiagnosticReport.subject | Derived through its explicit owning Task | Subject consistency required; no invented Task or provenance. |
| DiagnosticReport.result | `health:reportResult` | Closed, same-subject Observation references preserved. |
| DiagnosticReport.conclusion | Known synthetic fixture maps to `health:findingText`; unverified text stays sidecar only | No arbitrary free text emitted from unverified import. |
| OperationOutcome.issue | Sidecar only | Original warnings not reconstructed from local graph. |
| All other fields on accepted resources and Bundle/entry metadata | Exact original bytes in restricted sidecar | No implied RDF semantics or re-export fidelity. |
| Unsupported resource types/contained patterns or invalid mappings | Import rejected; input file preserved | No partial dataset published and no remote fetch. |

The matrix describes this bounded exchange implementation. It does not assert
FHIR resource equivalence, complete clinical coverage, lossless RDF mapping, or
partner-profile conformance.
