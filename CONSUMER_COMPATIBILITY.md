# Consumer contract review gate

The existing `ontology-compatibility-baseline.json` compares schema axioms.
`consumer_compatibility.py` adds a separate conservative gate for consumers of
SHACL acceptance, selected HTTP response shapes, and documented competency
questions. Neither baseline substitutes for the other.

```powershell
# Normal check: exit 0 compatible; exit 1 review required or collection blocked.
.\.venv\Scripts\python.exe consumer_compatibility.py

# Explicit initialization/replacement after reviewing all affected contracts.
.\.venv\Scripts\python.exe consumer_compatibility.py --write-baseline

# Targeted mutation checks.
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_consumer_compatibility.py -v
```

Normal checks never create or rewrite the baseline. Review the report and
prepare consumer changes, migration instructions, and an appropriate release
version before explicitly accepting a changed baseline. A reported change is a
request for major compatibility review, not an automatic proof that every
consumer breaks or that a version bump alone resolves the change.

Collection failures produce a `blocked` report and a nonzero exit code. The
report records the exception type without source values. A change that makes a
frozen accept/reject fixture fail its named expectation blocks collection before
comparison; inspect the changed shape or fixture and retain the baseline during
that review.

## Frozen contracts

| Contract | Evidence captured | Drift policy |
| --- | --- | --- |
| Eight SHACL profiles | Semantic triples for the seven application profiles plus evidence, including shared shapes | Any change in an existing profile requires review. Anonymous node identifiers and presentation messages are ignored. |
| Sixteen constructed acceptance/rejection cases | Each profile's old raw and RDFS-expanded acceptance/rejection plus immutable input digest | Changed acceptance in either phase or changed source fixture requires review. |
| OpenAPI operations | Parameters, request constraints, response status/media/schema declarations, security and reusable components | Removing/changing a prior operation or declaration requires review. New operations are allowed. |
| Two actual Flask read-only responses | GET `/api/v1/domains` and GET `/api/v1/auth/identity` status/media and recursive JSON key/type shapes | Removed fields or changed types/status/media require review; new fields are additive. Response values are never stored. |
| Forty documented questions | Query digest, output variables, golden answer, and input-fixture/factory digests for 37 main and three evidence questions | Old query/variable/answer/input changes require review; new questions are additive. |

The fixture uses constructed images, artifacts, a product, an academic course,
and an evidence claim. The healthcare acceptance case is an analysis agent with
a label; it contains no patient record and does not establish compatibility for
complete diagnostic workflows. Coverage is intentionally stated at the case
level. Extend the frozen case catalog through explicit review when important
consumer workflows need representation.

SHACL graph equality is a conservative change detector. It does not prove
logical equivalence between different shapes, and adding a constraint to an
existing profile can be a breaking change even when its current small fixtures
still pass. Acceptance cases use `validation_pipeline.validate_phases`, so
domain/range inference cannot silently repair absent explicit instance types.

Golden question snapshots retain the existing reviewed answer files and
deterministically calculated benchmark answers. Evidence answers execute only
the committed synthetic evidence example. Healthcare questions remain
constructed aggregate-only cases; the real healthcare example and project
patient datasets are never snapshotted. Existing CQ regression tests remain the
execution gate for all question answers; this compatibility gate also protects
their output contract from drift.

This is bounded coverage. It does not verify every HTTP operation's behavior,
authentication semantics, every possible SHACL instance, FHIR exchange fidelity,
clinical safety, or partner implementation-guide compatibility. The FHIR loss
matrix and separate importer/official validator gates document their scope.

Custom profiles are discovered from validated local catalog metadata. They
provide separate immutable question fixtures, reviewed answer files and
`consumer-cases.trig` acceptance/rejection graphs. The current collection also
executes AI-film's two acceptance cases and five questions: 9 shape profiles,
18 acceptance cases and 45 questions in total. The original baseline remains
8 profiles/16 cases/40 questions; additions are accepted after their executable
fixtures pass. They become protected snapshot contracts when a new reviewed
baseline is explicitly recorded. No CI command rewrites the existing baseline.
